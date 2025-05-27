from abc import ABC, abstractmethod
import logging
from typing import Optional, Dict, Any
import carla
import yaml
import os
import time
from dataclasses import dataclass
from src.core.interfaces import IWorldManager, IVehicleController, ISensorManager, ILogger
from src.utils.config import (
    CameraConfig,
    CollisionConfig,
    GNSSConfig,
    ServerConfig,
    WorldConfig,
    SimulationConfig as SimConfig,
    LoggingConfig,
    DisplayConfig,
    SensorConfig,
    ControllerConfig,
    ScenarioConfig,
    VehicleConfig,
    Config,
    KeyboardConfig
)
from src.utils.logging import SimulationData, Logger

@dataclass
class ServerConfig:
    """Server configuration parameters"""
    host: str
    port: int
    timeout: float
    connection: Dict[str, Any]

class ConnectionManager:
    """Handles connection to CARLA server"""
    def __init__(self, server_config: ServerConfig):
        self.config = server_config
        self.client = None

    def connect(self) -> bool:
        """Connect to CARLA server"""
        try:
            print(f"Connecting to CARLA server at {self.config.host}:{self.config.port}...")
            self.client = carla.Client(self.config.host, self.config.port)
            self.client.set_timeout(self.config.timeout)
            
            # Test connection
            world = self.client.get_world()
            if not world:
                print("Failed to get CARLA world")
                return False
                
            print("Successfully connected to CARLA server")
            return True
        except Exception as e:
            print(f"Failed to connect to CARLA server: {str(e)}")
            print("Make sure the CARLA server is running and accessible")
            self.client = None
            return False

    def disconnect(self) -> None:
        """Disconnect from CARLA server"""
        if self.client:
            print("Disconnecting from CARLA server...")
            self.client = None

class SimulationState:
    """Manages simulation state"""
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_scenario = None
        self.start_time = None
        self.elapsed_time = 0.0

    def start(self) -> None:
        """Start simulation"""
        self.is_running = True
        self.start_time = time.time()

    def pause(self) -> None:
        """Pause simulation"""
        self.is_paused = True

    def resume(self) -> None:
        """Resume simulation"""
        self.is_paused = False

    def stop(self) -> None:
        """Stop simulation"""
        self.is_running = False
        self.is_paused = False

    def update(self) -> None:
        """Update simulation state"""
        if self.is_running and not self.is_paused:
            self.elapsed_time = time.time() - self.start_time

class SimulationMetrics:
    """Tracks simulation metrics"""
    def __init__(self, logger: Logger):
        """Initialize metrics with logger"""
        self.logger = logger
        self.metrics = {
            'fps': 0.0,
            'frame_count': 0,
            'last_frame_time': time.time(),  # Initialize with current time
            'vehicle_speed': 0.0,
            'distance_traveled': 0.0,
            'collisions': 0,
            'min_frame_time': 0.001  # Minimum frame time to avoid division by zero
        }

    def update(self, vehicle_state: Dict[str, Any]) -> None:
        """Update metrics with current state"""
        current_time = time.time()
        frame_time = current_time - self.metrics['last_frame_time']
        
        # Update FPS with minimum frame time to avoid division by zero
        if frame_time > 0:
            self.metrics['fps'] = 1.0 / max(frame_time, self.metrics['min_frame_time'])
        self.metrics['last_frame_time'] = current_time
        self.metrics['frame_count'] += 1

        # Update vehicle metrics
        if 'velocity' in vehicle_state:
            speed = vehicle_state['velocity'].length() * 3.6  # Convert to km/h
            self.metrics['vehicle_speed'] = speed

    def log_metrics(self) -> None:
        """Log current metrics to file"""
        if not self.logger:
            return
            
        # Create simulation data object
        data = SimulationData(
            elapsed_time=self.metrics.get('elapsed_time', 0.0),
            speed=self.metrics.get('vehicle_speed', 0.0),
            position=(0.0, 0.0, 0.0),  # Default position
            controls={
                'throttle': 0.0,
                'brake': 0.0,
                'steer': 0.0,
                'gear': 1,
                'hand_brake': False,
                'reverse': False,
                'manual_gear_shift': False
            },
            target_info={
                'distance': 0.0,
                'heading': 0.0,
                'heading_diff': 0.0
            },
            vehicle_state={
                'heading': 0.0,
                'acceleration': 0.0,
                'angular_velocity': 0.0,
                'collision_intensity': 0.0,
                'rotation': (0.0, 0.0, 0.0)
            },
            weather={
                'cloudiness': 0.0,
                'precipitation': 0.0
            },
            traffic_count=0,
            fps=self.metrics.get('fps', 0.0),
            event='metrics_update',
            event_details=''
        )
        
        # Log to file only
        self.logger.log_data(data)

