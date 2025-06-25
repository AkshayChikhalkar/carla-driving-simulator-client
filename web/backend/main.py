import os

if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/xdg"
    if not os.path.exists("/tmp/xdg"):
        os.makedirs("/tmp/xdg", exist_ok=True)

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
import threading
from threading import Lock, Event
import queue
import time
import uuid  # Added import for UUID generation

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.config import Config, load_config, save_config
from src.visualization.display_manager import DisplayManager
from src.utils.logging import Logger
from src.utils.paths import get_project_root
from src.core.scenario_results_manager import ScenarioResultsManager


# Request/Response Models
class SimulationRequest(BaseModel):
    scenarios: List[str]
    debug: bool = False
    report: bool = False


class LogWriteRequest(BaseModel):
    content: str


class LogFileRequest(BaseModel):
    filename: str


class ConfigUpdate(BaseModel):
    config_data: dict


class LogDirectoryRequest(BaseModel):
    pass


# Thread-safe state management
class ThreadSafeState:
    def __init__(self):
        self._lock = Lock()
        self._state = {
            "is_running": False,
            "current_scenario": None,
            "scenarios_to_run": [],
            "current_scenario_index": 0,
            "scenario_results": ScenarioResultsManager(),
            "batch_start_time": None,
            "current_scenario_completed": False,
            "scenario_start_time": None,
            "cleanup_event": Event(),
            "cleanup_completed": False,
        }

    def __getitem__(self, key):
        with self._lock:
            return self._state[key]

    def __setitem__(self, key, value):
        with self._lock:
            self._state[key] = value

    def get_state(self):
        with self._lock:
            return self._state.copy()

    def set_state(self, new_state):
        with self._lock:
            self._state.update(new_state)


# Thread-safe queue for scenario transitions
scenario_queue = queue.Queue()


# Utility functions
async def wait_for_cleanup(app, max_wait_time=10, wait_interval=0.1):
    """Wait for cleanup to complete with timeout"""
    start_time = datetime.now()
    cleanup_started = False

    while True:
        try:
            # Check if cleanup has started
            if not cleanup_started and hasattr(app, "is_cleanup_complete"):
                cleanup_started = True
                logger.info("Waiting for cleanup to complete...")

            # Check cleanup status
            if hasattr(app, "is_cleanup_complete") and app.is_cleanup_complete:
                logger.info("Cleanup completed successfully")
                break
            else:
                # Check for timeout
                if (datetime.now() - start_time).total_seconds() > max_wait_time:
                    logger.warning("Cleanup wait timeout reached")
                    break
            await asyncio.sleep(wait_interval)
        except Exception as e:
            logger.error(f"Error during cleanup wait: {str(e)}")
            break

    # Additional verification and wait for CARLA to process cleanup
    if hasattr(app, "world_manager"):
        try:
            # Verify world is clean
            if hasattr(app.world_manager, "is_clean"):
                if not app.world_manager.is_clean:
                    logger.warning("World cleanup verification failed")
                    # Wait additional time for CARLA to process cleanup
                    # await asyncio.sleep(2)

            # Additional wait to ensure CARLA has time to remove actors
            # await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error verifying world cleanup: {str(e)}")


def cleanup_resources():
    """Clean up resources when shutting down"""
    try:
        logger.info("Cleaning up resources...")

        # Only clean up if we have an app instance
        if hasattr(runner, "app") and runner.app:
            try:
                # First, stop any running simulation
                if hasattr(runner.app, "state"):
                    runner.app.state.is_running = False

                # Get cleanup results first
                if hasattr(runner.app, "get_cleanup_results"):
                    completed, success = runner.app.get_cleanup_results()
                    # Only perform cleanup if results are not cached
                    if completed is None:
                        if hasattr(runner.app, "cleanup"):
                            # Perform general cleanup
                            runner.app.cleanup()
                else:
                    # Fallback to direct cleanup if get_cleanup_results is not available
                    if hasattr(runner.app, "cleanup"):
                        # Perform general cleanup
                        runner.app.cleanup()

            except Exception as e:
                logger.error(f"Error during app cleanup: {str(e)}")

        # Clear the app instance
        runner.app = None

        logger.info("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, lambda s, f: cleanup_resources())
signal.signal(signal.SIGTERM, lambda s, f: cleanup_resources())


def setup_simulation_components(runner, app, max_retries=3):
    """Setup simulation components and application with retry logic"""
    logger.info("Setting up simulation components...")

    for attempt in range(max_retries):
        try:
            components = runner.setup_components(app)

            logger.info("Setting up application...")
            app.setup(
                world_manager=components["world_manager"],
                vehicle_controller=components["vehicle_controller"],
                sensor_manager=components["sensor_manager"],
                logger=runner.logger,
            )
            return components
        except RuntimeError as e:
            if "Failed to create vehicle" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Vehicle spawn attempt {attempt + 1} failed, retrying..."
                    )
                    # Clean up before retry
                    cleanup_resources()
                    # Wait a bit before retrying
                    # time.sleep(2)
                else:
                    logger.error("All vehicle spawn attempts failed")
                    raise RuntimeError(
                        "Failed to create vehicle after multiple attempts"
                    )
            else:
                raise
        except Exception as e:
            logger.error(f"Error setting up components: {str(e)}")
            raise


