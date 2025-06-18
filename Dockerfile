# Use Python 3.11 as base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CARLA wheel file and install
COPY carla-0.9.14-cp311-cp311-linux_x86_64.whl .
RUN pip install --no-cache-dir carla-0.9.14-cp311-cp311-linux_x86_64.whl

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Copy default config if it doesn't exist
RUN if [ ! -f /app/config/simulation.yaml ]; then \
    cp /app/config/simulation.yaml.example /app/config/simulation.yaml; \
    fi

# Install the package in development mode
RUN pip install -e .

# Expose ports
EXPOSE 3000 8000 2000-2002

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0

# Create start script
RUN echo '#!/bin/bash\n\
cd /app/web/frontend && npm start & \
cd /app/web/backend && uvicorn main:app --host 0.0.0.0 --port 8000 & \
carla-simulator-client\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"] 