"""
Keyboard control module for the CARLA Driving Simulator.
Handles keyboard input and vehicle control.
"""

import carla
import pygame
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ControlState:
    """Represents the current control state."""

    throttle: float = 0.0
    steer: float = 0.0
    brake: float = 0.0
    hand_brake: bool = False
    reverse: bool = False


class KeyboardControl:
    """Handles keyboard input and vehicle control."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize keyboard control.

        Args:
            config: Control configuration dictionary
        """
        self.config = config
        self.control_state = ControlState()
        self._setup_control_mapping()

    def _setup_control_mapping(self):
        """Set up keyboard control mapping using configuration."""
        # Create a mapping of key names to pygame key constants
        key_map = {
            "w": pygame.K_w,
            "s": pygame.K_s,
            "a": pygame.K_a,
            "d": pygame.K_d,
            "space": pygame.K_SPACE,
            "q": pygame.K_q,
            "r": pygame.K_r,
        }

        # Set up control mapping using configuration
        self.control_mapping = {
            key_map[self.config["throttle_up"]]: ("throttle", 1.0),
            key_map[self.config["throttle_down"]]: ("throttle", -1.0),
            key_map[self.config["steer_left"]]: ("steer", -1.0),
            key_map[self.config["steer_right"]]: ("steer", 1.0),
            key_map[self.config["brake"]]: ("brake", 1.0),
            key_map[self.config["hand_brake"]]: ("hand_brake", True),
            key_map[self.config["reverse"]]: ("reverse", True),
        }

    def process_events(self) -> bool:
        """
        Process keyboard events.

        Returns:
            True if simulation should continue, False if should quit
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYUP:
                self._handle_key_up(event.key)
            if event.type == pygame.KEYDOWN:
                self._handle_key_down(event.key)
        return True

    def _handle_key_up(self, key: int):
        """
        Handle key release events.

        Args:
            key: Pygame key code
        """
        if key in self.control_mapping:
            control_type, _ = self.control_mapping[key]
            if control_type == "throttle":
                self.control_state.throttle = 0.0
            elif control_type == "steer":
                self.control_state.steer = 0.0
            elif control_type == "brake":
                self.control_state.brake = 0.0
            elif control_type == "hand_brake":
                self.control_state.hand_brake = False
            elif control_type == "reverse":
                self.control_state.reverse = False

    def _handle_key_down(self, key: int):
        """
        Handle key press events.

        Args:
            key: Pygame key code
        """
        if key in self.control_mapping:
            control_type, value = self.control_mapping[key]
            if control_type == "throttle":
                self.control_state.throttle = value
            elif control_type == "steer":
                self.control_state.steer = value
            elif control_type == "brake":
                self.control_state.brake = value
            elif control_type == "hand_brake":
                self.control_state.hand_brake = value
            elif control_type == "reverse":
                self.control_state.reverse = value

    def get_control(self) -> carla.VehicleControl:
        """
        Get the current vehicle control command.

        Returns:
            CARLA vehicle control command
        """
        control = carla.VehicleControl()
        control.throttle = abs(self.control_state.throttle)
        control.steer = self.control_state.steer
        control.brake = self.control_state.brake
        control.hand_brake = self.control_state.hand_brake
        control.reverse = self.control_state.reverse
        return control

    def get_control_state(self) -> Dict[str, Any]:
        """
        Get the current control state as a dictionary.

        Returns:
            Dictionary containing control state
        """
        return {
            "throttle": self.control_state.throttle,
            "steer": self.control_state.steer,
            "brake": self.control_state.brake,
            "hand_brake": self.control_state.hand_brake,
            "reverse": self.control_state.reverse,
        }
