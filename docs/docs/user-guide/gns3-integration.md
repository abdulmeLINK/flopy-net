# GNS3 VM Integration

This guide covers integrating FLOPY-NET with GNS3 VM for realistic network simulation, enabling comprehensive testing of federated learning systems under various network conditions and topologies.

## Critical Configuration Requirements

### Same Subnet Requirement for GNS3 VM

⚠️ **IMPORTANT**: When using GNS3 VM integration, all FLOPY-NET components **MUST** be configured in the same subnet (192.168.100.0/24) for proper operation when Cloud node used in the project. For advanced Layer 3 forwarding routers should be used. Routers is not currently supported by scenario GNS3 deployment. 

**Correct Configuration:**
```yaml
# All components in 192.168.100.0/24
Policy Engine: 192.168.100.20
FL Server: 192.168.100.10  
Collector: 192.168.100.40
SDN Controller: 192.168.100.41
OpenVSwitch: 192.168.100.60
FL Clients: 192.168.100.101-105
```

**Incorrect Configuration:**
```yaml
# DON'T DO THIS - Different subnets will cause communication failures
Policy Engine: 192.168.20.10   # Different subnet
FL Server: 192.168.10.10       # Different subnet  
Collector: 192.168.40.10       # Different subnet
```

### Required Network Settings

```json
{
  "network_requirements": {
    "subnet_mask": "255.255.255.0",
    "gateway": "192.168.100.1",
    "broadcast_domain": "192.168.100.255",
    "mtu": 1500,
    "dns_servers": ["8.8.8.8", "8.8.4.4"]
  },
  
  "container_networking": {
    "bridge_mode": true,
    "host_networking": false,
    "custom_networks": false,
    "ip_forwarding": true
  }
}
```

## Overview

GNS3 VM integration provides:

- **Realistic Network Topologies**: Complex multi-hop networks, WAN links, cellular networks, edge computing scenarios
- **Dynamic Network Conditions**: Real-time latency injection, bandwidth limitations, packet loss simulation, and jitter
- **Container Integration**: Deploy FLOPY-NET Docker containers as GNS3 nodes with full service functionality
- **SDN Integration**: OpenVSwitch and Ryu controller integration for programmable network behavior
- **VM-based Performance**: Better performance than containerized GNS3 for complex simulations
- **FL-Specific Scenarios**: Pre-built templates for federated learning network research

## Architecture Integration

FLOPY-NET integrates with GNS3 VM through multiple layers:

### GNS3 VM Architecture
- **GNS3 VM Host**: Ubuntu-based virtual machine running GNS3 server
- **Docker Runtime**: Native Docker installation within the VM for container management
- **FLOPY-NET Containers**: Deploy `abdulmelink/flopynet-*` images as GNS3 Docker nodes
- **Network Simulation**: Virtual networks with realistic latency, bandwidth, and loss characteristics
- **SSH Integration**: Remote control and monitoring via SSH from host machine

### Host-VM Communication
- **GNS3 API**: REST API communication over VM network adapter
- **SSH Integration**: Secure shell access for container management and monitoring
- **Cloud Node Bridge**: Direct network access between host and GNS3 topology
- **File Transfer**: Configuration and result exchange via SCP/SFTP

## Prerequisites

### 1. GNS3 VM Installation

**Download and Install GNS3 VM:**

1. **Download GNS3 VM** from https://www.gns3.com/software/download-vm
2. **Choose your hypervisor:**
   - VMware Workstation/vSphere (Recommended for performance)
   - VirtualBox (Free option)
   - Hyper-V (Windows Pro/Enterprise)

3. **Import VM and configure resources:**
```powershell
# VMware example resource allocation
CPU: 4 cores (minimum 2)
RAM: 8 GB (minimum 4 GB)  
Disk: 50 GB (minimum 20 GB)
Network Adapter 1: NAT (internet access)
Network Adapter 2: Host-only (FLOPY-NET integration)
```

### 2. Configure GNS3 VM Networking

**Setup VM network configuration:**
```bash
# SSH into GNS3 VM (default credentials: gns3/gns3)
ssh gns3@192.168.56.100

# Configure static IP for host-only adapter
sudo nano /etc/netplan/01-netcfg.yaml

# Example configuration:
network:
  version: 2
  ethernets:
    eth0:  # NAT adapter  
      dhcp4: true
    eth1:  # Host-only adapter
      dhcp4: false
      addresses: [192.168.56.100/24]
      nameservers:
        addresses: [8.8.8.8]

# Apply network configuration
sudo netplan apply
```

### 3. Install Docker in GNS3 VM

**Install Docker runtime for container support:**
```bash
# Update package repositories
sudo apt update && sudo apt upgrade -y

# Install Docker dependencies
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key and repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add gns3 user to docker group
sudo usermod -aG docker gns3
newgrp docker

# Verify Docker installation
docker --version
docker run hello-world
```

### 4. Configure GNS3 Server in VM

