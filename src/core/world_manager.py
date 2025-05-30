"""
World management system for CARLA simulation.
"""

import carla
import random
import math
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from ..utils.logging import Logger
from ..utils.config import WorldConfig, VehicleConfig
from src.core.interfaces import IWorldManager
from ..utils.default_config import SIMULATION_CONFIG

# Get logger instance
logger = Logger()

@dataclass
class TargetPoint:
    """Target point information"""
    location: carla.Location
    transform: carla.Transform
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
        self.logger = logging.getLogger(__name__)
        
        # Get configuration values with fallbacks
        self.synchronous_mode = getattr(config, 'synchronous_mode', True)
        self.fixed_delta_seconds = getattr(config, 'fixed_delta_seconds', 0.05)
        self.enable_collision = getattr(config, 'enable_collision', False)
        
        # Get vehicle configuration values with fallbacks
        self.vehicle_mass = getattr(vehicle_config, 'mass', 1500.0)
        self.vehicle_drag = getattr(vehicle_config, 'drag_coefficient', 0.3)
        self.vehicle_max_rpm = getattr(vehicle_config, 'max_rpm', 6000.0)
        self.vehicle_moi = getattr(vehicle_config, 'moi', 1.0)
        self.vehicle_model = getattr(vehicle_config, 'model', 'vehicle.tesla.model3')
        
        self._setup_world()
        
        # Wait for the world to be ready
        self.world.tick()

    def connect(self) -> bool:
        """Connect to CARLA server"""
        try:
            self.client = carla.Client(self.host, self.port)
            self.client.set_timeout(2.0)
            self.world = self.client.get_world()
            self.logger.info(f"Connected to CARLA server at {self.host}:{self.port}")
            return True
        except Exception as e:
            self.logger.error("Failed to connect to CARLA server", exc_info=e)
            return False

    def disconnect(self) -> None:
        """Disconnect from CARLA server"""
        try:
            if self.client:
                self.client = None
                self.world = None
                self.logger.info("Disconnected from CARLA server")
        except Exception as e:
            self.logger.error("Error disconnecting from CARLA server", exc_info=e)

    def get_world(self) -> carla.World:
        """Get the current world"""
        if not self.world:
            self.logger.error("Not connected to CARLA server")
            raise RuntimeError("Not connected to CARLA server")
        return self.world

    def get_map(self) -> carla.Map:
        """Get the current map"""
        if not self.world:
            self.logger.error("Not connected to CARLA server")
            raise RuntimeError("Not connected to CARLA server")
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
        """Setup the CARLA world"""
        try:
            # Get the world
            self.world = self.client.get_world()
            
            # Set synchronous mode if configured
            if self.synchronous_mode:
                settings = self.world.get_settings()
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = self.fixed_delta_seconds
                self.world.apply_settings(settings)
            
            # Get blueprint library
            self.blueprint_library = self.world.get_blueprint_library()
            
            # Get spawn points
            self.spawn_points = self.world.get_map().get_spawn_points()
            
            self.logger.info("World setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up world: {str(e)}")
            raise

    def _spawn_with_retry(self, blueprint: carla.ActorBlueprint, spawn_point: carla.Transform, max_attempts: int = 10) -> Optional[carla.Actor]:
        """Attempt to spawn an actor with retry logic"""
        for attempt in range(max_attempts):
            try:
                actor = self.world.spawn_actor(blueprint, spawn_point)
                if actor and actor.is_alive:
                    self.logger.info(f"{actor.type_id} spawned successfully")
                    return actor
                elif actor:
                    actor.destroy()
            except Exception as e:
                self.logger.warning(f"Spawn attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(0.5)  # Wait before retry
                continue
        return None

    def create_vehicle(self) -> Optional[carla.Vehicle]:
        """Create and spawn a vehicle in the world"""
        try:
            # Get vehicle blueprint
            vehicle_bp = self.blueprint_library.find(self.vehicle_model)
            if not vehicle_bp:
                self.logger.error(f"Vehicle blueprint {self.vehicle_model} not found")
                return None
                
            # Set vehicle attributes with proper CARLA attribute names
            try:
                # Physics control attributes
                physics_control = carla.VehiclePhysicsControl(
                    mass=self.vehicle_mass,
                    drag_coefficient=self.vehicle_drag,
                    max_rpm=self.vehicle_max_rpm,
                    moi=self.vehicle_moi
                )
                
                # Try to spawn vehicle with retries
                spawn_point = self.spawn_points[0]  # Use first spawn point
                self.vehicle = self._spawn_with_retry(vehicle_bp, spawn_point)
                
                if not self.vehicle:
                    self.logger.error("Failed to spawn vehicle after all attempts")
                    return None
                    
                # Apply physics control after spawning
                self.vehicle.apply_physics_control(physics_control)
                
                # Set additional vehicle attributes if available
                if hasattr(vehicle_bp, 'set_attribute'):
                    # Engine attributes
                    if hasattr(vehicle_bp, 'set_attribute'):
                        try:
                            vehicle_bp.set_attribute('engine_power', str(self.vehicle_max_rpm * 0.7))
                        except Exception as e:
                            self.logger.debug(f"Could not set engine_power for {self.vehicle.type_id}: {str(e)}")
                            
                        try:
                            vehicle_bp.set_attribute('engine_torque', str(self.vehicle_mass * 0.5))
                        except Exception as e:
                            self.logger.debug(f"Could not set engine_torque for {self.vehicle.type_id}: {str(e)}")
                            
                        try:
                            vehicle_bp.set_attribute('engine_max_rpm', str(self.vehicle_max_rpm))
                        except Exception as e:
                            self.logger.debug(f"Could not set engine_max_rpm for {self.vehicle.type_id}: {str(e)}")
                
                return self.vehicle
                
            except Exception as e:
                self.logger.error(f"Error setting vehicle attributes: {str(e)}")
                if self.vehicle:
                    self.vehicle.destroy()
                return None
            
        except Exception as e:
            self.logger.error(f"Error creating vehicle: {str(e)}")
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
        
        # Log waypoint details in debug mode
        self.logger.debug(f"Generated waypoint at location: {waypoint.transform.location}")
        
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
                self.logger.debug(f"Spawned target marker at {target_loc}")
        
        self.target = TargetPoint(
            location=waypoint.transform.location,
            transform=waypoint.transform,
            waypoint=waypoint
        )
        return self.target
    
    def get_random_spawn_point(self) -> carla.Transform:
        """Get a random spawn point from the map"""
        return random.choice(self.world.get_map().get_spawn_points())
    
    def cleanup(self) -> None:
        """Clean up world resources"""
        try:
            # Destroy all actors
            actors = self.world.get_actors()
            
            def safe_destroy_actor(actor, actor_type="actor"):
                if not actor:
                    return False
                    
                try:
                    if actor.is_alive:
                        actor.destroy()
                        self.logger.info(f"Destroyed {actor.type_id}")
                        return True
                except Exception as e:
                    self.logger.error(f"Error destroying {actor.type_id if actor else 'unknown'}: {str(e)}")
                    return False
            
            # Only destroy vehicles and dynamic actors, not map actors
            vehicle_actors = [actor for actor in actors if actor and 
                            actor.type_id.startswith('vehicle.') and 
                            not actor.type_id.startswith('traffic.')]
            for actor in vehicle_actors:
                safe_destroy_actor(actor, "vehicle")
            
            # Wait for vehicles to be destroyed
            time.sleep(1.0)
            
            # Then destroy any remaining dynamic actors (excluding map actors)
            other_actors = [actor for actor in actors if actor and 
                          not actor.type_id.startswith(('sensor.', 'vehicle.', 'traffic.', 'static.'))]
            for actor in other_actors:
                safe_destroy_actor(actor, "actor")
            
            # Final wait and world tick
            time.sleep(1.0)
            if self.world:
                try:
                    self.world.tick()
                except Exception as e:
                    if "connection failed" in str(e).lower():
                        self.logger.error("Connection lost during cleanup - server may have crashed")
                    else:
                        self.logger.error(f"Error during final world tick: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise
    
    def get_blueprint_library(self) -> carla.BlueprintLibrary:
        """Get the CARLA blueprint library"""
        return self.blueprint_library
    
    def get_spawn_points(self) -> List[carla.Transform]:
        """Get the list of spawn points"""
        return self.spawn_points 