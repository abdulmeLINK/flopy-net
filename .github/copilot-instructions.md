# FLOPY-NET AI Coding Agent Instructions

## Project Overview

FLOPY-NET is a federated learning research platform integrating **Flower FL framework** with **GNS3 network emulation**. It's a containerized microservices architecture (v1.0.0-alpha.8) designed to study how network conditions affect FL training.

**Critical Context**: This is a research platform with simulated FL training using random data. Real ML research requires extending FL components with actual models/datasets.

## Architecture: The Big Picture

### Microservices Communication Pattern
The system uses **static IP addressing** on subnet `192.168.100.0/24` for deterministic service discovery:

```
Dashboard (8085) ← aggregates data from →
├─ Policy Engine (192.168.100.20:5000) - Flask REST API
├─ Collector (192.168.100.40:8000) - SQLite metrics storage
├─ FL Server (192.168.100.10:8080) - Flower coordination
├─ SDN Controller (192.168.100.41:6633/8181) - Ryu OpenFlow
└─ GNS3 VM (user-configured IP:3080) - Network emulation host
```

**Why static IPs?** Network emulation requires predictable addressing for flow rules, policy enforcement, and cross-service communication. All components deployed in GNS3 use this subnet.

### Dual Deployment Model
1. **Host Services** (`docker-compose.yml`): Dashboard, APIs, monitoring
2. **GNS3 Services** (`src/scenarios/`): FL Server, FL Clients, SDN infrastructure deployed as Docker containers inside GNS3 VM

**Critical**: Configuration files use placeholder IPs (`192.168.141.x`). Users MUST find-replace with their GNS3 VM IP during setup.

## Configuration Philosophy

### Layered Configuration System
1. **Primary**: `docker-compose.yml` environment variables (controls all service behavior)
2. **Secondary**: JSON files in `config/` (scenario-specific overrides)
3. **Tertiary**: Hardcoded defaults in source code

**Anti-pattern to avoid**: Never hardcode IPs/ports. Always use environment variables or ConfigManager.

### Critical Configuration Files
- `config/gns3_connection.json` - GNS3 server connection (first file to update)
- `config/scenarios/basic_main.json` - FL experiment parameters
- `config/topology/basic_topology.json` - Network topology definition
- `config/policies/policies.json` - Active policy rules loaded by Policy Engine

**Loading Pattern**: Use `ConfigManager` singleton for all config access.

```python
from src.core.config.config_manager import config_manager

# Load config files (JSON/YAML supported)
config_manager.load_config("server_config")
config_manager.load_config("gns3_connection")

# Access with dot notation for nested values
server_port = config_manager.get("server.port", default=8080)
gns3_url = config_manager.get("gns3.server_url")

# Load from environment variables (FL_* prefix)
config_manager.load_environment_variables(prefix="FL_")

# Set values programmatically
config_manager.set("network.subnet_prefix", "192.168.100")
```

**Config file search order**: JSON → YAML → YML. Thread-safe with RLock for concurrent access.

## Developer Workflows

### Scenario Deployment (Primary Workflow)
```powershell
# 1. Deploy FL experiment to GNS3
python -m src.scenarios.basic.scenario --config config/scenarios/basic_main.json

# 2. Monitor via Dashboard
# Open http://localhost:8085

# 3. Check logs
docker-compose logs -f [fl-server|policy-engine|collector]
```

**What happens internally**:
1. `DeploymentManager` creates/opens GNS3 project via API
2. `TopologyCreator` builds network (switches, links) using `gns3fy` library
3. Containers deployed with static IPs from config
4. FL training starts, metrics flow to Collector
5. Dashboard polls Collector's SQLite DB for visualization

### GNS3 Cleanup Pattern
**Critical issue**: GNS3 has 255 VPCS node limit. Old projects accumulate and cause capacity errors.

