#!/bin/bash

# Script to run CARLA Driving Simulator Client in production mode
# Usage: ./scripts/docker/run-prod.sh [backend|frontend|full]

set -e

SERVICE=${1:-full}
COMPOSE_DIR="docker/compose"

echo "Starting CARLA Driving Simulator Client in production mode..."
echo "Service: $SERVICE"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "ERROR: docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create necessary directories
mkdir -p logs reports config

# Check if config file exists
if [ ! -f config/simulation.yaml ]; then
    echo "WARNING: config/simulation.yaml not found. Creating default config..."
    cp config/simulation.yaml.example config/simulation.yaml 2>/dev/null || {
        echo "ERROR: No example config found. Please create config/simulation.yaml manually."
        exit 1
    }
fi

# Choose compose file based on service
case $SERVICE in
    "backend")
        COMPOSE_FILE="$COMPOSE_DIR/docker-compose-backend-prod.yml"
        echo "Running backend only..."
        ;;
    "frontend")
        COMPOSE_FILE="$COMPOSE_DIR/docker-compose-frontend-prod.yml"
        echo "Running frontend only..."
        ;;
    "full"|*)
        COMPOSE_FILE="$COMPOSE_DIR/docker-compose-full-prod.yml"
        echo "Running full stack with monitoring..."
        ;;
esac

echo "Using compose file: $COMPOSE_FILE"

# Build and start services
echo "Building and starting services..."
docker-compose -f $COMPOSE_FILE up --build -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 15

# Check service health
echo "Checking service health..."
if docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    echo "✅ Services are running successfully!"
    echo ""
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8000"
    echo "🗄️  Database: localhost:5432"
    echo "📊 Grafana (if enabled): http://localhost:3001"
    echo "📈 Prometheus (if enabled): http://localhost:9090"
    echo ""
    echo "To view logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "To stop services: docker-compose -f $COMPOSE_FILE down"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "docker-compose -f $COMPOSE_FILE logs"
    exit 1
fi 