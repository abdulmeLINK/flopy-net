---
sidebar_position: 1
---

# Configuration Guide

FLOPY-NET employs a hierarchical configuration system designed to support both development and research environments while maintaining consistency across Docker Compose and GNS3 deployment scenarios. This guide covers configuration management for the v1.0.0-alpha.8 implementation, including simulation parameters, network settings, and component coordination.

## Current Implementation Configuration Context

**Important Note**: The current FLOPY-NET v1.0.0-alpha.8 configuration is optimized for system architecture research and network simulation studies. The federated learning components use simulated training with synthetic data generation rather than actual machine learning training, allowing researchers to focus on network behavior, policy enforcement, and system scalability analysis.

Configuration parameters primarily control simulation behavior, network topology settings, policy enforcement rules, and monitoring data collection rather than actual machine learning hyperparameters. For production federated learning deployments, custom configurations would need to be developed that extend these base settings with real training parameters, dataset specifications, and model architecture definitions.

## Configuration Architecture

FLOPY-NET follows a multi-layered configuration approach that adapts to different deployment environments while maintaining consistent behavior across development and research scenarios. The configuration hierarchy ensures that system behavior can be precisely controlled while providing sensible defaults for rapid deployment and experimentation.

**Configuration Precedence (highest to lowest priority):**

1. **Runtime Command Arguments** - Direct CLI parameters when launching scenarios or services
2. **Docker Environment Variables** - Container-specific settings in docker-compose.yml or GNS3 templates  
3. **JSON Configuration Files** - Structured configuration stored in the config/ directory hierarchy
4. **System Defaults** - Built-in defaults defined in source code for reliable fallback behavior

This layered approach enables flexible deployment across different environments while ensuring reproducible experimental conditions and consistent system behavior.

## Container Configuration

### Docker Compose Environment Variables

The primary configuration method for FLOPY-NET v1.0.0-alpha.8 is through Docker Compose environment variables:

#### Network Configuration (All Services)
```yaml
- USE_STATIC_IP=true
- SUBNET_PREFIX=192.168.100
- CLIENT_IP_RANGE=100-255          # FL Clients: 192.168.100.101-255
- SERVER_IP_RANGE=10-19            # FL Server: 192.168.100.10-19
- POLICY_IP_RANGE=20-29            # Policy Engine: 192.168.100.20-29
- CONTROLLER_IP_RANGE=30-49        # SDN Controller: 192.168.100.30-49
- OVS_IP_RANGE=60-99              # OpenVSwitch: 192.168.100.60-99
- NORTHBOUND_IP_RANGE=50-59        # Dashboard/APIs: 192.168.100.50-59
- COLLECTOR_IP=40                  # Collector Service: 192.168.100.40
```

#### Service-Specific Static IP Assignments
```yaml
- NODE_IP_FL_SERVER=192.168.100.10
- NODE_IP_POLICY_ENGINE=192.168.100.20
- NODE_IP_SDN_CONTROLLER=192.168.100.41
- NODE_IP_COLLECTOR=192.168.100.40
- NODE_IP_OPENVSWITCH=192.168.100.60
- NODE_IP_FL_CLIENT_1=192.168.100.101
- NODE_IP_FL_CLIENT_2=192.168.100.102
```

### Container Service Configuration

#### Policy Engine (Port 5000, IP 192.168.100.20)
```yaml
environment:
  - SERVICE_TYPE=policy-engine
  - POLICY_PORT=5000
  - LOG_LEVEL=INFO
  - POLICY_CONFIG=/app/config/policies/policy_config.json
  - POLICY_FUNCTIONS_DIR=/app/config/policy_functions
```

#### FL Server (Port 8080, IP 192.168.100.10)  
```yaml
environment:
  - SERVICE_TYPE=fl-server
  - FL_SERVER_PORT=8080
  - METRICS_PORT=8081
  - MIN_CLIENTS=1
  - MIN_AVAILABLE_CLIENTS=1
  - POLICY_ENGINE_HOST=policy-engine
  - POLICY_ENGINE_PORT=5000
```

#### FL Clients (IPs 192.168.100.101-102)
```yaml
environment:
  - SERVICE_TYPE=fl-client
  - CLIENT_ID=client-1                    # Unique client identifier
  - SERVER_HOST=fl-server                 # FL Server hostname
  - POLICY_ENGINE_HOST=policy-engine      # Policy Engine hostname
  - MAX_RECONNECT_ATTEMPTS=-1             # Infinite reconnection attempts
  - RETRY_INTERVAL=5                      # Retry interval in seconds
```

