"""
Default configuration values for the simulation.
These values are used as fallbacks if not found in the YAML configuration.
"""

from typing import Dict, Any

# Default simulation configuration (fallback values)
SIMULATION_CONFIG: Dict[str, Any] = {
    "scenario": "follow_route",  # Default scenario if none specified
    "debug": False,  # Default debug mode
    "web_mode": False,  # Default web mode state
}

# Default logging configuration (fallback values)
LOGGING_CONFIG: Dict[str, Any] = {
    "log_level": "INFO",  # Default log level if not in YAML
    "enabled": True,  # Default logging enabled state
    "directory": "logs",  # Default log directory
}

# Default display configuration (fallback values)
DISPLAY_CONFIG: Dict[str, Any] = {
    "width": 1280,  # Default display width
    "height": 720,  # Default display height
    "fps": 60,  # Default FPS
    "hud_enabled": True,  # Default HUD state
    "minimap_enabled": True,  # Default minimap state
}
