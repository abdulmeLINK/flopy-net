# FLOPY-NET Future Roadmap

This document outlines the planned future work and potential improvements for the FLOPY-NET platform.

---

## Prioritized Next Steps (Immediate Focus)

Based on the latest review, the following high-impact features should be prioritized to deliver the most value to the platform's core mission.

1.  **Implement Real Training FL Client:** The highest priority is to replace simulated clients with a client capable of performing genuine PyTorch training on real datasets (e.g., CIFAR-10). This is a prerequisite for all scientifically valid research on model performance and convergence.

2.  **Evolve to Declarative Scenarios (JSON):** Architecturally, the most important next step is to migrate from Python-class-based scenario definitions to a single, declarative JSON or YAML file per experiment. A generic "Scenario Runner" will interpret this file, which will define the network topology, FL parameters, policies, and a timeline of chaos events. This will dramatically improve reproducibility and accessibility.

3.  **Implement Dual-Path Network Control:** Solidify the two primary methods for creating network challenges. The system should support both **Direct GNS3 Manipulation** (for simulating raw network failures like a cut cable) and **Policy-Driven SDN Control** (for simulating intelligent governance actions like quarantining a node).

4.  **Enhance Observability with Host Discovery:** The `fl-client` should report its host characteristics (OS, hardware, e.g., Raspberry Pi vs. x86) to the `Collector`. This adds crucial context to performance metrics.

5.  **Introduce Interactive Topology Control:** The dashboard should evolve from a passive observatory to an interactive control panel, allowing users to modify the GNS3 topology live.

---

## Thematic Roadmap Details

The following sections provide a detailed breakdown of all planned features, incorporating the priorities listed above.

### 1. Deepen Research Capabilities & Network Control

This theme focuses on enhancing the core strength of FLOPY-NET: its integrated network observatory.

#### 1.1. Dynamic Network Chaos Engine
- **Current State:** The `GNS3Manager` is primarily used for setting up and tearing down topologies.
- **Next Step:** Extend `gns3_manager.py` with methods to manipulate a *running* network.
  - **Action:** Implement `update_link_properties(link_id, latency, packet_loss, jitter)`.
  - **Action:** Implement `stop_link(link_id)` and `start_link(link_id)` to simulate network partitions.

#### 1.2. Policy-Driven SDN Control
- **Current State:** The SDN controller (Ryu) is used for basic topology discovery.
- **Next Step:** Leverage the *programmable* nature of the SDN controller for governance.
  - **Action:** Develop a `PolicyEngine` function that can push dynamic flow rules to the Ryu controller via its API. This enables policies that can, for example, automatically quarantine a misbehaving client by instructing Ryu to drop its traffic.

#### 1.3. Advanced Scenario Library
- **Current State:** The system supports a `BasicScenario` which can be extended.
- **Next Step:** Create a rich, pre-built library of challenging scenarios in a new `src/scenarios/library/` directory.
  - **Scenario Idea (Network Attack):** A "Man-in-the-Middle" scenario where a malicious node alters FL traffic.
  - **Scenario Idea (Client Behavior):** A "Byzantine Client" scenario where specific clients are instructed to send garbage data or delayed updates.
  - **Scenario Idea (Network Failure):** A "Cascading Failure" scenario where stopping one link triggers a script to systematically degrade other parts of the network.

### 2. Enhance Architecture & Data Flow

This theme focuses on modernizing the backend architecture for better performance, scalability, and maintainability.

#### 2.1. Migrate to Declarative, JSON-based Scenarios
- **Current State:** Scenarios are defined by inheriting from a `BaseScenario` Python class.
- **Next Step:** This is a top architectural priority. Refactor the system to be driven by a single, declarative experiment file (JSON/YAML).
  - **Action:** Create a generic "Scenario Runner" engine in Python.
  - **Action:** This engine will parse the experiment file which defines:
    - The full network topology.
    - The FL model, dataset, and hyperparameters.
    - A timeline of events (e.g., "at T+60s, introduce 30% packet loss on link X for 120s").
    - The policies to be enforced.
  - **Benefit:** This makes experiments fully reproducible from a single file and accessible to non-programmers.

