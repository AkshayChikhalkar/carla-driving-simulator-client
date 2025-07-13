# Staging Environment

This document describes the staging environment for the CARLA Driving Simulator Client, which serves as a pre-production testing environment.

## 🎯 **Staging Environment Overview**

The staging environment is designed to mirror production conditions while providing additional testing and monitoring capabilities:

- **Purpose**: Pre-production testing and validation
- **Environment**: Production-like with enhanced monitoring
- **Ports**: Different from production to avoid conflicts
- **Database**: Separate staging database
- **Monitoring**: Full monitoring stack included

## 🏗️ **Staging Architecture**

### Services
- **Backend**: FastAPI application (Port 8001)
- **Frontend**: React application (Port 3001)
- **Database**: PostgreSQL (Port 5433)
- **Prometheus**: Metrics collection (Port 9091)
- **Grafana**: Dashboards (Port 3002)
- **Loki**: Log aggregation (Port 3101)
- **Postman**: API testing
- **K6**: Load testing

### Port Mapping
```
Service        Internal    External    Purpose
Backend        8000        8001        API endpoints
Frontend       3000        3001        Web interface
Database       5432        5433        Data storage
Prometheus     9090        9091        Metrics
Grafana        3000        3002        Dashboards
Loki           3100        3101        Logs
```

## 🚀 **Quick Start**

### Start Staging Environment
```bash
# Start staging environment
./scripts/run-separate.sh staging

# Run comprehensive tests
./scripts/test-staging-setup.sh
```

### Access Staging Services
```bash
# Frontend
http://localhost:3001

# Backend API
http://localhost:8001

# API Documentation
http://localhost:8001/docs

# Prometheus
http://localhost:9091

# Grafana
http://localhost:3002

# Loki
http://localhost:3101
```

## 🧪 **Staging Testing**

### Automated Testing
The staging environment includes comprehensive automated testing:

1. **Prerequisites Check**
   - Docker and Docker Compose availability
   - Port conflict detection
   - Configuration validation

2. **Service Testing**
   - Container startup verification
   - Health check validation
   - Endpoint responsiveness

3. **Performance Testing**
   - API response time measurement
   - Load testing with multiple users
   - Resource usage monitoring

4. **Integration Testing**
   - API endpoint validation
   - Database connectivity
   - Frontend-backend communication

5. **Security Testing**
   - Sensitive endpoint protection
   - Network isolation verification
   - Access control validation

### Manual Testing
```bash
# Test API endpoints
curl http://localhost:8001/api/scenarios
curl http://localhost:8001/api/version
curl http://localhost:8001/health

# Test frontend
curl http://localhost:3001
curl http://localhost:3001/version.txt

# Test monitoring
curl http://localhost:9091
curl http://localhost:3002
curl http://localhost:3101
```

## 📊 **Monitoring and Observability**

### Metrics Collection
- **Prometheus**: Collects application and system metrics
- **Grafana**: Visualizes metrics and performance data
- **Loki**: Aggregates and queries application logs

### Key Metrics
- Container health and resource usage
- API response times and error rates
- Database performance and connections
- Frontend load times and user experience

### Dashboards
- **Application Overview**: General application health
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Error rates and types
- **Resource Usage**: CPU, memory, and disk usage

## 🔧 **Configuration**

### Environment Variables
```bash
# Staging-specific variables
VERSION=staging
ENVIRONMENT=staging
DATABASE_URL=postgresql://postgres:postgres@database:5432/carla_simulator_staging
LOG_LEVEL=INFO
DEBUG=false
TESTING=false
```

### Database Configuration
- **Database**: `carla_simulator_staging`
- **User**: `postgres`
- **Password**: `postgres`
- **Port**: `5433`

### Monitoring Configuration
- **Retention**: 7 days (shorter than production)
- **Log Level**: INFO
- **Debug Mode**: Disabled
- **Testing Mode**: Disabled

## 🧪 **Testing Tools**

### Postman Integration
- Automated API testing
- Collection validation
- Performance testing
- Report generation

### K6 Load Testing
- Simulated user load
- Performance benchmarking
- Stress testing
- Scalability validation

