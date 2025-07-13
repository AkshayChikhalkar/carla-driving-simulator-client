# Development Workflow

This document outlines the development workflow for the CARLA Driving Simulator Client, focusing on testing in development before pushing to production.

## 🎯 **Development Strategy**

### Phase 1: Development Testing ✅
- Test all new features in development environment
- Verify separate container architecture
- Ensure version tracking works correctly
- Test automated builds and deployments

### Phase 2: Production Deployment 🚀
- Push tested changes to production branch
- Deploy with confidence using proven setup
- Monitor production performance

## 🧪 **Testing Checklist**

### Pre-Development Testing
- [ ] Docker and Docker Compose installed
- [ ] Ports 3000, 8000, 5432 available
- [ ] Configuration files present
- [ ] Git repository clean

### Development Environment Testing
- [ ] Run comprehensive test script
- [ ] Verify all containers start correctly
- [ ] Test API endpoints
- [ ] Verify version tracking
- [ ] Check frontend functionality
- [ ] Test database connectivity
- [ ] Verify logging works
- [ ] Test health checks

### Feature Testing
- [ ] Test new features in development
- [ ] Verify backward compatibility
- [ ] Test error handling
- [ ] Performance testing
- [ ] Security testing

## 🚀 **Development Commands**

### Quick Start Development
```bash
# Start development environment
./scripts/run-separate.sh dev

# Run comprehensive tests
./scripts/test-dev-setup.sh

# View logs
docker-compose -f docker/compose/docker-compose-full-dev.yml logs -f

# Stop development environment
docker-compose -f docker/compose/docker-compose-full-dev.yml down
```

### Manual Testing
```bash
# Test backend API
curl http://localhost:8000/api/scenarios

# Test version endpoint
curl http://localhost:8000/api/version

# Test frontend
curl http://localhost:3000

# Check container status
docker-compose -f docker-compose.separate.dev.yml ps
```

### Development Debugging
```bash
# Access backend container
docker-compose -f docker/compose/docker-compose-full-dev.yml exec backend bash

# Access frontend container
docker-compose -f docker/compose/docker-compose-full-dev.yml exec frontend sh

# Access database
docker-compose -f docker/compose/docker-compose-full-dev.yml exec database psql -U postgres
```

## 📊 **Testing Results Tracking**

### Automated Tests
The `test-dev-setup.sh` script performs:
- ✅ Prerequisites check
- ✅ Port conflict detection
- ✅ Configuration validation
- ✅ Docker Compose validation
- ✅ Service startup testing
- ✅ Endpoint health checks
- ✅ Version tracking verification
- ✅ Container health monitoring
- ✅ Logging verification
- ✅ Performance assessment

### Manual Tests
Additional manual testing should include:
- [ ] UI/UX testing
- [ ] Cross-browser compatibility
- [ ] Mobile responsiveness
- [ ] Load testing
- [ ] Security testing
- [ ] Integration testing

## 🔄 **Development Workflow Steps**

### 1. Setup Development Environment
```bash
# Clone repository
git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
cd carla-driving-simulator-client

# Run development tests
./scripts/test-dev-setup.sh
```

### 2. Make Changes
- Edit code in development environment
- Test changes locally
- Verify functionality

### 3. Test Changes
```bash
# Rebuild and test
docker-compose -f docker/compose/docker-compose-full-dev.yml up --build -d
./scripts/test-dev-setup.sh

# Run specific tests
curl http://localhost:8000/api/scenarios
curl http://localhost:3000
```

### 4. Commit and Push
```bash
# Commit changes
git add .
git commit -m "feat: add new feature"

# Push to development branch
git push origin development
```

### 5. CI/CD Testing
- GitHub Actions will run automatically
- Check build status in GitHub
- Verify Docker images build correctly
- Test change detection works

### 6. Production Deployment
```bash
# Merge to production branch
git checkout production
git merge development
git push origin production

# Deploy to production
./scripts/run-separate.sh
```

## 🐛 **Debugging Guide**

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker-compose -f docker/compose/docker-compose-full-dev.yml logs

# Check container status
docker-compose -f docker/compose/docker-compose-full-dev.yml ps

# Restart containers
docker-compose -f docker/compose/docker-compose-full-dev.yml restart
```

#### Port Conflicts
```bash
# Check what's using the port
netstat -tuln | grep :3000
netstat -tuln | grep :8000

# Kill process using port
sudo kill -9 $(lsof -t -i:3000)
```

#### Database Issues
```bash
# Check database logs
docker-compose -f docker/compose/docker-compose-full-dev.yml logs database

# Reset database
docker-compose -f docker/compose/docker-compose-full-dev.yml down -v
docker-compose -f docker/compose/docker-compose-full-dev.yml up -d
```

#### Version Display Issues
```bash
# Check version API
curl http://localhost:8000/api/version

# Check frontend version
curl http://localhost:3000/version.txt

# Rebuild with version
VERSION=test ./scripts/update_version.sh
```

## 📈 **Performance Monitoring**

### Development Metrics
- Container startup time
- API response times
- Memory usage
- CPU usage
- Network connectivity

### Monitoring Commands
```bash
# Check resource usage
docker stats

# Check container logs
docker-compose -f docker/compose/docker-compose-full-dev.yml logs -f

# Monitor specific service
docker-compose -f docker/compose/docker-compose-full-dev.yml logs -f backend
```

## 🔒 **Security Testing**

### Development Security Checklist
- [ ] No hardcoded secrets
- [ ] Environment variables properly set
- [ ] Network isolation working
- [ ] Health checks functional
- [ ] Logging doesn't expose sensitive data

## 📝 **Documentation Updates**

### Required Documentation
- [ ] Update README.md
- [ ] Update SEPARATE_CONTAINERS.md
- [ ] Update API documentation
- [ ] Update deployment guides
- [ ] Update troubleshooting guides

## 🚀 **Production Readiness Checklist**

Before pushing to production:

### Technical Requirements
- [ ] All tests pass
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Security reviewed
- [ ] Documentation updated

### Deployment Requirements
- [ ] Docker images built successfully
- [ ] Version tracking working
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Rollback plan ready

### Business Requirements
- [ ] Features meet requirements
- [ ] User acceptance testing complete
- [ ] Stakeholder approval
- [ ] Release notes prepared

## 🎯 **Success Criteria**

### Development Success
- ✅ All containers start successfully
- ✅ All endpoints respond correctly
- ✅ Version tracking works
- ✅ Logging is functional
- ✅ Health checks pass
- ✅ Performance is acceptable

### Production Success
- ✅ Zero-downtime deployment
- ✅ All services healthy
- ✅ Monitoring working
- ✅ Users can access application
- ✅ No critical errors in logs

## 📞 **Support and Escalation**

### Development Issues
1. Check logs: `docker-compose logs`
2. Restart services: `docker-compose restart`
3. Rebuild containers: `docker-compose up --build`
4. Check GitHub Issues for known problems

### Production Issues
1. Check monitoring dashboards
2. Review application logs
3. Check system resources
4. Contact development team
5. Consider rollback if necessary

This workflow ensures that all changes are thoroughly tested in development before being deployed to production, minimizing risks and ensuring a stable application. 