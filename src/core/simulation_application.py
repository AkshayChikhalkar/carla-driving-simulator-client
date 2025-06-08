from typing import Optional, Dict, Any
import time
import carla
from src.core.simulation_components import (
    ConnectionManager,
    SimulationState,
    SimulationMetrics,
    SimulationConfig
)
from src.core.interfaces import (
    IWorldManager,
    IVehicleController,
    ISensorManager,
    ILogger,
    IScenario
)
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.config import LoggingConfig
from src.visualization.display_manager import DisplayManager, VehicleState
import threading

class SimulationApplication:
    """Main application class that coordinates all simulation components"""

    # Class-level cleanup tracking
    cleanup_lock = threading.Lock()
    is_cleanup_complete = False

    def __init__(self, config_path: str, scenario: str = None, logger: ILogger = None):
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
        self.display_manager: Optional[DisplayManager] = None
        # Do not connect here; connect only in setup()

    def setup(self,
             world_manager: IWorldManager,
             vehicle_controller: IVehicleController,
             sensor_manager: ISensorManager,
             logger: ILogger) -> None:
        """Setup the simulation application"""
        self.logger.info("[SimulationApplication] Setting up simulation components...")

        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.sensor_manager = sensor_manager
        # Update logger with the provided one
        self.logger = logger

        self.logger.debug("[SimulationApplication] Basic components initialized")

        # Initialize metrics after logger is available
        self.metrics = SimulationMetrics(logger)
        self.logger.debug("[SimulationApplication] Metrics initialized")

        # Initialize display manager
        self.logger.debug("[SimulationApplication] Initializing display manager...")
        # Check if we're in web mode
        is_web_mode = getattr(self._config, 'web_mode', False)
        self.display_manager = DisplayManager(self._config.display_config, web_mode=is_web_mode)
        self.logger.debug("[SimulationApplication] Display manager initialized")

        # Attach camera view to sensor manager
        self.logger.debug("[SimulationApplication] Setting up camera...")
        camera_sensor = self.sensor_manager.get_sensor('camera')
        if camera_sensor:
            self.logger.debug("[SimulationApplication] Camera sensor found, attaching view...")
            camera_sensor.attach(self.display_manager.camera_view)
            self.logger.debug("[SimulationApplication] Camera view attached to sensor manager")
        else:
            self.logger.debug("[SimulationApplication] ERROR: Camera sensor not found!")

        # Verify connection is valid
        self.logger.debug("[SimulationApplication] Verifying CARLA connection...")
        if not self.connection.client:
            raise RuntimeError("CARLA client is not initialized")

        try:
            # Test connection by getting world
            self.logger.debug("[SimulationApplication] Attempting to get CARLA world...")
            world = self.connection.client.get_world()
            if not world:
                raise RuntimeError("Failed to get CARLA world")
            self.logger.debug("[SimulationApplication] Successfully connected to CARLA world")
        except Exception as e:
            self.logger.debug(f"[SimulationApplication] ERROR: Failed to connect to CARLA server: {str(e)}")
            raise RuntimeError(f"Failed to connect to CARLA server: {str(e)}")

        # Create initial scenario
        self.logger.debug("[SimulationApplication] Setting up initial scenario...")
        self._setup_scenario(self._config.get('scenario', 'follow_route'))
        self.logger.debug("[SimulationApplication] Setup completed successfully")

    def _setup_scenario(self, scenario_type: str, scenario_config: Optional[Dict] = None) -> None:
        """Setup a new scenario"""
        try:
            self.logger.debug(f"Setting up scenario: {scenario_type}")

            # Verify required components are initialized
            if not all([self.world_manager, self.vehicle_controller, self.logger]):
                raise RuntimeError("Application not properly initialized")

            # Get scenario configuration from main config
            if scenario_config is None:
                scenario_config = self._config.scenario_config.__dict__.get(scenario_type, {})
                # Convert dataclass to dictionary if needed
                if hasattr(scenario_config, '__dict__'):
                    scenario_config = scenario_config.__dict__

            # Create scenario using registry
            self.logger.debug("Creating scenario from registry...")

            new_scenario = ScenarioRegistry.create_scenario(
                scenario_type=scenario_type,
                world_manager=self.world_manager,
                vehicle_controller=self.vehicle_controller,
                logger=self.logger,
                config=scenario_config
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
            self.logger.error(f"Error setting up scenario: {str(e)}")
            # Ensure current_scenario is None if setup fails
            self.current_scenario = None
            raise RuntimeError(f"Failed to setup scenario: {str(e)}")

    def run(self) -> None:
        """Run the simulation loop"""
        if not self.current_scenario:
            raise RuntimeError("No scenario set")

        self.state.start()
        self.logger.info("Starting simulation loop")

        try:
            world = self.connection.client.get_world()

            while self.state.is_running and not self.current_scenario.is_completed():
                loop_start = time.time()

                if self.state.is_paused:
                    time.sleep(0.1)
                    continue

                # Process input first (keyboard events, etc.)
                if self.vehicle_controller.process_input():
                    break  # Exit if process_input returns True

                # Get sensor data
                sensor_data = self.sensor_manager.get_sensor_data()

                # Get vehicle state
                vehicle = self.vehicle_controller.get_vehicle()
                if not vehicle:
                    continue

                vehicle_state = {
                    'location': vehicle.get_location(),
                    'velocity': vehicle.get_velocity(),
                    'acceleration': vehicle.get_acceleration(),
                    'transform': vehicle.get_transform(),
                    'sensor_data': sensor_data
                }

                try:
                    # Update scenario
                    self.current_scenario.update()
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
                    if self.display_manager:
                        display_state = VehicleState(
                            speed=vehicle_state['velocity'].length(),
                            position=(
                                vehicle_state['location'].x,
                                vehicle_state['location'].y,
                                vehicle_state['location'].z
                            ),
                            heading=vehicle_state['transform'].rotation.yaw,
                            distance_to_target=0.0,  # This should be updated by the scenario
                            controls={
                                'throttle': control.throttle,
                                'brake': control.brake,
                                'steer': control.steer,
                                'gear': control.gear,
                                'hand_brake': control.hand_brake,
                                'reverse': control.reverse,
                                'manual_gear_shift': control.manual_gear_shift
                            },
                            speed_kmh=vehicle_state['velocity'].length() * 3.6,
                            scenario_name=self.current_scenario.name
                        )

                        # Get target position from scenario if available
                        target_pos = getattr(self.current_scenario, 'target_position', None)
                        if target_pos is None:
                            target_pos = carla.Location()

                        # Render display and check for quit signal
                        if not self.display_manager.render(display_state, target_pos):
                            self.logger.info("Display manager requested exit")
                            break
                except Exception as e:
                    self.logger.error("Exception in display rendering", exc_info=e)

                try:
                    # Log metrics periodically
                    if self.metrics.metrics['frame_count'] % 30 == 0:
                        self.metrics.log_metrics()
                        # self.logger.log_vehicle_state(vehicle_state)
                except Exception as e:
                    self.logger.error("Exception in logging", exc_info=e)

                # Tick the CARLA world (required for synchronous mode)
                world.tick()

        except Exception as e:
            self.logger.error("Error in simulation loop", exc_info=e)
            raise
        finally:
            self.cleanup()

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
                scenario_name = getattr(self.current_scenario, 'name', None)
                scenario_completed = self.current_scenario.is_completed()
                scenario_success = self.current_scenario.is_successful()
                
                self.logger.info("================================")
                self.logger.info(f"Stopping scenario: {scenario_name}")
                self.logger.info(f"Status: {'Completed' if scenario_completed else 'Incomplete'}")
                self.logger.info(f"Result: {'Success' if scenario_success else 'Failed'}")
                self.logger.info("================================")

    def cleanup(self) -> None:
        """Clean up simulation resources"""
        try:
            self.logger.debug("Starting cleanup process...")

            # First stop any ongoing simulation
            self.logger.debug("Stopping simulation...")
            self.stop()

            # Store scenario completion status before cleanup
            scenario_completed = False
            scenario_success = False

            # Safely check and cleanup current scenario
            if hasattr(self, 'current_scenario') and self.current_scenario is not None:
                try:
                    # Store scenario info before cleanup
                    scenario_name = getattr(self.current_scenario, 'name', None)
                    scenario_completed = self.current_scenario.is_completed()
                    scenario_success = self.current_scenario.is_successful()

                    self.logger.info("================================")
                    self.logger.info(f"Cleaning up scenario: {scenario_name}")
                    self.logger.info(f"Status: {'Completed' if scenario_completed else 'Incomplete'}")
                    self.logger.info(f"Result: {'Success' if scenario_success else 'Failed'}")
                    self.logger.info("================================")

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

            # Clean up vehicle controller
            if self.vehicle_controller:
                self.logger.debug("Cleaning up vehicle controller...")
                try:
                    self.vehicle_controller.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up vehicle controller: {str(e)}")

            # Clean up world and all actors last
            if self.world_manager:
                self.logger.debug("Cleaning up world manager...")
                try:
                    self.world_manager.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up world manager: {str(e)}")

            # Check if we're in web mode
            is_web_mode = getattr(self._config, 'web_mode', False)
            if is_web_mode:
                self.logger.debug("Web mode: Maintaining CARLA connection for next scenario")
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

            self.logger.info("Cleanup completed successfully")

            # Return completion status
            return scenario_completed, scenario_success

        except Exception as e:
            self.logger.error(f"Error in cleanup: {str(e)}")
            # Set cleanup flag even on error
            with self.cleanup_lock:
                self.is_cleanup_complete = True
            return False, False

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