```powershell
# Automatic cleanup (default in scenarios)
cleanup_before_create=True  # Set in GNS3Simulator init

# Manual cleanup for stuck projects
python scripts/cleanup_gns3.py --days 1 --dry-run
python scripts/cleanup_gns3.py --aggressive  # When desperate
```

**When to use**: Before any new scenario deployment if you've been testing multiple times.

### Building & Pushing Docker Images
```powershell
# Build all GNS3 component images
python scripts/build_gns3_images.py

# Push to Docker Hub (requires credentials)
python scripts/build_gns3_images.py --push

# Deploy to GNS3 VM (required after building)
python scripts/deploy_gns3_images.py
```

**Registry pattern**: Images tagged as `abdulmelink/flopynet-[component]:v1.0.0-alpha.8`. All components must match version.

## Project-Specific Patterns

### Flower FL Integration
**Pattern**: Flower framework (`flwr`) handles FL orchestration, PyTorch for models.

```python
# FL Server (src/fl/server/fl_server.py)
import flwr as fl
from flwr.server.strategy import FedAvg

# Custom strategy with policy integration
class PolicyAwareFedAvg(FedAvg):
    def configure_fit(self, server_round, parameters, client_manager):
        # Consult Policy Engine before client selection
        allowed_clients = policy_engine.get_allowed_clients()
        # ... filter clients
```

**Key files**:
- `src/fl/server/fl_server.py` - FL Server with SQLite persistence (2832 lines)
- `src/fl/client/fl_client.py` - FL Client with PyTorch training loop
- `src/fl/run_flower_federated_learning.py` - Entrypoint for both

### Policy Engine Pattern
**Design**: Centralized policy evaluation service that ALL components query before actions.

```python
# All services use this pattern:
response = requests.post(
    "http://192.168.100.20:5000/api/policies/evaluate",
    json={"action": "client_participate", "context": {...}}
)
if response.json()["allowed"]:
    # Proceed with action
```

**Policy files**: JSON in `config/policies/`, loaded at Policy Engine startup. Supports custom Python functions in `config/policy_functions/`.

### GNS3 API Integration
**Pattern**: Dual API usage - `GNS3API` (custom) + `gns3fy` library (community).

```python
from src.networking.gns3.gns3_api import GNS3API
from gns3fy import Gns3Connector, Project, Node, Link

# Always initialize both
api = GNS3API(server_url)  # For project mgmt
connector = Gns3Connector(url=server_url)  # For topology operations
```

**Why both?** `gns3fy` has better topology abstractions, custom `GNS3API` has additional functionality not in library.

### Scenario Discovery Pattern
**Auto-discovery**: Scenarios auto-register via directory structure.

```python
# src/scenarios/[scenario_name]/scenario.py must contain class ending in "Scenario"
class BasicScenario:  # Will be discovered as "basic"
    pass

# Framework loads via: src/scenarios/common.py:discover_scenarios()
SCENARIOS = discover_scenarios()  # Called at module import
```

**To add scenario**: Create `src/scenarios/my_scenario/scenario.py` with `MyScenario` class inheriting from base.

### Creating Custom Scenarios (Step-by-Step)

**1. Create Scenario Directory Structure**:
```powershell
mkdir src\scenarios\my_scenario
New-Item src\scenarios\my_scenario\scenario.py
New-Item src\scenarios\my_scenario\__init__.py
```

**2. Create Scenario Class** (`src/scenarios/my_scenario/scenario.py`):
```python
from src.scenarios.base_scenario import BaseScenario

class MyScenario(BaseScenario):
    def __init__(self, config_file=None):
        super().__init__(config_file)
        self.scenario_name = "my_scenario"
    
    def setup(self):
        """Setup scenario-specific configuration"""
        # Load custom config
        self.config = self.load_config()
        # Configure topology
        self.configure_topology()
        return True
    
    def run(self):
        """Execute the scenario"""
        # Deploy components to GNS3
        if not self.deploy_components():
            return False
        # Start FL training
        return self.start_training()
    
    def cleanup(self):
        """Cleanup scenario resources"""
        self.stop_training()
        self.cleanup_gns3_project()
```

