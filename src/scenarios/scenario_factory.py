from typing import Dict, Type
from src.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger
from src.scenarios.follow_route_scenario import FollowRouteScenario

class ScenarioFactory:
    """Factory class for creating scenario instances"""
    
    _scenarios: Dict[str, Type[IScenario]] = {
        'follow_route': FollowRouteScenario,
        # Add more scenarios here as they are implemented
    }

    @classmethod
    def create_scenario(cls,
                       scenario_type: str,
                       world_manager: IWorldManager,
                       vehicle_controller: IVehicleController,
                       logger: ILogger,
                       **kwargs) -> IScenario:
        """
        Create a scenario instance based on the scenario type
        
        Args:
            scenario_type: String identifier for the scenario type
            world_manager: World manager instance
            vehicle_controller: Vehicle controller instance
            logger: Logger instance
            **kwargs: Additional arguments for specific scenario types
            
        Returns:
            IScenario: Instance of the requested scenario type
            
        Raises:
            ValueError: If scenario_type is not recognized
        """
        if scenario_type not in cls._scenarios:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
            
        scenario_class = cls._scenarios[scenario_type]
        return scenario_class(
            world_manager=world_manager,
            vehicle_controller=vehicle_controller,
            logger=logger,
            **kwargs
        )

    @classmethod
    def register_scenario(cls, scenario_type: str, scenario_class: Type[IScenario]) -> None:
        """
        Register a new scenario type with the factory
        
        Args:
            scenario_type: String identifier for the scenario type
            scenario_class: Class implementing IScenario interface
        """
        if not issubclass(scenario_class, IScenario):
            raise ValueError(f"Scenario class must implement IScenario interface")
        cls._scenarios[scenario_type] = scenario_class 