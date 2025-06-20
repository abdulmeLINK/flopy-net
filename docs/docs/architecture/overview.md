---
sidebar_position: 1
---

# System Architecture Overview

FLOPY-NET is architected as a modular, policy-driven platform that integrates the Flower federated learning framework with comprehensive network simulation and monitoring. The system follows a layered microservices architecture approach, enabling researchers to conduct realistic federated learning experiments while maintaining strict policy compliance and comprehensive observability.

## High-Level Architecture

FLOPY-NET consists of five primary layers deployed as Docker containers with static IP assignment (192.168.100.0/24 network), each serving distinct functional responsibilities while maintaining loose coupling through well-defined interfaces:

```mermaid
graph TB
    subgraph "User Interface Layer"
        A[Dashboard Frontend<br/>React + TypeScript<br/>Port 8085]
        B[Dashboard API<br/>FastAPI Backend<br/>Port 8001]
        C[CLI Interface<br/>Python main.py]
    end
    
    subgraph "Core Services Layer"
        D[Policy Engine<br/>Flask REST API<br/>Port 5000]
        E[Collector Service<br/>Metrics & Analytics<br/>Port 8000]
        F[FL Server<br/>Training Coordination<br/>Port 8080]
    end
    
    subgraph "Federated Learning Layer"
        G[FL Client 1<br/>192.168.100.101]
        H[FL Client 2<br/>192.168.100.102]
        I[FL Client N<br/>192.168.100.101-255]
        J[Model Aggregation]
        K[Privacy Mechanisms]
    end
    
    subgraph "Network Simulation Layer"
        L[GNS3 Integration<br/>Network Topology<br/>Port 3080]
        M[SDN Controller<br/>Ryu OpenFlow<br/>Port 6633/8181]
        N[OpenVSwitch<br/>Programmable Switches<br/>192.168.100.60-99]
        O[Network Monitoring]
    end
    
    subgraph "Data & Storage Layer"
        P[SQLite Metrics DB<br/>Time-series Data]
        Q[Policy Storage<br/>JSON + SQLite]
        R[Event Logs<br/>Structured Events]
        S[Configuration Store<br/>Hierarchical Config]
    end
    
    %% Data flows
    A --> B
    B --> D
    B --> E
    B --> F
    C --> D
    C --> E
    C --> F
    
    %% Control flows
    D --> F
    D --> G
    D --> H
    D --> I
    D --> M
    
    %% FL flows
    F --> G
    F --> H
    F --> I
    G --> J
    H --> J
    I --> J
    
    %% Network flows
    L --> M
    M --> N
    
    %% Storage flows
    E --> P
    D --> Q
    E --> R
    D --> S
    
    %% Monitoring flows
    G --> E
    H --> E
    I --> E
    M --> E
    N --> E
    
    style D fill:#d2a8ff,stroke:#8b5cf6,color:#000
    style A fill:#79c0ff,stroke:#1f6feb,color:#000
    style E fill:#7ce38b,stroke:#1a7f37,color:#000
    style F fill:#ffa7c4,stroke:#bf8700,color:#000
```

## Architectural Design Principles

### 1. Policy-Driven Architecture

The **Policy Engine** serves as the central nervous system of FLOPY-NET, ensuring that all components operate according to defined security, performance, and governance rules.

**Core Principles:**
- **Centralized Decision Making**: All system components query the Policy Engine before taking actions
- **Real-time Enforcement**: Policies are enforced in real-time across all system operations
- **Dynamic Updates**: Policy changes can be applied without system restart
- **Audit Trail**: Complete logging of policy decisions and enforcement actions
- **Event-Driven Compliance**: Continuous monitoring with event buffer system

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
        A[Policy Engine<br/>Flask REST<br/>Port 5000] <--> B[Collector<br/>FastAPI<br/>Port 8000]
        A <--> C[FL Server<br/>Custom HTTP<br/>Port 8080]
        A <--> D[SDN Controller<br/>OpenFlow<br/>Port 6633]
        B <--> C
        B <--> D
        C <--> E[FL Clients<br/>gRPC/HTTP<br/>Port range]
        D <--> F[OpenVSwitch<br/>OpenFlow<br/>Network]
    end
    
    style A fill:#d2a8ff,stroke:#8b5cf6,color:#000
    style B fill:#7ce38b,stroke:#1a7f37,color:#000
    style C fill:#ffa7c4,stroke:#bf8700,color:#000
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

