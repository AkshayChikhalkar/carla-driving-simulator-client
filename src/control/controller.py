"""
Vehicle control system using the strategy pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import pygame
import carla
from typing import Optional
import logging
import os
from datetime import datetime
from ..utils.config import ControllerConfig, LoggingConfig
from ..utils.logging import SimulationLogger

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

    def __init__(self, config: ControllerConfig, logger: Optional[SimulationLogger] = None):
        self._control = VehicleControl()
        self._steer_cache = 0.0
        self.config = config
        self.is_manual_mode = False  # Start in automatic mode
        self.debug_mode = getattr(config, 'debug_mode', False)
        self.logger = logger

        # Initialize Pygame
        pygame.init()

        # Create key mapping dictionary
        key_map = {
            'w': pygame.K_w,
            's': pygame.K_s,
            'a': pygame.K_a,
            'd': pygame.K_d,
            'space': pygame.K_SPACE,
            'b': pygame.K_b,
            'r': pygame.K_r,
            'q': pygame.K_q,
            'escape': pygame.K_ESCAPE,
            'up': pygame.K_UP,
            'down': pygame.K_DOWN,
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT,
            '1': pygame.K_1,
            '2': pygame.K_2,
            '3': pygame.K_3,
            '4': pygame.K_4,
            '5': pygame.K_5,
            '6': pygame.K_6,
            'm': pygame.K_m
        }

        # Log controller initialization
        if self.logger:
            self.logger.log_info("Initializing keyboard controller")
            self.logger.log_info("Controls:")
            self.logger.log_info("- W/Up Arrow: Accelerate")
            self.logger.log_info("- S/Down Arrow: Toggle Reverse")
            self.logger.log_info("- A/Left Arrow: Steer Left")
            self.logger.log_info("- D/Right Arrow: Steer Right")
            self.logger.log_info("- Space: Brake")
            self.logger.log_info("- B: Hand Brake")
            self.logger.log_info("- M: Toggle Manual/Automatic Transmission")
            self.logger.log_info("- 1-6: Select Gear (Manual Mode)")
            self.logger.log_info("- R: Reverse Gear (Manual Mode)")
            self.logger.log_info("- Q/Escape: Quit")

        # Initialize key mappings
        self.keys = {
            'forward': [],
            'backward': [],
            'left': [],
            'right': [],
            'brake': [],
            'hand_brake': [],
            'reverse': [],
            'quit': [],
            'gear_1': [],
            'gear_2': [],
            'gear_3': [],
            'gear_4': [],
            'gear_5': [],
            'gear_6': [],
            'gear_r': [],
            'manual_mode': []
        }

        # Map keys from config
        if hasattr(config, 'keyboard'):
            for key in config.keyboard.forward:
                if key.lower() in key_map:
                    self.keys['forward'].append(key_map[key.lower()])
            for key in config.keyboard.backward:
                if key.lower() in key_map:
                    self.keys['backward'].append(key_map[key.lower()])
            for key in config.keyboard.left:
                if key.lower() in key_map:
                    self.keys['left'].append(key_map[key.lower()])
            for key in config.keyboard.right:
                if key.lower() in key_map:
                    self.keys['right'].append(key_map[key.lower()])
            for key in config.keyboard.brake:
                if key.lower() in key_map:
                    self.keys['brake'].append(key_map[key.lower()])
            for key in config.keyboard.hand_brake:
                if key.lower() in key_map:
                    self.keys['hand_brake'].append(key_map[key.lower()])
            for key in config.keyboard.reverse:
                if key.lower() in key_map:
                    self.keys['reverse'].append(key_map[key.lower()])
            for key in config.keyboard.quit:
                if key.lower() in key_map:
                    self.keys['quit'].append(key_map[key.lower()])

        # Add default keys if no keys were mapped
        if not self.keys['forward']:
            self.keys['forward'] = [pygame.K_UP, pygame.K_w]
        if not self.keys['backward']:
            self.keys["backward"] = [pygame.K_s, pygame.K_DOWN]  # No backward keys
        if not self.keys['left']:
            self.keys['left'] = [pygame.K_LEFT, pygame.K_a]
        if not self.keys['right']:
            self.keys['right'] = [pygame.K_RIGHT, pygame.K_d]
        if not self.keys['brake']:
            self.keys['brake'] = [pygame.K_SPACE]  # Space is brake
        if not self.keys['hand_brake']:
            self.keys['hand_brake'] = [pygame.K_b]
        if not self.keys['reverse']:
            self.keys['reverse'] = [pygame.K_r]  # Both 's' and down arrow for reverse
        if not self.keys['quit']:
            self.keys['quit'] = [pygame.K_ESCAPE]
        if not self.keys['manual_mode']:
            self.keys['manual_mode'] = [pygame.K_m]  # M key to toggle manual/automatic mode

        # Add default gear keys
        if not self.keys['gear_1']:
            self.keys['gear_1'] = [pygame.K_1]
        if not self.keys['gear_2']:
            self.keys['gear_2'] = [pygame.K_2]
        if not self.keys['gear_3']:
            self.keys['gear_3'] = [pygame.K_3]
        if not self.keys['gear_4']:
            self.keys['gear_4'] = [pygame.K_4]
        if not self.keys['gear_5']:
            self.keys['gear_5'] = [pygame.K_5]
        if not self.keys['gear_6']:
            self.keys['gear_6'] = [pygame.K_6]
        if not self.keys['gear_r']:
            self.keys['gear_r'] = [pygame.K_r]

        # Start in automatic mode
        self._control.manual_gear_shift = False
        self._control.gear = 1

        if self.logger:
            self.logger.log_info("Keyboard controller initialization complete")

    def process_input(self) -> bool:
        """Process keyboard input"""
        # Process events first
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True

            if event.type == pygame.KEYDOWN:
                # Check quit
                if event.key in self.keys['quit']:
                    if self.logger:
                        self.logger.log_info("Quitting simulation")
                    return True

                # Toggle manual/automatic mode
                if event.key in self.keys['manual_mode']:
                    self.is_manual_mode = not self.is_manual_mode
                    self._control.manual_gear_shift = self.is_manual_mode
                    if self.logger:
                        self.logger.log_info(f"Transmission: {'Manual' if self.is_manual_mode else 'Automatic'}")

                # Handle reverse toggle
                if event.key in self.keys['reverse']:
                    if self._control.manual_gear_shift:
                        # In manual mode, toggle between reverse and forward
                        self._control.reverse = not self._control.reverse
                        self._control.gear = -1 if self._control.reverse else 1
                        if self.logger:
                            self.logger.log_info(f"Gear: {'Reverse' if self._control.reverse else 'Forward'}")
                    else:
                        # In automatic mode, just toggle reverse
                        self._control.reverse = not self._control.reverse
                        if self.logger:
                            self.logger.log_info(f"Gear: {'Reverse' if self._control.reverse else 'Forward'}")

                # Handle gear shifting (only in manual mode)
                if self.is_manual_mode:
                    if event.key in self.keys['gear_1']:
                        self._control.gear = 1
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 1")
                    elif event.key in self.keys['gear_2']:
                        self._control.gear = 2
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 2")
                    elif event.key in self.keys['gear_3']:
                        self._control.gear = 3
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 3")
                    elif event.key in self.keys['gear_4']:
                        self._control.gear = 4
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 4")
                    elif event.key in self.keys['gear_5']:
                        self._control.gear = 5
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 5")
                    elif event.key in self.keys['gear_6']:
                        self._control.gear = 6
                        self._control.reverse = False
                        if self.logger:
                            self.logger.log_info("Gear: 6")

                # Handle hand brake
                if event.key in self.keys['hand_brake']:
                    self._control.hand_brake = not self._control.hand_brake
                    if self.logger:
                        self.logger.log_info(f"Hand brake: {'On' if self._control.hand_brake else 'Off'}")

        # Get pressed keys
        keys = pygame.key.get_pressed()

        # Reset control values
        self._control.throttle = 0.0
        self._control.brake = 0.0
        self._steer_cache = 0.0

        # Throttle
        if any(keys[key] for key in self.keys['forward']):
            self._control.throttle = 1.0  # Set to full throttle when key is pressed
            if self.debug_mode and self.logger:
                self.logger.log_info("Throttle: 100%")

        # Brake (Space)
        if any(keys[key] for key in self.keys['brake']):
            self._control.brake = 1.0  # Set to full brake when key is pressed
            if self.debug_mode and self.logger:
                self.logger.log_info("Brake: 100%")

        # Steering
        if any(keys[key] for key in self.keys['left']):
            self._control.steer = -0.7  # Set to full left when key is pressed
            if self.debug_mode and self.logger:
                self.logger.log_info("Steering: Left")
        elif any(keys[key] for key in self.keys['right']):
            self._control.steer = 0.7  # Set to full right when key is pressed
            if self.debug_mode and self.logger:
                self.logger.log_info("Steering: Right")
        else:
            self._control.steer = 0.0  # Reset steering when no keys are pressed

        return False

    def get_control(self) -> VehicleControl:
        """Get current control state"""
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
    
    def __init__(self, vehicle: carla.Vehicle, config: ControllerConfig, client: carla.Client):
        self.vehicle = vehicle
        self.config = config
        
        # Get traffic manager directly from client
        traffic_manager = client.get_trafficmanager()
        traffic_manager.set_global_distance_to_leading_vehicle(2.5)
        traffic_manager.vehicle_percentage_speed_difference(self.vehicle, 0)  # No speed reduction
        traffic_manager.ignore_lights_percentage(self.vehicle, 100)
        traffic_manager.ignore_signs_percentage(self.vehicle, 100)
        traffic_manager.set_synchronous_mode(True)
        
        # Enable autopilot with traffic manager settings
        self.vehicle.set_autopilot(True, traffic_manager.get_port())
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

class VehicleController:
    """Main vehicle controller class"""
    
    def __init__(self, config: ControllerConfig):
        self.config = config
        self._strategy: Optional[ControllerStrategy] = None
    
    def set_strategy(self, strategy: ControllerStrategy) -> None:
        """Set the control strategy"""
        self._strategy = strategy
    
    def process_input(self) -> bool:
        """Process input using current strategy"""
        if self._strategy is None:
            raise RuntimeError("No control strategy set")
        return self._strategy.process_input()
    
    def get_control(self) -> VehicleControl:
        """Get control state from current strategy"""
        if self._strategy is None:
            raise RuntimeError("No control strategy set")
        return self._strategy.get_control() 
