import os
import logging
import functools
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/xdg"
    if not os.path.exists("/tmp/xdg"):
        os.makedirs("/tmp/xdg", exist_ok=True)

# Ensure headless-friendly SDL drivers for pygame on servers without display/audio, and hide support prompt
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, status, websockets
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from jsonschema import validate as js_validate, Draft7Validator
import jsonschema
from typing import List, Optional, Dict
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
from contextvars import ContextVar
import threading
from threading import Lock, Event
import queue
import time
import uuid
import atexit
import signal
from fastapi.responses import FileResponse
from carla_simulator.database.models import Tenant, TenantConfig
from carla_simulator.database.db_manager import DatabaseManager

# Add monitoring imports
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, Info
import prometheus_client

app = FastAPI()
# Import tenant context for logging and set per-request based on header/query/env
from carla_simulator.utils.logging import CURRENT_TENANT_ID
from carla_simulator.utils.auth import verify_jwt_token
from carla_simulator.database.models import Tenant, TenantConfig
from carla_simulator.database.db_manager import DatabaseManager
@app.on_event("startup")
async def _ensure_global_default_on_startup():
    try:
        db = DatabaseManager()
        t = Tenant.create_if_not_exists(db, name="Global Default", slug="global-default", is_active=True)
        if not t:
            return
        tid = int(t["id"]) if isinstance(t, dict) else None
        if tid is None:
            return
        existing = TenantConfig.get_active_config(db, tid)
        if not existing:
            defaults = db.get_carla_metadata("simulation_defaults") or {}
            if isinstance(defaults, dict) and len(defaults) > 0:
                TenantConfig.upsert_active_config(db, tid, defaults)
    except Exception:
        pass

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    tenant_id_ctx = None
    header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
    if header_tid:
        try:
            tenant_id_ctx = int(header_tid)
        except ValueError:
            tenant_id_ctx = None
    if tenant_id_ctx is None:
        tid_q = request.query_params.get("tenant_id")
        if tid_q:
            try:
                tenant_id_ctx = int(tid_q)
            except ValueError:
                tenant_id_ctx = None
    if tenant_id_ctx is None:
        env_tid = os.getenv("CONFIG_TENANT_ID")
        if env_tid:
            try:
                tenant_id_ctx = int(env_tid)
            except ValueError:
                tenant_id_ctx = None
    # 4) JWT claim
    if tenant_id_ctx is None:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = verify_jwt_token(token)
            if payload and isinstance(payload, dict):
                try:
                    claim_tid = payload.get("tenant_id")
                    if claim_tid is not None:
                        tenant_id_ctx = int(claim_tid)
                except Exception:
                    tenant_id_ctx = tenant_id_ctx
    token = CURRENT_TENANT_ID.set(tenant_id_ctx)
    # Also set user id context if a valid bearer token exists
    user_token = None
    try:
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            jwt_token = auth_header.split(" ", 1)[1]
            payload = verify_jwt_token(jwt_token)
            if isinstance(payload, dict):
                uid = payload.get("user_id") or payload.get("id")
                if uid is not None:
                    from carla_simulator.utils.logging import CURRENT_USER_ID as _CUID
                    user_token = _CUID.set(int(uid))
    except Exception:
        user_token = None
    try:
        response = await call_next(request)
    finally:
        CURRENT_TENANT_ID.reset(token)
        try:
            if user_token is not None:
                from carla_simulator.utils.logging import CURRENT_USER_ID as _CUID
                _CUID.reset(user_token)
        except Exception:
            pass
    return response

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
CARLA_POOL_IN_USE_GAUGE = Gauge('carla_pool_in_use', 'Number of CARLA endpoints/containers in use')
CARLA_POOL_RUNNING_GAUGE = Gauge('carla_pool_running_total', 'Number of CARLA containers/endpoints available/running')

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
from .runner_registry import RunnerRegistry
from .carla_pool import CarlaContainerManager
from carla_simulator.scenarios.scenario_registry import ScenarioRegistry
from carla_simulator.utils.config import Config, load_config, save_config
from carla_simulator.utils.logging import Logger
from carla_simulator.utils.paths import get_project_root
from carla_simulator.core.scenario_results_manager import ScenarioResultsManager
from carla_simulator.database.db_manager import DatabaseManager
from carla_simulator.database.models import User, UserSession, TenantConfig, SimulationReport, CarlaMetadata
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
    app_config: dict | None = None
    sim_config: dict | None = None


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
            "tenant_id": None,  # Active tenant id for the running simulation (if any)
            "status_message": "Ready to Start",
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

# Global primitives kept for legacy single-tenant flow, but per-tenant events live on TenantRunner
setup_event = Event()
simulation_ready = Event()


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

        # Prefer per-tenant cleanup to avoid cross-tenant interference using the
        # in-module registry created below.
        try:
            for tid, tenant_runner in list(registry._tenant_to_runner.items()):
                try:
                    app = getattr(tenant_runner.runner, "app", None)
                    if app is None:
                        continue
                    # Stop the loop
                    if hasattr(app, "state"):
                        app.state.is_running = False
                    # Perform cleanup once
                    if hasattr(app, "get_cleanup_results"):
                        completed, _ = app.get_cleanup_results()
                        if not completed and hasattr(app, "cleanup"):
                            app.cleanup()
                    elif hasattr(app, "cleanup"):
                        app.cleanup()
                    # Drop reference
                    tenant_runner.runner.app = None
                except Exception as e:
                    logger.error(f"Error cleaning tenant {tid}: {e}")
        except Exception:
            # Fallback: legacy single-runner cleanup
            if hasattr(runner, "app") and runner.app:
                try:
                    if hasattr(runner.app, "state"):
                        runner.app.state.is_running = False
                    if hasattr(runner.app, "cleanup"):
                        runner.app.cleanup()
                except Exception as e:
                    logger.error(f"Error during app cleanup: {str(e)}")
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
                    # IMPORTANT: Do not invoke global cleanup here, it may disrupt other tenants.
                    # Per-tenant cleanup below will be handled by the tenant's world manager during retry/setup.
                    # Consider small backoff if needed.
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


