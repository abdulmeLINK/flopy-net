# Docker Configuration

This directory contains Docker configurations for containerized deployment of the FL-SDN project.

## Files

- **docker-compose.yml**: Multi-container Docker application definition
- **docker-run.ps1**: PowerShell script to run Docker containers (Windows)
- **docker-run.sh**: Shell script to run Docker containers (Linux/Mac)
- **dashboard.Dockerfile**: Dockerfile for the dashboard service
- **fl-server.Dockerfile**: Dockerfile for the federated learning server
- **policy-engine.Dockerfile**: Dockerfile for the policy engine service

## Build and Run

```bash
# Build all images
docker-compose build

# Run all services
docker-compose up
```

Or use the provided scripts:

```bash
# On Linux/Mac
./docker-run.sh

# On Windows
.\docker-run.ps1
```

## Container Services

1. **dashboard**: Web interface for monitoring and control (port 8050)
2. **fl-server**: Federated learning server (port 8080)
3. **policy-engine**: Policy engine service (port 8000)

## Development with Docker

For development, you can mount local directories to containers:

```yaml
volumes:
  - ./src:/app/src
```

This enables hot-reloading of code during development.

## Deployment Guidance

For comprehensive deployment patterns and guidelines, including:

- Development, staging, and production deployment architectures
- Kubernetes orchestration configurations
- Cloud deployment options
- Security hardening for containers
- Monitoring and observability setup

Please refer to the [Deployment Patterns](../docs/deployment_patterns.md) document for detailed deployment guidance. 