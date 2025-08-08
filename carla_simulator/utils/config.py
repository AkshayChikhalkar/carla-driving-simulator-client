"""
Configuration management for the simulation.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import yaml
import os


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

    simulation_file: str
    operations_file: str
    log_level: str
    format: Dict[str, str]
    enabled: bool = True
    directory: str = "logs"

    def __post_init__(self):
        """Ensure log files are in the configured directory"""
        if self.directory:
            self.simulation_file = os.path.join(self.directory, self.simulation_file)
            self.operations_file = os.path.join(self.directory, self.operations_file)


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
    web_mode: bool = False


def load_config(config_path: str) -> Config:
    """Load configuration from YAML file"""
    with open(config_path, "r") as f:
        config_dict = yaml.safe_load(f)

    config = Config(
        server=ServerConfig(
            host=config_dict["server"]["host"],
            port=config_dict["server"]["port"],
            timeout=config_dict["server"]["timeout"],
            connection=ConnectionConfig(**config_dict["server"]["connection"]),
        ),
        world=WorldConfig(**config_dict["world"]),
        simulation=SimulationConfig(**config_dict["simulation"]),
        logging=LoggingConfig(**config_dict["logging"]),
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
    )

    if os.environ.get("WEB_MODE", "false").lower() == "true":
        config.web_mode = True

    return config


def save_config(config: Config, config_path: str) -> None:
    """Save configuration to YAML file"""
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
            "simulation_file": config.logging.simulation_file,
            "operations_file": config.logging.operations_file,
            "log_level": config.logging.log_level,
            "format": config.logging.format,
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
        "web_mode": config.web_mode,
    }

    with open(config_path, "w") as f:
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