class SimulationConfig:
    """Manages simulation configuration"""
    def __init__(self, config_path: str, scenario: str = None):
        self.config = self._load_config(config_path, scenario)
        self.validate_config()
        
        # Create the main config object
        self._main_config = Config(
            server=self._create_server_config(),
            world=self._create_world_config(),
            simulation=self._create_simulation_config(),
            logging=self._create_logging_config(),
            display=self._create_display_config(),
            sensors=self._create_sensor_config(),
            controller=self._create_controller_config(),
            vehicle=self._create_vehicle_config(),
            scenarios=self._create_scenario_config()
        )
        
        # Expose config components for backward compatibility
        self.server_config = self._main_config.server
        self.world_config = self._main_config.world
        self.simulation_config = self._main_config.simulation
        self.logging_config = self._main_config.logging
        self.display_config = self._main_config.display
        self.sensor_config = self._main_config.sensors
        self.controller_config = self._main_config.controller
        self.vehicle = self._main_config.vehicle
        self.scenario_config = self._main_config.scenarios

    def _load_config(self, config_path: str, scenario: str = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            if not os.path.isabs(config_path):
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), config_path)
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}

            # Use scenario from argument
            if scenario:
                config['scenario'] = scenario

            return config
        except Exception as e:
            raise RuntimeError(f"Failed to load config file {config_path}: {str(e)}")

    def _create_server_config(self) -> ServerConfig:
        """Create ServerConfig object from configuration"""
        server = self.config.get('server')
        if not server:
            raise ValueError("Missing required 'server' configuration section")
            
        return ServerConfig(
            host=server['host'],
            port=server['port'],
            timeout=server['timeout'],
            connection=server.get('connection', {})
        )

    def _create_world_config(self) -> WorldConfig:
        """Create WorldConfig object from configuration"""
        world = self.config.get('world')
        if not world:
            raise ValueError("Missing required 'world' configuration section")
            
        return WorldConfig(
            map=world['map'],
            weather=world.get('weather', {}),
            physics=world.get('physics', {}),
            traffic=world.get('traffic', {}),
            fixed_delta_seconds=world['fixed_delta_seconds'],
            target_distance=world['target_distance'],
            num_vehicles=world['num_vehicles'],
            enable_collision=world['enable_collision'],
            synchronous_mode=world['synchronous_mode']
        )

    def _create_simulation_config(self) -> SimConfig:
        """Create SimulationConfig object from configuration"""
        simulation = self.config.get('simulation')
        if not simulation:
            raise ValueError("Missing required 'simulation' configuration section")
            
        return SimConfig(
            max_speed=simulation['max_speed'],
            simulation_time=simulation['simulation_time'],
            update_rate=simulation['update_rate'],
            speed_change_threshold=simulation['speed_change_threshold'],
            position_change_threshold=simulation['position_change_threshold'],
            heading_change_threshold=simulation['heading_change_threshold'],
            target_tolerance=simulation['target_tolerance'],
            max_collision_force=simulation['max_collision_force']
        )

    def _create_logging_config(self) -> LoggingConfig:
        """Create LoggingConfig object from configuration"""
        logging = self.config.get('logging')
        if not logging:
            raise ValueError("Missing required 'logging' configuration section")
            
        return LoggingConfig(
            simulation_file=logging['simulation_file'],
            operations_file=logging['operations_file'],
            log_level=logging['log_level'],
            format=logging.get('format', {}),
            enabled=logging['enabled'],
            directory=logging['directory']
        )

    def _create_display_config(self) -> DisplayConfig:
        """Create DisplayConfig object from configuration"""
        display = self.config.get('display')
        if not display:
            raise ValueError("Missing required 'display' configuration section")
            
        return DisplayConfig(
            width=display['width'],
            height=display['height'],
            fps=display['fps'],
            hud=display.get('hud', {}),
            minimap=display.get('minimap', {}),
            camera=display.get('camera', {}),
            hud_enabled=display['hud_enabled'],
            minimap_enabled=display['minimap_enabled']
        )

    def _create_sensor_config(self) -> SensorConfig:
        """Create SensorConfig object from configuration"""
        sensors = self.config.get('sensors')
        if not sensors:
            raise ValueError("Missing required 'sensors' configuration section")
            
        # Create individual sensor configs
        camera_config = CameraConfig(
            enabled=sensors.get('camera', {}).get('enabled', True),
            width=sensors.get('camera', {}).get('width', 1280),
            height=sensors.get('camera', {}).get('height', 720),
            fov=sensors.get('camera', {}).get('fov', 90),
            x=sensors.get('camera', {}).get('x', -2.5),
            y=sensors.get('camera', {}).get('y', 0.0),
            z=sensors.get('camera', {}).get('z', 2.0)
        )
        
        collision_config = CollisionConfig(
            enabled=sensors.get('collision', {}).get('enabled', True)
        )
        
        gnss_config = GNSSConfig(
            enabled=sensors.get('gnss', {}).get('enabled', True)
        )
        
        return SensorConfig(
            camera=camera_config,
            collision=collision_config,
            gnss=gnss_config
        )

    def _create_controller_config(self) -> ControllerConfig:
        """Create ControllerConfig object from configuration"""
        controller = self.config.get('controller')
        if not controller:
            raise ValueError("Missing required 'controller' configuration section")
            
        keyboard = controller.get('keyboard')
        if not keyboard:
            raise ValueError("Missing required 'keyboard' configuration section")
        
        # Create keyboard config using values from config file
        keyboard_config = KeyboardConfig(
            forward=keyboard['forward'],
            backward=keyboard['backward'],
            left=keyboard['left'],
            right=keyboard['right'],
            brake=keyboard['brake'],
            hand_brake=keyboard['hand_brake'],
            reverse=keyboard['reverse'],
            quit=keyboard['quit']
        )
        
        return ControllerConfig(
            type=controller['type'],
            steer_speed=controller['steer_speed'],
            throttle_speed=controller['throttle_speed'],
            brake_speed=controller['brake_speed'],
            keyboard=keyboard_config
        )

    def _create_scenario_config(self) -> ScenarioConfig:
        """Create ScenarioConfig object from configuration"""
        scenarios = self.config.get('scenarios')
        if not scenarios:
            raise ValueError("Missing required 'scenarios' configuration section")
            
        return ScenarioConfig(
            follow_route=scenarios.get('follow_route', {}),
            avoid_obstacle=scenarios.get('avoid_obstacle', {}),
            emergency_brake=scenarios.get('emergency_brake', {}),
            vehicle_cutting=scenarios.get('vehicle_cutting', {})
        )

    def _create_vehicle_config(self) -> VehicleConfig:
        """Create VehicleConfig object from configuration"""
        vehicle = self.config.get('vehicle')
        if not vehicle:
            raise ValueError("Missing required 'vehicle' configuration section")
            
        return VehicleConfig(
            model=vehicle['model'],
            mass=vehicle['mass'],
            drag_coefficient=vehicle['drag_coefficient'],
            max_rpm=vehicle['max_rpm'],
            moi=vehicle['moi'],
            center_of_mass=vehicle['center_of_mass']
        )

    def validate_config(self) -> None:
        """Validate configuration values"""
        if 'server' not in self.config:
            raise ValueError("Missing required 'server' configuration section")
        
        server = self.config['server']
        required_keys = ['host', 'port', 'timeout']
        for key in required_keys:
            if key not in server:
                raise ValueError(f"Missing required server config key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default) 