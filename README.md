# CARLA Driving Simulator Client

<p align="left">
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/actions/workflows/build-publish-release.yml" target="_blank">
        <img src="https://img.shields.io/github/actions/workflow/status/akshaychikhalkar/carla-driving-simulator-client/build-publish-release.yml?branch=master&label=CI%2FCD%20Pipeline&logo=github" alt="CI/CD Pipeline">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/actions/workflows/build-publish-release.yml" target="_blank">
        <img src="https://img.shields.io/github/actions/workflow/status/akshaychikhalkar/carla-driving-simulator-client/build-publish-release.yml?branch=master&label=Tests&logo=github" alt="Tests">
    </a>
    <a href="https://codecov.io/gh/akshaychikhalkar/carla-driving-simulator-client" target="_blank">
        <img src="https://img.shields.io/codecov/c/github/akshaychikhalkar/carla-driving-simulator-client/master?logo=codecov" alt="Codecov">
    </a>
    <a href="https://carla-driving-simulator-client.readthedocs.io/en/latest/" target="_blank">
        <img src="https://img.shields.io/readthedocs/carla-driving-simulator-client?logo=read-the-docs" alt="Documentation Status">
    </a>
    <a href="https://opensource.org/licenses/MIT" target="_blank">
        <img src="https://img.shields.io/github/license/akshaychikhalkar/carla-driving-simulator-client" alt="License">
    </a>
    <a href="https://www.python.org/downloads/" target="_blank">
        <img src="https://img.shields.io/badge/python-3.11-blue.svg?logo=python" alt="Python 3.11">
    </a>
    <a href="https://github.com/psf/black" target="_blank">
        <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
    </a>
    <a href="https://pypi.org/project/carla-driving-simulator-client/" target="_blank">
        <img src="https://img.shields.io/pypi/v/carla-driving-simulator-client?logo=pypi" alt="PyPI version">
    </a>
    <a href="https://hub.docker.com/r/akshaychikhalkar/carla-driving-simulator-client" target="_blank">
        <img src="https://img.shields.io/docker/pulls/akshaychikhalkar/carla-driving-simulator-client?logo=docker" alt="Docker Hub">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/releases" target="_blank">
        <img src="https://img.shields.io/github/v/release/akshaychikhalkar/carla-driving-simulator-client?logo=github" alt="GitHub release">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/issues" target="_blank">
        <img src="https://img.shields.io/github/issues/akshaychikhalkar/carla-driving-simulator-client" alt="GitHub issues">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/pulls" target="_blank">
        <img src="https://img.shields.io/github/issues-pr/akshaychikhalkar/carla-driving-simulator-client" alt="GitHub pull requests">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client/commits/master" target="_blank">
        <img src="https://img.shields.io/github/last-commit/akshaychikhalkar/carla-driving-simulator-client/master" alt="GitHub last commit">
    </a>
    <a href="https://github.com/akshaychikhalkar/carla-driving-simulator-client" target="_blank">
        <img src="https://img.shields.io/github/repo-size/akshaychikhalkar/carla-driving-simulator-client" alt="GitHub repo size">
    </a>
</p>

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
- **Automatic versioning and CI/CD pipeline**
- **Docker support with zero-configuration setup**
- **Web-based frontend and backend API**

## Requirements

- Python 3.11
- CARLA Simulator 0.10.0
- Pygame
- NumPy
- Matplotlib
- Tabulate
- PyYAML
- SQLAlchemy
- PostgreSQL (optional)

## Installation

### From Docker (Recommended)
```bash
# Pull the latest image
docker pull akshaychikhalkar/carla-driving-simulator-client:latest

# Run with Docker (frontend served by backend on port 8081)
docker run -p 8081:8000 akshaychikhalkar/carla-driving-simulator-client:latest

# Or use Docker Compose (recommended)
git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
cd carla-driving-simulator-client
docker-compose -f docker-compose-prod.yml up -d
```

### From PyPI
```bash
pip install carla-driving-simulator-client
```

### From Source
1. Clone the repository:
```bash
git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
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
set PYTHONPATH=%PYTHONPATH%;C:\path\to\carla\PythonAPI\carla\dist\carla-0.10.0-py3.11-win-amd64.egg

# For Linux
export PYTHONPATH=$PYTHONPATH:/path/to/carla/PythonAPI/carla/dist/carla-0.10.0-py3.11-linux-x86_64.egg
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
python -m carla_simulator.cli
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
├── carla_simulator/
│   ├── core/
│   ├── visualization/
│   ├── control/
│   ├── scenarios/
│   ├── database/
│   ├── utils/
│   └── cli.py
├── web/
├── tests/
├── config/
├── docs/
├── requirements/
└── README.md
```

## Testing

This project includes comprehensive testing for both backend (Python) and frontend (React) components.

### Backend Testing
```bash
# Run all Python tests
pytest tests/ --cov=carla_simulator --cov=web --cov-branch

# Run specific test modules
pytest tests/test_core.py
pytest tests/test_scenarios.py
```

### Frontend Testing
```bash
# Navigate to frontend directory
cd web/frontend

# Install dependencies
npm install

# Run tests in watch mode (development)
npm test

# Run tests in CI mode (no watch, with coverage)
npm run test:ci
```

### CI/CD Pipeline
The project uses GitHub Actions for automated testing:
- **Backend Tests**: Python tests with pytest and coverage reporting
- **Frontend Tests**: React tests with Jest and coverage reporting
- **Docker Tests**: Build and runtime validation of Docker containers
- **Integration Tests**: End-to-end testing of the complete system

All tests must pass before code can be merged to the main branch.

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

**Important**: Please ensure all tests pass before submitting a pull request. The CI/CD pipeline will automatically run both backend and frontend tests.

Note: I cannot guarantee response times or implementation of suggested features as this project is maintained in my free time.

## Support

If you need help, please check our [Support Guide](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/SUPPORT.md) for various ways to get assistance.

## Security

Please report any security issues to our [Security Policy](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/LICENSE) file for details.

## Acknowledgments

- CARLA Simulator Team
- TH OWL for initial development

## Roadmap

Check our [Roadmap](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/ROADMAP.md) for planned features and improvements.

## Documentation

- **[Versioning Strategy](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/VERSIONING.md)** - How automatic versioning works
- **[Environment Configuration](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/ENVIRONMENT.md)** - Environment variables and configuration
- **[Support Guide](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/SUPPORT.md)** - Getting help and support
- **[Security Policy](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/SECURITY.md)** - Reporting security issues
- **[Contributing Guidelines](https://github.com/AkshayChikhalkar/carla-driving-simulator-client/blob/master/CONTRIBUTING.md)** - How to contribute to the project

## Configuration 