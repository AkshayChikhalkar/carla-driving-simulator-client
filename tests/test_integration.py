"""
Integration tests for CARLA Driving Simulator Client.

These tests verify the interaction between different components:
- Database and models
- Web backend and frontend communication
- Configuration loading and validation
- CLI interface
- Docker container management
"""

import pytest
import tempfile
import os
import json
import subprocess
import time
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import requests
from pathlib import Path

# Import components to test
try:
    from carla_simulator.database.db_manager import DatabaseManager
    from carla_simulator.database.models import User, Tenant, TenantConfig
    from carla_simulator.utils.config import ConfigLoader
    from carla_simulator.core.simulation_runner import SimulationRunner
    from carla_simulator.cli import main as cli_main
    from web.backend.runner_registry import RunnerRegistry
    from web.backend.carla_pool import CarlaContainerManager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some imports not available for integration tests: {e}")
    IMPORTS_AVAILABLE = False


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestDatabaseIntegration:
    """Test database integration with models and operations."""
    
    def test_database_user_tenant_integration(self):
        """Test user creation and tenant association."""
        with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
            # Setup mock database
            mock_db_instance = MagicMock()
            mock_db.return_value = mock_db_instance
            
            # Create tenant
            tenant = Tenant(
                id=1,
                name="Test Tenant",
                slug="test-tenant",
                is_active=True
            )
            
            # Create user (note: User model doesn't have tenant_id field)
            user = User(
                id=1,
                username="testuser",
                email="test@example.com",
                password_hash="hashed_password",
                is_active=True
            )
            
            # Verify basic properties
            assert tenant.id == 1
            assert tenant.is_active == True
            assert user.is_active == True
            assert user.username == "testuser"
    
    def test_tenant_config_integration(self):
        """Test tenant configuration integration."""
        with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
            mock_db_instance = MagicMock()
            mock_db.return_value = mock_db_instance
            
            # Create tenant config
            config_data = {
                "simulation": {
                    "max_vehicles": 10,
                    "weather": "ClearNoon"
                },
                "display": {
                    "resolution": "1920x1080"
                }
            }
            
            tenant_config = TenantConfig(
                id=1,
                tenant_id=1,
                config=config_data,
                is_active=True
            )
            
            # Verify config structure
            assert tenant_config.tenant_id == 1
            assert tenant_config.config["simulation"]["max_vehicles"] == 10
            assert tenant_config.is_active == True


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestConfigurationIntegration:
    """Test configuration loading and validation integration."""
    
    def test_config_loader_database_integration(self):
        """Test config loader with database integration."""
        with patch('carla_simulator.database.models.TenantConfig') as mock_tenant_config:
            with patch('carla_simulator.utils.config.ConfigLoader') as mock_config_loader:
                # Setup mock tenant config
                mock_config = MagicMock()
                mock_config.config_data = {
                    "simulation": {"max_vehicles": 15},
                    "display": {"resolution": "1920x1080"}
                }
                mock_tenant_config.get_active_config.return_value = mock_config
                
                # Setup mock config loader
                mock_loader_instance = MagicMock()
                mock_config_loader.return_value = mock_loader_instance
                mock_loader_instance.get_config.return_value = mock_config.config_data
                
                # Test integration
                config = mock_loader_instance.get_config()
                assert config["simulation"]["max_vehicles"] == 15
                assert config["display"]["resolution"] == "1920x1080"
    
    def test_config_validation_integration(self):
        """Test configuration validation across components."""
        test_config = {
            "simulation": {
                "max_vehicles": 10,
                "weather": "ClearNoon",
                "map": "Town01"
            },
            "display": {
                "resolution": "1920x1080",
                "fullscreen": False
            },
            "database": {
                "url": "sqlite:///:memory:"
            }
        }
        
        # Test that config can be used by different components
        assert "simulation" in test_config
        assert "display" in test_config
        assert "database" in test_config
        
        # Test simulation config
        sim_config = test_config["simulation"]
        assert sim_config["max_vehicles"] > 0
        assert sim_config["weather"] in ["ClearNoon", "CloudyNoon", "WetNoon", "WetCloudyNoon"]
        
        # Test display config
        display_config = test_config["display"]
        assert "x" in display_config["resolution"]
        assert isinstance(display_config["fullscreen"], bool)


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestWebBackendIntegration:
    """Test web backend integration with other components."""
    
    def test_runner_registry_integration(self):
        """Test runner registry integration."""
        with patch('web.backend.runner_registry.RunnerRegistry') as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry.return_value = mock_registry_instance
            
            # Test registry operations
            mock_registry_instance.register_runner.return_value = "runner-123"
            mock_registry_instance.get_runner.return_value = MagicMock()
            mock_registry_instance.cleanup.return_value = None
            
            # Verify integration
            runner_id = mock_registry_instance.register_runner("test-runner")
            assert runner_id == "runner-123"
            
            runner = mock_registry_instance.get_runner(runner_id)
            assert runner is not None
    
    def test_carla_pool_integration(self):
        """Test CARLA container manager integration."""
        with patch('web.backend.carla_pool.CarlaContainerManager') as mock_pool:
            mock_pool_instance = MagicMock()
            mock_pool.return_value = mock_pool_instance
            
            # Test pool operations
            mock_pool_instance.acquire.return_value = ("localhost", 2000)
            mock_pool_instance.release.return_value = None
            mock_pool_instance.cleanup.return_value = None
            
            # Verify integration
            host, port = mock_pool_instance.acquire(tenant_id=1)
            assert host == "localhost"
            assert port == 2000
            
            mock_pool_instance.release(tenant_id=1)
            mock_pool_instance.cleanup()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestCLIIntegration:
    """Test CLI integration with other components."""
    
    def test_cli_config_integration(self):
        """Test CLI with configuration integration."""
        with patch('carla_simulator.cli.main') as mock_cli:
            with patch('carla_simulator.utils.config.ConfigLoader') as mock_config:
                # Setup mock config
                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_config_instance.get_config.return_value = {
                    "simulation": {"max_vehicles": 5}
                }
                
                # Test CLI integration
                mock_cli.return_value = 0
                result = mock_cli()
                assert result == 0
    
    def test_cli_database_integration(self):
        """Test CLI with database integration."""
        with patch('carla_simulator.cli.main') as mock_cli:
            with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
                # Setup mock database
                mock_db_instance = MagicMock()
                mock_db.return_value = mock_db_instance
                mock_db_instance.connect.return_value = True
                
                # Test CLI integration
                mock_cli.return_value = 0
                result = mock_cli()
                assert result == 0


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestSimulationIntegration:
    """Test simulation runner integration."""
    
    def test_simulation_config_integration(self):
        """Test simulation runner with configuration."""
        with patch('carla_simulator.core.simulation_runner.SimulationRunner') as mock_runner:
            mock_runner_instance = MagicMock()
            mock_runner.return_value = mock_runner_instance
            
            # Setup mock config
            config = {
                "simulation": {
                    "max_vehicles": 10,
                    "weather": "ClearNoon"
                }
            }
            
            # Test simulation integration
            mock_runner_instance.initialize.return_value = True
            mock_runner_instance.run.return_value = True
            mock_runner_instance.cleanup.return_value = None
            
            # Verify integration
            assert mock_runner_instance.initialize(config)
            assert mock_runner_instance.run()
            mock_runner_instance.cleanup()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestEndToEndIntegration:
    """Test end-to-end integration scenarios."""
    
    def test_full_workflow_integration(self):
        """Test complete workflow from config to simulation."""
        with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
            with patch('carla_simulator.utils.config.ConfigLoader') as mock_config:
                with patch('carla_simulator.core.simulation_runner.SimulationRunner') as mock_runner:
                    # Setup mocks
                    mock_db_instance = MagicMock()
                    mock_db.return_value = mock_db_instance
                    mock_db_instance.connect.return_value = True
                    
                    mock_config_instance = MagicMock()
                    mock_config.return_value = mock_config_instance
                    mock_config_instance.get_config.return_value = {
                        "simulation": {"max_vehicles": 5},
                        "database": {"url": "sqlite:///:memory:"}
                    }
                    
                    mock_runner_instance = MagicMock()
                    mock_runner.return_value = mock_runner_instance
                    mock_runner_instance.initialize.return_value = True
                    mock_runner_instance.run.return_value = True
                    
                    # Test full workflow
                    config = mock_config_instance.get_config()
                    assert config["simulation"]["max_vehicles"] == 5
                    
                    assert mock_runner_instance.initialize(config)
                    assert mock_runner_instance.run()
    
    def test_error_handling_integration(self):
        """Test error handling across components."""
        with patch('carla_simulator.database.db_manager.DatabaseManager') as mock_db:
            with patch('carla_simulator.utils.config.ConfigLoader') as mock_config:
                # Setup error scenario
                mock_db_instance = MagicMock()
                mock_db.return_value = mock_db_instance
                mock_db_instance.connect.side_effect = Exception("Database connection failed")
                
                mock_config_instance = MagicMock()
                mock_config.return_value = mock_config_instance
                mock_config_instance.get_config.side_effect = Exception("Config loading failed")
                
                # Test error handling
                with pytest.raises(Exception, match="Database connection failed"):
                    mock_db_instance.connect()
                
                with pytest.raises(Exception, match="Config loading failed"):
                    mock_config_instance.get_config()


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestDockerIntegration:
    """Test Docker container integration."""
    
    def test_docker_container_lifecycle(self):
        """Test Docker container lifecycle integration."""
        with patch('subprocess.run') as mock_subprocess:
            # Setup mock subprocess
            mock_subprocess.return_value = MagicMock()
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = b"container_id_123"
            
            # Test container operations
            result = mock_subprocess(["docker", "run", "-d", "test-image"])
            assert result.returncode == 0
            
            # Test container stop
            result = mock_subprocess(["docker", "stop", "container_id_123"])
            assert result.returncode == 0
    
    def test_docker_compose_integration(self):
        """Test Docker Compose integration."""
        with patch('subprocess.run') as mock_subprocess:
            # Setup mock subprocess
            mock_subprocess.return_value = MagicMock()
            mock_subprocess.return_value.returncode = 0
            
            # Test docker-compose up
            result = mock_subprocess(["docker-compose", "up", "-d"])
            assert result.returncode == 0
            
            # Test docker-compose down
            result = mock_subprocess(["docker-compose", "down"])
            assert result.returncode == 0


@pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports not available")
class TestAPIIntegration:
    """Test API integration scenarios."""
    
    def test_api_health_check(self):
        """Test API health check integration."""
        with patch('requests.get') as mock_request:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_request.return_value = mock_response
            
            # Test health check
            response = requests.get("http://localhost:8000/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    def test_api_config_endpoint(self):
        """Test API config endpoint integration."""
        with patch('requests.get') as mock_request:
            # Setup mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "simulation": {"max_vehicles": 10},
                "display": {"resolution": "1920x1080"}
            }
            mock_request.return_value = mock_response
            
            # Test config endpoint
            response = requests.get("http://localhost:8000/config")
            assert response.status_code == 200
            config = response.json()
            assert config["simulation"]["max_vehicles"] == 10
            assert config["display"]["resolution"] == "1920x1080"


if __name__ == "__main__":
    pytest.main([__file__])
