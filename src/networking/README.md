# Networking Module (`src/networking/`)

This module handles all network simulation and GNS3 integration for the FLOPY-NET platform.

## Architecture

### Core GNS3 Integration (`gns3/`)
- **API Client** (`gns3/core/api.py`): Low-level GNS3 API communication
- **Simulator Class** (`gns3/core/simulator.py`): High-level GNS3 project management

### Network Simulators (`simulators/`)
- **GNS3 Simulator** (`gns3_simulator.py`): Primary network simulation implementation
- **Network Simulator Interface** (`network_simulator.py`): Abstract interface for different simulators

## Key Capabilities

- **GNS3 Project Management**: Create, configure, and manage network topologies
- **SDN Integration**: OpenFlow switches and controller integration
- **Docker Node Deployment**: Custom containerized network components
- **Automatic Resource Management**: VPCS cleanup and capacity monitoring
- **Realistic Network Conditions**: Packet loss, latency, and bandwidth simulation

## Usage

The networking module is used by:
- **Scenario Scripts** (`src/scenarios/`) for deploying network topologies
- **Utility Scripts** (`scripts/`) for GNS3 environment management
- **Dashboard Backend** for network topology visualization
- **Collector Service** for network metrics gathering

## Configuration

- **GNS3 Connection**: `config/gns3/gns3_connection.json`
- **Node Templates**: `config/gns3/templates/` (see templates README for details)
- **Network Topologies**: `config/topology/` directory

For detailed simulator usage and development guidelines, see `simulators/README.md`.
For GNS3 template configuration and IP management, see `config/gns3/templates/README.md`.