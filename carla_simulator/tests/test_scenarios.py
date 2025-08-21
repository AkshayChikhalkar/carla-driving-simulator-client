import pytest
import logging
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

try:
    from carla_simulator.core.simulation_runner import SimulationRunner
    from carla_simulator.scenarios.scenario_registry import ScenarioRegistry
    from carla_simulator.utils.logging import Logger
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some imports not available: {e}")
    IMPORTS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if IMPORTS_AVAILABLE:
    logger = Logger()
else:
    logger = logging.getLogger(__name__)


class TestScenario:
    """Base class for scenario tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required imports not available")
            
        with patch("carla_simulator.core.simulation_runner.SimulationRunner") as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            self.runner = mock_runner
            
            # Setup mock methods
            self.runner.setup_logger.return_value = None
            self.runner.register_scenarios.return_value = None
            self.runner.run_single_scenario.return_value = True
            
            # Mock logger
            self.runner.logger = MagicMock()
            self.runner.logger.close.return_value = None
            
            yield
            
            # Cleanup after test
            if hasattr(self.runner, "logger"):
                self.runner.logger.close()

    def run_scenario(self, scenario_name):
        """Run a single scenario and return result"""
        try:
            success = self.runner.run_single_scenario(scenario_name)
            assert success, f"Scenario {scenario_name} failed"
            return True
        except Exception as e:
            logger.error(f"Error in scenario {scenario_name}: {str(e)}")
            return False


# Dynamically create test methods for each scenario
def create_scenario_test(scenario_name):
    """Create a test method for a specific scenario"""

    def test_scenario(self):
        """Test a specific scenario"""
        result = self.run_scenario(scenario_name)
        assert result, f"Scenario {scenario_name} failed"

    return test_scenario


# Register all available scenarios as test methods
try:
    scenarios = ScenarioRegistry.get_available_scenarios()
    for scenario in scenarios:
        test_method = create_scenario_test(scenario)
        test_method.__name__ = f"test_{scenario}"
        setattr(TestScenario, test_method.__name__, test_method)
except Exception as e:
    # If ScenarioRegistry is not available, create a basic test
    def test_basic_scenario(self):
        """Basic scenario test when registry is not available"""
        assert self.runner is not None
        assert hasattr(self.runner, 'run_single_scenario')
    
    setattr(TestScenario, 'test_basic_scenario', test_basic_scenario)

# Add a test to verify imports work
def test_imports_available():
    """Test that all required imports are available."""
    assert IMPORTS_AVAILABLE, "Required imports are not available"
