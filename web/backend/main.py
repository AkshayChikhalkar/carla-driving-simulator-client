from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from pathlib import Path
import base64
import cv2
import numpy as np
import asyncio
from fastapi import WebSocketDisconnect
import atexit
import signal
from fastapi.responses import FileResponse
from datetime import datetime
import yaml

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.config import Config, load_config, save_config
from src.visualization.display_manager import DisplayManager
from src.utils.logging import Logger
from src.utils.paths import get_project_root

app = FastAPI()
logger = Logger()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize simulation runner
runner = SimulationRunner()

# Web frontend log file handle
web_log_file = None

# Use robust project root
project_root = get_project_root()

class LogWriteRequest(BaseModel):
    content: str

class LogFileRequest(BaseModel):
    filename: str

class SimulationState:
    def __init__(self):
        self.is_running = False
        self.current_scenario = None
        self.scenarios_to_run = []
        self.current_scenario_index = 0
        self.scenario_results = []
        self.batch_start_time = None
        self.current_scenario_completed = False

# Add state to runner
runner.state = SimulationState()

@app.post("/api/logs/directory")
async def create_logs_directory():
    """Ensure logs directory exists"""
    try:
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        return {"message": "Logs directory ready"}
    except Exception as e:
        logger.error(f"Error creating logs directory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/file")
async def create_log_file(request: LogFileRequest):
    """Create or open a log file"""
    global web_log_file
    try:
        log_path = project_root / "logs" / request.filename
        web_log_file = open(log_path, "a", encoding="utf-8")
        return {"message": "Log file opened"}
    except Exception as e:
        logger.error(f"Error creating log file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/write")
async def write_log(request: LogWriteRequest):
    """Write to the current log file"""
    global web_log_file
    try:
        if web_log_file:
            web_log_file.write(request.content)
            web_log_file.flush()
            return {"message": "Log written"}
        else:
            raise HTTPException(status_code=400, detail="No log file open")
    except Exception as e:
        logger.error(f"Error writing to log file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logs/close")
async def close_log_file():
    """Close the current log file"""
    global web_log_file
    try:
        if web_log_file:
            web_log_file.close()
            web_log_file = None
            return {"message": "Log file closed"}
        else:
            raise HTTPException(status_code=400, detail="No log file open")
    except Exception as e:
        logger.error(f"Error closing log file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add cleanup handler
def cleanup_resources():
    """Clean up resources when shutting down"""
    try:
        logger.info("Cleaning up resources...")
        
        # Clean up resources
        if hasattr(runner.app, 'cleanup'):
            runner.app.cleanup()
        
        # Only disconnect from CARLA server if not in web mode
        if hasattr(runner.app, 'connection') and runner.app.connection:
            is_web_mode = getattr(runner.app._config, 'web_mode', False)
            if not is_web_mode:
                logger.debug("CLI mode: Disconnecting from CARLA server")
                runner.app.connection.disconnect()
            else:
                logger.debug("Web mode: Maintaining CARLA connection")
        
        # Clear the app instance
        runner.app = None
        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, lambda s, f: cleanup_resources())
signal.signal(signal.SIGTERM, lambda s, f: cleanup_resources())

# Override the display manager creation in the runner
def create_display_manager(config):
    return DisplayManager(config, web_mode=True)

# Monkey patch the display manager creation
runner.create_display_manager = create_display_manager

class SimulationRequest(BaseModel):
    scenarios: List[str]
    debug: bool = False
    report: bool = False

class ConfigUpdate(BaseModel):
    config_data: dict

