---
sidebar_position: 1
---

# System Architecture Overview

FLOPY-NET is architected as a modular, policy-driven platform that integrates a custom federated learning framework with comprehensive network simulation and monitoring. The system follows a layered microservices architecture approach, enabling researchers to conduct realistic federated learning experiments while maintaining strict policy compliance and comprehensive observability.

## High-Level Architecture

FLOPY-NET is architected as a containerized platform integrating federated learning with comprehensive network simulation. The system runs across multiple deployment modes: standalone Docker Compose for development and GNS3 VM integration for advanced network research.

```mermaid
graph TB
    subgraph "User Interface Layer"
        A[Dashboard Frontend<br/>React + TypeScript<br/>Port 3000]
        B[Dashboard API<br/>FastAPI Backend<br/>Port 8001]  
        C[CLI Interface<br/>Python main.py<br/>src/main.py]
    end
    
    subgraph "Core Services Layer"
        D[Policy Engine<br/>Flask REST API<br/>Port 5000<br/>IP: 192.168.100.20]
        E[Collector Service<br/>Metrics & Analytics<br/>Port 8000<br/>IP: 192.168.100.40]
        F[FL Server<br/>Flower gRPC Server<br/>Port 8080<br/>IP: 192.168.100.10]
        G[FL Metrics API<br/>HTTP Endpoints<br/>Port 8081]
    end
    
    subgraph "Federated Learning Layer"
        H[FL Client 1<br/>IP: 192.168.100.101<br/>Flower Client]
        I[FL Client 2<br/>IP: 192.168.100.102<br/>Flower Client]
        J[FL Client N<br/>IP: 192.168.100.103-255<br/>Flower Client]
        K[MetricsTrackingStrategy<br/>Custom FedAvg Extension]
        L[Policy Integration<br/>Real-time Checks]
        M[SQLite Round Storage<br/>fl_rounds.db]
    end
    
    subgraph "Network Simulation Layer"
        N[GNS3 VM Integration<br/>Network Topology Management<br/>VM Host Port 3080]
        O[SDN Controller<br/>Ryu OpenFlow<br/>Port 6633/8181<br/>IP: 192.168.100.41]
        P[OpenVSwitch<br/>Programmable Network<br/>IP: 192.168.100.60-99]
        Q[Network Monitoring<br/>Real-time Metrics]
    end
    
    subgraph "Data & Storage Layer"
        R[SQLite Metrics DB<br/>Time-series Data<br/>logs/metrics.db]
        S[Policy Storage<br/>JSON Configuration<br/>config/policies/]
        T[Event Logs<br/>JSONL Format<br/>logs/events.jsonl]
        U[Configuration Store<br/>Docker Environment<br/>docker-compose.yml]
    end
    
    %% User Interface flows
    A -.-> B
    B -.-> D
    B -.-> E
    B -.-> F
    C -.-> D
    C -.-> E
    C -.-> F
    
    %% Critical dependency flows
    D --> F
    F --> H
    F --> I
    F --> J
    D --> H
    D --> I
    D --> J
    
    %% FL training flows (Flower gRPC)
    F <--> H
    F <--> I
    F <--> J
    H --> K
    I --> K
    J --> K
    K --> F
    K --> M
    F --> L
    L --> D
    G --> E
    
    %% Network simulation flows
    N -.-> O
    N -.-> P
    O <--> P
    
    %% Storage flows
    E --> R
    D --> S
    E --> T
    D --> U
    F --> M
    
    %% Monitoring flows
    H --> E
    I --> E
    J --> E
    O --> E
    P --> E
    F --> E
    
    style D fill:#d2a8ff,stroke:#8b5cf6,color:#000
    style A fill:#79c0ff,stroke:#1f6feb,color:#000
    style E fill:#7ce38b,stroke:#1a7f37,color:#000
    style F fill:#ffa7c4,stroke:#bf8700,color:#000
    style N fill:#f0ad4e,stroke:#ec971f,color:#000
    style M fill:#f85149,stroke:#da3633,color:#fff
```

## Architectural Design Principles

### 1. Policy-Driven Architecture

The **Policy Engine** serves as the central nervous system of FLOPY-NET, ensuring that all components operate according to defined security, performance, and governance rules.

