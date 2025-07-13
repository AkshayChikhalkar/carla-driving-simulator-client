# 🚀 CI/CD Workflow Guide

This document explains the new organized CI/CD workflow structure for the CARLA Driving Simulator Client project.

## 📋 **Workflow Overview**

### **🏗️ Build Workflows**
- **`build-backend.yml`**: Backend-only builds and tests
- **`build-frontend.yml`**: Frontend-only builds and tests
- **`build-docs.yml`**: Documentation generation and builds

### **🚀 Deployment Workflows**
- **`deploy-dev.yml`**: Development environment deployment
- **`deploy-staging.yml`**: Staging environment deployment
- **`deploy-prod.yml`**: Production environment deployment

### **🧪 Testing Workflows**
- **`test-integration.yml`**: Integration testing across all components

### **📦 Release Workflows**
- **`release.yml`**: Release management and GitHub releases

## 🎯 **Workflow Triggers**

### **Build Workflows**
```yaml
# Backend triggers on:
- src/** changes
- web/backend/** changes
- requirements*.txt changes
- setup.py changes
- run.py changes
- config/** changes
- docker/backend/** changes

# Frontend triggers on:
- web/frontend/** changes
- package.json changes
- package-lock.json changes
- docker/frontend/** changes

# Documentation triggers on:
- docs/** changes
- README.md changes
- CHANGELOG.md changes
```

### **Deployment Workflows**
```yaml
# Development triggers on:
- development branch push
- docker/compose/docker-compose-full-dev.yml changes
- scripts/docker/run-dev.sh changes

# Staging triggers on:
- staging branch push
- docker/compose/docker-compose-full-staging.yml changes
- scripts/docker/run-staging.sh changes

# Production triggers on:
- master branch push
- docker/compose/docker-compose-full-prod.yml changes
- scripts/docker/run-prod.sh changes
```

## 🔄 **Workflow Benefits**

### **🚀 Performance Benefits**
- **Parallel Execution**: Backend and frontend build simultaneously
- **Selective Building**: Only build components that changed
- **Faster Feedback**: Get results quicker for each component
- **Resource Efficiency**: Use GitHub Actions minutes more efficiently

### **🔧 Development Benefits**
- **Independent Testing**: Test backend/frontend separately
- **Easier Debugging**: Isolate issues to specific components
- **Better Monitoring**: Track each component's health
- **Flexible Deployment**: Deploy components independently

### **📊 Monitoring Benefits**
- **Granular Status**: See which component failed
- **Better Notifications**: Get alerts for specific components
- **Easier Rollbacks**: Rollback specific components
- **Performance Tracking**: Monitor each component's build time

## 📁 **Workflow Structure**

```
.github/workflows/
├── 🏗️ build-backend.yml          # Backend builds only
├── 🎨 build-frontend.yml         # Frontend builds only
├── 📚 build-docs.yml             # Documentation builds
├── 🚀 deploy-dev.yml             # Development deployment
├── 🧪 deploy-staging.yml         # Staging deployment
├── 🏭 deploy-prod.yml            # Production deployment
├── 🧪 test-integration.yml       # Integration testing
└── 📦 release.yml                # Release management
```

## 🎯 **Usage Examples**

### **Manual Workflow Triggers**
```bash
# Trigger development deployment
gh workflow run deploy-dev.yml

# Trigger staging deployment
gh workflow run deploy-staging.yml

# Trigger production deployment
gh workflow run deploy-prod.yml

# Trigger release creation
gh workflow run release.yml --field version=1.2.3
```

### **Branch Strategy**
```bash
# Development workflow
git checkout development
git push origin development  # Triggers deploy-dev.yml

# Staging workflow
git checkout staging
git merge development
git push origin staging     # Triggers deploy-staging.yml

# Production workflow
git checkout master
git merge staging
git push origin master      # Triggers deploy-prod.yml
```

## 🔧 **Configuration Requirements**

### **Repository Secrets**
```yaml
DOCKERHUB_USERNAME: "your-dockerhub-username"
DOCKERHUB_TOKEN: "your-dockerhub-token"
PYPI_TOKEN: "your-pypi-token"
```

### **Environment Variables**
```yaml
DOCKER_IMAGE: "akshaychikhalkar/carla-driving-simulator-client"
```

### **Branch Protection Rules**
- **development**: Require status checks to pass
- **staging**: Require status checks to pass
- **master**: Require status checks to pass, require reviews

## 📊 **Monitoring and Notifications**

### **Workflow Status**
- **Green**: All tests passed, deployment successful
- **Yellow**: Some tests failed, deployment partial
- **Red**: Critical failures, deployment failed

### **Notification Channels**
- **GitHub**: Built-in notifications
- **Slack/Discord**: Custom webhooks (if configured)
- **Email**: Repository notifications

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Build Failures**
```bash
# Check build logs
gh run list --workflow=build-backend.yml
gh run view --log

# Re-run failed workflow
gh run rerun <run-id>
```

#### **Deployment Failures**
```bash
# Check deployment logs
gh run list --workflow=deploy-prod.yml
gh run view --log

# Rollback deployment
git revert HEAD
git push origin master
```

#### **Test Failures**
```bash
# Run tests locally
./scripts/test-dev-setup.sh

# Check specific component
docker-compose -f docker/compose/docker-compose-full-dev.yml logs backend
```

## 📈 **Performance Metrics**

### **Build Times**
- **Backend**: ~5-10 minutes
- **Frontend**: ~3-5 minutes
- **Documentation**: ~2-3 minutes
- **Integration Tests**: ~8-12 minutes

### **Deployment Times**
- **Development**: ~3-5 minutes
- **Staging**: ~5-8 minutes
- **Production**: ~8-12 minutes

## 🎯 **Best Practices**

### **✅ Do's**
- Use feature branches for development
- Test locally before pushing
- Monitor workflow status regularly
- Keep secrets updated
- Use semantic versioning

### **❌ Don'ts**
- Push directly to master
- Skip testing
- Ignore build failures
- Use outdated secrets
- Break semantic versioning

## 🔄 **Migration from Monolithic**

### **Step 1: Update References**
```bash
# Update any scripts that reference old workflows
sed -i 's/build-publish-release.yml/build-backend.yml/g' scripts/*
```

### **Step 2: Test New Workflows**
```bash
# Test each workflow individually
gh workflow run build-backend.yml
gh workflow run build-frontend.yml
gh workflow run deploy-dev.yml
```

### **Step 3: Monitor Performance**
```bash
# Check workflow performance
gh run list --limit=10
```

## 📞 **Support**

### **Getting Help**
- Check workflow logs for detailed error messages
- Review this guide for common solutions
- Create GitHub issues for persistent problems
- Contact the development team for critical issues

---

*This workflow structure provides maximum flexibility, performance, and maintainability for the CARLA Driving Simulator Client project.* 