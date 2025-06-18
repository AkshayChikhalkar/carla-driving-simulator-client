# CARLA Driving Simulator Client

[![CI](https://github.com/akshaychikhalkar/carla-driving-simulator-client/actions/workflows/ci.yml/badge.svg)](https://github.com/akshaychikhalkar/carla-driving-simulator-client/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/akshaychikhalkar/carla-driving-simulator-client/branch/main/graph/badge.svg)](https://codecov.io/gh/akshaychikhalkar/carla-driving-simulator-client)
[![Documentation Status](https://readthedocs.org/projects/carla-driving-simulator-client/badge/?version=latest)](https://carla-driving-simulator-client.readthedocs.io/en/latest/?badge=latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI version](https://badge.fury.io/py/carla-driving-simulator-client.svg)](https://badge.fury.io/py/carla-driving-simulator-client)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/akshaychikhalkar/carla-driving-simulator-client)](https://github.com/akshaychikhalkar/carla-driving-simulator-client/releases)
[![GitHub issues](https://img.shields.io/github/issues/akshaychikhalkar/carla-driving-simulator-client)](https://github.com/akshaychikhalkar/carla-driving-simulator-client/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/akshaychikhalkar/carla-driving-simulator-client)](https://github.com/akshaychikhalkar/carla-driving-simulator-client/pulls)
[![Run tests and upload coverage](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/actions/workflows/build-publish-release.yml/badge.svg?branch=CI%2FCD)](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/actions/workflows/build-publish-release.yml)
A personal project for experimenting with CARLA client, featuring vehicle control, sensor management, and visualization capabilities.

## Features

- Realistic vehicle physics and control
- Multiple sensor types (Camera, GNSS, Collision, Lane Invasion)
- Dynamic weather system
- Traffic and pedestrian simulation
- Real-time visualization with HUD and minimap
- Comprehensive logging and data collection
- Support for both manual and autopilot modes
- Configurable simulation parameters

## Requirements

- Python 3.7+
- CARLA Simulator 0.10.0
- Pygame
- NumPy
- Matplotlib
- Tabulate
- PyYAML

## Installation

### From PyPI
```bash
pip install carla-driving-simulator-client
```

### From Source
1. Clone the repository:
```bash
git clone https://github.com/akshaychikhalkar/carla-driving-simulator-client.git
cd carla-driving-simulator-client
```

2. Install in development mode:
```bash
pip install -e .
```

3. Install CARLA:
- Download CARLA 0.10.0 from [CARLA's website](https://carla.org/)
- Extract the package and set the CARLA_ROOT environment variable
- Add CARLA Python API to your PYTHONPATH:
```bash
# For Windows
set PYTHONPATH=%PYTHONPATH%;C:\path\to\carla\PythonAPI\carla\dist\carla-0.10.0-py3.7-win-amd64.egg

# For Linux
export PYTHONPATH=$PYTHONPATH:/path/to/carla/PythonAPI/carla/dist/carla-0.10.0-py3.7-linux-x86_64.egg
```

## Usage

1. Start the CARLA server:
```bash
./CarlaUE4.sh -carla-rpc-port=2000
```

2. Run the simulator client:
```bash
# If installed from PyPI
carla-simulator-client

# If installed from source
python src/main.py
```

## Configuration

The simulator client can be configured through the `config/simulation_config.yaml` file. Key parameters include:

- Target distance
- Maximum speed
- Simulation duration
- Vehicle model
- Sensor settings
- Weather conditions

## Project Structure

```
carla-driving-simulator-client/
├── src/
│   ├── core/
│   │   ├── world.py
│   │   ├── vehicle.py
│   │   └── sensors.py
│   ├── visualization/
│   │   ├── hud.py
│   │   ├── minimap.py
│   │   └── camera.py
│   ├── control/
│   │   ├── keyboard.py
│   │   └── autopilot.py
│   └── utils/
│       ├── config.py
│       └── logging.py
├── tests/
├── config/
├── docs/
├── requirements.txt
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch:
```bash
git checkout -b feature/amazing-feature
```
3. Commit your changes:
```bash
git commit -m 'Add some amazing feature'
```
4. Push to the branch:
```bash
git push origin feature/amazing-feature
```
5. Open a Pull Request

Note: I cannot guarantee response times or implementation of suggested features as this project is maintained in my free time.

## Support

If you need help, please check our [Support Guide](SUPPORT.md) for various ways to get assistance.

## Security

Please report any security issues to our [Security Policy](SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- CARLA Simulator Team
- TH OWL for initial development

## Roadmap

Check our [Roadmap](ROADMAP.md) for planned features and improvements. 