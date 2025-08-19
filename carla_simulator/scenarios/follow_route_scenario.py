import time
import math
import random
import carla
from typing import List, Optional, Dict, Any
from carla_simulator.scenarios.base_scenario import BaseScenario
from carla_simulator.core.interfaces import IWorldManager, IVehicleController, ILogger


class FollowRouteScenario(BaseScenario):
    """Scenario where vehicle must follow a route with waypoints"""

    def __init__(
        self,
        world_manager: IWorldManager,
        vehicle_controller: IVehicleController,
        logger: ILogger,
        config: Dict[str, Any],
    ):
        super().__init__(world_manager, vehicle_controller, logger)

        # Load configuration parameters
        self.num_waypoints = config.get("num_waypoints", 5)
        self.waypoint_tolerance = config.get("waypoint_tolerance", 5.0)  # meters
        self.min_distance = config.get("min_distance", 50.0)  # meters
        self.max_distance = config.get("max_distance", 100.0)  # meters

        # Scenario state
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0
        # Pre-allocate location for distance calculations
        self._current_loc = carla.Location()
        self._name = "Follow Route"  # User-friendly display name

    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def setup(self) -> None:
        """Setup the route following scenario"""
        super().setup()

        # Get vehicle's current position
        current_point = self.vehicle.get_location()

        # Generate waypoints
        for _ in range(self.num_waypoints):
            # Get random point between min and max distance away
            distance = random.uniform(self.min_distance, self.max_distance)
            angle = random.uniform(0, 2 * math.pi)

            # Calculate next point
            next_x = current_point.x + distance * math.cos(angle)
            next_y = current_point.y + distance * math.sin(angle)

            # Get valid waypoint on road
            waypoint = self.world_manager.get_map().get_waypoint(
                carla.Location(x=next_x, y=next_y, z=current_point.z),
                project_to_road=True,
            )

            if waypoint:
                self.waypoints.append(waypoint.transform.location)
                current_point = waypoint.transform.location
                self.logger.debug(f"Added waypoint at {current_point}")

        if not self.waypoints:
            self.logger.error("Failed to generate valid waypoints")
            self._set_completed(success=False)
            return

        # Set first waypoint as target
        self.vehicle_controller.set_target(self.waypoints[0])
        self.logger.info(
            f"Follow route scenario started with {len(self.waypoints)} waypoints"
        )

    def update(self) -> None:
        """Update scenario state"""
        if self.is_completed():
            return

        # Get current vehicle state using cached reference
        self._current_loc = self.vehicle.get_location()

        # Check distance to current waypoint
        distance = self._current_loc.distance(self.waypoints[self.current_waypoint])

        if distance < self.waypoint_tolerance:
            self.current_waypoint += 1
            if self.current_waypoint >= len(self.waypoints):
                self._set_completed(success=True)
            else:
                # Set next waypoint as target
                self.vehicle_controller.set_target(
                    self.waypoints[self.current_waypoint]
                )
                self.logger.info(
                    f"Reached waypoint {self.current_waypoint}/{len(self.waypoints)}"
                )

    def cleanup(self) -> None:
        """Clean up scenario resources"""
        super().cleanup()
        self.waypoints.clear()

    def _generate_waypoints(self) -> None:
        """Generate waypoints for the route"""
        try:
            # Get map and spawn point
            map = self.world_manager.get_map()
            spawn_point = self.world_manager.get_random_spawn_point()
            current_point = spawn_point

            # Generate waypoints
            self.waypoints = []

            for _ in range(self.config.num_waypoints):
                # Get next waypoint
                waypoint = map.get_waypoint(current_point.location)
                if not waypoint:
                    self.logger.error("Failed to get waypoint")
                    continue

                # Add to waypoints list
                self.waypoints.append(waypoint)
                self.logger.debug(f"Added waypoint at {current_point}")

                # Update current point
                current_point = waypoint.transform

            if not self.waypoints:
                self.logger.error("Failed to generate valid waypoints")
                return

            self.logger.debug(f"Generated {len(self.waypoints)} waypoints")

        except Exception as e:
            self.logger.error("Error generating waypoints", exc_info=e)
