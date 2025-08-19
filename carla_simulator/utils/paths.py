"""
Utility functions for path management.
"""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_config_path(config_file: str = "simulation.yaml") -> str:
    """Get the absolute path to a config file.

    If the default file "simulation.yaml" is requested and a JSON configuration
    named "simulation.json" exists in the same directory, prefer the JSON file.
    This enables a seamless migration path to JSON while keeping YAML backward
    compatibility.
    """
    base_dir = get_project_root() / "config"
    # Prefer JSON if default requested and JSON exists
    if config_file == "simulation.yaml":
        json_candidate = base_dir / "simulation.json"
        if json_candidate.exists():
            return str(json_candidate)
    return str(base_dir / config_file)


def get_log_path(log_file: str) -> str:
    """Get the absolute path to a log file."""
    return str(get_project_root() / "logs" / log_file)
