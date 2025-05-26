from typing import Dict, Any
import time
from src.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger

class BaseScenario(IScenario):
    """Base class for all scenarios implementing the IScenario interface"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger):
        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.logger = logger
        self._is_completed = False
        self._is_successful = False
        self._start_time = None
        self._completion_time = None
        # Cache vehicle reference
        self._vehicle = None

    def setup(self) -> None:
        """Base setup method to be overridden by specific scenarios"""
        self._start_time = time.time()
        self._vehicle = self.vehicle_controller.get_vehicle()
        self.logger.log_info(f"Starting scenario: {self.__class__.__name__}")

    def update(self) -> None:
        """Base update method to be overridden by specific scenarios"""
        pass

    def cleanup(self) -> None:
        """Base cleanup method to be overridden by specific scenarios"""
        if self._is_completed:
            self._completion_time = time.time() - self._start_time
            status = "successfully" if self._is_successful else "unsuccessfully"
            self.logger.log_info(
                f"Scenario completed {status} in {self._completion_time:.1f} seconds"
            )

    def is_completed(self) -> bool:
        """Check if scenario is completed"""
        return self._is_completed

    def is_successful(self) -> bool:
        """Check if scenario was successful"""
        return self._is_successful

    def _set_completed(self, success: bool = True) -> None:
        """Internal method to mark scenario as completed"""
        self._is_completed = True
        self._is_successful = success

    @property
    def vehicle(self):
        """Get cached vehicle reference"""
        return self._vehicle 