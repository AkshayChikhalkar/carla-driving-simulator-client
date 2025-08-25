"""
Vehicle control system using the strategy pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import pygame
import carla
from typing import Optional, Dict, Any
import logging
import os
from datetime import datetime

from ..utils.config import ControllerConfig, LoggingConfig
from ..utils.logging import Logger
from ..core.interfaces import IWorldManager
import math


@dataclass
class VehicleControl:
    """Vehicle control state"""

    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    hand_brake: bool = False
    reverse: bool = False
    manual_gear_shift: bool = False
    gear: int = 1

    def __str__(self):
        return f"Control: throttle={self.throttle:.2f}, brake={self.brake:.2f}, steer={self.steer:.2f}, reverse={self.reverse}, gear={self.gear}"


class ControllerStrategy(ABC):
    """Abstract base class for controller strategies"""

    @abstractmethod
    def process_input(self) -> bool:
        """Process input and return whether to exit"""
        pass

    @abstractmethod
    def get_control(self) -> VehicleControl:
        """Get current control state"""
        pass


class KeyboardController(ControllerStrategy):
    """Keyboard-based vehicle control"""

    def __init__(self, config: ControllerConfig, logger: Optional[Logger] = None):
        self._control = VehicleControl()
        self._steer_cache = 0.0
        self.config = config
        # Set initial mode based on config type
        self.is_manual_mode = (
            config.type == "keyboard"
        )  # True for keyboard, False for autopilot
        self.logger = logger

        # Initialize Pygame with error handling
        try:
            pygame.init()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize pygame for keyboard controller: {str(e)}")
            raise RuntimeError(f"Keyboard controller cannot be initialized in this environment: {str(e)}")

        # Create key mapping dictionary
        key_map = {
            "w": pygame.K_w,
            "s": pygame.K_s,
            "a": pygame.K_a,
            "d": pygame.K_d,
            "space": pygame.K_SPACE,
            "b": pygame.K_b,
            "r": pygame.K_r,
            "q": pygame.K_q,
            "escape": pygame.K_ESCAPE,
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "1": pygame.K_1,
            "2": pygame.K_2,
            "3": pygame.K_3,
            "4": pygame.K_4,
            "5": pygame.K_5,
            "6": pygame.K_6,
            "m": pygame.K_m,
        }

        # Initialize key mappings
        self.keys = {
            "forward": [],
            "backward": [],
            "left": [],
            "right": [],
            "brake": [],
            "hand_brake": [],
            "reverse": [],
            "quit": [],
            "gear_1": [],
            "gear_2": [],
            "gear_3": [],
            "gear_4": [],
            "gear_5": [],
            "gear_6": [],
            "gear_r": [],
            "manual_mode": [],
        }

        # Map keys from config
        if hasattr(config, "keyboard"):
            for key in config.keyboard.forward:
                if key.lower() in key_map:
                    self.keys["forward"].append(key_map[key.lower()])
            for key in config.keyboard.backward:
                if key.lower() in key_map:
                    self.keys["backward"].append(key_map[key.lower()])
            for key in config.keyboard.left:
                if key.lower() in key_map:
                    self.keys["left"].append(key_map[key.lower()])
            for key in config.keyboard.right:
                if key.lower() in key_map:
                    self.keys["right"].append(key_map[key.lower()])
            for key in config.keyboard.brake:
                if key.lower() in key_map:
                    self.keys["brake"].append(key_map[key.lower()])
            for key in config.keyboard.hand_brake:
                if key.lower() in key_map:
                    self.keys["hand_brake"].append(key_map[key.lower()])
            for key in config.keyboard.reverse:
                if key.lower() in key_map:
                    self.keys["reverse"].append(key_map[key.lower()])
            for key in config.keyboard.quit:
                if key.lower() in key_map:
                    self.keys["quit"].append(key_map[key.lower()])

        # Add default keys if no keys were mapped
        if not self.keys["forward"]:
            self.keys["forward"] = [pygame.K_UP, pygame.K_w]
        if not self.keys["backward"]:
            self.keys["backward"] = [pygame.K_s, pygame.K_DOWN]
        if not self.keys["left"]:
            self.keys["left"] = [pygame.K_LEFT, pygame.K_a]
        if not self.keys["right"]:
            self.keys["right"] = [pygame.K_RIGHT, pygame.K_d]
        if not self.keys["brake"]:
            self.keys["brake"] = [pygame.K_SPACE]
        if not self.keys["hand_brake"]:
            self.keys["hand_brake"] = [pygame.K_b]
        if not self.keys["reverse"]:
            self.keys["reverse"] = [pygame.K_r]
        if not self.keys["quit"]:
            self.keys["quit"] = [pygame.K_ESCAPE]
        if not self.keys["manual_mode"]:
            self.keys["manual_mode"] = [pygame.K_m]

        # Add default gear keys
        if not self.keys["gear_1"]:
            self.keys["gear_1"] = [pygame.K_1]
        if not self.keys["gear_2"]:
            self.keys["gear_2"] = [pygame.K_2]
        if not self.keys["gear_3"]:
            self.keys["gear_3"] = [pygame.K_3]
        if not self.keys["gear_4"]:
            self.keys["gear_4"] = [pygame.K_4]
        if not self.keys["gear_5"]:
            self.keys["gear_5"] = [pygame.K_5]
        if not self.keys["gear_6"]:
            self.keys["gear_6"] = [pygame.K_6]
        if not self.keys["gear_r"]:
            self.keys["gear_r"] = [pygame.K_r]

        # Start in automatic mode
        self._control.manual_gear_shift = False
        self._control.gear = 1

        self.logger.debug("Keyboard controller initialization complete")
        self.logger.debug(f"Controller type: {config.type}")
        self.logger.debug(
            f"Initial mode: {'Manual' if self.is_manual_mode else 'Automatic'}"
        )

    def process_input(self) -> bool:
        """Process keyboard input"""
        # Skip input processing in headless mode
        if self.headless:
            return False

        # Process events first
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True

            if event.type == pygame.KEYDOWN:
                # Check quit
                if event.key in self.keys["quit"]:
                    self.logger.debug("Quitting simulation")
                    return True

                # Toggle manual/automatic mode
                if event.key in self.keys["manual_mode"]:
                    self.is_manual_mode = not self.is_manual_mode
                    self._control.manual_gear_shift = self.is_manual_mode
                    self.logger.debug(
                        f"Transmission: {'Manual' if self.is_manual_mode else 'Automatic'}"
                    )

                # Handle reverse toggle
                if event.key in self.keys["reverse"]:
                    if self._control.manual_gear_shift:
                        # In manual mode, toggle between reverse and forward
                        self._control.reverse = not self._control.reverse
                        if self._control.reverse:
                            self._control.gear = -1
                        else:
                            self._control.gear = 1
                        self.logger.debug(f"Reverse: {self._control.reverse}")

                # Handle gear changes in manual mode
                if self._control.manual_gear_shift:
                    if event.key in self.keys["gear_1"]:
                        self._control.gear = 1
                        self._control.reverse = False
                    elif event.key in self.keys["gear_2"]:
                        self._control.gear = 2
                        self._control.reverse = False
                    elif event.key in self.keys["gear_3"]:
                        self._control.gear = 3
                        self._control.reverse = False
                    elif event.key in self.keys["gear_4"]:
                        self._control.gear = 4
                        self._control.reverse = False
                    elif event.key in self.keys["gear_5"]:
                        self._control.gear = 5
                        self._control.reverse = False
                    elif event.key in self.keys["gear_6"]:
                        self._control.gear = 6
                        self._control.reverse = False
                    elif event.key in self.keys["gear_r"]:
                        self._control.gear = -1
                        self._control.reverse = True

        # Get keyboard state
        keys = pygame.key.get_pressed()

        # Update control based on key states
        self._control.throttle = (
            1.0 if any(keys[key] for key in self.keys["forward"]) else 0.0
        )
        self._control.brake = (
            1.0 if any(keys[key] for key in self.keys["brake"]) else 0.0
        )
        self._control.hand_brake = any(keys[key] for key in self.keys["hand_brake"])

        # Handle steering
        steer = 0.0
        if any(keys[key] for key in self.keys["left"]):
            steer = 1.0
        elif any(keys[key] for key in self.keys["right"]):
            steer = -1.0

        # Apply steering smoothing
        if steer != 0.0:
            self._steer_cache = steer
        else:
            self._steer_cache = 0.0

        self._control.steer = self._steer_cache

        return False

    def get_control(self) -> VehicleControl:
        """Get current control state based on keyboard input"""
        # Get current keyboard state
        keys = pygame.key.get_pressed()

        # Reset control values
        self._control.throttle = 0.0
        self._control.brake = 0.0
        self._control.steer = 0.0
        self._control.hand_brake = False

        # Process throttle/brake
        if any(keys[key] for key in self.keys["forward"]):
            self._control.throttle = 1.0
        elif any(keys[key] for key in self.keys["backward"]):
            self._control.brake = 1.0

        # Process steering
        if any(keys[key] for key in self.keys["left"]):
            self._control.steer = -0.7  # Reduced from -1.0 for smoother steering
        elif any(keys[key] for key in self.keys["right"]):
            self._control.steer = 0.7  # Reduced from 1.0 for smoother steering

        # Process hand brake
        if any(keys[key] for key in self.keys["hand_brake"]):
            self._control.hand_brake = True

        # Process brake key
        if any(keys[key] for key in self.keys["brake"]):
            self._control.brake = 1.0
            self._control.throttle = 0.0  # Ensure throttle is off when braking

        return self._control


class GamepadController(ControllerStrategy):
    """Gamepad-based vehicle control"""

    def __init__(self, config: ControllerConfig):
        self._control = VehicleControl()
        self.config = config
        pygame.joystick.init()

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        else:
            raise RuntimeError("No gamepad detected")

    def process_input(self) -> bool:
        """Process gamepad input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True

        # Throttle (right trigger)
        self._control.throttle = max(0, self.joystick.get_axis(5))

        # Brake (left trigger)
        self._control.brake = max(0, self.joystick.get_axis(4))

        # Steering (left stick)
        self._control.steer = self.joystick.get_axis(0)

        # Reverse (B button)
        if self.joystick.get_button(1):
            self._control.reverse = not self._control.reverse
            self._control.gear = -1 if self._control.reverse else 1

        return False

    def get_control(self) -> VehicleControl:
        """Get current control state"""
        return self._control


