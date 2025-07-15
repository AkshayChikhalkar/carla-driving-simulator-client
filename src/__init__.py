"""
CARLA Driving Simulator package.
"""

import os
import re
import subprocess


def get_version():
    """
    Get the current version of the package.
    
    Priority order:
    1. PACKAGE_VERSION environment variable (set by CI/CD pipeline)
    2. Git tag
    3. Default version
    
    Returns:
        str: The version string
    """
    # First try to get version from environment variable (set by CI/CD pipeline)
    version = os.environ.get("PACKAGE_VERSION")
    if version:
        return version

    # If not in environment, try git tag
    try:
        version = (
            subprocess.check_output(["git", "describe", "--tags", "--match", "v[0-9]*", "--abbrev=0"])
            .decode()
            .strip()
        )
        # Remove 'v' prefix
        return version[1:] if version.startswith('v') else version
    except:
        return "1.0.0"  # Default version if nothing else is available


__version__ = get_version()
__all__ = ["__version__"]
