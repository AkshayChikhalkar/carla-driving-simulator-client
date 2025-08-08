from abc import ABC, abstractmethod
from typing import Protocol, Any, Dict
import carla


class ISimulationManager(ABC):
    """Interface for managing the simulation lifecycle"""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the simulation server"""
        pass

    @abstractmethod
    def setup(self) -> None:
        """Setup the simulation environment"""
        pass

    @abstractmethod
    def run(self) -> None:
        """Run the simulation"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up simulation resources"""
        pass


class IScenario(ABC):
    """Interface for simulation scenarios"""

    @abstractmethod
    def setup(self) -> None:
        """Setup the scenario"""
        pass

    @abstractmethod
    def update(self) -> None:
        """Update scenario state"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up scenario resources"""
        pass

    @abstractmethod
    def is_completed(self) -> bool:
        """Check if scenario is completed"""
        pass

    @abstractmethod
    def is_successful(self) -> bool:
        """Check if scenario was successful"""
        pass


class IVehicleController(ABC):
    """Interface for vehicle control"""

    @abstractmethod
    def get_control(self, vehicle_state: Dict[str, Any]) -> carla.VehicleControl:
        """Get control commands based on vehicle state"""
        pass

    @abstractmethod
    def get_vehicle(self) -> carla.Vehicle:
        """Get the controlled vehicle instance"""
        pass

    @abstractmethod
    def set_target(self, target: carla.Location) -> None:
        """Set the target location for the vehicle"""
        pass


class ISensorManager(ABC):
    """Interface for managing vehicle sensors"""

    @abstractmethod
    def setup_sensors(self) -> None:
        """Setup vehicle sensors"""
        pass

    @abstractmethod
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get data from all sensors"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up sensor resources"""
        pass


class IWorldManager(ABC):
    """Interface for managing the simulation world"""

    @abstractmethod
    def get_world(self) -> carla.World:
        """Get the CARLA world instance"""
        pass

    @abstractmethod
    def get_map(self) -> carla.Map:
        """Get the current map"""
        pass

    @abstractmethod
    def spawn_actor(
        self, blueprint: carla.ActorBlueprint, transform: carla.Transform
    ) -> carla.Actor:
        """Spawn an actor in the world"""
        pass

    @abstractmethod
    def destroy_actor(self, actor: carla.Actor) -> None:
        """Destroy an actor from the world"""
        pass


class ILogger(ABC):
    """Interface for logging functionality"""

    @abstractmethod
    def info(self, message: str) -> None:
        """Log informational message"""
        pass

    @abstractmethod
    def error(self, message: str) -> None:
        """Log error message"""
        pass

    @abstractmethod
    def debug(self, message: str) -> None:
        """Log debug message"""
        pass

    @abstractmethod
    def warning(self, message: str) -> None:
        """Log warning message"""
        pass

    @abstractmethod
    def log_vehicle_state(self, state: Dict[str, Any]) -> None:
        """Log vehicle state data"""
        pass
