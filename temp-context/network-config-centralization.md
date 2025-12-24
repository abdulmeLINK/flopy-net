# Network Configuration Centralization - Implementation Summary

## Overview

This document describes the centralized network configuration system implemented for FLOPY-NET to solve GitHub Issues #22, #23, #24.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE SOURCE OF TRUTH                        │
│              config/network_addressing.json                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  simulator  │  │   network    │  │      services         │  │
│  │  (GNS3 IP)  │  │  (subnet)    │  │  (ports, ip_suffix)   │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │   scripts/sync_network_config.py  │
              │         (Generator Script)         │
              └───────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   ┌──────────┐      ┌───────────────┐    ┌──────────────────┐
   │  .env    │      │ gns3_connection│   │ topology/*.json  │
   │  file    │      │    .json       │   │ scenario/*.json  │
   └──────────┘      └───────────────┘    └──────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   docker-compose      Python scripts        GNS3 Nodes
```

## Files Changed/Created

### 1. `config/network_addressing.json` (Updated)
**Purpose**: Single source of truth for ALL network configuration

**Key Changes**:
- Added `simulator` section (replaces old `gns3` section)
- Services now use `ip_suffix` instead of full IP (allows subnet changes)
- Added `northbound` section for SDN external interfaces
- Added `ip_ranges` for network policies

**Structure**:
```json
{
  "simulator": {
    "host": "192.168.141.128",  // ← CHANGE THIS FOR YOUR GNS3 VM
    "api_port": 3080,
    "ssh": { ... }
  },
  "network": {
    "subnet_prefix": "192.168.100",  // Services subnet
    "ip_ranges": { ... }
  },
  "services": {
    "fl_server": { "ip_suffix": 10, "port": 8080 },
    // Full IP = subnet_prefix + ip_suffix = 192.168.100.10
  }
}
```

### 2. `src/core/config/network_addressing.py` (Rewritten)
**Purpose**: Python API for accessing network configuration

**Features**:
- Singleton pattern for app-wide consistency
- Computes full IPs from `subnet_prefix` + `ip_suffix`
- Environment variable overrides (`GNS3_VM_IP`, `SUBNET_PREFIX`)
- Backwards compatible with old `NetworkAddressing` name
- Convenience functions: `get_gns3_url()`, `get_policy_engine_url()`, etc.

**Usage**:
```python
from src.core.config.network_addressing import network_config

# Get service URLs
policy_url = network_config.get_service_url('policy_engine')
gns3_url = network_config.get_simulator_url()

# Get client IP
client_ip = network_config.get_client_ip(1)  # 192.168.100.101
```

### 3. `scripts/sync_network_config.py` (Rewritten)
**Purpose**: Generate configuration files from central config

**Features**:
- `--gns3-ip` flag to change GNS3 VM IP everywhere
- `--subnet` flag to change entire subnet
- `--dry-run` to preview changes
- Updates: `.env`, `gns3_connection.json`, topology files, scenario files

**Usage**:
```bash
# Preview what would change
python scripts/sync_network_config.py --dry-run

# Apply all changes
python scripts/sync_network_config.py

# Change GNS3 VM IP (updates everywhere)
python scripts/sync_network_config.py --gns3-ip 192.168.50.100

# Change entire subnet
python scripts/sync_network_config.py --subnet 10.0.0
```

### 4. `config/gns3_connection.json` (Updated)
- Now generated from `network_addressing.json`
- Fixed port (was 80, should be 3080)

## How to Use

### For Users Setting Up the Project

1. **Edit the central config** - Only ONE file to change:
   ```bash
   # Edit config/network_addressing.json
   # Change simulator.host to your GNS3 VM IP
   ```

2. **Run the sync script**:
   ```bash
   python scripts/sync_network_config.py
   ```

3. **Done!** All configuration files are updated.

### Quick Command (One-Liner)

```bash
python scripts/sync_network_config.py --gns3-ip YOUR_GNS3_VM_IP
```

### For Developers

**To get a service URL in Python**:
```python
from src.core.config.network_addressing import network_config

# In FL Server
policy_engine_url = network_config.get_service_url('policy_engine')

# In scripts
gns3_url = network_config.get_simulator_url()
ssh_config = network_config.get_simulator_ssh_config()
```

**To add a new service**:
1. Add to `config/network_addressing.json` under `services`
2. Add getter method to `network_addressing.py` if needed
3. Update `sync_network_config.py` to propagate to files

## Environment Variable Overrides

The Python module supports runtime overrides:

| Variable | Purpose |
|----------|---------|
| `GNS3_VM_IP` | Override simulator host |
| `GNS3_HOST` | Alternative for `GNS3_VM_IP` |
| `SUBNET_PREFIX` | Override subnet (e.g., `10.0.0`) |
| `NETWORK_CONFIG_PATH` | Custom config file path |

## Migration Notes

### Before (Hardcoded IPs everywhere)
```python
policy_url = "http://192.168.100.20:5000"  # BAD
```

### After (Use centralized config)
```python
from src.core.config.network_addressing import network_config
policy_url = network_config.get_service_url('policy_engine')  # GOOD
```

## Files Still Needing Migration

The following files still have hardcoded IPs that should be migrated to use the central config:

1. `src/utils/gns3_config.py` - Has fallback default IP
2. `src/scenarios/common/gns3_utils.py` - Has fallback default IP
3. `src/networking/gns3/component_executor.py` - Has hardcoded IP in command
4. Various scripts in `scripts/` - Have default IPs in help text

These are lower priority as they use the IP as fallback defaults.