**3. Create Configuration File** (`config/scenarios/my_scenario.json`):
```json
{
  "scenario_name": "my_scenario",
  "gns3": {
    "server_url": "http://192.168.100.1:3080",
    "project_name": "my_fl_experiment"
  },
  "fl_server": {
    "host": "192.168.100.10",
    "port": 8080,
    "rounds": 10
  },
  "fl_clients": [
    {"id": 1, "host": "192.168.100.101", "data_size": 1000},
    {"id": 2, "host": "192.168.100.102", "data_size": 1500}
  ],
  "network": {
    "latency_ms": 50,
    "packet_loss": 0.01,
    "bandwidth_mbps": 100
  }
}
```

**4. Create Topology Definition** (`config/topology/my_topology.json`):
```json
{
  "topology_name": "my_topology",
  "nodes": [
    {
      "type": "docker",
      "name": "fl-server",
      "image": "abdulmelink/flopynet-server:v1.0.0-alpha.8",
      "ip": "192.168.100.10"
    },
    {
      "type": "docker", 
      "name": "fl-client-1",
      "image": "abdulmelink/flopynet-client:v1.0.0-alpha.8",
      "ip": "192.168.100.101"
    },
    {
      "type": "openvswitch",
      "name": "switch-1",
      "ip": "192.168.100.60"
    }
  ],
  "links": [
    {"source": "fl-server", "target": "switch-1"},
    {"source": "fl-client-1", "target": "switch-1"}
  ]
}
```

**5. Run Your Scenario**:
```powershell
python -m src.scenarios.my_scenario.scenario --config config/scenarios/my_scenario.json
```

**Key Scenario Methods to Override**:
- `setup()` - Initialize scenario, load configs, validate requirements
- `run()` - Execute main scenario logic (deploy + train)
- `cleanup()` - Teardown resources, save results
- `configure_topology()` - Define network structure
- `deploy_components()` - Deploy Docker containers to GNS3
- `start_training()` - Initiate FL training rounds
- `collect_metrics()` - Gather performance data

**Scenario Discovery Requirements**:
1. Class name MUST end with "Scenario" (e.g., `MyScenario`, `CustomScenario`)
2. File MUST be named `scenario.py` in scenario directory
3. Directory name becomes scenario ID (e.g., `my_scenario` → accessible as "my_scenario")

**Testing Your Scenario**:
```powershell
# 1. Verify discovery
python -c "from src.scenarios.common import SCENARIOS; print(SCENARIOS)"

# 2. Dry-run (if supported)
python -m src.scenarios.my_scenario.scenario --config config/scenarios/my_scenario.json --dry-run

# 3. Full deployment
python -m src.scenarios.my_scenario.scenario --config config/scenarios/my_scenario.json
```

## Testing & Debugging

### Current State
⚠️ **Limited test coverage** - this is alpha software. No comprehensive test suite exists yet.

**Testing pattern** (ad-hoc):
```powershell
# Component tests
python -m src.fl.server.fl_server --config config/server_config.json
python scripts/check_gns3_connectivity.py

# Dashboard tests (if they exist)
cd dashboard/frontend && npm run test
cd dashboard/backend && pytest  # May not exist yet
```

### Common Issues & Debugging

**Issue**: Scenario deployment fails with "No available VPCS nodes"
- **Fix**: Run `python scripts/cleanup_gns3.py --aggressive`

**Issue**: Services can't communicate (connection refused)
- **Check**: Static IPs in `docker-compose.yml` match subnet
- **Verify**: `docker network inspect flopy-net_flopynet_network`

**Issue**: Dashboard shows no data
- **Debug**: Check Collector API directly: `http://localhost:8000/api/metrics/latest`
- **Verify**: Collector container logs: `docker-compose logs collector`

