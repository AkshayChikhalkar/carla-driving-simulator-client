import os
import logging
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/xdg"
    if not os.path.exists("/tmp/xdg"):
        os.makedirs("/tmp/xdg", exist_ok=True)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from pathlib import Path
import base64
import cv2
import numpy as np
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import yaml
import threading
from threading import Lock, Event
import queue
import time
import uuid
import atexit
import signal
from fastapi.responses import FileResponse

# Add monitoring imports
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, Info
import prometheus_client

app = FastAPI()

# Serve React production build
from fastapi.staticfiles import StaticFiles
import os

frontend_build_dir = os.path.join(os.path.dirname(__file__), "../../web/frontend/build")

# Custom middleware to handle React routing
@app.middleware("http")
async def react_routing_middleware(request: Request, call_next):
    # Let API routes pass through
    if request.url.path.startswith("/api/") or request.url.path.startswith("/health") or request.url.path.startswith("/metrics"):
        return await call_next(request)
    
    # Check if the request is for a static file (CSS, JS, images)
    if os.path.exists(frontend_build_dir):
        static_file_path = os.path.join(frontend_build_dir, request.url.path.lstrip("/"))
        if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
            return FileResponse(static_file_path)
    
    # For all other routes, serve the React app
    if os.path.exists(frontend_build_dir):
        index_path = os.path.join(frontend_build_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
    
    # If React build doesn't exist, continue with normal processing
    return await call_next(request)

# Remove the StaticFiles mount since we're handling it in middleware
# if os.path.exists(frontend_build_dir):
#     app.mount("/", StaticFiles(directory=frontend_build_dir, html=False), name="static")

# Prometheus metrics
# Counters
SIMULATION_START_COUNTER = Counter('carla_simulation_starts_total', 'Total number of simulation starts')
SIMULATION_STOP_COUNTER = Counter('carla_simulation_stops_total', 'Total number of simulation stops')
SIMULATION_SKIP_COUNTER = Counter('carla_simulation_skips_total', 'Total number of scenario skips')
WEBSOCKET_CONNECTIONS_COUNTER = Counter('carla_websocket_connections_total', 'Total number of WebSocket connections')
API_REQUESTS_COUNTER = Counter('carla_api_requests_total', 'Total number of API requests', ['endpoint', 'method'])

# Histograms
SIMULATION_DURATION_HISTOGRAM = Histogram('carla_simulation_duration_seconds', 'Simulation duration in seconds')
API_REQUEST_DURATION_HISTOGRAM = Histogram('carla_api_request_duration_seconds', 'API request duration in seconds', ['endpoint'])

# Gauges
SIMULATION_STATUS_GAUGE = Gauge('carla_simulation_status', 'Current simulation status (0=stopped, 1=running, 2=paused)')
ACTIVE_WEBSOCKET_CONNECTIONS_GAUGE = Gauge('carla_active_websocket_connections', 'Number of active WebSocket connections')
SCENARIO_PROGRESS_GAUGE = Gauge('carla_scenario_progress', 'Current scenario progress (0-100)')

# Info
APP_INFO = Info('carla_app', 'Application information')

# Middleware for tracking API requests
@app.middleware("http")
async def track_api_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract endpoint and method
    endpoint = request.url.path
    method = request.method
    
    # Increment request counter
    API_REQUESTS_COUNTER.labels(endpoint=endpoint, method=method).inc()
    
    # Process request
    response = await call_next(request)
    
    # Record request duration
    duration = time.time() - start_time
    API_REQUEST_DURATION_HISTOGRAM.labels(endpoint=endpoint).observe(duration)
    
    return response

# Custom logging filter to suppress WebSocket connection messages
class WebSocketConnectionFilter(logging.Filter):
    def filter(self, record):
        # Suppress "connection closed" messages
        if "connection closed" in record.getMessage().lower():
            return False
        return True

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from carla_simulator.core.simulation_runner import SimulationRunner
from carla_simulator.scenarios.scenario_registry import ScenarioRegistry
from carla_simulator.utils.config import Config, load_config, save_config
from carla_simulator.visualization.display_manager import DisplayManager
from carla_simulator.utils.logging import Logger
from carla_simulator.utils.paths import get_project_root
from carla_simulator.core.scenario_results_manager import ScenarioResultsManager
from carla_simulator.database.db_manager import DatabaseManager
from carla_simulator.database.models import User, UserSession, TenantConfig, SimulationReport
from carla_simulator.utils.auth import (
    LoginRequest, RegisterRequest, UserResponse,
    hash_password, verify_password, generate_session_token,
    create_jwt_token, verify_jwt_token, validate_password,
    validate_email, validate_username, get_current_user, require_admin
)


# Request/Response Models
class SimulationRequest(BaseModel):
    scenarios: List[str]
    debug: bool = False
    report: bool = False
    tenant_id: Optional[int] = None


class LogWriteRequest(BaseModel):
    content: str


class FrontendLogRequest(BaseModel):
    message: str
    data: Optional[dict] = None
    timestamp: str
    component: str


class LogFileRequest(BaseModel):
    filename: str


class ConfigUpdate(BaseModel):
    config_data: dict


class ResetConfigRequest(BaseModel):
    tenant_id: Optional[int] = None


class LogDirectoryRequest(BaseModel):
    pass


# Thread-safe state management
class ThreadSafeState:
    def __init__(self):
        self._lock = Lock()
        self._state = {
            "is_running": False,
            "is_starting": False,  # New flag for starting state
            "is_stopping": False,  # Explicit flag for stopping state
            "is_skipping": False,  # New flag for skipping state
            "current_scenario": None,
            "scenarios_to_run": [],
            "current_scenario_index": 0,
            "scenario_results": ScenarioResultsManager(),
            "batch_start_time": None,
            "current_scenario_completed": False,
            "scenario_start_time": None,
            "cleanup_event": Event(),
            "cleanup_completed": False,
            "is_transitioning": False,  # Flag to track scenario transitions
            "last_state_update": datetime.now(),  # Track when state was last updated
            "setup_complete": False,  # Flag to track if setup is complete
        }

    def __getitem__(self, key):
        with self._lock:
            return self._state[key]

    def __setitem__(self, key, value):
        with self._lock:
            self._state[key] = value
            self._state["last_state_update"] = datetime.now()

    def get(self, key, default=None):
        """Get a value with a default if key doesn't exist"""
        with self._lock:
            return self._state.get(key, default)

    def get_state(self):
        with self._lock:
            return self._state.copy()

    def set_state(self, new_state):
        with self._lock:
            self._state.update(new_state)
            self._state["last_state_update"] = datetime.now()

    def is_consistent(self):
        """Check if the state is consistent between runner and app"""
        with self._lock:
            if not hasattr(runner, "app") or runner.app is None:
                return True
            
            # Check if app state exists and is consistent
            if hasattr(runner.app, "state"):
                app_running = runner.app.state.is_running
                runner_running = self._state["is_running"]
                return app_running == runner_running
            
            return True

    def force_sync(self):
        """Force synchronization between runner and app state"""
        with self._lock:
            if hasattr(runner, "app") and runner.app and hasattr(runner.app, "state"):
                # Sync app state to runner state
                self._state["is_running"] = runner.app.state.is_running
                self._state["last_state_update"] = datetime.now()


# Thread-safe queue for scenario transitions
scenario_queue = queue.Queue()

# Thread synchronization primitives
setup_event = Event()  # Signals when setup is complete
simulation_ready = Event()  # Signals when simulation thread is ready


# Utility functions
async def wait_for_cleanup(app, max_wait_time=15, wait_interval=0.1):
    """Wait for cleanup to complete with improved timeout and error handling"""
    start_time = datetime.now()
    cleanup_started = False
    last_progress_time = start_time

    logger.debug(f"Starting cleanup wait with timeout: {max_wait_time}s")

    while True:
        try:
            current_time = datetime.now()
            elapsed_time = (current_time - start_time).total_seconds()

            # Check if cleanup has started
            if not cleanup_started and hasattr(app, "is_cleanup_complete"):
                cleanup_started = True
                logger.debug("Cleanup process detected, waiting for completion...")

            # Check cleanup status
            if hasattr(app, "is_cleanup_complete") and app.is_cleanup_complete:
                logger.debug("Cleanup completed successfully")
                break
            
            # Check for timeout
            if elapsed_time > max_wait_time:
                logger.warning(f"Cleanup wait timeout reached after {elapsed_time:.1f}s")
                break

            # Log progress every 5 seconds to reduce spam
            if (current_time - last_progress_time).total_seconds() > 5:
                logger.debug(f"Still waiting for cleanup... ({elapsed_time:.1f}s elapsed)")
                last_progress_time = current_time

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
                    await asyncio.sleep(1)

            # Additional wait to ensure CARLA has time to remove actors
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error verifying world cleanup: {str(e)}")

    logger.debug("Cleanup wait process completed")


def cleanup_resources():
    """Clean up resources when shutting down"""
    try:
        logger.debug("Cleaning up resources...")

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

        logger.debug("Cleanup completed successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGINT, lambda s, f: cleanup_resources())
signal.signal(signal.SIGTERM, lambda s, f: cleanup_resources())


def setup_simulation_components(runner, app, max_retries=3):
    """Setup simulation components and application with retry logic"""

    for attempt in range(max_retries):
        try:
            components = runner.setup_components(app)

            logger.debug("Setting up application...")
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
    if not hasattr(runner, "app") or runner.app is None:
        return
    results = runner.state["scenario_results"].all_results() if runner.state else []
    # Only generate when explicitly requested and we actually have results
    if getattr(runner.app._config, "report", False) and results:
        runner.app.metrics.generate_html_report(results, runner.state["batch_start_time"], datetime.now())


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
    """Thread-safe simulation runner with proper synchronization"""
    global setup_event, simulation_ready
    
    try:
        logger.debug("Simulation thread started, waiting for setup completion...")
        
        # Signal that simulation thread is ready
        simulation_ready.set()
        
        # Wait for setup to complete before starting simulation
        if setup_event.wait(timeout=600):  # 120 second timeout (2 minutes)
            logger.debug("Setup completed, starting simulation loop")
        else:
            logger.error("Setup timeout - simulation thread exiting")
            return
        
        # Mark setup as complete
        runner.state["setup_complete"] = True
        
        # Clear the starting flag now that simulation is actually running
        runner.state["is_starting"] = False
        logger.debug("Cleared is_starting flag - simulation is now running")
        logger.debug(f"State after clearing is_starting: is_running={runner.state['is_running']}, is_starting={runner.state['is_starting']}, is_transitioning={runner.state['is_transitioning']}")
        
        logger.debug("Simulation loop started")
        
        try:
            # Start the simulation
            runner.app.run()
            logger.debug("Simulation app.run() completed normally")
        except Exception as e:
            logger.error(f"Exception in runner.app.run(): {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    except Exception as e:
        logger.error(f"Error in simulation thread: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update state to reflect error
        if hasattr(runner, "state"):
            runner.state["is_running"] = False
            runner.state["is_transitioning"] = False
            runner.state["is_starting"] = False  # Clear starting flag on error
            runner.state["error"] = str(e)
        
        if hasattr(runner, "app") and runner.app and hasattr(runner.app, "state"):
            runner.app.state.is_running = False
    finally:
        logger.debug("Simulation thread ending")
        # Reset setup complete flag
        runner.state["setup_complete"] = False
        # Clear starting flag when thread ends
        if hasattr(runner, "state"):
            runner.state["is_starting"] = False


def transition_to_next_scenario(runner, next_scenario):
    """Thread-safe scenario transition"""
    try:
        # Create new application instance
        new_app = runner.create_application(
            next_scenario, session_id=runner.state["session_id"]
        )
        new_app._config.web_mode = True

        # Connect to CARLA server
        logger.debug("Connecting to CARLA server...")
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


# --- Global exception handler to prevent container crash ---
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_uncaught_exception


# Remove the custom root and catch-all routes since StaticFiles will handle them
# @app.get("/")
# async def root():
#     """Serve React app index.html for root and non-API routes"""
#     if os.path.exists(frontend_build_dir):
#         index_path = os.path.join(frontend_build_dir, "index.html")
#         if os.path.exists(index_path):
#             return FileResponse(index_path, media_type="text/html")
#     
#     # Fallback if React build doesn't exist
#     return {"message": "CARLA Simulator Backend is running", "status": "healthy"}

# # Catch-all route for React client-side routing
# @app.get("/{full_path:path}")
# async def catch_all(full_path: str):
#     """Serve React app for all non-API routes to support client-side routing"""
#     # Don't serve React app for API routes
#     if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("metrics"):
#         raise HTTPException(status_code=404, detail="Not found")
#     
#     # Serve React app for all other routes
#     if os.path.exists(frontend_build_dir):
#         index_path = os.path.join(frontend_build_dir, "index.html")
#         if os.path.exists(index_path):
#             return FileResponse(index_path, media_type="text/html")
#     
#     raise HTTPException(status_code=404, detail="Not found")


@app.get("/health")
async def health_check():
    """Health check endpoint - always returns 200 if process is alive"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update app info
        APP_INFO.info({
            'version': os.getenv("VERSION", "dev"),
            'build_time': os.getenv("BUILD_TIME", datetime.now().isoformat()),
            'docker_image_tag': os.getenv("DOCKER_IMAGE_TAG", "latest")
        })
        
        # Update simulation status gauge with proper error handling
        try:
            if runner.state["is_running"]:
                SIMULATION_STATUS_GAUGE.set(1)  # Running
            elif runner.state.get("is_paused", False):
                SIMULATION_STATUS_GAUGE.set(2)  # Paused
            else:
                SIMULATION_STATUS_GAUGE.set(0)  # Stopped
        except Exception as e:
            logger.error(f"Error updating simulation status gauge: {str(e)}")
            SIMULATION_STATUS_GAUGE.set(0)  # Default to stopped on error
        
        # Update scenario progress gauge with proper error handling
        try:
            scenarios_to_run = runner.state.get("scenarios_to_run", [])
            if scenarios_to_run:
                total_scenarios = len(scenarios_to_run)
                current_index = runner.state.get("current_scenario_index", 0)
                if total_scenarios > 0:
                    progress = (current_index / total_scenarios) * 100
                    SCENARIO_PROGRESS_GAUGE.set(progress)
                else:
                    SCENARIO_PROGRESS_GAUGE.set(0)
            else:
                SCENARIO_PROGRESS_GAUGE.set(0)
        except Exception as e:
            logger.error(f"Error updating scenario progress gauge: {str(e)}")
            SCENARIO_PROGRESS_GAUGE.set(0)  # Default to 0 on error
        
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
    except Exception as e:
        logger.error(f"Error in metrics endpoint: {str(e)}")
        # Return basic metrics even on error to prevent 500
        try:
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except Exception as inner_e:
            logger.error(f"Error generating metrics: {str(inner_e)}")
            # Return minimal metrics to prevent complete failure
            minimal_metrics = "# HELP carla_app_info Application information\n# TYPE carla_app_info gauge\ncarla_app_info{version=\"error\"} 1\n"
            return Response(minimal_metrics, media_type=CONTENT_TYPE_LATEST)


# Remove duplicate version endpoint - keeping the one at the end of the file


@app.get("/api/scenarios")
async def get_scenarios():
    """Get list of available scenarios"""
    try:
        logger.debug("Fetching available scenarios")
        # Ensure scenarios are registered
        ScenarioRegistry.register_all()
        scenarios = ScenarioRegistry.get_available_scenarios()
        logger.debug(f"Found {len(scenarios)} scenarios: {scenarios}")
        return {"scenarios": scenarios}
    except Exception as e:
        logger.error(f"Error fetching scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config(tenant_id: Optional[int] = None):
    """Get current configuration. If tenant_id provided, return DB-backed active config."""
    try:
        # Resolve effective tenant id: query param overrides env
        effective_tenant_id: Optional[int] = None
        if tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        if effective_tenant_id is not None:
            dbm = DatabaseManager()
            cfg = TenantConfig.get_active_config(dbm, effective_tenant_id)
            if cfg:
                return cfg
        # fallback to current loaded YAML config
        logger.debug("Fetching current configuration from YAML fallback")
        return runner.config if isinstance(runner.config, dict) else {}
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config")
async def update_config(config_update: ConfigUpdate, tenant_id: Optional[int] = None):
    """Update configuration"""
    try:
        logger.debug("Updating configuration")

        # Validate the config data
        if not isinstance(config_update.config_data, dict):
            raise HTTPException(status_code=400, detail="Invalid configuration format")

        # Best-effort validation: use current loader to check required sections
        # but do not force dataclass construction here (save path can be YAML)
        if not isinstance(config_update.config_data, dict):
            raise HTTPException(status_code=400, detail="Invalid configuration format")

        # Resolve effective tenant id: query param overrides env
        effective_tenant_id: Optional[int] = None
        if tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        if effective_tenant_id is not None:
            # Store config in DB for tenant and return
            dbm = DatabaseManager()
            result = TenantConfig.upsert_active_config(dbm, effective_tenant_id, config_update.config_data)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to store tenant config")
            return {"message": "Tenant configuration updated", "tenant_id": effective_tenant_id, "version": result["version"], "config": config_update.config_data}
        else:
            # Save to YAML fallback
            # Write raw dict to YAML to preserve structure
            try:
                with open(runner.config_file, "w", encoding="utf-8") as f:
                    yaml.safe_dump(config_update.config_data, f, sort_keys=False)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed writing YAML: {str(e)}")
            # Immediately reflect saved YAML in in-memory config without DB override
            runner.config = config_update.config_data

        logger.debug("Configuration updated successfully")
        return {
            "message": "Configuration updated successfully",
                # Return the dict we just wrote (frontend expects plain JSON)
                "config": config_update.config_data,
                "source": "db" if effective_tenant_id is not None else "fs",
        }
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/skip")
async def skip_scenario():
    """Skip the current scenario and move to the next one with improved reliability"""
    try:
        # Check if simulation is running
        if not runner.state["is_running"]:
            logger.warning("Attempted to skip scenario while simulation is not running")
            return {"success": False, "message": "Simulation is not running"}

        # Check if we're already transitioning
        if runner.state["is_transitioning"]:
            logger.warning("Attempted to skip scenario while transition is in progress")
            return {"success": False, "message": "Scenario transition already in progress"}
        
        # Set skipping flag for immediate UX feedback
        runner.state["is_skipping"] = True
        
        # Track metrics
        SIMULATION_SKIP_COUNTER.inc()
        
        # Only set is_transitioning for actual scenario transitions
        current_index = runner.state["current_scenario_index"]
        total_scenarios = len(runner.state["scenarios_to_run"])
        if current_index < total_scenarios - 1:
            runner.state["is_transitioning"] = True
        try:
            current_scenario = runner.state["current_scenario"]
            if current_scenario:
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
                    logger.debug("Set app.state.is_running = False for transition")

                # Wait for cleanup using utility function with increased timeout
                logger.debug("Waiting for cleanup before scenario transition...")
                await wait_for_cleanup(runner.app, max_wait_time=20)

                # Transition to next scenario
                if transition_to_next_scenario(runner, next_scenario):
                    # Start simulation in background
                    logger.debug("Starting simulation thread...")
                    simulation_thread = threading.Thread(
                        target=run_simulation_thread,
                        args=(runner, next_scenario),
                        daemon=True,
                    )
                    simulation_thread.start()

                    # Reset transition flag
                    runner.state["is_transitioning"] = False
                    runner.state["is_skipping"] = False  # Clear skipping flag after successful skip

                    return {
                        "success": True,
                        "message": f"Skipped {current_scenario} ({current_index + 1}/{total_scenarios}). Running: {next_scenario}",
                        "current_scenario": current_scenario,
                        "next_scenario": next_scenario,
                        "scenario_index": current_index + 2,
                        "total_scenarios": total_scenarios,
                    }
                else:
                    runner.state["is_running"] = False
                    runner.state["is_transitioning"] = False
                    return {
                        "success": False,
                        "message": "Failed to transition to next scenario",
                    }
            else:
                # This was the last scenario - call stop_simulation to handle cleanup
                logger.info("================================")
                logger.info("Last scenario skipped. Simulation complete.")
                logger.info("================================")

                # Call stop_simulation to handle the cleanup properly
                stop_result = await stop_simulation()
                return {
                    "success": True,
                    "message": f"Skipped {current_scenario} ({current_index + 1}/{total_scenarios}). Simulation complete.",
                    "current_scenario": current_scenario,
                    "scenario_index": current_index + 1,
                    "total_scenarios": total_scenarios,
                }

        except Exception as e:
            logger.error(f"Error during scenario skip process: {str(e)}")
            # Reset state on error
            runner.state["is_running"] = False
            runner.state["is_stopping"] = False  # Reset stopping flag on error
            runner.state["is_transitioning"] = False
            runner.state["is_skipping"] = False  # Reset skipping flag on error
            raise

    except Exception as e:
        logger.error(f"Error skipping scenario: {str(e)}")
        # Ensure is_running is set to false on error
        runner.state["is_running"] = False
        runner.state["is_stopping"] = False  # Reset stopping flag on error
        runner.state["is_transitioning"] = False
        runner.state["is_skipping"] = False  # Reset skipping flag on error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest):
    """Start simulation with given parameters"""
    global setup_event, simulation_ready
    
    try:
        # Check if simulation is already running
        if runner.state["is_running"]:
            logger.warning("Attempted to start simulation while already running")
            return {"success": False, "message": "Simulation is already running"}

        # Check if we're already transitioning
        if runner.state["is_transitioning"]:
            logger.warning("Attempted to start simulation while transition is in progress")
            return {"success": False, "message": "Simulation transition already in progress"}

        # Set transition flag to prevent race conditions
        runner.state["is_transitioning"] = True
        runner.state["is_starting"] = True  # Set starting flag for immediate UX feedback
        logger.info(f"State is_starting: {runner.state['is_starting']}")
        logger.info(
            f"Starting simulation with scenarios: {request.scenarios}, debug: {request.debug}, report: {request.report}"
        )

        # Reset synchronization events
        setup_event.clear()
        simulation_ready.clear()

        # Register scenarios first
        ScenarioRegistry.register_all()

        # Setup logger
        runner.setup_logger(request.debug)

        try:
            # Create and store the app instance
            logger.debug("Creating application instance...")
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
                    "is_stopping": False,  # Reset stopping flag when starting
                    "session_id": session_id,
                    "setup_complete": False,  # Reset setup flag
                }
            )
            logger.debug(f"Updated state: is_running=True, is_starting={runner.state['is_starting']}, is_transitioning={runner.state['is_transitioning']}")
            runner.state["scenario_results"].clear_results()

            # If tenant_id provided, set env for config loader to fetch DB config BEFORE app creation
            if request.tenant_id is not None:
                os.environ["CONFIG_TENANT_ID"] = str(request.tenant_id)

            runner.app = runner.create_application(
                scenarios_to_run[0], session_id=session_id
            )

            # Set web mode in configuration
            runner.app._config.web_mode = True
            # Set report flag in configuration if requested
            if request.report:
                setattr(runner.app._config, "report", True)

            # Connect to CARLA server
            logger.debug("Connecting to CARLA server...")
            if not runner.app.connection.connect():
                logger.error("Failed to connect to CARLA server")
                runner.state["is_running"] = False
                runner.state["is_transitioning"] = False
                return {
                    "success": False,
                    "message": "Failed to connect to CARLA server",
                }

            # Start simulation thread FIRST (it will wait for setup completion)
            logger.debug("Starting simulation thread (will wait for setup completion)...")
            simulation_thread = threading.Thread(
                target=run_simulation_thread,
                args=(runner, scenarios_to_run[0]),
                daemon=True,
            )
            simulation_thread.start()

            # Wait for simulation thread to be ready
            if not simulation_ready.wait(timeout=10):
                logger.error("Simulation thread failed to start within timeout")
                runner.state["is_running"] = False
                runner.state["is_transitioning"] = False
                return {
                    "success": False,
                    "message": "Simulation thread failed to start",
                }

            # Setup components using utility function with retry logic
            try:
                setup_simulation_components(runner, runner.app)
                logger.debug("Simulation components setup completed")
            except RuntimeError as e:
                if "Failed to create vehicle" in str(e):
                    runner.state["is_running"] = False
                    runner.state["is_transitioning"] = False
                    # Return HTTP 500 error instead of 200 OK
                    raise HTTPException(status_code=500, detail="Failed to create vehicle after multiple attempts. Please try again.")
                raise

            # Wait a moment to ensure all setup is stable
            logger.debug("Waiting for setup to stabilize...")
            time.sleep(0.5)

            # Signal that setup is complete - simulation thread can now start
            logger.debug("Signaling setup completion to simulation thread...")
            setup_event.set()

            # Reset transition flag after successful start
            runner.state["is_transitioning"] = False
            # Don't clear is_starting flag here - let the simulation thread clear it when actually running

            logger.debug(f"Reset is_transitioning=False, is_starting={runner.state['is_starting']}")
            logger.info("Simulation started successfully")
            
            # Track metrics
            SIMULATION_START_COUNTER.inc()
            SIMULATION_STATUS_GAUGE.set(1)  # Running
            
            return {
                "success": True,
                "message": "Simulation started successfully",
                "session_id": str(session_id),  # Return session_id as string to client
            }
        except Exception as e:
            logger.error(f"Error during simulation setup: {str(e)}")
            runner.state["is_running"] = False
            runner.state["is_stopping"] = False  # Reset stopping flag on error
            runner.state["is_transitioning"] = False
            runner.state["is_starting"] = False  # Clear starting flag on error
            cleanup_resources()
            raise e

    except Exception as e:
        logger.error(f"Error in start_simulation: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        # Reset state on error
        runner.state["is_running"] = False
        runner.state["is_stopping"] = False  # Reset stopping flag on error
        runner.state["is_transitioning"] = False
        runner.state["is_starting"] = False  # Clear starting flag on error
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop the current simulation with improved reliability"""
    try:
        logger.info("================================")
        logger.info("Stopping simulation")
        logger.info("================================")
        
        # Track metrics
        SIMULATION_STOP_COUNTER.inc()
        SIMULATION_STATUS_GAUGE.set(0)  # Stopped

        # Check if simulation is actually running
        if not runner.state["is_running"]:
            logger.debug("Simulation is not running, returning success")
            return {"success": True, "message": "Simulation is not running"}
        
        # Synchronize the two state objects immediately
        runner.state["is_running"] = False      # tell WebSocket on next tick
        runner.state["is_stopping"] = True      # new explicit flag

        if hasattr(runner, "app") and runner.app:
            runner.app.state.is_running = False  # halt frame producer
        try:
            current_scenario = runner.state["current_scenario"]
            
            # Record scenario result
            if current_scenario:
                record_scenario_result(
                    runner,
                    current_scenario,
                    "Failed",
                    "Stopped",
                    datetime.now() - runner.state["scenario_start_time"],
                )

            # Stop the simulation application first
            if hasattr(runner, "app") and runner.app:
                try:
                    if hasattr(runner.app, "is_cleanup_complete"):
                        runner.app.is_cleanup_complete = False
                    if hasattr(runner.app, "state"):
                        runner.app.state.is_running = False
                    await wait_for_cleanup(runner.app, max_wait_time=20)
                except Exception as e:
                    logger.error(f"Error during app cleanup: {str(e)}")
            generate_final_report(runner)
        except Exception as e:
            logger.error(f"Error during simulation stop process: {str(e)}")
            # Continue with cleanup even if there's an error

        finally:
            # Always reset simulation state
            runner.state["is_running"] = False
            runner.state["is_stopping"] = False  # Reset stopping flag
            runner.state["is_transitioning"] = False
            runner.state["is_skipping"] = False  # Reset skipping flag
            runner.state["current_scenario"] = None
            runner.state["current_scenario_index"] = 0
            runner.state["scenarios_to_run"] = []
            
            # Clear the app instance
            runner.app = None
            
            logger.debug("Simulation state reset completed")

        logger.info("Simulation stopped")
        return {"success": True, "message": "Simulation stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error stopping simulation: {str(e)}")
        # Ensure state is reset on error
        runner.state["is_running"] = False
        runner.state["is_stopping"] = False  # Reset stopping flag on error
        runner.state["is_transitioning"] = False
        runner.state["is_skipping"] = False  # Reset skipping flag on error
        raise HTTPException(status_code=500, detail=str(e))


# --- OPTIMIZATION: WebSocket video frame sending, only send if frame is new ---
@app.websocket("/ws/simulation-view")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        
        # Track metrics
        WEBSOCKET_CONNECTIONS_COUNTER.inc()
        ACTIVE_WEBSOCKET_CONNECTIONS_GAUGE.inc()
        logger.debug("WebSocket connection established")
        last_sent_state = None
        last_frame_hash = [None]
        async def send_video_frames():
            while True:
                try:
                    state = runner.state if hasattr(runner, 'state') else None
                    app = runner.app if hasattr(runner, 'app') else None
                    if (app and getattr(app, 'display_manager', None) and state and
                        state["is_running"] and not state["is_transitioning"] and
                        not state["is_stopping"] and not state["is_skipping"] and not state["is_starting"]):
                        frame = app.display_manager.get_current_frame()
                        if frame is not None:
                            frame_bytes = frame.tobytes()
                            frame_hash = hash(frame_bytes)
                            if frame_hash != last_frame_hash[0]:
                                _, buffer = cv2.imencode('.jpg', frame)
                                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                try:
                                    await websocket.send_text(frame_base64)
                                    last_frame_hash[0] = frame_hash
                                except asyncio.CancelledError:
                                    break
                                except Exception as e:
                                    error_str = str(e).lower()
                                    if any(pattern in error_str for pattern in [
                                        "1001", "1005", "1006", "1011", "1012",
                                        "going away", "no status code", "no close frame received or sent",
                                        "connection closed", "connection reset", "connection aborted",
                                        "connection refused", "connection timed out", "broken pipe",
                                        "websocket is closed", "websocket connection is closed",
                                        "remote end closed connection", "connection lost",
                                        "peer closed connection", "socket is not connected"
                                    ]):
                                        break
                                    else:
                                        logger.error(f"Error sending video frame: {str(e)}")
                                        break
                    await asyncio.sleep(0.0167)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.critical(f"Uncaught exception in send_video_frames: {e}", exc_info=True)
                    break
        video_task = asyncio.create_task(send_video_frames())
        try:
            while True:
                state = runner.state if hasattr(runner, 'state') else None
                state_info = {
                    "type": "status",
                    "is_running": False,
                    "is_starting": False,
                    "is_stopping": False,
                    "is_skipping": False,
                    "current_scenario": None,
                    "scenario_index": 0,
                    "total_scenarios": 0,
                    "is_transitioning": False,
                    "status_message": "Ready to Start",
                    "timestamp": datetime.now().isoformat(),
                }
                if state:
                    try:
                        status_message = "Ready to Start"
                        if state["is_starting"]:
                            status_message = "Hang on,\nLoading Simulation..."
                        elif state["is_stopping"]:
                            status_message = "Stopping simulation..."
                        elif state["is_skipping"]:
                            current_index = state["current_scenario_index"]
                            total_scenarios = len(state["scenarios_to_run"])
                            if current_index >= total_scenarios - 1:
                                status_message = "Stopping simulation..."
                            else:
                                status_message = "Skipping scenario..."
                        elif state["is_running"]:
                            if state["is_transitioning"]:
                                status_message = "Transitioning between scenarios..."
                            else:
                                status_message = "Simulation running"
                        state_info.update({
                            "is_running": state["is_running"],
                            "is_starting": state["is_starting"],
                            "is_stopping": state["is_stopping"],
                            "is_skipping": state["is_skipping"],
                            "current_scenario": state["current_scenario"],
                            "scenario_index": state["current_scenario_index"] + 1,
                            "total_scenarios": len(state["scenarios_to_run"]),
                            "is_transitioning": state["is_transitioning"],
                            "status_message": status_message,
                        })
                        current_state_key = (
                            state_info["is_running"],
                            state_info["is_starting"],
                            state_info["is_stopping"],
                            state_info["is_skipping"],
                            state_info["is_transitioning"],
                            state_info["status_message"],
                            state_info["current_scenario"],
                            state_info["scenario_index"],
                            state_info["total_scenarios"]
                        )
                        if last_sent_state != current_state_key:
                            try:
                                await websocket.send_json(state_info)
                                last_sent_state = current_state_key
                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                error_str = str(e).lower()
                                if any(pattern in error_str for pattern in [
                                    "1001", "1005", "1006", "1011", "1012",
                                    "going away", "no status code", "no close frame received or sent",
                                    "connection closed", "connection reset", "connection aborted",
                                    "connection refused", "connection timed out", "broken pipe",
                                    "websocket is closed", "websocket connection is closed",
                                    "remote end closed connection", "connection lost",
                                    "peer closed connection", "socket is not connected"
                                ]):
                                    break
                                else:
                                    logger.error(f"Error sending status update: {str(e)}")
                                    break
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.critical(f"Uncaught exception in websocket main loop: {e}", exc_info=True)
                        break
                else:
                    if last_sent_state is None:
                        try:
                            await websocket.send_json(state_info)
                            last_sent_state = (False, False, False, False, False, "Ready to Start", None, 0, 0)
                        except asyncio.CancelledError:
                            break
                        except Exception as e:
                            logger.critical(f"Uncaught exception in websocket main loop: {e}", exc_info=True)
                            break
                await asyncio.sleep(0.1)
        finally:
            if 'video_task' in locals():
                video_task.cancel()
                try:
                    await video_task
                except asyncio.CancelledError:
                    pass
    except asyncio.CancelledError:
        # Suppress noisy CancelledError on disconnect
        return
    except Exception as e:
        logger.critical(f"Uncaught exception in websocket endpoint: {e}", exc_info=True)
        # Never crash the process
    finally:
        # Track metrics for connection cleanup
        ACTIVE_WEBSOCKET_CONNECTIONS_GAUGE.dec()


@app.get("/api/reports")
async def list_reports(tenant_id: Optional[int] = None):
    """List HTML reports. Prefer DB if tenant context is present (query param or CONFIG_TENANT_ID), otherwise filesystem."""
    try:
        effective_tenant_id: Optional[int] = None
        if tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        if effective_tenant_id is not None:
            dbm = DatabaseManager()
            rows = dbm.execute_query(
                "SELECT id, name, created_at FROM simulation_reports WHERE tenant_id = %(tenant_id)s ORDER BY created_at DESC",
                {"tenant_id": effective_tenant_id},
            )
            reports = [
                {"id": r["id"], "filename": r["name"], "created": r["created_at"]}
                for r in rows
            ]
            return {"reports": reports, "source": "db"}
        # Fallback to filesystem
        reports_dir = project_root / "reports"
        logger.logger.info(f"Looking for reports in: {reports_dir.resolve()}")
        reports_dir.mkdir(exist_ok=True)
        reports = []
        for file in sorted(reports_dir.glob("*.html"), reverse=True):
            created = datetime.fromtimestamp(file.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            reports.append({"filename": file.name, "created": created})
        return {"reports": reports, "source": "fs"}
    except Exception as e:
        logger.logger.error(f"Error listing reports: {str(e)}")
        return {"reports": [], "error": str(e)}


@app.get("/api/reports/{ref}")
async def get_report(ref: str, tenant_id: Optional[int] = None):
    """Serve a specific HTML report. If tenant context is present, ref is DB id; otherwise ref is filename from filesystem."""
    try:
        effective_tenant_id: Optional[int] = None
        if tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        if effective_tenant_id is not None:
            dbm = DatabaseManager()
            rows = dbm.execute_query(
                "SELECT name, html FROM simulation_reports WHERE id = %(id)s AND tenant_id = %(tenant_id)s",
                {"id": int(ref), "tenant_id": effective_tenant_id},
            )
            if not rows:
                raise HTTPException(status_code=404, detail="Report not found")
            name = rows[0]["name"]
            html = rows[0]["html"]
            return Response(content=html, media_type="text/html", headers={"Content-Disposition": f"inline; filename={name}"})

        reports_dir = project_root / "reports"
        file_path = reports_dir / ref
        return handle_file_operation(
            file_path, lambda p: FileResponse(str(p), media_type="text/html")
        )
    except Exception as e:
        logger.error(f"Error serving report {ref}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{ref}")
async def delete_report(ref: str, tenant_id: Optional[int] = None):
    """Delete a specific HTML report. Prefer DB if tenant context is present, else filesystem."""
    effective_tenant_id: Optional[int] = None
    if tenant_id is not None:
        effective_tenant_id = tenant_id
    else:
        env_tid = os.getenv("CONFIG_TENANT_ID")
        if env_tid is not None:
            try:
                effective_tenant_id = int(env_tid)
            except ValueError:
                effective_tenant_id = None

    if effective_tenant_id is not None:
        try:
            dbm = DatabaseManager()
            dbm.execute_query(
                "DELETE FROM simulation_reports WHERE id = %(id)s AND tenant_id = %(tenant_id)s",
                {"id": int(ref), "tenant_id": effective_tenant_id},
            )
            return {"success": True, "message": "Report deleted"}
        except Exception as e:
            logger.error(f"Error deleting report {ref}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    reports_dir = project_root / "reports"
    file_path = reports_dir / ref
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


# --- Unified Logging: All logs go to logs/app.log ---

@app.post("/api/logs/write")
async def write_log(request: LogWriteRequest):
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        app_log_file = logs_dir / "app.log"
        log_entry = f"FRONTEND: {request.content}"
        logger.info(log_entry)
        return {"success": True, "file": str(app_log_file)}
    except Exception as e:
        logger.warning(f"Failed to write frontend log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/close")
async def close_log():
    """Close the current log file (no-op since files are closed after each write)"""
    return {"message": "Log file closed"}


@app.post("/api/logs/frontend")
async def frontend_log(request: FrontendLogRequest):
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_message = f"[{request.component}] {request.message}"
        if request.data:
            log_message += f" - Data: {request.data}"
        log_message += "\n"
        logger.info(log_message)
        return {"message": "Frontend log received"}
    except Exception as e:
        logger.error(f"Error logging frontend message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reset")
async def reset_config(request: ResetConfigRequest):
    """Reset configuration to defaults for a tenant (DB) or overwrite YAML fallback with defaults."""
    try:
        # Determine effective tenant id
        effective_tenant_id: Optional[int] = None
        if request.tenant_id is not None:
            effective_tenant_id = request.tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        # Load defaults from YAML file path; if missing, use currently loaded config
        from carla_simulator.utils.paths import get_config_path
        cfg_file = get_config_path("simulation.yaml")
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                defaults = yaml.safe_load(f) or {}
        except Exception:
            defaults = runner.config if isinstance(runner.config, dict) else {}

        if effective_tenant_id is not None:
            dbm = DatabaseManager()
            result = TenantConfig.upsert_active_config(dbm, effective_tenant_id, defaults)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to reset tenant config")
            return {"message": "Configuration reset to defaults (DB)", "tenant_id": effective_tenant_id, "config": defaults}

        # YAML fallback: overwrite file
        with open(runner.config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(defaults, f, sort_keys=False)
        runner.config = defaults
        return {"message": "Configuration reset to defaults (YAML)", "config": defaults}
    except Exception as e:
        logger.error(f"Error resetting configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simulation/status")
async def get_simulation_status():
    """Get detailed simulation status for debugging"""
    try:
        status_info = {
            "is_running": False,
            "is_starting": False,  # Include starting flag
            "is_stopping": False,  # Include stopping flag
            "is_skipping": False,  # Include skipping flag
            "is_transitioning": False,
            "current_scenario": None,
            "scenario_index": 0,
            "total_scenarios": 0,
            "session_id": None,
            "app_exists": False,
            "app_state_consistent": True,
            "last_state_update": None,
            "timestamp": datetime.now().isoformat(),
        }

        if hasattr(runner, "state"):
            status_info.update({
                "is_running": runner.state["is_running"],
                "is_starting": runner.state["is_starting"],  # Include starting flag
                "is_stopping": runner.state["is_stopping"],  # Include stopping flag
                "is_skipping": runner.state["is_skipping"],  # Include skipping flag
                "is_transitioning": runner.state["is_transitioning"],
                "current_scenario": runner.state["current_scenario"],
                "scenario_index": runner.state["current_scenario_index"] + 1,
                "total_scenarios": len(runner.state["scenarios_to_run"]),
                "session_id": str(runner.state.get("session_id", "")),
                "last_state_update": runner.state["last_state_update"].isoformat() if runner.state["last_state_update"] else None,
            })

        # Check if app exists and state consistency
        if hasattr(runner, "app") and runner.app:
            status_info["app_exists"] = True
            if hasattr(runner.app, "state"):
                app_running = runner.app.state.is_running
                runner_running = runner.state["is_running"]
                status_info["app_state_consistent"] = (app_running == runner_running)
                status_info["app_is_running"] = app_running
            else:
                status_info["app_state_consistent"] = False

        return status_info
    except Exception as e:
        logger.error(f"Error getting simulation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Authentication endpoints
@app.post("/api/auth/login")
async def login(request: Request, login_request: LoginRequest):
    """User login endpoint"""
    try:
        db = DatabaseManager()
        logger.info(f"Login attempt: username={login_request.username}")
        # Get user by username
        user = User.get_by_username(db, login_request.username)
        if not user:
            logger.warning(f"Login failed: username={login_request.username} (user not found)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        # Verify password
        if not verify_password(login_request.password, user["password_hash"]):
            logger.warning(f"Login failed: username={login_request.username} (wrong password)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        # Update last login
        user_obj = User()
        user_obj.id = user["id"]
        user_obj.update_last_login(db)
        # Create JWT token
        token_data = {
            "sub": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "is_admin": user["is_admin"]
        }
        access_token = create_jwt_token(token_data)
        # Create session token for additional security
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=24)
        # Get IP address and user agent from request
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        UserSession.create(
            db,
            user_id=user["id"],
            session_token=session_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        return {
            "access_token": access_token,
            "session_token": session_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "is_admin": user["is_admin"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """User registration endpoint"""
    try:
        db = DatabaseManager()
        logger.info(f"Register attempt: username={request.username}, email={request.email}")
        # Validate input
        if not validate_username(request.username):
            logger.warning(f"Register failed: invalid username={request.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be 3-50 characters and contain only letters, numbers, and underscores"
            )
        
        if not validate_email(request.email):
            logger.warning(f"Register failed: invalid email={request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        if not validate_password(request.password):
            logger.warning(f"Register failed: weak password for username={request.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters with uppercase, lowercase, and digit"
            )
        
        # Check if username already exists
        existing_user = User.get_by_username(db, request.username)
        if existing_user:
            logger.warning(f"Register failed: username already exists: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = User.get_by_email(db, request.email)
        if existing_email:
            logger.warning(f"Register failed: email already exists: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # Hash password
        password_hash = hash_password(request.password)
        
        # Create user
        user_data = {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "is_active": True,
            "is_admin": False
        }
        
        new_user = User.create(db, **user_data)
        if not new_user:
            logger.error(f"Register failed: could not create user {request.username}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        logger.info(f"Register success: username={request.username}, id={new_user['id']}")

        # Seed default config for this user by creating a per-user tenant if none provided
        try:
            # Determine tenant to use: if CONFIG_TENANT_ID is set, use it; otherwise create a per-user tenant
            default_tenant_id: Optional[int] = None
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    default_tenant_id = int(env_tid)
                except ValueError:
                    default_tenant_id = None

            if default_tenant_id is None:
                from carla_simulator.database.models import Tenant
                slug = f"user-{new_user['id']}"
                name = f"User {new_user['username']}"
                tenant = Tenant.create_if_not_exists(db, name=name, slug=slug, is_active=True)
                if tenant:
                    default_tenant_id = tenant["id"]

            if default_tenant_id is not None:
                # Load defaults from YAML fallback and store as active tenant config
                from carla_simulator.utils.paths import get_config_path
                cfg_file = get_config_path("simulation.yaml")
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        defaults = yaml.safe_load(f) or {}
                except Exception:
                    defaults = runner.config if isinstance(runner.config, dict) else {}
                TenantConfig.upsert_active_config(db, default_tenant_id, defaults)
        except Exception as se:
            logger.warning(f"Failed to seed default config for new user: {se}")
        
        return {
            "message": "User registered successfully",
            "user": {
                "id": new_user["id"],
                "username": new_user["username"],
                "email": new_user["email"],
                "first_name": new_user["first_name"],
                "last_name": new_user["last_name"],
                "is_admin": new_user["is_admin"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """User logout endpoint"""
    try:
        db = DatabaseManager()
        logger.info(f"Logout: user_id={current_user['sub']}, username={current_user['username']}")
        # Delete user sessions
        UserSession.delete_user_sessions(db, current_user["sub"])
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    try:
        db = DatabaseManager()
        logger.info(f"Get current user info: user_id={current_user['sub']}, username={current_user['username']}")
        user = User.get_by_username(db, current_user["username"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_admin": user["is_admin"],
            "created_at": user["created_at"],
            "last_login": user["last_login"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/api/auth/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users (admin only)"""
    try:
        require_admin(current_user)
        
        db = DatabaseManager()
        query = "SELECT id, username, email, first_name, last_name, is_active, is_admin, created_at, last_login FROM users ORDER BY created_at DESC"
        users = db.execute_query(query)
        
        return {"users": users}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get users error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.post("/api/auth/check-username")
async def check_username(payload: dict):
    db = DatabaseManager()
    username = payload.get("username")
    user = User.get_by_username(db, username)
    return {"exists": bool(user)}

@app.post("/api/auth/reset-password")
async def reset_password(payload: dict):
    db = DatabaseManager()
    username = payload.get("username")
    new_password = payload.get("new_password")
    user = User.get_by_username(db, username)
    if not user:
        return {"success": False, "message": "User not found"}
    password_hash = hash_password(new_password)
    query = "UPDATE users SET password_hash = %(password_hash)s WHERE username = %(username)s"
    db.execute_query(query, {"password_hash": password_hash, "username": username})
    return {"success": True, "message": "Password updated"}


@app.post("/api/auth/change-password")
async def change_password(payload: dict, current_user: dict = Depends(get_current_user)):
    db = DatabaseManager()
    user = User.get_by_username(db, current_user["username"])
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")
    if not user or not verify_password(current_password, user["password_hash"]):
        return {"success": False, "message": "Current password is incorrect."}
    password_hash = hash_password(new_password)
    query = "UPDATE users SET password_hash = %(password_hash)s WHERE username = %(username)s"
    db.execute_query(query, {"password_hash": password_hash, "username": user["username"]})
    return {"success": True, "message": "Password changed successfully."}


@app.get("/api/version")
async def get_version():
    version = os.environ.get("VERSION", "dev")
    return {"version": version}


if __name__ == "__main__":
    import uvicorn
    import logging

    # Configure logging to use separate backend logs directory
    logs_dir = Path("logs")
    backend_logs_dir = logs_dir / "backend"
    backend_logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure backend logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(backend_logs_dir / "app.log"),
            logging.StreamHandler()
        ]
    )

    # Suppress specific WebSocket connection messages
    websocket_filter = WebSocketConnectionFilter()
    logging.getLogger("uvicorn.protocols.websockets.websockets_impl").setLevel(logging.ERROR)
    logging.getLogger("websockets").setLevel(logging.ERROR)
    logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
    logging.getLogger("websockets.server").setLevel(logging.ERROR)
    logging.getLogger("websockets.client").setLevel(logging.ERROR)
    
    # Apply filter to suppress "connection closed" messages
    for logger_name in ["uvicorn.error", "uvicorn.access", "uvicorn.protocols.websockets.websockets_impl"]:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.addFilter(websocket_filter)

    # Load host/port strictly from YAML config (fallback to defaults if missing)
    try:
        import yaml
        from carla_simulator.utils.paths import get_config_path

        cfg_host, cfg_port = "0.0.0.0", 8000
        cfg_path = get_config_path("simulation.yaml")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                web_cfg = cfg.get("web", {}) or {}
                cfg_host = str(web_cfg.get("host", cfg_host))
                cfg_port = int(web_cfg.get("port", cfg_port))

        logger.info(f"Starting FastAPI server on {cfg_host}:{cfg_port}")
        uvicorn.run(app, host=cfg_host, port=cfg_port, log_level="warning")
    except Exception:
        # Fallback to sane defaults if config loading fails
        logger.info("Starting FastAPI server on 0.0.0.0:8000 (config load failed)")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
