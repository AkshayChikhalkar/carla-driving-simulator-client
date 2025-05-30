from typing import Dict, Type, Optional, Any
from src.core.interfaces import IScenario, IWorldManager, IVehicleController, ILogger
from src.scenarios.follow_route_scenario import FollowRouteScenario
from src.scenarios.avoid_obstacle_scenario import AvoidObstacleScenario
from src.scenarios.emergency_brake_scenario import EmergencyBrakeScenario
from src.scenarios.vehicle_cutting_scenario import VehicleCuttingScenario

class ScenarioRegistry:
    """Registry for scenario types"""
    
    # Define all available scenarios in one place
    AVAILABLE_SCENARIOS = {
        'follow_route': {
            'class': FollowRouteScenario,
            'default_config': {
                'num_waypoints': 5,
                'waypoint_tolerance': 5.0,
                'min_distance': 50.0,
                'max_distance': 100.0
            }
        },
        'avoid_obstacle': {
            'class': AvoidObstacleScenario,
            'default_config': {
                'target_distance': 100.0,
                'obstacle_spacing': 25.0,
                'completion_distance': 110.0,
                'collision_threshold': 1.0,
                'max_simulation_time': 120.0,
                'waypoint_tolerance': 5.0,
                'min_waypoint_distance': 30.0,
                'max_waypoint_distance': 50.0,
                'num_waypoints': 3
            }
        },
        'emergency_brake': {
            'class': EmergencyBrakeScenario,
            'default_config': {
                'trigger_distance': 50.0,
                'target_speed': 40.0,
                'obstacle_type': "static.prop.streetbarrier"
            }
        },
        'vehicle_cutting': {
            'class': VehicleCuttingScenario,
            'default_config': {
                'target_distance': 100.0,
                'cutting_distance': 30.0,
                'completion_distance': 110.0,
                'collision_threshold': 1.0,
                'max_simulation_time': 120.0,
                'waypoint_tolerance': 5.0,
                'min_waypoint_distance': 30.0,
                'max_waypoint_distance': 50.0,
                'num_waypoints': 3,
                'cutting_vehicle_model': "vehicle.fuso.mitsubishi",
                'normal_speed': 30.0,
                'cutting_speed': 40.0,
                'cutting_trigger_distance': 20.0
            }
        }
    }
    
    _scenarios: Dict[str, Type[IScenario]] = {}
    _scenario_configs: Dict[str, Dict] = {}

    @classmethod
    def register_all(cls) -> None:
        """Register all available scenarios"""
        for scenario_type, scenario_info in cls.AVAILABLE_SCENARIOS.items():
            cls.register(
                scenario_type=scenario_type,
                scenario_class=scenario_info['class'],
                default_config=scenario_info['default_config']
            )

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
            config=default_config  # Pass config as a single dictionary
        )

    @classmethod
    def get_available_scenarios(cls) -> list[str]:
        """Get list of registered scenario types"""
        return list(cls._scenarios.keys())

    @classmethod
    def get_scenario_config(cls, scenario_type: str) -> Optional[Dict]:
        """Get default configuration for a scenario type"""
        return cls._scenario_configs.get(scenario_type) 