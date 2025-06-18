# Network Simulators

This directory contains network simulation components for the FLOPY-NET federated learning system.

## Overview

The network simulators provide abstraction layers for different network simulation environments, primarily focusing on GNS3 integration with SDN capabilities.

## Components

### GNS3 Simulator (`gns3_simulator.py`)
- **Primary simulator implementation** for GNS3 network emulation
- **Automatic cleanup functionality** to manage VPCS node limits
- **Docker container integration** with custom node templates
- **OpenFlow switch support** for SDN scenarios

### Network Simulator Interface (`network_simulator.py`)
- **Abstract interface** for network simulation implementations
- **Facade pattern** for different concrete simulators
- **Standardized API** for scenario deployment and management

## Key Features

- **GNS3 Integration**: Programmatic control of GNS3 projects, nodes, and links
- **SDN Support**: OpenFlow switches and SDN controller integration
- **Automatic Resource Management**: VPCS cleanup and capacity monitoring
- **Docker Node Templates**: Custom containerized network components
- **Scenario Support**: Network topology creation for federated learning experiments

## Usage

### Basic GNS3 Simulator Usage

```python
from src.networking.simulators.gns3_simulator import GNS3Simulator

# Initialize with automatic cleanup (default)
simulator = GNS3Simulator("http://localhost:3080", "my_project")

# Create network topology
topology = simulator.create_topology(nodes_config, links_config)

# Deploy federated learning scenario
simulator.deploy_fl_scenario(fl_config)
```

### Configuration

The simulator uses configuration from:
- `config/gns3/gns3_connection.json` - GNS3 server connection details
- `config/gns3/templates/` - Node template definitions
- Environment variables for runtime configuration

## Network Simulation Capabilities

### Topology Management
- **Dynamic topology creation** based on configuration files
- **Node lifecycle management** (start, stop, delete)
- **Link configuration** with bandwidth and latency settings
- **Network segmentation** for different FL client groups

### Realistic Network Conditions
- **Packet loss simulation** for unreliable network scenarios
- **Bandwidth limitations** to simulate constrained environments
- **Latency injection** for geographically distributed scenarios
- **Network partitioning** for testing fault tolerance

### Integration Points

The simulators are used by:
- **Scenario deployment scripts** (`src/scenarios/`) for creating network topologies
- **Utility scripts** (`scripts/`) for managing GNS3 environments
- **Dashboard backend** for retrieving network topology information
- **Collector service** for network metrics gathering

## Development Guidelines

- **Single Responsibility**: Keep simulation components focused on specific tasks
- **Clean Interfaces**: Provide consistent APIs for metrics collection
- **Documentation**: Document simulation capabilities and limitations
- **Error Handling**: Implement robust error handling for network operations
- **Resource Management**: Always clean up network resources after use

## GNS3 Template Management

Node templates are managed through:
- **JSON definitions** in `config/gns3/templates/`
- **Template utility** (`scripts/gns3_templates.py`) for template operations
- **Docker registry integration** for custom node images

For GNS3 template configuration and IP address management, see `config/gns3/templates/README.md`.

## Troubleshooting

### Common Issues
- **VPCS limit reached**: Use cleanup functionality or run cleanup scripts
- **GNS3 connection errors**: Verify GNS3 server URL and connectivity
- **Template not found**: Check template definitions and GNS3 server templates
- **Network creation failures**: Check GNS3 server resources and permissions

### Debugging
- Enable debug logging in simulator configuration
- Check GNS3 server logs for detailed error information
- Use GNS3 utility scripts for connectivity testing
- Monitor resource usage with cleanup test scripts