class AutopilotController(ControllerStrategy):
    """AI-based autopilot control"""

    def __init__(
        self,
        vehicle: carla.Vehicle,
        config: ControllerConfig,
        client: carla.Client,
        world_manager: Optional["IWorldManager"] = None,
    ):
        self.vehicle = vehicle
        self.config = config
        self.world_manager = world_manager

        # Get traffic manager from world manager if available, otherwise create new one
        if world_manager and hasattr(world_manager, "get_traffic_manager"):
            self.traffic_manager = world_manager.get_traffic_manager()
            if not self.traffic_manager:
                # If traffic manager doesn't exist yet, create it
                world_manager.setup_traffic()
                self.traffic_manager = world_manager.get_traffic_manager()
        else:
            # Fallback to creating new traffic manager if world manager not available
            self.traffic_manager = client.get_trafficmanager()

        # Get traffic settings from config
        traffic_config = getattr(config, "traffic", {})

        # Configure traffic manager settings
        distance_to_leading = traffic_config.get("distance_to_leading_vehicle", 2.5)
        speed_diff = traffic_config.get(
            "speed_difference_percentage", -100
        )  # Default to full speed
        ignore_lights = traffic_config.get("ignore_lights_percentage", 0)
        ignore_signs = traffic_config.get("ignore_signs_percentage", 0)

        # Apply traffic settings
        try:
            # Keep TM and world in sync; each tenant uses its own TM port
            self.traffic_manager.set_synchronous_mode(True)
            self.traffic_manager.set_global_distance_to_leading_vehicle(distance_to_leading)
            # Negative value means faster than limit in CARLA TM
            self.traffic_manager.vehicle_percentage_speed_difference(self.vehicle, speed_diff)
        except Exception:
            pass
        self.traffic_manager.ignore_lights_percentage(self.vehicle, ignore_lights)
        self.traffic_manager.ignore_signs_percentage(self.vehicle, ignore_signs)

        # Enable autopilot
        try:
            # Engage autopilot on the ego with the TM's port
            self.vehicle.set_autopilot(True, self.traffic_manager.get_port())
        except Exception:
            pass

        # Initialize control
        self._control = VehicleControl()

    def process_input(self) -> bool:
        """Process AI decisions"""
        # Get current control from autopilot
        carla_control = self.vehicle.get_control()

        # Convert to our control format
        self._control.throttle = carla_control.throttle
        self._control.brake = carla_control.brake
        self._control.steer = carla_control.steer
        self._control.hand_brake = carla_control.hand_brake
        self._control.reverse = carla_control.reverse
        self._control.manual_gear_shift = carla_control.manual_gear_shift
        self._control.gear = carla_control.gear

        return False

    def get_control(self) -> VehicleControl:
        """Get current control state"""
        return self._control

    def cleanup(self) -> None:
        """Clean up autopilot resources"""
        try:
            # Disable autopilot
            self.vehicle.set_autopilot(False)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error("Error cleaning up autopilot", exc_info=e)


