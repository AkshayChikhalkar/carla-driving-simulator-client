import time
import math
import random
import carla
from typing import List, Optional
from src.scenarios.base_scenario import BaseScenario
from src.core.interfaces import IWorldManager, IVehicleController, ILogger

class FollowRouteScenario(BaseScenario):
    """Scenario where vehicle must follow a route with waypoints"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger,
                 num_waypoints: int = 5,
                 waypoint_tolerance: float = 5.0,
                 min_distance: float = 50.0,
                 max_distance: float = 100.0):
        super().__init__(world_manager, vehicle_controller, logger)
        self.num_waypoints = num_waypoints
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0
        self.waypoint_tolerance = waypoint_tolerance  # meters
        self.min_distance = min_distance  # meters
        self.max_distance = max_distance  # meters
        # Pre-allocate location for distance calculations
        self._current_loc = carla.Location()

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
                project_to_road=True
            )
            
            if waypoint:
                self.waypoints.append(waypoint.transform.location)
                current_point = waypoint.transform.location
                self.logger.log_info(f"Added waypoint at {current_point}")

        if not self.waypoints:
            self.logger.log_error("Failed to generate valid waypoints")
            self._set_completed(success=False)
            return

        # Set first waypoint as target
        self.vehicle_controller.set_target(self.waypoints[0])
        self.logger.log_info(f"Follow route scenario started with {len(self.waypoints)} waypoints")

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
                self.vehicle_controller.set_target(self.waypoints[self.current_waypoint])
                self.logger.log_info(
                    f"Reached waypoint {self.current_waypoint}/{len(self.waypoints)}"
                )

    def cleanup(self) -> None:
        """Clean up scenario resources"""
        super().cleanup()
        self.waypoints.clear() 