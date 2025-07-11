"""
Setup script for the CARLA Driving Simulator Client.
"""

from setuptools import setup, find_packages
import os
import re
import subprocess


def get_version():
    """
    Get the current version of the package.
    
    Priority order:
    1. PACKAGE_VERSION environment variable (set by CI/CD)
    2. Git tag
    3. Default version
    
    Returns:
        str: The version string
    """
    # First try to get version from environment variable (set by CI/CD)
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


# Read README.md for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


# Get version
version = get_version()


# Read requirements from requirements.txt
def read_requirements(filename):
    with open(filename) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Base requirements
install_requires = [
    "pygame>=2.0.0",
    "numpy>=1.19.0",
    "matplotlib>=3.3.0",
    "tabulate>=0.8.7",
    "pyyaml>=5.4.0",
    "psycopg2-binary>=2.9.9",
    "SQLAlchemy>=2.0.0",
    "alembic>=1.13.0",
]

# Development requirements
extras_require = {
    "dev": [
        "pytest>=6.0.0",
        "pytest-cov>=2.10.0",
        "pytest-html>=3.2.0",
        "black>=21.5b2",
        "flake8>=3.9.0",
        "mypy>=0.812",
    ],
    "docs": [
        "sphinx>=4.0.0",
        "sphinx-rtd-theme>=0.5.0",
        "myst-parser>=0.15.0",
    ]
}

setup(
    name="carla-driving-simulator-client",
    version=version,
    description="A comprehensive CARLA client for autonomous driving simulation, featuring scenario-based testing, real-time visualization, and customizable vehicle control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Akshay Chikhalkar",
    author_email="akshaychikhalkar15@gmail.com",
    url="https://github.com/akshaychikhalkar/carla-driving-simulator-client",
    project_urls={
        "Bug Tracker": "https://github.com/akshaychikhalkar/carla-driving-simulator-client/issues",
        "Documentation": "https://carla-driving-simulator-client.readthedocs.io/",
        "Source Code": "https://github.com/akshaychikhalkar/carla-driving-simulator-client",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires="==3.11.*",
    entry_points={
        "console_scripts": [
            "carla-simulator-client=src.main:main",
            "csc=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Testing",
        "Topic :: Games/Entertainment :: Simulation",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Environment :: Web Environment",
    ],
    keywords="carla, autonomous-driving, simulation, pygame, visualization, scenario-testing, vehicle-control, driving-simulator, computer-vision, machine-learning, robotics, testing-framework, web-api, real-time-simulation",
    zip_safe=False,
)