**Core Principles:**
- Centralized Decision Making: All system components query the Policy Engine before taking actions
- Real-time Enforcement: Policies are enforced in real-time across all system operations
- Dynamic Updates: Policy changes can be applied without system restart
- Audit Trail: Complete logging of policy decisions and enforcement actions
- Event-Driven Compliance: Continuous monitoring with event buffer system

**Implementation:**
- Flask-based REST API service on port 5000
- SQLite and JSON storage backends for policies and events
- Custom policy functions in `config/policy_functions/`
- Real-time event buffer with configurable retention

### 2. Microservices Architecture

Each major component is implemented as an independent service with well-defined interfaces, enabling independent development, deployment, and scaling.

**Service Independence:**
- Components can be developed and deployed independently
- Different technology stacks optimized for each service
- Fault isolation prevents cascading failures
- Horizontal scaling of individual components

**Interface Contracts:**
- RESTful APIs with comprehensive documentation
- Standardized error handling and status codes
- Event-driven communication patterns
- Consistent authentication and authorization

```mermaid
graph LR
    subgraph "Service Communication"
        A[Policy Engine<br/>Flask REST<br/>Port 5000] <--> B[Collector<br/>Custom HTTP<br/>Port 8000]
        A <--> C[FL Server<br/>Flower gRPC<br/>Port 8080]
        A <--> D[SDN Controller<br/>OpenFlow<br/>Port 6633]
        B <--> C
        B <--> D
        C <--> E[FL Clients<br/>Flower gRPC<br/>Dynamic Ports]
        D <--> F[OpenVSwitch<br/>OpenFlow<br/>Network Layer]
        C --> G[SQLite Storage<br/>fl_rounds.db]
        C --> H[HTTP Metrics API<br/>Port 8081]
    end
    
    style A fill:#d2a8ff,stroke:#8b5cf6,color:#000
    style B fill:#7ce38b,stroke:#1a7f37,color:#000
    style C fill:#ffa7c4,stroke:#bf8700,color:#000
    style G fill:#f85149,stroke:#da3633,color:#fff
```

### 3. Observable Systems

Every component exposes comprehensive metrics, logs, and control interfaces to ensure complete system visibility.

**Metrics Collection:**
- Performance metrics from all components
- Business metrics for federated learning research
- Infrastructure metrics for system health
- Custom metrics for experimental analysis

**Structured Logging:**
- JSON-formatted structured logs
- Centralized log aggregation in Collector
- Configurable log levels and retention
- Event correlation across components

**Health Monitoring:**
- Component health endpoints
- Dependency health checking
- Resource utilization monitoring
- Automated alerting and remediation

### 3. Observable and Controllable Systems

Every component exposes metrics, logs, and control interfaces:

- Metrics: Performance, health, and business metrics
- Events: System events and state changes
- Controls: REST APIs for configuration and control
- Health Checks: Liveness and readiness probes

### 4. Research-First Design

The platform is optimized for research workflows:

- Reproducible Experiments: Deterministic seeding and configuration
- Extensible Frameworks: Plugin architecture for custom algorithms
- Data Export: Comprehensive data export for analysis
- Scenario Management: Pre-defined and custom scenarios

## Component Interactions

### System Startup Sequence

```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant PE as Policy Engine
    participant FS as FL Server
    participant FC as FL Clients
    participant SUP as Support Services
    
    Note over DC,SUP: Container Startup Sequence
    
    %% Phase 1: Core Services
    DC->>PE: Start Policy Engine (No Dependencies)
    PE->>PE: Initialize Flask API (port 5000)
    PE-->>DC: Health check passes
    
    Note over PE: Policy Engine Ready
    
    %% Phase 2: FL Server
    DC->>FS: Start FL Server (depends on Policy Engine)
    FS->>PE: Wait for health check
    PE-->>FS: Health OK (200)
    FS->>FS: Initialize Flower server (port 8080)
    FS-->>DC: Health check passes
    
    Note over FS: FL Server Ready
    
    %% Phase 3: FL Clients & Support Services
    par FL Clients
        DC->>FC: Start FL Clients (depends on Server + Policy)
        FC->>FS: Check server health
        FC->>PE: Check policy health
        FS-->>FC: Server ready
        PE-->>FC: Policy ready
        FC->>FS: Connect via Flower gRPC
    and Support Services
        DC->>SUP: Start Collector, SDN Controller, OpenVSwitch
        SUP->>SUP: Initialize independent services
    end
    
    Note over PE,SUP: All Services Ready for FL Training
```

