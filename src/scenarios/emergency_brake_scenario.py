import carla
import math
from typing import Optional
from src.scenarios.base_scenario import BaseScenario
from src.core.interfaces import IWorldManager, IVehicleController, ILogger

class EmergencyBrakeScenario(BaseScenario):
    """Scenario where vehicle must perform emergency braking when obstacle appears"""
    
    def __init__(self, 
                 world_manager: IWorldManager,
                 vehicle_controller: IVehicleController,
                 logger: ILogger,
                 trigger_distance: float = 50.0,
                 target_speed: float = 40.0,
                 obstacle_type: str = "static.prop.streetbarrier"):
        super().__init__(world_manager, vehicle_controller, logger)
        self.trigger_distance = trigger_distance
        self.target_speed = target_speed  # km/h
        self.obstacle_type = obstacle_type
        
        # Scenario state
        self.obstacle: Optional[carla.Actor] = None
        self.obstacle_spawned = False
        self._name = "Emergency Brake"
        
    @property
    def name(self) -> str:
        """Get the user-friendly name of the scenario"""
        return self._name

    def setup(self) -> None:
        """Setup the emergency brake scenario"""
        try:
            super().setup()
            
            # Set initial target speed
            self.vehicle_controller.set_target_speed(self.target_speed)
            self.logger.info("Emergency brake scenario started")
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
            vehicle_velocity = self.vehicle.get_velocity()
            current_speed = vehicle_velocity.length() * 3.6  # Convert to km/h
            
            # Spawn obstacle when vehicle reaches trigger distance
            if not self.obstacle_spawned:
                vehicle_transform = self.vehicle.get_transform()
                vehicle_rotation = vehicle_transform.rotation
                
                # Calculate obstacle position
                obstacle_x = vehicle_location.x + self.trigger_distance * math.cos(math.radians(vehicle_rotation.yaw))
                obstacle_y = vehicle_location.y + self.trigger_distance * math.sin(math.radians(vehicle_rotation.yaw))
                obstacle_location = carla.Location(x=obstacle_x, y=obstacle_y, z=vehicle_location.z)
                
                # Get the world and blueprint
                world = self.world_manager.get_world()
                blueprint = world.get_blueprint_library().find(self.obstacle_type)
                
                # Spawn obstacle
                self.obstacle = world.spawn_actor(
                    blueprint,
                    carla.Transform(obstacle_location, vehicle_rotation)
                )
                
                if self.obstacle:
                    self.obstacle_spawned = True
                    self.logger.info("Obstacle spawned, emergency braking required")
                else:
                    self.logger.error("Failed to spawn obstacle")
                    self._set_completed(success=False)
                    return
            
            # Check if vehicle has stopped
            if self.obstacle_spawned and current_speed < 1.0:  # Consider stopped if speed < 1 km/h
                obstacle_location = self.obstacle.get_location()
                distance_to_obstacle = vehicle_location.distance(obstacle_location)
                
                if distance_to_obstacle > 2.0:  # Vehicle stopped at safe distance
                    self.logger.info("Emergency braking successful")
                    self._set_completed(success=True)
                else:
                    self.logger.error("Vehicle stopped too close to obstacle")
                    self._set_completed(success=False)
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
        except Exception as e:
            self.logger.error(f"Error in scenario cleanup: {str(e)}")
            # Don't re-raise here to ensure cleanup continues 