#### Collector Service (Port 8083, IP 192.168.100.40)
```yaml
environment:
  - SERVICE_TYPE=collector
  - NETWORK_MONITOR_ENABLED=true
  - FL_SERVER_HOST=fl-server
  - FL_SERVER_PORT=8081
  - POLICY_ENGINE_URL=http://policy-engine:5000
  - SDN_CONTROLLER_URL=http://sdn-controller:8181
  - POLICY_INTERVAL_SEC=5                 # Policy check interval
  - FL_INTERVAL_SEC=5                     # FL metrics collection interval
  - NETWORK_INTERVAL_SEC=5                # Network monitoring interval
```

**Note**: The Collector API provides custom endpoint documentation at `http://localhost:8083/api` (not automatic OpenAPI docs).

#### SDN Controller (Ports 6633/8181, IP 192.168.100.41)
```yaml
environment:
  - SERVICE_TYPE=sdn-controller
  - CONTROLLER_HOST=0.0.0.0
  - CONTROLLER_PORT=6633                  # OpenFlow protocol port
  - REST_PORT=8181                        # Ryu REST API port
  - POLICY_ENGINE_HOST=policy-engine
```

#### OpenVSwitch (IP 192.168.100.60)
```yaml
environment:
  - SERVICE_TYPE=openvswitch
  - OVS_NUM_PORTS=16                      # Number of switch ports
  - OVS_BRIDGE_NAME=br0                   # Bridge name
  - SDN_CONTROLLER_HOST=sdn-controller
  - SDN_CONTROLLER_PORT=6633
  - OVS_PROTOCOL=OpenFlow13               # OpenFlow version
  - OVS_FAIL_MODE=standalone             # Failover mode
```

## Core Configuration Files

### System Version (`version.json`)

Defines the system version and component information:

```json
{
    "system_version": "v1.0.0-alpha.8",
    "build_date": "2025-06-10",
    "components": {
        "policy-engine": {
            "version": "v1.0.0-alpha.8",
            "image": "abdulmelink/flopynet-policy-engine",
            "status": "alpha"
        },
        "fl-server": {
            "version": "v1.0.0-alpha.8",
            "image": "abdulmelink/flopynet-server",
            "status": "alpha"
        }
    },
    "registry": {
        "name": "abdulmelink",
        "url": "https://hub.docker.com/u/abdulmelink"
    }
}
```

### Policy Engine Configuration (`policy_engine/policy_config.json`)

Configures the Policy Engine service:

```json
{
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false,
    "storage": {
        "type": "sqlite",
        "database_path": "policies.db"
    },
    "policy_functions_dir": "/app/config/policy_functions",
    "default_policies": "/app/config/policies/default_policies.json"
}
```

### Collector Configuration (`collector_config.json`)

Configures the Collector service:

```json
{
    "host": "0.0.0.0",
    "port": 8000,
    "collection_interval": 5,
    "storage": {
        "type": "sqlite",
        "database_path": "metrics.db"
    },
    "monitors": {
        "fl_monitor": {
            "enabled": true,
            "interval": 5
        },
        "network_monitor": {
            "enabled": true,
            "interval": 10
        },
        "policy_monitor": {
            "enabled": true,
            "interval": 3
        }
    }
}
```

### FL Server Configuration (`server_config.json`)

Configures the FL Server:

```json
{
    "host": "0.0.0.0",
    "port": 8080,
    "api_port": 8081,
    "min_clients": 1,
    "min_available_clients": 1,
    "policy_engine_url": "http://policy-engine:5000",
    "model": {
        "type": "pytorch",
        "architecture": "simple_cnn",
        "dataset": "mnist"
    },
    "training": {
        "num_rounds": 10,
        "local_epochs": 1,
        "batch_size": 32,
        "learning_rate": 0.01
    }
}
```

### FL Client Configuration (`client_config.json`)

Base configuration for FL clients:

```json
{
    "server_host": "fl-server",
    "server_port": 8080,
    "policy_engine_url": "http://policy-engine:5000",
    "client_id": "client-default",
    "data_partition": "iid",
    "local_epochs": 1,
    "batch_size": 32,
    "learning_rate": 0.01
}
```

### GNS3 Connection (`gns3_connection.json`)

Configures GNS3 server connection:

```json
{
    "host": "localhost",
    "port": 3080,
    "user": "admin",
    "password": "admin",
    "verify_ssl": false,
    "timeout": 30
}
```

