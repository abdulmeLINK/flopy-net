FROM python:3.9-slim

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="Federated Learning Client for flopynet System - Trains models on local data"

WORKDIR /app

# Copy requirements first for better caching
COPY docker/requirements/fl-client-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src

# Copy entrypoint script
COPY docker/entrypoints/entrypoint-fl-client.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV CLIENT_PORT=8081
ENV CONFIG_DIR=/app/config
ENV MODELS_DIR=/app/models
ENV LOGS_DIR=/app/logs
ENV DATA_DIR=/app/data

# Create necessary directories
RUN mkdir -p /app/config /app/models /app/logs /app/data

# Set default configuration
ENV LOG_LEVEL=INFO
ENV CLIENT_ID=client-1
ENV SERVICE_ID=1
ENV SERVICE_TYPE=fl-client
ENV SERVER_HOST=fl-server
ENV POLICY_ENGINE_HOST=policy-engine
ENV USE_STATIC_IP=true
ENV FL_CLIENT_IP=192.168.100.101
ENV DOCKER_COMPOSE_ENV=true

# Install curl and networking tools
RUN apt-get update && apt-get install -y curl net-tools iputils-ping iproute2 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose the client port
EXPOSE 8081

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${CLIENT_PORT}/health || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 