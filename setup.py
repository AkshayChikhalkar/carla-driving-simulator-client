"""
Setup script for the CARLA Driving Simulator Client.
"""

from setuptools import setup, find_packages
import os
import re

# Read README.md for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read version from git tag or version file
def get_version():
    # First try to get version from git tag
    try:
        import subprocess
        version = subprocess.check_output(['git', 'describe', '--tags', '--always']).decode().strip()
        # Remove any leading 'v' and any additional git info after the version number
        version = re.sub(r'^v', '', version)
        version = re.sub(r'-.*$', '', version)
        return version
    except:
        # If git tag is not available, try to read from version file
        try:
            with open('VERSION', 'r') as f:
                return f.read().strip()
        except:
            return "1.0.0"  # Default version if neither git nor version file is available

# Write version to VERSION file if it doesn't exist
version = get_version()
if not os.path.exists('VERSION'):
    with open('VERSION', 'w') as f:
        f.write(version)

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
    packages=find_packages(),
    install_requires=[
        "carla==0.10.0",
        "pygame>=2.0.0",
        "numpy>=1.19.0",
        "matplotlib>=3.3.0",
        "tabulate>=0.8.7",
        "pyyaml>=5.4.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "carla-simulator-client=src.main:main",
            "csc=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Framework :: CARLA",
    ],
    keywords="carla, autonomous-driving, simulation, pygame, visualization, scenario-testing, vehicle-control, driving-simulator",
    zip_safe=False,
) 