# GNS3 Templates for Network Components

This directory contains template definitions for GNS3 network components used in the federated learning system.

## IP Address Configuration

The system uses a flexible approach to IP address configuration through environment variables following this pattern:

```
NODE_IP_COMPONENT_NAME=192.168.100.x
```

### How It Works

The OpenVSwitch entrypoint script automatically detects any environment variables with the `NODE_IP_` prefix and uses them to:

1. Build an IP mapping table for all components
2. Configure networking
3. Update host files
4. Set up routing

### Adding a New Component

To add a new component to the network without modifying the entrypoint script:

1. Define a new environment variable with the `NODE_IP_` prefix in your template's environment section:

```json
{
  "environment": {
    "NODE_IP_NEW_COMPONENT": "192.168.100.xyz"
  }
}
```

2. The OpenVSwitch will automatically detect this new component and add it to the hosts file and IP mapping.

### Example: Adding a Monitoring Server

To add a monitoring server:

```json
{
  "name": "Monitoring-Server",
  "environment": {
    "SERVICE_TYPE": "monitoring",
    "NODE_IP_MONITORING_SERVER": "192.168.100.45",
    "NETWORK_MODE": "gns3",
    "USE_STATIC_IP": "true"
  }
}
```

### Default IP Ranges

The system uses these default IP ranges:

* FL Server: 192.168.100.10-19
* Policy Engine: 192.168.100.20-29
* Controller: 192.168.100.30-49
* OpenVSwitch: 192.168.100.42-99
* Collector: 192.168.100.40
* FL Clients: 192.168.100.100-255

You can override these ranges by setting the corresponding environment variables:
* `SUBNET_PREFIX`
* `SERVER_IP_RANGE`
* `POLICY_IP_RANGE`
* `CONTROLLER_IP_RANGE`
* `OVS_IP_RANGE`
* `COLLECTOR_IP`
* `CLIENT_IP_RANGE`

### Fallback Support

For backward compatibility, the system also supports:

* `GNS3_IP_MAP` - Legacy format for IP mapping
* `IP_MAP` - Non-prefixed version of the IP mapping
* Legacy individual IP variables like `FL_SERVER_IP`, `POLICY_ENGINE_IP`, etc.

However, the `NODE_IP_` prefix convention is recommended for all new components. 