@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available scenarios"""
    logger.info("Fetching available scenarios")
    ScenarioRegistry.register_all()
    scenarios = ScenarioRegistry.get_available_scenarios()
    logger.info(f"Found {len(scenarios)} scenarios")
    return {"scenarios": scenarios}

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    logger.info("Fetching current configuration")
    return runner.config

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration"""
    try:
        logger.info("Updating configuration")
        
        # Validate the config data
        if not isinstance(config_update.config_data, dict):
            raise HTTPException(status_code=400, detail="Invalid configuration format")
            
        # Try to create a Config object to validate the structure
        try:
            Config(**config_update.config_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid configuration structure: {str(e)}")
            
        # Save the configuration
        save_config(config_update.config_data, runner.config_file)
        
        # Reload the configuration
        runner.config = load_config(runner.config_file)
        
        logger.info("Configuration updated successfully")
        return {"message": "Configuration updated successfully", "config": runner.config}
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/skip")
async def skip_scenario():
    """Skip the current scenario and move to the next one"""
    try:
        # Check if simulation is running
        if not hasattr(runner, 'app') or not runner.app:
            logger.warn("Attempted to skip scenario while no simulation is running")
            return {"success": False, "message": "No simulation is running"}
        
        # Check if simulation is actually running
        if not runner.app.state.is_running:
            logger.warn("Attempted to skip scenario while simulation is not running")
            return {"success": False, "message": "Simulation is not running"}
        
        logger.info("Skipping current scenario")
        
        # Get current scenario index and total scenarios
        current_index = runner.state.current_scenario_index
        total_scenarios = len(runner.state.scenarios_to_run)
        
        # Record skipped scenario result
        runner.state.scenario_results.append({
            "name": runner.state.current_scenario,
            "result": "Skipped",
            "duration": str(datetime.now() - runner.state.batch_start_time).split('.')[0]
        })
        
        # If there are more scenarios, prepare for next one
        if current_index < total_scenarios - 1:
            next_scenario = runner.state.scenarios_to_run[current_index + 1]
            logger.info(f"Preparing to run next scenario: {next_scenario}")
            
            # Store current app reference
            current_app = runner.app
            
            # Reset cleanup flag
            current_app.is_cleanup_complete = False
            
            # Stop current scenario by setting running flag to False
            current_app.state.is_running = False
            
            # Wait for cleanup to complete
            max_wait_time = 10  # Maximum wait time in seconds
            wait_interval = 0.1  # Check every 100ms
            start_time = datetime.now()
            
            while not current_app.is_cleanup_complete:
                if (datetime.now() - start_time).total_seconds() > max_wait_time:
                    logger.warn("Cleanup wait timeout reached")
                    break
                await asyncio.sleep(wait_interval)
            
            try:
                # Create new application instance for next scenario
                new_app = runner.create_application(next_scenario)
                
                # Set web mode in configuration
                new_app._config.web_mode = True
                
                # Connect to CARLA server
                logger.info("Connecting to CARLA server...")
                if not new_app.connection.connect():
                    logger.error("Failed to connect to CARLA server")
                    return {"success": False, "message": "Failed to connect to CARLA server"}
                
                # Wait for connection to stabilize
                await asyncio.sleep(1)
                
                # Setup components
                logger.info("Setting up simulation components...")
                components = runner.setup_components(new_app)
                
                # Setup application
                logger.info("Setting up application...")
                new_app.setup(
                    world_manager=components['world_manager'],
                    vehicle_controller=components['vehicle_controller'],
                    sensor_manager=components['sensor_manager'],
                    logger=runner.logger
                )
                
                # Update runner state
                runner.state.current_scenario = next_scenario
                runner.state.current_scenario_index = current_index + 1
                runner.app = new_app
                
                # Start simulation in background
                logger.info("Starting simulation thread...")
                import threading
                def run_simulation():
                    try:
                        logger.info("Simulation loop started")
                        new_app.run()
                    except Exception as e:
                        logger.error(f"Error in simulation thread: {str(e)}")
                        if hasattr(new_app, 'state'):
                            new_app.state.is_running = False
                    finally:
                        logger.info("Simulation loop ended")
                
                simulation_thread = threading.Thread(target=run_simulation)
                simulation_thread.daemon = True
                simulation_thread.start()
                
                return {
                    "success": True,
                    "message": f"Skipped scenario {current_index + 1}/{total_scenarios}. Moving to next scenario: {next_scenario}"
                }
                
            except Exception as e:
                logger.error(f"Error during simulation setup: {str(e)}")
                cleanup_resources()
                raise e
                
        else:
            # This was the last scenario
            logger.info("Last scenario skipped. Simulation complete.")
            
            # Reset cleanup flag
            runner.app.is_cleanup_complete = False
            
            # Stop current scenario
            runner.app.state.is_running = False
            
            # Wait for cleanup to complete
            max_wait_time = 10  # Maximum wait time in seconds
            wait_interval = 0.1  # Check every 100ms
            start_time = datetime.now()
            
            while not runner.app.is_cleanup_complete:
                if (datetime.now() - start_time).total_seconds() > max_wait_time:
                    logger.warn("Cleanup wait timeout reached")
                    break
                await asyncio.sleep(wait_interval)
            
            # Generate final report
            if hasattr(runner.app, 'metrics'):
                runner.app.metrics.generate_html_report(
                    runner.state.scenario_results,
                    runner.state.batch_start_time,
                    datetime.now()
                )
            
            return {
                "success": True,
                "message": "Last scenario skipped. Simulation complete."
            }
            
    except Exception as e:
        logger.error(f"Error skipping scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    """Start simulation with given parameters"""
    try:
        # Check if simulation is already running
        if hasattr(runner, 'app') and runner.app and runner.app.state.is_running:
            logger.warn("Attempted to start simulation while already running")
            return {"success": False, "message": "Simulation is already running"}
        
        logger.info(f"Starting simulation with scenarios: {request.scenarios}, debug: {request.debug}, report: {request.report}")
        
        # Register scenarios first
        ScenarioRegistry.register_all()
        
        # Setup logger
        runner.setup_logger(request.debug)
        
        try:
            # Create and store the app instance
            logger.info("Creating application instance...")
            # If "all" is selected, use all available scenarios
            scenarios_to_run = ScenarioRegistry.get_available_scenarios() if "all" in request.scenarios else request.scenarios
            runner.state.scenarios_to_run = scenarios_to_run
            runner.state.current_scenario_index = 0
            runner.state.current_scenario = scenarios_to_run[0]
            runner.state.batch_start_time = datetime.now()
            runner.state.scenario_results = []
            
            runner.app = runner.create_application(scenarios_to_run[0])
            
            # Set web mode in configuration
            runner.app._config.web_mode = True
            # Set report flag in configuration if requested
            if request.report:
                setattr(runner.app._config, 'report', True)
            
            # Connect to CARLA server
            logger.info("Connecting to CARLA server...")
            if not runner.app.connection.connect():
                logger.error("Failed to connect to CARLA server")
                return {"success": False, "message": "Failed to connect to CARLA server"}
            
            try:
                # Setup components
                logger.info("Setting up simulation components...")
                components = runner.setup_components(runner.app)
                
                # Setup application
                logger.info("Setting up application...")
                runner.app.setup(
                    world_manager=components['world_manager'],
                    vehicle_controller=components['vehicle_controller'],
                    sensor_manager=components['sensor_manager'],
                    logger=runner.logger
                )
                
                # Start simulation in background
                logger.info("Starting simulation thread...")
                import threading
                def run_simulation():
                    try:
                        logger.info("Simulation loop started")
                        # Run all selected scenarios
                        total_scenarios = len(scenarios_to_run)
                        for i, scenario in enumerate(scenarios_to_run):
                            logger.info(f"================================")
                            logger.info(f"Running scenario {i+1}/{total_scenarios}: {scenario}")
                            logger.info(f"================================")
                            
                            if i > 0:  # Skip first scenario as it's already set up
                                runner.state.current_scenario = scenario
                                runner.state.current_scenario_index = i
                                runner.app._setup_scenario(scenario)
                            
                            # Run the scenario
                            runner.app.run()
                            
                            # Record result
                            if hasattr(runner.app, 'cleanup'):
                                completed, success = runner.app.cleanup()
                                result = "Passed" if success else "Failed"
                                if not completed:
                                    result = "Incomplete"
                            else:
                                result = "Completed"
                                
                            runner.state.scenario_results.append({
                                "name": scenario,
                                "result": result,
                                "duration": str(datetime.now() - runner.state.batch_start_time).split('.')[0]
                            })
                            
                    except Exception as e:
                        logger.error(f"Error in simulation thread: {str(e)}")
                        if hasattr(runner.app, 'state'):
                            runner.app.state.is_running = False
                        # Ensure cleanup happens on error
                        cleanup_resources()
                    finally:
                        # Always ensure cleanup happens
                        logger.info("Simulation loop ended, cleaning up...")
                        cleanup_resources()
                        # Update the frontend state
                        if hasattr(runner.app, 'state'):
                            runner.app.state.is_running = False
                        # Generate final report
                        if hasattr(runner.app, 'metrics'):
                            runner.app.metrics.generate_html_report(
                                runner.state.scenario_results,
                                runner.state.batch_start_time,
                                datetime.now()
                            )
                
                simulation_thread = threading.Thread(target=run_simulation)
                simulation_thread.daemon = True
                simulation_thread.start()
                
                logger.info("Simulation started successfully")
                return {
                    "success": True,
                    "message": "Simulation started successfully"
                }
            except Exception as e:
                logger.error(f"Error during simulation setup: {str(e)}")
                cleanup_resources()
                raise e
                
        except Exception as e:
            logger.error(f"Error creating application: {str(e)}")
            cleanup_resources()
            raise e
            
    except Exception as e:
        logger.error(f"Error in start_simulation: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the current simulation"""
    try:
        logger.info("Stopping simulation")
        cleanup_resources()
        logger.info("Simulation stopped successfully")
        return {"success": True, "message": "Simulation stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/simulation-view")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    try:
        while True:
            # Send status update
            is_running = False
            if hasattr(runner, 'app') and runner.app:
                is_running = runner.app.state.is_running if hasattr(runner.app, 'state') else False
            
            try:
                await websocket.send_json({
                    "type": "status",
                    "is_running": is_running
                })
                
                # Send video frame if available
                if hasattr(runner, 'app') and runner.app and runner.app.display_manager:
                    frame = runner.app.display_manager.get_current_frame()
                    if frame is not None:
                        # Convert frame to JPEG
                        _, buffer = cv2.imencode('.jpg', frame)
                        # Convert to base64
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        # Send to client
                        await websocket.send_text(frame_base64)
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error sending WebSocket data: {str(e)}")
                break
            
            await asyncio.sleep(0.033)  # ~30 FPS
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in websocket: {str(e)}")
    finally:
        logger.info("WebSocket connection closed")

@app.get("/api/reports")
async def list_reports():
    """List all HTML reports in the /reports directory."""
    try:
        reports_dir = project_root / "reports"
        logger.logger.info(f"Looking for reports in: {reports_dir.resolve()}")
        reports_dir.mkdir(exist_ok=True)
        reports = []
        for file in sorted(reports_dir.glob("*.html"), reverse=True):
            created = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            reports.append({"filename": file.name, "created": created})
        return {"reports": reports}
    except Exception as e:
        logger.logger.error(f"Error listing reports: {str(e)}")
        return {"reports": [], "error": str(e)}

@app.get("/api/reports/{filename}")
async def get_report(filename: str):
    """Serve a specific HTML report file."""
    try:
        reports_dir = project_root / "reports"
        file_path = reports_dir / filename
        if not file_path.exists() or not file_path.suffix == ".html":
            raise HTTPException(status_code=404, detail="Report not found")
        return FileResponse(str(file_path), media_type="text/html")
    except Exception as e:
        logger.error(f"Error serving report {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    reports_dir = project_root / "reports"
    file_path = reports_dir / filename
    if not file_path.exists() or not file_path.suffix == ".html":
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        file_path.unlink()
        return {"success": True, "message": "Report deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def list_logs():
    """List all log files in the /logs directory."""
    try:
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        logs = []
        for file in sorted(logs_dir.glob("*.log"), reverse=True):
            created = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            logs.append({"filename": file.name, "created": created})
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error listing logs: {str(e)}")
        return {"logs": [], "error": str(e)}

@app.get("/api/logs/{filename}")
async def get_log(filename: str):
    """Serve a specific log file."""
    try:
        logs_dir = project_root / "logs"
        file_path = logs_dir / filename
        if not file_path.exists() or not file_path.suffix == ".log":
            raise HTTPException(status_code=404, detail="Log not found")
        return FileResponse(str(file_path), media_type="text/plain")
    except Exception as e:
        logger.error(f"Error serving log {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/logs/{filename}")
async def delete_log(filename: str):
    logs_dir = project_root / "logs"
    file_path = logs_dir / filename
    if not file_path.exists() or not file_path.suffix == ".log":
        raise HTTPException(status_code=404, detail="Log not found")
    try:
        file_path.unlink()
        return {"success": True, "message": "Log deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
