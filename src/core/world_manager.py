"""
Manages the CARLA world, including weather, traffic, and target points.
"""

import carla
import random
import math
from typing import List, Optional, Dict
from dataclasses import dataclass
from ..utils.config import WorldConfig

@dataclass
class TargetPoint:
    """Represents a target point in the world"""
    location: carla.Location
    actors: List[carla.Actor]
    waypoint: carla.Waypoint

class WorldManager:
    """Manages the CARLA world state and operations"""
    
    def __init__(self, client: carla.Client, config: WorldConfig):
        """Initialize the world manager"""
        self.client = client
        self.config = config
        self.world = self.client.get_world()
        self.target: Optional[TargetPoint] = None
        self._traffic_actors: List[carla.Actor] = []
        
        # Apply initial settings
        settings = self.world.get_settings()
        settings.synchronous_mode = config.synchronous_mode
        settings.fixed_delta_seconds = config.fixed_delta_seconds
        settings.substepping = True
        settings.max_substep_delta_time = 0.01  # 10ms
        settings.max_substeps = 10
        self.world.apply_settings(settings)
        
        # Wait for the world to be ready
        self.world.tick()
        
        # Set up traffic manager
        traffic_manager = self.client.get_trafficmanager()
        traffic_manager.set_synchronous_mode(True)
        traffic_manager.set_global_distance_to_leading_vehicle(2.5)
        traffic_manager.global_percentage_speed_difference(30.0)  # Allow some speed variation
    
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
    
    def setup_traffic(self) -> None:
        """Initialize traffic in the world"""
        traffic_manager = self.world.get_traffic_manager()
        traffic_manager.set_global_distance_to_leading_vehicle(2.0)
        traffic_manager.set_random_device_seed(0)
        
        for _ in range(self.config.num_vehicles):
            transform = random.choice(self.world.get_map().get_spawn_points())
            bp = random.choice(self.world.get_blueprint_library().filter('vehicle.*'))
            
            npc = self.world.try_spawn_actor(bp, transform)
            if npc is not None:
                npc.set_autopilot(True)
                traffic_manager.ignore_lights_percentage(npc, 0)
                traffic_manager.vehicle_percentage_speed_difference(npc, random.uniform(-20, 20))
                self._traffic_actors.append(npc)
    
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
            target = self.world.spawn_actor(target_bp, target_transform)
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
                    actor.destroy()
        
        # Clean up traffic
        for actor in self._traffic_actors:
            if actor is not None:
                actor.destroy()
        
        # Reset world settings
        self.world.apply_settings(carla.WorldSettings()) 