"""
Vehicle control system for CARLA simulation.
"""

import carla
import math
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from carla_simulator.utils.logging import Logger
from .interfaces import IVehicleController
from ..utils.config import VehicleConfig
from ..utils.default_config import SIMULATION_CONFIG


@dataclass
class ControlState:
    """Current control state of the vehicle"""

    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    hand_brake: bool = False
    reverse: bool = False


class VehicleController(IVehicleController):
    """Controls vehicle movement and behavior"""

    def __init__(self, vehicle: carla.Vehicle, config: VehicleConfig):
        """Initialize the vehicle controller"""
        self.vehicle = vehicle
        self.config = config
        self.control_state = ControlState()
        self.logger = Logger()

        # Get configuration values with fallbacks
        self.max_speed = getattr(config, "max_speed", 30.0)  # m/s
        self.max_steer_angle = getattr(config, "max_steer_angle", 70.0)  # degrees
        self.max_throttle = getattr(config, "max_throttle", 1.0)
        self.max_brake = getattr(config, "max_brake", 1.0)
        self.steer_sensitivity = getattr(config, "steer_sensitivity", 1.0)

        # Initialize control
        self._reset_control()

    def _reset_control(self) -> None:
        """Reset control to neutral state"""
        self.control_state = ControlState()
        self._apply_control()

    def _apply_control(self) -> None:
        """Apply current control state to vehicle"""
        try:
            control = carla.VehicleControl()
            control.throttle = self.control_state.throttle
            control.brake = self.control_state.brake
            control.steer = self.control_state.steer
            control.hand_brake = self.control_state.hand_brake
            control.reverse = self.control_state.reverse

            self.vehicle.apply_control(control)

        except Exception as e:
            self.logger.error(f"Error applying control: {str(e)}")

    def set_throttle(self, value: float) -> None:
        """Set throttle value (0.0 to 1.0)"""
        self.control_state.throttle = max(0.0, min(value, self.max_throttle))
        self._apply_control()

    def set_brake(self, value: float) -> None:
        """Set brake value (0.0 to 1.0)"""
        self.control_state.brake = max(0.0, min(value, self.max_brake))
        self._apply_control()

    def set_steer(self, value: float) -> None:
        """Set steering value (-1.0 to 1.0)"""
        # Convert to degrees and apply sensitivity
        steer_angle = value * self.max_steer_angle * self.steer_sensitivity
        # Normalize to -1.0 to 1.0 range
        self.control_state.steer = max(
            -1.0, min(steer_angle / self.max_steer_angle, 1.0)
        )
        self._apply_control()

    def set_hand_brake(self, value: bool) -> None:
        """Set hand brake state"""
        self.control_state.hand_brake = value
        self._apply_control()

    def set_reverse(self, value: bool) -> None:
        """Set reverse gear state"""
        self.control_state.reverse = value
        self._apply_control()

    def get_control_state(self) -> Dict[str, Any]:
        """Get current control state"""
        return {
            "throttle": self.control_state.throttle,
            "brake": self.control_state.brake,
            "steer": self.control_state.steer,
            "hand_brake": self.control_state.hand_brake,
            "reverse": self.control_state.reverse,
        }

    def get_vehicle_state(self) -> Dict[str, Any]:
        """Get current vehicle state"""
        if not self.vehicle:
            return {}

        velocity = self.vehicle.get_velocity()
        speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)

        return {
            "speed": speed,
            "location": self.vehicle.get_location(),
            "rotation": self.vehicle.get_transform().rotation,
            "acceleration": self.vehicle.get_acceleration(),
            "angular_velocity": self.vehicle.get_angular_velocity(),
        }

    def cleanup(self) -> None:
        """Clean up controller resources"""
        try:
            self._reset_control()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise
