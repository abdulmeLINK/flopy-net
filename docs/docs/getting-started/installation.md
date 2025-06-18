---
sidebar_position: 1
---

# Installation

Get FLOPY-NET up and running on your system in just a few steps.

## Prerequisites

Before installing FLOPY-NET, ensure you have the following prerequisites:

### Required Software

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Python** (version 3.8 or higher)
- **Git** (for cloning the repository)

### Optional but Recommended

- **GNS3 Server** (version 2.2 or higher) - for network simulation
- **Node.js** (version 16 or higher) - for development
- **Visual Studio Code** - for development with our extensions

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB or more |
| CPU | 4 cores | 8 cores or more |
| Storage | 20 GB | 50 GB or more |
| Network | 100 Mbps | 1 Gbps |

## Quick Installation

The fastest way to get FLOPY-NET running is using Docker Compose:

```powershell title="Quick Start (Windows PowerShell)"
# Clone the repository
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# Start all services using the PowerShell script
.\docker-run.ps1

# Or manually with docker-compose
docker-compose up -d

# Verify installation
docker-compose ps
```

This will start all FLOPY-NET components:
- **Policy Engine**: http://localhost:5000 (IP: 192.168.100.20)
- **FL Server**: Port 8080 (IP: 192.168.100.10)  
- **FL Clients**: IPs 192.168.100.101, 192.168.100.102
- **Collector Service**: Port 8000 (IP: 192.168.100.40)
- **SDN Controller**: Port 6633/8181 (IP: 192.168.100.41)
- **OpenVSwitch**: IP range 192.168.100.60-99
- **Dashboard**: Frontend and backend services (see dashboard documentation)

## System Architecture

The system uses a **static IP configuration** on the `192.168.100.0/24` network:

| Component | IP Range | Example IPs |
|-----------|----------|-------------|
| Policy Engine | 192.168.100.20-29 | 192.168.100.20 |
| FL Server | 192.168.100.10-19 | 192.168.100.10 |
| FL Clients | 192.168.100.100-255 | 192.168.100.101, 102 |
| Collector | 192.168.100.40 | 192.168.100.40 |
| SDN Controller | 192.168.100.30-49 | 192.168.100.41 |
| OpenVSwitch | 192.168.100.60-99 | 192.168.100.60 |
| Northbound APIs | 192.168.100.50-59 | 192.168.100.50 |

## Manual Installation

For development or custom configurations, you can install components manually:

### 1. Clone and Setup

```bash
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configurations
cp config/collector_config.json.example config/collector_config.json
cp config/server_config.json.example config/server_config.json
cp config/policies/policies.json.example config/policies/policies.json

# Edit configurations as needed
```

### 3. Start Components

```powershell
# Terminal 1: Start the collector service
python src\main.py run collector

# Terminal 2: Start the policy engine  
python src\main.py run policy-engine

# Terminal 3: Start the FL server
python src\main.py run fl-server

# Terminal 4: Start FL clients
python src\main.py run fl-client --client-id client-1

# Terminal 5: Run a scenario
python src\main.py scenario run basic
```
cd dashboard/backend && python -m app.main

# Terminal 4: Start the dashboard frontend
cd dashboard/frontend && npm install && npm run dev
```

## Docker Installation

### Using Pre-built Images

```bash title="Using Docker Hub Images"
# Pull the latest images
docker pull abdulmelink/flopynet-dashboard:latest
docker pull abdulmelink/flopynet-collector:latest
docker pull abdulmelink/flopynet-policy-engine:latest
docker pull abdulmelink/flopynet-fl-server:latest
docker pull abdulmelink/flopynet-fl-client:latest

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Building from Source

```bash title="Build Local Images"
# Build all images
docker-compose build

# Or build specific components
docker build -f docker/collector.Dockerfile -t flopynet-collector .
docker build -f docker/flopynet_policy_engine.Dockerfile -t flopynet-policy-engine .
```

## GNS3 Integration Setup

For network simulation capabilities, set up GNS3 integration:

### 1. Install GNS3 Server

```bash title="GNS3 Server Installation"
# Using Docker (recommended)
docker run -d \
  --name gns3-server \
  -p 3080:3080 \
  --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gns3/gns3:latest

# Or install native GNS3 server
# See: https://docs.gns3.com/docs/
```

### 2. Configure GNS3 Connection

```json title="config/gns3_connection.json"
{
  "host": "localhost",
  "port": 3080,
  "protocol": "http",
  "user": null,
  "password": null,
  "verify_ssl": false
}
```

### 3. Deploy FLOPY-NET Images to GNS3

```bash
# Use our deployment script
python scripts/deploy_gns3_images.py

# Or manually build and push
./docker/build-and-push-all.sh
```

## Verification

After installation, verify that everything is working:

### 1. Check Service Status

```bash
# Using Docker Compose
docker-compose ps

# Expected output:
# NAME                    IMAGE                              STATUS
# flopy-net-dashboard     abdulmelink/flopynet-dashboard     Up
# flopy-net-collector     abdulmelink/flopynet-collector     Up
# flopy-net-policy        abdulmelink/flopynet-policy        Up
```

### 2. Access Dashboards

- **Main Dashboard**: http://localhost:8085
- **API Documentation**: http://localhost:8001/docs
- **Alternative Dashboard**: http://localhost:8050

### 3. Run Health Checks

```bash
# Check API health
curl http://localhost:8001/health

# Check collector metrics
curl http://localhost:8002/metrics

# Check policy engine status
curl http://localhost:8003/status
```

## Troubleshooting

### Common Issues

#### Port Conflicts
If you encounter port conflicts, modify the ports in `docker-compose.yml`:

```yaml title="docker-compose.yml"
services:
  dashboard-frontend:
    ports:
      - "8085:80"  # Change 8085 to available port
```

#### Permission Issues
On Linux systems, you might need to adjust Docker permissions:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

#### Memory Issues
If containers crash due to memory issues, increase Docker's memory limit or reduce the number of FL clients in scenarios.

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](/docs/user-guide/troubleshooting)
2. Review logs: `docker-compose logs [service-name]`
3. Open an issue on [GitHub](https://github.com/abdulmelink/flopy-net/issues)
4. Join our [Discord community](https://discord.gg/flopy-net)

## Next Steps

Now that FLOPY-NET is installed:

1. **[Quick Start Guide](/docs/getting-started/quick-start)** - Run your first experiment
2. **[Quick Start](./quick-start.md)** - Customize your setup
3. **[Basic Experiment](../tutorials/basic-experiment.md)** - Learn the basics

---

## Advanced Installation Options

### Custom Build Options

```bash title="Advanced Build"
# Build with specific tags
docker build -f docker/collector.Dockerfile \
  --build-arg VERSION=v1.0.0 \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  -t flopynet-collector:custom .

# Build for specific architecture
docker buildx build --platform linux/amd64,linux/arm64 \
  -f docker/collector.Dockerfile \
  -t flopynet-collector:multiarch .
```

### Development Installation

```bash title="Development Setup"
# Install development dependencies
pip install -r requirements-dev.txt
npm install -g @angular/cli  # For dashboard development

# Set up pre-commit hooks
pre-commit install

# Run in development mode
docker-compose -f docker-compose.dev.yml up -d
```
