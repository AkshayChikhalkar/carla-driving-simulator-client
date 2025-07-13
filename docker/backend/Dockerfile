# Backend Dockerfile for CARLA Driving Simulator Client
FROM python:3.11-slim

# Build arguments
ARG VERSION=latest
ARG BUILD_TIME

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV VERSION=${VERSION}
ENV BUILD_TIME=${BUILD_TIME}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl dos2unix \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-dev \
    lsof \
    procps \
    libstdc++6 \
    libgcc1 \
    libx11-6 \
    libpthread-stubs0-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports

# Copy requirements first for better caching
COPY requirements-docker.txt .
COPY wheels/ ./wheels/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ./wheels/carla-0.10.0-cp311-cp311-linux_x86_64.whl && \
    pip install --no-cache-dir -r requirements-docker.txt

# Copy essential configuration
COPY config/simulation.yaml /app/config/

# Copy backend source code
COPY src/ ./src/
COPY web/backend/ ./web/backend/
COPY setup.py run.py VERSION README.md ./
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app \
    HOST=0.0.0.0 \
    CARLA_HOST=carla-server \
    CARLA_PORT=2000 \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=8000 \
    LOG_LEVEL=INFO \
    DEBUG=false \
    TESTING=false \
    CONTAINER_ENV=true \
    WEB_MODE=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/scenarios || exit 1

# Default command
CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"] 