- **Metrics**: Performance, health, and business metrics
- **Events**: System events and state changes
- **Controls**: REST APIs for configuration and control
- **Health Checks**: Liveness and readiness probes

### 4. Research-First Design

The platform is optimized for research workflows:

- **Reproducible Experiments**: Deterministic seeding and configuration
- **Extensible Frameworks**: Plugin architecture for custom algorithms
- **Data Export**: Comprehensive data export for analysis
- **Scenario Management**: Pre-defined and custom scenarios

## Component Interactions

### Startup Sequence

```mermaid
sequenceDiagram
    participant PE as Policy Engine
    participant C as Collector
    participant FL as FL Framework
    participant D as Dashboard
    participant GNS3 as GNS3 Integration
    
    Note over PE,GNS3: System Startup
    PE->>PE: Load policies
    PE->>C: Register collector
    PE->>FL: Register FL framework
    PE->>D: Register dashboard
    C->>GNS3: Initialize network monitoring
    FL->>PE: Request FL policies
    PE->>FL: Provide FL policies
    D->>C: Request system metrics
    C->>D: Provide metrics stream
    Note over PE,GNS3: System Ready
```

### Experiment Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant D as Dashboard
    participant PE as Policy Engine
    participant FL as FL Framework
    participant C as Collector
    participant GNS3 as GNS3
    
    U->>D: Start Experiment
    D->>PE: Validate experiment config
    PE->>D: Config approved
    D->>FL: Initialize FL experiment
    FL->>C: Register experiment metrics
    FL->>GNS3: Setup network topology
    GNS3->>FL: Network ready
    FL->>FL: Start training rounds
    loop Training Rounds
        FL->>C: Report round metrics
        C->>PE: Check policy compliance
        PE->>FL: Continue/Stop signal
    end
    FL->>D: Experiment complete
    D->>U: Show results
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

1. **Network Layer**: SDN-based network isolation and monitoring
2. **Application Layer**: Policy-based access control and validation
3. **Data Layer**: Encryption at rest and in transit
4. **Component Layer**: Service-to-service authentication

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

### Development Environment

```mermaid
graph TB
    subgraph "Developer Machine"
        A[Docker Compose]
        B[Local Services]
        C[Mock GNS3]
    end
    
    A --> B
    A --> C
```

### Production Environment

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        A[Ingress Controller]
        B[Dashboard Pods]
        C[Service Pods]
        D[FL Pods]
    end
    
    subgraph "External Services"
        E[GNS3 Server]
        F[Database Cluster]
        G[Object Storage]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    D --> G
```

## Technology Stack

### Core Technologies

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + TypeScript | Interactive dashboard |
| **Backend** | FastAPI + Python | REST API services |
| **Database** | PostgreSQL + InfluxDB | Metrics and metadata storage |
| **Message Queue** | Redis | Event streaming |
| **Container** | Docker + Compose | Service orchestration |
| **Network** | GNS3 + OpenFlow | Network simulation |

### ML/FL Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **FL Framework** | Custom + PyTorch | Federated learning implementation |
| **Model Training** | PyTorch | Deep learning models |
| **Data Handling** | Pandas + NumPy | Data preprocessing |
| **Visualization** | Plotly + D3.js | Interactive charts |

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

1. **Business Metrics**: FL accuracy, convergence, client participation
2. **Performance Metrics**: Latency, throughput, resource utilization
3. **Infrastructure Metrics**: CPU, memory, disk, network usage
4. **Security Metrics**: Policy violations, authentication failures

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