def record_scenario_result(runner, scenario, result, status, duration):
    """Record scenario result with duration"""
    runner.state["scenario_results"].set_result(
        scenario, result, status, str(duration).split(".")[0]
    )


def generate_final_report(runner):
    """Generate final report if enabled"""
    if hasattr(runner.app, "metrics") and getattr(runner.app._config, "report", False):
        runner.app.metrics.generate_html_report(
            runner.state["scenario_results"].all_results(),
            runner.state["batch_start_time"],
            datetime.now(),
        )


def handle_file_operation(file_path, operation):
    """Handle file operations with error handling"""
    try:
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return operation(file_path)
    except Exception as e:
        logger.error(f"Error in file operation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def run_simulation_thread(runner, scenario):
    """Thread-safe simulation runner"""
    try:
        logger.info("Simulation loop started")
        runner.app.run()
    except Exception as e:
        logger.error(f"Error in simulation thread: {str(e)}")
        if hasattr(runner.app, "state"):
            runner.app.state.is_running = False
    finally:
        logger.info("Simulation loop ended")
        # No need to call cleanup_resources here as it's handled in run_single_scenario


def transition_to_next_scenario(runner, next_scenario):
    """Thread-safe scenario transition"""
    try:
        # Create new application instance
        new_app = runner.create_application(
            next_scenario, session_id=runner.state["session_id"]
        )
        new_app._config.web_mode = True

        # Connect to CARLA server
        logger.info("Connecting to CARLA server...")
        if not new_app.connection.connect():
            logger.error("Failed to connect to CARLA server")
            return False

        # Wait for connection to stabilize
        # time.sleep(1)

        # Setup components
        setup_simulation_components(runner, new_app)

        # Update runner state
        runner.state["current_scenario"] = next_scenario
        runner.state["current_scenario_index"] += 1
        runner.state["scenario_start_time"] = datetime.now()
        runner.app = new_app

        # Ensure is_running stays true during transition
        runner.state["is_running"] = True

        # Log transition completion
        logger.info(f"Successfully transitioned to scenario: {next_scenario}")

        return True
    except Exception as e:
        logger.error(f"Error during scenario transition: {str(e)}")
        return False


# Initialize FastAPI app and logger
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

# Use robust project root
project_root = get_project_root()

# Initialize simulation runner with thread-safe state
runner = SimulationRunner()
runner.state = ThreadSafeState()

# Web frontend log file handle
web_log_file = None


@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"message": "CARLA Simulator Backend is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available scenarios"""
    try:
        logger.info("Fetching available scenarios")
        # Ensure scenarios are registered
        ScenarioRegistry.register_all()
        scenarios = ScenarioRegistry.get_available_scenarios()
        logger.info(f"Found {len(scenarios)} scenarios: {scenarios}")
        return {"scenarios": scenarios}
    except Exception as e:
        logger.error(f"Error fetching scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(
                status_code=400, detail=f"Invalid configuration structure: {str(e)}"
            )

        # Save the configuration
        save_config(config_update.config_data, runner.config_file)

        # Reload the configuration
        runner.config = load_config(runner.config_file)

        logger.info("Configuration updated successfully")
        return {
            "message": "Configuration updated successfully",
            "config": runner.config,
        }
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
        if not runner.state["is_running"]:
            logger.warning("Attempted to skip scenario while simulation is not running")
            return {"success": False, "message": "Simulation is not running"}

        # Get current scenario index and total scenarios
        current_index = runner.state["current_scenario_index"]
        total_scenarios = len(runner.state["scenarios_to_run"])
        current_scenario = runner.state["current_scenario"]

        logger.info(
            f"Skipping scenario {current_index + 1}/{total_scenarios}: {current_scenario}"
        )

        # Record scenario result using utility function
        record_scenario_result(
            runner,
            current_scenario,
            "Failed",
            "Skipped",
            datetime.now() - runner.state["scenario_start_time"],
        )

        # If there are more scenarios, prepare for next one
        if current_index < total_scenarios - 1:
            next_scenario = runner.state["scenarios_to_run"][current_index + 1]
            logger.info("================================")
            logger.info(
                f"Starting scenario {current_index + 2}/{total_scenarios}: {next_scenario}"
            )
            logger.info("================================")

            # Stop current scenario but keep is_running true during transition
            if hasattr(runner.app, "state"):
                runner.app.state.is_running = False

            # Wait for cleanup using utility function with increased timeout
            await wait_for_cleanup(runner.app, max_wait_time=15)

            # Additional wait to ensure CARLA has time to process cleanup
            # await asyncio.sleep(2)

            # Transition to next scenario
            if transition_to_next_scenario(runner, next_scenario):
                # Start simulation in background
                logger.info("Starting simulation thread...")
                simulation_thread = threading.Thread(
                    target=run_simulation_thread,
                    args=(runner, next_scenario),
                    daemon=True,
                )
                simulation_thread.start()

                return {
                    "success": True,
                    "message": f"Skipped {current_scenario} ({current_index + 1}/{total_scenarios}). Running: {next_scenario}",
                    "current_scenario": current_scenario,
                    "next_scenario": next_scenario,
                    "scenario_index": current_index + 2,
                    "total_scenarios": total_scenarios,
                }
            else:
                # If transition fails, set is_running to false
                runner.state["is_running"] = False
                return {
                    "success": False,
                    "message": "Failed to transition to next scenario",
                }

        else:
            # This was the last scenario
            logger.info("================================")
            logger.info("Last scenario skipped. Simulation complete.")
            logger.info("================================")

            # Stop current scenario
            if hasattr(runner.app, "state"):
                runner.app.state.is_running = False

            # Wait for cleanup using utility function with increased timeout
            await wait_for_cleanup(runner.app, max_wait_time=15)

            # Generate final report using utility function
            generate_final_report(runner)

            # Set is_running to false only after everything is complete
            runner.state["is_running"] = False

            return {
                "success": True,
                "message": f"Skipped {current_scenario} ({current_index + 1}/{total_scenarios}). Simulation complete.",
                "current_scenario": current_scenario,
                "scenario_index": current_index + 1,
                "total_scenarios": total_scenarios,
            }

    except Exception as e:
        logger.error(f"Error skipping scenario: {str(e)}")
        # Ensure is_running is set to false on error
        runner.state["is_running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    """Start simulation with given parameters"""
    try:
        # Check if simulation is already running
        if runner.state["is_running"]:
            logger.warning("Attempted to start simulation while already running")
            return {"success": False, "message": "Simulation is already running"}

        logger.info(
            f"Starting simulation with scenarios: {request.scenarios}, debug: {request.debug}, report: {request.report}"
        )

        # Register scenarios first
        ScenarioRegistry.register_all()

        # Setup logger
        runner.setup_logger(request.debug)

        try:
            # Create and store the app instance
            logger.info("Creating application instance...")
            # If "all" is selected, use all available scenarios
            scenarios_to_run = (
                ScenarioRegistry.get_available_scenarios()
                if "all" in request.scenarios
                else request.scenarios
            )

            # Generate a new session_id for this simulation run (as UUID object)
            session_id = uuid.uuid4()

            # Update state atomically
            runner.state.set_state(
                {
                    "scenarios_to_run": scenarios_to_run,
                    "current_scenario_index": 0,
                    "current_scenario": scenarios_to_run[0],
                    "batch_start_time": datetime.now(),
                    "scenario_start_time": datetime.now(),
                    "is_running": True,
                    "session_id": session_id,
                }
            )
            runner.state["scenario_results"].clear_results()

            runner.app = runner.create_application(
                scenarios_to_run[0], session_id=session_id
            )

            # Set web mode in configuration
            runner.app._config.web_mode = True
            # Set report flag in configuration if requested
            if request.report:
                setattr(runner.app._config, "report", True)

            # Connect to CARLA server
            logger.info("Connecting to CARLA server...")
            if not runner.app.connection.connect():
                logger.error("Failed to connect to CARLA server")
                runner.state["is_running"] = False
                return {
                    "success": False,
                    "message": "Failed to connect to CARLA server",
                }

            # Setup components using utility function with retry logic
            try:
                setup_simulation_components(runner, runner.app)
            except RuntimeError as e:
                if "Failed to create vehicle" in str(e):
                    runner.state["is_running"] = False
                    return {
                        "success": False,
                        "message": "Failed to create vehicle after multiple attempts. Please try again.",
                    }
                raise

            # Start simulation in background
            logger.info("Starting simulation thread...")
            simulation_thread = threading.Thread(
                target=run_simulation_thread,
                args=(runner, scenarios_to_run[0]),
                daemon=True,
            )
            simulation_thread.start()

            logger.info("Simulation started successfully")
            return {
                "success": True,
                "message": "Simulation started successfully",
                "session_id": str(session_id),  # Return session_id as string to client
            }
        except Exception as e:
            logger.error(f"Error during simulation setup: {str(e)}")
            runner.state["is_running"] = False
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
        logger.info("================================")
        logger.info("Stopping simulation")
        logger.info("================================")

        if runner.state["is_running"]:
            current_scenario = runner.state["current_scenario"]
            record_scenario_result(
                runner,
                current_scenario,
                "Failed",
                "Stopped",
                datetime.now() - runner.state["scenario_start_time"],
            )

            # Reset cleanup flag
            if hasattr(runner.app, "is_cleanup_complete"):
                runner.app.is_cleanup_complete = False

            # Stop current scenario
            if hasattr(runner.app, "state"):
                runner.app.state.is_running = False

            # Wait for cleanup using utility function
            await wait_for_cleanup(runner.app)

            # Generate final report using utility function
            generate_final_report(runner)

        # Reset simulation state
        runner.state["is_running"] = False

        logger.info("Simulation stopped successfully")
        return {"success": True, "message": "Simulation stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping simulation: {str(e)}")
        # Reset simulation state on error
        runner.state["is_running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/simulation-view")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    try:
        while True:
            # Get comprehensive state information
            state_info = {
                "type": "status",
                "is_running": False,
                "current_scenario": None,
                "scenario_index": 0,
                "total_scenarios": 0,
                "is_transitioning": False,
            }

            # Update state information if runner exists
            if hasattr(runner, "state"):
                state_info.update(
                    {
                        "is_running": runner.state["is_running"],
                        "current_scenario": runner.state["current_scenario"],
                        "scenario_index": runner.state["current_scenario_index"] + 1,
                        "total_scenarios": len(runner.state["scenarios_to_run"]),
                        "is_transitioning": hasattr(runner, "app")
                        and runner.app
                        and hasattr(runner.app, "state")
                        and not runner.app.state.is_running
                        and runner.state["is_running"],
                    }
                )

            try:
                # Send state update
                await websocket.send_json(state_info)

                # Send video frame if available
                if hasattr(runner, "app") and runner.app and runner.app.display_manager:
                    frame = runner.app.display_manager.get_current_frame()
                    if frame is not None:
                        # Convert frame to JPEG
                        _, buffer = cv2.imencode(".jpg", frame)
                        # Convert to base64
                        frame_base64 = base64.b64encode(buffer).decode("utf-8")
                        # Send to client
                        await websocket.send_text(frame_base64)
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error sending WebSocket data: {str(e)}")
                break

            # await asyncio.sleep(0.033)  # ~30 FPS
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
            created = datetime.fromtimestamp(file.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
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
        return handle_file_operation(
            file_path, lambda p: FileResponse(str(p), media_type="text/html")
        )
    except Exception as e:
        logger.error(f"Error serving report {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{filename}")
async def delete_report(filename: str):
    """Delete a specific HTML report file."""
    reports_dir = project_root / "reports"
    file_path = reports_dir / filename
    return handle_file_operation(
        file_path,
        lambda p: (
            {"success": True, "message": "Report deleted"} if p.unlink() else None
        ),
    )


@app.get("/api/logs")
async def list_logs():
    """List all log files in the /logs directory."""
    try:
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        logs = []
        for file in sorted(logs_dir.glob("*.log"), reverse=True):
            created = datetime.fromtimestamp(file.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
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
        return handle_file_operation(
            file_path, lambda p: FileResponse(str(p), media_type="text/plain")
        )
    except Exception as e:
        logger.error(f"Error serving log {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/logs/{filename}")
async def delete_log(filename: str):
    """Delete a specific log file."""
    logs_dir = project_root / "logs"
    file_path = logs_dir / filename
    return handle_file_operation(
        file_path,
        lambda p: {"success": True, "message": "Log deleted"} if p.unlink() else None,
    )


@app.post("/api/logs/directory")
async def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    try:
        logs_dir = Path(get_project_root()) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return {"message": "Logs directory created/verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/file")
async def create_log_file(request: LogFileRequest):
    """Create a new log file"""
    try:
        logs_dir = Path(get_project_root()) / "logs"
        log_file = logs_dir / request.filename
        # Create file if it doesn't exist
        log_file.touch()
        return {"message": f"Log file {request.filename} created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/write")
async def write_to_log(request: LogWriteRequest):
    """Write content to the current log file"""
    try:
        logs_dir = Path(get_project_root()) / "logs"
        # Get the most recent log file
        log_files = sorted(logs_dir.glob("web_simulation_*.log"), reverse=True)
        if not log_files:
            raise HTTPException(status_code=404, detail="No log file found")
        
        current_log = log_files[0]
        with open(current_log, "a") as f:
            f.write(request.content)
        return {"message": "Log entry written"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/close")
async def close_log():
    """Close the current log file (no-op since files are closed after each write)"""
    return {"message": "Log file closed"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
