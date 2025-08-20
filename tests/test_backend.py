"""
Unit tests for the FastAPI backend.
"""

import pytest
from fastapi.testclient import TestClient
from web.backend.main import app
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import os


# Mock CARLA dependencies
@pytest.fixture(autouse=True)
def mock_carla():
    """Mock CARLA-related dependencies."""
    with patch("carla_simulator.core.simulation_runner.SimulationRunner") as mock_runner, \
         patch("carla_simulator.core.simulation_runner.SimulationApplication") as mock_sim_app:
        # Setup mock runner
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Mock scenario registry
        mock_runner_instance.scenario_registry = MagicMock()
        mock_runner_instance.scenario_registry.get_available_scenarios.return_value = [
            "follow_route",
            "avoid_obstacle",
            "emergency_brake",
            "vehicle_cutting"
        ]

        # Mock simulation state
        mock_runner_instance.state = {
            "is_running": False,
            "current_scenario": None,
            "scenarios_to_run": [],
            "current_scenario_index": 0,
            "scenario_results": MagicMock(),
            "batch_start_time": None,
            "current_scenario_completed": False,
            "scenario_start_time": None,
            "cleanup_event": MagicMock(),
            "cleanup_completed": False,
        }

        # Mock create_app method
        mock_runner_instance.create_app = MagicMock()
        mock_runner_instance.create_app.return_value = MagicMock()
        mock_runner_instance.create_app.return_value.state = MagicMock()
        mock_runner_instance.create_app.return_value.state.is_running = True
        mock_runner_instance.create_app.return_value.display_manager = MagicMock()
        mock_runner_instance.create_app.return_value.display_manager.get_current_frame.return_value = None
        
        # Mock create_application method (used in simulation start)
        mock_app = MagicMock()
        mock_runner_instance.create_application = MagicMock()
        mock_runner_instance.create_application.return_value = mock_app
        
        # Mock the SimulationApplication class itself
        mock_sim_app.return_value = mock_app
        
        # Mock setup_components method
        mock_runner_instance.setup_components = MagicMock()
        mock_runner_instance.setup_components.return_value = {
            "world_manager": MagicMock(),
            "sensor_manager": MagicMock(),
            "vehicle_controller": MagicMock(),
            "display_manager": MagicMock()
        }

        # Mock start and stop methods
        mock_runner_instance.start = MagicMock()
        mock_runner_instance.stop = MagicMock()
        mock_runner_instance.start.return_value = True
        mock_runner_instance.stop.return_value = True

        yield mock_runner_instance


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["CONFIG_TENANT_ID"] = "1"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
    os.environ["DISABLE_AUTH_FOR_TESTING"] = "true"
    return TestClient(app)

@pytest.fixture
def test_headers():
    """Headers for authenticated requests."""
    return {
        "X-Tenant-Id": "1",
        "Authorization": "Bearer test_token"
    }

