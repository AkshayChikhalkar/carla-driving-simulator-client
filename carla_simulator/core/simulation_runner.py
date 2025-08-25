"""
Core simulation runner class for managing simulation execution.
"""

import os
import sys
import argparse
import pytest
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from carla_simulator.core.simulation_application import SimulationApplication
# Lazy-import modules that indirectly import pygame to avoid initializing SDL at web startup
# (FastAPI imports this module when the container starts)
from carla_simulator.utils.logging import Logger
from carla_simulator.scenarios.scenario_registry import ScenarioRegistry
from carla_simulator.utils.paths import get_config_path
from carla_simulator.utils.default_config import SIMULATION_CONFIG
from carla_simulator.utils.config import load_config


class SimulationRunner:
    """Class to handle simulation execution and management"""

    def __init__(self, config_file: str = None, session_id: uuid.UUID = None, db_only: bool = False):
        self.config_file = config_file or get_config_path()
        # In DB-only mode, defer config loading until a tenant is known
        self.config = None if db_only else load_config(self.config_file)
        self.logger = Logger()
        self.session_id = session_id or uuid.uuid4()

    def setup_logger(self, debug: bool = False) -> None:
        """Setup logger with debug mode"""
        # Use debug from config if available, otherwise use provided value
        debug_mode = getattr(self.config, "debug", debug)
        self.logger.set_debug_mode(debug_mode)

    def register_scenarios(self) -> None:
        """Register all available scenarios"""
        ScenarioRegistry.register_all()

    def create_application(
        self, scenario: str, session_id=None
    ) -> SimulationApplication:
        """Create a new simulation application instance"""
        # If config not yet loaded (DB-only), attempt to load strictly from DB using tenant context
        if self.config is None:
            from carla_simulator.utils.paths import get_config_path
            from carla_simulator.utils.config import load_config
            self.config_file = get_config_path()
            # load_config now enforces DB-only and will raise if tenant context/config missing
            self.config = load_config(self.config_file)
        return SimulationApplication(
            self.config_file,
            scenario=scenario,
            logger=self.logger,
            session_id=session_id or self.session_id,
        )

    def setup_components(self, app: SimulationApplication) -> Dict[str, Any]:
        """Setup simulation components and return them"""
        # Create and setup components with required arguments
        # Import here to avoid eager pygame import at process start
        from carla_simulator.core.world_manager import WorldManager
        from carla_simulator.core.sensors import SensorManager
        from carla_simulator.control.controller import (
            VehicleController,
            KeyboardController,
            GamepadController,
            AutopilotController,
        )

        world_manager = WorldManager(
            client=app.connection.client,
            config=app.world_config,
            vehicle_config=app._config.vehicle,
            logger=self.logger,
        )

        # Create vehicle first
        vehicle = world_manager.create_vehicle()
        if not vehicle:
            raise RuntimeError("Failed to create vehicle")

        # Create sensor manager with vehicle
        sensor_manager = SensorManager(config=app.sensor_config, vehicle=vehicle, world_manager=world_manager)

        # Create controller based on config type
        controller_type = getattr(app.controller_config, "type", "autopilot")
        is_web_mode = getattr(app._config, "web_mode", False)
        self.logger.debug(f"Creating controller with type: {controller_type}")
        vehicle_controller = VehicleController(
            app.controller_config, headless=is_web_mode
        )

        if controller_type == "keyboard" and not is_web_mode:
            self.logger.debug("Initializing keyboard controller")
            controller = KeyboardController(app.controller_config)
        elif controller_type == "keyboard" and is_web_mode:
            # Use web-based keyboard controller for web mode
            from carla_simulator.control.web_controller import WebKeyboardController
            self.logger.debug("Initializing web keyboard controller")
            controller = WebKeyboardController(app.controller_config, self.logger)
        elif controller_type == "gamepad" and not is_web_mode:
            self.logger.debug("Initializing gamepad controller")
            controller = GamepadController(app.controller_config)
        elif controller_type == "gamepad" and is_web_mode:
            # Use web-based gamepad controller for web mode
            from carla_simulator.control.web_controller import WebGamepadController
            self.logger.debug("Initializing web gamepad controller")
            controller = WebGamepadController(app.controller_config, self.logger)
        elif controller_type == "autopilot":
            self.logger.debug("Initializing autopilot controller")
            controller = AutopilotController(
                vehicle, app.controller_config, app.connection.client, world_manager
            )
            # Ensure autopilot is engaged and traffic manager in sync
            try:
                vehicle.set_autopilot(True, world_manager.get_traffic_manager().get_port())
            except Exception:
                pass
        else:
            raise ValueError(f"Unsupported controller type: {controller_type}")

        self.logger.debug(f"Setting controller strategy: {type(controller).__name__}")
        vehicle_controller.set_strategy(controller)
        self.logger.debug("Setting vehicle for controller")
        vehicle_controller.set_vehicle(vehicle)

        return {
            "world_manager": world_manager,
            "vehicle_controller": vehicle_controller,
            "sensor_manager": sensor_manager,
        }

    def run_single_scenario(self, scenario: str) -> tuple[bool, str]:
        """
        Run a single scenario

        Args:
            scenario: Name of the scenario to run

        Returns:
            tuple[bool, str]: (success status, result message)
        """
        try:
            # Create application instance for current scenario
            app = self.create_application(scenario, session_id=self.session_id)

            # Connect to CARLA server
            if not app.connection.connect():
                return False, "Failed to connect to CARLA server"

            try:
                # Setup components
                components = self.setup_components(app)

                # Setup application
                app.setup(
                    world_manager=components["world_manager"],
                    vehicle_controller=components["vehicle_controller"],
                    sensor_manager=components["sensor_manager"],
                    logger=self.logger,
                )

                # Run simulation
                app.run()

                # Get scenario result from cleanup
                if hasattr(app, "cleanup"):
                    completed, success = app.cleanup()
                    if completed:
                        message = (
                            "Scenario completed successfully"
                            if success
                            else "Scenario failed to meet success criteria"
                        )
                        return success, message
                    else:
                        return False, "Scenario did not complete"
                return True, "Scenario completed"

            finally:
                # Cleanup is handled by app.cleanup()
                pass

        except Exception as e:
            self.logger.error(f"Error running scenario: {str(e)}")
            return False, f"Error: {str(e)}"

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

            success, message = self.run_single_scenario(scenario)
            if not success:
                self.logger.error(f"Scenario {scenario} failed: {message}")

    def run_with_report(self, scenarios: List[str], debug: bool = False) -> None:
        """
        Run scenarios as tests and generate HTML report

        Args:
            scenarios: List of scenarios to run
            debug: Whether to enable debug logging
        """
        # Respect DB-only/report-toggle: only generate when explicitly enabled
        if os.getenv("ENABLE_FILE_REPORTS", "false").lower() != "true":
            # Fallback: just run scenarios without file report
            self.run_scenarios(scenarios)
            return

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_report = reports_dir / f"scenario_report_{timestamp}.html"

        # Create temporary test file
        test_file = Path("tests/temp_test_scenarios.py")
        test_file.parent.mkdir(exist_ok=True)

        # Generate test file content
        test_content = f'''import pytest
from carla_simulator.core.simulation_runner import SimulationRunner

class TestScenario:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.runner = SimulationRunner()
        self.runner.setup_logger(debug={debug})
        self.runner.register_scenarios()
        yield
        if hasattr(self.runner, 'logger'):
            self.runner.logger.close()

    def run_scenario(self, scenario_name):
        """Run a single scenario and return result with message"""
        success, message = self.runner.run_single_scenario(scenario_name)
        return success, message
'''

        # Add test methods for each scenario
        for scenario in scenarios:
            test_content += f'''
    def test_{scenario}(self):
        """Test {scenario} scenario"""
        success, message = self.run_scenario("{scenario}")
        assert success, message
'''

        # Write test file
        test_file.write_text(test_content)

        try:
            # Run pytest with proper argument handling
            import sys

            # Save original sys.argv
            original_argv = sys.argv.copy()

            # Set up pytest arguments
            sys.argv = [
                "pytest",
                str(test_file),
                "-v",
                f"--html={html_report}",
                "--self-contained-html",
            ]

            if debug:
                sys.argv.append("--log-cli-level=DEBUG")

            # Run pytest
            pytest.main()

        finally:
            # Restore original sys.argv
            sys.argv = original_argv
            # Clean up temporary test file
            if test_file.exists():
                test_file.unlink()

    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command line arguments

        Args:
            argv: Optional list of command line arguments

        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(
            description="CARLA Driving Simulator",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        # Get debug setting from config or use default
        debug_default = getattr(self.config, "debug", SIMULATION_CONFIG["debug"])

        # Add arguments with defaults from config
        parser.add_argument(
            "--debug",
            action="store_true",
            default=debug_default,
            help="Enable debug mode for detailed logging",
        )

        parser.add_argument(
            "--report",
            action="store_true",
            help="Run scenarios as tests and generate HTML report",
        )

        # Register scenarios first to get available scenarios
        self.register_scenarios()
        available_scenarios = ScenarioRegistry.get_available_scenarios()

        # Get default scenario from config or use default
        default_scenario = getattr(
            self.config, "scenario", SIMULATION_CONFIG["scenario"]
        )

        parser.add_argument(
            "--scenario",
            type=str,
            default=default_scenario,
            help='Type of scenario to run. Can be "all" or comma-separated list of scenarios: '
            + ", ".join(available_scenarios),
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
            self.logger.info(
                f"Configuration: scenario={args.scenario}, debug={args.debug}"
            )

            # Determine which scenarios to run
            if args.scenario.lower() == "all":
                scenarios_to_run = ScenarioRegistry.get_available_scenarios()
            else:
                scenarios_to_run = [s.strip() for s in args.scenario.split(",")]
                # Validate scenarios
                invalid_scenarios = [
                    s
                    for s in scenarios_to_run
                    if s not in ScenarioRegistry.get_available_scenarios()
                ]
                if invalid_scenarios:
                    raise ValueError(
                        f"Invalid scenario(s): {', '.join(invalid_scenarios)}. Available scenarios: {', '.join(ScenarioRegistry.get_available_scenarios())}"
                    )

            # Run scenarios with or without report
            if args.report:
                self.run_with_report(scenarios_to_run, args.debug)
            else:
                self.run_scenarios(scenarios_to_run)

        except KeyboardInterrupt:
            self.logger.info("Simulation stopped by user")
        except Exception as e:
            self.logger.error("Error running simulation", exc_info=e)
            sys.exit(1)
        finally:
            self.logger.info("Simulation completed")
            self.logger.close()
