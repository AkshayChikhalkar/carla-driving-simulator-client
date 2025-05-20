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
    connection: 'ConnectionConfig'

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
    sun_altitude_angle: float = 45
    sun_azimuth_angle: float = 0
    wind_intensity: float = 0
    fog_density: float = 0
    wetness: float = 0

@dataclass
class WorldConfig:
    """World configuration parameters"""
    map: str
    weather: WeatherConfig
    physics: PhysicsConfig
    traffic: TrafficConfig
    fixed_delta_seconds: float = 0.1
    target_distance: float = 500.0
    num_vehicles: int = 20
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

@dataclass
class EmergencyBrakeConfig:
    """Emergency brake scenario configuration"""
    trigger_distance: float
    target_speed: float
    obstacle_type: str

@dataclass
class VehicleCuttingConfig:
    """Vehicle cutting scenario configuration"""
    target_speed: float
    spawn_distance: float
    lateral_offset: float
    cutting_vehicle_model: str

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
class Config:
    """Main configuration class"""
    server: ServerConfig
    world: WorldConfig
    simulation: SimulationConfig
    logging: LoggingConfig
    display: DisplayConfig
    sensors: SensorConfig
    controller: ControllerConfig
    vehicle_model: str
    scenarios: ScenarioConfig

def load_config(config_path: str) -> Config:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)
    
    return Config(
        server=ServerConfig(
            host=config_dict['server']['host'],
            port=config_dict['server']['port'],
            timeout=config_dict['server']['timeout'],
            connection=ConnectionConfig(**config_dict['server']['connection'])
        ),
        world=WorldConfig(**config_dict['world']),
        simulation=SimulationConfig(**config_dict['simulation']),
        logging=LoggingConfig(**config_dict['logging']),
        display=DisplayConfig(**config_dict['display']),
        sensors=SensorConfig(
            camera=CameraConfig(**config_dict['sensors']['camera']),
            collision=CollisionConfig(**config_dict['sensors']['collision']),
            gnss=GNSSConfig(**config_dict['sensors']['gnss'])
        ),
        controller=ControllerConfig(
            type=config_dict['controller']['type'],
            steer_speed=config_dict['controller']['steer_speed'],
            throttle_speed=config_dict['controller']['throttle_speed'],
            brake_speed=config_dict['controller']['brake_speed'],
            keyboard=KeyboardConfig(**config_dict['controller']['keyboard'])
        ),
        vehicle_model=config_dict['vehicle_model'],
        scenarios=ScenarioConfig(**config_dict['scenarios'])
    ) 