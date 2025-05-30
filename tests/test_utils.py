"""
Unit tests for utility modules.
"""

import os
import pytest
from src.utils.config import ConfigLoader, SimulationConfig
from src.utils.logging import Logger, SimulationData

@pytest.fixture
def config_loader():
    """Fixture providing a ConfigLoader instance."""
    return ConfigLoader("config/simulation_config.yaml")

@pytest.fixture
def simulation_logger():
    """Fixture providing a Logger instance."""
    return Logger("test_simulation.csv", "test_operations.log")

def test_config_loader_initialization(config_loader):
    """Test ConfigLoader initialization."""
    assert config_loader.config_path == "config/simulation_config.yaml"
    assert config_loader.config is None
    assert config_loader.simulation_config is None

def test_config_loading(config_loader):
    """Test configuration loading from YAML file."""
    config = config_loader.load_config()
    assert isinstance(config, dict)
    assert 'target' in config
    assert 'vehicle' in config
    assert 'simulation' in config

def test_config_validation(config_loader):
    """Test configuration validation."""
    config_loader.load_config()
    assert config_loader.validate_config() is True

def test_simulation_config_creation(config_loader):
    """Test creation of SimulationConfig object."""
    sim_config = config_loader.get_simulation_config()
    assert isinstance(sim_config, SimulationConfig)
    assert sim_config.target_distance == 500.0
    assert sim_config.vehicle_model == "vehicle.dodge.charger"

def test_simulation_logger_initialization(simulation_logger):
    """Test Logger initialization."""
    assert simulation_logger.simulation_log == "test_simulation.csv"
    assert simulation_logger.operations_log == "test_operations.log"
    assert simulation_logger.simulation_file is not None
    assert simulation_logger.operations_file is not None

def test_simulation_data_logging(simulation_logger):
    """Test logging of simulation data."""
    data = SimulationData(
        time_elapsed=1.0,
        speed=50.0,
        position_x=100.0,
        position_y=200.0,
        position_z=0.0,
        throttle=0.5,
        brake=0.0,
        steer=0.0,
        distance_to_target=300.0,
        heading_to_target=45.0,
        vehicle_heading=40.0,
        heading_difference=5.0,
        acceleration=2.0,
        angular_velocity=0.1,
        gear=1,
        hand_brake=False,
        reverse=False,
        manual_shift=False,
        collision_intensity=0.0,
        weather_cloudiness=0.0,
        weather_precipitation=0.0,
        traffic_count=5,
        fps=60.0,
        scenario_event="NONE",
        event_details="",
        rotation_pitch=0.0,
        rotation_yaw=40.0,
        rotation_roll=0.0
    )
    
    simulation_logger.log_simulation_data(data)
    
    # Verify file was created and contains data
    assert os.path.exists("test_simulation.csv")
    with open("test_simulation.csv", 'r') as f:
        content = f.read()
        assert "Time_Elapsed[s]" in content
        assert "1.00" in content  # time_elapsed
        assert "50.00" in content  # speed

def test_operation_logging(simulation_logger):
    """Test logging of operational messages."""
    test_message = "Test operation message"
    simulation_logger.log_operation(test_message)
    
    # Verify file was created and contains message
    assert os.path.exists("test_operations.log")
    with open("test_operations.log", 'r') as f:
        content = f.read()
        assert "Test operation message" in content

def test_logger_cleanup(simulation_logger):
    """Test proper cleanup of logger resources."""
    simulation_logger.close()
    assert simulation_logger.operations_file is None

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test files after each test."""
    yield
    for file in ["test_simulation.csv", "test_operations.log"]:
        if os.path.exists(file):
            os.remove(file) 