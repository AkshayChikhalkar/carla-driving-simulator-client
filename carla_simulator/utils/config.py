"""
Configuration management for the simulation.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import yaml
import os
import json

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override into base and return a new dict."""
    result = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


@dataclass
class ServerConfig:
    """Server configuration parameters"""

    host: str
    port: int
    timeout: float
    connection: "ConnectionConfig"


@dataclass
class ConnectionConfig:
    """Connection retry configuration"""

    max_retries: int
    retry_delay: float


@dataclass
class PhysicsConfig:
    """Physics simulation configuration"""

    max_substep_delta_time: float
    max_substeps: int


@dataclass
class TrafficConfig:
    """Traffic management configuration"""

    distance_to_leading_vehicle: float
    speed_difference_percentage: float
    ignore_lights_percentage: float
    ignore_signs_percentage: float


@dataclass
class WeatherConfig:
    """Weather configuration parameters"""

    cloudiness: float = 0
    precipitation: float = 0
    precipitation_deposits: float = 0
    sun_altitude_angle: float = 45
    sun_azimuth_angle: float = 0
    wind_intensity: float = 0
    fog_density: float = 0
    fog_distance: float = 0
    fog_falloff: float = 0
    wetness: float = 0


@dataclass
class WorldConfig:
    """World configuration parameters"""

    map: str
    weather: WeatherConfig
    physics: PhysicsConfig
    traffic: TrafficConfig
    fixed_delta_seconds: float = 0.0167  # 60 FPS default
    target_distance: float = 500.0
    num_vehicles: int = 5
    enable_collision: bool = False
    synchronous_mode: bool = True

    def __post_init__(self):
        """Convert weather dict to WeatherConfig if needed"""
        if isinstance(self.weather, dict):
            self.weather = WeatherConfig(**self.weather)
        if isinstance(self.physics, dict):
            self.physics = PhysicsConfig(**self.physics)
        if isinstance(self.traffic, dict):
            self.traffic = TrafficConfig(**self.traffic)


@dataclass
class FollowRouteConfig:
    """Follow route scenario configuration"""

    num_waypoints: int
    waypoint_tolerance: float
    min_distance: float
    max_distance: float


@dataclass
class AvoidObstacleConfig:
    """Avoid obstacle scenario configuration"""

    target_distance: float
    obstacle_spacing: float
    completion_distance: float
    collision_threshold: float
    max_simulation_time: float
    waypoint_tolerance: float
    min_waypoint_distance: float
    max_waypoint_distance: float
    num_waypoints: int
    num_obstacles: int
    min_obstacle_distance: float
    obstacle_types: List[str]


@dataclass
class EmergencyBrakeConfig:
    """Emergency brake scenario configuration"""

    trigger_distance: float
    target_speed: float
    obstacle_type: str


@dataclass
class VehicleCuttingConfig:
    """Vehicle cutting scenario configuration"""

    target_distance: float
    cutting_distance: float
    completion_distance: float
    collision_threshold: float
    max_simulation_time: float
    waypoint_tolerance: float
    min_waypoint_distance: float
    max_waypoint_distance: float
    num_waypoints: int
    cutting_vehicle_model: str
    normal_speed: float
    cutting_speed: float
    cutting_trigger_distance: float


@dataclass
class ScenarioConfig:
    """Scenario configuration parameters"""

    follow_route: FollowRouteConfig
    avoid_obstacle: AvoidObstacleConfig
    emergency_brake: EmergencyBrakeConfig
    vehicle_cutting: VehicleCuttingConfig

    def __post_init__(self):
        """Convert dicts to config objects if needed"""
        if isinstance(self.follow_route, dict):
            self.follow_route = FollowRouteConfig(**self.follow_route)
        if isinstance(self.avoid_obstacle, dict):
            self.avoid_obstacle = AvoidObstacleConfig(**self.avoid_obstacle)
        if isinstance(self.emergency_brake, dict):
            self.emergency_brake = EmergencyBrakeConfig(**self.emergency_brake)
        if isinstance(self.vehicle_cutting, dict):
            self.vehicle_cutting = VehicleCuttingConfig(**self.vehicle_cutting)


@dataclass
class SimulationConfig:
    """Simulation configuration parameters"""

    max_speed: float
    simulation_time: int
    update_rate: float
    speed_change_threshold: float
    position_change_threshold: float
    heading_change_threshold: float
    target_tolerance: float
    max_collision_force: float = 1000.0  # Default collision force threshold in Newtons