#### 2.2. Transition from Polling to Event-Driven Architecture
- **Current State:** The `Collector` uses `APScheduler` to poll other services for data.
- **Next Step:** Integrate a lightweight message bus (e.g., RabbitMQ, Redis Pub/Sub) to create a real-time, push-based system.
  - **Action:** Refactor the `Collector` to be a subscriber that listens for events.
  - **Action:** Refactor components like the `PolicyEngine` and `fl-server` to become publishers that push events to the message bus as they happen.

#### 2.3. Improve Data Persistence
- **Current State:** The `Collector` uses SQLite, which is good but has limitations for high-frequency time-series data.
- **Next Step:** Abstract the storage layer and add support for a proper time-series database.
  - **Action:** Refactor `collector/storage.py` to use a base `Storage` class (interface).
  - **Action:** Create implementations for `SQLiteStorage` (current) and `InfluxDBStorage` or `PrometheusStorage` for more scalable and query-friendly metrics storage.

### 3. Bridge to Real-World Security & Deployment

This theme focuses on adding features necessary for a secure, production-ready system.

#### 3.1. Implement Authentic FL Training
- **Current State:** Clients may be using simulated or dummy data.
- **Next Step:** This is the **top priority** for scientific validity.
  - **Action:** Develop a new version of the `flopynet_fl_client` container that includes common datasets (e.g., CIFAR-10) and performs a genuine PyTorch training loop.
  - **Action:** Ensure this client can be configured to leverage a GPU if it's passed through to the container by the GNS3 node.

#### 3.2. Implement Application-Layer Security Defenses
- **Current State:** Security is focused on network-level policies.
- **Next Step:** Add defenses against FL-specific attacks that bypass network security.
  - **Action (Privacy):** Integrate a Differential Privacy library (e.g., PyTorch Opacus) into the `fl-client`.
  - **Action (Robustness):** Implement robust aggregation algorithms on the `fl-server` (e.g., Krum, Trimmed Mean).

#### 3.3. Hardware-Level Security via Remote Attestation
- **Current State:** Clients are trusted based on their network identity.
- **Next Step:** Implement a mechanism to verify the integrity of the software running on the edge.
  - **Action:** Design an experimental `fl-client` capable of running within a Trusted Execution Environment (TEE).
  - **Action:** Extend the `PolicyEngine` with a new `check_attestation(quote)` endpoint.

### 4. Improve User Experience & Usability

This theme focuses on making the platform easier for other researchers and users to adopt and operate.

#### 4.1. Interactive Dashboard for Network & Topology Control
- **Current State:** The dashboard is for observation only.
- **Next Step:** Add controls to the dashboard to make it an interactive control panel for the live simulation.
  - **Action:** Create API endpoints on the `dashboard-backend` that can proxy commands to the `GNS3Manager`.
  - **Action:** Add UI elements to the frontend to allow users to add/remove nodes, stop/start links, and change link properties, and see the results reflected immediately.

#### 4.2. Host & Device Observability
- **Current State:** All clients are treated as generic nodes.
- **Next Step:** Provide context on the environment where each client is running.
  - **Action:** Modify the `fl-client` entrypoint script or application to collect system information (e.g., OS, CPU architecture, memory) using libraries like `platform` or `psutil`.
  - **Action:** Report this static information to the `Collector` upon startup.
  - **Action:** Display the host information in the dashboard's client list.

#### 4.3. Enhanced CLI Tool & Documentation
- **Current State:** The `main.py` script is a basic service launcher.
- **Next Step:** Improve developer and user experience.
  - **Action:** Use a library like `Click` or `Typer` to build a richer CLI with commands like `flopynet scenario run <name>`, `flopynet system status`, `flopynet policy list`.
  - **Action:** Build a dedicated documentation website using `MkDocs` (already a dependency). 