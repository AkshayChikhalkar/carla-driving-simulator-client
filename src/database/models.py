"""
Database models for the CARLA Driving Simulator.
"""

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from .config import Base
from .db_manager import DatabaseManager
from src.models.metrics import SimulationMetricsData


def log_error(message: str, error: Exception) -> None:
    """Centralized error logging function"""
    from src.utils.logging import Logger

    Logger().error(f"{message}: {error}")


class User(Base):
    """Model for storing user authentication data"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def create(cls, db: DatabaseManager, **kwargs) -> Optional["User"]:
        """Create a new user"""
        try:
            query = """
                INSERT INTO users (username, email, password_hash, first_name, last_name, is_active, is_admin)
                VALUES (%(username)s, %(email)s, %(password_hash)s, %(first_name)s, %(last_name)s, %(is_active)s, %(is_admin)s)
                RETURNING *
            """
            result = db.execute_query(query, kwargs)
            return result[0] if result else None
        except Exception as e:
            log_error("Error creating user", e)
            return None

    @classmethod
    def get_by_username(cls, db: DatabaseManager, username: str) -> Optional["User"]:
        """Get user by username"""
        try:
            query = "SELECT * FROM users WHERE username = %(username)s AND is_active = TRUE"
            result = db.execute_query(query, {"username": username})
            return result[0] if result else None
        except Exception as e:
            log_error("Error getting user by username", e)
            return None

    @classmethod
    def get_by_email(cls, db: DatabaseManager, email: str) -> Optional["User"]:
        """Get user by email"""
        try:
            query = "SELECT * FROM users WHERE email = %(email)s AND is_active = TRUE"
            result = db.execute_query(query, {"email": email})
            return result[0] if result else None
        except Exception as e:
            log_error("Error getting user by email", e)
            return None

    def update_last_login(self, db: DatabaseManager) -> bool:
        """Update user's last login timestamp"""
        try:
            query = """
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = %(user_id)s
                RETURNING *
            """
            result = db.execute_query(query, {"user_id": self.id})
            return bool(result)
        except Exception as e:
            log_error("Error updating last login", e)
            return False


class UserSession(Base):
    """Model for storing user session data"""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(String)

    # Relationship
    user = relationship("User", back_populates="sessions")

    @classmethod
    def create(cls, db: DatabaseManager, **kwargs) -> Optional["UserSession"]:
        """Create a new user session"""
        try:
            query = """
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (%(user_id)s, %(session_token)s, %(expires_at)s, %(ip_address)s, %(user_agent)s)
                RETURNING *
            """
            result = db.execute_query(query, kwargs)
            return result[0] if result else None
        except Exception as e:
            log_error("Error creating user session", e)
            return None

    @classmethod
    def get_by_token(cls, db: DatabaseManager, session_token: str) -> Optional["UserSession"]:
        """Get session by token"""
        try:
            query = """
                SELECT us.*, u.* FROM user_sessions us
                JOIN users u ON us.user_id = u.id
                WHERE us.session_token = %(session_token)s AND us.expires_at > CURRENT_TIMESTAMP
            """
            result = db.execute_query(query, {"session_token": session_token})
            return result[0] if result else None
        except Exception as e:
            log_error("Error getting session by token", e)
            return None

    @classmethod
    def delete_expired_sessions(cls, db: DatabaseManager) -> bool:
        """Delete expired sessions"""
        try:
            query = "DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP"
            db.execute_query(query)
            return True
        except Exception as e:
            log_error("Error deleting expired sessions", e)
            return False

    @classmethod
    def delete_user_sessions(cls, db: DatabaseManager, user_id: int) -> bool:
        """Delete all sessions for a user"""
        try:
            query = "DELETE FROM user_sessions WHERE user_id = %(user_id)s"
            db.execute_query(query, {"user_id": user_id})
            return True
        except Exception as e:
            log_error("Error deleting user sessions", e)
            return False


