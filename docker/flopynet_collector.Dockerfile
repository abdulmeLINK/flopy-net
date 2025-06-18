FROM python:3.9-slim

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="Metrics Collector for flopynet System"

WORKDIR /app

# Copy requirements first for better caching
COPY docker/requirements/collector-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src

# Copy configuration files
COPY config /app/config

# Copy entrypoint script
COPY docker/entrypoints/entrypoint-collector.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV COLLECTOR_PORT=8000
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs
ENV RESULTS_DIR=/app/results

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/results

# Set default configuration
ENV LOG_LEVEL=INFO
ENV SERVICE_TYPE=collector
ENV FL_SERVER_HOST=fl-server
ENV POLICY_ENGINE_HOST=policy-engine
ENV USE_STATIC_IP=true
ENV COLLECTOR_IP=192.168.100.40
ENV DOCKER_COMPOSE_ENV=true
ENV POLICY_INTERVAL_SEC=5
ENV FL_INTERVAL_SEC=5
ENV NETWORK_INTERVAL_SEC=5
ENV EVENT_INTERVAL_SEC=5

# Install curl and networking tools
RUN apt-get update && apt-get install -y curl net-tools iputils-ping iproute2 jq && apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose the collector port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${COLLECTOR_PORT}/health || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 