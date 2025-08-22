"""
Configuration and fixtures for integration tests.
"""

import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="session")
def test_config():
    """Provide a test configuration for integration tests."""
    return {
        "simulation": {
            "max_vehicles": 10,
            "weather": "ClearNoon",
            "map": "Town01",
            "timeout": 30
        },
        "display": {
            "resolution": "1920x1080",
            "fullscreen": False,
            "fps": 60
        },
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False
        },
        "logging": {
            "level": "INFO",
            "file": "test_integration.log"
        }
    }


@pytest.fixture(scope="session")
def mock_database():
    """Provide a mock database for integration tests."""
    with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
        mock_db_instance = MagicMock()
        mock_db.return_value = mock_db_instance
        mock_db_instance.connect.return_value = True
        mock_db_instance.disconnect.return_value = None
        yield mock_db_instance


@pytest.fixture(scope="session")
def mock_config_loader():
    """Provide a mock config loader for integration tests."""
    with patch('carla_simulator.utils.config.ConfigLoader') as mock_loader:
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.get_config.return_value = {
            "simulation": {"max_vehicles": 5},
            "display": {"resolution": "1920x1080"}
        }
        yield mock_loader_instance


@pytest.fixture(scope="session")
def mock_simulation_runner():
    """Provide a mock simulation runner for integration tests."""
    with patch('carla_simulator.core.simulation_runner.SimulationRunner') as mock_runner:
        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance
        mock_runner_instance.initialize.return_value = True
        mock_runner_instance.run.return_value = True
        mock_runner_instance.cleanup.return_value = None
        yield mock_runner_instance


@pytest.fixture(scope="session")
def temp_test_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def clean_environment():
    """Clean environment variables for tests."""
    # Store original environment
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ.update({
        "TESTING": "true",
        "DATABASE_URL": "sqlite:///:memory:",
        "CONFIG_TENANT_ID": "1",
        "WEB_FILE_LOGS_ENABLED": "false",
        "DISABLE_AUTH_FOR_TESTING": "true"
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def integration_test_data():
    """Provide test data for integration tests."""
    return {
        "users": [
            {
                "id": 1,
                "username": "testuser1",
                "email": "test1@example.com",
                "tenant_id": 1,
                "is_active": True
            },
            {
                "id": 2,
                "username": "testuser2",
                "email": "test2@example.com",
                "tenant_id": 1,
                "is_active": True
            }
        ],
        "tenants": [
            {
                "id": 1,
                "name": "Test Tenant",
                "slug": "test-tenant",
                "is_active": True
            }
        ],
        "configs": [
            {
                "id": 1,
                "tenant_id": 1,
                "config_data": {
                    "simulation": {"max_vehicles": 10},
                    "display": {"resolution": "1920x1080"}
                },
                "is_active": True
            }
        ]
    }