**Configure GNS3 server settings:**
```bash
# Create GNS3 configuration directory
mkdir -p ~/.config/GNS3/2.2

# Configure GNS3 server
cat > ~/.config/GNS3/2.2/gns3_server.conf << 'EOF'
[Server]
host = 0.0.0.0
port = 3080
images_path = /opt/gns3/images
projects_path = /opt/gns3/projects
appliances_path = /opt/gns3/appliances
configs_path = /opt/gns3/configs
report_errors = True

[Qemu]
enable_hardware_acceleration = true
require_hardware_acceleration = false

[Dynamips]
allocate_hypervisor_per_device = true

[Docker]
enable = true
EOF

# Create required directories
sudo mkdir -p /opt/gns3/{images,projects,appliances,configs}
sudo chown -R gns3:gns3 /opt/gns3
```

### 5. Start and Verify GNS3 Services

**Start GNS3 server:**
```bash
# Start GNS3 server (auto-starts on VM boot)
sudo systemctl start gns3

# Enable auto-start on boot
sudo systemctl enable gns3

# Check server status
sudo systemctl status gns3

# Verify GNS3 API is accessible
curl http://localhost:3080/v2/version
```

**Test from host machine:**
```powershell
# Test GNS3 VM connectivity from host
curl http://192.168.56.100:3080/v2/version

# Expected response: JSON with GNS3 version info
```

## FLOPY-NET GNS3 VM Integration

### 1. Configure Host Machine Integration

Update FLOPY-NET configuration to connect to GNS3 VM:

```json
// config/gns3_connection.json
{
  "host": "192.168.56.100",  // GNS3 VM IP address
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
    "password": "gns3",
    "key_file": null  // Optional: use SSH key instead of password
  },
  "container_registry": {
    "username": "abdulmelink",
    "images": [
      "flopynet-fl-server:latest",
      "flopynet-fl-client:latest", 
      "flopynet-policy-engine:latest",
      "flopynet-collector:latest",
      "flopynet-sdn-controller:latest",
      "flopynet-openvswitch:latest"
    ]
  }
}
```

### 2. Register GNS3 Templates

Before pulling images, register the FLOPY-NET templates in GNS3 using the dedicated template registration script:

```powershell
# From the host machine (FLOPY-NET project directory)
cd d:\dev\microfed\codebase

# Register all FLOPY-NET templates in GNS3 VM
python scripts\gns3_templates.py register --host 192.168.56.100 --port 3080

# Verify template registration
python scripts\gns3_templates.py list --host 192.168.56.100 --flopynet-only

# Expected output should show all registered templates:
# DOCKER TEMPLATES (6):
#   - flopynet-FLServer (guest): abdulmelink/flopynet-server:latest
#   - flopynet-FLClient (guest): abdulmelink/flopynet-client:latest
#   - flopynet-PolicyEngine (guest): abdulmelink/flopynet-policy-engine:latest
#   - flopynet-Collector (guest): abdulmelink/flopynet-collector:latest
#   - flopynet-SDNController (guest): abdulmelink/flopynet-sdn-controller:latest
#   - OpenVSwitch (guest): abdulmelink/flopynet-openvswitch:latest
```

### 3. Pull FLOPY-NET Base Images

After template registration, pull the required Docker images into the GNS3 VM:
```bash
# SSH into GNS3 VM
ssh gns3@192.168.56.100

# Pull all FLOPY-NET Docker images
docker pull abdulmelink/flopynet-server:latest
docker pull abdulmelink/flopynet-client:latest
docker pull abdulmelink/flopynet-policy-engine:latest  
docker pull abdulmelink/flopynet-collector:latest
docker pull abdulmelink/flopynet-sdn-controller:latest
docker pull abdulmelink/flopynet-openvswitch:latest

# Verify images are available
docker images | grep abdulmelink

# Expected output should show all flopynet images with their tags and sizes
```

### 4. Deploy Custom Images (Optional)

For custom images built on top of FLOPY-NET base images, follow this comprehensive workflow:

#### 4.1. Build Custom Images

**⚠️ CRITICAL REQUIREMENT: Metric Collection Consistency**

When building custom FL clients and servers, you **MUST** maintain the same metric collection methods and interfaces as the base FLOPY-NET images. The Collector service expects consistent metric formats and endpoints across all FL components.

**Required Metric Collection Standards:**
- FL clients must expose metrics on port 8081 with the same API endpoints
- FL servers must maintain the MetricsTrackingStrategy interface
- Custom implementations must preserve the JSON response format
- Metric timestamps and data structures must remain consistent

