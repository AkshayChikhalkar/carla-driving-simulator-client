"""
Pytest configuration for carla_simulator tests.
"""

import os
import pytest
import logging
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def setup_carla_test_environment():
    """Setup test environment for carla_simulator tests."""
    # Set test environment variables
    test_env_vars = {
        "TESTING": "true",
        "DATABASE_URL": "sqlite:///:memory:",
        "CONFIG_TENANT_ID": "1"
    }
    
    # Store original values for cleanup
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Configure logging to suppress warnings during tests
    logging.getLogger('carla_simulator.database').setLevel(logging.CRITICAL)
    logging.getLogger('carla_simulator.utils.logging').setLevel(logging.CRITICAL)
    
    yield
    
    # Cleanup: restore original environment variables
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_database():
    """Mock database manager for carla_simulator tests."""
    with patch("carla_simulator.database.db_manager.DatabaseManager") as mock_db:
        mock_instance = MagicMock()
        mock_db.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_logger():
    """Mock logger for carla_simulator tests."""
    with patch("carla_simulator.utils.logging.Logger") as mock_logger:
        logger = MagicMock()
        logger.simulation_log = "test_simulation.csv"
        logger.operations_log = "test_operations.log"
        logger.simulation_file = MagicMock()
        logger.operations_file = MagicMock()
        mock_logger.return_value = logger
        yield logger
