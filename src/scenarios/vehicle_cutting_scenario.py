import carla
import math
import random
import time
from typing import Optional, List, Dict, Any
from src.scenarios.base_scenario import BaseScenario
from src.core.interfaces import IWorldManager, IVehicleController, ILogger

class VehicleCuttingScenario(BaseScenario):
    """Scenario where another vehicle cuts in front of the ego vehicle"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger,
                 config: Dict[str, Any]):
        super().__init__(world_manager, vehicle_controller, logger)
        
        # Load configuration parameters
        self.target_distance = config.get('target_distance', 100.0)
        self.cutting_distance = config.get('cutting_distance', 30.0)
        self.completion_distance = config.get('completion_distance', 110.0)
        self.collision_threshold = config.get('collision_threshold', 1.0)
        self.max_simulation_time = config.get('max_simulation_time', 120.0)
        self.waypoint_tolerance = config.get('waypoint_tolerance', 5.0)
        self.min_waypoint_distance = config.get('min_waypoint_distance', 30.0)
        self.max_waypoint_distance = config.get('max_waypoint_distance', 50.0)
        self.num_waypoints = config.get('num_waypoints', 3)
        self.cutting_vehicle_model = config.get('cutting_vehicle_model', "vehicle.tesla.model3")
        self.normal_speed = config.get('normal_speed', 30.0)
        self.cutting_speed = config.get('cutting_speed', 40.0)
        self.cutting_trigger_distance = config.get('cutting_trigger_distance', 20.0)
        
        # Scenario state
        self.cutting_vehicle: Optional[carla.Actor] = None
        self.waypoints: List[carla.Location] = []
        self.current_waypoint = 0  # Initialize current waypoint index
        self._name = "Vehicle Cutting"
        self.scenario_started = False
        self._current_loc = carla.Location()
        self.start_time = 0.0
        self.current_speed = 0.0  # Current speed in km/h
        self.cutting_triggered = False  # Track if cutting has been triggered
        self.cutting_completed = False  # Track if cutting maneuver is completed
        
    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def setup(self) -> None:
        """Setup the vehicle cutting scenario"""
        try:
            super().setup()
            self.start_time = time.time()
            current_point = self.vehicle.get_location()
            for _ in range(self.num_waypoints):
                distance = random.uniform(self.min_waypoint_distance, self.max_waypoint_distance)
                angle = random.uniform(0, 2 * math.pi)
                next_x = current_point.x + distance * math.cos(angle)
                next_y = current_point.y + distance * math.sin(angle)
                waypoint = self.world_manager.get_map().get_waypoint(
                    carla.Location(x=next_x, y=next_y, z=current_point.z),
                    project_to_road=True
                )
                if waypoint:
                    self.waypoints.append(waypoint.transform.location)
                    current_point = waypoint.transform.location
                    self.logger.info(f"Added waypoint at {current_point}")
            if not self.waypoints:
                self.logger.error("Failed to generate valid waypoints")
                self._set_completed(success=False)
                return
            self.vehicle_controller.set_target(self.waypoints[0])
            self.logger.info("Vehicle cutting scenario started")
            self.scenario_started = False
        except Exception as e:
            self.logger.error(f"Error in scenario setup: {str(e)}")
            self.cleanup()
            raise

    def spawn_cutting_vehicle(self):
        """Spawn the cutting vehicle"""
        try:
            if self.cutting_vehicle:
                return
            world = self.world_manager.get_world()
            blueprint_library = world.get_blueprint_library()
            blueprint = blueprint_library.find(self.cutting_vehicle_model)
            if not blueprint:
                self.logger.error(f"Failed to find blueprint for {self.cutting_vehicle_model}")
                return
            vehicle_transform = self.vehicle.get_transform()
            vehicle_rotation = vehicle_transform.rotation
            spawn_distance = 15.0
            spawn_x = self._current_loc.x + spawn_distance * math.cos(math.radians(vehicle_rotation.yaw + 90))
            spawn_y = self._current_loc.y + spawn_distance * math.sin(math.radians(vehicle_rotation.yaw + 90))
            spawn_waypoint = self.world_manager.get_map().get_waypoint(
                carla.Location(x=spawn_x, y=spawn_y, z=self._current_loc.z),
                project_to_road=True,
                lane_type=carla.LaneType.Driving
            )
            if not spawn_waypoint:
                self.logger.error("Failed to get valid waypoint for cutting vehicle spawn")
                return
            spawn_transform = spawn_waypoint.transform
            spawn_transform.location.z += 0.5
            try:
                self.cutting_vehicle = world.spawn_actor(
                    blueprint,
                    spawn_transform
                )
            except Exception as e:
                spawn_transform.location.x += 2.0
                spawn_transform.location.y += 2.0
                self.cutting_vehicle = world.spawn_actor(
                    blueprint,
                    spawn_transform
                )
            if not self.cutting_vehicle:
                self.logger.error("Failed to spawn cutting vehicle")
                return
            self.logger.info(f"Spawned cutting vehicle at location {spawn_transform.location}")
        except Exception as e:
            self.logger.error(f"Error spawning cutting vehicle: {str(e)}")

    def apply_speed_control(self, target_speed: float):
        """Apply smooth speed control"""
        try:
            speed_diff = target_speed - self.current_speed
            if speed_diff > 0:
                throttle = min(0.7, speed_diff / 10.0)
                brake = 0.0
            else:
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
            if self.max_simulation_time > 0:
                elapsed_time = time.time() - self.start_time
                if elapsed_time > self.max_simulation_time:
                    self.logger.error(f"Scenario timed out after {elapsed_time:.1f} seconds")
                    self._set_completed(success=False)
                    return
            self._current_loc = self.vehicle.get_location()
            vehicle_velocity = self.vehicle.get_velocity()
            self.current_speed = vehicle_velocity.length() * 3.6
            if not self.scenario_started and self.current_speed > 5.0:
                self.scenario_started = True
                self.logger.info("Vehicle started moving, beginning vehicle cutting test")
            if self.scenario_started:
                if not self.cutting_triggered and self.current_waypoint > 0:
                    distance_to_next = self._current_loc.distance(self.waypoints[self.current_waypoint])
                    if distance_to_next < self.cutting_trigger_distance:
                        self.spawn_cutting_vehicle()
                        self.cutting_triggered = True
                if self.cutting_vehicle and not self.cutting_completed:
                    cutting_loc = self.cutting_vehicle.get_location()
                    distance_to_cutting = self._current_loc.distance(cutting_loc)
                    if distance_to_cutting < self.collision_threshold:
                        self.logger.error("Collision with cutting vehicle detected")
                        self._set_completed(success=False)
                        return
                    if not self.cutting_completed:
                        current_waypoint = self.world_manager.get_map().get_waypoint(self._current_loc)
                        if current_waypoint:
                            next_waypoint = current_waypoint.next(5.0)[0]
                            vehicle_transform = self.vehicle.get_transform()
                            vehicle_rotation = vehicle_transform.rotation
                            cut_x = self._current_loc.x + 8.0 * math.cos(math.radians(vehicle_rotation.yaw))
                            cut_y = self._current_loc.y + 8.0 * math.sin(math.radians(vehicle_rotation.yaw))
                            cut_waypoint = self.world_manager.get_map().get_waypoint(
                                carla.Location(x=cut_x, y=cut_y, z=self._current_loc.z),
                                project_to_road=True
                            )
                            if cut_waypoint:
                                direction = cut_waypoint.transform.location - cutting_loc
                                direction = direction.make_unit_vector()
                                cutting_transform = self.cutting_vehicle.get_transform()
                                cutting_rotation = cutting_transform.rotation
                                target_angle = math.degrees(math.atan2(direction.y, direction.x))
                                current_angle = cutting_rotation.yaw
                                angle_diff = (target_angle - current_angle + 180) % 360 - 180
                                control = carla.VehicleControl()
                                control.throttle = 0.8
                                if angle_diff > 0:
                                    control.steer = -0.5
                                else:
                                    control.steer = -0.3
                                self.cutting_vehicle.apply_control(control)
                                if cutting_loc.distance(cut_waypoint.transform.location) < self.waypoint_tolerance:
                                    self.cutting_completed = True
                                    self.logger.info("Cutting vehicle completed its maneuver")
                self.vehicle_controller.set_target(self.waypoints[self.current_waypoint])
                self.apply_speed_control(self.normal_speed)
            distance = self._current_loc.distance(self.waypoints[self.current_waypoint])
            if distance < self.waypoint_tolerance:
                self.current_waypoint += 1
                if self.current_waypoint >= len(self.waypoints):
                    self.logger.info("Successfully completed vehicle cutting test")
                    self._set_completed(success=True)
                else:
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
            if self.cutting_vehicle:
                self.world_manager.destroy_actor(self.cutting_vehicle)
                self.cutting_vehicle = None
            self.waypoints.clear()
        except Exception as e:
            self.logger.error(f"Error in scenario cleanup: {str(e)}")
            # Don't re-raise here to ensure cleanup continues 