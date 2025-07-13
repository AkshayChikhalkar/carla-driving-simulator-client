# CI/CD Workflow Documentation

## Overview

This project uses a **single, unified CI/CD workflow** that handles all activities (build, test, deploy) for both backend and frontend components. The workflow automatically adapts based on which branch triggered the build.

## Workflow Structure

### Main Jobs

1. **Backend Job** - Handles all backend activities
2. **Frontend Job** - Handles all frontend activities  
3. **Integration Tests** - Runs after both backend and frontend complete
4. **Documentation** - Builds and deploys docs (main branch only)
5. **Security Scan** - Scans for vulnerabilities (main branch only)
6. **Notifications** - Notifies team of deployment results

## Branch-Based Behavior

### Development Branch (`develop`)
- **Builds**: Uses development Dockerfiles (`Dockerfile.dev`)
- **Tags**: `dev-{sha}` and `dev-latest`
- **Deploy**: Automatically deploys to development environment
- **Tests**: Runs all tests but skips integration tests

### Staging Branch (`staging`)
- **Builds**: Uses production Dockerfiles (optimized builds)
- **Tags**: `staging-{sha}` and `staging-latest`
- **Deploy**: Automatically deploys to staging environment
- **Tests**: Runs all tests including integration tests

### Production Branch (`master`)
- **Version Bump**: Automatically bumps version based on commit messages
  - `feat:` → Minor version bump
  - `fix:` → Patch version bump  
  - `BREAKING CHANGE` → Major version bump
- **Builds**: Uses production Dockerfiles (optimized builds)
- **Tags**: `prod-{version}` and `latest`
- **Deploy**: Automatically deploys to production environment
- **Tests**: Runs all tests including integration tests
- **Documentation**: Builds and deploys to GitHub Pages
- **Security**: Runs vulnerability scans

### Release Events
- **Builds**: Uses production Dockerfiles
- **Tags**: `prod-{sha}` and `prod-latest`
- **Deploy**: Automatically deploys to production environment

## Workflow Triggers

```yaml
on:
  push:
    branches: [ master, develop, staging ]
  pull_request:
    branches: [ master, develop, staging ]
  release:
    types: [ published ]
```

## Docker Image Naming Convention

| Environment | Backend Image | Frontend Image |
|-------------|---------------|----------------|
| Development | `backend:dev-{version}` | `frontend:dev-{version}` |
| Staging | `backend:staging-{version}` | `frontend:staging-{version}` |
| Production | `backend:prod-{version}` | `frontend:prod-{version}` |

## Development vs Production Dockerfiles

### Backend
- **Development**: `docker/backend/Dockerfile.dev`
  - Includes development tools (pytest, black, flake8, mypy)
  - Hot reload enabled
  - Debug-friendly configuration

- **Production**: `docker/backend/Dockerfile`
  - Optimized for production
  - Minimal dependencies
  - Security hardened

### Frontend
- **Development**: `docker/frontend/Dockerfile.dev`
  - Hot reload enabled
  - Development server
  - Source maps for debugging

- **Production**: `docker/frontend/Dockerfile`
  - Optimized build
  - Static file serving
  - Production-ready configuration

## Deployment Environments

### Development Environment
- **Trigger**: Push to `develop` branch
- **Purpose**: Feature testing and development
- **Deployment**: Automatic
- **Rollback**: Easy (previous dev-latest tag)

### Staging Environment
- **Trigger**: Push to `staging` branch
- **Purpose**: Pre-production testing
- **Deployment**: Automatic
- **Rollback**: Easy (previous staging-latest tag)

### Production Environment
- **Trigger**: Push to `main` branch or release
- **Purpose**: Live production system
- **Deployment**: Automatic
- **Rollback**: Easy (previous prod-latest tag)

## Testing Strategy

### Unit Tests
- **Backend**: Python tests with pytest
- **Frontend**: JavaScript tests with Jest
- **Coverage**: Uploaded to Codecov

### Integration Tests
- **Trigger**: Main and staging branches only
- **Purpose**: End-to-end testing
- **Tools**: Docker Compose test environment

### Security Tests
- **Trigger**: Main branch only
- **Purpose**: Vulnerability scanning
- **Tools**: Trivy scanner

## Monitoring and Notifications

### Success Notifications
- Team is notified when deployments succeed
- Includes environment and version information

### Failure Notifications
- Team is notified when deployments fail
- Includes error details and rollback instructions

## Manual Workflow Triggers

### Testing Specific Branches
```bash
# Test development build
git push origin develop

# Test staging build
git push origin staging

# Test production build (with automatic version bump)
git push origin master
```

### Version Bumping on Master Branch
The workflow automatically bumps versions based on commit messages:

```bash
# Minor version bump (new feature)
git commit -m "feat: add new dashboard feature"
git push origin master

# Patch version bump (bug fix)
git commit -m "fix: resolve authentication issue"
git push origin master

# Major version bump (breaking change)
git commit -m "feat: BREAKING CHANGE - new API structure"
git push origin master
```

### Creating Releases
1. Create a new release in GitHub
2. Tag with version (e.g., v1.0.0)
3. Publish the release
4. Workflow automatically deploys to production

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check Dockerfile syntax
   - Verify dependencies in requirements files
   - Check for missing files in COPY commands

2. **Deployment Failures**
   - Verify environment secrets are set
   - Check deployment scripts
   - Verify target environment is accessible

3. **Test Failures**
   - Check test dependencies
   - Verify test configuration
   - Check for flaky tests

### Debugging Steps

1. **Check Workflow Logs**
   - Go to Actions tab in GitHub
   - Click on the failed workflow
   - Review step-by-step logs

2. **Local Testing**
   - Test Docker builds locally
   - Run tests locally
   - Verify deployment scripts

3. **Rollback Procedure**
   - Use previous image tags
   - Revert to previous commit
   - Redeploy with known good version

## Best Practices

### Code Quality
- Write comprehensive tests
- Use linting tools (black, flake8, mypy)
- Follow coding standards

### Deployment Safety
- Always test in staging first
- Use feature flags for risky changes
- Monitor deployments closely

### Security
- Keep dependencies updated
- Scan for vulnerabilities regularly
- Use least privilege principle

## Configuration

### Environment Variables
- `REGISTRY`: Docker registry (default: ghcr.io)
- `IMAGE_NAME`: Repository name (auto-set)

### Secrets Required
- `GITHUB_TOKEN`: For Docker registry access
- Environment-specific deployment secrets

## Support

For issues with the CI/CD workflow:
1. Check the workflow logs
2. Review this documentation
3. Contact the DevOps team
4. Create an issue in the repository 