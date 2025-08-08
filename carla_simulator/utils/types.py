"""
Shared types and interfaces for the CARLA Driving Simulator.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple


@dataclass
class SimulationData:
    """Data structure for simulation metrics"""

    elapsed_time: float
    speed: float
    position: Tuple[float, float, float]
    controls: Dict[str, float]
    target_info: Dict[str, float]
    vehicle_state: Dict[str, Any]
    weather: Dict[str, float]
    traffic_count: int
    fps: float
    event: str
    event_details: str
