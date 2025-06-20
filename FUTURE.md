# FLOPY-NET Future Roadmap

This document outlines the planned future work and potential improvements for the FLOPY-NET platform based on the current v1.0.0-alpha.8 implementation status.

---

## Current State Assessment

FLOPY-NET v1.0.0-alpha.8 provides a solid foundation with:
- **Flower Framework Integration**: Full Flower-based FL server and client implementation
- **Container Architecture**: Docker Compose with static IP assignment (192.168.100.0/24)
- **Core Services**: Policy Engine, Collector, SDN Controller, OpenVSwitch all operational
- **GNS3 Integration**: Functional network simulation with programmable topology control
- **Dashboard System**: React frontend with FastAPI backend for real-time monitoring
- **Model Support**: PyTorch-based CNN/MLP models for MNIST, CIFAR-10, and financial datasets

## Prioritized Next Steps (Immediate Focus)

Based on the current implementation, the following high-impact features should be prioritized:

1. **Enhanced Real Dataset Training**: Expand the current model implementations to support more realistic datasets and improve training performance with the existing PyTorch + Flower integration.

2. **Advanced Network Scenario Library**: Leverage the existing GNS3 and SDN integration to create a comprehensive library of network scenarios with pre-configured topologies for common FL research patterns.

3. **Policy Engine Enhancement**: Extend the current Flask-based Policy Engine with more sophisticated policy types, including dynamic client selection, security policies, and automated network response policies.

4. **Dashboard Interactivity**: Enhance the React dashboard to provide interactive control over the GNS3 topology, allowing researchers to modify network conditions in real-time during experiments.

5. **Metrics Analysis Tools**: Build upon the existing SQLite-based metrics collection to provide automated analysis, comparison tools, and research-ready data export capabilities.

---

## Thematic Roadmap Details

The following sections provide a detailed breakdown of planned features based on the current implementation.

### 1. Enhanced Federated Learning Capabilities

Building upon the existing Flower framework integration and PyTorch model support.

#### 1.1. Advanced Model Architectures
- **Current State:** Basic CNN and MLP models for MNIST/CIFAR-10
- **Next Step:** Expand model support for state-of-the-art architectures
  - **Action:** Implement ResNet, VGG, and Transformer architectures within the existing model handler system
  - **Action:** Add support for natural language processing models using Hugging Face integration
  - **Action:** Create scenario-specific models for computer vision, NLP, and time-series forecasting

#### 1.2. Advanced Aggregation Algorithms
- **Current State:** FedAvg implementation through Flower framework
- **Next Step:** Implement robust aggregation methods to handle non-IID data and Byzantine clients
  - **Action:** Extend the FL Server with FedProx, FedNova, and SCAFFOLD algorithms
  - **Action:** Add Byzantine-robust aggregation (Krum, Trimmed Mean, Byzantine-robust FedAvg)
  - **Action:** Implement adaptive aggregation based on network conditions and client reliability

#### 1.3. Privacy-Preserving Mechanisms
- **Current State:** Basic FL client with data locality
- **Next Step:** Implement advanced privacy protection mechanisms
  - **Action:** Integrate differential privacy using PyTorch Opacus within FL clients
  - **Action:** Add secure aggregation protocols for parameter encryption
  - **Action:** Implement homomorphic encryption for sensitive data scenarios

### 2. Network Simulation Enhancement

Leveraging the existing GNS3 and SDN integration for more sophisticated network scenarios.

#### 2.1. Advanced Network Scenario Library
- **Current State:** Basic GNS3 integration with topology creation
- **Next Step:** Create comprehensive pre-built network scenarios
  - **Action:** Develop scenario templates for edge computing, IoT networks, and cellular environments
  - **Action:** Implement hierarchical network topologies with multi-tier federated learning
  - **Action:** Add support for dynamic client join/leave scenarios during training

#### 2.2. Enhanced SDN Control
- **Current State:** Ryu controller with basic OpenFlow support
- **Next Step:** Advanced programmable network behavior
  - **Action:** Implement QoS policies for differentiated FL traffic handling
  - **Action:** Add adaptive routing based on FL training progress and network conditions
  - **Action:** Develop network security policies that respond to detected anomalies

#### 2.3. Real-time Network Condition Simulation
- **Current State:** Static network condition configuration
- **Next Step:** Dynamic network condition changes during experiments
  - **Action:** Implement time-based network condition scenarios (e.g., daily traffic patterns)
  - **Action:** Add event-driven network failures and recovery scenarios
  - **Action:** Create realistic mobility patterns for mobile federated learning scenarios

### 3. Enhanced Policy and Security Framework

Building upon the existing Flask-based Policy Engine.

#### 3.1. Advanced Policy Types
- **Current State:** Basic policy definitions and enforcement
- **Next Step:** Sophisticated policy management and enforcement
  - **Action:** Implement client reputation systems with trust scoring
  - **Action:** Add dynamic client selection policies based on performance and reliability
  - **Action:** Create security policies that automatically respond to detected threats

#### 3.2. Compliance and Audit Framework
- **Current State:** Basic policy logging and event tracking
- **Next Step:** Comprehensive compliance monitoring and reporting
  - **Action:** Implement regulatory compliance policies (GDPR, HIPAA)
  - **Action:** Add automated audit trail generation and reporting
  - **Action:** Create policy impact analysis and performance correlation tools

### 4. Dashboard and User Experience Improvements

Enhancing the existing React + FastAPI dashboard architecture.

#### 4.1. Interactive Network Control
- **Current State:** Read-only network topology visualization
- **Next Step:** Interactive network topology management
  - **Action:** Add drag-and-drop network topology editor
  - **Action:** Implement real-time network condition adjustment controls
  - **Action:** Create scenario recording and playback functionality

#### 4.2. Advanced Analytics and Visualization
- **Current State:** Basic metrics visualization with charts
- **Next Step:** Comprehensive research analytics platform
  - **Action:** Implement comparative analysis tools for multiple experiments
  - **Action:** Add statistical significance testing and visualization
  - **Action:** Create automated report generation for research publications

#### 4.3. Experiment Management
- **Current State:** Manual experiment configuration and execution
- **Next Step:** Comprehensive experiment lifecycle management
  - **Action:** Implement experiment templating and versioning system
  - **Action:** Add collaborative features for multi-researcher environments
  - **Action:** Create experiment reproducibility verification tools
- **Next Step:** Provide context on the environment where each client is running.
  - **Action:** Modify the `fl-client` entrypoint script or application to collect system information (e.g., OS, CPU architecture, memory) using libraries like `platform` or `psutil`.
  - **Action:** Report this static information to the `Collector` upon startup.
  - **Action:** Display the host information in the dashboard's client list.

#### 4.3. Enhanced CLI Tool & Documentation
- **Current State:** The `main.py` script is a basic service launcher.
- **Next Step:** Improve developer and user experience.
  - **Action:** Use a library like `Click` or `Typer` to build a richer CLI with commands like `flopynet scenario run <name>`, `flopynet system status`, `flopynet policy list`.
  - **Action:** Build a dedicated documentation website using `MkDocs` (already a dependency). 