**Example: Custom FL Client with Consistent Metrics**
```dockerfile
# Dockerfile.custom-fl-client
FROM abdulmelink/flopynet-client:latest

# Add custom dependencies
RUN pip install transformers torch-audio scikit-image pandas seaborn

# Add custom model implementations
COPY custom_models/ /app/custom_models/
COPY custom_datasets/ /app/custom_datasets/
COPY custom_config.json /app/config/

# CRITICAL: Preserve metric collection interface
COPY custom_metrics_handler.py /app/src/fl/
COPY custom_model_handler.py /app/src/fl/

# Custom environment variables
ENV CUSTOM_MODEL_PATH=/app/custom_models
ENV CUSTOM_DATASET_PATH=/app/custom_datasets
ENV ENABLE_CUSTOM_FEATURES=true
# REQUIRED: Maintain metrics endpoint compatibility
ENV METRICS_PORT=8081
ENV METRICS_ENDPOINT=/metrics

# Custom startup script that preserves metric collection
COPY custom_entrypoint.sh /app/
RUN chmod +x /app/custom_entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/app/custom_entrypoint.sh"]
```

**Example: Custom FL Server with Preserved Metrics**
```dockerfile
# Dockerfile.custom-fl-server
FROM abdulmelink/flopynet-server:latest

# Add custom aggregation algorithms
COPY custom_aggregation/ /app/custom_aggregation/
COPY custom_strategies/ /app/src/fl/strategies/

# CRITICAL: Custom strategy must extend MetricsTrackingStrategy
COPY custom_metrics_strategy.py /app/src/fl/strategies/

# Environment for custom registry
ENV CUSTOM_REGISTRY=your-org
ENV CUSTOM_AGGREGATION_PATH=/app/custom_aggregation
# REQUIRED: Preserve metrics collection interface
ENV FL_METRICS_PORT=8081
ENV ENABLE_METRICS_TRACKING=true

COPY custom_server_entrypoint.sh /app/
RUN chmod +x /app/custom_server_entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/app/custom_server_entrypoint.sh"]
```

**Build and Deploy Custom Image with Registry Management:**
```powershell
# Build custom images with your registry
docker build -f Dockerfile.custom-fl-client -t your-org/custom-flopynet-client:v1.0 .
docker build -f Dockerfile.custom-fl-server -t your-org/custom-flopynet-server:v1.0 .

# Tag for your custom registry (different from abdulmelink registry)
docker tag your-org/custom-flopynet-client:v1.0 your-registry.com/flopynet/custom-client:v1.0
docker tag your-org/custom-flopynet-server:v1.0 your-registry.com/flopynet/custom-server:v1.0

# Push to your custom registry
docker push your-registry.com/flopynet/custom-client:v1.0
docker push your-registry.com/flopynet/custom-server:v1.0

# Save images for transfer to GNS3 VM (if not using registry)
docker save your-org/custom-flopynet-client:v1.0 | gzip > custom-client.tar.gz
docker save your-org/custom-flopynet-server:v1.0 | gzip > custom-server.tar.gz

# Transfer to GNS3 VM
scp custom-client.tar.gz custom-server.tar.gz gns3@192.168.56.100:/tmp/

# SSH into GNS3 VM and load images
ssh gns3@192.168.56.100
docker load < /tmp/custom-client.tar.gz
docker load < /tmp/custom-server.tar.gz
docker images | grep custom-flopynet
```

**⚠️ Registry Considerations for Custom Images:**
- Use your own Docker registry namespace (e.g., `your-org/` instead of `abdulmelink/`)
- Update template configurations to reference your custom registry
- **CRITICAL**: Ensure metric collection compatibility with base images
- Maintain version compatibility with FLOPY-NET core services
- **Registry Separation**: Custom registries must maintain the same API contracts as `abdulmelink/` registry

#### 4.2. Create Custom Templates with Metric Collection Consistency

**⚠️ MANDATORY: Metric Collection Method Consistency**

When creating custom FL implementations, the metric collection methods **MUST** remain identical between FL clients and servers regardless of your custom registry. The FLOPY-NET Collector service expects consistent metric interfaces across all components.

**Required Metric Collection Standards:**

1. **FL Client Metric Requirements (MANDATORY):**
   ```json
   {
     "endpoint": "http://client:8081/metrics",
     "response_format": {
       "client_id": "string",
       "training_accuracy": "float",
       "training_loss": "float", 
       "data_samples": "integer",
       "training_time": "float",
       "round_number": "integer",
       "timestamp": "ISO8601"
     }
   }
   ```

2. **FL Server Metric Requirements (MANDATORY):**
   ```json
   {
     "interface": "MetricsTrackingStrategy",
     "sqlite_storage": "fl_rounds.db",
     "endpoint": "http://server:8081/metrics",
     "round_tracking": "required",
     "aggregation_metrics": "required"
   }
   ```

3. **Cross-Registry Compatibility:**
   - Metric API endpoints must match `abdulmelink/` base images exactly
   - JSON response schemas must be identical
   - SQLite database format must be compatible
   - Timestamp formats and data types must remain consistent

