---
sidebar_position: 2
---

# Quick Start

Get hands-on with FLOPY-NET in under 10 minutes! This guide will walk you through running your first federated learning experiment with network simulation.

## Step 1: Verify Installation

First, ensure FLOPY-NET is running:

```powershell
# Check that all services are up
docker-compose ps

# You should see all services with "Up" status:
# - policy-engine (192.168.100.20:5000)
# - fl-server (192.168.100.10:8080)  
# - fl-client-1 (192.168.100.101)
# - fl-client-2 (192.168.100.102)
# - collector (192.168.100.40:8000)
# - sdn-controller (192.168.100.41:6633)

# Check system health
curl http://localhost:5000/health  # Policy Engine
```

## Step 2: Access the System

The FLOPY-NET system provides multiple access points:

- **Policy Engine API**: http://localhost:5000 (Core system)
- **FL Server**: Internal port 8080 (Policy-controlled access)
- **Collector API**: http://localhost:8000 (Metrics and monitoring)
- **Dashboard**: Available when dashboard components are running

## Step 3: Run Your First Experiment

### Option A: Using the CLI (Recommended)

```powershell title="CLI Experiment"
# Navigate to the project directory
cd d:\dev\microfed\codebase

# List available scenarios
python src\main.py scenario list

# Run a basic scenario  
python src\main.py scenario run basic

# Start individual services
python src\main.py run policy-engine
python src\main.py run collector
python src\main.py run fl-server
```

### Option B: Using Docker Services

```powershell title="Docker-based Experiment"
# Start all services with docker-compose
docker-compose up -d

# View logs for specific services
docker-compose logs -f policy-engine
docker-compose logs -f fl-server
docker-compose logs -f collector

# Check container status
docker-compose ps
```

### Option C: Using the Policy Engine API

```powershell title="API-based Control"
# Get current policies
curl http://localhost:5000/policies

# Create a new policy
curl -X POST "http://localhost:5000/policies" `
  -H "Content-Type: application/json" `
  -d '{
    "name": "test-policy",
    "description": "Test policy for FL experiment",
    "rules": [{"condition": "client_count > 0", "action": "allow"}],
    "enabled": true
  }'
```

## Step 4: Monitor Your Experiment

### Real-time System Monitoring

The system provides multiple monitoring interfaces:

1. **Policy Engine Status**: Monitor policy enforcement and compliance
2. **FL Training Progress**: Track federated learning rounds and client participation
3. **Network Metrics**: View SDN statistics and traffic patterns  
4. **System Health**: Monitor container status and resource utilization

### Key Metrics to Watch

| Metric | API Endpoint | Description |
|--------|-------------|-------------|
| **Policy Status** | `GET /policies` | Active policies and enforcement |
| **FL Server Health** | Container logs | Training progress and client connections |
| **Network Stats** | Collector API | SDN controller and switch statistics |
| **Container Status** | `docker-compose ps` | Service health and uptime |

### Monitoring Commands

```powershell title="System Monitoring"
# Check Policy Engine status
curl http://localhost:5000/health

# View FL server logs
docker-compose logs -f fl-server

# Monitor collector metrics
curl http://localhost:8000/metrics

# Check all container status
docker-compose ps

# View network statistics (if available)
curl http://localhost:8000/network/stats
```

## Step 5: Explore Network Conditions

FLOPY-NET provides realistic network simulation through GNS3 and SDN integration:

### Network Topology Management

```powershell title="Network Control"
# Check GNS3 connectivity (if GNS3 server is available)
python scripts\check_gns3_connectivity.py

# View network topology configuration
Get-Content config\topology\basic_topology.json

# Check SDN controller status
curl http://localhost:8181/onos/v1/devices  # If SDN controller REST API is exposed
```
```powershell title="Network Impairments"
# Using the network control API (if available)
curl -X POST "http://localhost:8001/api/v1/network/impairments" `
  -H "Content-Type: application/json" `
  -d '{"type": "packet_loss", "value": 0.05, "nodes": ["client-1", "client-2"]}'
```

```json title="Latency Configuration"
{
  "network_conditions": {
    "latency": {
      "mean": 100,
      "std": 20,
      "unit": "ms"
    },
    "bandwidth": {
      "upload": "10Mbps", 
      "download": "50Mbps"
    }
  }
}
```

## Step 6: Examine Results

