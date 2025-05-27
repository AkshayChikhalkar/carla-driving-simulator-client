from typing import Dict, Type, Optional, Any
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
    def create_scenario(cls, scenario_type: str, world_manager: IWorldManager, 
                       vehicle_controller: IVehicleController, logger: ILogger, config: Dict[str, Any] = None) -> IScenario:
        """Create a new scenario instance"""
        if scenario_type not in cls._scenarios:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
            
        # Get default config for this scenario type
        default_config = cls._scenario_configs.get(scenario_type, {})
        
        # Merge with provided config if any
        if config:
            default_config.update(config)
            
        scenario_class = cls._scenarios[scenario_type]
        return scenario_class(
            world_manager=world_manager,
            vehicle_controller=vehicle_controller,
            logger=logger,
            **default_config  # Unpack config as keyword arguments
        )

    @classmethod
    def get_available_scenarios(cls) -> list[str]:
        """Get list of registered scenario types"""
        return list(cls._scenarios.keys())

    @classmethod
    def get_scenario_config(cls, scenario_type: str) -> Optional[Dict]:
        """Get default configuration for a scenario type"""
        return cls._scenario_configs.get(scenario_type) 