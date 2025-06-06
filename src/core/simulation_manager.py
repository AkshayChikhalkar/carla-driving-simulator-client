"""
Manages the simulation state, events, and metrics.
"""

from logging import Logger
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum, auto
import carla
from src.core.interfaces import (
    ISimulationManager,
    IScenario,
    IWorldManager,
    IVehicleController,
    ISensorManager,
    ILogger
)
from src.utils.settings import DEBUG_MODE
from ..visualization.display_manager import VehicleState

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

class SimulationManager(ISimulationManager):
    """Manages the simulation lifecycle and coordinates between components"""
    
    def __init__(self, logger: ILogger):
        self.logger = logger
        self.world_manager = None
        self.sensor_manager = None
        self._state = None
        self.last_speed = 0.0
        self.last_position = (0.0, 0.0, 0.0)
        self.last_heading = 0.0
        self.is_finished = False
        self.start_time = None
        self._scenario = None

    def connect(self) -> bool:
        """Connect to the CARLA server"""
        try:
            self.world_manager.get_world()
            self.logger.info("Successfully connected to CARLA server")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to CARLA server: {str(e)}")
            return False

    def setup(self) -> None:
        """Setup the simulation environment"""
        try:
            # Setup sensors
            self.sensor_manager.setup_sensors()
            
            # Get initial vehicle state
            vehicle = self.vehicle_controller.get_vehicle()
            if not vehicle:
                raise RuntimeError("Vehicle not available")
                
            self.logger.info("Simulation environment setup completed")
        except Exception as e:
            self.logger.error(f"Failed to setup simulation: {str(e)}")
            raise

    def set_scenario(self, scenario: IScenario) -> None:
        """Set the current scenario"""
        self._scenario = scenario

    def run(self) -> None:
        """Run the simulation"""
        if not self._scenario:
            raise RuntimeError("No scenario set")
            
        self._state.is_running = True
        self.logger.info("Starting simulation loop")
        
        try:
            while self._state.is_running:
                # Update scenario
                self._scenario.update()
                
                # Check if scenario is complete
                if self._scenario.is_completed():
                    self._state.is_running = False
                    break
                    
        except Exception as e:
            self.logger.error(f"Error in simulation loop: {str(e)}")
            raise
        finally:
            self._state.is_running = False

    def stop(self) -> None:
        """Stop the simulation"""
        self.is_finished = True
        if self._state:
            self._state.is_running = False

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

    def initialize(self) -> bool:
        """Initialize the simulation"""
        try:
            # Connect to CARLA server
            if not self.world_manager.connect():
                self.logger.error("Failed to connect to CARLA server")
                return False
                
            # Load map
            self.world_manager.load_map(self.map_name)
            self.logger.info(f"Loaded map: {self.map_name}")
            
            # Spawn vehicle
            if not self.spawn_vehicle():
                self.logger.error("Failed to spawn vehicle")
                return False
                
            self.logger.info("Simulation initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Error initializing simulation", exc_info=e)
            return False

    def spawn_vehicle(self) -> bool:
        """Spawn the ego vehicle"""
        try:
            # Get spawn points
            spawn_points = self.world_manager.get_map().get_spawn_points()
            if not spawn_points:
                self.logger.error("No spawn points found in map")
                return False
                
            # Spawn vehicle
            self.vehicle = self.world_manager.spawn_actor(
                self.vehicle_bp,
                spawn_points[0]
            )
            
            if not self.vehicle:
                self.logger.error("Failed to spawn vehicle")
                return False
                
            self.logger.info("Vehicle spawned successfully")
            return True
            
        except Exception as e:
            self.logger.error("Error spawning vehicle", exc_info=e)
            return False 