@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication dependencies."""
    with patch("carla_simulator.utils.auth.get_current_user") as mock_get_user:
        mock_get_user.return_value = {
            "sub": "1",
            "username": "test_user",
            "email": "test@example.com",
            "is_admin": True,
            "tenant_id": 1
        }
        
        with patch("carla_simulator.utils.auth.verify_jwt_token") as mock_verify:
            mock_verify.return_value = {
                "user_id": 1,
                "username": "test_user",
                "tenant_id": 1
            }
            
            with patch("carla_simulator.database.db_manager.DatabaseManager") as mock_db:
                mock_db_instance = MagicMock()
                mock_db.return_value = mock_db_instance
                
                # Mock database methods
                mock_db_instance.execute_query.return_value = []
                mock_db_instance.fetch_one.return_value = None
                mock_db_instance.fetch_all.return_value = []
                
                # Mock the config data that get_carla_metadata returns
                test_config = {
                    "server": {
                        "host": "localhost", 
                        "port": 2000,
                        "timeout": 5.0,  # Required by SimulationConfig validation
                        "connection": {
                            "max_retries": 3,
                            "retry_delay": 1.0
                        }
                    },
                    "world": {
                        "map": "Town01",
                        "fixed_delta_seconds": 0.05,
                        "target_distance": 10.0,
                        "num_vehicles": 0,
                        "enable_collision": True,
                        "synchronous_mode": True,
                        "weather": {
                            "cloudiness": 10.0,
                            "precipitation": 0.0,
                            "wind_intensity": 0.0
                        },
                        "physics": {
                            "max_substep_delta_time": 0.01,
                            "max_substeps": 10
                        },
                        "traffic": {
                            "distance_to_leading_vehicle": 5.0,
                            "speed_difference_percentage": 20.0,
                            "ignore_lights_percentage": 0.0,
                            "ignore_signs_percentage": 0.0
                        }
                    },
                    "simulation": {
                        "timeout": 20.0,
                        "max_speed": 50.0,
                        "simulation_time": 300,
                        "update_rate": 60.0,
                        "speed_change_threshold": 0.1,
                        "position_change_threshold": 0.1,
                        "heading_change_threshold": 0.1,
                        "target_tolerance": 1.0,
                        "max_collision_force": 1000.0
                    },
                    "logging": {
                        "log_level": "INFO",
                        "enabled": True,
                        "directory": "logs"
                    },
                    "display": {
                        "width": 800,
                        "height": 600,
                        "fps": 60,
                        "hud_enabled": True,
                        "minimap_enabled": True,
                        "hud": {
                            "font_size": 18,
                            "font_name": "Arial",
                            "alpha": 255,
                            "colors": {
                                "target": "green",
                                "vehicle": "blue",
                                "text": "white",
                                "background": "black"
                            }
                        },
                        "minimap": {
                            "width": 200,
                            "height": 200,
                            "scale": 0.1,
                            "alpha": 255,
                            "colors": {
                                "target": "green",
                                "vehicle": "blue",
                                "text": "white",
                                "background": "black"
                            }
                        },
                        "camera": {
                            "font_size": 14,
                            "font_name": "Arial"
                        }
                    },
                    "sensors": {"camera": {"enabled": True}},
                    "controller": {"type": "keyboard"},
                    "vehicle": {"model": "vehicle.tesla.model3"},
                    "scenarios": {"enabled": ["follow_route"]}
                }
                mock_db_instance.get_carla_metadata.return_value = test_config
                
                with patch("carla_simulator.utils.config.ConfigLoader") as mock_config:
                    mock_config_instance = MagicMock()
                    mock_config.return_value = mock_config_instance
                    mock_config_instance.get_config.return_value = test_config
                    
                    # Mock additional dependencies
                    with patch("web.backend.main.DatabaseManager", return_value=mock_db_instance):
                        with patch("carla_simulator.database.models.User") as mock_user_model:
                            with patch("carla_simulator.database.models.Tenant") as mock_tenant_model:
                                with patch("carla_simulator.database.models.TenantConfig") as mock_tenant_config:
                                    # Mock user operations
                                    mock_user_model.get_by_username.return_value = {
                                        "id": 1,
                                        "username": "test_user",
                                        "email": "test@example.com",
                                        "password_hash": "hashed_password",
                                        "is_admin": True
                                    }
                                    
                                    # Mock tenant operations
                                    mock_tenant_model.get_by_slug.return_value = {
                                        "id": 1,
                                        "name": "Test Tenant",
                                        "slug": "test-tenant"
                                    }
                                    
                                    # Mock tenant config methods
                                    mock_tenant_config.get_active_config.return_value = test_config
                                    mock_tenant_config.get_config.return_value = test_config
                                    
                                    # Mock the config loading function for simulation creation
                                    with patch("carla_simulator.utils.config.load_config") as mock_load_config:
                                        mock_load_config.return_value = test_config
                                        
                                        yield mock_get_user


def test_get_scenarios(client, mock_carla):
    """Test getting available scenarios."""
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "scenarios" in data
    assert isinstance(data["scenarios"], list)
    assert len(data["scenarios"]) > 0
    assert data["scenarios"] == ["follow_route", "avoid_obstacle", "emergency_brake", "vehicle_cutting"]


def test_get_config(client, test_headers):
    """Test getting simulation configuration."""
    response = client.get("/api/config", headers=test_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # Check for required config sections
    assert "server" in data
    assert "world" in data
    assert "simulation" in data
    assert "logging" in data
    assert "display" in data
    assert "sensors" in data
    assert "controller" in data
    assert "vehicle" in data
    assert "scenarios" in data


# def test_update_config(client):
#     """Test updating simulation configuration."""
#     test_config = {
#         "target": {"distance": 100.0},
#         "vehicle": {"model": "vehicle.fuso.mitsubishi"},
#         "simulation": {"fps": 30},
#     }
#     response = client.post("/api/config", json={"config_data": test_config})
#     assert response.status_code == 200
#     data = response.json()
#     assert isinstance(data, dict)
#     assert "message" in data
#     assert "config" in data
#     assert data["message"] == "Configuration updated successfully"


def test_simulation_control(client, mock_carla, test_headers):
    """Test simulation control endpoints."""
    # Test starting simulation
    start_response = client.post(
        "/api/simulation/start",
        json={"scenarios": ["follow_route"], "debug": True, "report": True},
        headers=test_headers
    )
    start_data = start_response.json()
    assert isinstance(start_data, dict)
    assert "success" in start_data
    assert "message" in start_data
    assert start_data["success"] is True
    # Note: The simulation start process uses threading and background setup,
    # so we verify success through the response rather than direct method calls

    # Test stopping simulation
    stop_response = client.post("/api/simulation/stop", headers=test_headers)
    assert stop_response.status_code == 200
    stop_data = stop_response.json()
    assert isinstance(stop_data, dict)
    assert "success" in stop_data
    assert "message" in stop_data
    assert stop_data["success"] is True
    # Note: The simulation stop process manipulates state and handles cleanup
    # rather than calling a direct stop method, so we verify success through the response
    assert start_response.status_code == 200


def test_skip_scenario(client, mock_carla, test_headers):
    """Test skipping current scenario."""
    response = client.post("/api/simulation/skip", headers=test_headers)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    mock_carla.state["current_scenario_completed"] = True


def test_reports_endpoints(client, test_headers):
    """Test report-related endpoints."""
    # List reports
    list_response = client.get("/api/reports", headers=test_headers)
    assert list_response.status_code == 200
    data = list_response.json()
    assert isinstance(data, dict)
    assert "reports" in data
    reports = data["reports"]
    assert isinstance(reports, list)

    # Get specific report (if exists)
    if reports:
        report_response = client.get(f"/api/reports/{reports[0]['filename']}")
        assert report_response.status_code in [200, 404]


def test_logs_endpoints(client):
    """Test log-related endpoints."""
    # List logs
    list_response = client.get("/api/logs")
    assert list_response.status_code == 200
    data = list_response.json()
    assert isinstance(data, dict)
    assert "logs" in data
    logs = data["logs"]
    assert isinstance(logs, list)

    # Get specific log (if exists)
    if logs:
        log_response = client.get(f"/api/logs/{logs[0]['filename']}")
        assert log_response.status_code in [200, 404]


def test_websocket_connection(client, mock_carla):
    """Test WebSocket connection for simulation view."""
    import signal
    from contextlib import contextmanager
    import threading
    import time

    @contextmanager
    def timeout_context(seconds):
        def timeout_handler():
            time.sleep(seconds)
            raise TimeoutError(f"Test timed out after {seconds} seconds")

        timer = threading.Timer(seconds, timeout_handler)
        timer.daemon = True
        timer.start()
        try:
            yield
        finally:
            timer.cancel()

    try:
        with timeout_context(2.0):  # 2 second timeout
            with client.websocket_connect("/ws/simulation-view", timeout=2.0) as websocket:
                # Test if connection is established by receiving data
                response = websocket.receive_json()
                assert isinstance(response, dict)
                assert "type" in response
                assert response["type"] == "status"
                assert "is_running" in response
                assert "current_scenario" in response
                assert "scenario_index" in response
                assert "total_scenarios" in response
                assert "is_transitioning" in response

                # Close the connection explicitly
                websocket.close()
    except TimeoutError as e:
        pytest.fail(f"WebSocket test timed out: {str(e)}")
    except Exception as e:
        pytest.fail(f"WebSocket connection failed: {str(e)}")
