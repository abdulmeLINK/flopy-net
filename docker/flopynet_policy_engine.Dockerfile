FROM python:3.9-slim

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="Policy Engine for flopynet System - Enforces security and privacy policies"

WORKDIR /app

# Copy requirements first for better caching
COPY docker/requirements/policy-engine-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src /app/src

# Create necessary directories first
RUN mkdir -p /app/config/policies /app/logs

# Create other config directories (without symlinks yet)
RUN mkdir -p /app/config/policy_engine /app/config/policy_functions

# Copy policy files to the correct location
COPY config/policies/*.json /app/config/policies/

# Copy needed entrypoint script
COPY docker/entrypoints/entrypoint-policy.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV POLICY_PORT=5000
ENV CONFIG_DIR=/app/config
ENV POLICY_CONFIG=/app/config/policy_engine/policy_config.json
ENV POLICY_FILE=/app/config/policies/policies.json
ENV POLICY_FUNCTIONS_DIR=/app/config/policy_functions
ENV LOGS_DIR=/app/logs

# Set default configuration
ENV LOG_LEVEL=INFO
ENV USE_STATIC_IP=true
ENV POLICY_ENGINE_IP=192.168.100.20
ENV DOCKER_COMPOSE_ENV=true
ENV FL_SERVER_PORT=8080
ENV COLLECTOR_PORT=8082

# Install curl and networking tools
RUN apt-get update && apt-get install -y curl net-tools iputils-ping iproute2 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose the policy engine port
EXPOSE 5000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:${POLICY_PORT}/health || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 