@dataclass
class LoggingConfig:
    """Logging configuration parameters"""

    log_level: str
    enabled: bool = True
    directory: str = "logs"

    def __post_init__(self):
        # No file paths to normalize anymore
        pass


@dataclass
class DisplayColors:
    """Display color configuration"""

    target: str
    vehicle: str
    text: str
    background: str


@dataclass
class HUDConfig:
    """HUD configuration"""

    font_size: int
    font_name: str
    alpha: int
    colors: DisplayColors


@dataclass
class MinimapConfig:
    """Minimap configuration"""

    width: int
    height: int
    scale: float
    alpha: int
    colors: DisplayColors


@dataclass
class CameraDisplayConfig:
    """Camera display configuration"""

    font_size: int
    font_name: str


@dataclass
class DisplayConfig:
    """Display configuration parameters"""

    width: int
    height: int
    fps: int
    hud: HUDConfig
    minimap: MinimapConfig
    camera: CameraDisplayConfig
    hud_enabled: bool = True
    minimap_enabled: bool = True

    def __post_init__(self):
        """Convert dicts to config objects if needed"""
        if isinstance(self.hud, dict):
            self.hud = HUDConfig(**self.hud)
        if isinstance(self.minimap, dict):
            self.minimap = MinimapConfig(**self.minimap)
        if isinstance(self.camera, dict):
            self.camera = CameraDisplayConfig(**self.camera)


@dataclass
class AnalyticsConfig:
    """Analytics / Monitoring configuration"""

    grafana_base_url: str = "/grafana/d"


@dataclass
class CameraConfig:
    """Camera sensor configuration"""

    enabled: bool
    width: int
    height: int
    fov: int
    x: float
    y: float
    z: float


@dataclass
class CollisionConfig:
    """Collision sensor configuration"""

    enabled: bool


@dataclass
class GNSSConfig:
    """GNSS sensor configuration"""

    enabled: bool


@dataclass
class SensorConfig:
    """Sensor configuration parameters"""

    camera: CameraConfig
    collision: CollisionConfig
    gnss: GNSSConfig


@dataclass
class KeyboardConfig:
    """Keyboard control configuration"""

    forward: List[str]
    backward: List[str]
    left: List[str]
    right: List[str]
    brake: List[str]
    hand_brake: List[str]
    reverse: List[str]
    quit: List[str]


@dataclass
class ControllerConfig:
    """Controller configuration parameters"""

    type: str  # keyboard, gamepad, or autopilot
    steer_speed: float
    throttle_speed: float
    brake_speed: float
    keyboard: KeyboardConfig


@dataclass
class VehicleConfig:
    """Vehicle configuration parameters"""

    model: str
    mass: float
    drag_coefficient: float
    max_rpm: float
    moi: float
    center_of_mass: List[float]


@dataclass
class Config:
    """Main configuration class"""

    server: ServerConfig
    world: WorldConfig
    simulation: SimulationConfig
    logging: LoggingConfig
    display: DisplayConfig
    sensors: SensorConfig
    controller: ControllerConfig
    vehicle: VehicleConfig
    scenarios: ScenarioConfig
    analytics: Optional[AnalyticsConfig] = None
    web_mode: bool = False


