---
sidebar_position: 1
---

# Installation

Get FLOPY-NET up and running on your system in just a few steps.

## Prerequisites

Before installing FLOPY-NET, ensure you have the following prerequisites:

### Required Software

- **Docker Desktop for Windows** (version 4.10 or higher)
- **Docker Compose** (included with Docker Desktop)
- **Python** (version 3.8 or higher)
- **Git** (for cloning the repository)
- **Windows 10/11** with WSL2 enabled (recommended for Docker)

### Optional but Recommended

- **GNS3 Server** (version 2.2 or higher) - for network simulation
- **Node.js** (version 16 or higher) - for development
- **Visual Studio Code** - for development with our extensions
- **Windows Terminal** or **PowerShell 7** - for better CLI experience

### Windows-Specific Setup

For optimal performance on Windows:

1. **Enable WSL2**: FLOPY-NET works best with Docker Desktop using WSL2 backend
2. **Docker Desktop Configuration**:
   - Allocate at least 4 GB RAM to Docker
   - Enable "Use the WSL 2 based engine"
   - Ensure file sharing is enabled for your project directory
3. **Network Configuration**: Windows Defender Firewall may need configuration for container networking

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16 GB or more |
| CPU | 4 cores | 8 cores or more |
| Storage | 20 GB | 50 GB or more |
| Network | 100 Mbps | 1 Gbps |

## Quick Installation

The fastest way to get FLOPY-NET running on Windows is using Docker Compose:

```powershell title="Quick Start (Windows PowerShell)"
# Clone the repository
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# Start all services (Windows Docker)
docker-compose up -d

# Verify installation
docker-compose ps

# Check service health
docker-compose logs policy-engine
docker-compose logs fl-server
```

This will start all FLOPY-NET components:
- **Policy Engine**: http://localhost:5000 (IP: 192.168.100.20)
- **FL Server**: Port 8080 (IP: 192.168.100.10)  
- **FL Metrics**: Port 8081 (IP: 192.168.100.10)
- **FL Clients**: IPs 192.168.100.101, 192.168.100.102 (Port: 8081 each)
- **Collector Service**: Port 8083 (IP: 192.168.100.40)
- **SDN Controller**: Port 6633/8181 (IP: 192.168.100.41)
- **OpenVSwitch**: IP: 192.168.100.60
- **Dashboard Frontend**: Port 8085
- **Dashboard Backend**: Port 8001

## System Architecture

The system uses a **static IP configuration** on the `192.168.100.0/24` network:

| Component | IP Range | Example IPs | Ports |
|-----------|----------|-------------|-------|
| Policy Engine | 192.168.100.20-29 | 192.168.100.20 | 5000 |
| FL Server | 192.168.100.10-19 | 192.168.100.10 | 8080, 8081 |
| FL Clients | 192.168.100.100-255 | 192.168.100.101, 102 | 8081 |
| Collector | 192.168.100.40 | 192.168.100.40 | 8083 |
| SDN Controller | 192.168.100.30-49 | 192.168.100.41 | 6633, 8181 |
| OpenVSwitch | 192.168.100.60-99 | 192.168.100.60 | 6633 |
| Dashboard APIs | 192.168.100.50-59 | 192.168.100.50 | 8001, 8085 |

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
docker pull abdulmelink/flopynet-server:latest
docker pull abdulmelink/flopynet-client:latest

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

## GNS3 VM Setup for Network Simulation

For realistic network simulation capabilities, FLOPY-NET integrates with GNS3 VM rather than containerized GNS3. This provides better performance and compatibility.

### 1. Download and Setup GNS3 VM

**Download GNS3 VM:**
```powershell
# Download from official GNS3 website
# https://www.gns3.com/software/download-vm

# Choose your hypervisor:
# - VMware Workstation/vSphere (Recommended)
# - VirtualBox (Free alternative) 
# - Hyper-V (Windows Pro/Enterprise)
```

**VM Configuration Requirements:**
```yaml
Minimum Specs:
  - RAM: 4 GB (8 GB recommended)
  - CPU: 2 cores (4 cores recommended)  
  - Disk: 20 GB (50 GB recommended)
  - Network: NAT + Host-only adapters

Recommended Specs:
  - RAM: 8-16 GB
  - CPU: 4-8 cores
  - Disk: 100 GB SSD
  - Network: Bridged + Host-only adapters
```

### 2. Configure GNS3 VM Networking

