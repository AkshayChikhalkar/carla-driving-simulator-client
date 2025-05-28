import carla
import math
import time
from typing import Optional
from src.scenarios.base_scenario import BaseScenario
from src.core.interfaces import IWorldManager, IVehicleController, ILogger

class VehicleCuttingScenario(BaseScenario):
    """Scenario where another vehicle cuts in front of the ego vehicle"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger,
                 target_speed: float = 40.0,
                 spawn_distance: float = 20.0,
                 lateral_offset: float = 5.0,
                 cutting_vehicle_model: str = "vehicle.fuso.mitsubishi"):
        super().__init__(world_manager, vehicle_controller, logger)
        self.target_speed = target_speed  # km/h
        self.spawn_distance = spawn_distance
        self.lateral_offset = lateral_offset
        self.cutting_vehicle_model = cutting_vehicle_model
        
        # Scenario state
        self.cutting_vehicle: Optional[carla.Actor] = None
        self.cutting_vehicle_spawned = False
        self.cutting_completed = False
        self._name = "Vehicle Cutting"
        
    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def setup(self) -> None:
        """Setup the vehicle cutting scenario"""
        try:
            super().setup()
            
            # Set initial target speed
            self.vehicle_controller.set_target_speed(self.target_speed)
            self.logger.info("Vehicle cutting scenario started")
        except Exception as e:
            self.logger.error(f"Error in scenario setup: {str(e)}")
            self.cleanup()
            raise

    def update(self) -> None:
        """Update scenario state"""
        try:
            if self.is_completed():
                return
                
            # Get current vehicle state
            vehicle_location = self.vehicle.get_location()
            vehicle_transform = self.vehicle.get_transform()
            vehicle_rotation = vehicle_transform.rotation
            
            # Spawn cutting vehicle when ego vehicle reaches trigger point
            if not self.cutting_vehicle_spawned:
                # Calculate spawn position
                spawn_x = vehicle_location.x + self.spawn_distance * math.cos(math.radians(vehicle_rotation.yaw))
                spawn_y = vehicle_location.y + self.spawn_distance * math.sin(math.radians(vehicle_rotation.yaw))
                spawn_location = carla.Location(x=spawn_x, y=spawn_y, z=vehicle_location.z)
                
                # Get the world and blueprint
                world = self.world_manager.get_world()
                blueprint = world.get_blueprint_library().find(self.cutting_vehicle_model)
                
                # Spawn cutting vehicle
                self.cutting_vehicle = world.spawn_actor(
                    blueprint,
                    carla.Transform(spawn_location, vehicle_rotation)
                )
                
                if self.cutting_vehicle:
                    self.cutting_vehicle_spawned = True
                    self.logger.info("Cutting vehicle spawned")
                    
                    # Set cutting vehicle's target speed and path
                    self._setup_cutting_vehicle_path()
                else:
                    self.logger.error("Failed to spawn cutting vehicle")
                    self._set_completed(success=False)
                    return
            
            # Monitor scenario progress
            if self.cutting_vehicle_spawned and not self.cutting_completed:
                cutting_location = self.cutting_vehicle.get_location()
                distance_to_cutting = vehicle_location.distance(cutting_location)
                
                # Check if cutting vehicle has completed its maneuver
                if distance_to_cutting < 5.0 and not self.cutting_completed:
                    self.cutting_completed = True
                    self.logger.info("Cutting vehicle completed maneuver")
                    
                    # Wait a few seconds to ensure safe response
                    time.sleep(3)
                    
                    # Check if ego vehicle maintained safe distance
                    if distance_to_cutting > 2.0:
                        self.logger.info("Successfully handled cutting vehicle")
                        self._set_completed(success=True)
                    else:
                        self.logger.error("Too close to cutting vehicle")
                        self._set_completed(success=False)
        except Exception as e:
            self.logger.error(f"Error in scenario update: {str(e)}")
            self.cleanup()
            raise

    def _setup_cutting_vehicle_path(self) -> None:
        """Setup the path and behavior for the cutting vehicle"""
        try:
            if not self.cutting_vehicle:
                return
                
            # Get current positions
            ego_location = self.vehicle.get_location()
            ego_transform = self.vehicle.get_transform()
            cutting_location = self.cutting_vehicle.get_location()
            
            # Calculate target position in front of ego vehicle
            target_x = ego_location.x + self.spawn_distance * math.cos(math.radians(ego_transform.rotation.yaw))
            target_y = ego_location.y + self.spawn_distance * math.sin(math.radians(ego_transform.rotation.yaw))
            target_location = carla.Location(x=target_x, y=target_y, z=ego_location.z)
            
            # Set cutting vehicle's target
            self.cutting_vehicle.set_target_location(target_location)
            self.cutting_vehicle.set_target_speed(self.target_speed * 1.2)  # Slightly faster than ego vehicle
        except Exception as e:
            self.logger.error(f"Error in cutting vehicle path setup: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Clean up scenario resources"""
        try:
            super().cleanup()
            if self.cutting_vehicle:
                self.world_manager.destroy_actor(self.cutting_vehicle)
                self.cutting_vehicle = None
        except Exception as e:
            self.logger.error(f"Error in scenario cleanup: {str(e)}")
            # Don't re-raise here to ensure cleanup continues 