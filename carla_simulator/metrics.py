"""
Data models for simulation metrics.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple
from datetime import datetime
from uuid import UUID

from carla_simulator.utils.types import SimulationData


@dataclass
class SimulationMetricsData:
    """Data structure for simulation metrics that can be logged"""

    scenario_id: int = None
    session_id: UUID = None
    timestamp: datetime = None
    elapsed_time: float = 0.0
    speed: float = 0.0
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    target_distance: float = 0.0
    target_heading: float = 0.0
    vehicle_heading: float = 0.0
    heading_diff: float = 0.0
    acceleration: float = 0.0
    angular_velocity: float = 0.0
    gear: int = 1
    hand_brake: bool = False
    reverse: bool = False
    manual_gear_shift: bool = False
    collision_intensity: float = 0.0
    cloudiness: float = 0.0
    precipitation: float = 0.0
    traffic_count: int = 0
    fps: float = 0.0
    event: str = ""
    event_details: str = ""
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0

    @classmethod
    def from_simulation_data(
        cls, data: "SimulationData", scenario_id: int = None, session_id: UUID = None
    ) -> "SimulationMetricsData":
        """Create metrics data from simulation data"""
        return cls(
            scenario_id=scenario_id,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            elapsed_time=data.elapsed_time,
            speed=data.speed,
            position_x=data.position[0],
            position_y=data.position[1],
            position_z=data.position[2],
            throttle=data.controls["throttle"],
            brake=data.controls["brake"],
            steer=data.controls["steer"],
            target_distance=data.target_info["distance"],
            target_heading=data.target_info["heading"],
            vehicle_heading=data.vehicle_state["heading"],
            heading_diff=data.target_info["heading_diff"],
            acceleration=data.vehicle_state["acceleration"],
            angular_velocity=data.vehicle_state["angular_velocity"],
            gear=data.controls["gear"],
            hand_brake=data.controls["hand_brake"],
            reverse=data.controls["reverse"],
            manual_gear_shift=data.controls["manual_gear_shift"],
            collision_intensity=data.vehicle_state["collision_intensity"],
            cloudiness=data.weather["cloudiness"],
            precipitation=data.weather["precipitation"],
            traffic_count=data.traffic_count,
            fps=data.fps,
            event=data.event,
            event_details=data.event_details,
            rotation_x=data.vehicle_state["rotation"][0],
            rotation_y=data.vehicle_state["rotation"][1],
            rotation_z=data.vehicle_state["rotation"][2],
        )
