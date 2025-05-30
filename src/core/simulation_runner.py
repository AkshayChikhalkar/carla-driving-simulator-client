"""
Core simulation runner class for managing simulation execution.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.core.simulation_application import SimulationApplication
from src.core.world_manager import WorldManager
from src.core.sensors import SensorManager
from src.control.controller import VehicleController, KeyboardController, AutopilotController
from src.utils.logging import Logger
from src.scenarios.scenario_registry import ScenarioRegistry

# Default configuration values
DEFAULT_CONFIG = {
    'scenario': 'follow_route',
    'debug': False
}

# Default config file path
DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'simulation.yaml')

class SimulationRunner:
    """Class to handle simulation execution and management"""
    
    def __init__(self, config_file: str = DEFAULT_CONFIG_FILE):
        self.config_file = config_file
        self.logger = Logger()
        
    def setup_logger(self, debug: bool = False) -> None:
        """Setup logger with debug mode"""
        self.logger.set_debug_mode(debug)
        
    def register_scenarios(self) -> None:
        """Register all available scenarios"""
        ScenarioRegistry.register_all()
        
    def create_application(self, scenario: str) -> SimulationApplication:
        """Create a new simulation application instance"""
        return SimulationApplication(self.config_file, scenario)
        
    def setup_components(self, app: SimulationApplication) -> Dict[str, Any]:
        """Setup simulation components and return them"""
        # Create and setup components with required arguments
        world_manager = WorldManager(
            client=app.connection.client,
            config=app.world_config,
            vehicle_config=app._config.vehicle
        )
        
        # Create vehicle first
        vehicle = world_manager.create_vehicle()
        if not vehicle:
            raise RuntimeError("Failed to create vehicle")
            
        # Create sensor manager with vehicle
        sensor_manager = SensorManager(
            config=app.sensor_config,
            vehicle=vehicle
        )
        
        # Create controller based on config type
        self.logger.debug(f"Creating controller with type: {app.controller_config.type}")
        vehicle_controller = VehicleController(app.controller_config)
        
        if app.controller_config.type == 'keyboard':
            self.logger.debug("Initializing keyboard controller")
            controller = KeyboardController(app.controller_config)
        elif app.controller_config.type == 'autopilot':
            self.logger.debug("Initializing autopilot controller")
            controller = AutopilotController(vehicle, app.controller_config, app.connection.client)
        else:
            raise ValueError(f"Unsupported controller type: {app.controller_config.type}")
            
        self.logger.debug(f"Setting controller strategy: {type(controller).__name__}")
        vehicle_controller.set_strategy(controller)
        self.logger.debug("Setting vehicle for controller")
        vehicle_controller.set_vehicle(vehicle)
        
        return {
            'world_manager': world_manager,
            'vehicle_controller': vehicle_controller,
            'sensor_manager': sensor_manager
        }
        
    def run_single_scenario(self, scenario: str) -> bool:
        """
        Run a single scenario
        
        Args:
            scenario: Name of the scenario to run
            
        Returns:
            bool: True if scenario completed successfully, False otherwise
        """
        try:
            # Create application instance for current scenario
            app = self.create_application(scenario)
            
            # Connect to CARLA server
            if not app.connection.connect():
                raise RuntimeError("Failed to connect to CARLA server")
            
            try:
                # Setup components
                components = self.setup_components(app)
                
                # Setup application
                app.setup(
                    world_manager=components['world_manager'],
                    vehicle_controller=components['vehicle_controller'],
                    sensor_manager=components['sensor_manager'],
                    logger=self.logger
                )
                
                # Run simulation
                app.run()
                return True
                
            finally:
                # Clean up after scenario
                if hasattr(app, 'cleanup'):
                    app.cleanup()
                # Disconnect from CARLA server
                if hasattr(app, 'connection') and app.connection:
                    app.connection.disconnect()
                    
        except Exception as e:
            self.logger.error(f"Error running scenario {scenario}: {str(e)}")
            return False
            
    def run_scenarios(self, scenarios: List[str]) -> None:
        """
        Run multiple scenarios in sequence
        
        Args:
            scenarios: List of scenario names to run
        """
        total_scenarios = len(scenarios)
        for index, scenario in enumerate(scenarios, 1):
            self.logger.info(f"================================")
            self.logger.info(f"Running scenario {index}/{total_scenarios}: {scenario}")
            self.logger.info(f"================================")
            
            success = self.run_single_scenario(scenario)
            if not success:
                self.logger.error(f"Scenario {scenario} failed")
                
    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command line arguments
        
        Args:
            argv: Optional list of command line arguments
            
        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description='CARLA Driving Simulator',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # Add arguments with defaults from DEFAULT_CONFIG
        parser.add_argument(
            '--debug',
            action='store_true',
            default=DEFAULT_CONFIG['debug'],
            help='Enable debug mode for detailed logging'
        )
        
        # Register scenarios first to get available scenarios
        self.register_scenarios()
        available_scenarios = ScenarioRegistry.get_available_scenarios()
        
        parser.add_argument(
            '--scenario',
            type=str,
            default=DEFAULT_CONFIG['scenario'],
            help='Type of scenario to run. Can be "all" or comma-separated list of scenarios: ' + ', '.join(available_scenarios)
        )
        
        # Parse arguments
        args = parser.parse_args(argv)
        
        # Validate config file exists
        if not os.path.exists(self.config_file):
            parser.error(f"Default configuration file not found: {self.config_file}")
        
        return args
        
    def run(self, argv: Optional[List[str]] = None) -> None:
        """
        Main entry point for running simulations
        
        Args:
            argv: Optional list of command line arguments
        """
        try:
            # Parse command line arguments
            args = self.parse_args(argv)
            
            # Setup logger
            self.setup_logger(args.debug)
            
            # Log startup configuration
            self.logger.info(f"Starting CARLA Driving Simulator")
            self.logger.info(f"Configuration: scenario={args.scenario}, debug={args.debug}")
            
            # Determine which scenarios to run
            if args.scenario.lower() == 'all':
                scenarios_to_run = ScenarioRegistry.get_available_scenarios()
            else:
                scenarios_to_run = [s.strip() for s in args.scenario.split(',')]
                # Validate scenarios
                invalid_scenarios = [s for s in scenarios_to_run if s not in ScenarioRegistry.get_available_scenarios()]
                if invalid_scenarios:
                    raise ValueError(f"Invalid scenario(s): {', '.join(invalid_scenarios)}. Available scenarios: {', '.join(ScenarioRegistry.get_available_scenarios())}")
            
            # Run scenarios
            self.run_scenarios(scenarios_to_run)
            
        except KeyboardInterrupt:
            self.logger.info("Simulation stopped by user")
        except Exception as e:
            self.logger.error("Error running simulation", exc_info=e)
            sys.exit(1)
        finally:
            self.logger.info("Simulation completed")
            self.logger.close() 