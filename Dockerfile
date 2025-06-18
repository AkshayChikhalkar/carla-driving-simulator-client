# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels and requirements
COPY wheels/ ./wheels/
COPY requirements.txt .

# Install CARLA from wheel file
RUN pip install --no-cache-dir wheels/carla-0.10.0-cp311-cp311-linux_x86_64.whl

# Install other Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["carla-simulator-client"] 