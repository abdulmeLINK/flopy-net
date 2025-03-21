# Federated Learning Framework

This framework provides a modular architecture for building federated learning systems with an emphasis on performance, security, and policy-based management.

## Features

- **Federated Learning**: Train machine learning models across decentralized devices
- **Policy-Based Management**: Define and enforce policies for client selection, resource allocation, and data privacy
- **Software-Defined Networking**: Network optimizations for efficient model distribution and updates 
- **Scalable Architecture**: Modular, extensible design to support various ML models and training strategies
- **Realistic Simulation Scenarios**: Pre-defined realistic environments for testing federated learning strategies

## Project Structure

```
src/
├── api/                   # API interface layer
│   └── simulation_api.py  # Simulation API routes
├── application/           # Application layer containing services and use cases
│   ├── fl_strategies/     # Federated learning strategies (FedAvg, etc.)
│   └── services/          # Application services
├── domain/                # Domain layer with core business logic and interfaces
│   ├── entities/          # Domain entities (Model, Client, etc.)
│   ├── interfaces/        # Repository and service interfaces
│   ├── policy/            # Policy-related components
│   │   └── policy_engine.py  # Policy engine implementation
│   └── scenarios/         # Simulation scenarios
│       ├── scenario_registry.py  # Registry for all scenarios
│       ├── urban_scenario.py     # Urban environment scenario
│       ├── industrial_iot_scenario.py  # Industrial IoT scenario
│       └── healthcare_scenario.py      # Healthcare scenario
├── infrastructure/        # Infrastructure implementation layer
│   ├── repositories/      # Data storage implementations
│   └── sdn/               # Software-defined networking components
├── service/               # Service layer
│   └── simulation_runner.py  # Simulation execution service
└── main.py                # Main application entry point
```

## Model Repository

Models are stored using the `FileModelRepository` implementation with the following structure:

```
models/
├── [model_name]/
│   ├── [version]_metadata.json     # Model metadata
│   ├── [version]_weights_0.npy     # Weight array 0
│   ├── [version]_weights_1.npy     # Weight array 1
│   └── ...
```

Key improvements:
- NumPy arrays are properly serialized for storage
- Efficient binary storage of model weights
- Versioning support for tracking model evolution

## Simulation Scenarios

The framework includes predefined realistic scenarios for testing federated learning strategies:

### Urban Scenario

A city environment simulation with the following characteristics:
- Mobile and stationary clients (smartphones, laptops, IoT devices)
- Urban network infrastructure with varying signal quality
- Rush hour congestion patterns
- WiFi/cellular handovers
- High device heterogeneity

### Industrial IoT Scenario

A factory floor environment with:
- Smart manufacturing equipment and industrial sensors
- Challenging RF conditions (metal interference, machinery noise)
- Time-sensitive applications with high reliability requirements
- Legacy and modern equipment coexistence
- Shift patterns affecting network load

### Healthcare Scenario

A hospital and clinic environment featuring:
- Medical imaging devices (MRI, CT, X-ray)
- Strict privacy and security requirements
- High reliability needs for patient-critical systems
- Heterogeneous data distributions across facilities
- Priority-based network traffic for medical applications

## Simulation Policy Engine

The framework includes a powerful policy engine that enforces rules across the federated learning system. The policy engine is integrated with simulations to provide realistic policy-based behavior:

### Policy Domains

Policies are organized by domains to match different simulation scenarios:

- **Healthcare**: Policies for healthcare environments with strict privacy and security requirements
- **Industrial IoT**: Policies for industrial environments with high reliability requirements
- **Urban**: Policies for urban environments with mobile devices and varying connectivity
- **General**: Default policies applicable to all scenarios

### Policy Types

The policy engine supports several types of policies:

- **Server Configuration**: Control server behavior including minimum client requirements and privacy mechanisms
- **Client Selection**: Define which clients can participate in training based on battery levels, charging status, etc.
- **Network**: Manage traffic priorities, encryption requirements, and latency constraints
- **Data Privacy**: Enforce anonymization requirements and compliance with regulations (e.g., HIPAA)

### Using Custom Policies

When running simulations, you can provide custom policy configurations:

```json
{
  "server_config": [
    {
      "min_clients": 10,
      "privacy_mechanism": "secure_aggregation"
    }
  ],
  "network": [
    {
      "traffic_priority": {
        "fl_training": 2,
        "model_distribution": 1
      },
      "encryption": "required"
    }
  ]
}
```

This can be passed when starting a simulation:

```bash
curl -X POST "http://localhost:8000/api/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "Healthcare", 
    "policy_config": {
      "server_config": [{"min_clients": 10, "privacy_mechanism": "secure_aggregation"}],
      "network": [{"encryption": "required", "encryption_level": "AES-256"}]
    }
  }'
```

## Getting Started

### Prerequisites

- Python 3.8+
- NumPy
- PyTorch (or other ML frameworks)
- FastAPI (for API access)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/federated-learning.git
cd federated-learning

# Setup virtual environment
python -m venv fl_venv
source fl_venv/bin/activate  # On Windows: fl_venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Simulation

#### Simulation Mode

Run the application in simulation mode:

```bash
python -m src.main --mode simulation --port 8000
```

This launches a dedicated FastAPI server with the simulation API endpoints.

#### Using the Simulation API

The simulation API provides endpoints for running and managing federated learning simulations with different scenarios:

```bash
# List available scenarios
curl -X GET "http://localhost:8000/api/simulations/scenarios" -H "accept: application/json"

# Get details about a specific scenario
curl -X GET "http://localhost:8000/api/simulations/scenarios/Healthcare" -H "accept: application/json"

# Start a simulation with a specific scenario
curl -X POST "http://localhost:8000/api/simulations" \
  -H "Content-Type: application/json" \
  -d '{"scenario_name": "Healthcare", "policy_config": {"server_config": [{"min_clients": 8}]}}'

# List all running simulations
curl -X GET "http://localhost:8000/api/simulations" -H "accept: application/json"

# Get details about a specific simulation
curl -X GET "http://localhost:8000/api/simulations/{simulation_id}" -H "accept: application/json"

# Get metrics for a specific simulation
curl -X GET "http://localhost:8000/api/simulations/{simulation_id}/metrics" -H "accept: application/json"

# Stop a running simulation
curl -X POST "http://localhost:8000/api/simulations/{simulation_id}/stop" -H "accept: application/json"
```

#### Using Python script

```python
import requests

# Base URL for the simulation API
base_url = "http://localhost:8000/api/simulations"

# List available scenarios
response = requests.get(f"{base_url}/scenarios")
scenarios = response.json()
print(f"Available scenarios: {[s['name'] for s in scenarios]}")

# Run a simulation
response = requests.post(
    base_url,
    json={
        "scenario_name": "Healthcare",
        "config_overrides": {
            "server": {
                "min_clients": 8
            }
        }
    }
)
simulation = response.json()
simulation_id = simulation["simulation_id"]
print(f"Started simulation with ID: {simulation_id}")

# Monitor simulation status
response = requests.get(f"{base_url}/{simulation_id}")
status = response.json()["status"]
print(f"Simulation status: {status}")

# Get simulation metrics
response = requests.get(f"{base_url}/{simulation_id}/metrics")
metrics = response.json()["metrics"]
print(f"Simulation metrics: {metrics}")
```

## License

[MIT License](LICENSE)
