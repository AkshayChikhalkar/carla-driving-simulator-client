from typing import Dict, Any
import time
from carla_simulator.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger


class BaseScenario(IScenario):
    """Base class for all scenarios implementing the IScenario interface"""

    def __init__(
        self,
        world_manager: IWorldManager,
        vehicle_controller: IVehicleController,
        logger: ILogger,
    ):
        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.logger = logger
        self._is_completed = False
        self._is_successful = False
        self._start_time = time.time()  # Initialize start time in constructor
        self._completion_time = None
        self._max_duration = 120.0  # Default max duration in seconds
        # Cache vehicle reference
        self._vehicle = None
        self._cleanup_called = False
        self._elapsed_time = 0.0
        self._scenario_started = False
        self._name = self.__class__.__name__

    def setup(self) -> None:
        """Setup the scenario"""
        # Verify components are initialized
        if not self.world_manager:
            raise RuntimeError("World manager not initialized")
        if not self.vehicle_controller:
            raise RuntimeError("Vehicle controller not initialized")
        if not self.logger:
            raise RuntimeError("Logger not initialized")

        # Reset all state
        self._is_completed = False
        self._is_successful = False
        self._cleanup_called = False
        self._elapsed_time = 0.0
        self._scenario_started = False
        self._start_time = time.time()  # Reset start time in setup

        # Get vehicle reference
        self._vehicle = self.vehicle_controller.get_vehicle()
        if not self._vehicle:
            raise RuntimeError("Failed to get vehicle reference")

        self.logger.info(f"Starting scenario: {self._name}")

    def update(self) -> None:
        """Base update method to be overridden by specific scenarios"""
        if self._start_time is None:
            self._start_time = time.time()
            return

        # Calculate elapsed time
        self._elapsed_time = time.time() - self._start_time

        # Check for timeout
        if self._elapsed_time > self._max_duration:
            self.logger.error(
                f"Scenario timed out after {self._elapsed_time:.1f} seconds"
            )
            self._set_completed(False)
            return

    def cleanup(self) -> None:
        """Base cleanup method to be overridden by specific scenarios"""
        if not self._cleanup_called:
            self._cleanup_called = True
            # Ensure we have a valid elapsed time
            if self._start_time is not None:
                self._elapsed_time = time.time() - self._start_time

            if self._is_completed:
                self._completion_time = self._elapsed_time
                status = "successfully" if self._is_successful else "unsuccessfully"
                self.logger.info("================================")
                self.logger.info(f"Scenario completed {status}")
                self.logger.info(f"Duration: {self._completion_time:.1f} seconds")
                self.logger.info("================================")
            else:
                self.logger.info("================================")
                self.logger.info(f"Scenario stopped: {self._name}")
                self.logger.info(f"Status: Incomplete")
                self.logger.info(f"Duration: {self._elapsed_time:.1f} seconds")
                self.logger.info("================================")

    def is_completed(self) -> bool:
        """Check if scenario is completed"""
        return self._is_completed

    def is_successful(self) -> bool:
        """Check if scenario was successful"""
        return self._is_successful

    def _set_completed(self, success: bool = True) -> None:
        """Internal method to mark scenario as completed"""
        if not self._is_completed:  # Only set once
            self._is_completed = True
            self._is_successful = success
            self.cleanup()

    @property
    def vehicle(self):
        """Get cached vehicle reference"""
        return self._vehicle

    @property
    def elapsed_time(self) -> float:
        """Get the elapsed time since scenario start"""
        return self._elapsed_time

    @property
    def scenario_started(self) -> bool:
        """Get whether the scenario has started"""
        return self._scenario_started

    @scenario_started.setter
    def scenario_started(self, value: bool) -> None:
        """Set whether the scenario has started"""
        self._scenario_started = value
