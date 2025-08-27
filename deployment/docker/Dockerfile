# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies including CARLA wheel
COPY requirements/requirements-docker.txt ./requirements-docker.txt
COPY deployment/wheels/ ./wheels/
RUN pip install --no-cache-dir -r requirements-docker.txt

# Build frontend
COPY web/frontend/package*.json web/frontend/craco.config.js ./web/frontend/
COPY web/frontend/src/ ./web/frontend/src/
COPY web/frontend/public/ ./web/frontend/public/
WORKDIR /app/web/frontend
RUN npm install --production=true && npm run build

# Final stage
FROM python:3.11-slim

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    dos2unix \
    fonts-dejavu-core \
    libfreetype6 \
    libgcc-s1 \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    libsm6 \
    libsdl2-2.0-0 \
    libsdl2-image-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libstdc++6 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    lsof \
    procps \
    && rm -rf /var/lib/apt/lists/*

ARG DOCKER_IMAGE_TAG
ARG VERSION
ARG BUILD_TIME

ENV DOCKER_IMAGE_TAG=$DOCKER_IMAGE_TAG \
    VERSION=$VERSION \
    BUILD_TIME=$BUILD_TIME

WORKDIR /app

# Copy Python packages from builder (including CARLA)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy built frontend
COPY --from=builder /app/web/frontend/build ./web/frontend/build

# Copy application code
COPY carla_simulator/ ./carla_simulator/
COPY web/backend/ ./web/backend/
COPY pyproject.toml README.md ./

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports

# Set environment variables
ENV PYTHONPATH=/app \
    REACT_APP_API_URL=http://localhost:8000 \
    DATABASE_URL=postgresql://postgres:postgres@193.16.126.186:5432/carla_simulator \
    LOG_LEVEL=INFO \
    DEBUG=true \
    TESTING=false \
    CONTAINER_ENV=true \
    WEB_MODE=true \
    SDL_VIDEODRIVER=dummy \
    SDL_AUDIODRIVER=dummy \
    CARLA_POOL_MODE=docker

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
