---
sidebar_position: 1
---

# Basic Federated Learning Experiment

This tutorial walks you through running your first federated learning experiment with FLOPY-NET, from setup to analyzing results.

## Prerequisites

Before starting this tutorial, ensure you have:

- FLOPY-NET installed and configured (see [Installation Guide](../getting-started/installation.md))
- Docker and Docker Compose installed
- GNS3 server running (optional for network simulation)
- Basic understanding of federated learning concepts

## Overview

In this tutorial, you will:

1. Set up a basic FL experiment with 3 clients
2. Configure network conditions
3. Monitor the training process
4. Analyze the results

## Step 1: Environment Setup

### Start the Core Services

First, start the essential FLOPY-NET services:

```bash
# Navigate to the project root
cd path/to/flopy-net

# Start core services
docker-compose up -d policy-engine collector dashboard-backend dashboard-frontend
```

Wait for all services to be healthy:

```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs -f policy-engine collector
```

### Verify Dashboard Access

Open your browser and navigate to:
- **Dashboard**: http://localhost:8085
- **API Documentation**: http://localhost:8001/docs

You should see the FLOPY-NET dashboard with system status indicators.

## Step 2: Configure the Experiment

### Create Experiment Configuration

Create a new experiment configuration file:

```json
{
  "experiment_id": "tutorial_basic_001",
  "name": "Basic FL Tutorial Experiment",
  "description": "First federated learning experiment with 3 clients",
  "fl_config": {
    "algorithm": "FedAvg",
    "rounds": 10,
    "clients_per_round": 3,
    "local_epochs": 5,
    "learning_rate": 0.01,
    "dataset": "mnist",
    "model": "simple_cnn"
  },
  "network_config": {
    "simulation_enabled": false,
    "latency_ms": 50,
    "bandwidth_mbps": 100,
    "packet_loss": 0.001
  },
  "policies": [
    {
      "name": "basic_training_policy",
      "enabled": true,
      "rules": [
        {
          "condition": "client_count < 3",
          "action": "wait_for_clients",
          "timeout": 300
        },
        {
          "condition": "accuracy < 0.1",
          "action": "log_warning",
          "message": "Low accuracy detected"
        }
      ]
    }
  ]
}
```

Save this as `configs/experiments/tutorial_basic_001.json`.

### Load Dataset

Ensure the MNIST dataset is available:

```bash
# Check if dataset exists
ls data/datasets/mnist/

# If not present, download it
python -m src.utils.dataset_downloader --dataset mnist --output data/datasets/
```

## Step 3: Start the FL Server

### Configure FL Server

Create the FL server configuration:

```json
{
  "server_id": "fl-server-tutorial",
  "host": "0.0.0.0",
  "port": 8080,
  "experiment_config": "./configs/experiments/tutorial_basic_001.json",
  "model_config": {
    "architecture": "simple_cnn",
    "input_shape": [28, 28, 1],
    "num_classes": 10
  },
  "aggregation": {
    "strategy": "fedavg",
    "min_clients": 3,
    "max_wait_time": 300
  },
  "policy_engine": {
    "url": "http://localhost:5000",
    "check_interval": 10
  }
}
```

Save as `configs/fl_server/tutorial_server_config.json`.

### Start FL Server

```bash
# Start FL server
docker-compose up -d fl-server

# Monitor FL server logs
docker-compose logs -f fl-server
```

You should see output indicating the server is waiting for clients:

```
[INFO] FL Server started on 0.0.0.0:8080
[INFO] Waiting for 3 clients to connect...
[INFO] Policy Engine connected: http://localhost:5000
```

## Step 4: Start FL Clients

### Client Configuration

Create configurations for 3 clients with different data distributions:

**Client 1 (IID Data):**
```json
{
  "client_id": "client-1",
  "server_url": "http://localhost:8080",
  "data_config": {
    "dataset": "mnist",
    "data_split": "iid",
    "samples_per_client": 1000,
    "classes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  },
  "training_config": {
    "local_epochs": 5,
    "batch_size": 32,
    "learning_rate": 0.01
  },
  "policy_compliance": {
    "max_model_size_mb": 10,
    "privacy_level": "standard",
    "resource_limits": {
      "cpu_percent": 80,
      "memory_mb": 512
    }
  }
}
```