**Custom Template Definition with Registry Management:**
```json
// config/gns3/templates/custom_fl_client.json
{
  "name": "Custom-FLClient",
  "template_type": "docker",
  "image": "your-org/custom-flopynet-client:v1.0",
  "adapters": 1,
  "console_type": "telnet",
  "category": "guest",
  "symbol": ":/symbols/docker_guest.svg",
  "environment": {
    "SERVICE_TYPE": "fl-client",
    "CUSTOM_MODEL_PATH": "/app/custom_models",
    "CUSTOM_DATASET_PATH": "/app/custom_datasets",
    "ENABLE_CUSTOM_FEATURES": "true",
    "FL_SERVER_HOST": "192.168.141.10",
    "FL_SERVER_PORT": "8080",
    "POLICY_ENGINE_URL": "http://192.168.141.20:5000",
    "CLIENT_TYPE": "custom_enhanced",
    "METRICS_PORT": "8081",
    "METRICS_ENDPOINT": "/metrics",
    "REGISTRY_SOURCE": "your-org"
  }
}
```

```json
// config/gns3/templates/custom_fl_server.json
{
  "name": "Custom-FLServer", 
  "template_type": "docker",
  "image": "your-org/custom-flopynet-server:v1.0",
  "adapters": 1,
  "console_type": "telnet",
  "category": "guest", 
  "symbol": ":/symbols/docker_guest.svg",
  "environment": {
    "SERVICE_TYPE": "fl-server",
    "CUSTOM_AGGREGATION_PATH": "/app/custom_aggregation",
    "FL_SERVER_PORT": "8080",
    "FL_METRICS_PORT": "8081",
    "POLICY_ENGINE_URL": "http://192.168.141.20:5000",
    "ENABLE_METRICS_TRACKING": "true",
    "AGGREGATION_STRATEGY": "custom_fedavg",
    "REGISTRY_SOURCE": "your-org"
  }
}
```

**⚠️ CRITICAL: Metric Collection Consistency Requirements**

When creating custom templates, ensure the following metric collection standards are maintained:

1. **FL Client Metrics Requirements:**
   - Must expose metrics on port 8081 (`METRICS_PORT=8081`)
   - Must implement `/metrics` endpoint (`METRICS_ENDPOINT=/metrics`)
   - Must return JSON format compatible with Collector service
   - Must include client_id, training_accuracy, training_loss, data_samples

2. **FL Server Metrics Requirements:**
   - Must maintain MetricsTrackingStrategy interface
   - Must expose metrics on port 8081 for HTTP API
   - Must track global_accuracy, global_loss, round_number, active_clients
   - Must store round data in SQLite format compatible with collector

3. **Registry Naming Convention:**
   - Use consistent naming: `your-org/custom-flopynet-{component}:{version}`
   - Set `REGISTRY_SOURCE` environment variable for tracking
   - Maintain semantic versioning for compatibility tracking

**Register Custom Template with Registry Specification:**
```powershell
# Create custom templates directory structure
mkdir config\gns3\custom-templates\your-org
copy config\gns3\templates\custom_fl_client.json config\gns3\custom-templates\your-org\
copy config\gns3\templates\custom_fl_server.json config\gns3\custom-templates\your-org\

# Register custom templates with your registry
python scripts\gns3_templates.py register --host 192.168.56.100 --templates-dir config\gns3\custom-templates\your-org --registry your-org

# Register specific custom templates
python scripts\gns3_templates.py register --host 192.168.56.100 --registry your-org --custom-only

# Verify custom template registration
python scripts\gns3_templates.py list --host 192.168.56.100 --registry your-org | findstr Custom

# Expected output should show your custom templates:
# Custom-FLClient (guest): your-org/custom-flopynet-client:v1.0
# Custom-FLServer (guest): your-org/custom-flopynet-server:v1.0
```

#### 4.3. Template Management Commands

**Using the gns3_templates.py Script:**
```powershell
# List all available commands
python scripts\gns3_templates.py --help

# Register templates with specific options
python scripts\gns3_templates.py register --host 192.168.56.100 --registry your-registry --verbose

# Clean existing templates before re-registration
python scripts\gns3_templates.py clean --host 192.168.56.100 --pattern flopynet

# Update existing templates with new image versions
python scripts\gns3_templates.py update --host 192.168.56.100

# List templates with filtering
python scripts\gns3_templates.py list --host 192.168.56.100 --flopynet-only
```

### 5. Create GNS3 Project for FLOPY-NET

**Initialize a new GNS3 project:**
```powershell
# From host machine, create a new project
curl -X POST http://192.168.56.100:3080/v2/projects `
  -H "Content-Type: application/json" `
  -d '{
    "name": "FLOPY-NET-Federated-Learning",
    "project_id": "flopy-net-001",
    "auto_start": false,
    "auto_open": false
  }'
```

**Or use FLOPY-NET CLI:**
```powershell
# Navigate to FLOPY-NET directory
cd d:\dev\microfed\codebase

# Create GNS3 project via FLOPY-NET
python src\main.py gns3 create-project --name "FLOPY-NET-FL-Research" --vm-host 192.168.56.100
```

### 4. Configure Network Topology for Same Subnet

