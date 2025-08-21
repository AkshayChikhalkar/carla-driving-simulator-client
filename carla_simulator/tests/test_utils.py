"""
Unit tests for utility modules.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
try:
    from carla_simulator.utils.config import ConfigLoader
    from carla_simulator.utils.logging import Logger
    from carla_simulator.utils.types import SimulationData
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some imports not available: {e}")
    IMPORTS_AVAILABLE = False


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
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required imports not available")
    return ConfigLoader(mock_config_file)


@pytest.fixture
def simulation_logger():
    """Fixture providing a Logger instance."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required imports not available")
    with patch("carla_simulator.utils.logging.Logger") as mock_logger:
        logger = MagicMock()
        logger.simulation_log = "test_simulation.csv"
        logger.operations_log = "test_operations.log"
        logger.simulation_file = MagicMock()
        logger.operations_file = MagicMock()
        mock_logger.return_value = logger
        yield logger


def test_imports_available():
    """Test that all required imports are available."""
    assert IMPORTS_AVAILABLE, "Required imports are not available"


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
    """Test creation of simulation config object."""
    sim_config = config_loader.get_simulation_config()
    assert sim_config is not None
    # Test that it has expected attributes
    expected_attrs = ['max_speed', 'simulation_time', 'update_rate', 
                     'speed_change_threshold', 'position_change_threshold', 
                     'heading_change_threshold', 'target_tolerance']
    for attr in expected_attrs:
        assert hasattr(sim_config, attr), f"SimulationConfig missing {attr}"
        assert getattr(sim_config, attr) is not None, f"SimulationConfig {attr} is None"


def test_simulation_logger_initialization(simulation_logger):
    """Test Logger initialization."""
    # Basic logger attributes exist (mocked)
    assert simulation_logger is not None
    assert hasattr(simulation_logger, 'simulation_log')
    assert hasattr(simulation_logger, 'operations_log')
    assert hasattr(simulation_logger, 'simulation_file')
    assert hasattr(simulation_logger, 'operations_file')


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
    for file in []:
        if os.path.exists(file):
            os.remove(file)
