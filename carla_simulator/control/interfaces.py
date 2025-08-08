from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import carla


class IInputProcessor(ABC):
    """Interface for input processing"""

    @abstractmethod
    def process_input(self) -> bool:
        """Process input and return whether to exit"""
        pass


class IControlStrategy(ABC):
    """Interface for control strategy"""

    @abstractmethod
    def get_control(self, vehicle_state: Dict[str, Any]) -> carla.VehicleControl:
        """Get control commands based on vehicle state"""
        pass


class IController(ABC):
    """Interface for vehicle controller"""

    @abstractmethod
    def set_strategy(self, strategy: IControlStrategy) -> None:
        """Set the control strategy"""
        pass

    @abstractmethod
    def get_control(self, vehicle_state: Dict[str, Any]) -> carla.VehicleControl:
        """Get control commands"""
        pass


class IManualController(IController, IInputProcessor):
    """Interface for manual control (keyboard/gamepad)"""

    @abstractmethod
    def get_input_state(self) -> Dict[str, Any]:
        """Get current input state"""
        pass


class IAutopilotController(IController):
    """Interface for autopilot control"""

    @abstractmethod
    def set_target(self, target: carla.Location) -> None:
        """Set target location"""
        pass

    @abstractmethod
    def update_route(self, waypoints: list[carla.Location]) -> None:
        """Update route waypoints"""
        pass