def _load_config_dict(config_path: str) -> Dict[str, Any]:
    """Load config strictly from DB for the current tenant (no file fallback).

    Resolution order for tenant id:
    1) Request-scoped ContextVar (CURRENT_TENANT_ID)
    2) CONFIG_TENANT_ID environment variable (legacy)

    If no tenant id is available or no active config is found in DB, raise a RuntimeError.
    """
    # Resolve tenant id from request-scoped context first
    tenant_id: Optional[int] = None
    try:
        from carla_simulator.utils.logging import CURRENT_TENANT_ID  # lazy import to avoid cycles
        ctx_tid = CURRENT_TENANT_ID.get()
        if ctx_tid is not None:
            tenant_id = int(ctx_tid)
    except Exception:
        tenant_id = tenant_id

    # Fallback to env var if context not present
    if tenant_id is None:
        env_tid = os.environ.get("CONFIG_TENANT_ID")
        if env_tid is not None:
            try:
                tenant_id = int(env_tid)
            except ValueError:
                tenant_id = None

    if tenant_id is None:
        raise RuntimeError("Tenant context required to load configuration from DB (no file fallback)")

    # Load strictly from DB for this tenant, with fallback to global default
    from carla_simulator.database.db_manager import DatabaseManager
    from carla_simulator.database.models import TenantConfig

    db = DatabaseManager()
    config_from_db = TenantConfig.get_active_config(db, int(tenant_id))
    if not config_from_db:
        # Fallback to global-default tenant by slug, or to metadata if not present
        try:
            # Resolve global-default tenant id
            default_tid = None
            try:
                tenant_row = Tenant.get_by_slug(db, "global-default")  # type: ignore
                if tenant_row:
                    default_tid = int(tenant_row["id"]) if isinstance(tenant_row, dict) else None
            except Exception:
                default_tid = None
            default_cfg = None
            if default_tid is not None:
                default_cfg = TenantConfig.get_active_config(db, default_tid)
            if not default_cfg:
                # Fallback to metadata
                from carla_simulator.database.db_manager import DatabaseManager as _DBM
                md = _DBM()
                default_cfg = md.get_carla_metadata("simulation_defaults")
        except Exception:
            default_cfg = None
        if not isinstance(default_cfg, dict) or len(default_cfg) == 0:
            raise RuntimeError(
                f"No active configuration found for tenant {tenant_id} and no global default present"
            )
        # Seed this tenant with the default config so subsequent loads are fast
        try:
            TenantConfig.upsert_active_config(db, int(tenant_id), default_cfg)
        except Exception:
            pass
        return default_cfg

    return config_from_db


def load_config(config_path: str) -> Config:
    """Load configuration, with optional multi-tenant DB source."""
    config_dict = _load_config_dict(config_path)

    # Sanitize logging block to accept only supported keys
    logging_block = config_dict.get("logging", {}) or {}
    allowed_logging_keys = {"log_level", "enabled", "directory"}
    logging_filtered = {k: v for k, v in logging_block.items() if k in allowed_logging_keys}

    # Sanitize world block to drop unknown keys (e.g., 'walkers') and nested extras
    world_block = config_dict.get("world", {}) or {}
    allowed_world_keys = {
        "map",
        "weather",
        "physics",
        "traffic",
        "fixed_delta_seconds",
        "target_distance",
        "num_vehicles",
        "enable_collision",
        "synchronous_mode",
    }
    # Filter nested weather/physics/traffic to their known fields
    weather_block = (world_block.get("weather") or {}) if isinstance(world_block.get("weather"), dict) else world_block.get("weather")
    physics_block = (world_block.get("physics") or {}) if isinstance(world_block.get("physics"), dict) else world_block.get("physics")
    traffic_block = (world_block.get("traffic") or {}) if isinstance(world_block.get("traffic"), dict) else world_block.get("traffic")

    if isinstance(weather_block, dict):
        allowed_weather_keys = {
            "cloudiness",
            "precipitation",
            "precipitation_deposits",
            "sun_altitude_angle",
            "sun_azimuth_angle",
            "wind_intensity",
            "fog_density",
            "fog_distance",
            "fog_falloff",
            "wetness",
        }
        weather_block = {k: v for k, v in weather_block.items() if k in allowed_weather_keys}

    if isinstance(physics_block, dict):
        allowed_physics_keys = {"max_substep_delta_time", "max_substeps"}
        physics_block = {k: v for k, v in physics_block.items() if k in allowed_physics_keys}

    if isinstance(traffic_block, dict):
        allowed_traffic_keys = {
            "distance_to_leading_vehicle",
            "speed_difference_percentage",
            "ignore_lights_percentage",
            "ignore_signs_percentage",
        }
        traffic_block = {k: v for k, v in traffic_block.items() if k in allowed_traffic_keys}

    world_filtered = {k: v for k, v in world_block.items() if k in allowed_world_keys}
    if isinstance(weather_block, dict) or weather_block is not None:
        world_filtered["weather"] = weather_block
    if isinstance(physics_block, dict) or physics_block is not None:
        world_filtered["physics"] = physics_block
    if isinstance(traffic_block, dict) or traffic_block is not None:
        world_filtered["traffic"] = traffic_block

    config = Config(
        server=ServerConfig(
            host=config_dict["server"]["host"],
            port=config_dict["server"]["port"],
            timeout=config_dict["server"]["timeout"],
            connection=ConnectionConfig(**config_dict["server"]["connection"]),
        ),
        world=WorldConfig(**world_filtered),
        simulation=SimulationConfig(**config_dict["simulation"]),
        logging=LoggingConfig(**logging_filtered),
        display=DisplayConfig(**config_dict["display"]),
        sensors=SensorConfig(
            camera=CameraConfig(**config_dict["sensors"]["camera"]),
            collision=CollisionConfig(**config_dict["sensors"]["collision"]),
            gnss=GNSSConfig(**config_dict["sensors"]["gnss"]),
        ),
        controller=ControllerConfig(
            type=config_dict["controller"]["type"],
            steer_speed=config_dict["controller"]["steer_speed"],
            throttle_speed=config_dict["controller"]["throttle_speed"],
            brake_speed=config_dict["controller"]["brake_speed"],
            keyboard=KeyboardConfig(**config_dict["controller"]["keyboard"]),
        ),
        vehicle=VehicleConfig(**config_dict["vehicle"]),
        scenarios=ScenarioConfig(**config_dict["scenarios"]),
        analytics=AnalyticsConfig(**config_dict.get("analytics", {})) if config_dict.get("analytics") is not None else None,
    )

    if os.environ.get("WEB_MODE", "false").lower() == "true":
        config.web_mode = True

    return config


