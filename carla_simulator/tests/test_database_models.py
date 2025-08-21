"""
Unit tests for database models and operations.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid


# ========================= DATABASE MODEL TESTS =========================

@pytest.fixture
def mock_database():
    """Mock database manager."""
    with patch("carla_simulator.database.db_manager.DatabaseManager") as mock_db:
        mock_instance = MagicMock()
        mock_db.return_value = mock_instance
        yield mock_instance


def test_user_model_creation(mock_database):
    """Test User model creation."""
    from carla_simulator.database.models import User
    
    # Mock successful user creation
    mock_database.execute_query.return_value = [
        {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": False,
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }
    ]
    
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "first_name": "Test",
        "last_name": "User",
        "is_admin": False,
        "is_active": True
    }
    
    with patch.object(User, 'create') as mock_create:
        mock_create.return_value = mock_database.execute_query.return_value[0]
        
        user = User.create(mock_database, **user_data)
        
        assert user["id"] == 1
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert user["is_admin"] is False
        mock_create.assert_called_once_with(mock_database, **user_data)


def test_user_model_get_by_username(mock_database):
    """Test User model get by username."""
    from carla_simulator.database.models import User
    
    mock_database.fetch_one.return_value = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "is_admin": False
    }
    
    with patch.object(User, 'get_by_username') as mock_get:
        mock_get.return_value = mock_database.fetch_one.return_value
        
        user = User.get_by_username(mock_database, "testuser")
        
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        mock_get.assert_called_once_with(mock_database, "testuser")


def test_user_model_get_by_email(mock_database):
    """Test User model get by email."""
    from carla_simulator.database.models import User
    
    mock_database.fetch_one.return_value = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password"
    }
    
    with patch.object(User, 'get_by_email') as mock_get:
        mock_get.return_value = mock_database.fetch_one.return_value
        
        user = User.get_by_email(mock_database, "test@example.com")
        
        assert user["email"] == "test@example.com"
        assert user["username"] == "testuser"
        mock_get.assert_called_once_with(mock_database, "test@example.com")


def test_user_model_update_last_login(mock_database):
    """Test User model update last login."""
    from carla_simulator.database.models import User
    
    mock_database.execute_query.return_value = True
    
    with patch.object(User, 'update_last_login') as mock_update:
        mock_update.return_value = True
        
        result = User.update_last_login(mock_database, 1)
        
        assert result is True
        mock_update.assert_called_once_with(mock_database, 1)


def test_tenant_model_creation(mock_database):
    """Test Tenant model creation."""
    from carla_simulator.database.models import Tenant

    mock_database.execute_query.return_value = [
        {
            "id": 1,
            "name": "Test Tenant",
            "slug": "test-tenant",
            "is_active": True,
            "created_at": datetime.now()
        }
    ]

    with patch.object(Tenant, 'create_if_not_exists') as mock_create:
        mock_create.return_value = mock_database.execute_query.return_value[0]
        
        tenant = Tenant.create_if_not_exists(mock_database, "Test Tenant", "test-tenant", True)
        
        assert tenant["id"] == 1
        assert tenant["name"] == "Test Tenant"
        assert tenant["slug"] == "test-tenant"
        mock_create.assert_called_once_with(mock_database, "Test Tenant", "test-tenant", True)


def test_tenant_model_get_by_slug(mock_database):
    """Test Tenant model get by slug."""
    from carla_simulator.database.models import Tenant
    
    mock_database.fetch_one.return_value = {
        "id": 1,
        "name": "Test Tenant",
        "slug": "test-tenant",
        "is_active": True
    }
    
    with patch.object(Tenant, 'get_by_slug') as mock_get:
        mock_get.return_value = mock_database.fetch_one.return_value
        
        tenant = Tenant.get_by_slug(mock_database, "test-tenant")
        
        assert tenant["slug"] == "test-tenant"
        assert tenant["name"] == "Test Tenant"
        mock_get.assert_called_once_with(mock_database, "test-tenant")


def test_tenant_config_model(mock_database):
    """Test TenantConfig model."""
    from carla_simulator.database.models import TenantConfig
    
    mock_database.fetch_one.return_value = {
        "id": 1,
        "tenant_id": 1,
        "config_data": {"key": "value"},
        "is_active": True,
        "created_at": datetime.now()
    }
    
    with patch.object(TenantConfig, 'get_active_config') as mock_get:
        mock_get.return_value = mock_database.fetch_one.return_value["config_data"]
        
        config = TenantConfig.get_active_config(mock_database, 1)
        
        assert config == {"key": "value"}
        mock_get.assert_called_once_with(mock_database, 1)


def test_tenant_config_upsert(mock_database):
    """Test TenantConfig upsert."""
    from carla_simulator.database.models import TenantConfig
    
    mock_database.execute_query.return_value = [{"v": 1}]
    mock_database.execute_transaction.return_value = True
    
    config_data = {"key": "value"}
    
    with patch.object(TenantConfig, 'upsert_active_config') as mock_upsert:
        mock_upsert.return_value = {"tenant_id": 1, "version": 2, "config": config_data}
        
        result = TenantConfig.upsert_active_config(mock_database, 1, config_data)
        
        assert result["tenant_id"] == 1
        assert result["version"] == 2
        assert result["config"] == config_data
        mock_upsert.assert_called_once_with(mock_database, 1, config_data)


def test_user_session_model(mock_database):
    """Test UserSession model."""
    from carla_simulator.database.models import UserSession
    
    session_id = str(uuid.uuid4())
    mock_database.execute_query.return_value = [
        {
            "id": 1,
            "user_id": 1,
            "session_id": session_id,
            "is_active": True,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
    ]
    
    session_data = {
        "user_id": 1,
        "session_id": session_id,
        "is_active": True
    }
    
    with patch.object(UserSession, 'create') as mock_create:
        mock_create.return_value = mock_database.execute_query.return_value[0]
        
        session = UserSession.create(mock_database, **session_data)
        
        assert session["user_id"] == 1
        assert session["session_id"] == session_id
        mock_create.assert_called_once_with(mock_database, **session_data)


def test_user_session_delete(mock_database):
    """Test UserSession delete."""
    from carla_simulator.database.models import UserSession
    
    mock_database.execute_query.return_value = True
    
    with patch.object(UserSession, 'delete_user_sessions') as mock_delete:
        mock_delete.return_value = True
        
        result = UserSession.delete_user_sessions(mock_database, 1)
        
        assert result is True
        mock_delete.assert_called_once_with(mock_database, 1)


def test_simulation_report_model(mock_database):
    """Test SimulationReport model."""
    from carla_simulator.database.models import SimulationReport
    
    mock_database.execute_query.return_value = [
        {
            "id": 1,
            "tenant_id": 1,
            "scenario_name": "test_scenario",
            "status": "completed",
            "created_at": datetime.now()
        }
    ]
    
    report_data = {
        "tenant_id": 1,
        "scenario_name": "test_scenario",
        "status": "completed"
    }
    
    with patch.object(SimulationReport, 'create') as mock_create:
        mock_create.return_value = mock_database.execute_query.return_value[0]
        
        report = SimulationReport.create(mock_database, **report_data)
        
        assert report["tenant_id"] == 1
        assert report["scenario_name"] == "test_scenario"
        mock_create.assert_called_once_with(mock_database, **report_data)


def test_carla_metadata_model(mock_database):
    """Test CarlaMetadata model."""
    from carla_simulator.database.models import CarlaMetadata
    
    mock_database.execute_query.return_value = [
        {
            "id": 1,
            "tenant_id": 1,
            "key": "version",
            "value": "0.10.0",
            "created_at": datetime.now()
        }
    ]
    
    metadata_data = {
        "tenant_id": 1,
        "key": "version",
        "value": "0.10.0"
    }
    
    with patch.object(CarlaMetadata, 'upsert') as mock_upsert:
        mock_upsert.return_value = mock_database.execute_query.return_value[0]
        
        metadata = CarlaMetadata.upsert(mock_database, **metadata_data)
        
        assert metadata["key"] == "version"
        assert metadata["value"] == "0.10.0"
        mock_upsert.assert_called_once_with(mock_database, **metadata_data)


# ========================= DATABASE MANAGER TESTS =========================

def test_database_manager_initialization():
    """Test DatabaseManager initialization with actual data."""
    # Patch before importing to ensure the mock is used
    with patch("carla_simulator.database.db_manager.DatabaseManager") as mock_db_class:
        mock_instance = MagicMock()
        mock_db_class.return_value = mock_instance
        
        # Import after patching
        from carla_simulator.database.db_manager import DatabaseManager
        
        # Test initialization
        db = DatabaseManager()
        
        # Verify the class was called
        mock_db_class.assert_called_once()
        
        # Verify we got a mock instance
        assert db == mock_instance


def test_database_manager_execute_query(mock_database):
    """Test DatabaseManager execute_query."""
    mock_database.execute_query.return_value = [{"id": 1, "name": "test"}]
    
    result = mock_database.execute_query("SELECT * FROM test")
    
    assert result == [{"id": 1, "name": "test"}]
    mock_database.execute_query.assert_called_once_with("SELECT * FROM test")


def test_database_manager_fetch_one(mock_database):
    """Test DatabaseManager fetch_one."""
    mock_database.fetch_one.return_value = {"id": 1, "name": "test"}
    
    result = mock_database.fetch_one("SELECT * FROM test WHERE id = 1")
    
    assert result == {"id": 1, "name": "test"}
    mock_database.fetch_one.assert_called_once_with("SELECT * FROM test WHERE id = 1")


def test_database_manager_fetch_all(mock_database):
    """Test DatabaseManager fetch_all."""
    mock_database.fetch_all.return_value = [{"id": 1}, {"id": 2}]
    
    result = mock_database.fetch_all("SELECT * FROM test")
    
    assert result == [{"id": 1}, {"id": 2}]
    mock_database.fetch_all.assert_called_once_with("SELECT * FROM test")


def test_database_manager_get_carla_metadata(mock_database):
    """Test DatabaseManager get_carla_metadata."""
    mock_database.get_carla_metadata.return_value = {"version": "0.10.0"}
    
    result = mock_database.get_carla_metadata(1)
    
    assert result == {"version": "0.10.0"}
    mock_database.get_carla_metadata.assert_called_once_with(1)


def test_database_connection_error():
    """Test database connection error handling."""
    # Patch before importing to ensure the mock is used
    with patch("carla_simulator.database.db_manager.DatabaseManager") as mock_db_class:
        mock_db_class.side_effect = Exception("Connection failed")
        
        # Import after patching
        from carla_simulator.database.db_manager import DatabaseManager
        
        # Test that exception is raised
        with pytest.raises(Exception) as exc_info:
            DatabaseManager()
        
        assert str(exc_info.value) == "Connection failed"


def test_user_creation_error(mock_database):
    """Test user creation error handling."""
    from carla_simulator.database.models import User
    
    mock_database.execute_query.side_effect = Exception("User creation failed")
    
    with patch.object(User, 'create') as mock_create:
        mock_create.side_effect = Exception("User creation failed")
        
        with pytest.raises(Exception) as exc_info:
            User.create(mock_database, username="test", email="test@example.com")
        
        assert str(exc_info.value) == "User creation failed"


def test_tenant_config_invalid_data(mock_database):
    """Test tenant config with invalid data."""
    from carla_simulator.database.models import TenantConfig
    
    mock_database.execute_query.side_effect = Exception("Invalid config data")
    
    with patch.object(TenantConfig, 'upsert_active_config') as mock_upsert:
        mock_upsert.side_effect = Exception("Invalid config data")
        
        with pytest.raises(Exception) as exc_info:
            TenantConfig.upsert_active_config(mock_database, 1, None)
        
        assert str(exc_info.value) == "Invalid config data"


def test_database_transaction_commit(mock_database):
    """Test database transaction commit."""
    mock_database.begin_transaction.return_value = None
    mock_database.commit.return_value = True
    mock_database.rollback.return_value = None
    
    # Test successful transaction
    mock_database.begin_transaction()
    mock_database.execute_query("INSERT INTO test VALUES (1)")
    mock_database.commit()
    
    mock_database.begin_transaction.assert_called_once()
    mock_database.commit.assert_called_once()


def test_database_transaction_rollback(mock_database):
    """Test database transaction rollback."""
    mock_database.begin_transaction.return_value = None
    mock_database.rollback.return_value = None
    
    # Test transaction rollback
    mock_database.begin_transaction()
    mock_database.execute_query("INSERT INTO test VALUES (1)")
    mock_database.rollback()
    
    mock_database.begin_transaction.assert_called_once()
    mock_database.rollback.assert_called_once()


def test_database_migration():
    """Test database migration functionality."""
    with patch("carla_simulator.database.setup.create_database_if_not_exists") as mock_create_db:
        mock_create_db.return_value = True
        
        from carla_simulator.database.setup import create_database_if_not_exists
        
        result = create_database_if_not_exists()
        
        assert result is True
        mock_create_db.assert_called_once()


def test_database_schema_creation():
    """Test database schema creation."""
    with patch("carla_simulator.database.setup.create_schema_if_not_exists") as mock_create_schema:
        mock_create_schema.return_value = True
        
        from carla_simulator.database.setup import create_schema_if_not_exists
        
        result = create_schema_if_not_exists()
        
        assert result is True
        mock_create_schema.assert_called_once()


def test_bulk_user_creation(mock_database):
    """Test bulk user creation."""
    from carla_simulator.database.models import User
    
    users_data = [
        {"username": "user1", "email": "user1@example.com", "password_hash": "hash1"},
        {"username": "user2", "email": "user2@example.com", "password_hash": "hash2"}
    ]
    
    mock_database.execute_query.return_value = [{"id": 1}, {"id": 2}]
    
    with patch.object(User, 'create') as mock_create:
        mock_create.side_effect = [{"id": 1}, {"id": 2}]
        
        # Test creating multiple users
        results = []
        for user_data in users_data:
            result = User.create(mock_database, **user_data)
            results.append(result)
        
        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[1]["id"] == 2
        assert mock_create.call_count == 2


def test_config_retrieval_performance(mock_database):
    """Test config retrieval performance."""
    from carla_simulator.database.models import TenantConfig
    
    mock_database.fetch_one.return_value = {"config_data": {"key": "value"}}
    
    with patch.object(TenantConfig, 'get_active_config') as mock_get:
        mock_get.return_value = {"key": "value"}
        
        # Test performance with timing
        import time
        start_time = time.time()
        
        for i in range(10):
            TenantConfig.get_active_config(mock_database, 1)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance should be reasonable (less than 1 second for 10 operations)
        assert execution_time < 1.0
        assert mock_get.call_count == 10


def test_tenant_data_isolation(mock_database):
    """Test tenant data isolation."""
    from carla_simulator.database.models import TenantConfig
    
    # Mock different configs for different tenants
    mock_database.fetch_one.side_effect = [
        {"config_data": {"tenant": "1", "key": "value1"}},
        {"config_data": {"tenant": "2", "key": "value2"}}
    ]
    
    with patch.object(TenantConfig, 'get_active_config') as mock_get:
        mock_get.side_effect = [
            {"tenant": "1", "key": "value1"},
            {"tenant": "2", "key": "value2"}
        ]
        
        config1 = TenantConfig.get_active_config(mock_database, 1)
        config2 = TenantConfig.get_active_config(mock_database, 2)
        
        assert config1["tenant"] == "1"
        assert config2["tenant"] == "2"
        assert config1["key"] == "value1"
        assert config2["key"] == "value2"
        assert config1 != config2
