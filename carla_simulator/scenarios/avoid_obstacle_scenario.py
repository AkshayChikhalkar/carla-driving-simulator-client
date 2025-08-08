import carla
import math
import random
import time
from typing import Optional, List, Dict, Any
from carla_simulator.scenarios.base_scenario import BaseScenario
from carla_simulator.core.interfaces import IWorldManager, IVehicleController, ILogger


class AvoidObstacleScenario(BaseScenario):
    """Scenario where vehicle must avoid multiple static obstacles in its path"""

    def __init__(
        self,
        world_manager: IWorldManager,
        vehicle_controller: IVehicleController,
        logger: ILogger,
        config: Dict[str, Any],
    ):
        super().__init__(world_manager, vehicle_controller, logger)

        # Load configuration parameters
        self.target_distance = config.get("target_distance", 100.0)
        self.obstacle_spacing = config.get("obstacle_spacing", 25.0)
        self.completion_distance = config.get("completion_distance", 110.0)
        self.collision_threshold = config.get("collision_threshold", 1.0)
        self.max_simulation_time = config.get("max_simulation_time", 120.0)
        self.waypoint_tolerance = config.get("waypoint_tolerance", 5.0)
        self.min_waypoint_distance = config.get("min_waypoint_distance", 30.0)
        self.max_waypoint_distance = config.get("max_waypoint_distance", 50.0)
        self.num_waypoints = config.get("num_waypoints", 3)
        self.num_obstacles = config.get("num_obstacles", 2)
        self.min_obstacle_distance = config.get("min_obstacle_distance", 15.0)
        self.obstacle_types = config.get(
            "obstacle_types", ["static.prop.streetbarrier01"]
        )

        # Scenario state
        self.obstacles: List[carla.Actor] = []
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0
        self._name = "Avoid Obstacle"
        self.scenario_started = False
        self._current_loc = (
            carla.Location()
        )  # Pre-allocate location for distance calculations
        self.start_time = 0.0
        self.obstacle_detection_range = 30.0  # Increased detection range
        self.avoidance_angle = 90.0  # Increased avoidance angle
        self.avoidance_distance = 15.0  # Distance to move away from obstacle
        self.current_avoidance_target = None  # Current avoidance target
        self.emergency_brake_distance = 10.0  # Distance to trigger emergency brake
        self.normal_speed = 30.0  # Normal speed in km/h
        self.avoidance_speed = 10.0  # Speed during avoidance in km/h
        self.logged_obstacles = set()  # Track which obstacles we've logged about
        self.emergency_brake_active = False  # Track if emergency brake is active
        self.road_boundary_distance = 3.0  # Distance to check for road boundaries
        self.current_speed = 0.0  # Current speed in km/h

    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def check_road_boundaries(self, location: carla.Location) -> bool:
        """Check if the location is within road boundaries"""
        try:
            # Get the waypoint at the current location
            waypoint = self.world_manager.get_map().get_waypoint(location)
            if not waypoint:
                return False

            # Get the road boundaries
            left_lane = waypoint.get_left_lane()
            right_lane = waypoint.get_right_lane()

            # Check if we're too close to the road edges
            if left_lane:
                left_distance = location.distance(left_lane.transform.location)
                if left_distance < self.road_boundary_distance:
                    return False

            if right_lane:
                right_distance = location.distance(right_lane.transform.location)
                if right_distance < self.road_boundary_distance:
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error checking road boundaries: {str(e)}")
            return False

    def apply_speed_control(self, target_speed: float):
        """Apply smooth speed control"""
        try:
            # Calculate speed difference
            speed_diff = target_speed - self.current_speed

            # Apply gradual speed changes
            if speed_diff > 0:
                # Accelerate gradually
                throttle = min(0.7, speed_diff / 10.0)
                brake = 0.0
            else:
                # Decelerate gradually
                throttle = 0.0
                brake = min(0.7, abs(speed_diff) / 10.0)

            control = carla.VehicleControl()
            control.throttle = throttle
            control.brake = brake
            self.vehicle.apply_control(control)
        except Exception as e:
            self.logger.error(f"Error applying speed control: {str(e)}")

    def find_alternative_path(
        self, current_loc: carla.Location, target_loc: carla.Location
    ) -> Optional[carla.Location]:
        """Find an alternative path around obstacles"""
        try:
            # Get current waypoint
            current_waypoint = self.world_manager.get_map().get_waypoint(current_loc)
            if not current_waypoint:
                return None

            # Get vehicle's forward direction
            vehicle_transform = self.vehicle.get_transform()
            forward_vector = vehicle_transform.get_forward_vector()

            # Try multiple angles for avoidance
            angles = [
                -self.avoidance_angle,
                self.avoidance_angle,
                -self.avoidance_angle / 2,
                self.avoidance_angle / 2,
            ]
            best_alt_waypoint = None
            max_clear_distance = 0.0

            for angle in angles:
                # Calculate avoidance point
                alt_angle = math.radians(angle)
                # Use vehicle's forward direction as reference
                alt_x = current_loc.x + self.avoidance_distance * (
                    forward_vector.x * math.cos(alt_angle)
                    - forward_vector.y * math.sin(alt_angle)
                )
                alt_y = current_loc.y + self.avoidance_distance * (
                    forward_vector.x * math.sin(alt_angle)
                    + forward_vector.y * math.cos(alt_angle)
                )

                # Get valid waypoint for alternative path
                alt_waypoint = self.world_manager.get_map().get_waypoint(
                    carla.Location(x=alt_x, y=alt_y, z=current_loc.z),
                    project_to_road=True,
                )

                if alt_waypoint:
                    # Check if this path is clear of obstacles and within road boundaries
                    if not self.check_road_boundaries(alt_waypoint.transform.location):
                        continue

                    min_obstacle_distance = float("inf")
                    for obstacle in self.obstacles:
                        obstacle_loc = obstacle.get_location()
                        dist = alt_waypoint.transform.location.distance(obstacle_loc)
                        min_obstacle_distance = min(min_obstacle_distance, dist)

                    # If this path is clearer than previous best, use it
                    if min_obstacle_distance > max_clear_distance:
                        max_clear_distance = min_obstacle_distance
                        best_alt_waypoint = alt_waypoint

            if (
                best_alt_waypoint
                and max_clear_distance > self.obstacle_detection_range / 2
            ):
                return best_alt_waypoint.transform.location

            return None
        except Exception as e:
            self.logger.error(f"Error finding alternative path: {str(e)}")
            return None

    def _generate_waypoints(self) -> None:
        """Generate waypoints for the route"""
        try:
            # Get current map
            world = self.world_manager.get_world()
            map = world.get_map()

            # Get spawn points
            spawn_points = map.get_spawn_points()
            if not spawn_points:
                self.logger.error("No spawn points found in map")
                return

            # Generate waypoints
            current_point = spawn_points[0]
            self.waypoints = []

            for _ in range(self.num_waypoints):
                # Calculate next point
                distance = random.uniform(
                    self.min_waypoint_distance, self.max_waypoint_distance
                )
                angle = random.uniform(-math.pi / 4, math.pi / 4)

                # Get valid waypoint on road
                waypoint = map.get_waypoint(
                    carla.Location(
                        current_point.location.x + distance * math.cos(angle),
                        current_point.location.y + distance * math.sin(angle),
                        current_point.location.z,
                    )
                )

                if waypoint:
                    self.waypoints.append(waypoint.transform.location)
                    current_point = waypoint.transform
                    self.logger.debug(f"Added waypoint at {current_point.location}")

            if not self.waypoints:
                self.logger.error("Failed to generate valid waypoints")
                return

            self.logger.debug(f"Generated {len(self.waypoints)} waypoints")

        except Exception as e:
            self.logger.error("Error generating waypoints", exc_info=e)

    def setup(self) -> None:
        """Setup scenario"""
        try:
            super().setup()

            # Generate waypoints first
            self._generate_waypoints()
            if not self.waypoints:
                self.logger.error("Failed to generate waypoints")
                return

            # Get world reference
            world = self.world_manager.world

            # Spawn obstacles
            spawn_transform = self.vehicle.get_transform()

            # Spawn first obstacle
            spawn_transform.location.x += 10.0
            spawn_transform.location.y += 2.0
            obstacle1 = self.world_manager.spawn_scenario_actor(
                "static.prop.trafficcone01", spawn_transform, actor_type="obstacle1"
            )

            if not obstacle1:
                self.logger.error("Failed to spawn first obstacle")
                return

            # Spawn second obstacle
            spawn_transform.location.x += 5.0
            spawn_transform.location.y -= 4.0
            obstacle2 = self.world_manager.spawn_scenario_actor(
                "static.prop.trafficcone01", spawn_transform, actor_type="obstacle2"
            )

            if not obstacle2:
                self.logger.error("Failed to spawn second obstacle")
                return

            # Add obstacles to list
            self.obstacles = [obstacle1, obstacle2]
            self.logger.debug(
                f"Spawned obstacles at locations {spawn_transform.location}"
            )

            # Initialize scenario state
            self.start_time = time.time()
            self.scenario_started = False
            self.emergency_brake_active = False
            self.current_avoidance_target = None
            self.logged_obstacles.clear()
            self.current_speed = 0.0

        except Exception as e:
            self.logger.error(f"Error in scenario setup: {str(e)}")
            raise

    def apply_emergency_brake(self):
        """Apply emergency brake"""
        try:
            if not self.emergency_brake_active:
                control = carla.VehicleControl()
                control.throttle = 0.0
                control.brake = 1.0
                control.steer = 0.0
                self.vehicle.apply_control(control)
                self.emergency_brake_active = True
                self.logger.warning("EMERGENCY BRAKE APPLIED!")
        except Exception as e:
            self.logger.error(f"Error applying emergency brake: {str(e)}")

    def update(self) -> None:
        """Update scenario state"""
        try:
            if self.is_completed():
                return

            # Check if max simulation time has been exceeded (only if max_simulation_time > 0)
            if self.max_simulation_time > 0:
                elapsed_time = time.time() - self.start_time
                if elapsed_time > self.max_simulation_time:
                    self.logger.error(
                        f"Scenario timed out after {elapsed_time:.1f} seconds"
                    )
                    self._set_completed(success=False)
                    return

            # Get current vehicle state using cached reference
            self._current_loc = self.vehicle.get_location()
            vehicle_velocity = self.vehicle.get_velocity()
            self.current_speed = vehicle_velocity.length() * 3.6  # Convert to km/h

            # Check if we're within road boundaries
            if not self.check_road_boundaries(self._current_loc):
                # self.logger.warning("Vehicle too close to road boundary!")
                self.apply_emergency_brake()
                return

            # Wait for vehicle to start moving before checking collisions
            if (
                not self.scenario_started and self.current_speed > 5.0
            ):  # Wait until vehicle reaches 5 km/h
                self.scenario_started = True
                self.logger.info("Vehicle started moving, beginning obstacle avoidance")

            # Only check for collisions after vehicle has started moving
            if self.scenario_started:
                # Check for obstacles in path
                obstacle_detected = False
                closest_obstacle_distance = float("inf")
                closest_obstacle = None

                for obstacle in self.obstacles:
                    obstacle_location = obstacle.get_location()
                    distance_to_obstacle = self._current_loc.distance(obstacle_location)

                    # Emergency brake if too close
                    if distance_to_obstacle < self.emergency_brake_distance:
                        self.apply_emergency_brake()
                        if obstacle.id not in self.logged_obstacles:
                            self.logger.debug(
                                f"Emergency brake triggered! Distance to obstacle: {distance_to_obstacle:.2f}m"
                            )
                            self.logged_obstacles.add(obstacle.id)
                        return
                    else:
                        self.emergency_brake_active = False

                    if distance_to_obstacle < self.collision_threshold:
                        self.logger.error("Collision with obstacle detected")
                        self._set_completed(success=False)
                        return

                    # Track closest obstacle
                    if distance_to_obstacle < closest_obstacle_distance:
                        closest_obstacle_distance = distance_to_obstacle
                        closest_obstacle = obstacle

                    # If obstacle is within detection range, try to avoid it
                    if distance_to_obstacle < self.obstacle_detection_range:
                        obstacle_detected = True
                        if obstacle.id not in self.logged_obstacles:
                            self.logger.info(
                                f"Obstacle detected at distance: {distance_to_obstacle:.2f}m"
                            )
                            self.logged_obstacles.add(obstacle.id)

                # If we have a current avoidance target, check if we should continue avoiding
                if self.current_avoidance_target:
                    distance_to_avoidance = self._current_loc.distance(
                        self.current_avoidance_target
                    )
                    if distance_to_avoidance < self.waypoint_tolerance:
                        self.current_avoidance_target = None
                        self.logger.info(
                            "Reached avoidance target, returning to original path"
                        )
                    else:
                        # Continue following avoidance target at reduced speed
                        self.vehicle_controller.set_target(
                            self.current_avoidance_target
                        )
                        self.apply_speed_control(self.avoidance_speed)
                        return

                # If obstacle detected and no current avoidance target, find new path
                if obstacle_detected and not self.current_avoidance_target:
                    if closest_obstacle:
                        alternative_target = self.find_alternative_path(
                            self._current_loc, self.waypoints[self.current_waypoint]
                        )
                        if alternative_target:
                            self.current_avoidance_target = alternative_target
                            self.vehicle_controller.set_target(alternative_target)
                            if closest_obstacle.id not in self.logged_obstacles:
                                self.logger.info(
                                    f"Taking alternative path to avoid obstacle at {closest_obstacle.get_location()}"
                                )
                                self.logged_obstacles.add(closest_obstacle.id)
                            self.apply_speed_control(self.avoidance_speed)
                            return

                # If no obstacles detected or no alternative path found, continue to original waypoint
                if not obstacle_detected or not self.current_avoidance_target:
                    self.vehicle_controller.set_target(
                        self.waypoints[self.current_waypoint]
                    )
                    self.apply_speed_control(self.normal_speed)

            # Check distance to current waypoint
            distance = self._current_loc.distance(self.waypoints[self.current_waypoint])

            if distance < self.waypoint_tolerance:
                self.current_waypoint += 1
                if self.current_waypoint >= len(self.waypoints):
                    self.logger.info("Successfully completed obstacle avoidance")
                    self._set_completed(success=True)
                else:
                    # Set next waypoint as target
                    self.vehicle_controller.set_target(
                        self.waypoints[self.current_waypoint]
                    )
                    self.logger.info(
                        f"Moving to waypoint {self.current_waypoint + 1}/{len(self.waypoints)}"
                    )

        except Exception as e:
            self.logger.error(f"Error in scenario update: {str(e)}")
            self.cleanup()
            raise

    def cleanup(self) -> None:
        """Clean up scenario resources"""
        try:
            super().cleanup()
            # Only clear state, actor destruction is handled by world_manager
            self.obstacles.clear()
            self.waypoints.clear()
        except Exception as e:
            self.logger.error(f"Error in scenario cleanup: {str(e)}")
            # Don't re-raise here to ensure cleanup continues