**Critical**: All FLOPY-NET components must be in the same subnet when using GNS3 VM:

```json
// config/topology/flopy_net_same_subnet.json
{
  "topology": {
    "name": "FLOPY-NET Same Subnet Topology",
    "subnet": "192.168.100.0/24",
    "gateway": "192.168.100.1",
    
    "nodes": [
      {
        "name": "Core-Switch",
        "type": "ethernet_switch",
        "ports": 16,
        "position": {"x": 0, "y": 0}
      },
      {
        "name": "Policy-Engine",
        "type": "docker",
        "image": "abdulmelink/flopynet-policy-engine:latest",
        "ip": "192.168.100.20",
        "ports": ["5000:5000"],
        "position": {"x": -200, "y": -100}
      },
      {"source": "SDN-Controller", "destination": "Core-Switch"},
      {"source": "OpenVSwitch", "destination": "Core-Switch"},
      {"source": "FL-Client-1", "destination": "Core-Switch"},
      {"source": "FL-Client-2", "destination": "Core-Switch"},
      {"source": "FL-Client-3", "destination": "Core-Switch"},
      {"source": "FL-Client-4", "destination": "Core-Switch"},
      {"source": "FL-Client-5", "destination": "Core-Switch"}
    ]
  }
}
```

**Why This Topology Works:**
- **Single Broadcast Domain**: All containers can discover each other
- **Direct Communication**: No routing between subnets required
- **Policy Enforcement**: Policy engine can reach all components
- **Simplified Networking**: Reduces configuration complexity
```

## Automated Topology Deployment

### 1. Topology Deployment Script

Create automated deployment:

```python
#!/usr/bin/env python3
"""
GNS3 Topology Deployment for FLOPY-NET
"""

import requests
import json
import time
from typing import Dict, List

class GNS3Manager:
    def __init__(self, server_url: str = "http://localhost:3080"):
        self.server_url = server_url
        self.api_base = f"{server_url}/v2"
        
    def create_project(self, name: str) -> str:
        """Create a new GNS3 project"""
        response = requests.post(
            f"{self.api_base}/projects",
            json={"name": name}
        )
        response.raise_for_status()
        return response.json()["project_id"]
    
    def create_node(self, project_id: str, node_config: Dict) -> str:
        """Create a node in the project"""
        response = requests.post(
            f"{self.api_base}/projects/{project_id}/nodes",
            json=node_config
        )
        response.raise_for_status()
        return response.json()["node_id"]
    
    def create_link(self, project_id: str, link_config: Dict) -> str:
        """Create a link between nodes"""
        response = requests.post(
            f"{self.api_base}/projects/{project_id}/links",
            json=link_config
        )
        response.raise_for_status()
        return response.json()["link_id"]
    
    def start_all_nodes(self, project_id: str):
        """Start all nodes in the project"""
        response = requests.post(
            f"{self.api_base}/projects/{project_id}/nodes/start"
        )
        response.raise_for_status()
    
    def deploy_flopy_net_topology(self) -> str:
        """Deploy the complete FLOPY-NET topology"""
        
        # Create project
        project_id = self.create_project("FLOPY-NET-Testbed")
        print(f"Created project: {project_id}")
        
        # Node configurations
        nodes = [
            {
                "name": "FL-Server",
                "node_type": "docker",
                "compute_id": "local",
                "properties": {
                    "image": "flopy-net/fl-server:latest",
                    "container_name": "gns3-fl-server",
                    "environment": "FL_SERVER_PORT=8080\nFL_SERVER_HOST=0.0.0.0"
                }
            },
            {
                "name": "Policy-Engine",
                "node_type": "docker", 
                "compute_id": "local",
                "properties": {
                    "image": "flopy-net/policy-engine:latest",
                    "container_name": "gns3-policy-engine"
                }
            },
            {
                "name": "Core-Switch",
                "node_type": "ethernet_switch",
                "compute_id": "local",
                "properties": {
                    "ports_mapping": [
                        {"name": "Ethernet0", "port_number": 0},
                        {"name": "Ethernet1", "port_number": 1},
                        {"name": "Ethernet2", "port_number": 2},
                        {"name": "Ethernet3", "port_number": 3},
                        {"name": "Ethernet4", "port_number": 4},
                        {"name": "Ethernet5", "port_number": 5}
                    ]
                }
            }
        ]
        
        # Create FL clients
        for i in range(1, 6):  # 5 FL clients
            nodes.append({
                "name": f"FL-Client-{i:02d}",
                "node_type": "docker",
                "compute_id": "local", 
                "properties": {
                    "image": "flopy-net/fl-client:latest",
                    "container_name": f"gns3-fl-client-{i:02d}",
                    "environment": f"CLIENT_ID=client_{i:03d}\nFL_SERVER_URL=http://FL-Server:8080"
                }
            })
        
        # Create nodes
        node_ids = {}
        for node_config in nodes:
            node_id = self.create_node(project_id, node_config)
            node_ids[node_config["name"]] = node_id
            print(f"Created node: {node_config['name']} ({node_id})")
            time.sleep(1)  # Prevent rate limiting
        
        # Create links
        links = [
            # Connect FL Server to core switch
            {
                "nodes": [
                    {"node_id": node_ids["FL-Server"], "adapter_number": 0, "port_number": 0},
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 0}
                ]
            },
            # Connect Policy Engine to core switch  
            {
                "nodes": [
                    {"node_id": node_ids["Policy-Engine"], "adapter_number": 0, "port_number": 0},
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 1}
                ]
            },
            {
                "nodes": [
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 2},
                    {"node_id": node_ids["FL-Client-01"], "adapter_number": 0, "port_number": 0}
                ]
            },
            {
                "nodes": [
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 3},
                    {"node_id": node_ids["FL-Client-02"], "adapter_number": 0, "port_number": 0}
                ]
            },
            {
                "nodes": [
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 4},
                    {"node_id": node_ids["FL-Client-03"], "adapter_number": 0, "port_number": 0}
                ]
            },
            {
                "nodes": [
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 5},
                    {"node_id": node_ids["FL-Client-04"], "adapter_number": 0, "port_number": 0}
                ]
            },
            {
                "nodes": [
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": 6},
                    {"node_id": node_ids["FL-Client-05"], "adapter_number": 0, "port_number": 0}
                ]
            }
        ]
        
        # Create all links
        for link_config in links:
            link_id = self.create_link(project_id, link_config)
            print(f"Created link: {link_id}")
            time.sleep(0.5)
        
        print("Topology deployment completed!")
        return project_id

