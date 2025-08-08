FROM python:3.11-slim

# Install system and Node.js dependencies
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev curl dos2unix \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get update && apt-get install -y \
    lsof \
    procps \
    libstdc++6 \
    libgcc1 \
    libx11-6 \
    libpthread-stubs0-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

ARG DOCKER_IMAGE_TAG
ARG VERSION
ARG BUILD_TIME

ENV DOCKER_IMAGE_TAG=$DOCKER_IMAGE_TAG
ENV VERSION=$VERSION
ENV BUILD_TIME=$BUILD_TIME

# Create version file for application access
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports

# Copy requirements and wheels first for better layer caching
COPY requirements/requirements-docker.txt ./
COPY deployment/wheels/ ./wheels/
RUN pip install --no-cache-dir -r requirements-docker.txt \
    && pip install --no-cache-dir ./wheels/carla-0.10.0-cp311-cp311-linux_x86_64.whl

# Copy essential configuration
COPY config/simulation.yaml /app/config/

# Copy backend and source code
COPY carla_simulator/ ./carla_simulator/
COPY web/backend/ ./web/backend/
COPY setup.py pyproject.toml README.md ./
RUN pip install -e .

# Copy frontend source
COPY web/frontend/package*.json web/frontend/craco.config.js ./web/frontend/
COPY web/frontend/src/ ./web/frontend/src/
COPY web/frontend/public/ ./web/frontend/public/

# Install frontend dependencies
WORKDIR /app/web/frontend
RUN npm install --production=true
RUN npm run build

WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app \
    REACT_APP_API_URL=http://localhost:8000 \
    DATABASE_URL=postgresql://postgres:postgres@193.16.126.186:5432/carla_simulator \
    LOG_LEVEL=INFO \
    DEBUG=true \
    TESTING=false \
    # Container-specific environment variables for vehicle spawning fixes
    CONTAINER_ENV=true \
    WEB_MODE=true
# Copy start script and fix line endings
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
