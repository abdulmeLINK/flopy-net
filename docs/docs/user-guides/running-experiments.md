# Running Experiments

This guide walks you through setting up, running, and monitoring federated learning experiments in FLOPY-NET. You'll learn how to configure experiments, manage clients, and analyze results.

## Prerequisites

Before running experiments, ensure you have:

- FLOPY-NET system deployed and running
- Access to the Dashboard (http://localhost:8085)
- At least 3 FL clients configured and available
- GNS3 network simulation environment (optional but recommended)
- Basic understanding of federated learning concepts

## Quick Start

### 1. Basic Experiment Setup

The simplest way to run an experiment is through the Dashboard interface:

1. **Access the Dashboard**
   ```
   http://localhost:8085
   ```

2. **Navigate to Experiments**
   - Click on "Experiments" in the sidebar
   - Select "Create New Experiment"

3. **Configure Basic Settings**
   ```yaml
   Experiment Name: "CIFAR-10 Basic Training"
   Dataset: CIFAR-10
   Model: CNN
   Rounds: 10
   Minimum Clients: 3
   ```

4. **Start Experiment**
   - Review configuration
   - Click "Start Experiment"
   - Monitor progress in real-time

### 2. Command Line Experiment

For programmatic control, use the command line interface:

```bash
# Start a basic experiment
python -m src.main scenario basic_federated_learning \
  --rounds 10 \
  --min-clients 3 \
  --dataset cifar10 \
  --model cnn

# Monitor experiment progress
python -m src.main scenario status --experiment-id exp_2025_001
```

## Experiment Configuration

### Dataset Configuration

FLOPY-NET supports multiple datasets with different data distribution strategies:

#### CIFAR-10 Configuration
```json
{
  "dataset": {
    "name": "CIFAR-10",
    "split_strategy": "iid",
    "num_classes": 10,
    "client_data_distribution": {
      "strategy": "equal",
      "samples_per_client": 1000
    },
    "data_augmentation": {
      "enabled": true,
      "techniques": ["rotation", "flip", "noise"]
    }
  }
}
```

#### Non-IID Distribution
```json
{
  "dataset": {
    "name": "CIFAR-10",
    "split_strategy": "non_iid",
    "non_iid_config": {
      "alpha": 0.5,
      "min_samples_per_client": 100,
      "class_distribution": "dirichlet"
    }
  }
}
```

#### Custom Dataset
```json
{
  "dataset": {
    "name": "custom",
    "data_path": "/data/custom_dataset",
    "format": "pytorch",
    "preprocessing": {
      "normalize": true,
      "resize": [32, 32],
      "transforms": ["to_tensor", "normalize"]
    }
  }
}
```

### Model Configuration

#### CNN Model
```json
{
  "model": {
    "architecture": "CNN",
    "config": {
      "conv_layers": [
        {"channels": 32, "kernel_size": 3, "padding": 1},
        {"channels": 64, "kernel_size": 3, "padding": 1},
        {"channels": 128, "kernel_size": 3, "padding": 1}
      ],
      "fc_layers": [512, 256],
      "dropout": 0.5,
      "activation": "relu",
      "num_classes": 10
    }
  }
}
```

#### ResNet Model
```json
{
  "model": {
    "architecture": "ResNet",
    "config": {
      "depth": 18,
      "num_classes": 10,
      "pretrained": false,
      "freeze_backbone": false
    }
  }
}
```

#### Custom Model
```json
{
  "model": {
    "architecture": "custom",
    "model_path": "/models/custom_model.py",
    "class_name": "CustomNet",
    "config": {
      "custom_param1": "value1",
      "custom_param2": 42
    }
  }
}
```

### Training Configuration

#### Basic Training Settings
```json
{
  "training": {
    "rounds": 20,
    "local_epochs": 3,
    "batch_size": 32,
    "learning_rate": 0.01,
    "optimizer": "SGD",
    "optimizer_config": {
      "momentum": 0.9,
      "weight_decay": 1e-4
    },
    "lr_scheduler": {
      "type": "step",
      "step_size": 10,
      "gamma": 0.1
    }
  }
}
```

#### Advanced Training Settings
```json
{
  "training": {
    "rounds": 50,
    "local_epochs": 5,
    "batch_size": 64,
    "learning_rate": 0.001,
    "optimizer": "Adam",
    "optimizer_config": {
      "betas": [0.9, 0.999],
      "eps": 1e-8,
      "weight_decay": 1e-5
    },
    "loss_function": "cross_entropy",
    "metrics": ["accuracy", "f1_score", "precision", "recall"],
    "early_stopping": {
      "enabled": true,
      "patience": 5,
      "min_delta": 0.001
    }
  }
}
```

### Federated Learning Settings

#### Client Selection
```json
{
  "federated_config": {
    "client_selection": {
      "strategy": "random",
      "fraction": 0.8,
      "min_clients": 5,
      "max_clients": 20
    },
    "aggregation": {
      "algorithm": "FedAvg",
      "weighted": true,
      "weight_strategy": "sample_size"
    },
    "convergence_criteria": {
      "target_accuracy": 0.85,
      "patience": 10,
      "min_improvement": 0.001
    }
  }
}
```

#### Alternative Aggregation Strategies
```json
{
  "federated_config": {
    "aggregation": {
      "algorithm": "FedProx",
      "mu": 0.01,
      "weighted": true
    }
  }
}
```

```json
{
  "federated_config": {
    "aggregation": {
      "algorithm": "FedNova",
      "rho": 0.9,
      "weighted": true
    }
  }
}
```

## Network Scenarios

### Basic Network Setup

For experiments without network simulation:

```json
{
  "network_config": {
    "simulation": false,
    "client_network": {
      "bandwidth": "unlimited",
      "latency": 0,
      "packet_loss": 0
    }
  }
}
```

### GNS3 Network Simulation

For realistic network conditions:

```json
{
  "network_config": {
    "simulation": true,
    "gns3_config": {
      "project_name": "FL_Experiment_Network",
      "topology_file": "config/topology/realistic_wan.json"
    },
    "network_conditions": {
      "wan_latency": "50-200ms",
      "bandwidth_limit": "10-100Mbps",
      "packet_loss": "0.1-1%",
      "jitter": "5-15ms"
    }
  }
}
```

### Challenging Network Scenarios

#### High Latency Scenario
```json
{
  "network_config": {
    "scenario": "high_latency",
    "parameters": {
      "base_latency": "200ms",
      "latency_variation": "±50ms",
      "timeout_multiplier": 2.0
    }
  }
}
```

#### Bandwidth Constrained
```json
{
  "network_config": {
    "scenario": "low_bandwidth",
    "parameters": {
      "max_bandwidth": "1Mbps",
      "bandwidth_sharing": true,
      "compression": true
    }
  }
}
```

#### Unreliable Network
```json
{  
  "network_config": {
    "scenario": "unreliable",
    "parameters": {
      "packet_loss_rate": "5%",
      "connection_drops": true,
      "reconnect_delay": "10-30s"
    }
  }
}
```

## Complete Experiment Examples

### Example 1: Basic CIFAR-10 Experiment

```json
{
  "experiment_name": "CIFAR-10 Basic CNN",
  "description": "Baseline federated learning experiment with CIFAR-10",
  "dataset": {
    "name": "CIFAR-10",
    "split_strategy": "iid",
    "samples_per_client": 1000
  },
  "model": {
    "architecture": "CNN",
    "config": {
      "conv_layers": [
        {"channels": 32, "kernel_size": 3},
        {"channels": 64, "kernel_size": 3}
      ],
      "fc_layers": [128],
      "num_classes": 10
    }
  },
  "training": {
    "rounds": 20,
    "local_epochs": 3,
    "batch_size": 32,
    "learning_rate": 0.01,
    "optimizer": "SGD"
  },
  "federated_config": {
    "client_selection": {
      "fraction": 0.8,
      "min_clients": 5
    },
    "aggregation": {
      "algorithm": "FedAvg",
      "weighted": true
    }
  },
  "network_config": {
    "simulation": false
  },
  "monitoring": {
    "metrics": ["accuracy", "loss", "round_time"],
    "save_models": true,
    "checkpoint_interval": 5
  }
}
```

### Example 2: Non-IID with Network Simulation

```json
{
  "experiment_name": "Non-IID Realistic Network",
  "description": "Non-IID data distribution with realistic network conditions",
  "dataset": {
    "name": "CIFAR-10",
    "split_strategy": "non_iid",
    "non_iid_config": {
      "alpha": 0.1,
      "min_samples_per_client": 500
    }
  },
  "model": {
    "architecture": "ResNet",
    "config": {
      "depth": 18,
      "num_classes": 10
    }
  },
  "training": {
    "rounds": 50,
    "local_epochs": 5,
    "batch_size": 64,
    "learning_rate": 0.001,
    "optimizer": "Adam"
  },
  "federated_config": {
    "client_selection": {
      "fraction": 0.6,
      "min_clients": 8
    },
    "aggregation": {
      "algorithm": "FedProx",
      "mu": 0.01
    }
  },
  "network_config": {
    "simulation": true,
    "scenario": "wan_realistic",
    "parameters": {
      "latency": "50-200ms",
      "bandwidth": "5-50Mbps",
      "packet_loss": "0.5%"
    }
  },
  "policy_config": {
    "trust_threshold": 0.7,
    "max_client_failures": 3
  }
}
```

### Example 3: Edge Computing Scenario

```json
{
  "experiment_name": "Edge Computing FL",
  "description": "Federated learning in edge computing environment",
  "dataset": {
    "name": "custom_iot_data",
    "data_path": "/data/iot_sensors",
    "split_strategy": "geographical"
  },
  "model": {
    "architecture": "lightweight_cnn",
    "config": {
      "channels": [16, 32],
      "fc_layers": [64],
      "quantization": true
    }
  },
  "training": {
    "rounds": 100,
    "local_epochs": 10,
    "batch_size": 16,
    "learning_rate": 0.005
  },
  "federated_config": {
    "client_selection": {
      "strategy": "resource_aware",
      "fraction": 0.5,
      "resource_requirements": {
        "min_memory": "512MB",
        "min_cpu": "1 core"
      }
    },
    "aggregation": {
      "algorithm": "FedAvg",
      "compression": true
    }
  },
  "network_config": {
    "simulation": true,
    "scenario": "edge_network",
    "parameters": {
      "edge_latency": "10-50ms",
      "cloud_latency": "100-300ms",
      "mobile_bandwidth": "1-10Mbps"
    }
  }
}
```

## Running Experiments

### Via Dashboard

1. **Create Experiment Configuration**
   - Use the Dashboard's experiment wizard
   - Upload custom configuration JSON
   - Clone from existing experiments

2. **Configure Clients**
   - Register available clients
   - Set client-specific parameters
   - Test client connectivity

3. **Start Experiment**
   - Review final configuration
   - Start training
   - Monitor real-time progress

### Via Command Line

```bash
# Create experiment from config file
python -m src.main experiment create --config experiments/my_experiment.json

# Start experiment
python -m src.main experiment start --id exp_2025_001

# Monitor progress
python -m src.main experiment monitor --id exp_2025_001

# Stop experiment
python -m src.main experiment stop --id exp_2025_001
```

### Via Python API

```python
from src.fl.server import FLServer
from src.experiments import ExperimentManager

# Create experiment manager
exp_manager = ExperimentManager()

# Create experiment
experiment = exp_manager.create_experiment({
    "name": "My Experiment",
    "config": experiment_config
})

# Start experiment
exp_manager.start_experiment(experiment.id)

# Monitor progress
for update in exp_manager.monitor_experiment(experiment.id):
    print(f"Round {update.round}: Accuracy = {update.accuracy}")
```

## Monitoring and Analysis

### Real-time Monitoring

The Dashboard provides real-time monitoring with:

- **Training Progress**: Accuracy and loss curves
- **Client Status**: Active clients and their performance
- **Network Metrics**: Latency, bandwidth, packet loss
- **System Health**: Resource utilization and errors

### Key Metrics to Monitor

#### Training Metrics
- Global model accuracy and loss
- Per-client local accuracy
- Convergence rate
- Round duration

#### Network Metrics
- Communication time per round
- Network latency between clients and server
- Bandwidth utilization
- Connection stability

#### System Metrics
- CPU and memory usage
- Client availability
- Policy compliance
- Trust scores

### Analysis Tools

#### Experiment Comparison
```python
from src.analysis import ExperimentAnalyzer

analyzer = ExperimentAnalyzer()

# Compare two experiments
comparison = analyzer.compare_experiments(
    experiment_ids=["exp_2025_001", "exp_2025_002"],
    metrics=["accuracy", "convergence_rate", "communication_cost"]
)

print(comparison.summary())
```

#### Statistical Analysis
```python
# Generate experiment report
report = analyzer.generate_report(
    experiment_id="exp_2025_001",
    include_plots=True,
    export_format="pdf"
)
```

## Troubleshooting Common Issues

### Client Connection Issues

**Problem**: Clients not connecting to server
```bash
# Check client connectivity
python -m src.utils.network_test --client-id client-001

# Test FL server availability
curl http://localhost:8080/health
```

**Solution**: 
- Verify network configuration
- Check firewall settings
- Ensure correct server URL in client config

### Training Convergence Issues

**Problem**: Model not converging or poor accuracy

**Analysis**:
```python # Check data distribution
analyzer.analyze_data_distribution(experiment_id="exp_2025_001")

# Examine client performance
analyzer.analyze_client_performance(experiment_id="exp_2025_001")
```

**Solutions**:
- Adjust learning rate
- Increase local epochs
- Check data quality and distribution
- Review client selection strategy

### Network Performance Issues

**Problem**: High communication delays

**Monitoring**:
```bash
# Monitor network metrics
python -m src.utils.network_monitor --experiment-id exp_2025_001
```

**Solutions**:
- Enable model compression
- Adjust communication frequency
- Optimize network topology
- Use adaptive timeout settings

### Resource Constraints

**Problem**: Clients running out of memory or compute

**Monitoring**:
```python
# Check resource usage
resource_monitor.get_client_resources(client_id="client-001")
```

**Solutions**:
- Reduce batch size
- Use gradient compression
- Implement client selection based on resources
- Scale down model complexity

## Best Practices

### Experiment Design

1. **Start Simple**: Begin with basic configurations and gradually add complexity
2. **Control Variables**: Change one parameter at a time for clear comparisons
3. **Multiple Runs**: Run experiments multiple times for statistical significance
4. **Document Everything**: Keep detailed records of configurations and results

### Performance Optimization

1. **Resource Management**: Monitor and optimize resource usage
2. **Network Optimization**: Use compression and efficient communication protocols
3. **Model Efficiency**: Choose appropriate model sizes for your constraints
4. **Client Selection**: Implement smart client selection strategies

### Security and Privacy

1. **Policy Compliance**: Ensure all experiments follow configured policies
2. **Trust Management**: Monitor client trust scores and behavior
3. **Data Privacy**: Implement differential privacy when required
4. **Secure Communication**: Use encrypted communication channels

### Reproducibility

1. **Version Control**: Track all configuration changes
2. **Random Seeds**: Set fixed random seeds for reproducible results
3. **Environment**: Document software versions and dependencies
4. **Data Snapshots**: Maintain consistent dataset versions

## Advanced Features

### Custom Aggregation Algorithms

```python
from src.fl.aggregation import BaseAggregator

class CustomAggregator(BaseAggregator):
    def aggregate(self, client_updates, weights):
        # Implement custom aggregation logic
        return aggregated_model
```

### Adaptive Learning Rates

```json
{
  "training": {
    "lr_scheduler": {
      "type": "adaptive_fl",
      "adaptation_strategy": "convergence_based",
      "parameters": {
        "initial_lr": 0.01,
        "min_lr": 0.001,
        "adaptation_factor": 0.8
      }
    }
  }
}
```

### Dynamic Client Selection

```python
from src.fl.client_selection import ResourceAwareSelector

selector = ResourceAwareSelector(
    resource_weights={
        "cpu": 0.3,
        "memory": 0.3,
        "network": 0.4
    },
    min_resources={
        "cpu_cores": 2,
        "memory_gb": 4,
        "bandwidth_mbps": 10
    }
)
```

This comprehensive guide provides everything you need to successfully run federated learning experiments in FLOPY-NET, from basic setups to advanced scenarios with realistic network conditions.
