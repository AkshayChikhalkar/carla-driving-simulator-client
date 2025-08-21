"""
Pytest configuration for web backend tests.
"""

import os
import pytest
import logging
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def setup_web_backend_test_environment():
    """Setup test environment for web backend tests."""
    # Set test environment variables
    test_env_vars = {
        "TESTING": "true",
        "WEB_FILE_LOGS_ENABLED": "false",
        "DISABLE_AUTH_FOR_TESTING": "true",
        "DATABASE_URL": "sqlite:///:memory:",
        "CONFIG_TENANT_ID": "1"
    }
    
    # Store original values for cleanup
    original_values = {}
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Configure logging to suppress warnings during tests
    logging.getLogger('web.backend').setLevel(logging.CRITICAL)
    logging.getLogger('httpx').setLevel(logging.CRITICAL)
    
    yield
    
    # Cleanup: restore original environment variables
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_runner_registry():
    """Mock runner registry for web backend tests."""
    with patch("web.backend.runner_registry") as mock_registry:
        registry = MagicMock()
        registry.get_or_create.return_value = MagicMock()
        registry.get.return_value = MagicMock()
        registry.cleanup.return_value = True
        registry.list.return_value = []
        registry.remove.return_value = True
        mock_registry.return_value = registry
        yield registry


@pytest.fixture
def mock_carla_pool():
    """Mock carla pool for web backend tests."""
    with patch("web.backend.carla_pool") as mock_pool:
        pool = MagicMock()
        pool.acquire.return_value = MagicMock()
        pool.release.return_value = True
        pool.status.return_value = {"available": 5, "total": 10}
        pool.housekeeping.return_value = {"cleaned": 2, "errors": 0}
        pool.get_available.return_value = 5
        pool.get_total.return_value = 10
        mock_pool.return_value = pool
        yield pool
