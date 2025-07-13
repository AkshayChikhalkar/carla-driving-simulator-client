# Separate Container Deployment

This document describes the new separate container deployment setup for the CARLA Driving Simulator Client.

## Overview

The application is now deployed using separate containers for better scalability, maintainability, and resource isolation:

- **Backend Container**: FastAPI application with Python dependencies
- **Frontend Container**: React application served by Nginx
- **Database Container**: PostgreSQL database
- **Monitoring Containers**: Prometheus and Grafana (optional)

## Quick Start

### Using the provided script (Recommended)

```bash
# Production mode
./scripts/run-separate.sh

# Development mode
./scripts/run-separate.sh dev
```

### Manual deployment

```bash
# Production
docker-compose -f docker/compose/docker-compose-full-prod.yml up --build -d

# Development
docker-compose -f docker/compose/docker-compose-full-dev.yml up --build -d
```

## Container Architecture

### Backend Container (`docker/backend/Dockerfile`)
- **Base Image**: Python 3.11-slim
- **Port**: 8000
- **Features**:
  - FastAPI application
  - CARLA integration
  - Database management
  - API endpoints
  - WebSocket support

### Frontend Container (`Dockerfile.frontend`)
- **Base Image**: Node.js 18 (build) + Nginx (production)
- **Port**: 3000
- **Features**:
  - React application
  - Nginx reverse proxy
  - API proxying to backend
  - WebSocket proxying
  - Static file serving

### Database Container
- **Base Image**: PostgreSQL 15-alpine
- **Port**: 5432
- **Features**:
  - Persistent data storage
  - Health checks
  - Initialization scripts

## Version Tracking

The application now includes automatic version tracking:

1. **Version Display**: Shows in the bottom-left corner of the frontend
2. **Build Information**: Includes version and build time
3. **API Endpoint**: `/api/version` provides version information
4. **Environment Variables**: `VERSION` and `BUILD_TIME` are available

## Development vs Production

### Development Mode
- Hot reloading for frontend
- Volume mounts for live code changes
- Debug logging enabled
- Development dependencies included

### Production Mode
- Optimized builds
- Nginx serving static files
- Minimal container sizes
- Production logging levels

## Automated Builds

The GitHub Actions workflow now supports:

1. **Change Detection**: Only builds containers that have changes
2. **Separate Publishing**: Backend and frontend images published separately
3. **Version Management**: Automatic version bumping and tagging
4. **Artifact Caching**: Reuses built images when possible

### Change Detection Rules

- **Backend Changes**: `src/`, `web/backend/`, `requirements`, `setup.py`, `run.py`, `config/`
- **Frontend Changes**: `web/frontend/`, `package.json`, `package-lock.json`
- **Database Changes**: `database/`, `db_`, `sql`
- **Documentation Changes**: `docs/`, `README`, `CHANGELOG`

## Environment Variables

### Backend
```bash
DATABASE_URL=postgresql://postgres:postgres@database:5432/carla_simulator
CARLA_HOST=localhost
CARLA_PORT=2000
WEB_HOST=0.0.0.0
WEB_PORT=8000
LOG_LEVEL=INFO
DEBUG=false
TESTING=false
VERSION=latest
```

### Frontend
```bash
VERSION=latest
REACT_APP_API_URL=http://localhost:8000  # Development only
```

## Networking

All containers are connected via a custom bridge network (`carla-network`):
- Backend can reach database via `database:5432`
- Frontend can reach backend via `backend:8000`
- External access via exposed ports

## Health Checks

Each container includes health checks:

- **Backend**: `curl -f http://localhost:8000/api/scenarios`
- **Frontend**: `wget --spider http://localhost:3000/`
- **Database**: `pg_isready -U postgres`

## Monitoring

Optional monitoring stack included:

- **Prometheus**: Metrics collection on port 9090
- **Grafana**: Dashboard on port 3001
- **Configuration**: Uses existing monitoring configs

## Migration from Monolithic

To migrate from the old monolithic setup:

1. **Stop old containers**:
   ```bash
   docker-compose down
   ```

2. **Start new setup**:
   ```bash
   ./scripts/run-separate.sh
   ```

3. **Verify functionality**:
   - Check frontend: http://localhost:3000
   - Check backend: http://localhost:8000/api/scenarios
   - Check version display in frontend

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 8000, 5432 are available
2. **Database connection**: Check if database container is healthy
3. **Version not showing**: Check `/api/version` endpoint
4. **Build failures**: Check Docker logs for missing dependencies

### Useful Commands

```bash
# View all logs
docker-compose -f docker/compose/docker-compose-full-prod.yml logs -f

# View specific service logs
docker-compose -f docker/compose/docker-compose-full-prod.yml logs -f backend

# Restart specific service
docker-compose -f docker/compose/docker-compose-full-prod.yml restart backend

# Check service status
docker-compose -f docker/compose/docker-compose-full-prod.yml ps

# Access container shell
docker-compose -f docker/compose/docker-compose-full-prod.yml exec backend bash
```

## Performance Benefits

1. **Resource Isolation**: Each service has dedicated resources
2. **Independent Scaling**: Scale backend/frontend separately
3. **Faster Builds**: Only rebuild changed components
4. **Better Caching**: Layer caching per container
5. **Easier Debugging**: Isolated logs and processes

## Security Considerations

1. **Network Isolation**: Services communicate via internal network
2. **Minimal Base Images**: Reduced attack surface
3. **Non-root Users**: Containers run with limited privileges
4. **Health Checks**: Automatic failure detection
5. **Resource Limits**: Configurable memory and CPU limits 