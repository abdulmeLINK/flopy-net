# FLOPY-NET: Federated Learning Observatory Platform - Network Emulation & Testing

[![Documentation](https://img.shields.io/badge/Documentation-flopynetdocs--a960.eu.onamber.cloud-blue?style=for-the-badge&logo=readthedocs)](https://flopynetdocs-a960.eu.onamber.cloud/)
[![Demo Platform](https://img.shields.io/badge/Demo-flopynet.abdulme.link-green?style=for-the-badge&logo=rocket)](https://flopynet.abdulme.link/)
[![Visitor Badge](https://api.visitorbadge.io/api/VisitorHit?user=abdulmeLINK&repo=flopy-net&countColor=%2379c0ff)](https://github.com/abdulmelink/flopy-net)
[![Version](https://img.shields.io/badge/Version-v1.0.0--alpha.8-red?style=for-the-badge&logo=semver)](https://github.com/abdulmelink/flopy-net/releases)

> ⚠️ **ALPHA VERSION WARNING**  
> This is an **alpha development version** of FLOPY-NET. Many features are **not fully tested** and may contain bugs or incomplete implementations. The **Policy Engine** in particular has **untrusted policy types** and enforcement mechanisms that are still under development. Use this platform for research and development purposes only - **NOT for production environments**.

FLOPY-NET is a comprehensive research platform for evaluating federated learning systems under realistic network conditions. The current implementation provides FL simulation using random data to demonstrate network effects, policy enforcement, and system monitoring capabilities. It bridges the gap between theoretical federated learning research and real-world network dynamics by integrating network emulation, performance monitoring, and policy enforcement capabilities.

> **Current Implementation Status**: The FL client and server components simulate federated learning training using randomly generated data to demonstrate system behavior, network interaction patterns, and policy enforcement. For actual machine learning research, these components can be extended with real ML models and datasets.

**Developer Focus**: The platform prioritizes modularity and extensibility of FL Client and FL Server components through environment variable-based parameter injection and derivable Python modules, enabling researchers to implement domain-specific and custom FL systems.

*Author's recommendation*: Use AI tools and agents to understand the system components and their interactions for a smoother initial learning curve.

## Key Features

- **Network-Aware FL Simulation**: Study FL behavior under realistic network conditions including packet loss, latency, and bandwidth constraints using GNS3 integration
- **Policy-Driven Architecture**: Centralized Policy Engine enforces security, compliance, and governance rules across all components with real-time policy evaluation
- **Comprehensive Network Simulation**: GNS3 integration with SDN controllers (Ryu/OpenFlow) for realistic network topologies and dynamic network conditions
- **Real-time Observatory**: Web-based dashboard with live monitoring of FL simulation progress, network performance, and system health metrics
- **Scenario-Based Execution**: Complete simulation scenarios defined through JSON configuration files with reproducible experimental setups
- **Multi-Component Architecture**: Microservices architecture with Policy Engine, Collector Service, FL Server/Clients, SDN Controller, and OpenVSwitch
- **Comprehensive Metrics Collection**: SQLite-based metrics storage with real-time data aggregation and historical analysis capabilities
- **Container-based Deployment**: Docker-native platform with scalable microservices architecture and static IP assignment
- **Extensible FL Framework**: Base FL implementation designed for extension with real ML models and training algorithms

---

## System Architecture

FLOPY-NET follows a layered, microservices architecture with five primary layers, deployed using Docker Compose with static IP assignment:

### 1. User Interface Layer
- **Dashboard Frontend** (Port 8085): React + TypeScript web interface with real-time monitoring and interactive network topology visualization
- **Dashboard API** (Port 8001): FastAPI backend for data aggregation, system control, and REST API endpoints
- **CLI Interface** (`src/main.py`): Command-line tools for system management, scenario execution, and service orchestration

### 2. Core Services Layer
- **Policy Engine** (Port 5000, IP 192.168.100.20): Flask-based centralized policy definition, enforcement, and compliance monitoring with real-time event processing
- **Collector Service** (Port 8083, IP 192.168.100.40): FastAPI-based metrics aggregation, storage, and analytics engine with SQLite persistence
- **FL Server** (Port 8080, IP 192.168.100.10): Flower-based federated learning coordination and model aggregation with policy integration
- **FL Metrics** (Port 8081, IP 192.168.100.10): Internal metrics API for FL training monitoring

### 3. Federated Learning Layer
- **FL Clients** (IP 192.168.100.101-102): Containerized Flower clients with PyTorch model training, data loading, and metrics reporting
- **Training Coordination**: Round-based training orchestration with configurable client participation policies
- **Model Management**: Parameter aggregation, versioning, and distribution with support for various model architectures (CNN, MLP)

### 4. Network Simulation Layer
- **GNS3 Integration** (Port 3080): Realistic network topology simulation with programmatic control via GNS3 API
- **SDN Controller** (Port 6633/8181, IP 192.168.100.41): Ryu-based OpenFlow controller for programmable network control and policy enforcement
- **OpenVSwitch** (IP 192.168.100.60): Software-defined switches with OpenFlow 1.3 support and dynamic flow rule management

### 5. Data & Storage Layer
- **SQLite Metrics Database**: Time-series performance data, training metrics, and system analytics with historical data retention
- **JSON Policy Storage**: Hierarchical policy definitions with versioning and dynamic loading capabilities
- **Event Logs**: Structured system events, audit trails, and policy compliance logs with JSONL format
- **Configuration Management**: Docker Compose environment variables with JSON configuration files for complex settings

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose**: Container orchestration platform
- **Python 3.8+**: For local development and scripts
- **Node.js 16+ & npm**: For dashboard frontend development
- **GNS3 Server**: Network simulation platform (configured via docker-compose.yml)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abdulmelink/flopy-net.git
   cd flopy-net
   ```

2. **Configure environment variables (optional):**
   ```bash
   # All configuration is handled through docker-compose.yml environment variables
   # Modify docker-compose.yml to customize settings like GNS3 server URL
   # No separate .env file is needed - configuration is embedded in the compose file
   ```

3. **Start the dashboard:**
   ```bash
   cd dashboard
   docker-compose up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check service status
   docker-compose ps
   ```

5. **Run a basic simulation scenario:**
   ```bash
   # Execute basic federated learning simulation scenario
   python -m src.scenarios.run_scenario --scenario config/scenarios/basic_main.json
   ```

---

## Core Components

### 1. Policy Engine (Port 5000)
**The Heart of FLOPY-NET's Governance System**

> ⚠️ **DEVELOPMENT WARNING**: The Policy Engine contains **untested and potentially unreliable policy types**. Many enforcement mechanisms are experimental and may not function as expected. Use with caution in research environments.

The Policy Engine serves as the centralized authority for all system decisions, enforcing security, performance, and compliance rules across all components.

**Key Features:**
- **Centralized Policy Management**: JSON-based policy definitions with CRUD operations
- **Real-time Enforcement**: Authorization for client connections, model updates, and network operations
- **Compliance Monitoring**: Continuous policy adherence checking and violation detection
- **Trust Management**: Client reputation scoring and behavioral analysis
- **Audit Trail**: Complete logging of policy decisions and enforcement actions

**Architecture:**
- Flask-based REST API service with SQLite/JSON storage
- Event-driven policy evaluation with real-time updates
- Integration with all system components for decision queries

### 2. Collector Service (Port 8000)
**Comprehensive Metrics and Analytics Engine**

The Collector aggregates, stores, and analyzes metrics from all system components, providing the data foundation for monitoring and research.

**Key Features:**
- **Multi-Source Data Collection**: FL training metrics, network performance, system health
- **Time-Series Storage**: Efficient SQLite-based storage with metric aggregation
- **Real-time Analytics**: Performance analysis and trend detection
- **Event Logging**: Structured system events with JSON formatting
- **Research Data Export**: API endpoints for data extraction and analysis

### 3. Federated Learning Simulation Framework
**FL Simulation with Network Integration**

A complete FL simulation framework designed to demonstrate federated learning behavior patterns while studying network effects and policy enforcement.

**FL Server (Port 8080):**
- **Simulation Coordination**: Round-based FL simulation orchestration with client management
- **Mock Model Aggregation**: Simulated FedAvg aggregation using random data for system validation
- **Policy Integration**: Policy Engine queries for all training decisions and compliance checking
- **Performance Monitoring**: Real-time simulation metrics and convergence pattern demonstration

**FL Clients (192.168.100.101-255):**
- **Training Simulation**: Local training simulation with configurable parameters and synthetic data generation
- **Network Integration**: Real network communication patterns demonstrating FL protocol behavior
- **Network Awareness**: Adaptive behavior based on network conditions
- **Policy Compliance**: Real-time policy checking and enforcement

### 4. Network Simulation & SDN
**Realistic Network Environment**

Advanced network simulation capabilities combining GNS3 with SDN controllers for realistic experimentation.

**GNS3 Integration (Port 3080):**
- **Topology Management**: Dynamic network topology creation and modification
- **Container Deployment**: Automated FL component deployment in network nodes
- **Network Conditions**: Configurable packet loss, latency, and bandwidth constraints

**SDN Controller (Port 6633/8181):**
- **Programmable Networking**: Ryu-based OpenFlow controller with custom applications
- **Policy-Driven Routing**: Network policies enforced through flow rules
- **Traffic Management**: QoS, load balancing, and security controls
- **Network Monitoring**: Real-time topology discovery and performance tracking

### 5. Dashboard & Monitoring
**Comprehensive System Observatory**

Multi-tier web-based interface providing real-time visualization and system control capabilities.

**Frontend (Port 8085):**
- **React-based Interface**: Modern, responsive web application with TypeScript
- **Real-time Visualization**: Interactive charts, network topology, and system metrics
- **Component Management**: Service health monitoring and configuration

**Backend API (Port 8001):**
- **FastAPI Service**: High-performance data aggregation and API endpoints
- **Service Integration**: Unified interface to all system components
- **WebSocket Support**: Real-time data streaming for live updates

## Research Applications

FLOPY-NET is specifically designed for researchers studying:

- **Network-Aware Federated Learning**: Impact of real network conditions on FL performance, convergence, and accuracy
- **Security & Privacy Research**: Byzantine attack detection, differential privacy, secure aggregation mechanisms
- **Edge Computing Studies**: Resource-constrained device behavior, heterogeneous client capabilities
- **System Optimization**: Network topology effects, client selection strategies, adaptive algorithms
- **Policy & Governance**: Compliance monitoring, trust management, regulatory adherence in distributed ML

## Supported Experimental Scenarios

- **Basic FL Training**: Standard federated learning with configurable client counts and models
- **Network Variation Studies**: Different bandwidth, latency, packet loss, and jitter conditions
- **Client Heterogeneity**: Diverse device capabilities, data distributions, and participation patterns
- **Dynamic Network Conditions**: Changing topology, node failures, and network partitions
- **Security Testing**: Byzantine clients, model poisoning, privacy attacks and defenses
- **Policy Enforcement**: Dynamic rule changes, compliance violations, and remediation actions

## Creating Custom Scenarios

FLOPY-NET provides a comprehensive framework for creating custom federated learning scenarios:

### Configuration Files Required:
1. **Scenario Config** (`config/scenarios/your_scenario.json`): Defines FL parameters, network settings, GNS3 integration
2. **Topology Config** (`config/topology/your_topology.json`): Defines network nodes, IP addresses, service templates
3. **Policy Config** (`config/policies/`): Custom policies for your scenario
4. **Scenario Class** (`src/scenarios/your_scenario.py`): Python implementation extending BaseScenario

### Key Configuration Parameters:
- **Network Topology**: Node placement, IP assignments, service types, environmental variables
- **FL Parameters**: Client counts, training rounds, model types, aggregation methods
- **GNS3 Integration**: Server URLs, project settings, cleanup actions
- **Dynamic Events**: Network failures, client dropouts, policy changes during execution
- **Resource Constraints**: CPU, memory, bandwidth limitations per client type

### Quick Example:
```bash
# 1. Copy existing configs as templates
cp config/scenarios/basic_main.json config/scenarios/my_scenario.json
cp config/topology/basic_topology.json config/topology/my_topology.json

# 2. Modify configurations for your requirements
# 3. Run your custom scenario
python src/scenarios/basic/scenario.py --topology config/topology/my_topology.json --config config/scenarios/my_scenario.json
```

**📖 Complete Guide**: See `docs/docs/tutorials/custom-scenarios.md` for detailed instructions on creating scenarios with heterogeneous clients, dynamic network conditions, and custom policies.

## Project Structure

```
flopy-net/
├── src/                    # Core Python source code
│   ├── core/              # Base interfaces, models, policies, repositories
│   ├── fl/                # Federated learning framework (server/client)
│   ├── networking/        # GNS3 integration, SDN controllers, simulators
│   ├── policy_engine/     # Policy management and enforcement service
│   ├── metrics/           # Collector service and analytics
│   ├── scenarios/         # Experimental scenarios and configuration
│   └── utils/             # Shared utilities and helpers
├── dashboard/             # Web-based monitoring interface
│   ├── frontend/          # React TypeScript application
│   └── backend/           # FastAPI data aggregation service
├── config/                # System configuration files
│   ├── policies/          # Policy definitions and rules
│   ├── gns3/              # Network topology templates
│   └── scenarios/         # Experimental configurations
├── docker/                # Container definitions and entrypoints
├── scripts/               # Utility and maintenance scripts
├── docs/                  # Comprehensive documentation
└── docker-compose.yml     # Main deployment configuration
```

## Documentation Structure

### Component Documentation
- **`dashboard/README.md`**: Dashboard setup, development, and API documentation
- **`src/networking/README.md`**: Network simulation and GNS3 integration
- **`config/README.md`**: Configuration system and policy management
- **`scripts/README.md`**: Utility scripts and maintenance tools

### API Documentation
- **Policy Engine API**: http://localhost:5000 (Flask REST API, endpoints listed in source code)
- **Collector API**: http://localhost:8000/api (Custom endpoint documentation at /api)
- **Dashboard API**: http://localhost:8001 (FastAPI backend, docs availability depends on configuration)

### Research Documentation
- **`docs/`**: Comprehensive technical documentation and research guides
- **LaTeX Report**: Complete technical report in `docs/latex-report/`
- **Custom Scenarios Guide**: `docs/docs/tutorials/custom-scenarios.md` - Complete guide to creating custom FL scenarios
- **Scenario Components**: `docs/docs/components/scenarios.md` - Built-in scenarios and architecture
- **Configuration Templates**: `docs/latex-report/appendices/B-configuration-templates.tex` - JSON config examples

## Version Information

- **Current Version**: v1.0.0-alpha.8
- **Stability**: **Alpha - Active development, breaking changes expected**
- **Testing Status**: **Limited testing - many features are experimental**
- **Production Readiness**: **NOT suitable for production use**
- **Python Version**: 3.8+
- **Container Runtime**: Docker 20.10+
- **Supported Platforms**: Linux, Windows, macOS

## Quick Reference

- **System Status**: `docker-compose ps`
- **Configuration**: Edit environment variables in `docker-compose.yml` (no .env file needed)
- **Policy Management**: Edit `config/policies/policies.json` for active policies
- **GNS3 Management**: Use scripts in `scripts/` directory for maintenance
- **Log Monitoring**: `docker-compose logs -f [service-name]`

## Contributing

FLOPY-NET is an open-source research platform. Contributions are welcome!

1. **Fork the repository** and create a feature branch
2. **Follow the coding standards** defined in the development documentation
3. **Add tests** for new functionality
4. **Update documentation** for any changes
5. **Submit a pull request** with detailed description

See `docs/development/contributing.md` for detailed contribution guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use FLOPY-NET in your research, please cite:

```bibtex
@misc{flopynet2025,
  title={FLOPY-NET: A Modular Policy-Driven Architecture and Platform for Network-Aware Federated Learning Analysis},
  author={Abdulmelik Saylan},
  year={2025},
  version={v1.0.0-alpha.8},
  url={https://github.com/abdulmelink/flopy-net}
}
```

## Support & Community

- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Community discussions and Q&A
- **Documentation**: Comprehensive guides and API references in `docs/`
- **Examples**: Sample configurations and experiments in `config/scenarios/`

---

**FLOPY-NET** - Advancing Federated Learning Research Through Network-Aware Experimentation
