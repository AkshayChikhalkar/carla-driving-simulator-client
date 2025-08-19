"""
Manages the simulation state, events, and metrics.
"""

from logging import Logger
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum, auto
import carla
from carla_simulator.control.controller import VehicleController
from carla_simulator.core.interfaces import (
    ISimulationManager,
    IScenario,
    IWorldManager,
    IVehicleController,
    ISensorManager,
    ILogger,
)
from carla_simulator.core.sensors import SensorManager
from carla_simulator.core.world_manager import WorldManager
from carla_simulator.utils.config import load_config
from ..visualization.display_manager import VehicleState
import math


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
    """Manages the simulation lifecycle"""

    def __init__(self, config_path: str):
        """Initialize simulation manager"""
        self.config = load_config(config_path)
        self.world_manager = None
        self.sensor_manager = None
        self.vehicle = None
        self.vehicle_bp = None
        self.map_name = self.config.world_config.map_name
        self.logger = Logger()
        self._state = SimulationState()

    def connect(self) -> bool:
        """Connect to the simulation server"""
        try:
            self.world_manager = WorldManager(
                self.config.server_config,
                self.config.world_config,
                self.config.vehicle_config,
            )
            return True
        except Exception as e:
            self.logger.error("Error connecting to simulation server", exc_info=e)
            return False

    def setup(self) -> bool:
        """Setup simulation components"""
        try:
            # Initialize components
            self.world_manager = WorldManager(
                self.client, self.config.world, self.config.vehicle
            )
            self.vehicle_controller = VehicleController(
                self.world_manager, self.config.vehicle
            )
            self.sensor_manager = SensorManager(self.world_manager, self.config.sensors)

            # Setup sensors
            self.sensor_manager.setup_sensors()

            return True
        except Exception as e:
            self.logger.error("Error setting up simulation", exc_info=e)
            return False

    def run(self) -> None:
        """Run the simulation"""
        try:
            if not self._state.is_running:
                self._state.is_running = True
                self.logger.info("Starting simulation")

                # Main simulation loop
                while self._state.is_running:
                    # Update vehicle state
                    if self.vehicle:
                        self._update_vehicle_state()

                    # Process sensor data
                    if self.sensor_manager:
                        self.sensor_manager.process_data()

                    # Tick the world
                    self.world_manager.world.tick()

            else:
                self.logger.warning("Simulation is already running")

        except Exception as e:
            self.logger.error("Error in simulation loop", exc_info=e)
            self._state.is_running = False
            raise

    def stop(self) -> None:
        """Stop the simulation"""
        self._state.is_running = False
        self.logger.info("Stopping simulation")

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

            # Create vehicle
            self.vehicle = self.world_manager.create_vehicle()
            if not self.vehicle:
                self.logger.error("Failed to create vehicle")
                return False

            self.logger.info("Simulation initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Error initializing simulation", exc_info=e)
            return False

    def _update_vehicle_state(self) -> None:
        """Update vehicle state"""
        try:
            if self.vehicle:
                # Get vehicle transform
                transform = self.vehicle.get_transform()

                # Get vehicle velocity
                velocity = self.vehicle.get_velocity()
                speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)

                # Update state
                self._state.vehicle_state = VehicleState(
                    speed=speed,
                    position=(
                        transform.location.x,
                        transform.location.y,
                        transform.location.z,
                    ),
                    rotation=(
                        transform.rotation.pitch,
                        transform.rotation.yaw,
                        transform.rotation.roll,
                    ),
                    acceleration=0.0,  # TODO: Calculate acceleration
                    angular_velocity=0.0,  # TODO: Calculate angular velocity
                    collision_intensity=0.0,  # TODO: Get collision data
                    distance_to_target=float(
                        "inf"
                    ),  # TODO: Calculate distance to target
                    heading_to_target=0.0,  # TODO: Calculate heading to target
                    heading_difference=0.0,  # TODO: Calculate heading difference
                )

        except Exception as e:
            self.logger.error("Error updating vehicle state", exc_info=e)

    def check_events(self) -> tuple[SimulationEvent, str]:
        """Check for significant events based on current state"""
        event = SimulationEvent.NONE
        details = ""

        # Check speed changes
        if (
            abs(self._state.speed - self.last_speed)
            > self.config["speed_change_threshold"]
        ):
            event = SimulationEvent.SPEED_CHANGE
            details = (
                f"Speed change: {self.last_speed:.1f} -> {self._state.speed:.1f} km/h"
            )

        # Check target reached
        elif (
            self._state.distance_to_target < self.config["target_tolerance"]
            and not self.is_finished
        ):
            event = SimulationEvent.TARGET_REACHED
            details = (
                f"Target reached at distance: {self._state.distance_to_target:.1f}m"
            )
            self.is_finished = True

        # Check speed limit
        elif self._state.speed > self.config["max_speed"]:
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
        return elapsed_time < self.config["simulation_time"] and not self.is_finished

    def set_scenario(self, scenario: IScenario) -> None:
        """Set the current scenario"""
        self._scenario = scenario

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
                self.vehicle_bp, spawn_points[0]
            )

            if not self.vehicle:
                self.logger.error("Failed to spawn vehicle")
                return False

            self.logger.info("Vehicle spawned successfully")
            return True

        except Exception as e:
            self.logger.error("Error spawning vehicle", exc_info=e)
            return False