### Dashboard Analysis

1. **Navigate to Results**: Click on your completed experiment
2. **View Training Curves**: Analyze how network conditions affected convergence
3. **Network Impact**: Compare performance with and without network impairments
4. **Export Data**: Download results for further analysis

### Programmatic Access

```python title="Results Analysis"
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Get experiment results
response = requests.get("http://localhost:8001/api/v1/experiments/1/results")
results = response.json()

# Create training curve
df = pd.DataFrame(results['training_history'])
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(df['round'], df['accuracy'])
plt.title('Model Accuracy')
plt.xlabel('Round')
plt.ylabel('Accuracy')

plt.subplot(1, 2, 2)
plt.plot(df['round'], df['loss'])
plt.title('Model Loss')
plt.xlabel('Round')
plt.ylabel('Loss')

plt.tight_layout()
plt.show()
```

## Step 7: Try Advanced Scenarios

Now that you've run a basic experiment, try these advanced scenarios:

### Scenario 1: Non-IID Data Distribution

```bash title="Non-IID Experiment"
python -m src.main \
  --scenario non_iid_fl \
  --clients 5 \
  --rounds 20 \
  --dataset cifar10 \
  --data_distribution non_iid \
  --alpha 0.5
```

### Scenario 2: Byzantine Fault Tolerance

```bash title="Byzantine Clients"
python -m src.main \
  --scenario byzantine_fl \
  --clients 10 \
  --byzantine_clients 2 \
  --rounds 15 \
  --defense_mechanism krum
```

### Scenario 3: Edge Computing Simulation

```bash title="Edge Computing"
python -m src.main \
  --scenario edge_fl \
  --clients 20 \
  --client_resources heterogeneous \
  --network_topology star \
  --bandwidth_limit 1mbps
```

## Understanding Your Results

### What Good Results Look Like

✅ **Converging Accuracy**: Should increase and stabilize
✅ **Decreasing Loss**: Should decrease over rounds
✅ **Stable Round Times**: Consistent timing indicates healthy network
✅ **High Client Participation**: Most clients participating each round

### Warning Signs

⚠️ **Oscillating Metrics**: May indicate network instability
⚠️ **Slow Convergence**: Could suggest data distribution issues
⚠️ **Increasing Round Times**: May indicate network congestion
⚠️ **Low Participation**: Clients dropping out due to network issues

## Common Commands

Here are some frequently used commands:

```bash title="Useful Commands"
# List all experiments
curl http://localhost:8001/api/v1/experiments

# Stop a running experiment
curl -X POST http://localhost:8001/api/v1/experiments/1/stop

# Get system status
curl http://localhost:8001/api/v1/status

# View logs
docker-compose logs collector
docker-compose logs policy-engine

# Reset everything
docker-compose down && docker-compose up -d
```

## Next Steps

Congratulations! You've successfully run your first FLOPY-NET experiment. Here's what to explore next:

1. **[User Guide](../user-guide/running-experiments.md)** - Customize FLOPY-NET for your research
2. **[Basic Experiment Tutorial](../tutorials/basic-experiment.md)** - Detailed analysis of experiment results
3. **[User Guide](/docs/user-guide/running-experiments)** - Advanced experiment management
4. **[API Reference](/docs/api/overview)** - Programmatic control of FLOPY-NET

## Troubleshooting Quick Start

### Experiment Won't Start

```bash
# Check if all services are running
docker-compose ps

# Restart services if needed
docker-compose restart

# Check logs for errors
docker-compose logs
```

### Dashboard Not Loading

```bash
# Verify frontend is running
curl http://localhost:8085

# Check backend API
curl http://localhost:8001/health

# Clear browser cache and reload
```

### No Data in Dashboard

```bash
# Verify collector is running
curl http://localhost:8002/metrics

# Check if experiment is actually running
curl http://localhost:8001/api/v1/experiments
```

---

## Video Tutorial

Want to see this in action? Check out our [Quick Start Video Tutorial](https://www.youtube.com/watch?v=your-video-id) where we walk through each step.

## Community Examples

Join our community to see what others are building:

- [FLOPY-NET Examples Repository](https://github.com/abdulmelink/flopy-net-examples)
- [Research Papers Using FLOPY-NET](https://github.com/abdulmelink/flopy-net/wiki/Research-Papers)
- [Community Discord](https://discord.gg/flopy-net)