### Scenario Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as CLI/Dashboard
    participant S as Scenario
    participant GNS3 as GNS3 Environment
    participant FL as FL Components
    participant DB as Results
    
    Note over U,DB: Scenario Execution Phases
    
    %% Phase 1: Setup
    U->>CLI: Define & execute scenario
    CLI->>S: Initialize scenario
    S->>GNS3: Deploy network topology
    GNS3-->>S: Infrastructure ready
    S->>FL: Start FL server & clients
    FL-->>S: Services ready
    
    Note over S: Status: "setup_complete"
    
    %% Phase 2: Execution
    U->>CLI: Start training
    CLI->>S: Run federated learning
    S->>FL: Execute FL rounds
    
    loop Training Rounds
        FL->>FL: Local training & aggregation
        FL->>DB: Store metrics
        
        alt Training Complete
            FL->>S: Training finished
        else Policy Violation
            FL->>S: Training paused
        end
    end
    
    Note over S: Status: "workload_complete"
    
    %% Phase 3: Cleanup (Optional)
    U->>CLI: Cleanup (optional)
    CLI->>S: Clean resources
    S->>GNS3: Stop/preserve topology
    S->>DB: Store final results
    
    Note over U,DB: Scenario Complete
```

### Docker Health Check Dependencies

```mermaid
sequenceDiagram
    participant DC as Docker Compose
    participant PE as Policy Engine
    participant FS as FL Server  
    participant C1 as FL Client One
    participant C2 as FL Client Two
    
    Note over DC,C2: Health Check Dependency Chain
    
    DC->>PE: docker-compose up policy-engine
    PE->>PE: Start Flask server on port 5000
    PE->>PE: Load policies from config/
    PE->>PE: Initialize health endpoint
      loop Health Check Polling
        DC->>PE: curl -f http://localhost:5000/health
        PE-->>DC: 200 OK {"status": "healthy"}
    end
    
    Note over PE: Policy Engine Health Check PASSED
    
    DC->>FS: docker-compose up fl-server (depends_on policy-engine)
    FS->>PE: Wait for policy engine health (entrypoint)
    PE-->>FS: Health check response
    FS->>FS: Start Flower server on port 8080
    FS->>FS: Start HTTP API on port 8081
      loop Health Check Polling
        DC->>FS: curl -f http://localhost:8081/health
        FS-->>DC: 200 OK {"status": "healthy", "current_round": 0}
    end
    
    Note over FS: FL Server Health Check PASSED
    
    par FL Clients Wait for Dependencies
        DC->>C1: docker-compose up fl-client-one (depends_on fl-server + policy-engine)
        C1->>FS: Check FL server health
        C1->>PE: Check policy engine health
        FS-->>C1: 200 OK (healthy)
        PE-->>C1: 200 OK (healthy)
        C1->>C1: Start Flower client
        C1->>FS: Connect via gRPC port 8080
    and
        DC->>C2: docker-compose up fl-client-2 (depends_on fl-server + policy-engine)
        C2->>FS: Check FL server health
        C2->>PE: Check policy engine health  
        FS-->>C2: 200 OK (healthy)
        PE-->>C2: 200 OK (healthy)
        C2->>C2: Start Flower client
        C2->>FS: Connect via gRPC port 8080
    end
    
    Note over DC,C2: All Dependencies Satisfied - System Ready
```

## Data Flow Architecture

### Metrics Collection Flow

```mermaid
graph TD
    subgraph "Data Sources"
        A[FL Training Metrics]
        B[Network Performance]
        C[System Resources]
        D[Policy Violations]
    end
    
    subgraph "Collection Layer"
        E[Collector Service]
        F[Event Stream]
        G[Metrics Buffer]
    end
    
    subgraph "Storage Layer"
        H[Time Series DB]
        I[Event Store]
        J[Model Registry]
    end
    
    subgraph "Consumption Layer"
        K[Dashboard]
        L[Alert System]
        M[Export API]
    end
    
    A --> E
    B --> E
    C --> E
    D --> F
    E --> G
    F --> I
    G --> H
    E --> J
    H --> K
    I --> L
    H --> M
    I --> M
    J --> M
