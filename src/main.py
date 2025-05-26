"""
Main entry point for the CARLA Driving Simulator.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.simulation_application import SimulationApplication
from src.core.world_manager import WorldManager
from src.core.sensors import SensorManager
from src.control.controller import VehicleController, KeyboardController, AutopilotController
from src.utils.logging import SimulationLogger
from src.utils.config import LoggingConfig
from src.scenarios.scenario_registry import ScenarioRegistry
from src.scenarios.follow_route_scenario import FollowRouteScenario
from src.utils.settings import DEBUG_MODE  # Import from settings module

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

def main(argv=None):
    """Main entry point"""
    parser = argparse.ArgumentParser(description='CARLA Driving Simulator')
    parser.add_argument('--config', type=str, default='config/simulation.yaml',
                      help='Path to configuration file')
    parser.add_argument('--scenario', type=str, default='follow_route',
                      choices=['follow_route', 'all'],
                      help='Type of scenario to run (use "all" to run all scenarios sequentially)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    args = parser.parse_args(argv)

    # Set global debug state
    from src.utils.settings import DEBUG_MODE
    DEBUG_MODE = args.debug

    try:
        # Create application instance
        app = SimulationApplication(args.config, args.scenario)
        
        # Register available scenarios
        register_scenarios()
        
        # Initialize logger with proper config
        logger = SimulationLogger(app.logging_config)
        
        # Connect to CARLA server first
        if not app.connection.connect():
            raise RuntimeError("Failed to connect to CARLA server")
            
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
        if DEBUG_MODE:
            print(f"[Main] Creating controller with type: {app.controller_config.type}")
        vehicle_controller = VehicleController(app.controller_config)
        
        if app.controller_config.type == 'keyboard':
            if DEBUG_MODE:
                print("[Main] Initializing keyboard controller")
            controller = KeyboardController(app.controller_config, logger)
        elif app.controller_config.type == 'autopilot':
            if DEBUG_MODE:
                print("[Main] Initializing autopilot controller")
            controller = AutopilotController(vehicle, app.controller_config, app.connection.client)
        else:
            raise ValueError(f"Unsupported controller type: {app.controller_config.type}")
            
        if DEBUG_MODE:
            print(f"[Main] Setting controller strategy: {type(controller).__name__}")
        vehicle_controller.set_strategy(controller)
        if DEBUG_MODE:
            print("[Main] Setting vehicle for controller")
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
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        if 'app' in locals():
            app.cleanup()

if __name__ == '__main__':
    main() 