# Frontend Dockerfile for CARLA Driving Simulator Client
FROM node:18-alpine AS builder

# Build arguments
ARG VERSION=latest
ARG BUILD_TIME

# Set work directory
WORKDIR /app

# Copy package files
COPY web/frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY web/frontend/ ./

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Create version file for display
RUN echo "${VERSION}" > /usr/share/nginx/html/version.txt

# Set environment variables for production
ENV FRONTEND_PORT=3000

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 