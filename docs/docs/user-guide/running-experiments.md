---
sidebar_position: 1
---

# Running Experiments

Learn how to set up, configure, and execute federated learning simulation experiments in FLOPY-NET. This guide covers everything from basic simulation scenarios to advanced research configurations using the GNS3-based scenario architecture.

> **Note**: The current FLOPY-NET implementation simulates federated learning training using random data to demonstrate network effects, policy enforcement, and system monitoring. The FL client and server components can be extended for real machine learning workloads in research scenarios.

## Experiment Lifecycle in FLOPY-NET

FLOPY-NET uses a scenario-driven architecture where experiments are defined through GNS3 scenario configurations. The experiment lifecycle follows a structured approach from design through analysis:

```mermaid
graph LR
    A[Design Scenario] --> B[Configure Components]
    B --> C[Deploy to GNS3]
    C --> D[Execute Simulation]
    D --> E[Monitor Network & FL]
    E --> F[Collect Metrics]
    F --> G[Analyze Results]
    
    style A fill:#79c0ff,stroke:#333,stroke-width:2px,color:#000
    style D fill:#7ce38b,stroke:#333,stroke-width:2px,color:#000
    style F fill:#ffa7c4,stroke:#333,stroke-width:2px,color:#000
```

The scenario-based execution allows researchers to study federated learning under realistic network conditions, policy constraints, and system monitoring while maintaining reproducible experimental setups.

## Running Simulation Experiments

### Using Scenario Files (Recommended)

FLOPY-NET experiments are executed through scenario files that define the complete experiment setup, including network topology, FL configuration, and monitoring requirements.

**Basic Scenario Execution:**
```bash
# Execute a predefined scenario
python -m src.scenarios.run_scenario --scenario config/scenarios/basic_main.json

# Execute with custom output directory
python -m src.scenarios.run_scenario \
  --scenario config/scenarios/basic_main.json \
  --output-dir results/my_experiment
```

**Scenario Configuration Structure:**
The scenario files define all aspects of the simulation including GNS3 topology deployment, FL client/server configuration, policy settings, and monitoring requirements. Key configuration elements include:

- **GNS3 Integration**: Network topology and node deployment specifications
- **FL Simulation**: Client count, communication patterns, and training simulation parameters
- **Policy Enforcement**: Resource limits, security policies, and compliance requirements
- **Monitoring Setup**: Metric collection intervals and data aggregation settings

### Using the Dashboard for Monitoring

The dashboard provides real-time monitoring of simulation experiments but experiment creation and execution is primarily scenario-driven through configuration files.

**Dashboard Access:**
- Open http://localhost:8085 to access the monitoring dashboard
- View real-time FL simulation metrics, network performance, and policy compliance
- Monitor component health and system resource utilization

**Dashboard Features:**
- **Simulation Progress**: Track FL communication rounds and convergence simulation
- **Network Metrics**: Monitor latency, bandwidth utilization, and connectivity
- **Policy Compliance**: View policy enforcement actions and compliance status
- **Component Status**: Monitor FL client/server health and collector metrics
### Using the REST API for Monitoring

```bash title="Monitor Simulation via API"
# Get current simulation status
curl -X GET "http://localhost:8001/api/v1/simulation/status"

# Get FL simulation metrics
curl -X GET "http://localhost:8001/api/v1/metrics/fl"

# Get network performance metrics
curl -X GET "http://localhost:8001/api/v1/metrics/network"

# Get policy compliance status
curl -X GET "http://localhost:8001/api/v1/policies/status"
```

### Command Line Scenario Execution

```bash title="CLI Scenario Execution"
# Execute basic FL simulation scenario
python -m src.scenarios.run_scenario \
  --scenario config/scenarios/basic_main.json \
  --gns3-host 192.168.56.100 \
  --output-dir results/basic_simulation

# Execute with custom monitoring interval
python -m src.scenarios.run_scenario \
  --scenario config/scenarios/basic_main.json \
  --monitor-interval 30 \
  --duration 1800

# Execute with policy enforcement
python -m src.scenarios.run_scenario \
  --scenario config/scenarios/basic_main.json \
  --policy-config config/policies/default_policies.json
```

## Scenario Configuration

### Scenario File Structure

FLOPY-NET scenarios are defined in JSON files that specify the complete simulation setup including GNS3 network topology, FL component configuration, and monitoring parameters.

