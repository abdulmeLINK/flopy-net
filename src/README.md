# Federated Learning System - Source Code

This directory contains the source code for the federated learning system.

## Architecture

The system follows a clean architecture approach with the following layers:

### Domain Layer (`domain/`)

Contains the core business entities and interfaces:
- `entities/`: Client, Model, Strategy, etc.
- `interfaces/`: Repositories, Policy Engine, etc.

### Application Layer (`application/`)

Contains the application-specific business rules:
- `use_cases/`: Server and client use cases
- `policy/`: Policy engine implementation
- `fl_strategies/`: Federated learning strategies

### Infrastructure Layer (`infrastructure/`)

Contains framework implementations and adapters:
- `repositories/`: Data storage implementations
- `config/`: Configuration management
- `clients/`: External client/server adapters
- `api/`: External API implementations

### Presentation Layer (`presentation/`)

Contains user interfaces:
- `rest/`: REST API controllers
- `cli/`: Command-line interface

## Entry Points

- `main.py`: Main application module for running the API server
- `presentation/cli/__main__.py`: CLI entry point

## Running the System

### Using the API Server

```bash
python -m src.main --mode server --port 5000
```

### Using the CLI

```bash
python -m src.presentation.cli --mode server --port 5000
```

## Directory Structure

- **dashboard/**: Interactive web dashboard for monitoring and control
- **fl/**: Federated Learning implementation
- **sdn/**: Software-Defined Networking components
- **simulation/**: Simulation environment
- **policy/**: Policy engine for adaptive FL and network control
- **utils/**: Utility functions and shared components

## Development

Follow these guidelines when working with the source code:

1. Maintain separation of concerns between components
2. Use dependency injection for testing
3. Document all public APIs
4. Follow the module structure for new components

## Documentation

For detailed development and implementation guidelines, refer to the following documentation:

- [Architecture Patterns](../docs/architecture_patterns.md) - System architecture design
- [Code Patterns](../docs/code_patterns.md) - Coding standards and patterns
- [Development Workflow](../docs/development_workflow.md) - Development process
- [Testing Strategy](../docs/testing_strategy.md) - Testing guidelines
- [Deployment Patterns](../docs/deployment_patterns.md) - Deployment and containerization

## Network Communication Architecture

All components in the system (FL clients, server, SDN controller) communicate with each other through a standardized network communication layer. This ensures consistent policy enforcement and security.

### Key Components

1. **Network Client Interface**: Defines the contract for all network communication (`INetworkClient`)
2. **REST Network Client**: An HTTP/REST-based implementation of the network client interface
3. **Policy Message Broker**: A centralized service that routes messages between components and enforces policies
4. **Policy Engine**: Evaluates all communication against defined policies

### Communication Flow

1. Components connect to the system through their network client
2. All messages are checked with the policy engine before sending
3. The policy message broker validates and routes messages to their destinations
4. Receiving components validate messages again with the policy engine before processing

## Policy Engine Integration

The policy engine is central to the system's operation. All components must check with the policy engine before taking action:

- **Federated Learning Server**: Checks policies for client selection, model distribution, and aggregation
- **Federated Learning Clients**: Check policies for sending model updates and participation in rounds
- **SDN Controller**: Checks policies for network configuration changes and flow management

### Policy Structure

Policies are defined in a consistent and easy-to-understand format:

1. **Policy Registry**: Maps policy names to implementation classes (`policy_registry.json`)
2. **Policy Configuration**: JSON-based configuration for each policy (`network_policies.json`)
3. **Policy Implementation**: Python classes that implement policy logic (`MessageRoutingPolicy`, etc.)

### Adding New Policies

1. Create a new policy class in `src/application/policy/policies/`
2. Add the policy to the registry in `policy_registry.json`
3. Create a JSON configuration for the policy

### Examples

**JSON Policy Definition:**
```json
{
    "name": "message_routing",
    "config": {
        "allowed_component_pairs": [
            {"source": "fl_server", "target": "fl_client"},
            {"source": "fl_client", "target": "fl_server"}
        ]
    },
    "rules": [
        {
            "name": "allow_policy_engine",
            "condition": {
                "type": "simple",
                "field": "target_component",
                "operator": "eq",
                "value": "policy_engine"
            },
            "action": {
                "type": "allow",
                "reason": "Policy engine is always accessible"
            }
        }
    ]
}
```

**Loading Policies:**
```python
# Load policies from JSON files
policy_engine.load_policy_from_file("path/to/policy.json")

# Register policy directly
policy_engine.register_policy("message_routing") 
```

## Simulation Components

The system now includes a comprehensive simulation environment for testing federated learning strategies in realistic scenarios:

### Key Components

- **Scenario Registry (`domain/scenarios/scenario_registry.py`)**: Manages different simulation scenarios with standardized interfaces
- **Simulation Runner (`service/simulation_runner.py`)**: Executes simulations with policy integration
- **Policy Engine (`domain/policy/policy_engine.py`)**: Enforces policies across the federated learning system
- **Simulation API (`api/simulation_api.py`)**: RESTful API for managing simulations

### Predefined Scenarios

The system includes three realistic scenarios:

1. **Urban Scenario**: City environment with mobile devices and varying connectivity
2. **Industrial IoT Scenario**: Factory floor with specialized equipment and challenging conditions
3. **Healthcare Scenario**: Medical facilities with privacy requirements and specialized devices

### Running Simulations

To run the system in simulation mode:

```bash
python -m src.main --mode simulation --port 8000
```

This will start a FastAPI server with endpoints for managing simulations. Use the API to list available scenarios, start simulations, and collect metrics.

For detailed API documentation, visit the Swagger UI at http://localhost:8000/docs when the server is running. 