def run_simulation_thread(runner, scenario, tenant_events=None):
    """Thread-safe simulation runner with proper synchronization"""
    # Use per-tenant events if provided; fall back to globals for legacy
    per_setup_event = None
    per_sim_ready = None
    if tenant_events is not None:
        per_setup_event = tenant_events.get("setup_event")
        per_sim_ready = tenant_events.get("simulation_ready")
    
    # Add tenant identification for debugging
    tenant_id = None
    if hasattr(runner, "state") and runner.state:
        tenant_id = runner.state.get("tenant_id")
    
    logger.debug(f"Simulation thread started for tenant {tenant_id}, scenario: {scenario}")
    
    try:
        # Bind tenant context for this thread so DB logs and metrics are isolated
        _tenant_token = None
        try:
            tid = None
            if hasattr(runner, "state"):
                tid = runner.state.get("tenant_id")
            if tid is not None:
                _tenant_token = CURRENT_TENANT_ID.set(int(tid))
                logger.debug(f"Bound tenant context for thread: {tid}")
        except Exception:
            _tenant_token = None

        logger.debug(f"Simulation thread started, waiting for setup completion... (tenant: {tenant_id})")
        
        # Signal that simulation thread is ready
        # CRITICAL FIX: Only use per-tenant events when provided, never fall back to globals
        if per_sim_ready is not None:
            per_sim_ready.set()
            logger.debug(f"Set per-tenant simulation_ready event for tenant {tenant_id}")
        elif tenant_events is None:
            # Only use global events for legacy single-tenant flow
            simulation_ready.set()
            logger.debug("Set global simulation_ready event (legacy mode)")
        else:
            # If tenant_events is provided but per_sim_ready is None, this is an error
            logger.error("Per-tenant events provided but simulation_ready is None")
            return
        
        # Wait for setup to complete before starting simulation
        # CRITICAL FIX: Only use per-tenant events when provided, never fall back to globals
        if per_setup_event is not None:
            wait_event = per_setup_event
            logger.debug(f"Using per-tenant setup_event for tenant {tenant_id}")
        elif tenant_events is None:
            # Only use global events for legacy single-tenant flow
            wait_event = setup_event
            logger.debug("Using global setup_event (legacy mode)")
        else:
            # If tenant_events is provided but per_setup_event is None, this is an error
            logger.error("Per-tenant events provided but setup_event is None")
            return
            
        logger.debug(f"Waiting for setup completion... (tenant: {tenant_id})")
        if wait_event.wait(timeout=600):
            logger.debug(f"Setup completed, starting simulation loop (tenant: {tenant_id})")
        else:
            logger.error(f"Setup timeout - simulation thread exiting (tenant: {tenant_id})")
            return
        
        # Mark setup as complete
        runner.state["setup_complete"] = True
        
        # Clear the starting flag now that simulation is actually running
        runner.state["is_starting"] = False
        runner.state["status_message"] = "Simulation running"
        logger.debug(f"Cleared is_starting flag - simulation is now running (tenant: {tenant_id})")
        logger.debug(f"State after clearing is_starting: is_running={runner.state['is_running']}, is_starting={runner.state['is_starting']}, is_transitioning={runner.state['is_transitioning']} (tenant: {tenant_id})")
        
        logger.debug(f"Simulation loop started (tenant: {tenant_id})")
        
        try:
            # Start the simulation
            runner.app.run()
            logger.debug(f"Simulation app.run() completed normally (tenant: {tenant_id})")
        except Exception as e:
            logger.error(f"Exception in runner.app.run() for tenant {tenant_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    except Exception as e:
        logger.error(f"Error in simulation thread for tenant {tenant_id}: {str(e)}")
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
        # Reset bound tenant context for this thread if set
        try:
            if '_tenant_token' in locals() and _tenant_token is not None:
                CURRENT_TENANT_ID.reset(_tenant_token)
                logger.debug(f"Reset tenant context for thread (tenant: {tenant_id})")
        except Exception:
            pass
        logger.debug(f"Simulation thread ending (tenant: {tenant_id})")
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

        # Preserve CARLA endpoint (host:port) from current app to avoid reconnecting to defaults
        try:
            prev_app = getattr(runner, "app", None)
            if prev_app is not None and hasattr(prev_app, "_config") and hasattr(prev_app._config, "server_config"):
                prev_host = getattr(prev_app._config.server_config, "host", None)
                prev_port = getattr(prev_app._config.server_config, "port", None)
                if prev_host is not None and prev_port is not None:
                    try:
                        new_app._config.server_config.host = prev_host
                        new_app._config.server_config.port = int(prev_port)
                    except Exception:
                        pass
            # Also mirror onto the new connection manager config
            if hasattr(new_app, "connection") and hasattr(new_app.connection, "config"):
                if prev_host is not None and prev_port is not None:
                    try:
                        new_app.connection.config.host = prev_host
                        new_app.connection.config.port = int(prev_port)
                    except Exception:
                        pass
        except Exception:
            pass

        # Connect to CARLA server
        logger.debug("Connecting to CARLA server...")
        try:
            h = getattr(new_app._config.server_config, 'host', None)
            p = getattr(new_app._config.server_config, 'port', None)
            if h is not None and p is not None:
                logger.debug(f"Connecting to CARLA server at {h}:{p} ...")
        except Exception:
            pass
        if not new_app.connection.connect():
            logger.error("Failed to connect to CARLA server")
            return False

        # Wait for connection to stabilize
        # time.sleep(1)

        # Setup components
        setup_simulation_components(runner, new_app)

        # Update runner state
        runner.state["current_scenario"] = next_scenario
        # Get controller type from the new application configuration
        controller_type = new_app._config.controller_config.type if hasattr(new_app, '_config') and hasattr(new_app._config, 'controller_config') else "autopilot"
        
        # Store controller type in state
        runner.state["controller_type"] = controller_type
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

# Enable CORS (env-driven allowlist; default allows all for dev)
allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use robust project root
project_root = get_project_root()

# Initialize default single runner for backward compatibility (used if no tenant header)
runner = SimulationRunner(db_only=True)
runner.state = ThreadSafeState()

# Initialize per-tenant registry and CARLA pool
registry = RunnerRegistry()
carla_pool = CarlaContainerManager()

# Web frontend log file handle
web_log_file = None


# --- Global exception handler to prevent container crash ---
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        import traceback
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"Uncaught exception: {exc_type.__name__}: {exc_value}\n{tb_str}")
    except Exception:
        # Fallback if formatting fails
        logger.critical(f"Uncaught exception: {exc_type.__name__}: {exc_value}")

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


# Minimal root endpoint for Docker healthchecks (returns 200)
@app.get("/")
async def root_ok():
    return {"status": "ok", "service": "carla-backend", "timestamp": datetime.now().isoformat()}


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
        
        # Update CARLA pool metrics
        try:
            st = carla_pool.status()
            CARLA_POOL_IN_USE_GAUGE.set(int(st.get("in_use", 0)))
            running_total = int(st.get("running_total", st.get("capacity", 0) or 0))
            CARLA_POOL_RUNNING_GAUGE.set(running_total)
        except Exception:
            pass
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
async def get_config(request: Request, tenant_id: Optional[int] = None):
    """Get current configuration. If tenant_id provided, return DB-backed active config."""
    try:
        # Resolve effective tenant id: header > query > env
        effective_tenant_id: Optional[int] = None
        header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
        if header_tid:
            try:
                effective_tenant_id = int(header_tid)
            except ValueError:
                effective_tenant_id = None
        if effective_tenant_id is None and tenant_id is not None:
            effective_tenant_id = tenant_id
        if effective_tenant_id is None:
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
            # Fallback to DB defaults if active config not present
            defaults = dbm.get_carla_metadata("simulation_defaults")
            return defaults or {}
        # No tenant context: require tenant for DB-only mode
        raise HTTPException(status_code=400, detail="Tenant context required (CONFIG_TENANT_ID or ?tenant_id=)")
    except HTTPException:
        # Propagate intended HTTP errors (e.g., 400 when tenant context missing)
        raise
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/defaults")
async def get_config_defaults():
    """Return default configuration values stored in DB metadata."""
    try:
        dbm = DatabaseManager()
        defaults = dbm.get_carla_metadata("simulation_defaults")
        return {"config": defaults or {}}
    except Exception as e:
        logger.error(f"Error getting default configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/seed-default-config")
