"""
Vehicle control system using the strategy pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import pygame
import carla
from typing import Optional
from ..utils.config import ControllerConfig

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
    
    def __init__(self, config: ControllerConfig):
        self._control = VehicleControl()
        self._steer_cache = 0.0
        self.config = config
        
        # Key mappings using direct pygame constants
        self.keys = {
            'forward': [pygame.K_UP, pygame.K_w],
            'backward': [pygame.K_DOWN, pygame.K_s],
            'left': [pygame.K_LEFT, pygame.K_a],
            'right': [pygame.K_RIGHT, pygame.K_d],
            'brake': [pygame.K_SPACE],
            'hand_brake': [pygame.K_b],
            'reverse': [pygame.K_r],
            'quit': [pygame.K_ESCAPE, pygame.K_q]
        }
        
        # Try to override defaults with config if provided
        try:
            if hasattr(config, 'keyboard'):
                key_map = {
                    'w': pygame.K_w,
                    's': pygame.K_s,
                    'a': pygame.K_a,
                    'd': pygame.K_d,
                    'space': pygame.K_SPACE,
                    'b': pygame.K_b,
                    'r': pygame.K_r
                }
                
                if hasattr(config.keyboard, 'throttle_up') and config.keyboard.throttle_up.lower() in key_map:
                    self.keys['forward'][1] = key_map[config.keyboard.throttle_up.lower()]
                if hasattr(config.keyboard, 'throttle_down') and config.keyboard.throttle_down.lower() in key_map:
                    self.keys['backward'][1] = key_map[config.keyboard.throttle_down.lower()]
                if hasattr(config.keyboard, 'steer_left') and config.keyboard.steer_left.lower() in key_map:
                    self.keys['left'][1] = key_map[config.keyboard.steer_left.lower()]
                if hasattr(config.keyboard, 'steer_right') and config.keyboard.steer_right.lower() in key_map:
                    self.keys['right'][1] = key_map[config.keyboard.steer_right.lower()]
                if hasattr(config.keyboard, 'brake') and config.keyboard.brake.lower() in key_map:
                    self.keys['brake'][0] = key_map[config.keyboard.brake.lower()]
                if hasattr(config.keyboard, 'hand_brake') and config.keyboard.hand_brake.lower() in key_map:
                    self.keys['hand_brake'][0] = key_map[config.keyboard.hand_brake.lower()]
                if hasattr(config.keyboard, 'reverse') and config.keyboard.reverse.lower() in key_map:
                    self.keys['reverse'][0] = key_map[config.keyboard.reverse.lower()]
        except Exception as e:
            print(f"Warning: Using default key bindings. Config error: {e}")
    
    def process_input(self) -> bool:
        """Process keyboard input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            
            if event.type == pygame.KEYUP:
                # Check quit
                if event.key in self.keys['quit']:
                    return True
                # Handle gear shift
                if event.key in self.keys['reverse']:
                    self._control.reverse = not self._control.reverse
                    self._control.gear = -1 if self._control.reverse else 1
                # Handle hand brake
                if event.key in self.keys['hand_brake']:
                    self._control.hand_brake = not self._control.hand_brake
        
        # Get pressed keys
        keys = pygame.key.get_pressed()
        
        # Throttle
        if any(keys[key] for key in self.keys['forward']):
            self._control.throttle = min(self._control.throttle + self.config.throttle_speed * 0.01, 1.0)
        else:
            self._control.throttle = 0.0
        
        # Brake
        if any(keys[key] for key in self.keys['backward']):
            self._control.brake = min(self._control.brake + self.config.brake_speed * 0.2, 1.0)
        else:
            self._control.brake = 0.0
        
        # Steering
        steer_increment = 5e-4 * self.config.steer_speed
        if any(keys[key] for key in self.keys['left']):
            self._steer_cache = max(-0.7, self._steer_cache - steer_increment)
        elif any(keys[key] for key in self.keys['right']):
            self._steer_cache = min(0.7, self._steer_cache + steer_increment)
        else:
            self._steer_cache = 0.0
        
        self._control.steer = round(self._steer_cache, 1)
        
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