FROM python:3.9-slim

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="Federated Learning Server for flopynet System - Coordinates distributed training"

WORKDIR /app

# Copy requirements first for better caching
COPY docker/requirements/fl-server-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src

# Copy configuration files
COPY config /app/config

# Copy entrypoint script
COPY docker/entrypoints/entrypoint-fl-server.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV FL_SERVER_PORT=8080
ENV CONFIG_DIR=/app/config
ENV MODELS_DIR=/app/models
ENV LOGS_DIR=/app/logs
ENV DATA_DIR=/app/data
# Specify the application entry point
ENV FL_SERVER_ENTRYPOINT=/app/src/fl/server/fl_server.py

# Create necessary directories
RUN mkdir -p /app/config /app/models /app/logs /app/data

# Set default configuration
ENV LOG_LEVEL=INFO
ENV POLICY_ENGINE_HOST=policy-engine
ENV POLICY_ENGINE_PORT=5000
ENV MIN_CLIENTS=1
ENV MIN_AVAILABLE_CLIENTS=1
ENV USE_STATIC_IP=true
ENV FL_SERVER_IP=192.168.100.10
ENV DOCKER_COMPOSE_ENV=true

# Install necessary networking tools
RUN apt-get update && apt-get install -y curl net-tools iputils-ping iproute2 procps && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add debug flags for Python and gRPC
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1
ENV GRPC_VERBOSITY=DEBUG
ENV GRPC_TRACE=tcp
ENV FLWR_SERVER_TIMEOUT=600

# Expose the server port
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=1s --timeout=30s --retries=3 \
  CMD curl -f http://localhost:${FL_SERVER_PORT}/health || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 