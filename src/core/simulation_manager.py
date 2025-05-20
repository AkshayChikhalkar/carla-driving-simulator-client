"""
Manages the simulation state, events, and metrics.
"""

import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum, auto

class SimulationEvent(Enum):
    """Possible simulation events"""
    SPEED_CHANGE = auto()
    POSITION_CHANGE = auto()
    HEADING_CHANGE = auto()
    COLLISION = auto()
    TARGET_REACHED = auto()
    SPEED_LIMIT = auto()
    NONE = auto()

@dataclass
class SimulationState:
    """Current state of the simulation"""
    elapsed_time: float
    speed: float
    position: tuple[float, float, float]
    heading: float
    distance_to_target: float
    is_finished: bool
    collision_intensity: float = 0.0

class SimulationManager:
    """Manages simulation state and events"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize simulation manager"""
        self.config = config
        self.start_time = time.time()
        self.last_speed = 0.0
        self.last_position = (0.0, 0.0, 0.0)
        self.last_heading = 0.0
        self.is_finished = False
        self._state = SimulationState(
            elapsed_time=0.0,
            speed=0.0,
            position=(0.0, 0.0, 0.0),
            heading=0.0,
            distance_to_target=float('inf'),
            is_finished=False
        )
    
    @property
    def state(self) -> SimulationState:
        """Get current simulation state"""
        return self._state
    
    def update_state(self, **kwargs) -> None:
        """Update simulation state with new values"""
        self._state = SimulationState(
            elapsed_time=time.time() - self.start_time,
            **kwargs
        )
    
    def check_events(self) -> tuple[SimulationEvent, str]:
        """Check for significant events based on current state"""
        event = SimulationEvent.NONE
        details = ""
        
        # Check speed changes
        if abs(self._state.speed - self.last_speed) > self.config['speed_change_threshold']:
            event = SimulationEvent.SPEED_CHANGE
            details = f"Speed change: {self.last_speed:.1f} -> {self._state.speed:.1f} km/h"
        
        # Check target reached
        elif (self._state.distance_to_target < self.config['target_tolerance'] 
              and not self.is_finished):
            event = SimulationEvent.TARGET_REACHED
            details = f"Target reached at distance: {self._state.distance_to_target:.1f}m"
            self.is_finished = True
        
        # Check speed limit
        elif self._state.speed > self.config['max_speed']:
            event = SimulationEvent.SPEED_LIMIT
            details = f"Speed limit reached: {self._state.speed:.1f} km/h"
        
        # Update last values
        self.last_speed = self._state.speed
        self.last_position = self._state.position
        self.last_heading = self._state.heading
        
        return event, details
    
    def should_continue(self) -> bool:
        """Check if simulation should continue"""
        elapsed_time = time.time() - self.start_time
        return (elapsed_time < self.config['simulation_time'] 
                and not self.is_finished) 