**Issue**: GNS3 API errors
- **First step**: Verify GNS3 VM IP with `ping <vm-ip>`
- **Check**: `config/gns3_connection.json` has correct IP
- **Verify**: GNS3 server running: `curl http://<vm-ip>:3080/v2/version`

## Code Style Conventions

### Python Standards
- **PEP 8** with 100-char line limit (relaxed)
- **Google-style docstrings** for all public functions/classes
- **4-space indentation**, no tabs
- **Import order**: stdlib → third-party → local (grouped)

### Logging Pattern
```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed diagnostics")
logger.info("High-level progress")
logger.warning("Recoverable issues")
logger.error("Errors requiring attention")
```

**All services log to**: stdout (Docker captures), plus file in `logs/` directory.

### Environment Variable Pattern
```python
# Always provide defaults
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("FL_SERVER_PORT", "8080"))
SUBNET_PREFIX = os.getenv("SUBNET_PREFIX", "192.168.100")
```

## Extension Points

### Adding Custom FL Models
1. Extend `src/fl/client/fl_client.py:FlowerClient`
2. Override `get_parameters()`, `set_parameters()`, `fit()`, `evaluate()`
3. Replace random data generation with real dataset loading

### Adding Custom Aggregation
1. Extend `flwr.server.strategy.FedAvg`
2. Override `aggregate_fit()` method
3. Register in `src/fl/server/fl_server.py`

### Adding Custom Policies

**Policy System Architecture**:
- Policy Engine runs as Flask service at `192.168.100.20:5000`
- All components query Policy Engine via REST API before actions
- Policies loaded from `config/policies/policies.json` at startup
- Custom policy functions in `config/policy_functions/`

**1. Create Policy Definition** (`config/policies/policies.json`):
```json
{
  "policies": [
    {
      "id": "custom_client_selection",
      "name": "Custom Client Selection Policy",
      "description": "Allow only high-bandwidth clients in training",
      "type": "federated_learning",
      "effect": "allow",
      "enabled": true,
      "conditions": [
        {
          "type": "attribute_match",
          "data": {
            "attribute": "client_bandwidth_mbps",
            "operator": ">=",
            "value": 50
          }
        },
        {
          "type": "custom_function",
          "data": {
            "function": "evaluate_client_trust"
          }
        }
      ],
      "actions": {
        "allow_participation": true,
        "log_event": true,
        "notify_dashboard": true
      }
    }
  ]
}
```

**2. Create Custom Policy Function** (`config/policy_functions/client_trust.py`):
```python
def evaluate_client_trust(context: dict) -> dict:
    """
    Custom policy evaluation function.
    
    Args:
        context: Policy evaluation context with client data
        
    Returns:
        dict: {"passed": bool, "reason": str}
    """
    client_id = context.get("client_id")
    trust_score = context.get("trust_score", 0.0)
    
    # Custom logic
    if trust_score > 0.7:
        return {
            "passed": True,
            "reason": f"Client {client_id} trust score acceptable: {trust_score}"
        }
    else:
        return {
            "passed": False,
            "reason": f"Client {client_id} trust score too low: {trust_score}"
        }
```

**3. Register Custom Function** (`config/policy_functions/__init__.py`):
```python
from .client_trust import evaluate_client_trust

# Policy Engine auto-discovers functions in this module
__all__ = ['evaluate_client_trust']
```

**4. Query Policy Engine from Your Component**:
```python
import requests

def check_client_participation(client_id: str, client_data: dict):
    """Check if client can participate in FL round"""
    response = requests.post(
        "http://192.168.100.20:5000/api/policies/evaluate",
        json={
            "policy_id": "custom_client_selection",
            "context": {
                "client_id": client_id,
                "client_bandwidth_mbps": client_data["bandwidth"],
                "trust_score": client_data["trust_score"]
            }
        },
        timeout=5
    )
    
    result = response.json()
    if result["allowed"]:
        logger.info(f"Client {client_id} allowed: {result['reason']}")
        return True
    else:
        logger.warning(f"Client {client_id} denied: {result['reason']}")
        return False
```