class VehicleController:
    """Main vehicle controller class using the strategy pattern"""

    def __init__(self, config: ControllerConfig, headless: bool = False):
        """Initialize vehicle controller"""
        self.config = config
        self.headless = headless
        self._strategy = None
        self._vehicle = None
        self._target = None
        self._world_manager = None
        self._client = None
        self.logger = Logger()

    def set_strategy(self, strategy: ControllerStrategy) -> None:
        """Set the control strategy"""
        self._strategy = strategy

    def set_vehicle(self, vehicle: carla.Vehicle) -> None:
        """Set the controlled vehicle"""
        self._vehicle = vehicle

    def _update_vehicle_control_mode(self) -> None:
        """Update vehicle control mode based on config"""
        if not self._vehicle:
            return

        # Create appropriate controller based on config type
        if self.config.type == "keyboard":
            self._strategy = KeyboardController(self.config, self.logger)
        elif self.config.type == "gamepad":
            self._strategy = GamepadController(self.config)
        elif self.config.type == "autopilot":
            self._strategy = AutopilotController(
                self._vehicle, self.config, self._client, self._world_manager
            )
        else:
            raise ValueError(f"Unknown controller type: {self.config.type}")

    def get_vehicle(self) -> carla.Vehicle:
        """Get the controlled vehicle instance"""
        return self._vehicle

    def set_target(self, target: carla.Location) -> None:
        """Set the target location for navigation"""
        self._target = target
        if self._strategy and hasattr(self._strategy, "set_target"):
            self._strategy.set_target(target)

    def process_input(self) -> bool:
        """Process input using current strategy"""
        if not self._strategy:
            raise RuntimeError("No control strategy set")
        return self._strategy.process_input()

    def get_control(self, vehicle_state: Dict[str, Any]) -> carla.VehicleControl:
        """Get control commands using current strategy"""
        if not self._strategy:
            raise RuntimeError("No control strategy set")

        # Get control from the current strategy
        control = self._strategy.get_control()

        # Convert our VehicleControl to CARLA VehicleControl
        carla_control = carla.VehicleControl(
            throttle=float(control.throttle),
            steer=float(control.steer),
            brake=float(control.brake),
            hand_brake=bool(control.hand_brake),
            reverse=bool(control.reverse),
            manual_gear_shift=bool(control.manual_gear_shift),
            gear=int(control.gear),
        )

        return carla_control

    def initialize(self) -> bool:
        """Initialize the controller"""
        try:
            self.logger.info("Initializing controller")
            self.logger.info(f"Controller type: {self.__class__.__name__}")
            self.logger.info(f"Initial mode: {self.mode}")
            return True
        except Exception as e:
            self.logger.error("Error initializing controller", exc_info=e)
            return False

    def update(self) -> None:
        """Update controller state"""
        try:
            # Update control values
            self._update_control()

            # Apply control to vehicle
            self.vehicle.apply_control(self.control)

            # Log vehicle state in debug mode
            self.logger.debug(f"Vehicle state: {self.get_vehicle_state()}")

        except Exception as e:
            self.logger.error("Error updating controller", exc_info=e)

    def cleanup(self) -> None:
        """Clean up controller resources"""
        try:
            self.logger.debug("Cleaning up controller")
            # Clean up the strategy if it exists
            # if self._strategy and hasattr(self._strategy, 'cleanup'):
            #     self._strategy.cleanup()

            # Reset vehicle reference
            self._vehicle = None
            self._strategy = None

        except Exception as e:
            self.logger.error("Error cleaning up controller", exc_info=e)

    def get_vehicle_state(self) -> dict:
        """Get current vehicle state"""
        try:
            transform = self.vehicle.get_transform()
            velocity = self.vehicle.get_velocity()
            return {
                "location": (
                    transform.location.x,
                    transform.location.y,
                    transform.location.z,
                ),
                "rotation": (
                    transform.rotation.pitch,
                    transform.rotation.yaw,
                    transform.rotation.roll,
                ),
                "velocity": (velocity.x, velocity.y, velocity.z),
                "throttle": self.control.throttle,
                "brake": self.control.brake,
                "steer": self.control.steer,
                "gear": self.control.gear,
            }
        except Exception as e:
            self.logger.error("Error getting vehicle state", exc_info=e)
            return {}
