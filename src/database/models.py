from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .config import Base

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

class VehicleData(Base):
    """Model for storing vehicle telemetry data"""
    __tablename__ = "vehicle_data"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE"))
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
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE"))
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
    scenario_id = Column(Integer, ForeignKey("scenarios.scenario_id", ondelete="CASCADE"))
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