if __name__ == "__main__":
    manager = GNS3Manager()
    project_id = manager.deploy_flopy_net_topology()
    
    # Start all nodes
    print("Starting all nodes...")
    manager.start_all_nodes(project_id)
    print("All nodes started!")
```

### 2. Run Deployment

Execute the deployment script:

```bash
python3 deploy_gns3_topology.py
```

## Network Condition Simulation

### 1. Latency Injection

Inject network latency between specific nodes:

```bash
curl -X POST http://localhost:3080/v2/projects/$PROJECT_ID/links/$LINK_ID/filters \
  -H "Content-Type: application/json" \
  -d '{
    "type": "delay",
    "parameters": {
      "latency": "100ms",
      "jitter": "10ms"
    }
  }'
```

### 2. Bandwidth Limitation

Limit bandwidth on network links:

```bash
curl -X POST http://localhost:3080/v2/projects/$PROJECT_ID/links/$LINK_ID/filters \
  -H "Content-Type: application/json" \
  -d '{
    "type": "bandwidth",
    "parameters": {
      "bandwidth": "10Mbps",
      "burst": "1MB"
    }
  }'
```

### 3. Packet Loss Simulation

Simulate packet loss:

```bash
curl -X POST http://localhost:3080/v2/projects/$PROJECT_ID/links/$LINK_ID/filters \
  -H "Content-Type: application/json" \
  -d '{
    "type": "packet_loss",
    "parameters": {
      "loss_rate": 0.05,
      "correlation": 0.25
    }
  }'
```

### 4. Combined Network Conditions

Apply multiple network impairments:

```python
def apply_network_conditions(project_id: str, link_id: str, conditions: Dict):
    """Apply multiple network conditions to a link"""
    
    # Create traffic control configuration
    tc_config = {
        "filters": [
            {
                "type": "delay",
                "parameters": {
                    "latency": conditions.get("latency", "0ms"),
                    "jitter": conditions.get("jitter", "0ms")
                }
            },
            {
                "type": "bandwidth", 
                "parameters": {
                    "rate": conditions.get("bandwidth", "1000Mbps"),
                    "burst": conditions.get("burst", "10MB")
                }
            },
            {
                "type": "packet_loss",
                "parameters": {
                    "loss_rate": conditions.get("packet_loss", 0.0),
                    "correlation": conditions.get("correlation", 0.0)
                }
            }
        ]
    }
    
    response = requests.put(
        f"http://localhost:3080/v2/projects/{project_id}/links/{link_id}/filters",
        json=tc_config
    )
    response.raise_for_status()

# Example usage
apply_network_conditions(project_id, link_id, {
    "latency": "50ms",
    "jitter": "5ms", 
    "bandwidth": "50Mbps",
    "packet_loss": 0.01
})
```

## Scenario-Based Testing

### 1. Mobile Network Simulation

Simulate mobile network conditions:

```python
class MobileNetworkScenario:
    def __init__(self, gns3_manager: GNS3Manager, project_id: str):
        self.manager = gns3_manager
        self.project_id = project_id
    
    def simulate_mobility(self, client_links: List[str]):
        """Simulate client mobility with varying network conditions"""
        
        scenarios = [
            # Good signal
            {"latency": "20ms", "bandwidth": "50Mbps", "packet_loss": 0.001},
            # Moderate signal
            {"latency": "80ms", "bandwidth": "10Mbps", "packet_loss": 0.01},
            # Poor signal
            {"latency": "200ms", "bandwidth": "2Mbps", "packet_loss": 0.05},
            # Handoff/disconnection
            {"latency": "500ms", "bandwidth": "1Mbps", "packet_loss": 0.2}
        ]
        
        import random
        import time
        
        for round_num in range(10):  # 10 FL rounds
            print(f"FL Round {round_num + 1}")
            
            for link_id in client_links:
                # Randomly select network condition
                condition = random.choice(scenarios)
                apply_network_conditions(self.project_id, link_id, condition)
                print(f"Applied condition to {link_id}: {condition}")
            
            # Wait for FL round to complete
            time.sleep(120)  # 2 minutes per round