def save_config(config: Config, config_path: str) -> None:
    """Save configuration to file (JSON when path ends with .json, otherwise YAML)."""
    config_dict = {
        "server": {
            "host": config.server.host,
            "port": config.server.port,
            "timeout": config.server.timeout,
            "connection": {
                "retries": config.server.connection.max_retries,
                "retry_delay": config.server.connection.retry_delay,
            },
        },
        "world": {
            "map": config.world.map,
            "weather": {
                "cloudiness": config.world.weather.cloudiness,
                "precipitation": config.world.weather.precipitation,
                "precipitation_deposits": config.world.weather.precipitation_deposits,
                "wind_intensity": config.world.weather.wind_intensity,
                "sun_azimuth_angle": config.world.weather.sun_azimuth_angle,
                "sun_altitude_angle": config.world.weather.sun_altitude_angle,
                "fog_density": config.world.weather.fog_density,
                "fog_distance": config.world.weather.fog_distance,
                "fog_falloff": config.world.weather.fog_falloff,
                "wetness": config.world.weather.wetness,
            },
            "physics": {
                "gravity": config.world.physics.max_substep_delta_time,
                "max_substeps": config.world.physics.max_substeps,
                "substep_time": config.world.physics.max_substep_delta_time,
            },
            "traffic": {
                "distance_to_leading_vehicle": config.world.traffic.distance_to_leading_vehicle,
                "speed_difference_percentage": config.world.traffic.speed_difference_percentage,
                "ignore_lights_percentage": config.world.traffic.ignore_lights_percentage,
                "ignore_signs_percentage": config.world.traffic.ignore_signs_percentage,
            },
            "fixed_delta_seconds": config.world.fixed_delta_seconds,
            "target_distance": config.world.target_distance,
            "num_vehicles": config.world.num_vehicles,
            "enable_collision": config.world.enable_collision,
            "synchronous_mode": config.world.synchronous_mode,
        },
        "simulation": {
            "max_speed": config.simulation.max_speed,
            "simulation_time": config.simulation.simulation_time,
            "update_rate": config.simulation.update_rate,
            "speed_change_threshold": config.simulation.speed_change_threshold,
            "position_change_threshold": config.simulation.position_change_threshold,
            "heading_change_threshold": config.simulation.heading_change_threshold,
            "target_tolerance": config.simulation.target_tolerance,
            "max_collision_force": config.simulation.max_collision_force,
        },
        "logging": {
            "log_level": config.logging.log_level,
            "enabled": config.logging.enabled,
            "directory": config.logging.directory,
        },
        "display": {
            "width": config.display.width,
            "height": config.display.height,
            "fps": config.display.fps,
            "hud": {
                "font_size": config.display.hud.font_size,
                "font_name": config.display.hud.font_name,
                "alpha": config.display.hud.alpha,
                "colors": {
                    "text": config.display.hud.colors.text,
                    "background": config.display.hud.colors.background,
                    "border": config.display.hud.colors.border,
                },
            },
            "minimap": {
                "width": config.display.minimap.width,
                "height": config.display.minimap.height,
                "scale": config.display.minimap.scale,
                "alpha": config.display.minimap.alpha,
                "colors": {
                    "text": config.display.minimap.colors.text,
                    "background": config.display.minimap.colors.background,
                    "border": config.display.minimap.colors.border,
                },
            },
            "camera": {
                "font_size": config.display.camera.font_size,
                "font_name": config.display.camera.font_name,
            },
            "hud_enabled": config.display.hud_enabled,
            "minimap_enabled": config.display.minimap_enabled,
        },
        "sensors": {
            "camera": {
                "width": config.sensors.camera.width,
                "height": config.sensors.camera.height,
                "fov": config.sensors.camera.fov,
                "sensor_tick": config.sensors.camera.sensor_tick,
            },
            "collision": {"sensor_tick": config.sensors.collision.sensor_tick},
            "gnss": {
                "sensor_tick": config.sensors.gnss.sensor_tick,
                "noise_alt_bias": config.sensors.gnss.noise_alt_bias,
                "noise_alt_stddev": config.sensors.gnss.noise_alt_stddev,
                "noise_lat_bias": config.sensors.gnss.noise_lat_bias,
                "noise_lat_stddev": config.sensors.gnss.noise_lat_stddev,
                "noise_lon_bias": config.sensors.gnss.noise_lon_bias,
                "noise_lon_stddev": config.sensors.gnss.noise_lon_stddev,
            },
        },
        "controller": {
            "type": config.controller.type,
            "steer_speed": config.controller.steer_speed,
            "throttle_speed": config.controller.throttle_speed,
            "brake_speed": config.controller.brake_speed,
            "keyboard": {
                "forward": config.controller.keyboard.forward,
                "backward": config.controller.keyboard.backward,
                "left": config.controller.keyboard.left,
                "right": config.controller.keyboard.right,
                "brake": config.controller.keyboard.brake,
                "hand_brake": config.controller.keyboard.hand_brake,
                "reverse": config.controller.keyboard.reverse,
                "quit": config.controller.keyboard.quit,
            },
        },
        "vehicle": {
            "model": config.vehicle.model,
            "mass": config.vehicle.mass,
            "drag_coefficient": config.vehicle.drag_coefficient,
            "max_rpm": config.vehicle.max_rpm,
            "moi": config.vehicle.moi,
        },
        "scenarios": {
            "follow_route": {
                "num_waypoints": config.scenarios.follow_route.num_waypoints,
                "waypoint_distance": config.scenarios.follow_route.waypoint_distance,
            },
            "avoid_obstacle": {
                "obstacle_distance": config.scenarios.avoid_obstacle.target_distance,
                "obstacle_size": config.scenarios.avoid_obstacle.obstacle_spacing,
            },
            "emergency_brake": {
                "trigger_distance": config.scenarios.emergency_brake.trigger_distance,
                "min_speed": config.scenarios.emergency_brake.target_speed,
            },
            "vehicle_cutting": {
                "cutting_distance": config.scenarios.vehicle_cutting.cutting_distance,
                "cutting_speed": config.scenarios.vehicle_cutting.cutting_speed,
            },
        },
        "analytics": {
            "grafana_base_url": (config.analytics.grafana_base_url if config.analytics else "/grafana/d"),
        },
        "web_mode": config.web_mode,
    }

    with open(config_path, "w", encoding="utf-8") as f:
        if config_path.lower().endswith(".json"):
            json.dump(config_dict, f, indent=2)
        else:
            yaml.dump(config_dict, f, default_flow_style=False)


