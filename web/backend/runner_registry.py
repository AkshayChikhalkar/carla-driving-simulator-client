from __future__ import annotations

import threading
from typing import Dict, Optional, Tuple

from carla_simulator.core.simulation_runner import SimulationRunner
from carla_simulator.core.scenario_results_manager import ScenarioResultsManager


class TenantRunner:
    def __init__(self, runner: SimulationRunner):
        self.runner = runner
        self.lock = threading.Lock()
        # Per-tenant synchronization primitives (avoid global cross-talk)
        self.setup_event = threading.Event()
        self.simulation_ready = threading.Event()
        if not hasattr(self.runner, "state"):
            # Attach default ThreadSafeState-like dict when used outside main
            self.runner.state = {
                "is_running": False,
                "is_starting": False,
                "is_stopping": False,
                "is_skipping": False,
                "current_scenario": None,
                "scenarios_to_run": [],
                "current_scenario_index": 0,
                "scenario_results": ScenarioResultsManager(),
                "tenant_id": None,
            }


class RunnerRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tenant_to_runner: Dict[int, TenantRunner] = {}

    def get_or_create(self, tenant_id: int) -> TenantRunner:
        with self._lock:
            tr = self._tenant_to_runner.get(tenant_id)
            if tr is None:
                tr = TenantRunner(SimulationRunner(db_only=True))
                self._tenant_to_runner[tenant_id] = tr
            return tr

    def get(self, tenant_id: int) -> Optional[TenantRunner]:
        with self._lock:
            return self._tenant_to_runner.get(tenant_id)

    def remove(self, tenant_id: int) -> None:
        with self._lock:
            self._tenant_to_runner.pop(tenant_id, None)