```

### 2. Network Failure Simulation

Simulate network failures and recovery:

```python
def simulate_network_failure(project_id: str, link_id: str, duration: int):
    """Simulate link failure for specified duration"""
    
    print(f"Simulating network failure on link {link_id}")
    
    # Disable link (100% packet loss)
    apply_network_conditions(project_id, link_id, {
        "packet_loss": 1.0
    })
    
    # Wait for failure duration
    time.sleep(duration)
    
    # Restore link
    apply_network_conditions(project_id, link_id, {
        "packet_loss": 0.0
    })
    
    print(f"Network restored on link {link_id}")

# Example: Simulate 30-second network failure
simulate_network_failure(project_id, failing_link_id, 30)
```

### 3. Congestion Simulation

Simulate network congestion:

```python
def simulate_congestion(project_id: str, core_links: List[str]):
    """Simulate network congestion on core links"""
    
    congestion_levels = [
        {"name": "Light", "bandwidth": "800Mbps", "latency": "15ms"},
        {"name": "Moderate", "bandwidth": "400Mbps", "latency": "50ms"},
        {"name": "Heavy", "bandwidth": "100Mbps", "latency": "150ms"},
        {"name": "Severe", "bandwidth": "10Mbps", "latency": "300ms"}
    ]
    
    for level in congestion_levels:
        print(f"Applying {level['name']} congestion")
        
        for link_id in core_links:
            apply_network_conditions(project_id, link_id, {
                "bandwidth": level["bandwidth"],
                "latency": level["latency"]
            })
        
        # Run FL for 5 minutes under this congestion level
        time.sleep(300)
```

## Integration with FLOPY-NET Experiments

### 1. Experiment-Driven Network Conditions

Integrate GNS3 conditions with FL experiments:

```python
class GNS3ExperimentController:
    def __init__(self, gns3_manager: GNS3Manager, flopy_client):
        self.gns3 = gns3_manager
        self.flopy = flopy_client
    
    def run_experiment_with_conditions(self, experiment_config: Dict, network_scenario: Dict):
        """Run FL experiment with specific network conditions"""
        
        # Create FL experiment
        experiment = self.flopy.create_experiment(experiment_config)
        
        # Apply initial network conditions
        self.apply_scenario_conditions(network_scenario["initial"])
        
        # Start experiment
        self.flopy.start_experiment(experiment["id"])
        
        # Apply dynamic conditions during training
        for event in network_scenario["events"]:
            # Wait until event time
            time.sleep(event["delay"])
            
            # Apply network conditions
            self.apply_scenario_conditions(event["conditions"])
            
            print(f"Applied network event: {event['name']}")
        
        # Wait for experiment completion
        self.flopy.wait_for_completion(experiment["id"])
        
        return experiment
    
    def apply_scenario_conditions(self, conditions: Dict):
        """Apply network conditions to all relevant links"""
        for link_type, link_conditions in conditions.items():
            links = self.get_links_by_type(link_type)
            for link_id in links:
                apply_network_conditions(self.project_id, link_id, link_conditions)
```

### 2. Real-time Condition Adjustment

Adjust network conditions based on FL training progress:

```python
def adaptive_network_conditions(experiment_id: str, project_id: str):
    """Adjust network conditions based on FL performance"""
    
    while True:
        # Get current FL metrics
        metrics = requests.get(f"http://localhost:3001/api/v1/experiments/{experiment_id}").json()
        
        if metrics["status"] == "completed":
            break
        
        current_accuracy = metrics["metrics"]["global_accuracy"]
        current_round = metrics["metrics"]["current_round"]
        
        # Adjust network conditions based on performance
        if current_accuracy < 0.5 and current_round > 5:
            # Poor performance, improve network conditions
            improve_network_conditions(project_id)
            print("Improved network conditions due to poor FL performance")
        
        elif current_accuracy > 0.8:
            # Good performance, can handle some network stress
            stress_network_conditions(project_id)
            print("Added network stress due to good FL performance")
        
        time.sleep(60)  # Check every minute
```

## Monitoring GNS3 Integration

### 1. Network Topology Monitoring

Monitor GNS3 topology status:

```bash
# Get project status
curl http://localhost:3080/v2/projects/$PROJECT_ID