**Policy Types Supported**:
- `federated_learning` - FL client selection, model validation, training rules
- `network` - Traffic management, QoS, bandwidth allocation
- `security` - Access control, authentication, anomaly detection
- `system` - Resource limits, component health checks

**Policy Effects**:
- `allow` - Explicitly permit action (all conditions must pass)
- `deny` - Explicitly block action (any failing condition triggers denial)

**Condition Operators**:
- `attribute_match` - Compare context attributes (==, !=, <, >, <=, >=)
- `custom_function` - Execute Python function for complex logic
- `time_based` - Evaluate based on time/schedule
- `threshold` - Check numeric values against thresholds

**Policy Testing**:
```powershell
# Test policy evaluation via API
curl -X POST http://localhost:5000/api/policies/evaluate `
  -H "Content-Type: application/json" `
  -d '{"policy_id": "custom_client_selection", "context": {"client_id": "client-1", "client_bandwidth_mbps": 75, "trust_score": 0.85}}'

# Check Policy Engine logs
docker-compose logs policy-engine

# Reload policies without restart
curl -X POST http://localhost:5000/api/policies/reload
```

**Policy Best Practices**:
1. **Fail-safe defaults**: Use `"enabled": true` only after testing
2. **Logging**: Always enable `"log_event": true` for audit trails
3. **Performance**: Keep custom functions fast (<100ms) - Policy Engine is synchronous
4. **Error handling**: Custom functions should never raise exceptions (return `{"passed": false}`)
5. **Testing**: Test policies in isolation before production deployment

## Critical Knowledge

### Network Subnet Replacement
**Most common setup error**: Users forget to replace ALL occurrences of example IPs.

**Required replacements** (use VS Code find-replace `Ctrl+Shift+H`):
1. `192.168.141.128` → Your GNS3 VM IP (entire project)
2. `192.168.141` → Your subnet prefix (entire project)

**Affected files**: ~15+ files including docker-compose.yml, all configs, scenario files.

### Docker Registry
All images published to Docker Hub as `abdulmelink/flopynet-*`. 

**For development**: Build locally without push, then deploy to GNS3 VM's local Docker.

### Version Consistency
ALL components must use matching version tags. Mixing v1.0.0-alpha.7 and v1.0.0-alpha.8 causes incompatibilities.

**Check version**: `config/version.json` is source of truth.

## Priority Areas for Contributors

1. **Testing Infrastructure** - No comprehensive tests exist
2. **Policy Engine Hardening** - Known reliability issues (see CONTRIBUTING.md)
3. **Configuration Simplification** - Too many overlapping config files
4. **FL Framework Abstraction** - Generic base classes for any ML model/framework
5. **Documentation** - More code examples, better API docs

## Quick Reference

```powershell
# Essential Commands
python scripts/deploy_gns3_images.py          # Setup: Pull images
docker-compose up -d                           # Start host services
python -m src.scenarios.basic.scenario        # Deploy FL experiment
python scripts/cleanup_gns3.py --aggressive   # Cleanup when stuck

# Monitoring
http://localhost:8085                         # Dashboard
http://localhost:8001                         # Dashboard API
docker-compose logs -f [service-name]        # Service logs
```

## Key File Locations

- **Entry points**: `src/main.py`, `src/scenarios/basic/scenario.py`
- **FL implementation**: `src/fl/server/fl_server.py`, `src/fl/client/fl_client.py`
- **GNS3 integration**: `src/networking/gns3/topology_creator.py`, `src/networking/gns3/gns3_api.py`
- **Policy system**: `src/policy_engine/policies.py`, `config/policies/policies.json`
- **Deployment logic**: `src/scenarios/common/deployment_manager.py`
- **Dashboard backend**: `dashboard/backend/app/`, Dashboard frontend: `dashboard/frontend/src/`

---

**Remember**: This is a research platform (alpha). Expect incomplete features, limited error handling, and evolving architecture. Always test in isolated environments.