class Scenario(Base):
    """Model for storing scenario executions (was Simulation)"""

    __tablename__ = "scenarios"

    scenario_id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    scenario_name = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    status = Column(String)  # 'running', 'completed', 'failed'
    scenario_metadata = Column(JSON)  # Additional scenario metadata

    # Relationships
    vehicle_data = relationship("VehicleData", back_populates="scenario")
    sensor_data = relationship("SensorData", back_populates="scenario")
    metrics = relationship("SimulationMetrics", back_populates="scenario")

    @classmethod
    def create(cls, db: DatabaseManager, **kwargs) -> Optional["Scenario"]:
        """Create a new scenario"""
        try:
            query = """
                INSERT INTO scenarios (session_id, scenario_name, start_time, end_time, status, scenario_metadata)
                VALUES (%(session_id)s, %(scenario_name)s, %(start_time)s, %(end_time)s, %(status)s, %(scenario_metadata)s)
                RETURNING *
            """
            result = db.execute_query(query, kwargs)
            return result[0] if result else None
        except Exception as e:
            log_error("Error creating scenario", e)
            return None

    @classmethod
    def get_by_id(cls, db: DatabaseManager, scenario_id: int) -> Optional["Scenario"]:
        """Get scenario by ID"""
        try:
            query = "SELECT * FROM scenarios WHERE scenario_id = %(scenario_id)s"
            result = db.execute_query(query, {"scenario_id": scenario_id})
            return result[0] if result else None
        except Exception as e:
            log_error("Error getting scenario", e)
            return None

    def update(self, db: DatabaseManager, **kwargs) -> bool:
        """Update scenario"""
        try:
            update_fields = []
            params = {"scenario_id": self.scenario_id}

            for key, value in kwargs.items():
                if hasattr(self, key):
                    update_fields.append(f"{key} = %({key})s")
                    params[key] = value

            if not update_fields:
                return False

            query = f"""
                UPDATE scenarios 
                SET {', '.join(update_fields)}
                WHERE scenario_id = %(scenario_id)s
                RETURNING *
            """
            result = db.execute_query(query, params)
            return bool(result)
        except Exception as e:
            log_error("Error updating scenario", e)
            return False


class VehicleData(Base):
    """Model for storing vehicle telemetry data"""

    __tablename__ = "vehicle_data"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(
        Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE")
    )
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    position_x = Column(Float)
    position_y = Column(Float)
    position_z = Column(Float)
    velocity = Column(Float)
    acceleration = Column(Float)
    steering_angle = Column(Float)
    throttle = Column(Float)
    brake = Column(Float)

    # Relationship
    scenario = relationship("Scenario", back_populates="vehicle_data")


class SensorData(Base):
    """Model for storing sensor data"""

    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(
        Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE")
    )
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sensor_type = Column(String)  # 'camera', 'lidar', 'radar', etc.
    data = Column(JSON)  # Sensor-specific data

    # Relationship
    scenario = relationship("Scenario", back_populates="sensor_data")


class SimulationMetrics(Base):
    """Model for storing all metrics from simulation CSV logs"""

    __tablename__ = "simulation_metrics"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(
        Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE")
    )
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    elapsed_time = Column(Float)
    speed = Column(Float)
    position_x = Column(Float)
    position_y = Column(Float)
    position_z = Column(Float)
    throttle = Column(Float)
    brake = Column(Float)
    steer = Column(Float)
    target_distance = Column(Float)
    target_heading = Column(Float)
    vehicle_heading = Column(Float)
    heading_diff = Column(Float)
    acceleration = Column(Float)
    angular_velocity = Column(Float)
    gear = Column(Integer)
    hand_brake = Column(Boolean)
    reverse = Column(Boolean)
    manual_gear_shift = Column(Boolean)
    collision_intensity = Column(Float)
    cloudiness = Column(Float)
    precipitation = Column(Float)
    traffic_count = Column(Integer)
    fps = Column(Float)
    event = Column(String)
    event_details = Column(String)
    rotation_x = Column(Float)
    rotation_y = Column(Float)
    rotation_z = Column(Float)

    # Relationship
    scenario = relationship("Scenario", back_populates="metrics")

    @classmethod
    def from_metrics_data(cls, data: SimulationMetricsData) -> "SimulationMetrics":
        """Create a database model instance from metrics data"""
        return cls(
            scenario_id=data.scenario_id,
            session_id=data.session_id,
            timestamp=data.timestamp,
            elapsed_time=data.elapsed_time,
            speed=data.speed,
            position_x=data.position_x,
            position_y=data.position_y,
            position_z=data.position_z,
            throttle=data.throttle,
            brake=data.brake,
            steer=data.steer,
            target_distance=data.target_distance,
            target_heading=data.target_heading,
            vehicle_heading=data.vehicle_heading,
            heading_diff=data.heading_diff,
            acceleration=data.acceleration,
            angular_velocity=data.angular_velocity,
            gear=data.gear,
            hand_brake=data.hand_brake,
            reverse=data.reverse,
            manual_gear_shift=data.manual_gear_shift,
            collision_intensity=data.collision_intensity,
            cloudiness=data.cloudiness,
            precipitation=data.precipitation,
            traffic_count=data.traffic_count,
            fps=data.fps,
            event=data.event,
            event_details=data.event_details,
            rotation_x=data.rotation_x,
            rotation_y=data.rotation_y,
            rotation_z=data.rotation_z,
        )