## Network Configuration

### Static IP Allocation

FLOPY-NET uses a static IP configuration on the `192.168.100.0/24` network:

| Component | IP Range | Example IPs | Purpose |
|-----------|----------|-------------|---------|
| Policy Engine | 192.168.100.20-29 | 192.168.100.20 | Core policy service |
| FL Server | 192.168.100.10-19 | 192.168.100.10 | FL coordination |
| FL Clients | 192.168.100.100-255 | 192.168.100.101, 102 | Distributed training |
| Collector | 192.168.100.40 | 192.168.100.40 | Metrics collection |
| SDN Controller | 192.168.100.30-49 | 192.168.100.41 | Network control |
| OpenVSwitch | 192.168.100.60-99 | 192.168.100.60 | Network switching |
| Northbound APIs | 192.168.100.50-59 | 192.168.100.50 | API interfaces |

### Docker Compose Environment Variables

Key environment variables used in `docker-compose.yml`:

```yaml
environment:
  - SERVICE_TYPE=policy-engine
  - SERVICE_VERSION=v1.0.0-alpha.8
  - BUILD_DATE=2025-06-10
  - HOST=0.0.0.0
  - POLICY_PORT=5000
  - LOG_LEVEL=INFO
  - NETWORK_MODE=docker
  - USE_STATIC_IP=true
  - SUBNET_PREFIX=192.168.100
  - NODE_IP_FL_SERVER=192.168.100.10
  - NODE_IP_POLICY_ENGINE=192.168.100.20
  - NODE_IP_COLLECTOR=192.168.100.40
  - NODE_IP_SDN_CONTROLLER=192.168.100.41
```

## Policy Configuration

### Active Policies (`policies/policies.json`)

Defines the active policy rules:

```json
{
    "policies": [
        {
            "policy_id": "client_validation",
            "name": "Client Validation Policy",
            "description": "Validate FL client parameters",
            "conditions": [
                {
                    "field": "client_id",
                    "operator": "exists",
                    "value": true
                }
            ],
            "actions": [
                {
                    "type": "allow",
                    "target": "fl_participation"
                }
            ],
            "priority": 10,
            "enabled": true
        }
    ]
}
```

### Custom Policy Functions (`policy_functions/`)

Custom policy functions can be defined in this directory:

```json
{
    "function_name": "model_size_policy",
    "description": "Validate model size constraints",
    "parameters": {
        "max_size_mb": 100,
        "min_size_mb": 1
    },
    "implementation": "python"
}
```

## Scenario Configuration

### Basic Scenario (`scenarios/basic_main.json`)

Defines a basic FL scenario:

```json
{
    "name": "Basic FL Scenario",
    "description": "Basic federated learning scenario with 2 clients",
    "duration_minutes": 30,
    "fl_config": {
        "num_clients": 2,
        "num_rounds": 10,
        "model_type": "pytorch",
        "dataset": "mnist"
    },
    "network_config": {
        "topology": "basic",
        "packet_loss": 0.0,
        "latency_ms": 10,
        "bandwidth_mbps": 100
    }
}
```

## Best Practices

### 1. Configuration Management

- **Version Control**: Keep configuration files in version control
- **Environment Separation**: Use different configs for dev/test/prod
- **Validation**: Validate configuration files before deployment
- **Documentation**: Document all configuration options

### 2. Security Considerations

- **Sensitive Data**: Use environment variables for secrets
- **Access Control**: Restrict access to configuration files
- **Encryption**: Encrypt sensitive configuration data
- **Auditing**: Log configuration changes

### 3. Debugging Configuration

```powershell
# Verify configuration loading
python src\main.py --help

# Check configuration file syntax
python -m json.tool config\version.json

# Test Docker environment variables
docker-compose config

# Validate specific service configuration
docker-compose logs policy-engine | Select-String "config"
```

### 4. Common Issues

- **Port Conflicts**: Ensure ports are available and not conflicting
- **IP Address Conflicts**: Verify static IP ranges don't overlap
- **File Permissions**: Ensure configuration files are readable
- **JSON Syntax**: Validate JSON files for syntax errors
- **Environment Variables**: Check that required env vars are set

## Related Documentation

- [Policy Management](./policy-management.md) - Detailed policy configuration
- [GNS3 Integration](./gns3-integration.md) - Network simulation setup
- [Troubleshooting](./troubleshooting.md) - Common configuration issues
