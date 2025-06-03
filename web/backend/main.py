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

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.config import load_config, save_config
from src.visualization.display_manager import DisplayManager

app = FastAPI()

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

# Add cleanup handler
def cleanup_resources():
    print("Cleaning up resources...")
    if hasattr(runner, 'app') and runner.app:
        try:
            # Stop the simulation
            if hasattr(runner.app, 'stop'):
                runner.app.stop()
            
            # Clean up resources
            if hasattr(runner.app, 'cleanup'):
                runner.app.cleanup()
            
            # Disconnect from CARLA server
            if hasattr(runner.app, 'connection') and runner.app.connection:
                runner.app.connection.disconnect()
            
            # Clear the app instance
            runner.app = None
            print("Cleanup completed successfully")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

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
    scenario: str
    debug: bool = False
    report: bool = False

class ConfigUpdate(BaseModel):
    config_data: dict

@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available scenarios"""
    ScenarioRegistry.register_all()
    return {"scenarios": ScenarioRegistry.get_available_scenarios()}

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return runner.config

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration"""
    try:
        save_config(config_update.config_data, runner.config_file)
        runner.config = load_config(runner.config_file)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    """Start simulation with given parameters"""
    try:
        # Check if simulation is already running
        if hasattr(runner, 'app') and runner.app and runner.app.state.is_running:
            return {"success": False, "message": "Simulation is already running"}
        
        print(f"Starting simulation with scenario: {request.scenario}")
        
        # Register scenarios first
        ScenarioRegistry.register_all()
        
        # Setup logger
        runner.setup_logger(request.debug)
        
        try:
            # Create and store the app instance
            print("Creating application instance...")
            runner.app = runner.create_application(request.scenario)
            
            # Set web mode in configuration
            runner.app._config.web_mode = True
            
            # Connect to CARLA server
            print("Connecting to CARLA server...")
            if not runner.app.connection.connect():
                return {"success": False, "message": "Failed to connect to CARLA server"}
            
            try:
                # Setup components
                print("Setting up simulation components...")
                components = runner.setup_components(runner.app)
                
                # Setup application
                print("Setting up application...")
                runner.app.setup(
                    world_manager=components['world_manager'],
                    vehicle_controller=components['vehicle_controller'],
                    sensor_manager=components['sensor_manager'],
                    logger=runner.logger
                )
                
                # Start simulation in background
                print("Starting simulation thread...")
                import threading
                def run_simulation():
                    try:
                        runner.app.run()
                    except Exception as e:
                        print(f"Error in simulation thread: {str(e)}")
                        runner.logger.error(f"Error in simulation: {str(e)}")
                        if hasattr(runner.app, 'state'):
                            runner.app.state.is_running = False
                        # Ensure cleanup happens on error
                        cleanup_resources()
                
                simulation_thread = threading.Thread(target=run_simulation)
                simulation_thread.daemon = True
                simulation_thread.start()
                
                return {
                    "success": True,
                    "message": "Simulation started successfully"
                }
            except Exception as e:
                print(f"Error during simulation setup: {str(e)}")
                cleanup_resources()
                raise e
                
        except Exception as e:
            print(f"Error creating application: {str(e)}")
            cleanup_resources()
            raise e
            
    except Exception as e:
        print(f"Error in start_simulation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the current simulation"""
    try:
        cleanup_resources()
        return {"success": True, "message": "Simulation stopped successfully"}
    except Exception as e:
        print(f"Error stopping simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/simulation-view")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
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
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Error sending WebSocket data: {str(e)}")
                break
            
            await asyncio.sleep(0.033)  # ~30 FPS
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error in websocket: {str(e)}")
    finally:
        print("WebSocket connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 