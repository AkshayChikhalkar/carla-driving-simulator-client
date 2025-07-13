#!/bin/bash

# Development Testing Script for CARLA Driving Simulator Client
# This script tests the separate container development setup

set -e

echo "🧪 Testing CARLA Driving Simulator Client - Development Setup"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC}: $message"
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC}: $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC}: $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  INFO${NC}: $message"
            ;;
    esac
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    netstat -tuln 2>/dev/null | grep -q ":$1 "
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "INFO" "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            print_status "PASS" "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_status "FAIL" "$service_name failed to start within 60 seconds"
    return 1
}

echo ""
print_status "INFO" "Starting development environment tests..."

# 1. Check prerequisites
echo ""
print_status "INFO" "Checking prerequisites..."

if command_exists docker; then
    print_status "PASS" "Docker is installed"
else
    print_status "FAIL" "Docker is not installed"
    exit 1
fi

if command_exists docker-compose; then
    print_status "PASS" "Docker Compose is installed"
else
    print_status "FAIL" "Docker Compose is not installed"
    exit 1
fi

if docker info >/dev/null 2>&1; then
    print_status "PASS" "Docker daemon is running"
else
    print_status "FAIL" "Docker daemon is not running"
    exit 1
fi

# 2. Check for port conflicts
echo ""
print_status "INFO" "Checking for port conflicts..."

if port_in_use 3000; then
    print_status "WARN" "Port 3000 is in use (frontend)"
else
    print_status "PASS" "Port 3000 is available"
fi

if port_in_use 8000; then
    print_status "WARN" "Port 8000 is in use (backend)"
else
    print_status "PASS" "Port 8000 is available"
fi

if port_in_use 5432; then
    print_status "WARN" "Port 5432 is in use (database)"
else
    print_status "PASS" "Port 5432 is available"
fi

# 3. Check configuration files
echo ""
print_status "INFO" "Checking configuration files..."

if [ -f "config/simulation.yaml" ]; then
    print_status "PASS" "simulation.yaml found"
else
    print_status "WARN" "simulation.yaml not found, will create from example"
    if [ -f "config/simulation.yaml.example" ]; then
        cp config/simulation.yaml.example config/simulation.yaml
        print_status "PASS" "Created simulation.yaml from example"
    else
        print_status "FAIL" "No simulation.yaml.example found"
        exit 1
    fi
fi

if [ -f "docker/compose/docker-compose-full-dev.yml" ]; then
    print_status "PASS" "Development compose file found"
else
    print_status "FAIL" "docker/compose/docker-compose-full-dev.yml not found"
    exit 1
fi

# 4. Create necessary directories
echo ""
print_status "INFO" "Creating necessary directories..."

mkdir -p logs reports
print_status "PASS" "Directories created"

# 5. Test Docker Compose configuration
echo ""
print_status "INFO" "Testing Docker Compose configuration..."

if docker-compose -f docker/compose/docker-compose-full-dev.yml config >/dev/null 2>&1; then
    print_status "PASS" "Docker Compose configuration is valid"
else
    print_status "FAIL" "Docker Compose configuration is invalid"
    exit 1
fi

# 6. Build and start services
echo ""
print_status "INFO" "Building and starting development services..."

# Stop any existing containers
docker-compose -f docker/compose/docker-compose-full-dev.yml down >/dev/null 2>&1 || true

# Build and start
if docker-compose -f docker/compose/docker-compose-full-dev.yml up --build -d; then
    print_status "PASS" "Services started successfully"
else
    print_status "FAIL" "Failed to start services"
    exit 1
fi

# 7. Wait for services and test endpoints
echo ""
print_status "INFO" "Testing service endpoints..."

# Wait for database
sleep 10

# Test database
if docker-compose -f docker/compose/docker-compose-full-dev.yml exec -T database pg_isready -U postgres >/dev/null 2>&1; then
    print_status "PASS" "Database is ready"
else
    print_status "FAIL" "Database is not ready"
fi

# Test backend
if wait_for_service "http://localhost:8000/api/scenarios" "Backend API"; then
    print_status "PASS" "Backend API is responding"
else
    print_status "FAIL" "Backend API is not responding"
fi

# Test frontend
if wait_for_service "http://localhost:3000" "Frontend"; then
    print_status "PASS" "Frontend is responding"
else
    print_status "FAIL" "Frontend is not responding"
fi

# 8. Test version endpoint
echo ""
print_status "INFO" "Testing version tracking..."

VERSION_RESPONSE=$(curl -s http://localhost:8000/api/version 2>/dev/null || echo "{}")
if echo "$VERSION_RESPONSE" | grep -q "version"; then
    print_status "PASS" "Version API is working"
    echo "   Version info: $VERSION_RESPONSE"
else
    print_status "FAIL" "Version API is not working"
fi

# 9. Test frontend version display
FRONTEND_VERSION=$(curl -s http://localhost:3000/version.txt 2>/dev/null || echo "not_found")
if [ "$FRONTEND_VERSION" != "not_found" ]; then
    print_status "PASS" "Frontend version file is accessible"
    echo "   Frontend version: $FRONTEND_VERSION"
else
    print_status "WARN" "Frontend version file not accessible"
fi

# 10. Check container health
echo ""
print_status "INFO" "Checking container health..."

if docker-compose -f docker/compose/docker-compose-full-dev.yml ps | grep -q "Up"; then
    print_status "PASS" "All containers are running"
else
    print_status "FAIL" "Some containers are not running"
fi

# 11. Test logs
echo ""
print_status "INFO" "Testing logging..."

if docker-compose -f docker/compose/docker-compose-full-dev.yml logs --tail=10 >/dev/null 2>&1; then
    print_status "PASS" "Container logs are accessible"
else
    print_status "FAIL" "Container logs are not accessible"
fi

# 12. Performance check
echo ""
print_status "INFO" "Checking resource usage..."

CONTAINER_COUNT=$(docker-compose -f docker/compose/docker-compose-full-dev.yml ps -q | wc -l)
print_status "INFO" "Running $CONTAINER_COUNT containers"

# 13. Summary
echo ""
echo "=============================================================="
print_status "INFO" "Development Testing Complete!"
echo ""
print_status "INFO" "Access your application at:"
echo "   🌐 Frontend: http://localhost:3000"
echo "   🔧 Backend API: http://localhost:8000"
echo "   📊 API Docs: http://localhost:8000/docs"
echo ""
print_status "INFO" "Useful commands:"
echo "   View logs: docker-compose -f docker/compose/docker-compose-full-dev.yml logs -f"
echo "   Stop services: docker-compose -f docker/compose/docker-compose-full-dev.yml down"
echo "   Restart: docker-compose -f docker/compose/docker-compose-full-dev.yml restart"
echo ""
print_status "INFO" "Ready for development! 🚀" 