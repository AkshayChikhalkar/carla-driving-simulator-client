from abc import ABC, abstractmethod
import logging
from typing import Optional, Dict, Any
import carla
import yaml
import os
import time
from dataclasses import dataclass
from carla_simulator.core.interfaces import (
    IWorldManager,
    IVehicleController,
    ISensorManager,
    ILogger,
)
from carla_simulator.utils.config import (
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
    KeyboardConfig,
)
from carla_simulator.utils.logging import SimulationData
from datetime import datetime
from pathlib import Path


@dataclass
class ServerConfig:
    """Server configuration parameters"""

    host: str
    port: int
    timeout: float
    connection: Dict[str, Any]


class ConnectionManager:
    """Handles connection to CARLA server"""

    def __init__(self, server_config: ServerConfig, logger: ILogger):
        self.logger = logger
        self.config = server_config
        self.client = None

    def connect(self) -> bool:
        """Connect to CARLA server with retries"""
        max_retries = 3
        delay = 30
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.debug(
                    f"Connecting to CARLA server at {self.config.host}:{self.config.port} (attempt {attempt})..."
                )
                self.client = carla.Client(self.config.host, self.config.port)
                self.client.set_timeout(self.config.timeout)

                # Test connection
                world = self.client.get_world()
                if not world:
                    raise RuntimeError("Failed to get CARLA world")
                self.logger.info(f"Connected to CARLA server at {self.config.host}:{self.config.port} (attempt {attempt})")
                return True
            except Exception as e:
                self.logger.warning(
                    f"Failed to connect to CARLA server (attempt {attempt})"
                )
                self.logger.warning(
                    "Make sure the CARLA server is running and accessible"
                )
                self.client = None
                if attempt < max_retries:
                    self.logger.warning(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.warning("All connection attempts failed.")
                    return False

    def disconnect(self) -> None:
        """Disconnect from CARLA server"""
        if self.client:
            self.logger.info("Disconnecting from CARLA server...")
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

    def __init__(self, logger: ILogger):
        self.logger = logger
        self.metrics = {
            "fps": 0.0,
            "frame_count": 0,
            "last_frame_time": time.time(),  # Initialize with current time
            "vehicle_speed": 0.0,
            "distance_traveled": 0.0,
            "collisions": 0,
            "min_frame_time": 0.001,  # Minimum frame time to avoid division by zero
            "start_time": time.time(),  # Add start time for elapsed time calculation
            "elapsed_time": 0.0,
        }
        self.scenario = None
        self.start_time = datetime.now()
        self.end_time = None
        self.success = None

    def update(self, vehicle_state: Dict[str, Any]) -> None:
        """Update metrics with current state"""
        current_time = time.time()
        frame_time = current_time - self.metrics["last_frame_time"]

        # Update FPS with minimum frame time to avoid division by zero
        if frame_time > 0:
            self.metrics["fps"] = 1.0 / max(frame_time, self.metrics["min_frame_time"])
        self.metrics["last_frame_time"] = current_time
        self.metrics["frame_count"] += 1

        # Update elapsed time
        self.metrics["elapsed_time"] = current_time - self.metrics["start_time"]

        # Update vehicle metrics
        if "velocity" in vehicle_state:
            speed = vehicle_state["velocity"].length() * 3.6  # Convert to km/h
            self.metrics["vehicle_speed"] = speed

    def log_metrics(self) -> None:
        """Log current metrics to file"""
        if not self.logger:
            return

        # Get vehicle state from the current frame
        vehicle_state = {
            "heading": 0.0,
            "acceleration": 0.0,
            "angular_velocity": 0.0,
            "collision_intensity": 0.0,
            "rotation": (0.0, 0.0, 0.0),
        }

        # Get controls from the current frame
        controls = {
            "throttle": 0.0,
            "brake": 0.0,
            "steer": 0.0,
            "gear": 1,
            "hand_brake": False,
            "reverse": False,
            "manual_gear_shift": False,
        }

        # Get target info from the current frame
        target_info = {"distance": 0.0, "heading": 0.0, "heading_diff": 0.0}

        # Create simulation data object with actual metrics
        data = SimulationData(
            elapsed_time=self.metrics["elapsed_time"],
            speed=self.metrics["vehicle_speed"],
            position=(0.0, 0.0, 0.0),  # Default position
            controls=controls,
            target_info=target_info,
            vehicle_state=vehicle_state,
            weather={"cloudiness": 0.0, "precipitation": 0.0},
            traffic_count=0,
            fps=self.metrics["fps"],
            event="metrics_update",
            event_details="",
        )

        # Log to file and flush immediately
        self.logger.log_data(data)
        if hasattr(self.logger, "csv_file") and self.logger.csv_file:
            self.logger.csv_file.flush()

    def generate_html_report(self, scenario_results, start_time, end_time):
        """Generate a pytest-html style HTML report for multiple scenarios in the reports directory at the project root."""
        # Do not generate empty reports
        if not scenario_results or len(scenario_results) == 0:
            return
        import platform
        from carla_simulator.database.config import SessionLocal
        from carla_simulator.database.models import SimulationReport
        import os

        total = len(scenario_results)
        passed = sum(1 for s in scenario_results if s["result"].lower() == "passed")
        failed = sum(1 for s in scenario_results if s["result"].lower() == "failed")
        skipped = sum(1 for s in scenario_results if s["result"].lower() == "skipped")
        duration = str(end_time - start_time).split(".")[0]
        now_str = end_time.strftime("%d-%b-%Y at %H:%M:%S")
        python_version = platform.python_version()
        platform_str = platform.platform()

        html_content = f"""
        <!DOCTYPE html>
        <html lang='en'>
        <head>
            <meta charset='utf-8'>
            <title>CARLA Driving Simulator - Scenario Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #fff; color: #222; }}
                h1 {{ font-size: 2em; margin-bottom: 0.2em; }}
                .env-table, .summary-table {{ border-collapse: collapse; margin-bottom: 1.5em; }}
                .env-table td, .env-table th, .summary-table td, .summary-table th {{ border: 1px solid #ddd; padding: 6px 12px; }}
                .env-table th {{ background: #f5f5f5; }}
                .summary-bar {{ margin: 1em 0; }}
                .summary-bar span {{ margin-right: 1.5em; font-weight: bold; }}
                .passed {{ color: #388e3c; }}
                .failed {{ color: #d32f2f; }}
                .skipped {{ color: #fbc02d; }}
                .error {{ color: #d32f2f; }}
                .timeout {{ color: #f57c00; }}
                .stopped {{ color: #1976d2; }}
                .completed {{ color: #388e3c; }}
                .unknown {{ color: #757575; }}
                .summary-table th {{ background: #f5f5f5; }}
                .summary-table td {{ text-align: center; }}
                .summary-table .failed {{ background: #ffd6d6; }}
                .summary-table .passed {{ background: #d6ffd6; }}
                .summary-table .skipped {{ background: #fff9c4; }}
                .summary-table .error {{ background: #ffd6d6; }}
                .summary-table .timeout {{ background: #ffe0b2; }}
                .summary-table .stopped {{ background: #bbdefb; }}
                .summary-table .completed {{ background: #d6ffd6; }}
                .summary-table .unknown {{ background: #eeeeee; }}
                .summary-table .duration {{ font-family: monospace; }}
            </style>
        </head>
        <body>
            <h1>CARLA Driving Simulator - Scenario Test Report</h1>
            <div style='margin-bottom: 0.5em;'>Report generated on {now_str}</div>
            <h2>Environment</h2>
            <table class='env-table'>
                <tr><th>Python</th><td>{python_version}</td></tr>
                <tr><th>Platform</th><td>{platform_str}</td></tr>
                <tr><th>Packages</th><td>pytest-html style (custom)</td></tr>
                <tr><th>Plugins</th><td>n/a</td></tr>
            </table>
            <h2>Summary</h2>
            <div class='summary-bar'>
                <span class='failed'>{failed} Failed</span>
                <span class='passed'>{passed} Passed</span>
                <span class='skipped'>{skipped} Skipped</span>
                <span>0 Errors</span>
                <span>0 Reruns</span>
            </div>
            <div>{total} test(s) took {duration}</div>
            <table class='summary-table' style='width: 100%; margin-top: 1em;'>
                <tr>
                    <th>Result</th>
                    <th>Status</th>
                    <th>Scenario Name</th>
                    <th>Duration</th>
                </tr>
        """
        for s in scenario_results:
            # Use result and status fields directly
            result = s.get("result", "Unknown").capitalize()
            status = s.get("status", "Unknown").capitalize()
            # Color class for result
            result_class = result.lower()
            # Color class for status
            status_class = status.lower()
            html_content += f"<tr>"
            html_content += (
                f"<td class='{result_class}' style='font-weight: bold;'>{result}</td>"
            )
            html_content += f"<td class='{status_class}'>{status}</td>"
            html_content += f"<td>{s['name']}</td>"
            html_content += f"<td class='duration'>{s['duration']}</td>"
            html_content += f"</tr>"
        html_content += """
            </table>
        </body>
        </html>
        """
        # Save report only when explicitly enabled via env
        if os.getenv("ENABLE_FILE_REPORTS", "false").lower() == "true":
            reports_dir = Path(__file__).parent.parent.parent / "reports"
            reports_dir.mkdir(exist_ok=True)
            report_path = (
                reports_dir / f"simulation_report_{end_time.strftime('%Y%m%d_%H%M%S')}.html"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            if self.logger:
                self.logger.info(f"HTML report generated: {report_path}")

        # Also store report in DB if tenant context is present (prefer request-scoped)
        try:
            from carla_simulator.utils.logging import CURRENT_TENANT_ID
            tenant_ctx = None
            try:
                tenant_ctx = CURRENT_TENANT_ID.get()
            except Exception:
                tenant_ctx = None
            tenant_id = tenant_ctx
            if tenant_id is None:
                tenant_env = os.environ.get("CONFIG_TENANT_ID")
                if tenant_env:
                    tenant_id = int(tenant_env)
            if tenant_id is not None:
                report_name = (locals().get('report_path').name if 'report_path' in locals() else f"simulation_report_{end_time.strftime('%Y%m%d_%H%M%S')}.html")
                from carla_simulator.database.db_manager import DatabaseManager
                dbm = DatabaseManager()
                SimulationReport.create(dbm, name=report_name, html=html_content, tenant_id=int(tenant_id))
        except Exception:
            # Don't fail simulation if report DB save fails
            pass
            # self.logger.info(f"Report directory: {reports_dir.absolute()}")


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
            scenarios=self._create_scenario_config(),
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
        """Load configuration, preferring DB when CONFIG_TENANT_ID is set; fallback to YAML."""
        try:
            from carla_simulator.utils.config import _load_config_dict

            # Resolve relative path to absolute for YAML fallback resolution
            if not os.path.isabs(config_path):
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    config_path,
                )

            config = _load_config_dict(config_path) or {}

            # Use scenario from argument
            if scenario:
                config["scenario"] = scenario

            return config
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {str(e)}")

    def _create_server_config(self) -> ServerConfig:
        """Create ServerConfig object from configuration"""
        server = self.config.get("server")
        if not server:
            raise ValueError("Missing required 'server' configuration section")

        return ServerConfig(
            host=server["host"],
            port=server["port"],
            timeout=server["timeout"],
            connection=server.get("connection", {}),
        )

    def _create_world_config(self) -> WorldConfig:
        """Create WorldConfig object from configuration"""
        world = self.config.get("world")
        if not world:
            raise ValueError("Missing required 'world' configuration section")
        # Sanitize unknown keys (e.g., 'walkers') and nested extras to match dataclass
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
        world_filtered = {k: v for k, v in world.items() if k in allowed_world_keys}

        # Filter nested blocks
        weather_block = world_filtered.get("weather", world.get("weather", {})) or {}
        physics_block = world_filtered.get("physics", world.get("physics", {})) or {}
        traffic_block = world_filtered.get("traffic", world.get("traffic", {})) or {}

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

        return WorldConfig(
            map=world_filtered["map"],
            weather=weather_block,
            physics=physics_block,
            traffic=traffic_block,
            fixed_delta_seconds=world_filtered["fixed_delta_seconds"],
            target_distance=world_filtered["target_distance"],
            num_vehicles=world_filtered["num_vehicles"],
            enable_collision=world_filtered["enable_collision"],
            synchronous_mode=world_filtered["synchronous_mode"],
        )

    def _create_simulation_config(self) -> SimConfig:
        """Create SimulationConfig object from configuration"""
        simulation = self.config.get("simulation")
        if not simulation:
            raise ValueError("Missing required 'simulation' configuration section")

        return SimConfig(
            max_speed=simulation["max_speed"],
            simulation_time=simulation["simulation_time"],
            update_rate=simulation["update_rate"],
            speed_change_threshold=simulation["speed_change_threshold"],
            position_change_threshold=simulation["position_change_threshold"],
            heading_change_threshold=simulation["heading_change_threshold"],
            target_tolerance=simulation["target_tolerance"],
            max_collision_force=simulation["max_collision_force"],
        )

    def _create_logging_config(self) -> LoggingConfig:
        """Create LoggingConfig object from configuration"""
        logging = self.config.get("logging")
        if not logging:
            raise ValueError("Missing required 'logging' configuration section")

        return LoggingConfig(
            log_level=logging["log_level"],
            enabled=logging["enabled"],
            directory=logging["directory"],
        )

    def _create_display_config(self) -> DisplayConfig:
        """Create DisplayConfig object from configuration"""
        display = self.config.get("display")
        if not display:
            raise ValueError("Missing required 'display' configuration section")

        return DisplayConfig(
            width=display["width"],
            height=display["height"],
            fps=display["fps"],
            hud=display.get("hud", {}),
            minimap=display.get("minimap", {}),
            camera=display.get("camera", {}),
            hud_enabled=display["hud_enabled"],
            minimap_enabled=display["minimap_enabled"],
        )

    def _create_sensor_config(self) -> SensorConfig:
        """Create SensorConfig object from configuration"""
        sensors = self.config.get("sensors")
        if not sensors:
            raise ValueError("Missing required 'sensors' configuration section")

        # Create individual sensor configs
        camera_config = CameraConfig(
            enabled=sensors.get("camera", {}).get("enabled", True),
            width=sensors.get("camera", {}).get("width", 1280),
            height=sensors.get("camera", {}).get("height", 720),
            fov=sensors.get("camera", {}).get("fov", 90),
            x=sensors.get("camera", {}).get("x", -2.5),
            y=sensors.get("camera", {}).get("y", 0.0),
            z=sensors.get("camera", {}).get("z", 2.0),
        )

        collision_config = CollisionConfig(
            enabled=sensors.get("collision", {}).get("enabled", True)
        )

        gnss_config = GNSSConfig(enabled=sensors.get("gnss", {}).get("enabled", True))

        return SensorConfig(
            camera=camera_config, collision=collision_config, gnss=gnss_config
        )

    def _create_controller_config(self) -> ControllerConfig:
        """Create ControllerConfig object from configuration"""
        controller = self.config.get("controller")
        if not controller:
            raise ValueError("Missing required 'controller' configuration section")

        keyboard = controller.get("keyboard")
        if not keyboard:
            raise ValueError("Missing required 'keyboard' configuration section")

        # Create keyboard config using values from config file
        keyboard_config = KeyboardConfig(
            forward=keyboard["forward"],
            backward=keyboard["backward"],
            left=keyboard["left"],
            right=keyboard["right"],
            brake=keyboard["brake"],
            hand_brake=keyboard["hand_brake"],
            reverse=keyboard["reverse"],
            quit=keyboard["quit"],
        )

        return ControllerConfig(
            type=controller["type"],
            steer_speed=controller["steer_speed"],
            throttle_speed=controller["throttle_speed"],
            brake_speed=controller["brake_speed"],
            keyboard=keyboard_config,
        )

    def _create_scenario_config(self) -> ScenarioConfig:
        """Create ScenarioConfig object from configuration"""
        scenarios = self.config.get("scenarios")
        if not scenarios:
            raise ValueError("Missing required 'scenarios' configuration section")

        return ScenarioConfig(
            follow_route=scenarios.get("follow_route", {}),
            avoid_obstacle=scenarios.get("avoid_obstacle", {}),
            emergency_brake=scenarios.get("emergency_brake", {}),
            vehicle_cutting=scenarios.get("vehicle_cutting", {}),
        )

    def _create_vehicle_config(self) -> VehicleConfig:
        """Create VehicleConfig object from configuration"""
        vehicle = self.config.get("vehicle")
        if not vehicle:
            raise ValueError("Missing required 'vehicle' configuration section")

        return VehicleConfig(
            model=vehicle["model"],
            mass=vehicle["mass"],
            drag_coefficient=vehicle["drag_coefficient"],
            max_rpm=vehicle["max_rpm"],
            moi=vehicle["moi"],
            center_of_mass=vehicle["center_of_mass"],
        )

    def validate_config(self) -> None:
        """Validate configuration values"""
        if "server" not in self.config:
            raise ValueError("Missing required 'server' configuration section")

        server = self.config["server"]
        required_keys = ["host", "port", "timeout"]
        for key in required_keys:
            if key not in server:
                raise ValueError(f"Missing required server config key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
