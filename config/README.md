# FLOPY-NET Configuration

This directory contains all configuration files for the FLOPY-NET system components.

## Configuration Hierarchy

FLOPY-NET uses a layered configuration approach with the following precedence (highest to lowest):

1. **Command-Line Arguments** (highest priority)
2. **Environment Variables** (Docker containers, docker-compose.yml)
3. **JSON Configuration Files** (this directory)
4. **Hardcoded Defaults** (in source code)

## Core Configuration Files

### Federated Learning
- **`server_config.json`**: FL Server configuration (FLServer)
- **`client_config.json`**: FL Client base configuration (FLClient)
- **`fl_client/`**: Individual client configurations (client_1, client_2, etc.)
- **`fl_server/`**: Server-specific configurations

### System Services
- **`collector_config.json`**: Collector service configuration
- **`policy_engine/policy_config.json`**: Policy Engine master configuration
- **`policies/policies.json`**: Active policy rules and definitions

### Network and Simulation
- **`gns3/gns3_connection.json`**: GNS3 server connection settings
- **`gns3/templates/`**: GNS3 node template definitions
- **`topology/`**: Network topology configurations
- **`scenarios/`**: Experimental scenario definitions

## Directory Structure

```
config/
├── server_config.json          # FL Server main config
├── client_config.json          # FL Client base config
├── collector_config.json       # Collector service config
├── gns3_connection.json        # GNS3 server connection
├── version.json                # System version info
├── collector/                  # Collector-specific configs
├── fl_client/                  # Individual client configs
│   ├── client_1_config.json
│   └── client_2_config.json
├── fl_server/                  # Server-specific configs
├── gns3/                      # GNS3 and network configs
│   └── templates/             # Node template definitions
├── policies/                  # Policy definitions
│   ├── policies.json         # Active policies
│   ├── default_policies.json # Default policy set
│   └── README.md
├── policy_engine/             # Policy Engine configs
├── policy_functions/          # Custom policy functions
├── scenarios/                 # Scenario configurations
└── topology/                  # Network topology files
```

## Configuration Loading

### ConfigManager Usage

Always use the `ConfigManager` for loading configurations:

```python
from src.core.config import ConfigManager

# Get the global config manager instance
config_manager = ConfigManager()

# Load different types of configurations
server_config = config_manager.load_server_config()
client_config = config_manager.load_client_config()
scenario_config = config_manager.load_scenario_config("basic")
```

### Service-Specific Loading

Individual services have their own configuration loading:

- **FL Server**: Uses `src/core/config.get_fl_server_config()`
- **FL Client**: Uses `src/core/config.get_fl_client_config()`
- **Policy Engine**: Loads from `POLICY_CONFIG` environment variable

## Configuration Types

### JSON Configuration Files
All configuration files use JSON format with proper indentation for readability.

### Environment Variable Overrides
Common environment variables used in Docker deployments:

```env
# Service URLs
GNS3_URL=http://localhost:3080
POLICY_ENGINE_URL=http://localhost:5000
COLLECTOR_URL=http://localhost:8002
FL_SERVER_URL=http://localhost:8080

# Configuration file paths
POLICY_CONFIG=config/policy_engine/policy_config.json
SERVER_CONFIG=config/server_config.json
CLIENT_CONFIG=config/client_config.json
```

## Policy Configuration

### Active Policies
- **`policies/policies.json`**: Main active policy file used by Policy Engine
- **`policies/default_policies.json`**: Default policy backup/reference
- **`policy_engine/policy_config.json`**: Points to active policy file

### Policy Functions
- **`policy_functions/`**: Custom policy function definitions
- **`policy_functions/model_size_policy.json`**: Example policy function

## Scenario and Topology Configuration

### Scenarios
- **`scenarios/basic_main.json`**: Complete basic scenario configuration
- Custom scenarios can be added following the same pattern

### Network Topologies
- **`topology/basic_topology.json`**: Basic network topology definition
- Used by GNS3 simulator for network creation

## GNS3 Configuration

### Connection Settings
- **`gns3/gns3_connection.json`**: GNS3 server URL and connection details

### Node Templates
- **`gns3/templates/`**: JSON template definitions for GNS3 nodes
- Supports Docker containers with custom images
- See `gns3/templates/README.md` for IP address configuration

## Development and Testing

### Adding New Configurations

1. **Create JSON file** in appropriate subdirectory
2. **Update ConfigManager** if new configuration type
3. **Add environment variable overrides** if needed
4. **Document configuration options** in relevant README

### Configuration Validation

- Validate JSON syntax before deployment
- Test environment variable overrides
- Verify configuration precedence works as expected
- Check for required vs optional configuration parameters

## Deprecated Configurations

The following configurations have been consolidated or removed:

- `src/config/server_config.json` → `config/server_config.json`
- `config/local_server_config.json` → Removed (unused)
- `.conf` files → Removed (obsolete)
- `config/networking/sdn_controller_config.ini` → Hardcoded defaults

## Configuration Best Practices

### File Organization
- Group related configurations in subdirectories
- Use descriptive file names
- Maintain consistent JSON formatting

### Environment Variables
- Use clear, descriptive variable names
- Document all environment variables used
- Provide sensible defaults in configuration files

### Security
- Never commit sensitive information (passwords, keys)
- Use environment variables for sensitive data
- Implement proper access controls for configuration files

### Documentation
- Document all configuration options
- Provide examples for complex configurations
- Keep README files updated with changes

For component-specific configuration details, refer to individual service documentation.