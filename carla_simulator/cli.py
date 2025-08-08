#!/usr/bin/env python
"""
Command-line interface for the CARLA Driving Simulator.
"""
import os
import sys
import uuid
from typing import Optional, List

# Set up XDG runtime directory for Linux compatibility
if "XDG_RUNTIME_DIR" not in os.environ:
    os.environ["XDG_RUNTIME_DIR"] = "/tmp/xdg"
    if not os.path.exists("/tmp/xdg"):
        os.makedirs("/tmp/xdg", exist_ok=True)

from carla_simulator.utils.paths import get_config_path
from carla_simulator.core.simulation_runner import SimulationRunner


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for the CARLA Driving Simulator CLI"""
    runner = SimulationRunner(get_config_path(), session_id=uuid.uuid4())
    runner.run(argv)


if __name__ == "__main__":
    main(sys.argv[1:])
