.PHONY: help install install-dev test lint format clean build docker-build docker-run docs setup-pre-commit

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install production dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  test           - Run tests with coverage"
	@echo "  test-fast      - Run tests without coverage"
	@echo "  lint           - Run all linting checks"
	@echo "  format         - Format code with black and isort"
	@echo "  clean          - Clean build artifacts"
	@echo "  build          - Build Python package"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-run     - Run Docker container"
	@echo "  docs           - Build documentation"
	@echo "  setup-pre-commit - Install pre-commit hooks"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest --cov=src --cov-branch --cov-report=html --cov-report=term-missing tests/

test-fast:
	pytest tests/

# Linting and formatting
lint:
	black --check --diff src/ tests/
	isort --check-only --diff src/ tests/
	flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	mypy src/ --ignore-missing-imports --no-strict-optional
	bandit -r src/ -f screen
	pip-audit

format:
	black src/ tests/
	isort src/ tests/

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Building
build: clean
	python -m build

# Docker
docker-build:
	docker build -f deployment/docker/Dockerfile -t carla-simulator-client .

docker-run:
	docker run -p 8000:8000 carla-simulator-client

docker-compose-up:
	docker-compose -f deployment/docker/docker-compose.yml up -d

docker-compose-down:
	docker-compose -f deployment/docker/docker-compose.yml down

# Documentation
docs:
	python docs/auto_generate_docs.py

# Pre-commit setup
setup-pre-commit:
	pre-commit install

# Security
security:
	bandit -r src/ -f json -o bandit-report.json
	pip-audit --format json --output pip-audit-report.json

# Development workflow
dev-setup: install-dev setup-pre-commit
	@echo "Development environment setup complete!"

# CI/CD simulation
ci-simulate: lint test security docker-build
	@echo "CI/CD simulation complete!"

# Quick start
quick-start: install docker-build docker-compose-up
	@echo "Quick start complete! Application should be running on http://localhost:8000" 