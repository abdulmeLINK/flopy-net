FROM ubuntu:20.04

LABEL maintainer="https://github.com/abdulmeLINK"
LABEL description="Open vSwitch for flopynet System - Software-defined networking switch"

# Prevent apt from asking questions
ENV DEBIAN_FRONTEND=noninteractive

# Install Open vSwitch and required tools
RUN apt-get update && apt-get install -y \
    openvswitch-switch \
    openvswitch-common \
    net-tools \
    iproute2 \
    iputils-ping \
    iptables \
    tcpdump \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code (if needed)
COPY src /app/src

# Copy entrypoint script
COPY docker/entrypoints/entrypoint-ovs.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup environment variables
ENV PYTHONPATH=/app
ENV OVS_BRIDGE_NAME=br0
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs

# Create necessary directories
RUN mkdir -p /app/config /app/logs

# Set default configuration
ENV LOG_LEVEL=INFO
ENV SERVICE_TYPE=openvswitch
ENV SDN_CONTROLLER_HOST=sdn-controller
ENV SDN_CONTROLLER_PORT=6633
ENV USE_STATIC_IP=true
ENV OVS_IP=192.168.100.42
ENV DOCKER_COMPOSE_ENV=true

# Expose OpenFlow port
EXPOSE 6633

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ovs-vsctl show || exit 1

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 