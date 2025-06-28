---
title: Welcome to FLOPY-NET
description: Federated Learning Observatory Platform - Network Emulation & Testing
---

# FLOPY-NET

**Federated Learning Observatory Platform - Network Emulation & Testing**

FLOPY-NET v1.0.0-alpha.8 is a comprehensive research platform for evaluating federated learning systems under realistic network conditions. The platform provides a complete scenario-driven testing environment with GNS3 network emulation, SDN control, comprehensive monitoring, and policy enforcement capabilities for federated learning research.

## Current Implementation Status

**Research & Simulation Focus**: The current v1.0.0-alpha.8 implementation provides federated learning simulation using synthetic data to demonstrate system behavior, network interaction patterns, and policy enforcement. This simulation approach enables comprehensive study of network effects, policy enforcement, and system scalability without the computational overhead of actual machine learning training.

The FL server and client components simulate training rounds, model aggregation, and convergence patterns to provide realistic federated learning behavior for network and system research. For production federated learning research  requiring actual ML training, the base components can be extended with real datasets, models, and training algorithms.

## 🚀 Quick Start

Get started with FLOPY-NET scenario-based experiments:

```bash
# Clone the repository
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# Start with Docker Compose (development)
docker-compose up -d

# Or run scenario-based experiments
python -m src.scenarios.run_scenario --scenario config/scenarios/basic_main.json

# Access system interfaces
# Dashboard Frontend: http://localhost:8085
# Policy Engine API: http://localhost:5000
# Collector API: http://localhost:8083
```

## 🔧 Key Features

- **Scenario-Based FL Simulation**: Comprehensive experiment framework with GNS3 network simulation and policy-driven federated learning simulation coordination
- **Advanced Network Emulation**: GNS3 VM integration with realistic topology simulation, programmable network conditions, and SDN control capabilities  
- **Container Architecture**: Docker-based microservices with static IP assignment supporting both development (Docker Compose) and research (GNS3) environments
- **Policy-Driven Governance**: Centralized Policy Engine providing security, compliance, access control, and automated decision-making across distributed components
- **Comprehensive Monitoring**: Real-time metrics collection with React dashboard, time-series data storage, and research-ready analytics export
- **Extensible FL Framework**: Base simulation framework designed for extension with custom federated learning implementations, real ML models, and training algorithms
- **SDN Integration**: Ryu OpenFlow controllers with programmable network behavior, traffic management, and quality-of-service enforcement

## 📚 Documentation

- **[Getting Started](./docs/getting-started/installation)** - Installation guide with Docker Compose and GNS3 VM setup procedures
- **[User Guide](./docs/user-guide/running-experiments)** - Comprehensive experiment execution with scenario management and network simulation
- **[Architecture](./docs/architecture/overview)** - System architecture covering microservices, containers, and GNS3 integration
- **[API Reference](./docs/api/overview)** - Complete REST API documentation for all platform services and components
- **[GNS3 Integration](./docs/user-guide/gns3-integration)** - Advanced network simulation setup, template management, and custom topology creation

## 🔬 Research Applications

FLOPY-NET is designed for researchers working on:

- **Network-Aware FL Systems**: Study FL behavior and performance under realistic network conditions (latency, packet loss, bandwidth)
- **FL Algorithm Development**: Test and compare different federated learning approaches with consistent network simulation conditions
- **Edge Computing Research**: Evaluate resource-constrained scenarios with container resource limits and mobile network conditions
- **System Architecture Studies**: Test policy enforcement, monitoring systems, and distributed governance in federated learning environments
- **Network Optimization**: Evaluate client selection strategies, adaptive algorithms, and network topology effects on FL performance
- **Security and Policy Research**: Study compliance monitoring, trust management, and security policy enforcement in distributed systems

*Note: For actual ML research requiring real training, the base simulation framework can be extended with custom models, datasets, and training algorithms.*

## 🛠️ Container Components

- **FL Server**: `abdulmelink/flopynet-server:v1.0.0-alpha.8` (192.168.100.10:8080)
- **FL Clients**: `abdulmelink/flopynet-client:v1.0.0-alpha.8` (192.168.100.101-102)
- **Policy Engine**: `abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8` (192.168.100.20:5000)
- **Collector Service**: `abdulmelink/flopynet-collector:v1.0.0-alpha.8` (192.168.100.40:8000)
- **SDN Controller**: `abdulmelink/flopynet-sdn-controller:v1.0.0-alpha.8` (192.168.100.41:6633/8181)
- **OpenVSwitch**: `abdulmelink/flopynet-openvswitch:v1.0.0-alpha.8` (192.168.100.60)

## 📊 Supported Simulation Scenarios

- **Basic FL Simulation**: Standard federated learning simulation with synthetic data
- **Network Condition Studies**: Different bandwidth, latency, and loss conditions
- **Client Heterogeneity**: Diverse device capabilities and resource constraints
- **Dynamic Network Conditions**: Changing network topology and client availability
- **Security Policy Testing**: Policy enforcement and compliance monitoring scenarios

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/development/contributing) for details on:

- Development setup
- Code standards
- Testing procedures
- Pull request process

## 📄 License

FLOPY-NET is released under the MIT License. See the [LICENSE](https://github.com/abdulmelink/flopy-net/blob/main/LICENSE) file for details.

## 🔗 Links

- **[GitHub Repository](https://github.com/abdulmelink/flopy-net)**
- **[Documentation](docs/intro)**
- **[Issues & Support](https://github.com/abdulmelink/flopy-net/issues)**
