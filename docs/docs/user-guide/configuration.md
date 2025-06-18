---
sidebar_position: 1
---

# Configuration Guide

FLOPY-NET uses a hierarchical configuration system that allows for flexible customization of all system components. This guide covers the configuration structure, files, and best practices.

## Configuration Hierarchy

FLOPY-NET follows a layered configuration approach with the following precedence (highest to lowest):

1. **Command-Line Arguments** (highest priority)
2. **Environment Variables** (Docker containers, docker-compose.yml)
3. **JSON Configuration Files** (config/ directory)
4. **Hardcoded Defaults** (in source code)

## Configuration Structure

The configuration system is organized in the `config/` directory:

```
config/
├── version.json                 # System version and component information
├── client_config.json           # FL Client base configuration
├── server_config.json           # FL Server main configuration
├── collector_config.json        # Collector service configuration
├── gns3_connection.json         # GNS3 server connection settings
├── collector/                   # Collector-specific configurations
│   └── collector_config.json
├── fl_client/                   # Individual client configurations
│   ├── client_1_config.json
│   └── client_2_config.json
├── fl_server/                   # Server-specific configurations
│   └── server_config.json
├── gns3/                        # GNS3 and network configurations
│   └── templates/               # Node template definitions
├── policies/                    # Policy definitions and management
│   ├── policies.json            # Active policy rules
│   ├── default_policies.json    # Default policy set
│   └── README.md               # Policy documentation
├── policy_engine/               # Policy Engine configuration
│   └── policy_config.json
├── policy_functions/            # Custom policy functions
│   ├── __init__.py
│   └── model_size_policy.json
├── scenarios/                   # Scenario configurations
│   └── basic_main.json
└── topology/                    # Network topology definitions
    └── basic_topology.json
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