```json title="config/scenarios/basic_main.json"
{
  "name": "Basic FL Simulation",
  "description": "Standard FL simulation with network monitoring",
  "version": "1.0",
  "gns3": {
    "project_name": "FLOPY-NET-Basic",
    "topology_file": "config/topology/basic_topology.json",
    "auto_deploy": true
  },
  "fl_simulation": {
    "num_clients": 3,
    "simulation_rounds": 10,
    "round_duration": 60,
    "client_participation_rate": 1.0,
    "simulate_training": true,
    "use_random_data": true
  },
  "monitoring": {
    "collect_metrics": true,
    "metric_interval": 10,
    "collectors": ["fl_metrics", "network_metrics", "policy_metrics"]
  },
  "policy_enforcement": {
    "enable_policies": true,
    "policy_config": "config/policies/default_policies.json"
  },
  "duration": 600,
  "output_config": {
    "save_logs": true,
    "save_metrics": true,
    "log_level": "INFO"
  }
}
```### Simulation Component Configuration

The FL simulation components are configured to demonstrate federated learning behavior patterns without requiring actual machine learning workloads. This enables rapid testing of network conditions, policy enforcement, and system monitoring.

**FL Server Simulation Configuration:**
```json
"fl_server": {
  "simulation_mode": true,
  "mock_model_aggregation": true,
  "convergence_simulation": {
    "target_accuracy": 0.85,
    "convergence_rate": 0.95,
    "add_noise": true
  },
  "communication_patterns": {
    "client_selection": "random",
    "aggregation_strategy": "fedavg_simulation"
  }
}
```

**FL Client Simulation Configuration:**
```json
"fl_clients": {
  "simulation_mode": true,
  "generate_synthetic_updates": true,
  "training_simulation": {
    "local_epochs": 5,
    "batch_size": 32,
    "learning_rate_simulation": 0.01,
    "performance_variation": 0.1
  },
  "resource_constraints": {
    "cpu_limit": "500m",
    "memory_limit": "512Mi"
  }
}
```

### Scenario Templates

FLOPY-NET includes predefined scenarios for common research patterns:

#### Basic Federated Learning

```json title="scenarios/basic_fl.json"
{
  "name": "Basic Federated Learning",
  "description": "Standard FL setup with IID data distribution",
  "defaults": {
    "num_clients": 10,
    "clients_per_round": 8,
    "num_rounds": 20,
    "data_distribution": "iid",
    "network_conditions": "ideal"
  }
}
```

#### Non-IID Data Distribution

```json title="scenarios/non_iid.json"
{
  "name": "Non-IID Data Distribution",
  "description": "FL with heterogeneous data distribution",
  "defaults": {
    "data_distribution": {
      "type": "dirichlet",
      "alpha": 0.1
    },
    "num_clients": 20,
    "local_epochs": 10
  }
}
```

#### Byzantine Fault Tolerance

```json title="scenarios/byzantine.json"
{
  "name": "Byzantine Fault Tolerance",
  "description": "FL with malicious clients and defenses",
  "defaults": {
    "byzantine_clients": 3,
    "attack_types": ["label_flipping", "model_poisoning"],
    "defenses": ["krum", "trim_mean", "fedavg_robust"]
  }
}
```

#### Edge Computing Simulation

```json title="scenarios/edge_computing.json"
{
  "name": "Edge Computing",
  "description": "Resource-constrained edge devices",
  "defaults": {
    "client_resources": {
      "cpu_cores": 2,
      "memory_mb": 1024,
      "storage_gb": 16
    },
    "network_conditions": {
      "bandwidth": "1Mbps",
      "latency": 200,
      "intermittent_connectivity": true
    }
  }
}
```

## Monitoring Experiments

### Real-time Monitoring

#### Dashboard Views

1. **Training Progress**
   - Global model accuracy and loss curves
   - Per-round performance metrics
   - Convergence rate analysis

2. **Client Status**
   - Active vs inactive clients
   - Client resource utilization
   - Communication round participation

3. **Network Performance**
   - Latency distribution
   - Bandwidth utilization
   - Packet loss rates
   - Connection stability

4. **Security Metrics**
   - Trust scores
   - Anomaly detection alerts
   - Policy compliance status

#### Key Metrics to Track

| Metric | Description | Good Range |
|--------|-------------|------------|
| **Global Accuracy** | Model performance on test set | Increasing trend |
| **Round Duration** | Time per communication round | Consistent, < 60s |
| **Client Participation** | Active clients per round | > 80% of total |
| **Communication Cost** | Data transferred per round | Minimize while maintaining accuracy |
| **Convergence Rate** | Rounds to reach target accuracy | Depends on problem complexity |

### Programmatic Monitoring

