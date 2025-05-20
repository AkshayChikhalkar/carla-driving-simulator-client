"""
Setup script for the CARLA Driving Simulator Client.
"""

from setuptools import setup, find_packages
import os

# Read README.md for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read version from git tag
def get_version():
    try:
        import subprocess
        return subprocess.check_output(['git', 'describe', '--tags', '--always']).decode().strip()
    except:
        return "0.1.0"  # Default version if git is not available

setup(
    name="carla-driving-simulator-client",
    version=get_version(),
    description="A personal CARLA client for driving simulation experiments",
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
    keywords="carla, autonomous-driving, simulation, pygame, visualization",
    zip_safe=False,
) 