# Multi-stage build for better optimization
FROM node:18-alpine AS frontend-builder

# Install frontend dependencies
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci --only=production

# Copy frontend source and build
COPY web/frontend/ ./
RUN npm run build

# Python runtime stage
FROM python:3.11-slim

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    dos2unix \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    lsof \
    procps \
    libstdc++6 \
    libgcc1 \
    libx11-6 \
    libpthread-stubs0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy wheels directory first (needed for CARLA wheel)
COPY wheels/ ./wheels/

# Copy Python requirements first for better caching
COPY requirements-docker.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY web/backend/ ./web/backend/
COPY config/ ./config/
COPY run.py ./
COPY setup.py ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/build ./web/frontend/build

# Create necessary directories
RUN mkdir -p logs reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run.py"]
