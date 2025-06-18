# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Copy wheels and requirements
COPY wheels/ ./wheels/
COPY requirements.txt .
COPY web/backend/requirements.txt ./web/backend/

# Install CARLA from wheel file
RUN pip install --no-cache-dir wheels/carla-0.10.0-cp311-cp311-linux_x86_64.whl

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r web/backend/requirements.txt

# Copy frontend files and install dependencies
COPY web/frontend/package*.json ./web/frontend/
RUN cd web/frontend && npm install

# Copy config files
COPY config/simulation.yaml /app/config/

# Copy the rest of the application
COPY . .

# Build frontend
RUN cd web/frontend && npm run build

# Install the package in development mode
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Expose ports
EXPOSE 3000 8000

# Create start script
RUN echo '#!/bin/bash\n\
cd /app/web/frontend && npm start & \n\
cd /app/web/backend && uvicorn main:app --host 0.0.0.0 --port 8000 & \n\
carla-simulator-client\n\
wait' > /app/start.sh && chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"] 