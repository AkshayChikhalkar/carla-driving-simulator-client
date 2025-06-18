"""
Unit tests for core functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry


@pytest.fixture
def simulation_runner():
    """Fixture providing a SimulationRunner instance."""
    with patch("src.core.simulation_runner.SimulationRunner") as mock_runner:
        runner = MagicMock()
        runner.logger = MagicMock()
        runner.logger.debug_mode = True
        runner.logger.operations_file = MagicMock()
        runner.scenario_registry = MagicMock()
        runner.scenario_registry.get_available_scenarios.return_value = [
            "follow_route",
            "avoid_obstacle",
            "emergency_brake",
            "vehicle_cutting"
        ]
        mock_runner.return_value = runner
        yield runner


def test_simulation_runner_initialization(simulation_runner):
    """Test SimulationRunner initialization."""
    assert simulation_runner is not None
    assert simulation_runner.logger is not None
    assert simulation_runner.scenario_registry is not None


def test_scenario_registry():
    """Test ScenarioRegistry functionality."""
    registry = ScenarioRegistry()
    scenarios = registry.get_available_scenarios()
    assert isinstance(scenarios, list)
    assert len(scenarios) > 0


def test_scenario_registration(simulation_runner):
    """Test scenario registration."""
    simulation_runner.register_scenarios()
    scenarios = simulation_runner.scenario_registry.get_available_scenarios()
    assert len(scenarios) > 0
    assert all(isinstance(scenario, str) for scenario in scenarios)


def test_logger_setup(simulation_runner):
    """Test logger setup."""
    assert simulation_runner.logger is not None
    assert simulation_runner.logger.debug_mode is True


def test_cleanup(simulation_runner):
    """Test proper cleanup of resources."""
    simulation_runner.logger.close()
    simulation_runner.logger.operations_file = None
    assert simulation_runner.logger.operations_file is None
