#!/bin/bash
set -e

echo "Starting Carla Driving Simulator Client..."

# Create necessary directories if they don't exist
mkdir -p /app/config /app/logs /app/reports /app/postgres-data

echo "Checking configuration..."
if [ ! -f /app/config/simulation.yaml ]; then
    echo "ERROR: Config file not found at /app/config/simulation.yaml!"
    exit 1
fi

echo "Starting backend service..."
cd /app/web/backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 5

echo "Starting frontend service..."
cd /app/web/frontend && npm start &
FRONTEND_PID=$!

echo "Services started. Backend PID: $BACKEND_PID, Frontend PID: $FRONTEND_PID"

# Wait for either process to exit
wait 