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
from ..utils.logging import Logger, CURRENT_TENANT_ID
from ..utils.config import WorldConfig, VehicleConfig
from carla_simulator.core.interfaces import IWorldManager
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

    def __init__(
        self,
        client: carla.Client,
        config: WorldConfig,
        vehicle_config: VehicleConfig,
        logger: Logger,
    ):
        """Initialize the world manager"""
        self.client = client
        self.config = config
        self.vehicle_config = vehicle_config
        self.logger = logger
        self.world = None
        self.vehicle = None
        self.blueprint_library = None
        self.spawn_points = []
        self.target: Optional[TargetPoint] = None
        self._traffic_actors: List[carla.Actor] = []
        self._scenario_actors: List[carla.Actor] = []  # Track scenario-specific actors
        self._sensor_actors: List[carla.Actor] = []  # Track sensor actors
        self.traffic_manager = None
        # Default Traffic Manager port aligns with CARLA default; can be overridden per-tenant
        self.traffic_manager_port = 8000
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 2.0  # seconds

        # Get configuration values with fallbacks
        self.synchronous_mode = getattr(config, "synchronous_mode", True)
        self.fixed_delta_seconds = getattr(config, "fixed_delta_seconds", 0.05)
        self.enable_collision = getattr(config, "enable_collision", False)

        # Get vehicle configuration values with fallbacks
        self.vehicle_mass = getattr(vehicle_config, "mass", 1500.0)
        self.vehicle_drag = getattr(vehicle_config, "drag_coefficient", 0.3)
        self.vehicle_max_rpm = getattr(vehicle_config, "max_rpm", 6000.0)
        self.vehicle_moi = getattr(vehicle_config, "moi", 1.0)
        self.vehicle_model = getattr(vehicle_config, "model", "vehicle.fuso.mitsubishi")

        self._setup_world()

        # Wait for the world to be ready
        self.world.tick()

    def _handle_server_error(self, error: Exception) -> bool:
        """Handle server errors and attempt reconnection"""
        error_msg = str(error).lower()

        # Check if it's a connection error
        if any(
            msg in error_msg
            for msg in [
                "connection refused",
                "connection failed",
                "actively refused",
                "timeout",
                "no connection could be made",
            ]
        ):
            self.logger.error(f"CARLA server connection error: {str(error)}")
            return self._attempt_reconnection()

        # For other errors, just log them
        self.logger.error(f"CARLA server error: {str(error)}")
        return False

    def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the CARLA server"""
        for attempt in range(self.max_reconnect_attempts):
            try:
                self.logger.info(
                    f"Attempting to reconnect to CARLA server (attempt {attempt + 1}/{self.max_reconnect_attempts})..."
                )
                time.sleep(self.reconnect_delay)

                # Try to get the world
                self.world = self.client.get_world()
                if self.world is not None:
                    self.logger.info("Successfully reconnected to CARLA server")
                    return True

            except Exception as e:
                self.logger.error(
                    f"Reconnection attempt {attempt + 1} failed: {str(e)}"
                )
                if attempt < self.max_reconnect_attempts - 1:
                    time.sleep(self.reconnect_delay)

        self.logger.error("Failed to reconnect to CARLA server after multiple attempts")
        return False

    def connect(self) -> bool:
        """Connect to CARLA server"""
        try:
            self.client.set_timeout(2.0)
            self.world = self.client.get_world()
            if self.world is None:
                self.logger.error("Failed to get world from CARLA server")
                return False

            self.logger.info(
                f"Connected to CARLA server at {self.client.get_server_host()}:{self.client.get_server_port()}"
            )
            return True
        except Exception as e:
            return self._handle_server_error(e)

    def tick(self) -> bool:
        """Update the world state"""
        try:
            if self.world is None:
                self.logger.error("World is None, attempting to reconnect...")
                return self._attempt_reconnection()

            self.world.tick()
            return True
        except Exception as e:
            return self._handle_server_error(e)

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

    def spawn_actor(
        self, blueprint: carla.ActorBlueprint, transform: carla.Transform
    ) -> Optional[carla.Actor]:
        """Spawn an actor in the world using the centralized spawning logic"""
        return self._spawn_with_retry(blueprint, transform, spawn_id="direct_spawn")

    def destroy_actor(self, actor: carla.Actor) -> None:
        """Destroy an actor from the world"""
        if actor and actor.is_alive:
            actor.destroy()

    def _setup_world(self) -> None:
        """Setup the CARLA world"""
        try:
            # Get the world
            self.world = self.client.get_world()

            # Apply synchronous/asynchronous mode based on config
            settings = self.world.get_settings()
            if self.synchronous_mode:
                settings.synchronous_mode = True
                settings.fixed_delta_seconds = self.fixed_delta_seconds
            else:
                settings.synchronous_mode = False
                try:
                    # Clear fixed delta to let server drive real-time when async
                    settings.fixed_delta_seconds = None
                except Exception:
                    pass
            self.world.apply_settings(settings)

            # Get blueprint library
            self.blueprint_library = self.world.get_blueprint_library()

            # Get spawn points
            self.spawn_points = self.world.get_map().get_spawn_points()

            self.logger.info("World setup completed successfully")

        except Exception as e:
            self.logger.error(f"Error setting up world: {str(e)}")
            raise

    def _spawn_with_retry(
        self,
        blueprint: carla.ActorBlueprint,
        spawn_point: carla.Transform,
        max_attempts: int = 10,
        spawn_id: str = "unknown",
    ) -> Optional[carla.Actor]:
        """
        Attempt to spawn an actor with retry logic and location adjustment

        Args:
            blueprint: Actor blueprint to spawn
            spawn_point: Initial spawn point
            max_attempts: Maximum number of spawn attempts
            spawn_id: Identifier for this spawn attempt (for debugging)

        Returns:
            Optional[carla.Actor]: Spawned actor if successful, None otherwise
        """
        # Get all available spawn points
        spawn_points = self.world.get_map().get_spawn_points()
        if not spawn_points:
            self.logger.error("No spawn points available in the map")
            return None

        # Try initial spawn point first
        for attempt in range(max_attempts):
            try:
                self.logger.debug(f"[{spawn_id}] Spawn attempt {attempt + 1}/{max_attempts} for {blueprint.id}")
                
                # Try to spawn at current spawn point
                actor = self.world.spawn_actor(blueprint, spawn_point)
                
                if actor:
                    self.logger.debug(f"[{spawn_id}] Actor object created: {actor}")
                    self.logger.debug(f"[{spawn_id}] Actor type: {type(actor)}")
                    self.logger.debug(f"[{spawn_id}] Actor type_id: {actor.type_id}")
                    
                    # CRITICAL FIX: Tick the world immediately after spawning in synchronous mode
                    # This ensures the actor is properly registered before checking is_alive
                    if self.synchronous_mode:
                        try:
                            self.world.tick()
                            self.logger.debug(f"[{spawn_id}] World ticked immediately after spawn")
                            # Small delay to ensure CARLA processes the spawn
                            time.sleep(0.1)
                        except Exception as e:
                            self.logger.warning(f"[{spawn_id}] Error ticking world after spawn: {str(e)}")
                    
                    self.logger.debug(f"[{spawn_id}] Actor is_alive after tick: {actor.is_alive}")
                    
                    if actor.is_alive:
                        self.logger.debug(
                            f"[{spawn_id}] {actor.type_id} spawned successfully at {spawn_point.location} on attempt {attempt + 1}"
                        )
                        
                        # Additional tick to ensure everything is stable
                        try:
                            self.world.tick()
                            self.logger.debug(f"[{spawn_id}] World ticked after successful spawn verification")
                        except Exception as e:
                            self.logger.warning(f"[{spawn_id}] Error ticking world after spawn verification: {str(e)}")
                        
                        # Final check that actor is still alive after additional tick
                        if not actor.is_alive:
                            self.logger.warning(f"[{spawn_id}] Actor not alive after final tick, destroying and retrying")
                            try:
                                actor.destroy()
                            except Exception as destroy_error:
                                self.logger.warning(f"[{spawn_id}] Error destroying actor: {str(destroy_error)}")
                            continue
                        
                        return actor
                    else:
                        self.logger.warning(f"[{spawn_id}] Actor spawned but not alive, destroying and retrying")
                        try:
                            actor.destroy()
                        except Exception as destroy_error:
                            self.logger.warning(f"[{spawn_id}] Error destroying actor: {str(destroy_error)}")
                else:
                    self.logger.warning(f"[{spawn_id}] Spawn returned None for {blueprint.id}")

                # If spawn failed, try a different spawn point
                if attempt < max_attempts - 1:
                    # Get a random spawn point different from the current one
                    new_spawn_point = random.choice(spawn_points)
                    while (
                        new_spawn_point.location == spawn_point.location
                        and len(spawn_points) > 1
                    ):
                        new_spawn_point = random.choice(spawn_points)

                    # Adjust spawn point slightly to avoid collisions
                    new_spawn_point.location.x += random.uniform(-2.0, 2.0)
                    new_spawn_point.location.y += random.uniform(-2.0, 2.0)
                    new_spawn_point.location.z += (
                        0.5  # Lift slightly to avoid ground collision
                    )

                    spawn_point = new_spawn_point
                    self.logger.info(
                        f"[{spawn_id}] Trying new spawn point at {spawn_point.location}"
                    )
                    time.sleep(1.0)  # Increased wait time for synchronous mode

            except Exception as e:
                self.logger.warning(f"[{spawn_id}] Spawn attempt {attempt + 1} failed: {str(e)}")
                self.logger.debug(f"[{spawn_id}] Exception type: {type(e).__name__}")
                if attempt < max_attempts - 1:
                    # Try a different spawn point on next attempt
                    spawn_point = random.choice(spawn_points)
                    time.sleep(1.0)  # Increased wait time for synchronous mode
                continue

        self.logger.error(f"[{spawn_id}] Failed to spawn {blueprint.id} after {max_attempts} attempts")
        return None

    def _apply_advanced_attributes(self, blueprint: carla.ActorBlueprint, section: str, advanced: dict) -> None:
        """Apply dynamic attributes from config.advanced.<section>.attributes for CARLA 0.10.0.
        section: 'vehicle' | 'sensor' | 'walker'
        """
        try:
            attrs = (advanced or {}).get(section, {}).get('attributes', {})
            if not attrs:
                return
            for key, value in attrs.items():
                try:
                    if hasattr(blueprint, 'set_attribute'):
                        blueprint.set_attribute(str(key), str(value))
                except Exception as e:
                    self.logger.debug(f"Could not set attribute {key} on {blueprint.id}: {e}")
        except Exception as e:
            self.logger.debug(f"Advanced attribute application failed: {e}")

    def create_vehicle(self) -> Optional[carla.Vehicle]:
        """Create and spawn a vehicle in the world"""
        try:
            self.logger.debug(f"Starting vehicle creation for model: {self.vehicle_model}")
            
            # Get vehicle blueprint
            vehicle_bp = self.blueprint_library.find(self.vehicle_model)
            if not vehicle_bp:
                self.logger.error(f"Vehicle blueprint {self.vehicle_model} not found")
                # List available vehicle blueprints for debugging
                available_vehicles = self.blueprint_library.filter("vehicle.*")
                self.logger.info(f"Available vehicle blueprints: {[bp.id for bp in available_vehicles[:5]]}")
                return None

            self.logger.debug(f"Found vehicle blueprint: {vehicle_bp.id}")

            # Check spawn points
            if not self.spawn_points:
                self.logger.error("No spawn points available")
                return None
                
            self.logger.debug(f"Using spawn point: {self.spawn_points[0].location}")

            # Set vehicle attributes with proper CARLA attribute names
            try:
                # Physics control attributes
                physics_control = carla.VehiclePhysicsControl(
                    mass=self.vehicle_mass,
                    drag_coefficient=self.vehicle_drag,
                    max_rpm=self.vehicle_max_rpm,
                    moi=self.vehicle_moi,
                )

                # Try to spawn vehicle with retries
                spawn_point = self.spawn_points[0]  # Use first spawn point
                self.logger.debug(f"Attempting to spawn vehicle at {spawn_point.location}")
                
                # Apply advanced blueprint attributes (if provided via config._config.advanced)
                try:
                    advanced_cfg = getattr(self, 'advanced_config', None)
                    if advanced_cfg is None:
                        # attempt to reach through application config if available
                        if hasattr(self, 'app') and hasattr(self.app, '_config'):
                            advanced_cfg = getattr(self.app._config, 'advanced', None)
                    self._apply_advanced_attributes(vehicle_bp, 'vehicle', advanced_cfg or {})
                except Exception:
                    pass

                self.vehicle = self._spawn_with_retry(vehicle_bp, spawn_point, spawn_id="main_vehicle")

                if not self.vehicle:
                    self.logger.error("Failed to spawn vehicle after all attempts")
                    return None

                self.logger.info(f"Vehicle spawned successfully: {self.vehicle.type_id}")
                self.logger.debug(f"Vehicle object: {self.vehicle}")
                self.logger.debug(f"Vehicle is_alive: {self.vehicle.is_alive}")

                # Tick the world to ensure the vehicle is properly registered
                try:
                    self.world.tick()
                    self.logger.debug("World ticked after vehicle spawn")
                except Exception as e:
                    self.logger.warning(f"Error ticking world after spawn: {str(e)}")

                # Double-check vehicle is still alive after tick
                if not self.vehicle.is_alive:
                    self.logger.error("Vehicle is not alive after world tick")
                    return None

                # Apply physics control after spawning
                try:
                    self.vehicle.apply_physics_control(physics_control)
                    self.logger.debug("Physics control applied successfully")
                    
                    # Tick again after applying physics control
                    self.world.tick()
                    self.logger.debug("World ticked after physics control")
                    
                except Exception as e:
                    self.logger.error(f"Error applying physics control: {str(e)}")
                    # Don't destroy the vehicle, just log the error
                    pass

                # Set additional vehicle attributes if available
                if hasattr(vehicle_bp, "set_attribute"):
                    # Engine attributes
                    if hasattr(vehicle_bp, "set_attribute"):
                        try:
                            vehicle_bp.set_attribute(
                                "engine_power", str(self.vehicle_max_rpm * 0.7)
                            )
                        except Exception as e:
                            self.logger.debug(
                                f"Could not set engine_power for {self.vehicle.type_id}: {str(e)}"
                            )

                        try:
                            vehicle_bp.set_attribute(
                                "engine_torque", str(self.vehicle_mass * 0.5)
                            )
                        except Exception as e:
                            self.logger.debug(
                                f"Could not set engine_torque for {self.vehicle.type_id}: {str(e)}"
                            )

                        try:
                            vehicle_bp.set_attribute(
                                "engine_max_rpm", str(self.vehicle_max_rpm)
                            )
                        except Exception as e:
                            self.logger.debug(
                                f"Could not set engine_max_rpm for {self.vehicle.type_id}: {str(e)}"
                            )

                # Final tick to ensure everything is registered
                try:
                    self.world.tick()
                    self.logger.debug("Final world tick after vehicle setup")
                except Exception as e:
                    self.logger.warning(f"Error in final world tick: {str(e)}")

                # Final check before returning
                if not self.vehicle.is_alive:
                    self.logger.error("Vehicle is not alive after setup")
                    return None
                    
                self.logger.debug(f"Vehicle completed: {self.vehicle.type_id}")
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
            "location": self.vehicle.get_location(),
            "velocity": self.vehicle.get_velocity(),
            "acceleration": self.vehicle.get_acceleration(),
            "transform": self.vehicle.get_transform(),
        }

    def apply_control(self, control: carla.VehicleControl) -> None:
        """Apply control commands to vehicle"""
        if self.vehicle:
            self.vehicle.apply_control(control)

    def get_weather_parameters(self) -> Dict[str, float]:
        """Get current weather parameters"""
        weather = self.world.get_weather()
        return {
            "cloudiness": weather.cloudiness,
            "precipitation": weather.precipitation,
            "precipitation_deposits": weather.precipitation_deposits,
            "wind_intensity": weather.wind_intensity,
            "sun_azimuth_angle": weather.sun_azimuth_angle,
            "sun_altitude_angle": weather.sun_altitude_angle,
            "fog_density": weather.fog_density,
            "fog_distance": weather.fog_distance,
            "wetness": weather.wetness,
            "fog_falloff": weather.fog_falloff,
        }

    def get_traffic_actors(self) -> List[carla.Actor]:
        """Get list of all traffic actors in the world"""
        return self._traffic_actors

    def setup_traffic(self, tm_port: Optional[int] = None) -> None:
        """Initialize traffic in the world with specific traffic manager port"""
        if self.traffic_manager is not None:
            return  # Traffic manager already initialized

        # Resolve Traffic Manager port with per-tenant isolation if possible
        port_to_use = tm_port or self.traffic_manager_port
        try:
            # Allow base to be configured; default to 8000
            import os
            base = int(os.getenv("CARLA_TM_PORT_BASE", "8000"))
            # If tenant context is bound, derive a stable per-tenant port offset
            tenant_id = None
            try:
                tenant_id = CURRENT_TENANT_ID.get()
            except Exception:
                tenant_id = None
            if tenant_id is not None and tm_port is None:
                # Keep within a reasonable range to avoid privileged/used ports
                port_to_use = base + (int(tenant_id) % 1000)
        except Exception:
            # Fallback to provided/default port
            pass
        self.traffic_manager_port = int(port_to_use)

        # Get traffic manager with specific port
        self.traffic_manager = self.client.get_trafficmanager(self.traffic_manager_port)
        # Keep TM sync mode aligned with world sync
        try:
            self.traffic_manager.set_synchronous_mode(bool(self.synchronous_mode))
        except Exception:
            pass
        self.traffic_manager.set_global_distance_to_leading_vehicle(3.5)
        self.traffic_manager.global_percentage_speed_difference(15.0)
        self.traffic_manager.set_random_device_seed(0)

        # Spawn traffic vehicles
        for i in range(self.config.num_vehicles):
            transform = random.choice(self.world.get_map().get_spawn_points())
            bp = random.choice(self.world.get_blueprint_library().filter("vehicle.*"))

            npc = self._spawn_with_retry(bp, transform, spawn_id=f"traffic_vehicle_{i}")
            if npc is not None:
                npc.set_autopilot(True, self.traffic_manager_port)
                self.traffic_manager.ignore_lights_percentage(npc, 0)
                self.traffic_manager.vehicle_percentage_speed_difference(
                    npc, random.uniform(-10, 10)
                )
                self._traffic_actors.append(npc)
                # Tick the world to ensure proper spawning
                self.world.tick()

    def get_traffic_manager(self) -> Optional[carla.TrafficManager]:
        """Get the traffic manager instance"""
        return self.traffic_manager

    def get_traffic_manager_port(self) -> int:
        """Get the traffic manager port"""
        return self.traffic_manager_port

    def get_all_tracked_actors(self) -> Dict[str, List[carla.Actor]]:
        """Get all tracked actors for debugging purposes"""
        return {
            "traffic": self._traffic_actors.copy(),
            "scenario": self._scenario_actors.copy(),
            "sensors": self._sensor_actors.copy(),
            "vehicle": [self.vehicle] if self.vehicle else []
        }

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
        self.logger.debug(
            f"Generated waypoint at location: {waypoint.transform.location}"
        )

        # Spawn target markers
        target_actors = []
        for i in range(15):
            target_bp = self.world.get_blueprint_library().find(
                "static.prop.trafficcone01"
            )
            target_bp.set_attribute("role_name", "target")
            target_loc = carla.Location(
                waypoint.transform.location.x,
                waypoint.transform.location.y,
                waypoint.transform.location.z + 4 + i,
            )
            target_transform = carla.Transform(target_loc)
            target = self._spawn_with_retry(target_bp, target_transform)
            if target:
                target_actors.append(target)
                self.logger.debug(f"Spawned target marker at {target_loc}")

        self.target = TargetPoint(
            location=waypoint.transform.location,
            transform=waypoint.transform,
            waypoint=waypoint,
        )
        return self.target

    def get_random_spawn_point(self) -> carla.Transform:
        """Get a random spawn point from the map"""
        return random.choice(self.world.get_map().get_spawn_points())

    def spawn_scenario_actor(
        self,
        blueprint_id: str,
        transform: carla.Transform,
        actor_type: str = "vehicle",
        **kwargs,
    ) -> Optional[carla.Actor]:
        """Spawn an actor for a scenario with proper tracking"""
        try:
            # Get blueprint
            blueprint = self.blueprint_library.find(blueprint_id)
            if not blueprint:
                self.logger.error(f"Blueprint {blueprint_id} not found")
                return None

            # Apply any additional attributes
            for key, value in kwargs.items():
                if hasattr(blueprint, "set_attribute"):
                    blueprint.set_attribute(key, str(value))

            # Spawn the actor
            actor = self._spawn_with_retry(blueprint, transform, spawn_id=f"scenario_{actor_type}")
            if actor:
                self._scenario_actors.append(actor)
                self.logger.debug(
                    f"Spawned {actor_type} {blueprint_id} at {transform.location}"
                )
                return actor
            return None

        except Exception as e:
            self.logger.error(f"Error spawning scenario actor {blueprint_id}: {str(e)}")
            return None

    def track_sensor_actor(self, sensor_actor: carla.Actor) -> None:
        """Track a sensor actor for cleanup"""
        if sensor_actor:
            self._sensor_actors.append(sensor_actor)
            self.logger.debug(f"Tracking sensor actor: {sensor_actor.type_id} (ID: {sensor_actor.id})")

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.logger.info("Starting world manager cleanup...")
            
            # Track cleanup statistics
            destroyed_actors = 0
            failed_destroy_actors = 0
            
            # Prepare ordered destruction: sensors -> scenario/traffic -> vehicle, using batch API
            sensors = [a for a in self._sensor_actors if a is not None]
            scenario = [a for a in self._scenario_actors if a is not None]
            traffic = [a for a in self._traffic_actors if a is not None]
            ego_list = [self.vehicle] if self.vehicle is not None else []

            self.logger.debug(
                f"Found {len(traffic)+len(scenario)+len(sensors)} actors to destroy: {len(traffic)} traffic, {len(scenario)} scenario, {len(sensors)} sensors"
            )

            # Best-effort: disable autopilot before destroy to avoid TM races
            try:
                for veh in [a for a in traffic + ego_list if hasattr(a, 'set_autopilot')]:
                    try:
                        veh.set_autopilot(False)
                    except Exception:
                        pass
            except Exception:
                pass

            # Put TM back to async to avoid strict sync during teardown
            try:
                if self.traffic_manager is not None:
                    self.traffic_manager.set_synchronous_mode(False)
            except Exception:
                pass

            def _destroy_batch(actors):
                nonlocal destroyed_actors, failed_destroy_actors
                if not actors:
                    return
                # Filter alive actors and collect ids
                actor_ids = []
                for a in actors:
                    try:
                        if a and getattr(a, 'is_alive', False):
                            actor_ids.append(a.id)
                        else:
                            # Already gone
                            if a is not None:
                                self.logger.debug(f"Actor already destroyed: {getattr(a, 'type_id', 'unknown')} (ID: {getattr(a, 'id', 'unknown')})")
                    except Exception:
                        # If is_alive access fails, try to destroy anyway
                        try:
                            actor_ids.append(a.id)
                        except Exception:
                            pass
                if not actor_ids:
                    return
                try:
                    cmds = [carla.command.DestroyActor(aid) for aid in actor_ids]
                    results = self.client.apply_batch_sync(cmds, True)
                    # Count results
                    for res in results:
                        if res.error:
                            failed_destroy_actors += 1
                            self.logger.debug(f"Destroy error: {res.error}")
                        else:
                            destroyed_actors += 1
                except Exception as e:
                    self.logger.warning(f"Batch destroy failed: {e}. Falling back to per-actor destroy.")
                    for a in actors:
                        try:
                            if a and getattr(a, 'is_alive', False):
                                a.destroy()
                                destroyed_actors += 1
                        except Exception as e2:
                            failed_destroy_actors += 1
                            self.logger.debug(f"Per-actor destroy failed: {e2}")

            # Destroy in safe order
            _destroy_batch(sensors)
            _destroy_batch(scenario)
            _destroy_batch(traffic)
            _destroy_batch(ego_list)

            # Clear the lists and references
            self._traffic_actors.clear()
            self._scenario_actors.clear()
            self._sensor_actors.clear()
            self.vehicle = None
            
            # Add a small delay to ensure actors are destroyed
            time.sleep(0.2)
            
            # Flush destroy operations with a couple of world ticks to ensure the server processes removals
            try:
                if self.world is not None:
                    for _ in range(2):
                        try:
                            self.world.tick()
                        except Exception:
                            break
            except Exception:
                pass

            # Verify cleanup by checking if any actors are still alive (best-effort)
            remaining_alive = 0
            for actor in sensors + scenario + traffic + ego_list:
                try:
                    if actor and hasattr(actor, 'is_alive') and actor.is_alive:
                        remaining_alive += 1
                        self.logger.warning(f"Actor still alive after destroy: {actor.type_id} (ID: {actor.id})")
                except Exception:
                    continue
            
            self.logger.info(f"World manager cleanup completed: {destroyed_actors} actors destroyed, {failed_destroy_actors} failed, {remaining_alive} still alive")

            # Do not reload the world here to avoid native crashes during teardown; the next setup will ensure a clean world

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise

    def force_cleanup_all_actors(self) -> None:
        """Force cleanup of all actors in the world, including untracked ones"""
        try:
            if not self.world:
                return
                
            self.logger.info("Force cleaning up all actors in world...")
            
            # Get all actors in the world
            all_world_actors = self.world.get_actors()
            self.logger.debug(f"Found {len(all_world_actors)} total actors in world")
            
            destroyed_count = 0
            for actor in all_world_actors:
                try:
                    if actor and actor.is_alive:
                        self.logger.debug(f"Force destroying actor: {actor.type_id} (ID: {actor.id})")
                        actor.destroy()
                        destroyed_count += 1
                except Exception as e:
                    self.logger.warning(f"Error force destroying actor {actor.type_id if actor else 'Unknown'} (ID: {actor.id if actor else 'Unknown'}): {str(e)}")
            
            self.logger.info(f"Force cleanup completed: {destroyed_count} actors destroyed")
            
        except Exception as e:
            self.logger.error(f"Error during force cleanup: {str(e)}")
            raise

    def get_blueprint_library(self) -> carla.BlueprintLibrary:
        """Get the CARLA blueprint library"""
        return self.blueprint_library

    def get_spawn_points(self) -> List[carla.Transform]:
        """Get the list of spawn points"""
        return self.spawn_points
