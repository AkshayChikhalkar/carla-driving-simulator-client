"""
Unit tests for utility modules.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.utils.config import ConfigLoader, SimulationConfig
from src.utils.logging import Logger, SimulationData


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_content = """
    target:
        distance: 500.0
    vehicle:
        model: vehicle.dodge.charger
    simulation:
        fps: 30
    """
    config_file = tmp_path / "simulation_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def config_loader(mock_config_file):
    """Fixture providing a ConfigLoader instance."""
    return ConfigLoader(mock_config_file)


@pytest.fixture
def simulation_logger():
    """Fixture providing a Logger instance."""
    with patch("src.utils.logging.Logger") as mock_logger:
        logger = MagicMock()
        logger.simulation_log = "test_simulation.csv"
        logger.operations_log = "test_operations.log"
        logger.simulation_file = MagicMock()
        logger.operations_file = MagicMock()
        mock_logger.return_value = logger
        yield logger


def test_config_loader_initialization(config_loader, mock_config_file):
    """Test ConfigLoader initialization."""
    assert config_loader.config_path == mock_config_file
    assert config_loader.config is None
    assert config_loader.simulation_config is None


def test_config_loading(config_loader):
    """Test configuration loading from YAML file."""
    config = config_loader.load_config()
    assert isinstance(config, dict)
    assert "target" in config
    assert "vehicle" in config
    assert "simulation" in config


def test_config_validation(config_loader):
    """Test configuration validation."""
    config_loader.load_config()
    assert config_loader.validate_config() is True


def test_simulation_config_creation(config_loader):
    """Test creation of SimulationConfig object."""
    sim_config = config_loader.get_simulation_config()
    assert isinstance(sim_config, SimulationConfig)
    assert sim_config.max_speed is not None
    assert sim_config.simulation_time is not None
    assert sim_config.update_rate is not None
    assert sim_config.speed_change_threshold is not None
    assert sim_config.position_change_threshold is not None
    assert sim_config.heading_change_threshold is not None
    assert sim_config.target_tolerance is not None


def test_simulation_logger_initialization(simulation_logger):
    """Test Logger initialization."""
    assert simulation_logger.simulation_log == "test_simulation.csv"
    assert simulation_logger.operations_log == "test_operations.log"
    assert simulation_logger.simulation_file is not None
    assert simulation_logger.operations_file is not None


def test_simulation_data_logging(simulation_logger):
    """Test logging of simulation data."""
    data = SimulationData(
        elapsed_time=1.0,
        speed=50.0,
        position=(100.0, 200.0, 0.0),
        controls={
            "throttle": 0.5,
            "brake": 0.0,
            "steer": 0.0,
            "hand_brake": False,
            "reverse": False,
            "manual_gear_shift": False,
            "gear": 1
        },
        target_info={
            "distance": 300.0,
            "heading": 45.0,
            "heading_diff": 5.0
        },
        vehicle_state={
            "heading": 40.0,
            "acceleration": 2.0,
            "angular_velocity": 0.1,
            "collision_intensity": 0.0,
            "rotation": (0.0, 40.0, 0.0)
        },
        weather={
            "cloudiness": 0.0,
            "precipitation": 0.0
        },
        traffic_count=5,
        fps=60.0,
        event="NONE",
        event_details=""
    )

    simulation_logger.log_simulation_data(data)
    simulation_logger.log_simulation_data.assert_called_once_with(data)


def test_operation_logging(simulation_logger):
    """Test logging of operational messages."""
    test_message = "Test operation message"
    simulation_logger.log_operation(test_message)
    simulation_logger.log_operation.assert_called_once_with(test_message)


def test_logger_cleanup(simulation_logger):
    """Test proper cleanup of logger resources."""
    simulation_logger.close()
    simulation_logger.close.assert_called_once()


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test files after each test."""
    yield
    for file in ["test_simulation.csv", "test_operations.log"]:
        if os.path.exists(file):
            os.remove(file)
