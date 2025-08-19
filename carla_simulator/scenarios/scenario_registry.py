"""
Registry for managing available scenarios and their configurations.
"""

from typing import Dict, Type, List, Any, Optional
from carla_simulator.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger
from carla_simulator.scenarios.base_scenario import BaseScenario
from carla_simulator.scenarios.follow_route_scenario import FollowRouteScenario
from carla_simulator.scenarios.avoid_obstacle_scenario import AvoidObstacleScenario
from carla_simulator.scenarios.emergency_brake_scenario import EmergencyBrakeScenario
from carla_simulator.scenarios.vehicle_cutting_scenario import VehicleCuttingScenario
from carla_simulator.utils.config import Config, load_config
from carla_simulator.utils.paths import get_config_path


class ScenarioRegistry:
    """Registry for managing available scenarios and their configurations."""

    _scenarios: Dict[str, Type[BaseScenario]] = {}
    _config: Config = None

    @classmethod
    def register_scenario(
        cls, scenario_type: str, scenario_class: Type[BaseScenario]
    ) -> None:
        """
        Register a scenario type with its class.

        Args:
            scenario_type: Type identifier for the scenario
            scenario_class: Class implementing the scenario
        """
        if not issubclass(scenario_class, IScenario):
            raise ValueError(f"Scenario class must implement IScenario interface")
        cls._scenarios[scenario_type] = scenario_class

    @classmethod
    def get_scenario_class(cls, scenario_type: str) -> Type[BaseScenario]:
        """
        Get the class for a registered scenario type.

        Args:
            scenario_type: Type identifier for the scenario

        Returns:
            Type[BaseScenario]: Class implementing the scenario

        Raises:
            ValueError: If scenario type is not registered
        """
        if scenario_type not in cls._scenarios:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        return cls._scenarios[scenario_type]

    @classmethod
    def get_available_scenarios(cls) -> List[str]:
        """
        Get list of available scenario types.

        Returns:
            List[str]: List of registered scenario types
        """
        return list(cls._scenarios.keys())

    @classmethod
    def get_scenario_config(cls, scenario_type: str) -> Dict[str, Any]:
        """
        Get configuration for a specific scenario type.

        Args:
            scenario_type: Type identifier for the scenario

        Returns:
            Dict[str, Any]: Configuration for the scenario

        Raises:
            ValueError: If scenario type is not registered or configuration not found
        """
        if not cls._config:
            # Load config if not already loaded
            cls._config = load_config(get_config_path())

        # Get the scenario config from the Config object
        scenario_config = getattr(cls._config.scenarios, scenario_type, None)
        if not scenario_config:
            raise ValueError(
                f"No configuration found for scenario type: {scenario_type}"
            )

        # Convert the config object to a dictionary
        return {
            k: v for k, v in scenario_config.__dict__.items() if not k.startswith("_")
        }

    @classmethod
    def create_scenario(
        cls,
        scenario_type: str,
        world_manager: IWorldManager,
        vehicle_controller: IVehicleController,
        logger: ILogger,
        config: Optional[Dict[str, Any]] = None,
    ) -> IScenario:
        """
        Create a new scenario instance.

        Args:
            scenario_type: Type identifier for the scenario
            world_manager: World manager instance
            vehicle_controller: Vehicle controller instance
            logger: Logger instance
            config: Optional configuration overrides

        Returns:
            IScenario: New scenario instance

        Raises:
            ValueError: If scenario type is not registered
        """
        scenario_class = cls.get_scenario_class(scenario_type)
        scenario_config = cls.get_scenario_config(scenario_type)

        # Merge with provided config if any
        if config:
            scenario_config.update(config)

        return scenario_class(
            world_manager=world_manager,
            vehicle_controller=vehicle_controller,
            logger=logger,
            config=scenario_config,
        )

    @classmethod
    def register_all(cls) -> None:
        """Register all available scenario types."""
        cls.register_scenario("follow_route", FollowRouteScenario)
        cls.register_scenario("avoid_obstacle", AvoidObstacleScenario)
        cls.register_scenario("emergency_brake", EmergencyBrakeScenario)
        cls.register_scenario("vehicle_cutting", VehicleCuttingScenario)
