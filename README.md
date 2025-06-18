# FLOPY-NET: Federated Learning and SDN Observatory Platform

FLOPY-NET is a comprehensive platform for simulating and monitoring federated learning (FL) environments over a Software-Defined Network (SDN). It integrates GNS3 for network emulation, a custom FL framework, and a monitoring dashboard to provide insights into the performance, security, and behavior of distributed learning systems.

## Key Features

- **Federated Learning Simulation**: Train and evaluate FL models across a network of distributed clients.
- **SDN Integration**: Utilizes an SDN controller (Ryu) to manage network traffic, enforce policies, and simulate real-world network conditions.
- **Comprehensive Monitoring Dashboard**: A web-based interface to visualize FL training progress, network topology, system events, and policy compliance.
- **Policy Engine**: A centralized service to define and enforce rules for network traffic and component interactions.
- **Data Collection and Analysis**: A dedicated collector service gathers metrics from all components for storage and analysis.
- **Realistic Scenario Simulation**: Define and run complex scenarios involving different network conditions (e.g., packet loss, latency) and node behaviors.

---

## Project Structure

The project is organized into several key directories:

```
/
├── dashboard/        # The web-based monitoring dashboard (React frontend and FastAPI backend)
├── src/              # The core Python source code for all backend services
│   ├── collector/      # Metric collection service
│   ├── fl/             # Federated learning framework components
│   ├── ml/             # Core machine learning models and utilities
│   ├── networking/     # Networking simulation and GNS3 integration
│   ├── policy_engine/  # Policy enforcement service
│   └── scenarios/      # Definable simulation scenarios
├── config/           # System configuration files
├── scripts/          # Utility and setup scripts
└── docker-compose.yml # Main Docker Compose file for launching the platform
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Node.js and npm (for frontend development)
- A running GNS3 server (configured in `docker-compose.yml` and `config/`)

### Running the Platform

1.  **Clone the repository:**
    ```bash
git clone <repository-url>
    cd flopy-net
    ```

2.  **Configure Environment Variables:**
    Create a `.env` file in the root directory and configure the service URLs, particularly for GNS3. You can use the `docker-compose.yml` file as a reference.
    ```env
    GNS3_URL=http://<your-gns3-server-ip>:3080
    POLICY_ENGINE_URL=http://localhost:5000
    # ... other variables
    ```

3.  **Start the services:**
    ```bash
docker-compose up -d
    ```

4.  **Access the Dashboard:**
    Open your browser and navigate to `http://localhost:8085`.

---

## System Components

### 1. Dashboard

The dashboard provides a comprehensive web-based interface to monitor and control the entire FLOPY-NET system. It offers real-time visualization of federated learning progress, network topology, system metrics, and policy compliance.

**Key Features:**
- **Real-time FL Monitoring**: Training progress, client status, model metrics
- **Network Visualization**: Interactive topology maps, SDN integration, GNS3 status
- **Policy Dashboard**: Compliance monitoring, security metrics, trust scores
- **System Health**: Component status, resource usage, performance analytics

**Architecture:**
- **Frontend**: React 18 + TypeScript with Material-UI and interactive visualizations
- **Backend**: FastAPI server aggregating data from Collector, GNS3, and Policy Engine
- **Alternative Interface**: Dash-based dashboard with Plotly charts

**Access Points:**
- Main Dashboard: http://localhost:8085
- API Documentation: http://localhost:8001/docs
- Alternative Interface: http://localhost:8050

For detailed setup, development, and API documentation, see `dashboard/README.md`.

### 2. Collector

The collector service is responsible for gathering, storing, and providing metrics from all other components in the system, including the FL server, network switches, and policy engine. It uses a time-series database for efficient storage and retrieval.

### 3. Policy Engine

The policy engine is a central service that enforces rules and security policies. Other components query the policy engine to determine if actions are permitted (e.g., "Can this client join the training round?"). Policies are defined in configuration files and can be dynamically updated.

### 4. Networking

The networking component, powered by GNS3 and an SDN controller, simulates the underlying network topology. It allows for creating realistic network environments for the FL clients and servers, including the ability to introduce packet loss, latency, and other challenges.

### 5. Scenarios

Scenarios are Python classes that define a complete experiment, including the network topology, the FL training configuration, and any specific events or network conditions to simulate. This allows for reproducible and complex experiments.

---

## Documentation Structure

The project documentation is organized as follows:

### Component Documentation
- **`dashboard/README.md`**: Complete dashboard setup, development, and API documentation
- **`src/ml/README.md`**: Machine learning models, dynamic loading, and development guidelines
- **`src/networking/README.md`**: Network simulation and GNS3 integration overview
- **`src/networking/simulators/README.md`**: Detailed simulator implementation and usage

### Configuration Documentation
- **`config/README.md`**: Configuration system overview, file hierarchy, and best practices
- **`config/policies/README.md`**: Policy definitions, management, and development
- **`config/gns3/templates/README.md`**: GNS3 template configuration and IP management

### Utility Documentation
- **`scripts/README.md`**: Utility scripts for GNS3 management, cleanup, and maintenance

### Quick Reference
- **System Architecture**: This README (overview and getting started)
- **Dashboard Access**: http://localhost:8085 (frontend), http://localhost:8001/docs (API)
- **Configuration Hierarchy**: CLI Args > Environment Variables > JSON Files > Defaults
- **Policy Management**: Edit `config/policies/policies.json` for active policies
- **GNS3 Management**: Use scripts in `scripts/` directory for maintenance

---
