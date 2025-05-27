"""
Main entry point for the CARLA Driving Simulator.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, List

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.simulation_application import SimulationApplication
from src.core.world_manager import WorldManager
from src.core.sensors import SensorManager
from src.control.controller import VehicleController, KeyboardController, AutopilotController
from src.utils.logging import Logger
from src.scenarios.scenario_registry import ScenarioRegistry
from src.scenarios.follow_route_scenario import FollowRouteScenario

# Default configuration values
DEFAULT_CONFIG = {
    'scenario': 'follow_route',
    'debug': False
}

# Default config file path
DEFAULT_CONFIG_FILE = os.path.join(project_root, 'config', 'simulation.yaml')

def register_scenarios():
    """Register available scenarios"""
    # Register follow route scenario
    ScenarioRegistry.register(
        'follow_route',
        FollowRouteScenario,
        default_config={
            'num_waypoints': 5,
            'waypoint_tolerance': 5.0
        }
    )
    # Add more scenario registrations here

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments with standardized defaults.
    
    Args:
        argv: Optional list of command line arguments. If None, uses sys.argv[1:]
        
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
    
    parser.add_argument(
        '--scenario',
        type=str,
        default=DEFAULT_CONFIG['scenario'],
        choices=['follow_route', 'all'],
        help='Type of scenario to run'
    )
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    # Validate config file exists
    if not os.path.exists(DEFAULT_CONFIG_FILE):
        parser.error(f"Default configuration file not found: {DEFAULT_CONFIG_FILE}")
    
    return args

def main(argv: Optional[List[str]] = None) -> None:
    """
    Main entry point for the CARLA Driving Simulator.
    
    Args:
        argv: Optional list of command line arguments. If None, uses sys.argv[1:]
    """
    # Parse command line arguments
    args = parse_args(argv)
    
    # Initialize logger
    logger = Logger()
    
    # Set debug mode
    logger.set_debug_mode(args.debug)
    
    try:
        # Log startup configuration
        logger.info(f"Starting CARLA Driving Simulator")
        logger.info(f"Configuration: scenario={args.scenario}, debug={args.debug}")
        
        # Create application instance
        app = SimulationApplication(DEFAULT_CONFIG_FILE, args.scenario)
        
        # Register available scenarios
        register_scenarios()
        
        # Connect to CARLA server first
        if not app.connection.connect():
            raise RuntimeError("Failed to connect to CARLA server")
            
        # Create and setup components with required arguments
        world_manager = WorldManager(
            client=app.connection.client,
            config=app.world_config,
            vehicle_config=app._config.vehicle,
            logger=logger
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
        logger.debug(f"Creating controller with type: {app.controller_config.type}")
        vehicle_controller = VehicleController(app.controller_config)
        
        if app.controller_config.type == 'keyboard':
            logger.debug("Initializing keyboard controller")
            controller = KeyboardController(app.controller_config)
        elif app.controller_config.type == 'autopilot':
            logger.debug("Initializing autopilot controller")
            controller = AutopilotController(vehicle, app.controller_config, app.connection.client)
        else:
            raise ValueError(f"Unsupported controller type: {app.controller_config.type}")
            
        logger.debug(f"Setting controller strategy: {type(controller).__name__}")
        vehicle_controller.set_strategy(controller)
        logger.debug("Setting vehicle for controller")
        vehicle_controller.set_vehicle(vehicle)
        
        # Setup application
        app.setup(
            world_manager=world_manager,
            vehicle_controller=vehicle_controller,
            sensor_manager=sensor_manager,
            logger=logger
        )
        
        # Run simulation
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Simulation stopped by user")
    except Exception as e:
        logger.error("Error running simulation", exc_info=e)
        sys.exit(1)
    finally:
        logger.info("Simulation completed")
        logger.close()  # Make sure to close the logger and its files

if __name__ == '__main__':
    main(sys.argv[1:]) 