FROM python:3.11-slim

# Install system and Node.js dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    dos2unix \
    fonts-dejavu-core \
    libfreetype6 \
    libgcc-s1 \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
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
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

ARG DOCKER_IMAGE_TAG
ARG VERSION
ARG BUILD_TIME

ENV DOCKER_IMAGE_TAG=$DOCKER_IMAGE_TAG \
    VERSION=$VERSION \
    BUILD_TIME=$BUILD_TIME

WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports

# Copy requirements and wheels first for better layer caching
COPY requirements/requirements-docker.txt ./requirements-docker.txt
COPY deployment/wheels/ ./wheels/
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy backend and source code
COPY carla_simulator/ ./carla_simulator/
COPY web/backend/ ./web/backend/
COPY pyproject.toml README.md ./
RUN pip install -e .

# Copy frontend source
COPY web/frontend/package*.json web/frontend/craco.config.js ./web/frontend/
COPY web/frontend/src/ ./web/frontend/src/
COPY web/frontend/public/ ./web/frontend/public/

# Install frontend dependencies
WORKDIR /app/web/frontend
RUN npm install --production=true && npm run build

WORKDIR /app

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
