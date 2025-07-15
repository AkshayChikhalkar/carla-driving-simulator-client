# CARLA Driving Simulator Client - Development Tasks
# PowerShell script for Windows users

param(
    [Parameter(Position=0)]
    [string]$Task = "help"
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  install        - Install production dependencies"
    Write-Host "  install-dev    - Install development dependencies"
    Write-Host "  test           - Run tests with coverage"
    Write-Host "  test-fast      - Run tests without coverage"
    Write-Host "  lint           - Run all linting checks"
    Write-Host "  format         - Format code with black and isort"
    Write-Host "  clean          - Clean build artifacts"
    Write-Host "  build          - Build Python package"
    Write-Host "  docker-build   - Build Docker image"
    Write-Host "  docker-run     - Run Docker container"
    Write-Host "  docs           - Build documentation"
    Write-Host "  setup-pre-commit - Install pre-commit hooks"
    Write-Host "  security       - Run security scans"
    Write-Host "  dev-setup      - Complete development setup"
    Write-Host "  ci-simulate    - Simulate CI/CD pipeline locally"
    Write-Host "  quick-start    - Quick setup and run"
    Write-Host ""
    Write-Host "Usage: .\scripts\dev-tasks.ps1 <task>"
}

function Install-Dependencies {
    Write-Host "Installing production dependencies..." -ForegroundColor Yellow
    pip install -e .
}

function Install-DevDependencies {
    Write-Host "Installing development dependencies..." -ForegroundColor Yellow
    pip install -e ".[dev]"
    pre-commit install
}

function Run-Tests {
    Write-Host "Running tests with coverage..." -ForegroundColor Yellow
    pytest --cov=src --cov-branch --cov-report=html --cov-report=term-missing tests/
}

function Run-TestsFast {
    Write-Host "Running tests without coverage..." -ForegroundColor Yellow
    pytest tests/
}

function Run-Lint {
    Write-Host "Running linting checks..." -ForegroundColor Yellow
    black --check --diff src/ tests/
    isort --check-only --diff src/ tests/
    flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
    mypy src/ --ignore-missing-imports --no-strict-optional
    bandit -r src/ -f screen
    pip-audit
}

function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Yellow
    black src/ tests/
    isort src/ tests/
}

function Clean-Build {
    Write-Host "Cleaning build artifacts..." -ForegroundColor Yellow
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "*.egg-info") { Remove-Item -Recurse -Force "*.egg-info" }
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage" }
    if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }
    if (Test-Path ".mypy_cache") { Remove-Item -Recurse -Force ".mypy_cache" }
    
    # Remove __pycache__ directories
    Get-ChildItem -Path . -Name "__pycache__" -Recurse -Directory | ForEach-Object {
        Remove-Item -Recurse -Force $_
    }
    
    # Remove .pyc files
    Get-ChildItem -Path . -Name "*.pyc" -Recurse -File | ForEach-Object {
        Remove-Item -Force $_
    }
}

function Build-Package {
    Write-Host "Building Python package..." -ForegroundColor Yellow
    Clean-Build
    python -m build
}

function Build-Docker {
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    docker build -f deployment/docker/Dockerfile -t carla-simulator-client .
}

function Run-Docker {
    Write-Host "Running Docker container..." -ForegroundColor Yellow
    docker run -p 8000:8000 carla-simulator-client
}

function Start-DockerCompose {
    Write-Host "Starting Docker Compose..." -ForegroundColor Yellow
    docker-compose -f deployment/docker/docker-compose.yml up -d
}

function Stop-DockerCompose {
    Write-Host "Stopping Docker Compose..." -ForegroundColor Yellow
    docker-compose -f deployment/docker/docker-compose.yml down
}

function Build-Docs {
    Write-Host "Building documentation..." -ForegroundColor Yellow
    python docs/auto_generate_docs.py
}

function Setup-PreCommit {
    Write-Host "Installing pre-commit hooks..." -ForegroundColor Yellow
    pre-commit install
}

function Run-Security {
    Write-Host "Running security scans..." -ForegroundColor Yellow
    bandit -r src/ -f json -o bandit-report.json
    pip-audit --format json --output pip-audit-report.json
}

function Setup-DevEnvironment {
    Write-Host "Setting up development environment..." -ForegroundColor Yellow
    Install-DevDependencies
    Setup-PreCommit
    Write-Host "Development environment setup complete!" -ForegroundColor Green
}

function Simulate-CI {
    Write-Host "Simulating CI/CD pipeline locally..." -ForegroundColor Yellow
    Run-Lint
    Run-Tests
    Run-Security
    Build-Docker
    Write-Host "CI/CD simulation complete!" -ForegroundColor Green
}

function Quick-Start {
    Write-Host "Quick start setup..." -ForegroundColor Yellow
    Install-Dependencies
    Build-Docker
    Start-DockerCompose
    Write-Host "Quick start complete! Application should be running on http://localhost:8000" -ForegroundColor Green
}

# Main execution
switch ($Task.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "install-dev" { Install-DevDependencies }
    "test" { Run-Tests }
    "test-fast" { Run-TestsFast }
    "lint" { Run-Lint }
    "format" { Format-Code }
    "clean" { Clean-Build }
    "build" { Build-Package }
    "docker-build" { Build-Docker }
    "docker-run" { Run-Docker }
    "docker-compose-up" { Start-DockerCompose }
    "docker-compose-down" { Stop-DockerCompose }
    "docs" { Build-Docs }
    "setup-pre-commit" { Setup-PreCommit }
    "security" { Run-Security }
    "dev-setup" { Setup-DevEnvironment }
    "ci-simulate" { Simulate-CI }
    "quick-start" { Quick-Start }
    default {
        Write-Host "Unknown task: $Task" -ForegroundColor Red
        Show-Help
    }
} 