```python title="Monitor Experiment Progress"
import requests
import time
import matplotlib.pyplot as plt

def monitor_experiment(experiment_id: int, duration_minutes: int = 60):
    """Monitor experiment progress and plot real-time metrics."""
    
    start_time = time.time()
    metrics_history = []
    
    while time.time() - start_time < duration_minutes * 60:
        # Get current metrics
        response = requests.get(f"http://localhost:8001/api/v1/experiments/{experiment_id}/metrics")
        if response.status_code == 200:
            metrics = response.json()
            metrics['timestamp'] = time.time()
            metrics_history.append(metrics)
            
            # Plot real-time updates
            plot_metrics(metrics_history)
        
        time.sleep(30)  # Update every 30 seconds
    
    return metrics_history

def plot_metrics(metrics_history):
    """Plot training metrics in real-time."""
    if len(metrics_history) < 2:
        return
    
    rounds = [m['current_round'] for m in metrics_history]
    accuracy = [m['global_accuracy'] for m in metrics_history]
    loss = [m['global_loss'] for m in metrics_history]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    ax1.plot(rounds, accuracy, 'b-', linewidth=2)
    ax1.set_title('Global Model Accuracy')
    ax1.set_xlabel('Round')
    ax1.set_ylabel('Accuracy')
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(rounds, loss, 'r-', linewidth=2)
    ax2.set_title('Global Model Loss')
    ax2.set_xlabel('Round')
    ax2.set_ylabel('Loss')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.pause(0.1)
```

## Advanced Experiment Features

### Custom Data Distributions

```python title="Custom Data Distribution"
from src.data.distribution import DataDistributor

class CustomDistributor(DataDistributor):
    """Custom data distribution for specific research needs."""
    
    def distribute_data(self, dataset, num_clients):
        """Implement custom data distribution logic."""
        # Example: Temporal data split
        samples_per_client = len(dataset) // num_clients
        client_data = []
        
        for i in range(num_clients):
            start_idx = i * samples_per_client
            end_idx = (i + 1) * samples_per_client
            
            # Add temporal skew
            temporal_offset = i * 100  # Different time periods
            client_subset = dataset[start_idx:end_idx]
            
            client_data.append({
                'data': client_subset,
                'temporal_offset': temporal_offset,
                'client_id': i
            })
        
        return client_data
```

### Network Condition Simulation

```python title="Dynamic Network Conditions"
class DynamicNetworkSimulator:
    """Simulate changing network conditions during training."""
    
    def __init__(self, experiment_config):
        self.base_latency = experiment_config['network']['latency']['mean']
        self.base_bandwidth = experiment_config['network']['bandwidth']
        
    def get_network_conditions(self, round_number, client_id):
        """Get network conditions for specific round and client."""
        # Simulate network degradation over time
        latency_multiplier = 1 + (round_number * 0.05)  # 5% increase per round
        
        # Simulate client-specific conditions
        if client_id in self.get_mobile_clients():
            # Mobile clients have higher variability
            latency_variance = 0.5
            bandwidth_reduction = 0.3
        else:
            latency_variance = 0.1
            bandwidth_reduction = 0.0
        
        return {
            'latency': self.base_latency * latency_multiplier * (1 + random.uniform(-latency_variance, latency_variance)),
            'bandwidth': self.base_bandwidth * (1 - bandwidth_reduction),
            'packet_loss': min(0.1, round_number * 0.002)  # Max 10% loss
        }
```

### Adaptive Algorithms

```python title="Adaptive FL Algorithm"
class AdaptiveFedAvg:
    """FedAvg with adaptive learning rate and client selection."""
    
    def __init__(self, initial_lr=0.01, adaptation_factor=0.95):
        self.learning_rate = initial_lr
        self.adaptation_factor = adaptation_factor
        self.client_performance_history = {}
    
    def aggregate_updates(self, client_updates, round_number):
        """Aggregate client updates with adaptive weighting."""
        # Standard FedAvg aggregation
        aggregated_update = self.fedavg_aggregate(client_updates)
        
        # Adapt learning rate based on convergence
        if self.is_converging_slowly(round_number):
            self.learning_rate *= 1.1  # Increase LR
        elif self.is_converging_quickly(round_number):
            self.learning_rate *= 0.9  # Decrease LR
        
        return aggregated_update
    
    def select_clients(self, available_clients, target_count):
        """Select clients based on performance and network conditions."""
        # Prioritize clients with good network conditions and participation history
        client_scores = []
        
        for client in available_clients:
            network_quality = self.get_network_quality(client)
            participation_rate = self.get_participation_rate(client)
            trust_score = self.get_trust_score(client)
            
            score = (network_quality * 0.4 + 
                    participation_rate * 0.3 + 
                    trust_score * 0.3)
            
            client_scores.append((client, score))
        
        # Select top clients
        client_scores.sort(key=lambda x: x[1], reverse=True)
        return [client for client, score in client_scores[:target_count]]
```

