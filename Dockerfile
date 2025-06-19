# Build stage for frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci --only=production

COPY web/frontend/ ./
RUN npm run build

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js runtime
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Copy built frontend from builder
COPY --from=frontend-builder /app/frontend/build ./web/frontend/build

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/reports

# Copy default config if it doesn't exist
RUN if [ ! -f /app/config/simulation.yaml ]; then \
    cp /app/config/simulation.yaml; \
    fi

# Install Python dependencies, CARLA wheel, and the package
COPY requirements-docker.txt .
COPY wheels/ ./wheels/
RUN pip install --no-cache-dir -r requirements-docker.txt
RUN pip install --no-cache-dir ./wheels/carla-0.10.0-cp311-cp311-linux_x86_64.whl
RUN pip install .

# Expose ports
EXPOSE 3000 8000 2000-2002

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH
ENV HOST=0.0.0.0
ENV REACT_APP_API_URL=http://localhost:8000
ENV WDS_SOCKET_HOST=0.0.0.0
ENV WDS_SOCKET_PORT=3000

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p /home/appuser && chown -R appuser:appuser /home/appuser
ENV HOME=/home/appuser
ENV NPM_CONFIG_CACHE=/app/.npm
RUN chown -R appuser:appuser /app
USER appuser

# Create start script
RUN echo '#!/bin/bash\n\
echo "Starting CARLA Simulator Client..."\n\
echo "Starting backend..."\n\
cd /app/web/backend && python main.py &\n\
BACKEND_PID=$!\n\
echo "Backend started with PID: $BACKEND_PID"\n\
\n\
# Wait for backend to be ready\n\
echo "Waiting for backend to be ready..."\n\
max_retries=30\n\
count=0\n\
while ! curl -s http://localhost:8000/health > /dev/null; do\n\
    sleep 2\n\
    count=$((count + 1))\n\
    if [ $count -eq $max_retries ]; then\n\
        echo "Backend failed to start after 60 seconds"\n\
        exit 1\n\
    fi\n\
done\n\
echo "Backend is ready"\n\
\n\
echo "Starting frontend..."\n\
cd /app/web/frontend && npx serve -s build -l 3000 &\n\
FRONTEND_PID=$!\n\
echo "Frontend started with PID: $FRONTEND_PID"\n\
echo "Services started. Frontend available at http://localhost:3000"\n\
echo "Backend API available at http://localhost:8000"\n\
echo "Press Ctrl+C to stop all services"\n\
wait\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set the entrypoint
ENTRYPOINT ["/app/start.sh"] 