**Client 2 (Non-IID - Digits 0-4):**
```json
{
  "client_id": "client-2",
  "server_url": "http://localhost:8080",
  "data_config": {
    "dataset": "mnist",
    "data_split": "non_iid",
    "samples_per_client": 800,
    "classes": [0, 1, 2, 3, 4]
  },
  "training_config": {
    "local_epochs": 5,
    "batch_size": 32,
    "learning_rate": 0.01
  },
  "policy_compliance": {
    "max_model_size_mb": 10,
    "privacy_level": "standard",
    "resource_limits": {
      "cpu_percent": 70,
      "memory_mb": 512
    }
  }
}
```

**Client 3 (Non-IID - Digits 5-9):**
```json
{
  "client_id": "client-3",
  "server_url": "http://localhost:8080",
  "data_config": {
    "dataset": "mnist",
    "data_split": "non_iid",
    "samples_per_client": 1200,
    "classes": [5, 6, 7, 8, 9]
  },
  "training_config": {
    "local_epochs": 5,
    "batch_size": 32,
    "learning_rate": 0.01
  },
  "policy_compliance": {
    "max_model_size_mb": 10,
    "privacy_level": "standard",
    "resource_limits": {
      "cpu_percent": 60,
      "memory_mb": 512
    }
  }
}
```

Save these as:
- `configs/fl_client/tutorial_client_1.json`
- `configs/fl_client/tutorial_client_2.json`
- `configs/fl_client/tutorial_client_3.json`

### Start FL Clients

```bash
# Start all clients
docker-compose up -d fl-client-1 fl-client-2 fl-client-3

# Monitor client connections
docker-compose logs -f fl-client-1 fl-client-2 fl-client-3
```

You should see clients connecting to the server:

```
[INFO] Client client-1 connected to FL server
[INFO] Client client-2 connected to FL server
[INFO] Client client-3 connected to FL server
[INFO] Starting federated learning with 3 clients
```

## Step 5: Monitor the Experiment

### Dashboard Monitoring

1. **Open the Dashboard**: Navigate to http://localhost:8085

2. **FL Monitoring Tab**: 
   - View real-time training progress
   - Monitor accuracy and loss curves
   - Check client participation rates

3. **Network Tab**:
   - Observe network topology
   - Monitor network performance metrics
   - Check for any network issues

4. **Policy Tab**:
   - Verify policy compliance
   - Monitor trust scores
   - Check for policy violations

### CLI Monitoring

Monitor the experiment progress via command line:

```bash
# Check experiment status
python -m src.main scenario --list-running

# Get current round information
curl http://localhost:8080/api/v1/status

# Monitor policy compliance
curl http://localhost:5000/api/v1/compliance/status
```

### Log Analysis

Monitor system logs for detailed information:

```bash
# FL Server logs
docker-compose logs -f fl-server | grep "Round\|Accuracy\|Loss"

# Client training logs
docker-compose logs -f fl-client-1 | grep "Training\|Accuracy"

# Policy engine logs
docker-compose logs -f policy-engine | grep "Policy\|Compliance"
```

## Step 6: Analyze Results

### Real-time Metrics

As the experiment runs, you'll see:

1. **Round Progress**: Each round takes ~2-3 minutes
2. **Accuracy Improvement**: Should improve from ~0.1 to ~0.9+
3. **Loss Reduction**: Should decrease from ~2.3 to ~0.3
4. **Client Participation**: All 3 clients should participate in each round

Expected progress:

| Round | Global Accuracy | Global Loss | Participants |
|-------|----------------|-------------|--------------|
| 1     | 0.12           | 2.28        | 3/3          |
| 2     | 0.24           | 1.89        | 3/3          |
| 3     | 0.41           | 1.52        | 3/3          |
| 4     | 0.56           | 1.21        | 3/3          |
| 5     | 0.68           | 0.98        | 3/3          |
| 6     | 0.77           | 0.81        | 3/3          |
| 7     | 0.84           | 0.67        | 3/3          |
| 8     | 0.88           | 0.56        | 3/3          |
| 9     | 0.91           | 0.48        | 3/3          |
| 10    | 0.93           | 0.42        | 3/3          |

