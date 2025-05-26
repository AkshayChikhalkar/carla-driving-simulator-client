"""
Manages the simulation state, events, and metrics.
"""

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
    
    def __init__(self,
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 sensor_manager: ISensorManager,
                 logger: ILogger):
        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.sensor_manager = sensor_manager
        self.logger = logger
        self._scenario: Optional[IScenario] = None
        self._is_running = False
        # Pre-allocate vehicle state dictionary
        self._vehicle_state = {
            'location': None,
            'velocity': None,
            'acceleration': None,
            'transform': None,
            'sensor_data': None
        }

    def connect(self) -> bool:
        """Connect to the CARLA server"""
        try:
            self.world_manager.get_world()
            self.logger.log_info("Successfully connected to CARLA server")
            return True
        except Exception as e:
            self.logger.log_error(f"Failed to connect to CARLA server: {str(e)}")
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
                
            self.logger.log_info("Simulation environment setup completed")
        except Exception as e:
            self.logger.log_error(f"Failed to setup simulation: {str(e)}")
            raise

    def set_scenario(self, scenario: IScenario) -> None:
        """Set the current scenario"""
        self._scenario = scenario
        self._scenario.setup()

    def run(self) -> None:
        """Run the simulation loop"""
        if not self._scenario:
            raise RuntimeError("No scenario set")
            
        self._is_running = True
        self.logger.log_info("Starting simulation loop")
        
        try:
            vehicle = self.vehicle_controller.get_vehicle()
            
            while self._is_running and not self._scenario.is_completed():
                # Update vehicle state in-place
                self._vehicle_state['location'] = vehicle.get_location()
                self._vehicle_state['velocity'] = vehicle.get_velocity()
                self._vehicle_state['acceleration'] = vehicle.get_acceleration()
                self._vehicle_state['transform'] = vehicle.get_transform()
                self._vehicle_state['sensor_data'] = self.sensor_manager.get_sensor_data()
                
                # Update scenario
                self._scenario.update()
                
                # Get and apply control commands
                control = self.vehicle_controller.get_control(self._vehicle_state)
                vehicle.apply_control(control)
                
                # Log vehicle state (consider reducing logging frequency)
                self.logger.log_vehicle_state(self._vehicle_state)
                
        except Exception as e:
            self.logger.log_error(f"Error in simulation loop: {str(e)}")
            raise
        finally:
            self._is_running = False
            if self._scenario:
                self._scenario.cleanup()

    def stop(self) -> None:
        """Stop the simulation"""
        self._is_running = False

    def cleanup(self) -> None:
        """Clean up simulation resources"""
        try:
            self.stop()
            self.sensor_manager.cleanup()
            self.logger.log_info("Simulation cleanup completed")
        except Exception as e:
            self.logger.log_error(f"Error during cleanup: {str(e)}")
            raise

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