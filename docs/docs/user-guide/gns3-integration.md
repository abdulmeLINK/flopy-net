# GNS3 Integration

This guide covers integrating FLOPY-NET with GNS3 for realistic network simulation, enabling comprehensive testing of federated learning systems under various network conditions and topologies.

## Overview

GNS3 (Graphical Network Simulator-3) integration provides:

- **Realistic Network Topologies**: Complex multi-hop networks, WAN links, different access technologies
- **Dynamic Network Conditions**: Latency injection, bandwidth limitations, packet loss simulation
- **Network Device Simulation**: Routers, switches, firewalls, load balancers
- **Topology Management**: Programmatic network configuration and control
- **Condition Injection**: Real-time network impairment simulation

## Prerequisites

### 1. GNS3 Installation

Install GNS3 server:

```bash
# Install GNS3 server via Docker
docker pull gns3/gns3server:latest

# Or install natively on Ubuntu/Debian
sudo apt update
sudo apt install -y python3-pip
pip3 install gns3-server

# For GUI client (optional)
sudo apt install -y gns3-gui
```

### 2. Configure GNS3 Server

Create GNS3 server configuration:

```bash
# Create configuration directory
mkdir -p ~/.config/GNS3/2.2

# Configure server settings
cat > ~/.config/GNS3/2.2/gns3_server.conf << EOF
[Server]
host = 0.0.0.0
port = 3080
images_path = /opt/gns3/images
projects_path = /opt/gns3/projects
appliances_path = /opt/gns3/appliances
configs_path = /opt/gns3/configs

[Qemu]
enable_hardware_acceleration = true
require_hardware_acceleration = false

[Dynamips]
allocate_hypervisor_per_device = true
memory_usage_limit_per_hypervisor = 1024

[Docker]
enable = true
EOF
```

### 3. Start GNS3 Services

```bash
# Start GNS3 server
docker run -d \
  --name gns3-server \
  --privileged \
  -p 3080:3080 \
  -v /opt/gns3:/opt/gns3 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  gns3/gns3server:latest

# Verify GNS3 server is running
curl http://localhost:3080/v2/version
```

## FLOPY-NET GNS3 Integration

### 1. Configure Integration

Update FLOPY-NET configuration:

```yaml
# config/gns3_integration.yml
gns3:
  enabled: true
  server_url: "http://localhost:3080"
  api_version: "v2"
  auth:
    username: ""  # Leave empty for no auth
    password: ""
  
  default_project: "flopy-net-testbed"
  
  templates:
    - name: "Ubuntu Docker"
      template_id: "docker-ubuntu"
      symbol: "docker"
    - name: "OpenVSwitch"
      template_id: "openvswitch"
      symbol: "ethernet_switch"
  
  network_conditions:
    latency_range: [10, 200]  # ms
    bandwidth_range: [1, 1000]  # Mbps
    packet_loss_range: [0, 0.1]  # percentage
```

### 2. Initialize GNS3 Project

Create a new GNS3 project for FLOPY-NET:

```bash
curl -X POST http://localhost:3080/v2/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "flopy-net-testbed",
    "project_id": "12345678-1234-1234-1234-123456789abc"
  }'
```

### 3. Define Network Topology

Create a topology configuration:

```json
{
  "topology": {
    "name": "FLOPY-NET Federated Learning Testbed",
    "nodes": [
      {
        "name": "FL-Server",
        "node_type": "docker",
        "template": "flopy-net/fl-server:latest",
        "ports": [
          {"name": "eth0", "port_number": 0}
        ],
        "properties": {
          "image": "flopy-net/fl-server:latest",
          "environment": "FL_SERVER_PORT=8080",
          "extra_hosts": "host.docker.internal:host-gateway"
        }
      },
      {
        "name": "SDN-Controller",
        "node_type": "docker", 
        "template": "flopy-net/sdn-controller:latest",
        "ports": [
          {"name": "eth0", "port_number": 0}
        ]
      },
      {
        "name": "Core-Switch",
        "node_type": "ethernet_switch",
        "template": "ethernet_switch",
        "ports": [
          {"name": "Ethernet0", "port_number": 0},
          {"name": "Ethernet1", "port_number": 1},
          {"name": "Ethernet2", "port_number": 2},
          {"name": "Ethernet3", "port_number": 3}
        ]
      },
      {
        "name": "Edge-Switch-1",
        "node_type": "ethernet_switch",
        "template": "ethernet_switch"
      },
      {
        "name": "Edge-Switch-2", 
        "node_type": "ethernet_switch",
        "template": "ethernet_switch"
      }
    ],
    "links": [
      {
        "source": {"node": "FL-Server", "port": 0},
        "destination": {"node": "Core-Switch", "port": 0}
      },
      {
        "source": {"node": "SDN-Controller", "port": 0},
        "destination": {"node": "Core-Switch", "port": 1}
      },
      {
        "source": {"node": "Core-Switch", "port": 2},
        "destination": {"node": "Edge-Switch-1", "port": 0}
      },
      {
        "source": {"node": "Core-Switch", "port": 3},
        "destination": {"node": "Edge-Switch-2", "port": 0}
      }
    ]
  }
}
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
            }
        ]
        
        # Connect FL clients to core switch
        for i in range(1, 6):
            links.append({
                "nodes": [
                    {"node_id": node_ids[f"FL-Client-{i:02d}"], "adapter_number": 0, "port_number": 0},
                    {"node_id": node_ids["Core-Switch"], "adapter_number": 0, "port_number": i + 1}
                ]
            })
        
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
