import pytest
import logging
from pathlib import Path
from datetime import datetime
from src.core.simulation_runner import SimulationRunner
from src.scenarios.scenario_registry import ScenarioRegistry
from src.utils.logging import Logger

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = Logger()


class TestScenario:
    """Base class for scenario tests"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.runner = SimulationRunner()
        self.runner.setup_logger(debug=True)
        self.runner.register_scenarios()
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
for scenario in ScenarioRegistry.get_available_scenarios():
    test_method = create_scenario_test(scenario)
    test_method.__name__ = f"test_{scenario}"
    setattr(TestScenario, test_method.__name__, test_method)
