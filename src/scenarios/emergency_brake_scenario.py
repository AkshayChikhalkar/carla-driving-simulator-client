import carla
import math
import random
import time
from typing import Optional, List, Dict, Any
from src.scenarios.base_scenario import BaseScenario
from src.core.interfaces import IWorldManager, IVehicleController, ILogger

class EmergencyBrakeScenario(BaseScenario):
    """Scenario where vehicle must perform emergency braking when obstacle appears"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger,
                 config: Dict[str, Any]):
        super().__init__(world_manager, vehicle_controller, logger)
        
        # Load configuration parameters
        self.target_distance = config.get('target_distance', 100.0)
        self.obstacle_distance = config.get('obstacle_distance', 30.0)
        self.completion_distance = config.get('completion_distance', 110.0)
        self.collision_threshold = config.get('collision_threshold', 1.0)
        self.max_simulation_time = config.get('max_simulation_time', 120.0)
        self.waypoint_tolerance = config.get('waypoint_tolerance', 5.0)
        self.min_waypoint_distance = config.get('min_waypoint_distance', 30.0)
        self.max_waypoint_distance = config.get('max_waypoint_distance', 50.0)
        self.num_waypoints = config.get('num_waypoints', 3)
        self.obstacle_type = config.get('obstacle_type', "static.prop.streetbarrier01")
        
        # Scenario state
        self.obstacle: Optional[carla.Actor] = None
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0
        self._name = "Emergency Brake"
        self.scenario_started = False
        self._current_loc = carla.Location()  # Pre-allocate location for distance calculations
        self.start_time = 0.0
        self.emergency_brake_distance = 15.0  # Distance to trigger emergency brake
        self.normal_speed = 30.0  # Normal speed in km/h
        self.current_speed = 0.0  # Current speed in km/h
        self.emergency_brake_active = False  # Track if emergency brake is active
        
    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def setup(self) -> None:
        """Setup the emergency brake scenario"""
        try:
            super().setup()
            
            # Record start time
            self.start_time = time.time()
            
            # Get vehicle's current position
            current_point = self.vehicle.get_location()
            
            # Generate waypoints
            self._generate_waypoints()
            
            if not self.waypoints:
                self.logger.error("Failed to generate valid waypoints")
                self._set_completed(success=False)
                return
            
            # Get the world and blueprint library
            world = self.world_manager.get_world()
            blueprint_library = world.get_blueprint_library()
            
            # Calculate obstacle position
            obstacle_waypoint = self.world_manager.get_map().get_waypoint(
                self.waypoints[0],
                project_to_road=True
            )
            
            if not obstacle_waypoint:
                self.logger.error("Failed to get obstacle waypoint")
                self._set_completed(success=False)
                return
            
            # Calculate position for obstacle
            direction = carla.Vector3D(
                self.waypoints[0].x - current_point.x,
                self.waypoints[0].y - current_point.y,
                0
            )
            direction = direction.make_unit_vector()
            
            obstacle_x = current_point.x + direction.x * self.obstacle_distance
            obstacle_y = current_point.y + direction.y * self.obstacle_distance
            
            # Get valid waypoint for obstacle
            obstacle_waypoint = self.world_manager.get_map().get_waypoint(
                carla.Location(x=obstacle_x, y=obstacle_y, z=current_point.z),
                project_to_road=True
            )
            
            if not obstacle_waypoint:
                self.logger.error("Failed to get valid waypoint for obstacle")
                self._set_completed(success=False)
                return
            
            # Get blueprint for obstacle
            blueprint = blueprint_library.find(self.obstacle_type)
            if not blueprint:
                self.logger.error(f"Failed to find blueprint for {self.obstacle_type}")
                self._set_completed(success=False)
                return
            
            # Spawn obstacle
            try:
                self.obstacle = world.spawn_actor(
                    blueprint,
                    carla.Transform(
                        obstacle_waypoint.transform.location,
                        obstacle_waypoint.transform.rotation
                    )
                )
                
                if not self.obstacle:
                    self.logger.error("Failed to spawn obstacle")
                    self._set_completed(success=False)
                    return
                    
                self.logger.debug(f"Spawned obstacle at location {obstacle_waypoint.transform.location}")
            except Exception as e:
                self.logger.error(f"Error spawning obstacle: {str(e)}")
                self._set_completed(success=False)
                return
                
            # Set first waypoint as target
            self.vehicle_controller.set_target(self.waypoints[0])
            self.logger.info("Emergency brake scenario started")
            
            # Give vehicle time to start moving
            self.scenario_started = False
            
        except Exception as e:
            self.logger.error(f"Error in scenario setup: {str(e)}")
            self.cleanup()
            raise

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
                distance = random.uniform(self.min_waypoint_distance, self.max_waypoint_distance)
                angle = random.uniform(-math.pi/4, math.pi/4)
                
                # Get valid waypoint on road
                waypoint = map.get_waypoint(
                    carla.Location(
                        current_point.location.x + distance * math.cos(angle),
                        current_point.location.y + distance * math.sin(angle),
                        current_point.location.z
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

    def update(self) -> None:
        """Update scenario state"""
        try:
            if self.is_completed():
                return
                
            # Check if max simulation time has been exceeded (only if max_simulation_time > 0)
            if self.max_simulation_time > 0:
                elapsed_time = time.time() - self.start_time
                if elapsed_time > self.max_simulation_time:
                    self.logger.error(f"Scenario timed out after {elapsed_time:.1f} seconds")
                    self._set_completed(success=False)
                    return
                
            # Get current vehicle state using cached reference
            self._current_loc = self.vehicle.get_location()
            vehicle_velocity = self.vehicle.get_velocity()
            self.current_speed = vehicle_velocity.length() * 3.6  # Convert to km/h
            
            # Wait for vehicle to start moving before checking collisions
            if not self.scenario_started and self.current_speed > 5.0:  # Wait until vehicle reaches 5 km/h
                self.scenario_started = True
                self.logger.info("Vehicle started moving, beginning emergency brake test")
            
            # Only check for collisions after vehicle has started moving
            if self.scenario_started and self.obstacle:
                # Check distance to obstacle
                obstacle_location = self.obstacle.get_location()
                distance_to_obstacle = self._current_loc.distance(obstacle_location)
                
                # Emergency brake if too close
                if distance_to_obstacle < self.emergency_brake_distance:
                    self.apply_emergency_brake()
                    self.logger.debug(f"Emergency brake triggered! Distance to obstacle: {distance_to_obstacle:.2f}m")
                    return
                else:
                    self.emergency_brake_active = False
                
                if distance_to_obstacle < self.collision_threshold:
                    self.logger.error("Collision with obstacle detected")
                    self._set_completed(success=False)
                    return
                
                # Continue to waypoint at normal speed
                self.vehicle_controller.set_target(self.waypoints[self.current_waypoint])
                self.apply_speed_control(self.normal_speed)
            
            # Check distance to current waypoint
            distance = self._current_loc.distance(self.waypoints[self.current_waypoint])
            
            if distance < self.waypoint_tolerance:
                self.current_waypoint += 1
                if self.current_waypoint >= len(self.waypoints):
                    self.logger.info("Successfully completed emergency brake test")
                    self._set_completed(success=True)
                else:
                    # Set next waypoint as target
                    self.vehicle_controller.set_target(self.waypoints[self.current_waypoint])
                    self.logger.info(f"Moving to waypoint {self.current_waypoint + 1}/{len(self.waypoints)}")
                    
        except Exception as e:
            self.logger.error(f"Error in scenario update: {str(e)}")
            self.cleanup()
            raise

    def cleanup(self) -> None:
        """Clean up scenario resources"""
        try:
            super().cleanup()
            if self.obstacle:
                self.world_manager.destroy_actor(self.obstacle)
                self.obstacle = None
            self.waypoints.clear()
        except Exception as e:
            self.logger.error(f"Error in scenario cleanup: {str(e)}")
            # Don't re-raise here to ensure cleanup continues 