async def admin_seed_default_config(current_user: dict = Depends(get_current_user)):
    """Ensure a global default tenant exists and seed its config from carla_metadata('simulation_defaults')."""
    require_admin(current_user)
    try:
        db = DatabaseManager()
        # Ensure global-default tenant exists (id assigned by DB). Use slug for idempotency.
        tenant = Tenant.create_if_not_exists(db, name="Global Default", slug="global-default", is_active=True)
        if not tenant:
            raise HTTPException(status_code=500, detail="Failed to ensure global-default tenant")
        default_tid = int(tenant["id"]) if isinstance(tenant, dict) else int(tenant.id)
        # Fetch defaults from metadata
        defaults = db.get_carla_metadata("simulation_defaults")
        if not isinstance(defaults, dict) or len(defaults) == 0:
            raise HTTPException(status_code=400, detail="No defaults configured in DB (simulation_defaults)")
        # Upsert as active config for global-default tenant
        TenantConfig.upsert_active_config(db, default_tid, defaults)
        return {"message": "Seeded default config", "tenant_id": default_tid}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error seeding default config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(request: Request, config_update: ConfigUpdate, tenant_id: Optional[int] = None):
    """Update configuration"""
    try:
        logger.debug("Updating configuration")

        # Merge app and sim sections into one dict for existing storage shape
        merged: dict = {}
        if config_update.app_config:
            merged.update(config_update.app_config)
        if config_update.sim_config:
            merged.update(config_update.sim_config)

        # Server-side validation via jsonschema (permissive baseline)
        try:
            # Simple baseline schema requiring objects
            base_schema = {"type": "object"}
            Draft7Validator.check_schema(base_schema)
            js_validate(instance=config_update.app_config or {}, schema=base_schema)
            js_validate(instance=config_update.sim_config or {}, schema=base_schema)
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            raise HTTPException(status_code=400, detail=f"Configuration validation failed: {e}")

        # Ensure payload is acceptable even if client sends only split sections
        # (older clients used config_data, which we no longer require)

        # Resolve effective tenant id: header > query > env
        effective_tenant_id: Optional[int] = None
        header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
        if header_tid:
            try:
                effective_tenant_id = int(header_tid)
            except ValueError:
                effective_tenant_id = None
        if effective_tenant_id is None and tenant_id is not None:
            effective_tenant_id = tenant_id
        if effective_tenant_id is None:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        if effective_tenant_id is not None:
            try:
                dbm = DatabaseManager()
                merged_payload = merged
                # Touch columns (no-op) to ensure migration applied; ignore errors
                try:
                    dbm.execute_query("UPDATE tenant_configs SET app_config = app_config WHERE 1=0")
                except Exception:
                    pass
                result = TenantConfig.upsert_active_config(dbm, effective_tenant_id, merged_payload)
                if not result:
                    raise RuntimeError("DB upsert returned no result")
                return {"message": "Tenant configuration updated", "tenant_id": effective_tenant_id, "version": result["version"], "config": merged_payload}
            except Exception as e:
                logger.error(f"Tenant DB save failed (tenant_id={effective_tenant_id}): {e}")
                raise HTTPException(status_code=500, detail=f"DB save failed: {e}")

        # If no tenant context, explicitly reject (DB-only policy)
        raise HTTPException(status_code=400, detail="Tenant context required (CONFIG_TENANT_ID or ?tenant_id=) for saving")

        logger.debug("Configuration updated successfully")
        return {
            "message": "Configuration updated successfully",
                # Return the dict we just wrote (frontend expects plain JSON)
                "config": merged,
                "source": "db" if effective_tenant_id is not None else "fs",
        }
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid configuration format: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/skip")
async def skip_scenario(request: Request, current_user: dict = Depends(get_current_user)):
    """Skip the current scenario and move to the next one with improved reliability"""
    try:
        # Enforce tenant scoping: only allow the tenant that started the simulation to control it
        effective_tid: Optional[int] = None
        header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
        if header_tid:
            try:
                effective_tid = int(header_tid)
            except ValueError:
                effective_tid = None
        # Resolve tenant-specific runner
        tenant_runner = registry.get(effective_tid) if effective_tid is not None else None
        if tenant_runner is None:
            raise HTTPException(status_code=400, detail="No active simulation for this tenant")
        if tenant_runner.runner.state.get("tenant_id") is not None and effective_tid is not None:
            if int(tenant_runner.runner.state.get("tenant_id")) != int(effective_tid):
                raise HTTPException(status_code=403, detail="Operation not permitted for this tenant")

        # Check if simulation is running
        if not tenant_runner.runner.state["is_running"]:
            logger.warning("Attempted to skip scenario while simulation is not running")
            return {"success": False, "message": "Simulation is not running"}

        # Check if we're already transitioning
        if tenant_runner.runner.state["is_transitioning"]:
            logger.warning("Attempted to skip scenario while transition is in progress")
            return {"success": False, "message": "Scenario transition already in progress"}
        
        # Set skipping flag for immediate UX feedback
        tenant_runner.runner.state["is_skipping"] = True
        logger.debug(f"Skip operation started for tenant {effective_tid}, current scenario: {tenant_runner.runner.state.get('current_scenario')}")
        
        # Track metrics
        SIMULATION_SKIP_COUNTER.inc()
        
        # Only set is_transitioning for actual scenario transitions
        current_index = tenant_runner.runner.state["current_scenario_index"]
        total_scenarios = len(tenant_runner.runner.state["scenarios_to_run"])
        if current_index < total_scenarios - 1:
            tenant_runner.runner.state["is_transitioning"] = True
            logger.debug(f"Set is_transitioning=True for tenant {effective_tid}")
        try:
            current_scenario = tenant_runner.runner.state["current_scenario"]
            if current_scenario:
                # Offload DB/log write to thread to avoid blocking the event loop
                await asyncio.to_thread(
                    record_scenario_result,
                    tenant_runner.runner,
                    current_scenario,
                    "Failed",
                    "Skipped",
                    datetime.now() - tenant_runner.runner.state["scenario_start_time"],
                )

            # If there are more scenarios, prepare for next one
            if current_index < total_scenarios - 1:
                next_scenario = tenant_runner.runner.state["scenarios_to_run"][current_index + 1]
                logger.info("================================")
                logger.info(
                    f"Starting scenario {current_index + 2}/{total_scenarios}: {next_scenario}"
                )
                logger.info("================================")

                # Update status message immediately for frontend overlay during skip
                try:
                    tenant_runner.runner.state["status_message"] = (
                        f"Skipping to: {next_scenario} ({current_index + 2}/{total_scenarios})"
                    )
                except Exception:
                    pass

                # Stop current scenario but keep is_running true during transition
                if hasattr(tenant_runner.runner, "app") and tenant_runner.runner.app and hasattr(tenant_runner.runner.app, "state"):
                    tenant_runner.runner.app.state.is_running = False
                    logger.debug("Set app.state.is_running = False for transition")

                # Begin cleanup in background to reduce transition blocking; do not await full 20s
                logger.debug("Initiating cleanup before scenario transition (non-blocking)...")
                if hasattr(tenant_runner.runner, "app") and tenant_runner.runner.app:
                    import threading as _t
                    app_ref = tenant_runner.runner.app
                    def _bg_cleanup():
                        try:
                            if hasattr(app_ref, "is_cleanup_complete"):
                                app_ref.is_cleanup_complete = False
                            if hasattr(app_ref, "state"):
                                app_ref.state.is_running = False
                            if hasattr(app_ref, "cleanup"):
                                app_ref.cleanup()
                        except Exception as e:
                            logger.error(f"Background cleanup error during skip (tenant {effective_tid}): {e}")
                    _t.Thread(target=_bg_cleanup, daemon=True).start()

                # Transition to next scenario without blocking event loop
                success = await asyncio.to_thread(transition_to_next_scenario, tenant_runner.runner, next_scenario)
                if success:
                    # Prepare per-tenant events for the new run and mark setup complete
                    tenant_runner.setup_event.clear()
                    tenant_runner.simulation_ready.clear()

                    # Start simulation in background with per-tenant events
                    logger.debug(f"Starting simulation thread for tenant {effective_tid} with per-tenant events...")
                    tenant_events = {"setup_event": tenant_runner.setup_event, "simulation_ready": tenant_runner.simulation_ready}
                    simulation_thread = threading.Thread(
                        target=run_simulation_thread,
                        args=(tenant_runner.runner, next_scenario, tenant_events),
                        daemon=True,
                    )
                    # For transition we already connected and set up components; let thread proceed
                    tenant_runner.setup_event.set()
                    simulation_thread.start()

                    # Defer clearing flags until the new scenario signals readiness to avoid UI flicker
                    import threading as _t2
                    def _post_transition_finalize():
                        try:
                            # Wait up to 10s for simulation_ready; then finalize flags
                            tenant_runner.simulation_ready.wait(timeout=10.0)
                        except Exception:
                            pass
                        finally:
                            tenant_runner.runner.state["is_transitioning"] = False
                            tenant_runner.runner.state["is_skipping"] = False
                            # Compose a running status including index/total
                            try:
                                idx = tenant_runner.runner.state.get("current_scenario_index", 0) + 1
                                tot = len(tenant_runner.runner.state.get("scenarios_to_run", []))
                                cur = tenant_runner.runner.state.get("current_scenario")
                                if cur:
                                    tenant_runner.runner.state["status_message"] = f"Running: {cur} {idx}/{tot}"
                                else:
                                    tenant_runner.runner.state["status_message"] = "Simulation running"
                            except Exception:
                                tenant_runner.runner.state["status_message"] = "Simulation running"
                    _t2.Thread(target=_post_transition_finalize, daemon=True).start()

                    return {
                        "success": True,
                        "message": f"Skipped {current_scenario} ({current_index + 1}/{total_scenarios}). Running: {next_scenario}",
                        "current_scenario": current_scenario,
                        "next_scenario": next_scenario,
                        "scenario_index": current_index + 2,
                        "total_scenarios": total_scenarios,
                    }
                else:
                    tenant_runner.runner.state["is_running"] = False
                    tenant_runner.runner.state["is_transitioning"] = False
                    return {
                        "success": False,
                        "message": "Failed to transition to next scenario",
                    }
            else:
                # This was the last scenario - call stop_simulation to handle cleanup
                logger.info("================================")
                logger.info("Last scenario skipped. Simulation complete.")
                logger.info("================================")

                # Update status for final skip where no next scenario exists
                try:
                    tenant_runner.runner.state["status_message"] = (
                        f"Skipping scenario {current_index + 1}/{total_scenarios}...\nSimulation complete"
                    )
                except Exception:
                    pass

                # Call stop_simulation to handle the cleanup properly
                stop_result = await stop_simulation(request)
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
            tenant_runner.runner.state["is_running"] = False
            tenant_runner.runner.state["is_stopping"] = False  # Reset stopping flag on error
            tenant_runner.runner.state["is_transitioning"] = False
            tenant_runner.runner.state["is_skipping"] = False  # Reset skipping flag on error
            raise

    except Exception as e:
        logger.error(f"Error skipping scenario: {str(e)}")
        # Ensure is_running is set to false on error
        try:
            tenant_runner = registry.get(effective_tid) if effective_tid is not None else None
            if tenant_runner is not None:
                tenant_runner.runner.state["is_running"] = False
                tenant_runner.runner.state["is_stopping"] = False  # Reset stopping flag on error
                tenant_runner.runner.state["is_transitioning"] = False
                tenant_runner.runner.state["is_skipping"] = False  # Reset skipping flag on error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/start")
