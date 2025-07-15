@echo off
REM CARLA Driving Simulator Client - Development Tasks
REM Batch file for Windows users

if "%1"=="" (
    echo Available commands:
    echo   install        - Install production dependencies
    echo   install-dev    - Install development dependencies
    echo   test           - Run tests with coverage
    echo   test-fast      - Run tests without coverage
    echo   lint           - Run all linting checks
    echo   format         - Format code with black and isort
    echo   clean          - Clean build artifacts
    echo   build          - Build Python package
    echo   docker-build   - Build Docker image
    echo   docker-run     - Run Docker container
    echo   docs           - Build documentation
    echo   setup-pre-commit - Install pre-commit hooks
    echo   security       - Run security scans
    echo   dev-setup      - Complete development setup
    echo   ci-simulate    - Simulate CI/CD pipeline locally
    echo   quick-start    - Quick setup and run
    echo.
    echo Usage: dev-tasks.bat ^<task^>
    goto :eof
)

if "%1"=="install" (
    echo Installing production dependencies...
    pip install -e .
    goto :eof
)

if "%1"=="install-dev" (
    echo Installing development dependencies...
    pip install -e ".[dev]"
    pre-commit install
    goto :eof
)

if "%1"=="test" (
    echo Running tests with coverage...
    pytest --cov=src --cov-branch --cov-report=html --cov-report=term-missing tests/
    goto :eof
)

if "%1"=="test-fast" (
    echo Running tests without coverage...
    pytest tests/
    goto :eof
)

if "%1"=="lint" (
    echo Running linting checks...
    black --check --diff src/ tests/
    isort --check-only --diff src/ tests/
    flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
    mypy src/ --ignore-missing-imports --no-strict-optional
    bandit -r src/ -f screen
    pip-audit
    goto :eof
)

if "%1"=="format" (
    echo Formatting code...
    black src/ tests/
    isort src/ tests/
    goto :eof
)

if "%1"=="clean" (
    echo Cleaning build artifacts...
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist
    if exist *.egg-info rmdir /s /q *.egg-info
    if exist htmlcov rmdir /s /q htmlcov
    if exist .coverage del .coverage
    if exist .pytest_cache rmdir /s /q .pytest_cache
    if exist .mypy_cache rmdir /s /q .mypy_cache
    for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
    for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
    goto :eof
)

if "%1"=="build" (
    echo Building Python package...
    call dev-tasks.bat clean
    python -m build
    goto :eof
)

if "%1"=="docker-build" (
    echo Building Docker image...
    docker build -f deployment/docker/Dockerfile -t carla-simulator-client .
    goto :eof
)

if "%1"=="docker-run" (
    echo Running Docker container...
    docker run -p 8000:8000 carla-simulator-client
    goto :eof
)

if "%1"=="docker-compose-up" (
    echo Starting Docker Compose...
    docker-compose -f deployment/docker/docker-compose.yml up -d
    goto :eof
)

if "%1"=="docker-compose-down" (
    echo Stopping Docker Compose...
    docker-compose -f deployment/docker/docker-compose.yml down
    goto :eof
)

if "%1"=="docs" (
    echo Building documentation...
    python docs/auto_generate_docs.py
    goto :eof
)

if "%1"=="setup-pre-commit" (
    echo Installing pre-commit hooks...
    pre-commit install
    goto :eof
)

if "%1"=="security" (
    echo Running security scans...
    bandit -r src/ -f json -o bandit-report.json
    pip-audit --format json --output pip-audit-report.json
    goto :eof
)

if "%1"=="dev-setup" (
    echo Setting up development environment...
    call dev-tasks.bat install-dev
    call dev-tasks.bat setup-pre-commit
    echo Development environment setup complete!
    goto :eof
)

if "%1"=="ci-simulate" (
    echo Simulating CI/CD pipeline locally...
    call dev-tasks.bat lint
    call dev-tasks.bat test
    call dev-tasks.bat security
    call dev-tasks.bat docker-build
    echo CI/CD simulation complete!
    goto :eof
)

if "%1"=="quick-start" (
    echo Quick start setup...
    call dev-tasks.bat install
    call dev-tasks.bat docker-build
    call dev-tasks.bat docker-compose-up
    echo Quick start complete! Application should be running on http://localhost:8000
    goto :eof
)

echo Unknown task: %1
echo Run 'dev-tasks.bat' without arguments to see available commands. 