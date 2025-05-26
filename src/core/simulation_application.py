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
from src.utils.settings import DEBUG_MODE  # Import from settings module

class SimulationApplication:
    """Main application class that coordinates all simulation components"""
    
    def __init__(self, config_path: str, scenario: str = None):
        # Initialize configuration
        self._config = SimulationConfig(config_path, scenario)
        
        # Initialize connection manager with server config
        self.connection = ConnectionManager(self._config.server_config)
        
        # Initialize state and metrics
        self.state = SimulationState()
        self.metrics = None  # Will be initialized after logger
        
        # Component references (will be set during setup)
        self.world_manager: Optional[IWorldManager] = None
        self.vehicle_controller: Optional[IVehicleController] = None
        self.sensor_manager: Optional[ISensorManager] = None
        self.logger: Optional[ILogger] = None
        self.current_scenario: Optional[IScenario] = None
        self.display_manager: Optional[DisplayManager] = None
        # Do not connect here; connect only in setup()

    def setup(self,
             world_manager: IWorldManager,
             vehicle_controller: IVehicleController,
             sensor_manager: ISensorManager,
             logger: ILogger) -> None:
        """Setup the simulation application"""
        if DEBUG_MODE:
            print("[SimulationApplication] Setting up simulation components...")
        
        self.world_manager = world_manager
        self.vehicle_controller = vehicle_controller
        self.sensor_manager = sensor_manager
        self.logger = logger
        
        if DEBUG_MODE:
            print("[SimulationApplication] Basic components initialized")
        
        # Initialize metrics after logger is available
        self.metrics = SimulationMetrics(logger)
        if DEBUG_MODE:
            print("[SimulationApplication] Metrics initialized")
        
        # Initialize display manager
        if DEBUG_MODE:
            print("[SimulationApplication] Initializing display manager...")
        self.display_manager = DisplayManager(self._config.display_config)
        if DEBUG_MODE:
            print("[SimulationApplication] Display manager initialized")
        
        # Attach camera view to sensor manager
        if DEBUG_MODE:
            print("[SimulationApplication] Setting up camera...")
        camera_sensor = self.sensor_manager.get_sensor('camera')
        if camera_sensor:
            if DEBUG_MODE:
                print("[SimulationApplication] Camera sensor found, attaching view...")
            camera_sensor.attach(self.display_manager.camera_view)
            if DEBUG_MODE:
                print("[SimulationApplication] Camera view attached to sensor manager")
        else:
            if DEBUG_MODE:
                print("[SimulationApplication] ERROR: Camera sensor not found!")
        
        # Verify connection is valid
        if DEBUG_MODE:
            print("[SimulationApplication] Verifying CARLA connection...")
        if not self.connection.client:
            raise RuntimeError("CARLA client is not initialized")
            
        try:
            # Test connection by getting world
            if DEBUG_MODE:
                print("[SimulationApplication] Attempting to get CARLA world...")
            world = self.connection.client.get_world()
            if not world:
                raise RuntimeError("Failed to get CARLA world")
            if DEBUG_MODE:
                print("[SimulationApplication] Successfully connected to CARLA world")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[SimulationApplication] ERROR: Failed to connect to CARLA server: {str(e)}")
            raise RuntimeError(f"Failed to connect to CARLA server: {str(e)}")
            
        # Create initial scenario
        if DEBUG_MODE:
            print("[SimulationApplication] Setting up initial scenario...")
        self._setup_scenario(self._config.get('scenario', 'follow_route'))
        if DEBUG_MODE:
            print("[SimulationApplication] Setup completed successfully")

    def _setup_scenario(self, scenario_type: str, scenario_config: Optional[Dict] = None) -> None:
        """Setup a new scenario"""
        if not all([self.world_manager, self.vehicle_controller, self.logger]):
            raise RuntimeError("Application not properly initialized")
            
        # Get scenario configuration from main config
        if scenario_config is None:
            scenario_config = self._config.scenario_config.__dict__.get(scenario_type, {})
            # Convert dataclass to dictionary if needed
            if hasattr(scenario_config, '__dict__'):
                scenario_config = scenario_config.__dict__
            
        # Create scenario using registry
        self.current_scenario = ScenarioRegistry.create_scenario(
            scenario_type=scenario_type,
            world_manager=self.world_manager,
            vehicle_controller=self.vehicle_controller,
            logger=self.logger,
            config=scenario_config
        )
        
        # Setup the scenario
        self.current_scenario.setup()
        self.logger.log_info(f"Started scenario: {scenario_type}")

    def run(self) -> None:
        """Run the simulation loop"""
        if not self.current_scenario:
            raise RuntimeError("No scenario set")
            
        self.state.start()
        self.logger.log_info("Starting simulation loop")
        
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
                    if DEBUG_MODE:
                        print(f"Exception in scenario update: {e}")
                    
                try:
                    # Apply vehicle control
                    control = self.vehicle_controller.get_control(vehicle_state)
                    vehicle.apply_control(control)
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Exception in control/apply: {e}")
                    
                try:
                    # Update metrics
                    self.metrics.update(vehicle_state)
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Exception in metrics update: {e}")
                    
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
                            scenario_name=self.current_scenario.__class__.__name__
                        )
                        
                        # Get target position from scenario if available
                        target_pos = getattr(self.current_scenario, 'target_position', None)
                        if target_pos is None:
                            target_pos = carla.Location()
                            
                        # Render display
                        if not self.display_manager.render(display_state, target_pos):
                            break
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Exception in display rendering: {e}")
                    
                try:
                    # Log metrics periodically
                    if self.metrics.metrics['frame_count'] % 30 == 0:
                        self.metrics.log_metrics()
                        self.logger.log_vehicle_state(vehicle_state)
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Exception in logging: {e}")
                    
                # Tick the CARLA world (required for synchronous mode)
                world.tick()
                    
        except Exception as e:
            if DEBUG_MODE:
                print(f"[SimulationApplication] Error in simulation loop: {str(e)}")
            raise
        finally:
            self.cleanup()

    def pause(self) -> None:
        """Pause the simulation"""
        self.state.pause()
        self.logger.log_info("Simulation paused")

    def resume(self) -> None:
        """Resume the simulation"""
        self.state.resume()
        self.logger.log_info("Simulation resumed")

    def stop(self) -> None:
        """Stop the simulation"""
        self.state.stop()
        if self.logger:
            self.logger.log_info("Simulation stopped")

    def cleanup(self) -> None:
        """Clean up simulation resources"""
        try:
            self.stop()
            if self.current_scenario:
                self.current_scenario.cleanup()
            if self.sensor_manager:
                self.sensor_manager.cleanup()
            if self.display_manager:
                self.display_manager.cleanup()
            self.connection.disconnect()
            if self.logger:
                self.logger.log_info("Simulation cleanup completed")
        except Exception as e:
            if DEBUG_MODE:
                print(f"[SimulationApplication] Error during cleanup: {str(e)}")
            raise 

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