# Get all nodes status
curl http://localhost:3080/v2/projects/$PROJECT_ID/nodes

# Get all links status  
curl http://localhost:3080/v2/projects/$PROJECT_ID/links

# Get node console output
curl http://localhost:3080/v2/projects/$PROJECT_ID/nodes/$NODE_ID/console
```

### 2. Performance Monitoring

Monitor network performance within GNS3:

```python
def monitor_gns3_performance(project_id: str):
    """Monitor GNS3 network performance"""
    
    while True:
        # Get node statistics
        nodes_response = requests.get(f"http://localhost:3080/v2/projects/{project_id}/nodes")
        nodes = nodes_response.json()
        
        for node in nodes:
            if node["status"] == "started":
                # Get node resource usage
                stats_response = requests.get(
                    f"http://localhost:3080/v2/projects/{project_id}/nodes/{node['node_id']}/stats"
                )
                
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"Node {node['name']}: CPU {stats.get('cpu_usage', 0)}%, "
                          f"Memory {stats.get('memory_usage', 0)}MB")
        
        time.sleep(30)  # Monitor every 30 seconds
```

### 3. Integration Health Checks

Verify GNS3 integration health:

```bash
#!/bin/bash
# GNS3 Integration Health Check

echo "Checking GNS3 Server..."
if curl -s -f http://localhost:3080/v2/version > /dev/null; then
    echo "✓ GNS3 Server is running"
else
    echo "✗ GNS3 Server is not accessible"
    exit 1
fi

echo "Checking FLOPY-NET GNS3 Project..."
PROJECT_ID=$(curl -s http://localhost:3080/v2/projects | jq -r '.[] | select(.name=="FLOPY-NET-Testbed") | .project_id')

if [ -n "$PROJECT_ID" ]; then
    echo "✓ FLOPY-NET project found: $PROJECT_ID"
    
    # Check node status
    RUNNING_NODES=$(curl -s http://localhost:3080/v2/projects/$PROJECT_ID/nodes | jq '[.[] | select(.status=="started")] | length')
    TOTAL_NODES=$(curl -s http://localhost:3080/v2/projects/$PROJECT_ID/nodes | jq 'length')
    
    echo "✓ Nodes running: $RUNNING_NODES/$TOTAL_NODES"
else
    echo "✗ FLOPY-NET project not found"
    exit 1
fi

echo "GNS3 integration health check completed"
```

## Troubleshooting

### 1. Common Issues

**Issue: GNS3 Server Not Starting**
```bash
# Check Docker container logs
docker logs gns3-server

# Verify privileged mode
docker inspect gns3-server | grep Privileged

# Check port bindings
docker port gns3-server
```

**Issue: Nodes Not Starting**
```bash
# Check node status
curl http://localhost:3080/v2/projects/$PROJECT_ID/nodes/$NODE_ID

# View node console
curl http://localhost:3080/v2/projects/$PROJECT_ID/nodes/$NODE_ID/console

# Check Docker images
docker images | grep flopy-net
```

**Issue: Network Conditions Not Applied**
```bash
# Verify link exists
curl http://localhost:3080/v2/projects/$PROJECT_ID/links/$LINK_ID

# Check current filters
curl http://localhost:3080/v2/projects/$PROJECT_ID/links/$LINK_ID/filters

# Test connectivity
docker exec gns3-fl-client-01 ping FL-Server
```

### 2. Performance Issues

**High Resource Usage:**
```bash
# Monitor GNS3 server resources
docker stats gns3-server

# Reduce node resource limits
curl -X PUT http://localhost:3080/v2/projects/$PROJECT_ID/nodes/$NODE_ID \
  -d '{"properties": {"ram": 512, "cpus": 1}}'
```

**Slow Network Simulation:**
```bash
# Enable hardware acceleration
echo "net.core.netdev_max_backlog = 5000" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control = bbr" >> /etc/sysctl.conf
sysctl -p
```

## Best Practices

### 1. Project Organization

- Use descriptive project and node names
- Organize nodes by function (server, client, network)
- Document topology configurations
- Version control GNS3 project files

### 2. Resource Management

- Monitor GNS3 server resource usage
- Limit node resources appropriately
- Use snapshots for quick topology restoration
- Clean up unused projects regularly

### 3. Network Simulation

- Start with simple topologies and add complexity gradually
- Validate network conditions with ping/iperf tests
- Use realistic network parameters based on target environments
- Test edge cases (failures, congestion, mobility)

### 4. Integration Testing

- Test GNS3 integration before running experiments
- Verify network conditions are applied correctly
- Monitor both FL performance and network metrics
- Use automated scripts for repeatable testing

## Next Steps

- [Advanced Configurations](../tutorials/advanced-configuration.md) - Expert GNS3 integration setups
- [Troubleshooting](./troubleshooting.md) - Detailed troubleshooting procedures
- [Networking API Reference](../api/networking-api.md) - Programmatic network control
- [Development Guide](../development/setup.md) - Contributing to GNS3 integration