async def start_simulation(request: SimulationRequest, http_request: Request, current_user: dict = Depends(get_current_user)):
    """Start simulation with given parameters (per-tenant)."""
    global setup_event, simulation_ready
    
    try:
        # Resolve effective tenant id: header > body > JWT
        effective_tid: Optional[int] = None
        header_tid = http_request.headers.get("x-tenant-id") or http_request.headers.get("X-Tenant-Id")
        if header_tid:
            try:
                effective_tid = int(header_tid)
            except ValueError:
                effective_tid = None
        if effective_tid is None and request.tenant_id is not None:
            effective_tid = int(request.tenant_id)
        if effective_tid is None:
            try:
                claim_tid = current_user.get("tenant_id")
                if claim_tid is not None:
                    effective_tid = int(claim_tid)
            except Exception:
                effective_tid = None
        if effective_tid is None:
            raise HTTPException(status_code=400, detail="Tenant context required to start simulation")

        tenant_runner = registry.get_or_create(effective_tid)

        # Check if already running for this tenant
        if tenant_runner.runner.state.get("is_running"):
            logger.warning("Attempted to start simulation while already running (tenant)")
            return {"success": False, "message": "Simulation is already running"}

        if tenant_runner.runner.state.get("is_transitioning"):
            logger.warning("Attempted to start simulation while transition is in progress (tenant)")
            return {"success": False, "message": "Simulation transition already in progress"}

        # Set transition flag to prevent race conditions
        tenant_runner.runner.state["is_transitioning"] = True
        tenant_runner.runner.state["is_starting"] = True  # Set starting flag for immediate UX feedback
        tenant_runner.runner.state["status_message"] = "Hang on,\nLoading Simulation..."
        logger.info(f"State is_starting: {tenant_runner.runner.state['is_starting']}")
        logger.info(
            f"Starting simulation with scenarios: {request.scenarios}, debug: {request.debug}, report: {request.report}"
        )

        # Reset per-tenant synchronization events
        tenant_runner.setup_event.clear()
        tenant_runner.simulation_ready.clear()

        # Register scenarios first
        ScenarioRegistry.register_all()

        # Setup logger
        tenant_runner.runner.setup_logger(request.debug)

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
            # Update state
            tenant_runner.runner.state.update(
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
                    "tenant_id": effective_tid,
                    "status_message": "Hang on,\nLoading Simulation...",
                }
            )
            logger.debug(f"Updated state: is_running=True, is_starting={tenant_runner.runner.state['is_starting']}, is_transitioning={tenant_runner.runner.state['is_transitioning']}")
            tenant_runner.runner.state["scenario_results"].clear_results()

            # Resolve effective tenant for this run: header > body > env
            # Do NOT mutate process-wide environment for tenant selection; we'll bind
            # the tenant context to the simulation thread via ContextVar instead.

            # Create application instance up front
            tenant_runner.runner.app = tenant_runner.runner.create_application(
                scenarios_to_run[0], session_id=session_id
            )
            
            # Store controller type separately for frontend use
            controller_type = tenant_runner.runner.app._config.controller_config.type if hasattr(tenant_runner.runner.app, '_config') and hasattr(tenant_runner.runner.app._config, 'controller_config') else "autopilot"
            
            # Store controller type in state
            tenant_runner.runner.state["controller_type"] = controller_type

            # Set web mode in configuration
            tenant_runner.runner.app._config.web_mode = True
            # Set report flag in configuration if requested
            if request.report:
                setattr(tenant_runner.runner.app._config, "report", True)

            # Start simulation thread FIRST (it will wait for setup completion)
            logger.debug(f"Starting simulation thread for tenant {effective_tid} (will wait for setup completion)...")
            tenant_events = {"setup_event": tenant_runner.setup_event, "simulation_ready": tenant_runner.simulation_ready}
            simulation_thread = threading.Thread(
                target=run_simulation_thread,
                args=(tenant_runner.runner, scenarios_to_run[0], tenant_events),
                daemon=True,
            )
            simulation_thread.start()

            # Run heavy setup in background to avoid blocking HTTP request and event loop
            def _bg_heavy_setup():
                try:
                    # Bind tenant context in this background thread for per-tenant behavior (e.g., TM port)
                    _tenant_token = None
                    try:
                        _tenant_token = CURRENT_TENANT_ID.set(int(effective_tid))
                    except Exception:
                        _tenant_token = None
                    tenant_runner.runner.state["status_message"] = "Allocating CARLA server..."
                    # Acquire CARLA endpoint (may create container)
                    carla_host, carla_port = carla_pool.acquire(effective_tid)
                    try:
                        username = current_user.get("username") if isinstance(current_user, dict) else None
                    except Exception:
                        username = None
                    from carla_simulator.utils.logging import Logger as _L
                    _L().info(f"Tenant {effective_tid} (user={username}) assigned CARLA endpoint {carla_host}:{carla_port}")

                    tenant_runner.runner.state["status_message"] = "Connecting to CARLA server..."
                    # Inject tenant CARLA host/port
                    try:
                        if hasattr(tenant_runner.runner.app._config, 'server_config'):
                            tenant_runner.runner.app._config.server_config.host = carla_host
                            tenant_runner.runner.app._config.server_config.port = int(carla_port)
                        if hasattr(tenant_runner.runner.app, 'connection') and hasattr(tenant_runner.runner.app.connection, 'config'):
                            tenant_runner.runner.app.connection.config.host = carla_host
                            tenant_runner.runner.app.connection.config.port = int(carla_port)
                    except Exception:
                        pass

                    # Connect to CARLA server
                    logger.info(f"Connecting to CARLA server for tenant {effective_tid} at {carla_host}:{carla_port} ...")
                    if not tenant_runner.runner.app.connection.connect():
                        logger.error("Failed to connect to CARLA server")
                        tenant_runner.runner.state["is_running"] = False
                        tenant_runner.runner.state["is_transitioning"] = False
                        tenant_runner.runner.state["is_starting"] = False
                        tenant_runner.runner.state["status_message"] = "Failed to connect to CARLA server"
                        return

                    # Setup components with retry
                    tenant_runner.runner.state["status_message"] = "Setting up world and sensors..."
                    try:
                        setup_simulation_components(tenant_runner.runner, tenant_runner.runner.app)
                        logger.debug("Simulation components setup completed")
                    except RuntimeError as e:
                        if "Failed to create vehicle" in str(e):
                            tenant_runner.runner.state["is_running"] = False
                            tenant_runner.runner.state["is_transitioning"] = False
                            logger.error("Failed to create vehicle after multiple attempts. Please try again.")
                            tenant_runner.runner.state["status_message"] = "Failed to create vehicle"
                            return
                        raise

                    # Stabilize briefly
                    tenant_runner.runner.state["status_message"] = "Starting simulation..."
                    time.sleep(0.5)

                    # Signal setup complete so simulation thread can enter run()
                    logger.debug("Signaling setup completion to simulation thread...")
                    tenant_runner.setup_event.set()

                    # Reset transition flag after successful start
                    tenant_runner.runner.state["is_transitioning"] = False
                    tenant_runner.runner.state["status_message"] = "Simulation running"
                    logger.debug(f"Reset is_transitioning=False, is_starting={tenant_runner.runner.state['is_starting']}")
                    logger.info("Simulation started successfully")
                    SIMULATION_START_COUNTER.inc()
                    SIMULATION_STATUS_GAUGE.set(1)
                except Exception as e:
                    logger.error(f"Error during background setup: {e}")
                    tenant_runner.runner.state["is_running"] = False
                    tenant_runner.runner.state["is_transitioning"] = False
                    tenant_runner.runner.state["is_starting"] = False
                    tenant_runner.runner.state["status_message"] = f"Start failed: {str(e)}"
                finally:
                    # Reset tenant context for this thread, if set
                    try:
                        if '_tenant_token' in locals() and _tenant_token is not None:
                            CURRENT_TENANT_ID.reset(_tenant_token)
                    except Exception:
                        pass

            threading.Thread(target=_bg_heavy_setup, daemon=True).start()

            # Return immediately; background thread will complete setup and start simulation
            return {
                "success": True,
                "message": "Starting simulation...",
                "session_id": str(session_id),
            }
        except Exception as e:
            logger.error(f"Error during simulation setup: {str(e)}")
            tenant_runner.runner.state["is_running"] = False
            tenant_runner.runner.state["is_stopping"] = False  # Reset stopping flag on error
            tenant_runner.runner.state["is_transitioning"] = False
            tenant_runner.runner.state["is_starting"] = False  # Clear starting flag on error
            cleanup_resources()
            # Surface error to client
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Error in start_simulation: {str(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        # Best effort: nothing else to do; per-tenant runner will be reset by caller
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/stop")
async def stop_simulation(request: Request, current_user: dict = Depends(get_current_user)):
    """Stop the current simulation with improved reliability"""
    try:
        # Enforce tenant scoping: only allow the tenant that started the simulation to control it
        effective_tid: Optional[int] = None
        if request is not None:
            header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
            if header_tid:
                try:
                    effective_tid = int(header_tid)
                except ValueError:
                    effective_tid = None
        tenant_runner = registry.get(effective_tid) if effective_tid is not None else None
        if tenant_runner is None:
            return {"success": True, "message": "Simulation is not running"}
        if tenant_runner.runner.state.get("tenant_id") is not None and effective_tid is not None:
            if int(tenant_runner.runner.state.get("tenant_id")) != int(effective_tid):
                raise HTTPException(status_code=403, detail="Operation not permitted for this tenant")

        logger.info("================================")
        logger.info("Stopping simulation")
        logger.info("================================")
        
        # Track metrics
        SIMULATION_STOP_COUNTER.inc()
        SIMULATION_STATUS_GAUGE.set(0)  # Stopped

        # Check if simulation is actually running
        if not tenant_runner.runner.state.get("is_running"):
            logger.debug("Simulation is not running, returning success")
            return {"success": True, "message": "Simulation is not running"}
        
        # Synchronize the two state objects immediately
        tenant_runner.runner.state["is_running"] = False      # tell WebSocket on next tick
        tenant_runner.runner.state["is_stopping"] = True      # new explicit flag

        if hasattr(tenant_runner.runner, "app") and tenant_runner.runner.app:
            tenant_runner.runner.app.state.is_running = False  # halt frame producer
        try:
            current_scenario = tenant_runner.runner.state.get("current_scenario")
            
            # Record scenario result
            if current_scenario:
                record_scenario_result(
                    tenant_runner.runner,
                    current_scenario,
                    "Failed",
                    "Stopped",
                    datetime.now() - tenant_runner.runner.state["scenario_start_time"],
                )

            # Start cleanup in a background thread (non-blocking per-tenant stop)
            if hasattr(tenant_runner.runner, "app") and tenant_runner.runner.app:
                import threading as _t
                app_ref = tenant_runner.runner.app
                def _bg_cleanup():
                    try:
                        if hasattr(app_ref, "is_cleanup_complete"):
                            app_ref.is_cleanup_complete = False
                        if hasattr(app_ref, "state"):
                            app_ref.state.is_running = False
                        if hasattr(app_ref, "cleanup"):
                            app_ref.cleanup()
                    except Exception as e:
                        logger.error(f"Background cleanup error (tenant {effective_tid}): {e}")
                _t.Thread(target=_bg_cleanup, daemon=True).start()
            generate_final_report(tenant_runner.runner)
        except Exception as e:
            logger.error(f"Error during simulation stop process: {str(e)}")
            # Continue with cleanup even if there's an error

        finally:
            # Always reset simulation flags (do not clear tenant binding here)
            tenant_runner.runner.state["is_running"] = False
            tenant_runner.runner.state["is_stopping"] = False
            tenant_runner.runner.state["is_transitioning"] = False
            tenant_runner.runner.state["is_skipping"] = False
            
            logger.debug("Simulation state reset completed")

        logger.info("Simulation stopped")
        return {"success": True, "message": "Simulation stopped successfully"}
        
    except Exception as e:
        logger.error(f"Error stopping simulation: {str(e)}")
        # Ensure state is reset on error
        tenant_runner.runner.state["is_running"] = False
        tenant_runner.runner.state["is_stopping"] = False  # Reset stopping flag on error
        tenant_runner.runner.state["is_transitioning"] = False
        tenant_runner.runner.state["is_skipping"] = False  # Reset skipping flag on error
        raise HTTPException(status_code=500, detail=str(e))


# --- OPTIMIZATION: WebSocket video frame sending, only send if frame is new ---
@app.websocket("/ws/simulation-view")
async def websocket_endpoint(websocket: WebSocket):
    try:
        # Authenticate and scope by tenant via query params
        query = websocket.query_params
        token_q = query.get("token")
        q_tid = query.get("tenant_id")
        conn_tenant_id: Optional[int] = None
        if q_tid is not None:
            try:
                conn_tenant_id = int(q_tid)
            except ValueError:
                conn_tenant_id = None
        jwt_payload = None
        if token_q:
            try:
                jwt_payload = verify_jwt_token(token_q)
            except Exception:
                jwt_payload = None
        if conn_tenant_id is None and isinstance(jwt_payload, dict):
            try:
                claim_tid = jwt_payload.get("tenant_id")
                if claim_tid is not None:
                    conn_tenant_id = int(claim_tid)
            except Exception:
                conn_tenant_id = None

        await websocket.accept()

        # Require tenant scoping on WebSocket to prevent cross-tenant effects
        if conn_tenant_id is None:
            try:
                await websocket.send_json({
                    "type": "status",
                    "is_running": False,
                    "is_starting": False,
                    "is_stopping": False,
                    "is_skipping": False,
                    "current_scenario": None,
                    "scenario_index": 0,
                    "total_scenarios": 0,
                    "is_transitioning": False,
                    "status_message": "Tenant context required",
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception:
                pass
            await websocket.close(code=1008)
            return

        # Track metrics
        WEBSOCKET_CONNECTIONS_COUNTER.inc()
        ACTIVE_WEBSOCKET_CONNECTIONS_GAUGE.inc()
        logger.debug("WebSocket connection established")
        last_sent_state = None
        last_frame_obj = [None]
        async def send_video_frames():
            loop = asyncio.get_running_loop()
            last_send_ts = 0.0
            last_hud_ts = 0.0
            # Per-connection FPS limit (env-configurable); default disabled (0 = no throttle)
            try:
                max_fps = float(os.getenv("WEB_VIDEO_MAX_FPS", "0"))
            except Exception:
                max_fps = 0.0
            # When max_fps <= 0, disable throttling entirely
            min_interval = 1.0 / max_fps if max_fps > 0 else 0.0
            while True:
                try:
                    state = None
                    app = None
                    tr = registry.get(conn_tenant_id)
                    if tr is not None:
                        state = tr.runner.state
                        app = getattr(tr.runner, 'app', None)
                    # Enforce tenant: only stream frames if WS tenant matches runner state tenant (when set)
                    # Keep streaming during skip/transition; only stop when actually stopping
                    if (app and getattr(app, 'display_manager', None) and state and
                        (state.get("tenant_id") is None or conn_tenant_id is None or int(state.get("tenant_id")) == int(conn_tenant_id)) and
                        not state.get("is_stopping", False)):
                        frame = app.display_manager.get_current_frame()
                        if frame is not None:
                            # Dedupe by object identity to avoid expensive hashing of raw bytes
                            if frame is not last_frame_obj[0]:
                                try:
                                    # Offload JPEG encoding to threadpool to prevent event-loop blocking
                                    # Apply moderate JPEG quality to reduce CPU
                                    ok, buffer = await loop.run_in_executor(
                                        None,
                                        functools.partial(cv2.imencode, '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                                    )
                                except Exception as e:
                                    logger.error(f"Error encoding video frame: {e}")
                                    await asyncio.sleep(0.0167)
                                    continue
                                if not ok:
                                    await asyncio.sleep(0.0167)
                                    continue
                                # Throttle send to avoid saturating event loop/CPU
                                now = time.time()
                                if (now - last_send_ts) >= min_interval:
                                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                    try:
                                        await websocket.send_text(frame_base64)
                                        last_frame_obj[0] = frame
                                        last_send_ts = now
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
                            # Send HUD roughly at 5 Hz
                            try:
                                if hasattr(app, 'get_hud_payload'):
                                    now2 = time.time()
                                    if (now2 - last_hud_ts) >= 0.2:
                                        hud = app.get_hud_payload()
                                        if isinstance(hud, dict):
                                            await websocket.send_json({"type": "hud", "payload": hud})
                                        last_hud_ts = now2
                            except Exception:
                                pass
                    await asyncio.sleep(0.0167)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.critical(f"Uncaught exception in send_video_frames: {e}", exc_info=True)
                    break
        video_task = asyncio.create_task(send_video_frames())
        try:
            while True:
                state = None
                tr = registry.get(conn_tenant_id)
                if tr is not None:
                    state = tr.runner.state
                    # Debug: Log state changes for this tenant
                    if state and (state.get("is_skipping") or state.get("is_transitioning") or state.get("is_stopping")):
                        logger.debug(f"WebSocket state update for tenant {conn_tenant_id}: is_skipping={state.get('is_skipping')}, is_transitioning={state.get('is_transitioning')}, is_stopping={state.get('is_stopping')}")
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
                    "error": None,
                    "timestamp": datetime.now().isoformat(),
                }
                if state:
                    try:
                        # If tenant mismatch, inform client and close
                        if state.get("tenant_id") is not None and conn_tenant_id is not None and int(state.get("tenant_id")) != int(conn_tenant_id):
                            await websocket.send_json({
                                "type": "status",
                                "is_running": False,
                                "is_starting": False,
                                "is_stopping": False,
                                "is_skipping": False,
                                "current_scenario": None,
                                "scenario_index": 0,
                                "total_scenarios": 0,
                                "is_transitioning": False,
                                "status_message": "Not authorized for this tenant",
                                "error": None,
                                "timestamp": datetime.now().isoformat(),
                            })
                            await websocket.close(code=1008)
                            break
                        # Prefer backend-provided status_message when available
                        status_message = state.get("status_message") or "Ready to Start"
                        if state["is_starting"] and not state.get("status_message"):
                            status_message = "Hang on,\nLoading Simulation..."
                        elif state["is_stopping"] and not state.get("status_message"):
                            status_message = "Stopping simulation..."
                        elif state["is_skipping"]:
                            current_index = state.get("current_scenario_index", 0)
                            total_scenarios = len(state.get("scenarios_to_run", []))
                            # Prefer backend-provided message if present
                            if state.get("status_message"):
                                status_message = state["status_message"]
                            else:
                                if current_index + 1 < total_scenarios:
                                    next_scenario = state["scenarios_to_run"][current_index + 1]
                                    status_message = f"Skipping to: {next_scenario} ({current_index + 2}/{total_scenarios})"
                                else:
                                    status_message = f"Skipping scenario {current_index + 1}/{total_scenarios}...\nSimulation complete"
                        elif state["is_running"]:
                            # Prioritize starting state over transitioning state to show correct status during startup
                            if state["is_starting"]:
                                status_message = state.get("status_message") or "Hang on,\nLoading Simulation..."
                            # elif state["is_transitioning"]:
                            #     # Don't show "Transitioning between scenarios..." - just show the current scenario or default message
                            #     current = state.get("current_scenario")
                            #     if current:
                            #         status_message = f"Running: {current}"
                            #     else:
                            #         status_message = state.get("status_message") or "Simulation running"
                            else:
                                # Prefer showing the running scenario name with index/total
                                current = state.get("current_scenario")
                                idx = state.get("current_scenario_index", 0) + 1
                                tot = len(state.get("scenarios_to_run", []))
                                if current:
                                    status_message = f"Running: {current} {idx}/{tot}"
                                else:
                                    status_message = state.get("status_message") or "Simulation running"
                        state_info.update({
                            "is_running": state["is_running"],
                            "is_starting": state["is_starting"],
                            "is_stopping": state["is_stopping"],
                            "is_skipping": state["is_skipping"],
                            "current_scenario": state["current_scenario"],
                            "controller_type": state.get("controller_type", "autopilot"),
                            "scenario_index": state["current_scenario_index"] + 1,
                            "total_scenarios": len(state["scenarios_to_run"]),
                            "is_transitioning": state["is_transitioning"],
                            "status_message": status_message,
                            "error": state.get("error"),
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


@app.websocket("/ws/control")
async def control_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for receiving control commands from web interface"""
    try:
        # Authenticate and scope by tenant via query params
        query = websocket.query_params
        token_q = query.get("token")
        q_tid = query.get("tenant_id")
        conn_tenant_id: Optional[int] = None
        if q_tid is not None:
            try:
                conn_tenant_id = int(q_tid)
            except ValueError:
                conn_tenant_id = None
        jwt_payload = None
        if token_q:
            try:
                jwt_payload = verify_jwt_token(token_q)
            except Exception:
                jwt_payload = None
        if conn_tenant_id is None and isinstance(jwt_payload, dict):
            try:
                claim_tid = jwt_payload.get("tenant_id")
                if claim_tid is not None:
                    conn_tenant_id = int(claim_tid)
            except Exception:
                conn_tenant_id = None

        await websocket.accept()

        # Require tenant scoping on WebSocket to prevent cross-tenant effects
        if conn_tenant_id is None:
            await websocket.close(code=1008)
            return

        logger.debug(f"Control WebSocket connection established for tenant {conn_tenant_id}")
        
        while True:
            try:
                # Receive control command from frontend
                data = await websocket.receive_json()
                
                # Validate command structure
                if not isinstance(data, dict):
                    continue
                
                # Extract control data
                control_data = data.get("control", {})
                controller_type = data.get("controller_type", "web_keyboard")
                
                # Update controller command if runner exists and simulation is running
                tr = registry.get(conn_tenant_id)
                if tr and hasattr(tr.runner, 'app') and tr.runner.app:
                    app = tr.runner.app
                    # Check if simulation is still running
                    if hasattr(tr.runner, 'state') and tr.runner.state.get("is_running", False):
                        if hasattr(app, 'vehicle_controller') and app.vehicle_controller:
                            vehicle_controller = app.vehicle_controller
                            if hasattr(vehicle_controller, '_strategy') and vehicle_controller._strategy:
                                strategy = vehicle_controller._strategy
                                if hasattr(strategy, 'update_command'):
                                    # Create WebControlCommand from data
                                    from carla_simulator.control.web_controller import WebControlCommand
                                    command = WebControlCommand(
                                        throttle=float(control_data.get("throttle", 0.0)),
                                        brake=float(control_data.get("brake", 0.0)),
                                        steer=float(control_data.get("steer", 0.0)),
                                        hand_brake=bool(control_data.get("hand_brake", False)),
                                        reverse=bool(control_data.get("reverse", False)),
                                        manual_gear_shift=bool(control_data.get("manual_gear_shift", False)),
                                        gear=int(control_data.get("gear", 1)),
                                        quit=bool(control_data.get("quit", False)),
                                        gamepad_index=int(control_data.get("gamepad_index", 0))
                                    )
                                    
                                    # Handle multiple gamepads for WebGamepadController
                                    if controller_type == "web_gamepad" and hasattr(strategy, 'update_gamepad_command'):
                                        strategy.update_gamepad_command(command.gamepad_index, command)
                                    else:
                                        strategy.update_command(command)
                                    
                                    logger.debug(f"Updated {controller_type} command: {command}")
                    else:
                        # Simulation is not running, close connection gracefully
                        logger.debug("Simulation stopped, closing control WebSocket")
                        await websocket.close(code=1000, reason="Simulation stopped")
                        break
                
            except asyncio.CancelledError:
                break
            except websockets.exceptions.ConnectionClosed:
                logger.debug("Control WebSocket connection closed by client")
                break
            except Exception as e:
                logger.error(f"Error processing control command: {e}")
                # Don't break on general errors, just log them
                continue
                
    except asyncio.CancelledError:
        return
    except Exception as e:
        logger.critical(f"Uncaught exception in control websocket endpoint: {e}", exc_info=True)
    finally:
        logger.debug(f"Control WebSocket connection closed for tenant {conn_tenant_id}")


@app.get("/api/reports")
async def list_reports(tenant_id: Optional[int] = None):
    """List reports strictly per-tenant (DB only)."""
    try:
        # Resolve tenant strictly: header/context > query > env
        effective_tenant_id: Optional[int] = None
        ctx_tid = CURRENT_TENANT_ID.get()
        if ctx_tid is not None:
            effective_tenant_id = int(ctx_tid)
        elif tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None
        if effective_tenant_id is None:
            raise HTTPException(status_code=400, detail="Tenant context required")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Error listing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{ref}")
async def get_report(ref: str, tenant_id: Optional[int] = None):
    """Serve a specific HTML report strictly from DB for the tenant."""
    try:
        effective_tenant_id: Optional[int] = None
        ctx_tid = CURRENT_TENANT_ID.get()
        if ctx_tid is not None:
            effective_tenant_id = int(ctx_tid)
        elif tenant_id is not None:
            effective_tenant_id = tenant_id
        else:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None
        if effective_tenant_id is None:
            raise HTTPException(status_code=400, detail="Tenant context required")
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
    except Exception as e:
        logger.error(f"Error serving report {ref}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{ref}")
async def delete_report(ref: str, tenant_id: Optional[int] = None):
    """Delete a specific HTML report strictly from DB for the tenant."""
    effective_tenant_id: Optional[int] = None
    ctx_tid = CURRENT_TENANT_ID.get()
    if ctx_tid is not None:
        effective_tenant_id = int(ctx_tid)
    elif tenant_id is not None:
        effective_tenant_id = tenant_id
    else:
        env_tid = os.getenv("CONFIG_TENANT_ID")
        if env_tid is not None:
            try:
                effective_tenant_id = int(env_tid)
            except ValueError:
                effective_tenant_id = None

    if effective_tenant_id is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
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


def _web_file_logging_enabled() -> bool:
    return os.getenv("WEB_FILE_LOGS_ENABLED", "false").lower() == "true"


@app.post("/api/logs/directory")
async def create_logs_directory():
    """Create logs directory if it doesn't exist"""
    try:
        if not _web_file_logging_enabled():
            return {"message": "Web file logging disabled"}
        logs_dir = Path(get_project_root()) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return {"message": "Logs directory created/verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/file")
async def create_log_file(request: LogFileRequest):
    """Create a new log file"""
    try:
        if not _web_file_logging_enabled():
            return {"message": "Web file logging disabled"}
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
        if not _web_file_logging_enabled():
            return {"success": True, "message": "Web file logging disabled"}
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
@app.post("/api/carla/metadata")
async def upsert_carla_metadata(payload: dict):
    """Store CARLA catalogs (maps, blueprints, enums) by version into DB."""
    try:
        version = payload.get("version") or payload.get("carla_version")
        data = payload.get("data") or payload
        if not version or not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="version and data required")
        dbm = DatabaseManager()
        ok = CarlaMetadata.upsert(dbm, str(version), data)
        if not ok:
            raise HTTPException(status_code=500, detail="Failed to store metadata")
        return {"message": "Metadata stored", "version": version}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/carla/metadata/{version}")
async def get_carla_metadata(version: str):
    try:
        dbm = DatabaseManager()
        row = CarlaMetadata.get_by_version(dbm, version)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reset")
async def reset_config(request: Request, payload: ResetConfigRequest):
    """Reset configuration to defaults for a tenant from DB metadata."""
    try:
        # Determine effective tenant id: header > body > env
        effective_tenant_id: Optional[int] = None
        header_tid = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-Id")
        if header_tid:
            try:
                effective_tenant_id = int(header_tid)
            except ValueError:
                effective_tenant_id = None
        if effective_tenant_id is None and payload.tenant_id is not None:
            effective_tenant_id = payload.tenant_id
        if effective_tenant_id is None:
            env_tid = os.getenv("CONFIG_TENANT_ID")
            if env_tid is not None:
                try:
                    effective_tenant_id = int(env_tid)
                except ValueError:
                    effective_tenant_id = None

        # Load defaults from DB metadata
        dbm = DatabaseManager()
        defaults = dbm.get_carla_metadata("simulation_defaults") or {}
        if not isinstance(defaults, dict) or len(defaults) == 0:
            raise HTTPException(status_code=400, detail="No defaults configured in DB (simulation_defaults)")

        if effective_tenant_id is not None:
            result = TenantConfig.upsert_active_config(dbm, effective_tenant_id, defaults)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to reset tenant config")
            return {"message": "Configuration reset to defaults (DB)", "tenant_id": effective_tenant_id, "config": defaults}
        
        # No tenant context
        raise HTTPException(status_code=400, detail="Tenant context required (CONFIG_TENANT_ID or ?tenant_id=) for reset")
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
        # Determine default tenant for this user (per-user tenant)
        default_tenant_id: Optional[int] = None
        try:
            from carla_simulator.database.models import Tenant
            slug = f"user-{user['id']}"
            tenant = Tenant.get_by_slug(db, slug)
            if not tenant:
                tenant = Tenant.create_if_not_exists(db, name=f"User {user['username']}", slug=slug, is_active=True)
            if tenant:
                default_tenant_id = tenant["id"]
        except Exception:
            default_tenant_id = None

        # Create JWT token
        token_data = {
            "sub": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "is_admin": user["is_admin"],
            "tenant_id": default_tenant_id,
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
                "is_admin": user["is_admin"],
                "tenant_id": default_tenant_id,
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

        # Seed default config for this user by creating a per-user tenant and copying from global defaults/metadata
        try:
            # Create a per-user tenant
            slug = f"user-{new_user['id']}"
            name = f"User {new_user['username']}"
            tenant = Tenant.create_if_not_exists(db, name=name, slug=slug, is_active=True)
            if tenant and isinstance(tenant, dict):
                user_tid = int(tenant["id"])
                # Prefer global-default tenant config
                g = Tenant.create_if_not_exists(db, name="Global Default", slug="global-default", is_active=True)
                g_tid = int(g["id"]) if isinstance(g, dict) else None
                defaults = None
                if g_tid is not None:
                    defaults = TenantConfig.get_active_config(db, g_tid)
                if not defaults:
                    # Fallback to metadata
                    defaults = db.get_carla_metadata("simulation_defaults") or {}
                if isinstance(defaults, dict) and len(defaults) > 0:
                    TenantConfig.upsert_active_config(db, user_tid, defaults)
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
        
        # Determine user's default tenant id (if not present in JWT)
        tenant_id = current_user.get("tenant_id")
        if tenant_id is None:
            try:
                from carla_simulator.database.models import Tenant
                slug = f"user-{user['id']}"
                tenant = Tenant.get_by_slug(db, slug)
                if tenant:
                    tenant_id = tenant["id"]
            except Exception:
                tenant_id = None

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_admin": user["is_admin"],
            "created_at": user["created_at"],
            "last_login": user["last_login"],
            "tenant_id": tenant_id,
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


# ---- Admin endpoints for CARLA pool and runners ----
@app.get("/api/carla/pool/status")
async def get_carla_pool_status(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        return carla_pool.status()
    except Exception as e:
        logger.error(f"Error getting CARLA pool status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/carla/pool/housekeeping")
async def run_carla_pool_housekeeping(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        carla_pool.housekeeping()
        return {"message": "Housekeeping executed"}
    except Exception as e:
        logger.error(f"Error running housekeeping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/runners")
async def list_runners(current_user: dict = Depends(get_current_user)):
    require_admin(current_user)
    try:
        data = []
        try:
            data.append({
                "tenant_id": None,
                "is_running": runner.state.get("is_running"),
                "current_scenario": runner.state.get("current_scenario"),
                "scenarios_to_run": runner.state.get("scenarios_to_run"),
            })
        except Exception:
            pass
        try:
            for tid, tr in registry._tenant_to_runner.items():  # type: ignore[attr-defined]
                r = tr.runner
                rs = getattr(r, 'state', {})
                data.append({
                    "tenant_id": tid,
                    "is_running": bool(rs.get("is_running")),
                    "current_scenario": rs.get("current_scenario"),
                    "scenarios_to_run": rs.get("scenarios_to_run"),
                })
        except Exception:
            pass
        return {"runners": data}
    except Exception as e:
        logger.error(f"Error listing runners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        # Load host/port from environment variables (fallback to defaults if missing)
        cfg_host, cfg_port = "0.0.0.0", 8000
        cfg_path = get_config_path("simulation.yaml")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                if cfg_path.lower().endswith('.json'):
                    import json as _json
                    cfg = _json.load(f) or {}
                else:
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
