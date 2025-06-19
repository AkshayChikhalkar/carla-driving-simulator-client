# Docker Setup for CARLA Driving Simulator Client

This document explains how to use the Docker setup with Git workflows for the CARLA Driving Simulator Client.

## Docker Images

### Production Image (`Dockerfile`)
- **Purpose**: Optimized for production deployment
- **Features**: 
  - Multi-stage build for smaller image size
  - Built frontend (no development server)
  - Non-root user for security
  - Minimal runtime dependencies
- **Size**: ~50-70% smaller than development image

### Development Image (`Dockerfile.dev`)
- **Purpose**: Development and testing
- **Features**:
  - Single-stage build for faster iteration
  - Development server with hot reload
  - All development dependencies included
  - Easier debugging

## Quick Start

### Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Individual Docker Commands

#### Development Mode
```bash
# Build development image
docker build -f Dockerfile.dev -t carla-simulator:dev .

# Run development container
docker run -it --rm \
  -p 3000:3000 \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  carla-simulator:dev
```

#### Production Mode
```bash
# Build production image
docker build -t carla-simulator:prod .

# Run production container
docker run -it --rm \
  -p 3000:3000 \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  carla-simulator:prod
```

## Git Workflow Integration

### GitHub Actions Workflows

#### 1. Pull Request Tests (`pr-test.yml`)
- **Triggers**: Pull requests to `main` or `develop`
- **Actions**:
  - Run Python linting and tests
  - Run frontend linting and tests
  - Test Docker builds (both production and development)
  - Upload coverage reports

#### 2. Full CI/CD Pipeline (`ci-cd.yml`)
- **Triggers**: Push to `main`, `develop`, or `CI/CD` branches
- **Actions**:
  - All PR test actions
  - Build and test Docker images
  - Build Python package
  - Publish to Docker Hub (on `CI/CD` branch)
  - Publish to PyPI (on `CI/CD` branch)
  - Create GitHub release (on `CI/CD` branch)

### Required Secrets

Configure these secrets in your GitHub repository:

```bash
# Docker Hub
DOCKERHUB_USERNAME=your_dockerhub_username
DOCKERHUB_TOKEN=your_dockerhub_token

# PyPI
PYPI_TOKEN=your_pypi_token

# Code Coverage
CODECOV_TOKEN=your_codecov_token
```

### Branch Strategy

- **`main`**: Production-ready code
- **`develop`**: Development branch
- **`CI/CD`**: Triggers full deployment pipeline

## Docker Image Tags

### Production Images
- `latest`: Latest production release
- `prod`: Production tag
- `v1.2.3`: Semantic version tags
- `1.2`: Major.minor version tags
- `1`: Major version tags

### Development Images
- `dev-1.2.3`: Development version tags
- `dev`: Development tag

## Local Development

### Prerequisites
- Docker and Docker Compose
- Git

### Development Workflow

1. **Clone and setup**:
   ```bash
   git clone https://github.com/your-repo/carla-driving-simulator-client.git
   cd carla-driving-simulator-client
   ```

2. **Start development environment**:
   ```bash
   docker-compose up --build
   ```

3. **Access services**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

4. **Make changes**:
   - Frontend changes: Hot reload enabled
   - Backend changes: Restart container or use volume mounts

5. **Test changes**:
   ```bash
   # Run tests locally
   docker-compose exec carla-simulator pytest
   
   # Or run in CI
   git push origin feature/your-feature
   ```

### Volume Mounts

The Docker setup includes these volume mounts for development:

- `./config:/app/config`: Configuration files
- `./logs:/app/logs`: Application logs
- `./reports:/app/reports`: Generated reports

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the ports
lsof -i :3000
lsof -i :8000

# Kill processes or use different ports
docker run -p 3001:3000 -p 8001:8000 ...
```

#### 2. Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER config/ logs/ reports/

# Or run with proper user mapping
docker run -u $(id -u):$(id -g) ...
```

#### 3. Build Failures
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t carla-simulator:dev .
```

#### 4. Frontend Not Accessible
- Check if React dev server is binding to `0.0.0.0`
- Verify CRACO configuration
- Check container logs: `docker-compose logs frontend`

#### 5. Backend Connection Issues
- Verify backend is running: `docker-compose logs backend`
- Check API health: `curl http://localhost:8000/api/scenarios`
- Ensure proper proxy configuration in frontend

### Debugging

#### View Container Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend

# Follow logs
docker-compose logs -f
```

#### Access Container Shell
```bash
# Development container
docker-compose exec carla-simulator bash

# Or run new container
docker run -it carla-simulator:dev bash
```

#### Check Container Status
```bash
# Running containers
docker-compose ps

# Container details
docker-compose exec carla-simulator ps aux
```

## Performance Optimization

### Production Optimizations
- Use production Dockerfile for smaller images
- Enable Docker layer caching in CI/CD
- Use multi-stage builds
- Implement health checks

### Development Optimizations
- Use volume mounts for code changes
- Enable hot reload for frontend
- Use development Dockerfile for faster builds
- Implement proper caching strategies

## Security Considerations

### Production Security
- Non-root user in production images
- Minimal runtime dependencies
- Regular security updates
- Proper secret management

### Development Security
- Local development only
- No sensitive data in development images
- Proper .dockerignore configuration

## Monitoring and Logging

### Health Checks
```bash
# Check service health
curl http://localhost:8000/api/scenarios

# Docker health status
docker-compose ps
```

### Logging
- Application logs: `./logs/` directory
- Docker logs: `docker-compose logs`
- Structured logging with timestamps

## Contributing

### Development Guidelines
1. Use development Dockerfile for local work
2. Test both Dockerfiles before submitting PR
3. Update documentation for Docker changes
4. Follow the established Git workflow

### Testing Docker Changes
```bash
# Test production build
docker build -t test-prod .

# Test development build
docker build -f Dockerfile.dev -t test-dev .

# Test docker-compose
docker-compose up --build
```

## Support

For Docker-related issues:
1. Check the troubleshooting section
2. Review container logs
3. Verify configuration files
4. Create an issue with detailed error information 