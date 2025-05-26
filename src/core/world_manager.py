"""
Manages the CARLA world, including weather, traffic, and target points.
"""

import carla
import random
import math
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from ..utils.config import WorldConfig, VehicleConfig
import time
from src.core.interfaces import IWorldManager

@dataclass
class TargetPoint:
    """Represents a target point in the world"""
    location: carla.Location
    actors: List[carla.Actor]
    waypoint: carla.Waypoint

class WorldManager(IWorldManager):
    """Manages the CARLA world and its entities"""
    
    def __init__(self, client: carla.Client, config: WorldConfig, vehicle_config: VehicleConfig):
        """Initialize the world manager"""
        self.client = client
        self.config = config
        self.vehicle_config = vehicle_config
        self.world = None
        self.vehicle = None
        self.blueprint_library = None
        self.spawn_points = []
        self.target: Optional[TargetPoint] = None
        self._traffic_actors: List[carla.Actor] = []
        self._setup_world()
        
        # Apply initial settings with more stable timing parameters
        settings = self.world.get_settings()
        settings.synchronous_mode = config.synchronous_mode
        settings.fixed_delta_seconds = config.fixed_delta_seconds
        settings.substepping = True
        settings.max_substep_delta_time = config.physics.max_substep_delta_time
        settings.max_substeps = config.physics.max_substeps
        self.world.apply_settings(settings)
        
        # Wait for the world to be ready
        self.world.tick()

    def get_map(self) -> carla.Map:
        """Get the current CARLA map"""
        return self.world.get_map()

    def spawn_actor(self, blueprint: carla.ActorBlueprint, transform: carla.Transform) -> Optional[carla.Actor]:
        """Spawn an actor in the world"""
        try:
            return self.world.spawn_actor(blueprint, transform)
        except Exception as e:
            print(f"Error spawning actor: {str(e)}")
            return None

    def destroy_actor(self, actor: carla.Actor) -> None:
        """Destroy an actor from the world"""
        if actor and actor.is_alive:
            actor.destroy()

    def _setup_world(self) -> None:
        """Setup the CARLA world with specified configuration"""
        try:
            # Get world
            self.world = self.client.get_world()
            
            # Set synchronous mode if configured
            if self.config.synchronous_mode:
                settings = self.world.get_settings()
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = self.config.fixed_delta_seconds
                self.world.apply_settings(settings)
            
            # Get blueprint library
            self.blueprint_library = self.world.get_blueprint_library()
            
            # Get spawn points
            self.spawn_points = self.world.get_map().get_spawn_points()
            
        except Exception as e:
            raise RuntimeError(f"Failed to setup world: {str(e)}")

    def create_vehicle(self) -> Optional[carla.Vehicle]:
        """Create and spawn a vehicle in the world"""
        try:
            # Get vehicle blueprint from config
            vehicle_bp = self.blueprint_library.find(self.vehicle_config.model)
            if not vehicle_bp:
                raise RuntimeError(f"Failed to find vehicle blueprint: {self.vehicle_config.model}")
            
            # Get spawn points
            if not self.spawn_points:
                raise RuntimeError("No spawn points available")
            
            # Try multiple spawn points until successful
            for spawn_point in self.spawn_points:
                try:
                    # Spawn vehicle
                    self.vehicle = self.spawn_actor(vehicle_bp, spawn_point)
                    if self.vehicle:
                        # Set vehicle physics after spawning
                        physics_control = self.vehicle.get_physics_control()
                        
                        # Update physics control with configuration values
                        physics_control.mass = self.vehicle_config.mass
                        physics_control.drag_coefficient = self.vehicle_config.drag_coefficient
                        physics_control.max_rpm = self.vehicle_config.max_rpm
                        physics_control.moi = self.vehicle_config.moi
                        physics_control.center_of_mass = carla.Vector3D(*self.vehicle_config.center_of_mass)
                        
                        # Apply the physics control
                        self.vehicle.apply_physics_control(physics_control)
                        
                        print(f"Successfully spawned vehicle at location: {spawn_point.location}")
                        return self.vehicle
                except Exception as e:
                    print(f"Failed to spawn at location {spawn_point.location}: {str(e)}")
                    continue
            
            raise RuntimeError("Failed to spawn vehicle at any spawn point")
            
        except Exception as e:
            print(f"Error creating vehicle: {str(e)}")
            return None

    def get_vehicle_state(self) -> Dict[str, Any]:
        """Get current vehicle state"""
        if not self.vehicle:
            return {}
            
        return {
            'location': self.vehicle.get_location(),
            'velocity': self.vehicle.get_velocity(),
            'acceleration': self.vehicle.get_acceleration(),
            'transform': self.vehicle.get_transform()
        }

    def apply_control(self, control: carla.VehicleControl) -> None:
        """Apply control commands to vehicle"""
        if self.vehicle:
            self.vehicle.apply_control(control)

    def get_weather_parameters(self) -> Dict[str, float]:
        """Get current weather parameters"""
        weather = self.world.get_weather()
        return {
            'cloudiness': weather.cloudiness,
            'precipitation': weather.precipitation,
            'precipitation_deposits': weather.precipitation_deposits,
            'wind_intensity': weather.wind_intensity,
            'sun_azimuth_angle': weather.sun_azimuth_angle,
            'sun_altitude_angle': weather.sun_altitude_angle,
            'fog_density': weather.fog_density,
            'fog_distance': weather.fog_distance,
            'wetness': weather.wetness,
            'fog_falloff': weather.fog_falloff
        }
    
    def get_traffic_actors(self) -> List[carla.Actor]:
        """Get list of all traffic actors in the world"""
        return self._traffic_actors
    
    def setup_traffic(self, tm_port: int) -> None:
        """Initialize traffic in the world with specific traffic manager port"""
        # Get traffic manager with specific port
        self.traffic_manager = self.client.get_trafficmanager(tm_port)
        self.traffic_manager.set_synchronous_mode(True)
        self.traffic_manager.set_global_distance_to_leading_vehicle(3.5)
        self.traffic_manager.global_percentage_speed_difference(15.0)
        self.traffic_manager.set_random_device_seed(0)
        
        # Spawn traffic vehicles
        for _ in range(self.config.num_vehicles):
            transform = random.choice(self.world.get_map().get_spawn_points())
            bp = random.choice(self.world.get_blueprint_library().filter('vehicle.*'))
            
            npc = self.spawn_actor(bp, transform)
            if npc is not None:
                npc.set_autopilot(True, tm_port)
                self.traffic_manager.ignore_lights_percentage(npc, 0)
                self.traffic_manager.vehicle_percentage_speed_difference(npc, random.uniform(-10, 10))
                self._traffic_actors.append(npc)
                # Tick the world to ensure proper spawning
                self.world.tick()
    
    def generate_target_point(self, spawn_point: carla.Transform) -> TargetPoint:
        """Generate a target point at specified distance from spawn point"""
        target_dist = self.config.target_distance
        
        # Calculate random X and Y components
        target_dist_x = random.randint(1, 4) * target_dist / 5
        target_dist_y = math.sqrt(target_dist**2 - target_dist_x**2)
        
        # Randomize direction
        if random.random() < 0.5:
            target_dist_x *= -1
        if random.random() < 0.5:
            target_dist_y *= -1
        
        # Calculate target location
        target_x = spawn_point.location.x + target_dist_x
        target_y = spawn_point.location.y + target_dist_y
        
        # Get closest waypoint
        waypoint = self.world.get_map().get_waypoint(
            carla.Location(target_x, target_y, spawn_point.location.z)
        )
        
        # Spawn target markers
        target_actors = []
        for i in range(15):
            target_bp = self.world.get_blueprint_library().find('static.prop.trafficcone01')
            target_bp.set_attribute('role_name', 'target')
            target_loc = carla.Location(
                waypoint.transform.location.x,
                waypoint.transform.location.y,
                waypoint.transform.location.z + 4 + i
            )
            target_transform = carla.Transform(target_loc)
            target = self.spawn_actor(target_bp, target_transform)
            if target:
                target_actors.append(target)
        
        self.target = TargetPoint(
            location=waypoint.transform.location,
            actors=target_actors,
            waypoint=waypoint
        )
        return self.target
    
    def get_random_spawn_point(self) -> carla.Transform:
        """Get a random spawn point from the map"""
        return random.choice(self.world.get_map().get_spawn_points())
    
    def cleanup(self) -> None:
        """Clean up all spawned actors"""
        # Clean up target actors
        if self.target:
            for actor in self.target.actors:
                if actor is not None:
                    self.destroy_actor(actor)
        
        # Clean up traffic
        for actor in self._traffic_actors:
            if actor is not None:
                self.destroy_actor(actor)
        
        # Reset world settings
        self.world.apply_settings(carla.WorldSettings())
        
        # Clean up vehicle
        if self.vehicle:
            self.destroy_actor(self.vehicle)
        
        # Reset synchronous mode
        if self.world and self.config.synchronous_mode:
            settings = self.world.get_settings()
            settings.synchronous_mode = False
            self.world.apply_settings(settings)
        
        # Reset vehicle
        self.vehicle = None
        self.blueprint_library = None
        self.spawn_points = []
        self.target = None
        self._traffic_actors = []
    
    def get_world(self) -> carla.World:
        """Get the CARLA world"""
        return self.world
    
    def get_blueprint_library(self) -> carla.BlueprintLibrary:
        """Get the CARLA blueprint library"""
        return self.blueprint_library
    
    def get_spawn_points(self) -> List[carla.Transform]:
        """Get the list of spawn points"""
        return self.spawn_points 