"""
Web-based controller for handling keyboard and gamepad input from web interface.
This controller receives control commands via WebSocket instead of using pygame.
"""

import carla
from typing import Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..utils.config import ControllerConfig
from ..utils.logging import Logger
from .controller import ControllerStrategy, VehicleControl


@dataclass
class WebControlCommand:
    """Web control command structure"""
    throttle: float = 0.0
    brake: float = 0.0
    steer: float = 0.0
    hand_brake: bool = False
    reverse: bool = False
    manual_gear_shift: bool = False
    gear: int = 1
    quit: bool = False
    gamepad_index: int = 0  # Track which gamepad sent the command


class WebKeyboardController(ControllerStrategy):
    """Web-based keyboard controller that receives commands via WebSocket"""
    
    def __init__(self, config: ControllerConfig, logger: Optional[Logger] = None):
        self._control = VehicleControl()
        self.config = config
        self.logger = logger or Logger()
        self._current_command = WebControlCommand()
        self._last_command_time = 0.0
        
        self.logger.info("Web keyboard controller initialized")
    
    def update_command(self, command: WebControlCommand) -> None:
        """Update the current control command from web interface"""
        self._current_command = command
    
    def process_input(self) -> bool:
        """Process web input - returns True if quit requested"""
        # Check if quit was requested
        if self._current_command.quit:
            self.logger.info("Quit requested from web interface")
            return True
        
        # Update control based on current command
        self._control.throttle = self._current_command.throttle
        self._control.brake = self._current_command.brake
        self._control.steer = self._current_command.steer
        self._control.hand_brake = self._current_command.hand_brake
        self._control.reverse = self._current_command.reverse
        self._control.manual_gear_shift = self._current_command.manual_gear_shift
        self._control.gear = self._current_command.gear
        
        return False
    
    def get_control(self) -> VehicleControl:
        """Get current control state"""
        return self._control


class WebGamepadController(ControllerStrategy):
    """Web-based gamepad controller that receives commands via WebSocket"""
    
    def __init__(self, config: ControllerConfig, logger: Optional[Logger] = None):
        self._control = VehicleControl()
        self.config = config
        self.logger = logger or Logger()
        self._current_command = WebControlCommand()
        self._active_gamepads = {}  # Track multiple gamepads
        
        self.logger.info("Web gamepad controller initialized")
        # WebGamepadController specific initialization
    
    def update_gamepad_command(self, gamepad_index: int, command: WebControlCommand) -> None:
        """Update command for a specific gamepad"""
        self._active_gamepads[gamepad_index] = command
        self.logger.debug(f"Updated gamepad {gamepad_index} command: {command}")
    
    def get_primary_gamepad_command(self) -> WebControlCommand:
        """Get command from the primary (first) gamepad"""
        if self._active_gamepads:
            # Return command from the first available gamepad
            return next(iter(self._active_gamepads.values()))
        return self._current_command
    
    def update_command(self, command: WebControlCommand) -> None:
        """Update the current control command from web interface"""
        self._current_command = command
    
    def process_input(self) -> bool:
        """Process web input - returns True if quit requested"""
        # Check if quit was requested
        if self._current_command.quit:
            self.logger.info("Quit requested from web interface")
            return True
        
        # Update control based on current command
        self._control.throttle = self._current_command.throttle
        self._control.brake = self._current_command.brake
        self._control.steer = self._current_command.steer
        self._control.hand_brake = self._current_command.hand_brake
        self._control.reverse = self._current_command.reverse
        self._control.manual_gear_shift = self._current_command.manual_gear_shift
        self._control.gear = self._current_command.gear
        
        return False
    
    def get_control(self) -> VehicleControl:
        """Get current control state"""
        return self._control


class WebControllerManager:
    """Manager for web-based controllers"""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger()
        self._controllers: Dict[str, ControllerStrategy] = {}
    
    def create_controller(self, controller_type: str, config: ControllerConfig) -> ControllerStrategy:
        """Create a web-based controller"""
        if controller_type == "web_keyboard":
            controller = WebKeyboardController(config, self.logger)
        elif controller_type == "web_gamepad":
            controller = WebGamepadController(config, self.logger)
        else:
            raise ValueError(f"Unsupported web controller type: {controller_type}")
        
        self._controllers[controller_type] = controller
        return controller
    
    def update_controller_command(self, controller_type: str, command: WebControlCommand) -> None:
        """Update command for a specific controller"""
        if controller_type in self._controllers:
            controller = self._controllers[controller_type]
            if hasattr(controller, 'update_command'):
                controller.update_command(command)
            else:
                self.logger.warning(f"Controller {controller_type} does not support command updates")
        else:
            self.logger.warning(f"Controller {controller_type} not found")
    
    def get_controller(self, controller_type: str) -> Optional[ControllerStrategy]:
        """Get a controller by type"""
        return self._controllers.get(controller_type)
