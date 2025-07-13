# 🗂️ Project Organization Guide

This document explains the organized structure of the CARLA Driving Simulator Client project and best practices for maintaining it.

## 📁 **New Project Structure**

```
carla-driving-simulator-client/
├── 📦 docker/                          # All Docker-related files
│   ├── 🐳 backend/                     # Backend Dockerfiles
│   │   ├── Dockerfile                  # Production backend
│   │   └── Dockerfile.dev              # Development backend
│   ├── 🎨 frontend/                    # Frontend Dockerfiles
│   │   ├── Dockerfile                  # Production frontend
│   │   └── Dockerfile.dev              # Development frontend
│   ├── 🌐 nginx/                       # Nginx configuration
│   │   └── nginx.conf                  # Reverse proxy config
│   └── 🐙 compose/                     # Docker Compose files
│       ├── docker-compose-full-dev.yml     # Full dev stack
│       ├── docker-compose-full-staging.yml # Full staging stack
│       ├── docker-compose-full-prod.yml    # Full production stack
│       ├── docker-compose-backend-dev.yml  # Backend only (dev)
│       ├── docker-compose-backend-staging.yml # Backend only (staging)
│       ├── docker-compose-backend-prod.yml   # Backend only (prod)
│       ├── docker-compose-frontend-dev.yml   # Frontend only (dev)
│       ├── docker-compose-frontend-staging.yml # Frontend only (staging)
│       └── docker-compose-frontend-prod.yml  # Frontend only (prod)
├── 📚 docs/                            # All documentation
│   ├── 🚀 deployment/                  # Deployment guides
│   │   ├── SEPARATE_CONTAINERS.md      # Container architecture
│   │   ├── STAGING_ENVIRONMENT.md      # Staging setup
│   │   └── DOCKER_README.md            # Docker documentation
│   └── 🔧 development/                 # Development guides
│       ├── DEVELOPMENT_WORKFLOW.md     # Development process
│       └── BRANCH_STRATEGY.md         # Git workflow
├── 🛠️ scripts/                         # All scripts
│   ├── 🐳 docker/                      # Docker management scripts
│   │   ├── run-dev.sh                  # Development environment
│   │   ├── run-staging.sh              # Staging environment
│   │   └── run-prod.sh                 # Production environment
│   ├── 🚀 deployment/                  # Deployment scripts
│   │   └── update-version.sh           # Version management
│   └── start.sh                        # Legacy startup script
└── [existing folders remain]
```

## 🎯 **Naming Conventions**

### Docker Compose Files
- **Full Stack**: `docker-compose-full-{env}.yml`
- **Backend Only**: `docker-compose-backend-{env}.yml`
- **Frontend Only**: `docker-compose-frontend-{env}.yml`
- **Environment**: `dev`, `staging`, `prod`

### Scripts
- **Environment**: `run-{env}.sh`
- **Service**: `run-{env}.sh {service}`
- **Services**: `backend`, `frontend`, `full`

## 🚀 **Quick Start Commands**

### Development
```bash
# Full stack development
./scripts/docker/run-dev.sh

# Backend only development
./scripts/docker/run-dev.sh backend

# Frontend only development
./scripts/docker/run-dev.sh frontend
```

### Staging
```bash
# Full stack staging with monitoring
./scripts/docker/run-staging.sh

# Backend only staging
./scripts/docker/run-staging.sh backend

# Frontend only staging
./scripts/docker/run-staging.sh frontend
```

### Production
```bash
# Full stack production
./scripts/docker/run-prod.sh

# Backend only production
./scripts/docker/run-prod.sh backend

# Frontend only production
./scripts/docker/run-prod.sh frontend
```

## 🔧 **Manual Docker Compose Usage**

### Development
```bash
# Full stack
docker-compose -f docker/compose/docker-compose-full-dev.yml up --build -d

# Backend only
docker-compose -f docker/compose/docker-compose-backend-dev.yml up --build -d

# Frontend only
docker-compose -f docker/compose/docker-compose-frontend-dev.yml up --build -d
```