## Experiment Management

### Experiment States

```mermaid
stateDiagram-v2
    [*] --> Created
    Created --> Configured
    Configured --> Deployed
    Deployed --> Running
    Running --> Paused
    Paused --> Running
    Running --> Completed
    Running --> Failed
    Failed --> [*]
    Completed --> [*]
    
    note right of Running : Can pause/resume
    note right of Failed : Check logs for errors
```

### Experiment Control

```bash title="Experiment Control Commands"
# Start experiment
curl -X POST "http://localhost:8001/api/v1/experiments/1/start"

# Pause experiment
curl -X POST "http://localhost:8001/api/v1/experiments/1/pause"

# Resume experiment
curl -X POST "http://localhost:8001/api/v1/experiments/1/resume"

# Stop experiment
curl -X POST "http://localhost:8001/api/v1/experiments/1/stop"

# Get experiment status
curl "http://localhost:8001/api/v1/experiments/1/status"
```

### Experiment Scheduling

```python title="Experiment Scheduler"
from datetime import datetime, timedelta
import schedule

class ExperimentScheduler:
    """Schedule and manage multiple experiments."""
    
    def __init__(self):
        self.scheduled_experiments = []
        self.running_experiments = {}
    
    def schedule_experiment(self, experiment_config, start_time):
        """Schedule an experiment to run at a specific time."""
        schedule.every().day.at(start_time.strftime("%H:%M")).do(
            self.run_experiment, experiment_config
        )
    
    def schedule_experiment_series(self, base_config, parameter_sweep):
        """Schedule a series of experiments with parameter variations."""
        for i, params in enumerate(parameter_sweep):
            config = {**base_config, **params}
            start_time = datetime.now() + timedelta(hours=i * 2)  # 2 hours apart
            
            self.schedule_experiment(config, start_time)
    
    def run_experiment(self, experiment_config):
        """Execute a scheduled experiment."""
        experiment_id = self.create_experiment(experiment_config)
        self.start_experiment(experiment_id)
        self.running_experiments[experiment_id] = experiment_config

# Example parameter sweep
parameter_sweep = [
    {"num_clients": 10, "alpha": 0.1},
    {"num_clients": 10, "alpha": 0.5},
    {"num_clients": 10, "alpha": 1.0},
    {"num_clients": 20, "alpha": 0.1},
    {"num_clients": 20, "alpha": 0.5},
    {"num_clients": 20, "alpha": 1.0},
]
```

## Best Practices

### Experiment Design

1. **Clear Objectives**: Define specific research questions
2. **Controlled Variables**: Change one parameter at a time
3. **Statistical Significance**: Run multiple seeds for reliability
4. **Baseline Comparison**: Always include baseline scenarios
5. **Documentation**: Document all configuration choices

### Resource Management

1. **Resource Allocation**: Monitor CPU, memory, and network usage
2. **Experiment Queuing**: Avoid running too many experiments simultaneously
3. **Data Management**: Clean up experiment data regularly
4. **Backup Strategy**: Backup important experiment results

### Reproducibility

1. **Deterministic Seeds**: Use fixed random seeds
2. **Environment Consistency**: Use Docker for consistent environments
3. **Configuration Versioning**: Version control experiment configurations
4. **Data Versioning**: Track dataset versions and preprocessing steps

## Troubleshooting

### Common Issues

#### Experiment Won't Start

```bash
# Check experiment configuration
curl "http://localhost:8001/api/v1/experiments/1/config"

# Verify resource availability
curl "http://localhost:8001/api/v1/system/resources"

# Check component health
curl "http://localhost:8001/api/v1/health"
```

#### Slow Convergence

- **Check data distribution**: Highly non-IID data can slow convergence
- **Adjust learning rate**: May need tuning for your specific scenario
- **Increase local epochs**: More local training per round
- **Review network conditions**: High latency affects convergence

#### Client Dropouts

- **Network instability**: Check network simulation parameters
- **Resource constraints**: Verify client resource allocations
- **Policy violations**: Check policy engine logs
- **Timeout settings**: Adjust round timeout limits

### Debugging Tools

```bash title="Debug Commands"
# View experiment logs
docker-compose logs fl-server
docker-compose logs fl-client-1

# Check network connectivity
python scripts/check_gns3_connectivity.py

# Monitor resource usage
docker stats

# Get detailed metrics
curl "http://localhost:8002/api/v1/metrics/detailed"
```

Running successful experiments in FLOPY-NET requires careful planning, monitoring, and analysis. Follow these guidelines to conduct meaningful federated learning research in realistic network environments.
