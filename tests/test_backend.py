"""
Unit tests for the FastAPI backend.
"""

import pytest
from fastapi.testclient import TestClient
from web.backend.main import app
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


# Mock CARLA dependencies
@pytest.fixture(autouse=True)
def mock_carla():
    """Mock CARLA-related dependencies."""
    with patch("src.core.simulation_runner.SimulationRunner") as mock_runner:
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

        # Mock start and stop methods
        mock_runner_instance.start = MagicMock()
        mock_runner_instance.stop = MagicMock()
        mock_runner_instance.start.return_value = True
        mock_runner_instance.stop.return_value = True

        yield mock_runner_instance


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


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


def test_get_config(client):
    """Test getting simulation configuration."""
    response = client.get("/api/config")
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


def test_simulation_control(client, mock_carla):
    """Test simulation control endpoints."""
    # Test starting simulation
    start_response = client.post(
        "/api/simulation/start",
        json={"scenarios": ["follow_route"], "debug": True, "report": True},
    )
    assert start_response.status_code == 200
    # start_data = start_response.json()
    # assert isinstance(start_data, dict)
    # assert "success" in start_data
    # assert "message" in start_data
    # assert start_data["success"] is True
    # assert mock_carla.start.called

    # # Test stopping simulation
    # stop_response = client.post("/api/simulation/stop")
    # assert stop_response.status_code == 200
    # stop_data = stop_response.json()
    # assert isinstance(stop_data, dict)
    # assert "success" in stop_data
    # assert "message" in stop_data
    # assert stop_data["success"] is True
    # assert mock_carla.stop.called


def test_skip_scenario(client, mock_carla):
    """Test skipping current scenario."""
    response = client.post("/api/simulation/skip")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    mock_carla.state["current_scenario_completed"] = True


def test_reports_endpoints(client):
    """Test report-related endpoints."""
    # List reports
    list_response = client.get("/api/reports")
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


# def test_websocket_connection(client, mock_carla):
#     """Test WebSocket connection for simulation view."""
#     import signal
#     from contextlib import contextmanager
#     import threading
#     import time

#     @contextmanager
#     def timeout_context(seconds):
#         def timeout_handler():
#             time.sleep(seconds)
#             raise TimeoutError(f"Test timed out after {seconds} seconds")

#         timer = threading.Timer(seconds, timeout_handler)
#         timer.daemon = True
#         timer.start()
#         try:
#             yield
#         finally:
#             timer.cancel()

#     try:
#         with timeout_context(2.0):  # 2 second timeout
#             with client.websocket_connect("/ws/simulation-view", timeout=2.0) as websocket:
#                 # Test if connection is established by receiving data
#                 response = websocket.receive_json()
#                 assert isinstance(response, dict)
#                 assert "type" in response
#                 assert response["type"] == "status"
#                 assert "is_running" in response
#                 assert "current_scenario" in response
#                 assert "scenario_index" in response
#                 assert "total_scenarios" in response
#                 assert "is_transitioning" in response

#                 # Close the connection explicitly
#                 websocket.close()
#     except TimeoutError as e:
#         pytest.fail(f"WebSocket test timed out: {str(e)}")
#     except Exception as e:
#         pytest.fail(f"WebSocket connection failed: {str(e)}")
