# Setup Pre-commit Hooks for Windows
# This script sets up pre-commit hooks with the correct configuration

Write-Host "Setting up pre-commit hooks..." -ForegroundColor Green

# Check if pre-commit config exists in root
if (Test-Path ".pre-commit-config.yaml") {
    Write-Host "Pre-commit config already exists in root directory" -ForegroundColor Yellow
} else {
    # Copy from config/tools to root
    if (Test-Path "config\tools\.pre-commit-config.yaml") {
        Copy-Item "config\tools\.pre-commit-config.yaml" ".pre-commit-config.yaml"
        Write-Host "Copied pre-commit config to root directory" -ForegroundColor Green
    } else {
        Write-Host "Error: Pre-commit config not found in config\tools\" -ForegroundColor Red
        exit 1
    }
}

# Install pre-commit hooks
try {
    pre-commit install
    Write-Host "Pre-commit hooks installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "Error installing pre-commit hooks. Make sure pre-commit is installed:" -ForegroundColor Red
    Write-Host "pip install pre-commit" -ForegroundColor Yellow
    exit 1
}

Write-Host "Pre-commit setup complete!" -ForegroundColor Green
Write-Host "You can now run: .\scripts\dev-tasks.ps1 dev-setup" -ForegroundColor Cyan 