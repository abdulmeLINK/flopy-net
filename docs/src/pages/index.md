---
title: Welcome to FLOPY-NET
description: Federated Learning Observatory Platform - Network Emulation & Testing
---

# FLOPY-NET

**Federated Learning Observatory Platform - Network Emulation & Testing**

FLOPY-NET v1.0.0-alpha.8 is a comprehensive research platform for evaluating Flower-based federated learning algorithms under realistic network conditions. It provides a complete containerized testing environment with GNS3 network emulation, SDN control, performance monitoring, and policy enforcement capabilities.

## 🚀 Quick Start

Get started with FLOPY-NET in minutes:

```bash
# Clone the repository
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# Start the containerized platform
docker-compose up -d

# Access the dashboard
# Dashboard Frontend: http://localhost:8085
# Policy Engine API: http://localhost:5000
# Collector API: http://localhost:8000
```

## 🔧 Key Features

- **Flower Framework Integration**: Production-ready FL server and client implementations with PyTorch models
- **Container Architecture**: Docker Compose with static IP assignment (192.168.100.0/24 network)
- **GNS3 Network Emulation**: Realistic network topology simulation with programmable conditions
- **SDN Integration**: Ryu OpenFlow controllers for programmable network behavior and policy enforcement
- **Real-time Monitoring**: React dashboard with comprehensive metrics collection and interactive visualization
- **Policy-Driven Governance**: Centralized Policy Engine for security, compliance, and access control
- **Comprehensive Metrics**: SQLite-based time-series data with research-ready export capabilities

## 📚 Documentation

- **[Getting Started](./docs/getting-started/installation)** - Docker installation and container setup
- **[User Guide](./docs/user-guide/running-experiments)** - How to run FL experiments with network simulation
- **[Architecture](./docs/architecture/overview)** - Microservices architecture and container integration
- **[API Reference](./docs/api/overview)** - REST API documentation for all services
- **[GNS3 Integration](./docs/user-guide/gns3-integration)** - Network simulation setup and configuration

## 🔬 Research Applications

FLOPY-NET is designed for researchers working on:

- **Network-Aware Federated Learning**: Study FL performance under realistic network conditions (latency, packet loss, bandwidth)
- **FL Algorithm Comparison**: Test and compare different Flower-based FL approaches with consistent network conditions
- **Edge Computing Studies**: Evaluate resource-constrained scenarios with container resource limits
- **Security and Privacy Research**: Test Byzantine-robust algorithms, differential privacy, and threat models
- **System Optimization**: Evaluate client selection strategies, adaptive algorithms, and network topology effects
- **Policy and Governance**: Study compliance monitoring, trust management, and regulatory adherence in distributed ML

## 🛠️ Container Components

- **FL Server**: `abdulmelink/flopynet-server:v1.0.0-alpha.8` (192.168.100.10:8080)
- **FL Clients**: `abdulmelink/flopynet-client:v1.0.0-alpha.8` (192.168.100.101-102)
- **Policy Engine**: `abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8` (192.168.100.20:5000)
- **Collector Service**: `abdulmelink/flopynet-collector:v1.0.0-alpha.8` (192.168.100.40:8000)
- **SDN Controller**: `abdulmelink/flopynet-sdn-controller:v1.0.0-alpha.8` (192.168.100.41:6633/8181)
- **OpenVSwitch**: `abdulmelink/openvswitch:v1.0.0-alpha.8` (192.168.100.60)

- **FL Framework**: Distributed learning coordination
- **Network Controller**: SDN-based traffic management
- **Policy Engine**: Compliance and governance automation
- **Data Collector**: Metrics aggregation and storage
- **Dashboard**: Real-time monitoring and control interface

## 📊 Supported Scenarios

- **Basic FL Training**: Standard federated learning experiments
- **Network Variations**: Different bandwidth, latency, and loss conditions
- **Client Heterogeneity**: Diverse device capabilities and data distributions
- **Dynamic Conditions**: Changing network topology and client availability
- **Security Testing**: Byzantine and adversarial attack simulations

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