### Export Results

Export experiment data for analysis:

```bash
# Export training metrics
curl "http://localhost:8083/api/v1/export" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_id": "tutorial_basic_001",
    "components": ["fl", "network", "policy"],
    "format": "json"
  }'

# Download the export
wget http://localhost:8083/api/v1/downloads/{export_id}
```

### Analyze with Python

Create a simple analysis script:

```python
import json
import pandas as pd
import matplotlib.pyplot as plt

# Load exported data
with open('tutorial_basic_001_export.json', 'r') as f:
    data = json.load(f)

# Extract FL metrics
fl_metrics = data['fl_metrics']
rounds = [r['round_number'] for r in fl_metrics]
accuracy = [r['global_accuracy'] for r in fl_metrics]
loss = [r['global_loss'] for r in fl_metrics]

# Create plots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Accuracy plot
ax1.plot(rounds, accuracy, 'b-', marker='o')
ax1.set_title('Global Model Accuracy')
ax1.set_xlabel('Round')
ax1.set_ylabel('Accuracy')
ax1.grid(True)

# Loss plot
ax2.plot(rounds, loss, 'r-', marker='s')
ax2.set_title('Global Model Loss')
ax2.set_xlabel('Round')
ax2.set_ylabel('Loss')
ax2.grid(True)

plt.tight_layout()
plt.savefig('tutorial_results.png')
plt.show()

print(f"Final Accuracy: {accuracy[-1]:.3f}")
print(f"Final Loss: {loss[-1]:.3f}")
print(f"Convergence achieved in {len(rounds)} rounds")
```

## Step 7: Cleanup

When the experiment is complete, clean up resources:

```bash
# Stop all services
docker-compose down

# Clean up experiment data (optional)
rm -rf results/tutorial_basic_001/

# View experiment summary
python -m src.main scenario --show-results tutorial_basic_001
```

## Expected Output

After successful completion, you should see:

1. **Final Accuracy**: ~93% on MNIST test set
2. **Convergence**: Model converges in ~10 rounds
3. **Policy Compliance**: 100% compliance rate
4. **Network Performance**: No significant bottlenecks
5. **Client Participation**: All clients participate in all rounds

## Next Steps

Now that you've completed your first experiment:

1. **Try Different Scenarios**: Explore the [Custom Scenarios Tutorial](./custom-scenarios.md)
2. **Add Network Simulation**: Enable GNS3 integration for realistic network conditions
3. **Experiment with Policies**: Create custom policies for your use cases
4. **Scale Up**: Try experiments with more clients and different data distributions

## Troubleshooting

### Common Issues

1. **Clients Not Connecting**:
   ```bash
   # Check FL server logs
   docker-compose logs fl-server
   
   # Verify server is accessible
   curl http://localhost:8080/health
   ```

2. **Low Accuracy**:
   - Check data distribution balance
   - Verify learning rate settings
   - Ensure sufficient local epochs

3. **Policy Violations**:
   ```bash
   # Check policy status
   curl http://localhost:5000/api/v1/policies/violations
   
   # Review policy logs
   docker-compose logs policy-engine
   ```

4. **Network Issues**:
   - Verify all services are running
   - Check port availability
   - Review firewall settings

For more detailed troubleshooting, see the [Troubleshooting Guide](../user-guide/troubleshooting.md).

## Conclusion

Congratulations! You've successfully run your first federated learning experiment with FLOPY-NET. This tutorial demonstrated:

- Basic FL experiment setup and configuration
- Multi-client federated learning with different data distributions
- Real-time monitoring and policy compliance
- Results analysis and visualization

The platform provides comprehensive tools for federated learning research, from simple experiments to complex multi-scenario studies with realistic network conditions.
