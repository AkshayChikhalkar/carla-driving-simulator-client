"""
Main entry point for the CARLA Driving Simulator.
"""

import sys
from typing import Optional, List
import uuid
from src.utils.paths import get_config_path
from src.core.simulation_runner import SimulationRunner


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for the application"""
    runner = SimulationRunner(get_config_path(), session_id=uuid.uuid4())
    runner.run(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