**Setup VM Network Adapters:**
```powershell
# Adapter 1: NAT (for internet access)
# Purpose: GNS3 VM internet connectivity
# Configuration: DHCP enabled

# Adapter 2: Host-only (for FLOPY-NET integration)
# Purpose: Communication with host Docker containers
# Network: 192.168.56.0/24 (VirtualBox) or 192.168.137.0/24 (Hyper-V)
# VM IP: 192.168.56.100 (static assignment recommended)
```

**Configure VM Static IP:**
```bash
# SSH into GNS3 VM (default: gns3/gns3)
ssh gns3@192.168.56.100

# Edit network configuration  
sudo nano /etc/netplan/01-netcfg.yaml

# Add static IP configuration:
network:
  version: 2
  ethernets:
    eth1:  # Host-only adapter
      dhcp4: false
      addresses: [192.168.56.100/24]
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]

# Apply configuration
sudo netplan apply
```

### 3. Install Docker in GNS3 VM

**Install Docker Engine:**
```bash
# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add gns3 user to docker group
sudo usermod -aG docker gns3

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker --version
```

### 4. Configure GNS3 Server

**Configure GNS3 Server Settings:**
```bash
# Edit GNS3 server configuration
nano ~/.config/GNS3/2.2/gns3_server.conf

# Add/modify these settings:
[Server]
host = 0.0.0.0
port = 3080
images_path = /opt/gns3/images  
projects_path = /opt/gns3/projects
appliances_path = /opt/gns3/appliances

[Docker]
enable = true
# Use Docker runtime in VM
```

**Start GNS3 Server:**
```bash
# Start GNS3 server (will auto-start on boot)
sudo systemctl start gns3

# Enable auto-start
sudo systemctl enable gns3

# Verify server is running
curl http://localhost:3080/v2/version
```

### 5. Pull FLOPY-NET Docker Images

**Pull Required Images:**
```bash
# Pull FLOPY-NET images into GNS3 VM
docker pull abdulmelink/flopynet-server:latest
docker pull abdulmelink/flopynet-client:latest  
docker pull abdulmelink/flopynet-policy-engine:latest
docker pull abdulmelink/flopynet-collector:latest
docker pull abdulmelink/flopynet-sdn-controller:latest
docker pull abdulmelink/flopynet-openvswitch:latest

# Verify images are available
docker images | grep flopynet
```

### 6. Register FLOPY-NET Templates

After pulling the images, register the GNS3 templates using the template registration script:

```powershell
# Exit SSH session and return to host machine
exit

# From the host machine (FLOPY-NET project directory)
cd d:\dev\microfed\codebase

# Register all FLOPY-NET templates in GNS3 VM
python scripts\gns3_templates.py register --host 192.168.56.100 --port 3080

# Verify template registration
python scripts\gns3_templates.py list --host 192.168.56.100 --flopynet-only
```

**Expected template registration output:**
```
Found 6 templates:

DOCKER TEMPLATES (6):  - flopynet-FLServer (guest): abdulmelink/flopynet-server:latest
  - flopynet-FLClient (guest): abdulmelink/flopynet-client:latest
  - flopynet-PolicyEngine (guest): abdulmelink/flopynet-policy-engine:latest
  - flopynet-Collector (guest): abdulmelink/flopynet-collector:latest
  - flopynet-SDNController (guest): abdulmelink/flopynet-sdn-controller:latest
  - OpenVSwitch (guest): abdulmelink/flopynet-openvswitch:latest
```

### 7. Configure Host Machine Integration

**Update FLOPY-NET Configuration:**
```json
// config/gns3_connection.json
{
  "host": "192.168.56.100",  // GNS3 VM IP
  "port": 3080,
  "protocol": "http",
  "user": null,
  "password": null,
  "verify_ssl": false,
  "vm_integration": true,
  "ssh_config": {
    "host": "192.168.56.100",
    "port": 22,
    "username": "gns3", 
    "password": "gns3"
  }
}
```

**Test Connectivity:**
```powershell
# Test GNS3 VM connectivity from host
curl http://192.168.56.100:3080/v2/version

# Test SSH connectivity  
ssh gns3@192.168.56.100 'docker --version'

# Expected response: Docker version info
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
- **Dashboard API**: http://localhost:8001/docs
- **Policy Engine API**: http://localhost:5000
- **Collector API**: http://localhost:8083

### 3. Run Health Checks

```bash
# Check Policy Engine health (core system)
curl http://localhost:5000/health

# Check collector metrics endpoint
curl http://localhost:8083/health

# Check dashboard backend API
curl http://localhost:8001/health
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
