"""
Utility functions for path management.
"""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_config_path(config_file: str = "simulation.yaml") -> str:
    """Get the absolute path to a config file."""
    return str(get_project_root() / "config" / config_file)


def get_log_path(log_file: str) -> str:
    """Get the absolute path to a log file."""
    return str(get_project_root() / "logs" / log_file)