### Staging
```bash
# Full stack with monitoring
docker-compose -f docker/compose/docker-compose-full-staging.yml up --build -d

# Backend only
docker-compose -f docker/compose/docker-compose-backend-staging.yml up --build -d

# Frontend only
docker-compose -f docker/compose/docker-compose-frontend-staging.yml up --build -d
```

### Production
```bash
# Full stack
docker-compose -f docker/compose/docker-compose-full-prod.yml up --build -d

# Backend only
docker-compose -f docker/compose/docker-compose-backend-prod.yml up --build -d

# Frontend only
docker-compose -f docker/compose/docker-compose-frontend-prod.yml up --build -d
```

## 📋 **Port Mapping**

| Environment | Frontend | Backend | Database | Grafana | Prometheus | Loki |
|-------------|----------|---------|----------|---------|------------|------|
| **Development** | 3000 | 8000 | 5432 | - | - | - |
| **Staging** | 3001 | 8001 | 5433 | 3002 | 9091 | 3101 |
| **Production** | 3000 | 8000 | 5432 | 3001 | 9090 | - |

## 🏗️ **Architecture Benefits**

### ✅ **Organized Structure**
- **Clear separation** of Docker files by type and environment
- **Consistent naming** conventions across all files
- **Logical grouping** of related functionality

### ✅ **Flexible Deployment**
- **Service-specific** deployment (backend/frontend only)
- **Environment-specific** configurations (dev/staging/prod)
- **Monitoring integration** for staging and production

### ✅ **Maintainability**
- **Centralized documentation** in organized folders
- **Reusable scripts** for common operations
- **Clear file locations** for easy navigation

### ✅ **Scalability**
- **Independent services** can be deployed separately
- **Environment isolation** prevents conflicts
- **Monitoring stack** for production readiness

## 🔄 **Migration from Old Structure**

### Old Files (Removed)
- `Dockerfile.frontend` → `docker/frontend/Dockerfile`
- `Dockerfile.frontend.dev` → `docker/frontend/Dockerfile.dev`
- `nginx.conf` → `docker/nginx/nginx.conf`
- `docker-compose.separate.yml` → `docker/compose/docker-compose-full-prod.yml`
- `docker-compose.separate.dev.yml` → `docker/compose/docker-compose-full-dev.yml`
- `docker-compose.separate.staging.yml` → `docker/compose/docker-compose-full-staging.yml`
- `scripts/run-separate.sh` → `scripts/docker/run-*.sh`

### Updated References
- **Documentation**: Moved to `docs/deployment/` and `docs/development/`
- **Scripts**: Organized in `scripts/docker/` and `scripts/deployment/`
- **Paths**: Updated in all Docker Compose files to use relative paths

## 📖 **Documentation Organization**

### Deployment Documentation (`docs/deployment/`)
- **SEPARATE_CONTAINERS.md**: Container architecture and setup
- **STAGING_ENVIRONMENT.md**: Staging environment configuration
- **DOCKER_README.md**: Docker usage and best practices

### Development Documentation (`docs/development/`)
- **DEVELOPMENT_WORKFLOW.md**: Development process and guidelines
- **BRANCH_STRATEGY.md**: Git workflow and branching strategy

## 🎯 **Best Practices**

### ✅ **File Organization**
- Keep related files together in logical folders
- Use consistent naming conventions
- Separate concerns (Docker, docs, scripts)

### ✅ **Environment Management**
- Use separate compose files for each environment
- Maintain consistent port mapping across environments
- Include monitoring for staging and production

### ✅ **Script Management**
- Create reusable scripts for common operations
- Use descriptive names and clear documentation
- Support both full stack and service-specific deployment

### ✅ **Documentation**
- Organize documentation by purpose (deployment vs development)
- Keep documentation close to related code
- Maintain clear references and cross-links

## 🚀 **Next Steps**

1. **Test the new structure** with all environments
2. **Update CI/CD pipelines** to use new file paths
3. **Train team members** on the new organization
4. **Monitor deployment** success rates with new structure
5. **Gather feedback** and iterate on organization

---

*This organization follows industry best practices for Docker-based applications and provides a scalable foundation for future development.* 