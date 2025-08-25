from typing import Optional, Dict, Any
import time
import carla
from carla_simulator.core.simulation_components import (
    ConnectionManager,
    SimulationState,
    SimulationMetrics,
    SimulationConfig,
)
from carla_simulator.core.interfaces import (
    IWorldManager,
    IVehicleController,
    ISensorManager,
    ILogger,
    IScenario,
)
from carla_simulator.scenarios.scenario_registry import ScenarioRegistry
from carla_simulator.utils.config import LoggingConfig
# Lazy-import DisplayManager/VehicleState to avoid pygame initialization at app startup
import threading
from carla_simulator.database.config import SessionLocal
from carla_simulator.database.models import Scenario, VehicleData, SensorData
from datetime import datetime


class SimulationApplication:
    """Main application class that coordinates all simulation components"""

    # Class-level cleanup tracking
    cleanup_lock = threading.Lock()

    def __init__(self, config_path: str, scenario: str, session_id, logger: ILogger):
        # Initialize configuration
        self._config = SimulationConfig(config_path, scenario)

        # Initialize logger first
        self.logger = logger

        # Initialize connection manager with server config
        self.connection = ConnectionManager(self._config.server_config, self.logger)

        # Initialize state and metrics
        self.state = SimulationState()
        self.metrics = None  # Will be initialized after logger

        # Component references (will be set during setup)
        self.world_manager: Optional[IWorldManager] = None
        self.vehicle_controller: Optional[IVehicleController] = None
        self.sensor_manager: Optional[ISensorManager] = None
        self.current_scenario: Optional[IScenario] = None
        self.display_manager = None  # type: ignore[assignment]

        # Add results cache
        self._cleanup_results = None
        self._cleanup_results_lock = threading.Lock()
        # HUD snapshot shared with websocket
        self._hud_payload = None
        self._hud_lock = threading.Lock()

        # Require session_id to be provided
        if session_id is None:
            raise ValueError("session_id must be provided by SimulationRunner.")
        self.session_id = session_id

        # Instance-level cleanup tracking (not shared across instances)
        self.is_cleanup_complete = False

        # Do not connect here; connect only in setup()

    def setup(
        self,
        world_manager: IWorldManager,
        vehicle_controller: IVehicleController,
        sensor_manager: ISensorManager,
        logger: ILogger,
    ) -> None:
        """Setup the simulation application"""
        self.logger.info("[SimulationApplication] Setting up simulation components...")

        # Initialize components
        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.sensor_manager = sensor_manager
        self.logger = logger

        # Verify components are properly initialized
        if not self.world_manager:
            raise RuntimeError("World manager not properly initialized")
        if not self.vehicle_controller:
            raise RuntimeError("Vehicle controller not properly initialized")
        if not self.sensor_manager:
            raise RuntimeError("Sensor manager not properly initialized")
        if not self.logger:
            raise RuntimeError("Logger not properly initialized")

        # Verify world manager is ready
        try:
            world = self.world_manager.get_world()
            if not world:
                raise RuntimeError("Failed to get CARLA world")
            self.logger.debug(
                "[SimulationApplication] World manager initialized successfully"
            )
        except Exception as e:
            raise RuntimeError(f"World manager initialization failed: {str(e)}")

        # Verify vehicle controller is ready
        try:
            vehicle = self.vehicle_controller.get_vehicle()
            if not vehicle:
                raise RuntimeError("Failed to get vehicle")
            self.logger.debug(
                "[SimulationApplication] Vehicle controller initialized successfully"
            )
        except Exception as e:
            raise RuntimeError(f"Vehicle controller initialization failed: {str(e)}")

        # Initialize metrics after logger is available
        self.metrics = SimulationMetrics(logger)
        self.logger.debug("[SimulationApplication] Metrics initialized")

        # Initialize display manager
        self.logger.debug("[SimulationApplication] Initializing display manager...")
        is_web_mode = getattr(self._config, "web_mode", False)
        # Import here to ensure SDL envs are set beforehand
        from carla_simulator.visualization.display_manager import DisplayManager
        self.display_manager = DisplayManager(self._config.display_config, web_mode=is_web_mode)
        self.logger.debug("[SimulationApplication] Display manager initialized")

        # Attach camera view to sensor manager
        self.logger.debug("[SimulationApplication] Setting up camera...")
        camera_sensor = self.sensor_manager.get_sensor("camera")
        if camera_sensor:
            self.logger.debug(
                "[SimulationApplication] Camera sensor found, attaching view..."
            )
            camera_sensor.attach(self.display_manager.camera_view)
            self.logger.debug(
                "[SimulationApplication] Camera view attached to sensor manager"
            )
        else:
            self.logger.debug("[SimulationApplication] ERROR: Camera sensor not found!")

        # Verify connection is valid
        self.logger.debug("[SimulationApplication] Verifying CARLA connection...")
        if not self.connection.client:
            raise RuntimeError("CARLA client is not initialized")

        try:
            # Test connection by getting world
            self.logger.debug(
                "[SimulationApplication] Attempting to get CARLA world..."
            )
            world = self.connection.client.get_world()
            if not world:
                raise RuntimeError("Failed to get CARLA world")
            self.logger.debug(
                "[SimulationApplication] Successfully connected to CARLA world"
            )
        except Exception as e:
            self.logger.debug(
                f"[SimulationApplication] ERROR: Failed to connect to CARLA server: {str(e)}"
            )
            raise RuntimeError(f"Failed to connect to CARLA server: {str(e)}")

        # Create initial scenario
        self.logger.debug("[SimulationApplication] Setting up initial scenario...")
        self._setup_scenario(self._config.get("scenario", "follow_route"))
        self.logger.debug("[SimulationApplication] Setup completed successfully")

    def _setup_scenario(
        self, scenario_type: str, scenario_config: Optional[Dict] = None
    ) -> None:
        """Setup a new scenario"""
        try:
            self.logger.debug(f"Setting up scenario: {scenario_type}")

            # Verify required components are initialized
            if not self.world_manager:
                raise RuntimeError("World manager not initialized")
            if not self.vehicle_controller:
                raise RuntimeError("Vehicle controller not initialized")
            if not self.logger:
                raise RuntimeError("Logger not initialized")

            # Get scenario configuration from main config
            if scenario_config is None:
                scenario_config = self._config.scenario_config.__dict__.get(
                    scenario_type, {}
                )
                # Convert dataclass to dictionary if needed
                if hasattr(scenario_config, "__dict__"):
                    scenario_config = scenario_config.__dict__

            # Create scenario using registry
            self.logger.debug("Creating scenario from registry...")

            new_scenario = ScenarioRegistry.create_scenario(
                scenario_type=scenario_type,
                world_manager=self.world_manager,
                vehicle_controller=self.vehicle_controller,
                logger=self.logger,
                config=scenario_config,
            )

            if not new_scenario:
                raise RuntimeError(f"Failed to create scenario: {scenario_type}")

            # Setup the scenario
            self.logger.debug("Setting up new scenario...")

            new_scenario.setup()

            # Only set current_scenario after successful setup
            self.current_scenario = new_scenario

            self.logger.debug(f"Scenario setup completed: {scenario_type}")
            self.logger.info(f"Started scenario: {scenario_type}")

        except Exception as e:
            self.logger.warning(f"Error setting up scenario: {str(e)}")
            # Ensure current_scenario is None if setup fails
            self.current_scenario = None
            # Propagate failure so HTTP start returns 500 and UI doesn't show success
            raise RuntimeError(f"Failed to setup scenario: {str(e)}")

    def run(self) -> None:
        """Run the simulation loop"""
        if not self.current_scenario:
            raise RuntimeError("No scenario set")

        # --- DB: Create a new Scenario row for each scenario execution ---
        db = SessionLocal()
        new_scenario = Scenario(
            session_id=self.session_id,
            scenario_name=getattr(self.current_scenario, "name", "Unknown"),
            start_time=datetime.utcnow(),
            status="running",
            scenario_metadata={},
        )
        db.add(new_scenario)
        db.commit()
        db.refresh(new_scenario)
        scenario_id = new_scenario.scenario_id
        db.close()
        self.logger.set_scenario_id(scenario_id)
        self.logger.set_session_id(self.session_id)
        # --- End DB scenario creation ---

        self.state.start()
        self.logger.info("Starting simulation loop")

        # Test database connection before starting simulation loop
        # try:
        #     db = SessionLocal()
        #     db.execute("SELECT 1")  # Simple test query
        #     db.close()
        #     self.logger.info("Database connection test successful")
        # except Exception as e:
        #     self.logger.error(f"Database connection test failed: {str(e)}")
        #     # Continue anyway, but log the issue

        try:
            world = self.connection.client.get_world()
            frame_count = 0
            
            # Determine if we are in web mode to adjust workload (DB writes, rendering)
            is_web_mode = getattr(self._config, "web_mode", False)
            # Throttle DB writes to once per second (time-based, independent of FPS)
            last_db_write_ts = time.time()

            while self.state.is_running and not self.current_scenario.is_completed():
                frame_count += 1
                loop_start = time.time()

                # # Debug: Log every 30 frames to track progress
                # if frame_count % 30 == 0:
                #     self.logger.debug(f"Simulation frame {frame_count}: is_running={self.state.is_running}, scenario_completed={self.current_scenario.is_completed()}")

                if self.state.is_paused:
                    time.sleep(0.1)
                    continue

                # Process input first (keyboard events, etc.)
                try:
                    if self.vehicle_controller.process_input():
                        self.logger.info("Vehicle controller requested exit")
                        break  # Exit if process_input returns True
                except Exception as e:
                    self.logger.error(f"Error in vehicle controller input processing: {str(e)}")

                # Get sensor data
                try:
                    sensor_data = self.sensor_manager.get_sensor_data()
                except Exception as e:
                    self.logger.error(f"Error getting sensor data: {str(e)}")
                    sensor_data = {}

                # Get vehicle state
                try:
                    vehicle = self.vehicle_controller.get_vehicle()
                    if not vehicle:
                        self.logger.warning("No vehicle available, skipping frame")
                        continue
                except Exception as e:
                    self.logger.error(f"Error getting vehicle: {str(e)}")
                    continue

                try:
                    vehicle_state = {
                        "location": vehicle.get_location(),
                        "velocity": vehicle.get_velocity(),
                        "acceleration": vehicle.get_acceleration(),
                        "transform": vehicle.get_transform(),
                        "sensor_data": sensor_data,
                    }
                except Exception as e:
                    self.logger.error(f"Error getting vehicle state: {str(e)}")
                    continue

                # --- DB: Write vehicle and sensor data (once per second) ---
                try:
                    now_ts = time.time()
                    if (now_ts - last_db_write_ts) >= 1.0:
                        db = SessionLocal()
                        try:
                            db.add(
                                VehicleData(
                                    scenario_id=scenario_id,
                                    session_id=self.session_id,
                                    timestamp=datetime.utcnow(),
                                    position_x=vehicle_state["location"].x,
                                    position_y=vehicle_state["location"].y,
                                    position_z=vehicle_state["location"].z,
                                    velocity=vehicle_state["velocity"].length(),
                                    acceleration=vehicle_state["acceleration"].length(),
                                    steering_angle=vehicle_state["transform"].rotation.yaw,
                                    throttle=getattr(vehicle, "throttle", 0.0),
                                    brake=getattr(vehicle, "brake", 0.0),
                                )
                            )
                            # Write latest sensor data snapshot in same transaction
                            for sensor_type, sdata in (
                                sensor_data.items() if isinstance(sensor_data, dict) else []
                            ):
                                db.add(
                                    SensorData(
                                        scenario_id=scenario_id,
                                        session_id=self.session_id,
                                        timestamp=datetime.utcnow(),
                                        sensor_type=sensor_type,
                                        data=sdata,
                                    )
                                )
                            db.commit()
                            last_db_write_ts = now_ts
                        finally:
                            db.close()
                except Exception as e:
                    self.logger.error(f"Error writing data to DB (1 Hz): {str(e)}")
                # --- End DB write ---

                # (Sensor data write moved above into the 1 Hz combined write)

                try:
                    # Update scenario and autopilot movement
                    self.current_scenario.update()
                    # Nudge traffic manager each tick to ensure autopilot moves
                    try:
                        vc = self.vehicle_controller
                        if vc and hasattr(vc, "_strategy") and vc._strategy:
                            # Ensure autopilot strategy sync
                            if hasattr(vc._strategy, "process_input"):
                                vc._strategy.process_input()
                    except Exception:
                        pass
                    # Update HUD snapshot (best-effort)
                    try:
                        ctrl = vehicle.get_control()
                        
                        # Determine control type from configuration
                        control_type = "Autopilot"
                        scenario_name = getattr(self.current_scenario, "name", "Unknown")
                        
                        # Get controller type from configuration
                        if hasattr(self, '_config') and hasattr(self._config, 'controller_config'):
                            config_type = self._config.controller_config.type
                            if config_type == "keyboard":
                                control_type = "Keyboard"
                            elif config_type == "gamepad":
                                control_type = "Gamepad"
                            elif config_type == "autopilot":
                                control_type = "Autopilot"
                        
                        payload = {
                            "scenarioName": scenario_name,
                            "speedKmh": float(vehicle_state["velocity"].length() * 3.6) if isinstance(vehicle_state.get("velocity"), carla.Vector3D) else 0.0,
                            "gear": int(getattr(ctrl, "gear", 1)),
                            "controlType": control_type,
                            "fps": float(self.metrics.metrics.get("fps", 0.0)) if self.metrics else 0.0,
                        }
                        with self._hud_lock:
                            self._hud_payload = payload
                    except Exception:
                        pass
                except Exception as e:
                    self.logger.error("Exception in scenario update", exc_info=e)

                try:
                    # Apply vehicle control
                    control = self.vehicle_controller.get_control(vehicle_state)
                    vehicle.apply_control(control)
                except Exception as e:
                    self.logger.error("Exception in control/apply", exc_info=e)

                try:
                    # Update metrics
                    self.metrics.update(vehicle_state)
                except Exception as e:
                    self.logger.error("Exception in metrics update", exc_info=e)

                try:
                    # Render display
                    if self.display_manager and self.state.is_running:
                        from carla_simulator.visualization.display_manager import VehicleState
                        display_state = VehicleState(
                            speed=vehicle_state["velocity"].length(),
                            position=(
                                vehicle_state["location"].x,
                                vehicle_state["location"].y,
                                vehicle_state["location"].z,
                            ),
                            heading=vehicle_state["transform"].rotation.yaw,
                            distance_to_target=0.0,  # This should be updated by the scenario
                            controls={
                                "throttle": getattr(vehicle, "throttle", 0.0),
                                "brake": getattr(vehicle, "brake", 0.0),
                                "steer": getattr(vehicle, "steer", 0.0),
                                "gear": getattr(vehicle, "gear", 1),
                                "hand_brake": getattr(vehicle, "hand_brake", False),
                                "reverse": getattr(vehicle, "reverse", False),
                                "manual_gear_shift": getattr(
                                    vehicle, "manual_gear_shift", False
                                ),
                            },
                            speed_kmh=vehicle_state["velocity"].length() * 3.6,
                            scenario_name=self.current_scenario.name,
                        )
                        target_pos = getattr(
                            self.current_scenario, "target_position", None
                        )
                        if target_pos is None:
                            target_pos = carla.Location()
                        if not self.display_manager.render(display_state, target_pos):
                            self.logger.info("Display manager requested exit")
                            break
                except Exception as e:
                    self.logger.error("Exception in display rendering", exc_info=e)

                try:
                    # Log metrics periodically
                    if self.metrics.metrics["frame_count"] % 30 == 0:
                        self.metrics.log_metrics()
                except Exception as e:
                    self.logger.error("Exception in logging", exc_info=e)

                try:
                    world.tick()
                except Exception as e:
                    self.logger.error(f"Error in world tick: {str(e)}")
                    break

            # Log why the loop ended
            if not self.state.is_running:
                self.logger.info("Simulation loop ended: state.is_running = False")
            elif self.current_scenario.is_completed():
                self.logger.info("Simulation loop ended: scenario completed")
            else:
                self.logger.info(f"Simulation loop ended: frame_count = {frame_count}")

        except Exception as e:
            self.logger.error("Error in simulation loop", exc_info=e)
            raise
        finally:
            self.logger.debug("Simulation loop cleanup starting")
            self.cleanup()
            self.logger.debug("Simulation loop cleanup completed")

    def pause(self) -> None:
        """Pause the simulation"""
        self.state.pause()
        self.logger.info("Simulation paused")

    def resume(self) -> None:
        """Resume the simulation"""
        self.state.resume()
        self.logger.info("Simulation resumed")

    def stop(self) -> None:
        """Stop the simulation"""
        if self.state.is_running:
            self.state.stop()
            self.logger.info("Simulation stopped")

            # Add consistent logging format for scenario stop
            if self.current_scenario:
                scenario_name = getattr(self.current_scenario, "name", None)
                scenario_completed = self.current_scenario.is_completed()
                scenario_success = self.current_scenario.is_successful()

                self.logger.info("================================")
                self.logger.info(f"Stopping scenario: {scenario_name}")
                self.logger.info(
                    f"Status: {'Completed' if scenario_completed else 'Incomplete'}"
                )
                self.logger.info(
                    f"Result: {'Success' if scenario_success else 'Failed'}"
                )
                self.logger.info("================================")

    def cleanup(self) -> None:
        """Clean up simulation resources"""
        try:
            # Check if we already have results
            with self._cleanup_results_lock:
                if self._cleanup_results is not None:
                    return self._cleanup_results

            self.logger.debug("Starting cleanup process...")

            # First stop any ongoing simulation
            self.logger.debug("Stopping simulation...")
            self.stop()

            # Store scenario completion status before cleanup
            scenario_completed = False
            scenario_success = False

            # Safely check and cleanup current scenario
            if hasattr(self, "current_scenario") and self.current_scenario is not None:
                try:
                    # Store scenario info before cleanup
                    scenario_name = getattr(self.current_scenario, "name", None)
                    scenario_completed = self.current_scenario.is_completed()
                    scenario_success = self.current_scenario.is_successful()

                    # self.logger.info("================================")
                    # self.logger.info(f"Cleaning up scenario: {scenario_name}")
                    # self.logger.info(f"Status: {'Completed' if scenario_completed else 'Incomplete'}")
                    # self.logger.info(f"Result: {'Success' if scenario_success else 'Failed'}")
                    # self.logger.info("================================")

                    # Cleanup the scenario (only state cleanup, no actor destruction)
                    self.current_scenario.cleanup()

                    self.logger.debug(f"Scenario cleanup completed: {scenario_name}")

                except Exception as e:
                    self.logger.error(f"Error during scenario cleanup: {str(e)}")
                finally:
                    # Clear the scenario reference
                    self.current_scenario = None
                    self.logger.debug("Current scenario reference cleared")

            # Clean up sensors first
            if self.sensor_manager:
                self.logger.debug("Cleaning up sensor manager...")
                try:
                    self.sensor_manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up sensor manager: {str(e)}")

            # Clean up display
            if self.display_manager:
                self.logger.debug("Cleaning up display manager...")
                try:
                    self.display_manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up display manager: {str(e)}")

            # Clean up world and all actors last
            if self.world_manager:
                self.logger.debug("Cleaning up world manager...")
                try:
                    # Debug: Show tracked actors before cleanup
                    if hasattr(self.world_manager, 'get_all_tracked_actors'):
                        tracked_actors = self.world_manager.get_all_tracked_actors()
                        self.logger.debug(f"Tracked actors before cleanup: {tracked_actors}")
                    
                    # First destroy all actors including the vehicle
                    self.world_manager.cleanup()
                    # Add a small delay to ensure actors are destroyed
                    time.sleep(0.5)
                    
                    # Avoid calling force_cleanup_all_actors to prevent native crashes in libcarla
                except Exception as e:
                    self.logger.error(f"Error cleaning up world manager: {str(e)}")

            # Clean up vehicle controller after world cleanup
            if self.vehicle_controller:
                self.logger.debug("Cleaning up vehicle controller...")
                try:
                    self.vehicle_controller.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up vehicle controller: {str(e)}")

            # Check if we're in web mode
            is_web_mode = getattr(self._config, "web_mode", False)
            if is_web_mode:
                self.logger.debug(
                    "Web mode: Maintaining CARLA connection for next scenario"
                )
            else:
                self.logger.debug("CLI mode: Disconnecting from CARLA server")
                self.connection.disconnect()

            # Clear component references
            self.vehicle_controller = None
            self.sensor_manager = None
            self.display_manager = None
            self.world_manager = None

            # Force garbage collection
            import gc

            gc.collect()

            # Set cleanup flag
            with self.cleanup_lock:
                self.is_cleanup_complete = True

            self.logger.info("Cleanup completed")

            # Store results
            with self._cleanup_results_lock:
                self._cleanup_results = (scenario_completed, scenario_success)

            # Return completion status
            return scenario_completed, scenario_success

        except Exception as e:
            self.logger.error(f"Error in cleanup: {str(e)}")
            # Set cleanup flag even on error
            with self.cleanup_lock:
                self.is_cleanup_complete = True
            # Store error results
            with self._cleanup_results_lock:
                self._cleanup_results = (False, False)
            return False, False

    def get_cleanup_results(self) -> tuple[bool, bool]:
        """Get the stored cleanup results without performing cleanup again"""
        with self._cleanup_results_lock:
            if self._cleanup_results is None:
                return False, False
            return self._cleanup_results

    def get_hud_payload(self) -> Optional[dict]:
        """Get the latest HUD payload (thread-safe)."""
        try:
            with self._hud_lock:
                return dict(self._hud_payload) if isinstance(self._hud_payload, dict) else None
        except Exception:
            return None

    @property
    def logging_config(self):
        """Get logging configuration"""
        return self._config.logging_config

    @property
    def world_config(self):
        """Get world configuration"""
        return self._config.world_config

    @property
    def sensor_config(self):
        """Get sensor configuration"""
        return self._config.sensor_config

    @property
    def controller_config(self):
        """Get controller configuration"""
        return self._config.controller_config

    @property
    def config(self):
        """Get the main configuration"""
        return self._config