```

### Policy Enforcement Flow

```mermaid
graph TD
    subgraph "Policy Definition"
        A[Security Policies]
        B[Performance Policies]
        C[Compliance Policies]
    end
    
    subgraph "Policy Engine"
        D[Policy Loader]
        E[Rule Engine]
        F[Enforcement Points]
    end
    
    subgraph "Target Components"
        G[FL Server]
        H[FL Clients]
        I[Network Controller]
        J[Data Access]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    F --> J
    
    G --> E
    H --> E
    I --> E
    J --> E
```

## Security Architecture

### Multi-Layer Security Model

FLOPY-NET implements security at multiple layers:

1. Network Layer: SDN-based network isolation and monitoring
2. Application Layer: Policy-based access control and validation
3. Data Layer: Encryption at rest and in transit
4. Component Layer: Service-to-service authentication

```mermaid
graph TB
    subgraph "Security Layers"
        A[User Authentication]
        B[API Authorization]
        C[Component Authentication]
        D[Network Isolation]
        E[Data Encryption]
    end
    
    subgraph "Security Controls"
        F[Policy Engine]
        G[Certificate Management]
        H[Secret Management]
        I[Audit Logging]
    end
    
    A --> F
    B --> F
    C --> G
    D --> H
    E --> H
    F --> I
    G --> I
    H --> I
```

## Scalability Architecture

### Horizontal Scaling

```mermaid
graph TB
    subgraph "Load Balancer"
        A[API Gateway]
    end
    
    subgraph "Dashboard Tier"
        B[Dashboard 1]
        C[Dashboard 2]
        D[Dashboard N]
    end
    
    subgraph "Service Tier"
        E[Collector 1]
        F[Collector 2]
        G[Policy Engine]
    end
    
    subgraph "FL Tier"
        H[FL Server Cluster]
        I[FL Client Pool]
    end
    
    subgraph "Storage Tier"
        J[Distributed Database]
        K[Shared Storage]
    end
    
    A --> B
    A --> C
    A --> D
    B --> E
    C --> F
    B --> G
    C --> G
    E --> H
    F --> H
    G --> H
    H --> I
    E --> J
    F --> J
    H --> K
```

## Performance Characteristics

### Throughput Metrics

| Component | Metric | Target | Maximum |
|-----------|---------|---------|----------|
| Dashboard API | Requests/sec | 1,000 | 10,000 |
| Collector | Metrics/sec | 10,000 | 100,000 |
| Policy Engine | Evaluations/sec | 5,000 | 50,000 |
| FL Framework | Clients | 100 | 1,000 |

### Latency Targets

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| API Response | 50ms | 200ms | 500ms |
| Metric Collection | 10ms | 50ms | 100ms |
| Policy Evaluation | 5ms | 20ms | 50ms |
| FL Round Start | 1s | 5s | 10s |

## Deployment Architecture

### Docker Compose Development Environment

For development and simple testing scenarios:

```mermaid
graph TB
    subgraph "Host Machine"
        A[Docker Compose<br/>Main Orchestrator]
        B[Local Services<br/>All FLOPY-NET Components]
        C[Static Network<br/>192.168.100.0/24]
    end
    
    A --> B
    B --> C
