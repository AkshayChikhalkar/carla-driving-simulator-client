# Branch Strategy

This document outlines the branch strategy for the CARLA Driving Simulator Client, focusing on development testing before production deployment.

## 🌿 **Branch Structure**

```
master (main branch)
├── development (development branch)
│   ├── feature/separate-containers
│   ├── feature/version-tracking
│   └── feature/automated-builds
├── staging (staging branch)
│   ├── integration-tests
│   └── performance-tests
└── production (production branch)
```

## 🎯 **Branch Strategy**

### Development Branch (`development`)
- **Purpose**: Active development and testing
- **Workflow**: 
  - All new features developed here
  - Comprehensive testing before production
  - CI/CD runs on every push
  - Docker images tagged as `dev`

### Staging Branch (`staging`)
- **Purpose**: Pre-production testing and validation
- **Workflow**:
  - Features from development branch
  - Integration testing
  - Performance testing
  - Load testing
  - Security testing
  - Docker images tagged as `staging`

### Production Branch (`production`)
- **Purpose**: Stable production releases
- **Workflow**:
  - Only tested features from staging
  - Automated deployments
  - Docker images tagged with version numbers
  - Monitoring and alerting

### Master Branch (`master`)
- **Purpose**: Main branch for releases
- **Workflow**:
  - Automatic version bumping
  - GitHub releases
  - PyPI publishing
  - Docker Hub publishing

## 🚀 **Development Workflow**

### 1. Start Development
```bash
# Create development branch
git checkout -b development

# Push development branch
git push -u origin development
```

### 2. Develop Features
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
./scripts/test-dev-setup.sh

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push feature branch
git push origin feature/new-feature
```

### 3. Merge to Development
```bash
# Switch to development
git checkout development

# Merge feature
git merge feature/new-feature

# Test in development environment
./scripts/test-dev-setup.sh

# Push to development
git push origin development
```

### 4. Test Thoroughly
```bash
# Run comprehensive tests
./scripts/test-dev-setup.sh

# Manual testing
curl http://localhost:8000/api/scenarios
curl http://localhost:3000

# Check CI/CD pipeline
# Visit GitHub Actions to verify builds
```

### 5. Deploy to Staging
```bash
# Switch to staging
git checkout staging

# Merge from development
git merge development

# Test staging setup
./scripts/run-separate.sh staging

# Run staging tests
./scripts/test-staging-setup.sh

# Push to staging
git push origin staging
```

### 6. Deploy to Production
```bash
# Switch to production
git checkout production

# Merge from staging
git merge staging

# Test production setup
./scripts/run-separate.sh

# Push to production
git push origin production
```

## 🔄 **CI/CD Pipeline**

### Development Branch
- **Triggers**: Push to `development`
- **Actions**:
  - Run tests
  - Build Docker images (tagged as `dev`)
  - Deploy to development environment
  - Run change detection

### Staging Branch
- **Triggers**: Push to `staging`
- **Actions**:
  - Run integration tests
  - Run performance tests
  - Run load tests
  - Run security tests
  - Build staging Docker images
  - Deploy to staging environment
  - Monitor staging performance

### Production Branch
- **Triggers**: Push to `production`
- **Actions**:
  - Run comprehensive tests
  - Build production Docker images
  - Deploy to production
  - Create GitHub release
  - Publish to Docker Hub
  - Publish to PyPI

### Master Branch
- **Triggers**: Push to `master`
- **Actions**:
  - Version bumping
  - GitHub release creation
  - Docker image publishing
  - PyPI package publishing

## 🧪 **Testing Strategy**

### Development Testing
```bash
# Start development environment
./scripts/run-separate.sh dev

# Run comprehensive tests
./scripts/test-dev-setup.sh

# Manual testing
curl http://localhost:8000/api/scenarios
curl http://localhost:8000/api/version
curl http://localhost:3000
```

### Staging Testing
```bash
# Start staging environment
./scripts/run-separate.sh staging

# Run comprehensive staging tests
./scripts/test-staging-setup.sh

# Manual testing
curl http://localhost:8001/api/scenarios
curl http://localhost:8001/api/version
curl http://localhost:3001
```

### Production Testing
```bash
# Start production environment
./scripts/run-separate.sh

# Test production endpoints
curl http://localhost:8000/api/scenarios
curl http://localhost:3000

# Check version tracking
curl http://localhost:8000/api/version
```

## 📋 **Release Process**

### Pre-Release Checklist
- [ ] All tests pass in development
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Security reviewed
- [ ] Documentation updated
- [ ] Version tracking working
- [ ] Docker images build successfully

### Release Steps
1. **Development Testing**
   ```bash
   git checkout development
   ./scripts/test-dev-setup.sh
   ```

2. **Staging Testing**
   ```bash
   git checkout staging
   git merge development
   ./scripts/run-separate.sh staging
   ./scripts/test-staging-setup.sh
   git push origin staging
   ```

3. **Production Deployment**
   ```bash
   git checkout production
   git merge staging
   git push origin production
   ./scripts/run-separate.sh
   ```

4. **Monitor Production**
   - Check application health
   - Monitor logs
   - Verify version display
   - Test all features

5. **Create Release**
   ```bash
   git checkout master
   git merge production
   git push origin master
   ```

## 🐛 **Hotfix Process**

### Emergency Hotfix
```bash
# Create hotfix branch
git checkout -b hotfix/critical-fix

# Make fix
# Test fix
./scripts/test-dev-setup.sh

# Commit and push
git add .
git commit -m "fix: critical issue"
git push origin hotfix/critical-fix

# Merge to production
git checkout production
git merge hotfix/critical-fix
git push origin production

# Deploy
./scripts/run-separate.sh
```

## 📊 **Monitoring and Alerts**

### Development Monitoring
- Container health checks
- API response times
- Error rates
- Resource usage

### Production Monitoring
- Application availability
- Performance metrics
- Error tracking
- User experience monitoring

## 🔒 **Security Considerations**

### Development Security
- No production secrets in development
- Isolated development environment
- Regular security updates
- Code review process

### Production Security
- Secrets management
- Network isolation
- Access controls
- Monitoring and alerting

## 📝 **Documentation**

### Required Documentation Updates
- [ ] README.md
- [ ] SEPARATE_CONTAINERS.md
- [ ] DEVELOPMENT_WORKFLOW.md
- [ ] API documentation
- [ ] Deployment guides

### Release Notes
- Feature descriptions
- Bug fixes
- Breaking changes
- Migration guides

## 🎯 **Success Metrics**

### Development Success
- ✅ All tests pass
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Security reviewed

### Production Success
- ✅ Zero-downtime deployment
- ✅ All services healthy
- ✅ Users can access application
- ✅ No critical errors

This branch strategy ensures that all changes are thoroughly tested in development before being deployed to production, minimizing risks and ensuring a stable application. 