class ConfigLoader:
    """Configuration loader class for managing simulation configuration."""

    def __init__(self, config_path: str):
        """Initialize the config loader with the path to the config file."""
        self.config_path = config_path
        self.config = None
        self.simulation_config = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        return self.config

    def validate_config(self) -> bool:
        """Validate the loaded configuration."""
        if not self.config:
            return False
        required_sections = ['target', 'vehicle', 'simulation']
        return all(section in self.config for section in required_sections)

    def get_simulation_config(self) -> SimulationConfig:
        """Get the simulation configuration object."""
        if not self.config:
            self.load_config()
        
        sim_config = self.config.get('simulation', {})
        self.simulation_config = SimulationConfig(
            max_speed=sim_config.get('max_speed', 100.0),
            simulation_time=sim_config.get('simulation_time', 60),
            update_rate=sim_config.get('update_rate', 0.1),
            speed_change_threshold=sim_config.get('speed_change_threshold', 0.1),
            position_change_threshold=sim_config.get('position_change_threshold', 0.1),
            heading_change_threshold=sim_config.get('heading_change_threshold', 0.1),
            target_tolerance=sim_config.get('target_tolerance', 1.0),
            max_collision_force=sim_config.get('max_collision_force', 1000.0)
        )
        return self.simulation_config