### Custom Test Scripts
- End-to-end testing
- Integration validation
- Security verification
- Performance assessment

## 🔄 **Staging Workflow**

### Development → Staging → Production
```
Development → Staging → Production
     ↓           ↓         ↓
   Features   Testing    Release
   & Tests    & Validation
```

### Staging Process
1. **Merge from Development**
   ```bash
   git checkout staging
   git merge development
   ```

2. **Deploy to Staging**
   ```bash
   ./scripts/run-separate.sh staging
   ```

3. **Run Comprehensive Tests**
   ```bash
   ./scripts/test-staging-setup.sh
   ```

4. **Validate Results**
   - Check all tests pass
   - Verify performance metrics
   - Validate security tests
   - Review monitoring data

5. **Approve for Production**
   - Manual review of staging results
   - Performance validation
   - Security verification
   - User acceptance testing

## 📈 **Performance Benchmarks**

### Expected Performance
- **API Response Time**: < 1 second
- **Frontend Load Time**: < 3 seconds
- **Database Queries**: < 500ms
- **Container Startup**: < 30 seconds

### Load Testing Scenarios
- **Light Load**: 5 concurrent users
- **Medium Load**: 10 concurrent users
- **Heavy Load**: 20 concurrent users
- **Stress Test**: 50 concurrent users

## 🔒 **Security Considerations**

### Staging Security
- **Network Isolation**: Separate from production
- **Data Isolation**: Separate database
- **Access Control**: Limited access
- **Monitoring**: Security event tracking

### Security Testing
- **Endpoint Protection**: Verify sensitive endpoints
- **Authentication**: Test access controls
- **Data Protection**: Validate data isolation
- **Network Security**: Verify network isolation

## 🐛 **Troubleshooting**

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker-compose -f docker/compose/docker-compose-full-staging.yml logs

# Check container status
docker-compose -f docker/compose/docker-compose-full-staging.yml ps

# Restart containers
docker-compose -f docker/compose/docker-compose-full-staging.yml restart
```

#### Port Conflicts
```bash
# Check what's using the ports
netstat -tuln | grep :3001
netstat -tuln | grep :8001
netstat -tuln | grep :5433

# Kill processes using ports
sudo kill -9 $(lsof -t -i:3001)
sudo kill -9 $(lsof -t -i:8001)
sudo kill -9 $(lsof -t -i:5433)
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Check container logs
docker-compose -f docker/compose/docker-compose-full-staging.yml logs -f backend

# Monitor performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8001/api/scenarios
```

#### Database Issues
```bash
# Check database logs
docker-compose -f docker/compose/docker-compose-full-staging.yml logs database

# Reset database
docker-compose -f docker/compose/docker-compose-full-staging.yml down -v
docker-compose -f docker/compose/docker-compose-full-staging.yml up -d
```

## 📝 **Best Practices**

### Staging Environment Management
1. **Regular Updates**: Keep staging in sync with development
2. **Data Management**: Use realistic test data
3. **Performance Monitoring**: Track key metrics
4. **Security Validation**: Regular security testing
5. **Documentation**: Keep staging documentation updated

### Testing Strategy
1. **Automated Testing**: Run all automated tests
2. **Manual Testing**: Perform manual validation
3. **Performance Testing**: Regular performance benchmarks
4. **Security Testing**: Regular security validation
5. **User Testing**: Stakeholder validation

### Monitoring Strategy
1. **Real-time Monitoring**: Monitor staging continuously
2. **Alerting**: Set up appropriate alerts
3. **Logging**: Comprehensive logging
4. **Metrics**: Track key performance indicators
5. **Reporting**: Regular performance reports

## 🎯 **Success Criteria**

### Staging Success
- ✅ All automated tests pass
- ✅ Performance benchmarks met
- ✅ Security tests pass
- ✅ Integration tests successful
- ✅ Monitoring working correctly
- ✅ No critical issues found

### Production Readiness
- ✅ Staging validation complete
- ✅ Performance acceptable
- ✅ Security verified
- ✅ Documentation updated
- ✅ Stakeholder approval
- ✅ Rollback plan ready

This staging environment provides a robust pre-production testing platform that ensures high-quality releases to production. 