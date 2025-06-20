# Networking Module (`src/networking/`)

This module handles all network simulation, GNS3 integration, and SDN control for the FLOPY-NET platform. It provides realistic network emulation capabilities that enable researchers to study federated learning performance under various network conditions.

## Architecture

### Core GNS3 Integration (`gns3/`)
- **API Client** (`gns3/core/api.py`): Low-level GNS3 API communication and project management
- **Simulator Class** (`gns3/core/simulator.py`): High-level GNS3 project management with topology control
- **GNS3 Manager** (`gns3_manager.py`): Project lifecycle management and container deployment

### Network Simulators (`simulators/`)
- **GNS3 Simulator** (`gns3_simulator.py`): Primary network simulation implementation with Docker container support
- **Network Simulator Interface** (`network_simulator.py`): Abstract interface providing facade pattern for different simulators
- **Federated Learning Simulation** (`simulate_federated_learning_round`): FL-specific network simulation capabilities

### SDN Integration (Containerized Services)
- **SDN Controller Container**: `abdulmelink/flopynet-sdn-controller:v1.0.0-alpha.8` (IP: 192.168.100.41, Ports: 6633, 8181)
- **OpenVSwitch Container**: `abdulmelink/openvswitch:v1.0.0-alpha.8` (IP: 192.168.100.60)
- **Ryu OpenFlow Controller**: Custom applications for network policy enforcement and traffic management

## Key Capabilities

- **GNS3 Project Management**: Create, configure, and manage network topologies with automated cleanup
- **SDN Integration**: Ryu-based OpenFlow controllers with REST API (Port 8181) and policy-driven flow rules
- **Docker Node Deployment**: Custom containerized network components with static IP assignment
- **Automatic Resource Management**: VPCS cleanup, capacity monitoring, and container lifecycle management  
- **Realistic Network Conditions**: Configurable packet loss, latency, bandwidth constraints, and jitter simulation
- **Dynamic Topology Control**: Runtime network modification, link manipulation, and node management
- **Policy Enforcement**: Network-level policy implementation through SDN flow rules and traffic shaping
- **Comprehensive Monitoring**: Network performance metrics collection and integration with Collector Service

## Usage

The networking module is used by:
- **Docker Compose Services**: SDN Controller and OpenVSwitch containers for production deployment
- **Scenario Scripts** (`src/scenarios/`) for deploying federated learning network topologies
- **Utility Scripts** (`scripts/`) for GNS3 environment management and maintenance
- **Dashboard Backend** for real-time network topology visualization and control
- **Collector Service** for network metrics gathering and performance analysis
- **Policy Engine** for network policy enforcement and compliance monitoring

## Configuration

- **GNS3 Connection**: `config/gns3/gns3_connection.json`
- **Node Templates**: `config/gns3/templates/` (see templates README for details)
- **Network Topologies**: `config/topology/` directory

For detailed simulator usage and development guidelines, see `simulators/README.md`.
For GNS3 template configuration and IP management, see `config/gns3/templates/README.md`.