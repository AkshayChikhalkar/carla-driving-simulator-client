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
            "test_scenario1",
            "test_scenario2",
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
    assert isinstance(data, list)
    assert len(data) > 0
    assert data == ["test_scenario1", "test_scenario2"]


def test_get_config(client):
    """Test getting simulation configuration."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "target" in data
    assert "vehicle" in data
    assert "simulation" in data


def test_update_config(client):
    """Test updating simulation configuration."""
    test_config = {
        "target": {"distance": 100.0},
        "vehicle": {"model": "vehicle.tesla.model3"},
        "simulation": {"fps": 30},
    }
    response = client.post("/api/config", json={"config_data": test_config})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Configuration updated successfully"


def test_simulation_control(client, mock_carla):
    """Test simulation control endpoints."""
    # Test starting simulation
    start_response = client.post(
        "/api/simulation/start",
        json={"scenarios": ["test_scenario1"], "debug": True, "report": True},
    )
    assert start_response.status_code == 200
    mock_carla.run_single_scenario.assert_called_once()

    # Test stopping simulation
    stop_response = client.post("/api/simulation/stop")
    assert stop_response.status_code == 200
    assert mock_carla.state["is_running"] == False


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
    reports = list_response.json()
    assert isinstance(reports, list)

    # Get specific report (if exists)
    if reports:
        report_response = client.get(f"/api/reports/{reports[0]}")
        assert report_response.status_code in [200, 404]


def test_logs_endpoints(client):
    """Test log-related endpoints."""
    # List logs
    list_response = client.get("/api/logs")
    assert list_response.status_code == 200
    logs = list_response.json()
    assert isinstance(logs, list)

    # Get specific log (if exists)
    if logs:
        log_response = client.get(f"/api/logs/{logs[0]}")
        assert log_response.status_code in [200, 404]


def test_websocket_connection(client, mock_carla):
    """Test WebSocket connection for simulation view."""
    with client.websocket_connect("/ws/simulation-view") as websocket:
        # Test if connection is established
        assert websocket.client_state.value == 1  # 1 = CONNECTED

        # Test sending a message
        websocket.send_text("test message")

        # Test receiving a message
        response = websocket.receive_text()
        assert response is not None