```

### GNS3 VM Integration (Recommended for Research)

For advanced network simulation and realistic federated learning research:

```mermaid
graph TB
    subgraph "Host Machine"
        A[FLOPY-NET Control<br/>Dashboard + CLI]
        B[GNS3 VM<br/>Ubuntu 20.04/22.04]
    end
    
    subgraph "GNS3 VM Environment"
        C[GNS3 Server<br/>Port 3080]
        D[Docker Runtime<br/>Container Orchestration]
        E[FLOPY-NET Containers<br/>abdulmelink/* Images]
        F[Virtual Network<br/>SDN + OpenVSwitch]
    end
    
    A -.-> B
    B --> C
    C --> D
    D --> E
    E --> F
```

### Production Kubernetes Environment

For large-scale research deployments:

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        A[Ingress Controller]
        B[Dashboard Pods<br/>3 Replicas]
        C[Core Service Pods<br/>Policy Engine, Collector]
        D[FL Pods<br/>Server + Client Pool]
    end
    
    subgraph "External Services"
        E[GNS3 VM Farm<br/>Multiple Simulation Hosts]
        F[Database Cluster<br/>PostgreSQL]
        G[Object Storage<br/>Model & Data Store]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    D --> G
```

## Technology Stack

### Core Infrastructure

| Layer | Technology | Purpose | Configuration |
|-------|------------|---------|---------------|
| Container Platform | Docker + Compose | Service orchestration | docker-compose.yml |
| Network Simulation | GNS3 VM + Docker | Realistic network topologies | Ubuntu VM + GNS3 Server |
| SDN Control | Ryu Controller + OVS | Programmable networking | OpenFlow 1.3 |
| Backend Services | Python + Flask/Custom HTTP | Microservices architecture | REST APIs + gRPC |
| Frontend Dashboard | React 18 + TypeScript | Interactive monitoring | Node.js + Vite |
| Data Storage | SQLite + JSON | Metrics and configuration | File-based storage |
| Metrics Collection | Custom collector service | System monitoring | Port 8000 |

### Federated Learning Stack

| Component | Technology | Purpose | Integration |
|-----------|------------|---------|-------------|
| FL Framework | Flower v1.5.0 + Custom Extensions | Distributed training coordination | Flower gRPC protocol |
| FL Server | Custom Flower Server + MetricsTrackingStrategy | Server-side orchestration | Python + SQLite |
| FL Clients | Custom Flower Clients + ModelHandler | Client-side training | Dynamic model loading |
| Model Training | PyTorch + scikit-learn | Deep learning models | CNN/ResNet support |
| Data Handling | Custom data loaders + Pandas | Data preprocessing | CIFAR-10/MNIST/Custom |
| Aggregation | FedAvg + Custom Strategies | Model averaging | Policy integration |
| Storage | SQLite + JSON | Round tracking & metrics | File-based persistence |
| Policy Engine | Flask + Custom rule engine | Governance & compliance | Real-time enforcement |

### Network & Monitoring Stack

| Component | Technology | Purpose | Deployment |
|-----------|------------|---------|------------|
| **Network Emulation** | GNS3 + Docker | Realistic network conditions | VM-based |
| **SDN Controller** | Ryu Framework | Network programmability | Container in GNS3 |
| **Virtual Switches** | OpenVSwitch | Layer 2/3 switching | Hardware acceleration |
| **Monitoring** | Custom metrics collection | Real-time observability | REST APIs |
| **Visualization** | React + D3.js | Interactive charts | Web dashboard |
| **Log Aggregation** | Structured JSON logs | Centralized logging | File-based |

## Configuration Management

### Configuration Hierarchy

```mermaid
graph TD
    A[CLI Arguments] --> B[Environment Variables]
    B --> C[Configuration Files]
    C --> D[Default Values]
    
    E[Policy Engine] --> A
    F[Component Configs] --> C
    G[Runtime Configs] --> B
```

### Configuration Files Structure

```
config/
├── system/
│   ├── collector_config.json
│   ├── policy_config.json
│   └── server_config.json
├── scenarios/
│   ├── basic_fl.json
│   ├── non_iid.json
│   └── byzantine.json
├── policies/
│   ├── security_policies.json
│   ├── performance_policies.json
│   └── compliance_policies.json
└── network/
    ├── topology_configs/
    └── gns3_templates/
```

## Monitoring and Observability

### Metrics Collection

FLOPY-NET collects four types of metrics:

1. Business Metrics: FL accuracy, convergence, client participation
2. Performance Metrics: Latency, throughput, resource utilization
3. Infrastructure Metrics: CPU, memory, disk, network usage
4. Security Metrics: Policy violations, authentication failures

### Logging Strategy

```mermaid
graph LR
    subgraph "Log Sources"
        A[Application Logs]
        B[Access Logs]
        C[Audit Logs]
        D[Error Logs]
    end
    
    subgraph "Log Processing"
        E[Structured Logging]
        F[Log Aggregation]
        G[Log Analysis]
    end
    
    subgraph "Log Storage"
        H[Local Files]
        I[Elasticsearch]
        J[Long-term Archive]
    end
    
    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    F --> G
    F --> H
    G --> I
    H --> J
```

This architecture ensures that FLOPY-NET provides a robust, scalable, and research-friendly platform for studying federated learning in realistic network environments.
