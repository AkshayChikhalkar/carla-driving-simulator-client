from typing import Dict, Type, Optional
from src.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger

class ScenarioRegistry:
    """Registry for scenario types"""
    
    _scenarios: Dict[str, Type[IScenario]] = {}
    _scenario_configs: Dict[str, Dict] = {}

    @classmethod
    def register(cls, 
                scenario_type: str, 
                scenario_class: Type[IScenario],
                default_config: Optional[Dict] = None) -> None:
        """
        Register a new scenario type
        
        Args:
            scenario_type: String identifier for the scenario
            scenario_class: Class implementing IScenario interface
            default_config: Optional default configuration for the scenario
        """
        if not issubclass(scenario_class, IScenario):
            raise ValueError(f"Scenario class must implement IScenario interface")
            
        cls._scenarios[scenario_type] = scenario_class
        if default_config:
            cls._scenario_configs[scenario_type] = default_config

    @classmethod
    def create_scenario(cls,
                       scenario_type: str,
                       world_manager: IWorldManager,
                       vehicle_controller: IVehicleController,
                       logger: ILogger,
                       config: Optional[Dict] = None) -> IScenario:
        """
        Create a scenario instance
        
        Args:
            scenario_type: String identifier for the scenario
            world_manager: World manager instance
            vehicle_controller: Vehicle controller instance
            logger: Logger instance
            config: Optional configuration override
            
        Returns:
            IScenario: Instance of the requested scenario type
            
        Raises:
            ValueError: If scenario_type is not registered
        """
        if scenario_type not in cls._scenarios:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
            
        # Merge default config with provided config
        scenario_config = cls._scenario_configs.get(scenario_type, {}).copy()
        if config:
            scenario_config.update(config)
            
        scenario_class = cls._scenarios[scenario_type]
        return scenario_class(
            world_manager=world_manager,
            vehicle_controller=vehicle_controller,
            logger=logger,
            **scenario_config
        )

    @classmethod
    def get_available_scenarios(cls) -> list[str]:
        """Get list of registered scenario types"""
        return list(cls._scenarios.keys())

    @classmethod
    def get_scenario_config(cls, scenario_type: str) -> Optional[Dict]:
        """Get default configuration for a scenario type"""
        return cls._scenario_configs.get(scenario_type) 