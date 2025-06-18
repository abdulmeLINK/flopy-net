FROM python:3.9-slim

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="SDN Controller for flopynet FL System"

WORKDIR /app

# Copy requirements first for better caching
COPY docker/requirements/controller-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src

# Copy entrypoint script
COPY docker/entrypoints/entrypoint-controller.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV CONTROLLER_HOST=0.0.0.0
ENV CONTROLLER_PORT=6633
ENV REST_PORT=8181
ENV CONFIG_DIR=/app/config
ENV DATA_DIR=/app/data
ENV LOGS_DIR=/app/logs

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/data

# Set default configuration
ENV LOG_LEVEL=INFO
ENV SERVICE_TYPE=sdn-controller
ENV POLICY_ENGINE_HOST=policy-engine
ENV USE_STATIC_IP=true
ENV CONTROLLER_IP=192.168.100.41
ENV DOCKER_COMPOSE_ENV=true
ENV NORTHBOUND_INTERFACE=eth1
ENV NORTHBOUND_IP=192.168.100.51

# Install networking tools
RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    curl \
    procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose the controller ports
EXPOSE 6633
EXPOSE 8181

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${REST_PORT}/health || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 