class ScenarioResultsManager:
    def __init__(self):
        self._scenario_results = {}

    def set_result(self, scenario_name, result, status, duration):
        self._scenario_results[scenario_name] = {
            "name": scenario_name,
            "result": result,
            "status": status,
            "duration": duration,
        }

    def all_results(self):
        return list(self._scenario_results.values())

    def clear_results(self):
        self._scenario_results.clear()

    def get_result(self, scenario_name):
        return self._scenario_results.get(scenario_name)
