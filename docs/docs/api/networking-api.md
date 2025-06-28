# Networking API Reference

The Networking API provides comprehensive network management capabilities through SDN controller integration, supporting both Ryu and ONOS controllers for dynamic traffic management, QoS enforcement, and network topology control.

## Base URL

```
http://localhost:8181/stats  # Ryu Controller REST API
```

## Authentication

Currently, the Networking API does not implement authentication. All endpoints are accessible without authorization headers.

**Note**: Authentication features are planned for future releases.

## Network Topology

### Get Network Topology

```http
GET /switches
```

Returns all switches in the network.

**Response:**
```json
[
  123456789,
  987654321
]
```

### Get Switch Details

```http
GET /desc/{switch_id}
```

**Response:**
```json
{
  "123456789": {
    "mfr_desc": "Open vSwitch",
    "hw_desc": "2.15.0",
    "sw_desc": "2.15.0",
    "serial_num": "None",
    "dp_desc": "None"
  }
}
```

### Get Switch Ports

```http
GET /portdesc/{switch_id}
```

**Response:**
```json
{
  "123456789": [
    {
      "port_no": 1,
      "name": "s1-eth1",
      "config": 0,
      "state": 0,
      "curr": 2112,
      "advertised": 0,
      "supported": 0,
      "peer": 0,
      "curr_speed": 10000000,
      "max_speed": 0
    }
  ]
}
```

### Get Network Links

```http
GET /topology/links
```

**Response:**
```json
[
  {
    "src": {
      "dpid": "123456789",
      "port": 2
    },
    "dst": { 
      "dpid": "987654321",
      "port": 1
    }
  }
]
```

### Get Network Hosts

```http
GET /topology/hosts
```

**Response:**
```json
[
  {
    "mac": "00:00:00:00:00:01",
    "ipv4": ["192.168.100.10"],    "port": {
      "dpid": "123456789",
      "port_no": 1
    }
  }
]
```

### Get Switch Details

```http
GET /switches/{switch_id}
```

**Response:**
```json
{
  "switch": {
    "id": "of:0000000000000001",
    "type": "OpenFlow",
    "version": "1.3",
    "manufacturer": "Open vSwitch",
    "connection": {
      "status": "connected",
      "ip": "192.168.141.100",
      "port": 6653,
      "connected_since": "2024-01-15T09:00:00Z"
    },
    "ports": [
      {
        "number": 1,
        "name": "eth1",
        "status": "enabled",
        "statistics": {
          "rx_packets": 15678,
          "tx_packets": 14892,
          "rx_bytes": 2345678,
          "tx_bytes": 2198765,
          "errors": 0,
          "drops": 2
        }
      }
    ],
    "flows": [
      {
        "id": "flow_001",
        "priority": 100,
        "match": {
          "in_port": 1,
          "eth_type": "0x0800",
          "ip_proto": 6,
          "tcp_dst": 8080
        },
        "actions": [
          {
            "type": "set_queue",
            "queue_id": 1
          },
          {
            "type": "output",
            "port": 2
          }
        ],
        "statistics": {
          "packet_count": 1256,
          "byte_count": 156789,
          "duration": "00:15:30"
        }
      }
    ],
    "queues": [
      {
        "id": 1,
        "port": 2,
        "properties": {
          "min_rate": "10Mbps",
          "max_rate": "100Mbps"
        }
      }
    ]
  }
}
```

### Get Network Statistics

```http
GET /statistics
```

**Query Parameters:**
- `metric`: bandwidth, latency, packet_loss, flow_count
- `granularity`: 1m, 5m, 1h
- `from`: Start time (ISO 8601)
- `to`: End time (ISO 8601)

**Response:**
```json
{
  "statistics": {
    "bandwidth": {
      "total_capacity": "10Gbps",
      "current_utilization": "3.2Gbps",
      "utilization_percentage": 32.0,
      "peak_utilization": "4.8Gbps",
      "peak_time": "2024-01-15T10:45:00Z"
    },
    "latency": {
      "average": "15ms",
      "minimum": "2ms",
      "maximum": "45ms",
      "p95": "35ms"
    },
    "packet_loss": {
      "rate": 0.001,
      "total_dropped": 156,
      "total_transmitted": 156000
    },
    "flows": {
      "total_active": 45,
      "new_flows": 12,
      "expired_flows": 8,
      "average_duration": "00:08:30"
    }
  },
  "per_switch": [
    {
      "switch_id": "of:0000000000000001",
      "flows": 15,
      "utilization": 25.5,
      "status": "healthy"
    }
  ]
}
```

## Flow Management

### Get Flow Statistics

```http
GET /flow/{switch_id}
```

**Response:**
```json
{
  "123456789": [
    {
      "table_id": 0,
      "priority": 100,
      "match": {
        "in_port": 1,
        "eth_type": 2048,
        "ip_proto": 6,
        "tcp_dst": 8080
      },
      "instructions": [
        {
          "type": "APPLY_ACTIONS",
          "actions": [
            {
              "type": "OUTPUT",
              "port": 2
            }
          ]
        }
      ],
      "packet_count": 1256,
      "byte_count": 156789,
      "duration_sec": 930,
      "duration_nsec": 123000000
    }
  ]
}
```

### Install Flow Rule

```http
POST /flowentry/add
Content-Type: application/json
```

**Request Body:**
```json
{
  "dpid": 123456789,
  "priority": 100,
  "match": {
    "in_port": 1,
    "eth_type": 2048,
    "ip_proto": 6,
    "ipv4_src": "192.168.100.10",
    "ipv4_dst": "192.168.100.20",
    "tcp_dst": 8080
  },
  "actions": [
    {
      "type": "OUTPUT",
      "port": 2
    }
  ],
  "idle_timeout": 30,
  "hard_timeout": 300
}
```

### Remove Flow Rule

```http
POST /flowentry/delete
Content-Type: application/json
```

**Request Body:**
```json
{
  "dpid": 123456789,
  "match": {
    "in_port": 1,
    "eth_type": 2048,
    "tcp_dst": 8080
  }
}
```

### Get Port Statistics

```http
GET /port/{switch_id}
```

**Response:**
```json
{
  "123456789": [
    {
      "port_no": 1,
      "rx_packets": 15678,
      "tx_packets": 14892,
      "rx_bytes": 2345678,
      "tx_bytes": 2198765,
      "rx_dropped": 2,
      "tx_dropped": 0,
      "rx_errors": 0,
      "tx_errors": 0,
      "rx_frame_err": 0,
      "rx_over_err": 0,
      "rx_crc_err": 0,
      "collisions": 0,
      "duration_sec": 1230,      "duration_nsec": 456000000
    }
  ]
}
```

### List Flow Rules

```http
GET /flows
```

**Query Parameters:**
- `switch_id`: Filter by switch
- `priority`: Filter by priority
- `status`: active, expired, pending
- `experiment_id`: Filter by experiment

**Response:**
```json
{
  "flows": [
    {
      "id": "flow_001",
      "switch_id": "of:0000000000000001",
      "priority": 100,
      "status": "active",
      "match": {
        "in_port": 1,
        "eth_type": "0x0800",
        "tcp_dst": 8080
      },
      "actions": [
        {
          "type": "set_queue",
          "queue_id": 1
        },
        {
          "type": "output",
          "port": 2
        }
      ],
      "statistics": {
        "packet_count": 1256,
        "byte_count": 156789,
        "duration": "00:15:30",
        "packets_per_second": 1.4,
        "bits_per_second": "8.4Kbps"
      },
      "installed_at": "2024-01-15T11:15:00Z",
      "last_matched": "2024-01-15T11:29:45Z"
    }
  ],
  "total": 1
}
```

### Update Flow Rule

```http
PUT /flows/{flow_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "priority": 150,
  "actions": [
    {
      "type": "set_queue",
      "queue_id": 2
    },
    {
      "type": "output",
      "port": 2
    }
  ]
}
```

### Delete Flow Rule

```http
DELETE /flows/{flow_id}
```

**Response:**
```json
{
  "status": "deleted",
  "flow_id": "flow_001",
  "timestamp": "2024-01-15T11:35:00Z"
}
```

## Quality of Service (QoS)

### Configure QoS Queue

```http
POST /qos/queues
Content-Type: application/json
```

**Request Body:**
```json
{
  "switch_id": "of:0000000000000001",
  "port": 2,
  "queue_id": 1,
  "properties": {
    "min_rate": "10Mbps",
    "max_rate": "100Mbps",
    "burst": "10MB",
    "priority": "high"
  },
  "dscp_mapping": [46, 34, 26],
  "description": "FL communication priority queue"
}
```

**Response:**
```json
{
  "queue": {
    "id": 1,
    "switch_id": "of:0000000000000001",
    "port": 2,
    "status": "configured",
    "properties": {
      "min_rate": "10Mbps",
      "max_rate": "100Mbps",
      "burst": "10MB"
    },
    "statistics": {
      "enqueued_packets": 0,
      "dropped_packets": 0,
      "current_rate": "0bps"
    }
  }
}
```

### Get QoS Configuration

```http
GET /qos/queues
```

**Query Parameters:**
- `switch_id`: Filter by switch
- `port`: Filter by port

**Response:**
```json
{
  "queues": [
    {
      "id": 1,
      "switch_id": "of:0000000000000001",
      "port": 2,
      "properties": {
        "min_rate": "10Mbps",
        "max_rate": "100Mbps"
      },
      "statistics": {
        "enqueued_packets": 1256,
        "dropped_packets": 12,
        "current_rate": "25Mbps",
        "utilization": 25.0
      }
    }
  ]
}
```

### Apply Traffic Shaping

```http
POST /qos/shaping
Content-Type: application/json
```

**Request Body:**
```json
{
  "switch_id": "of:0000000000000001",
  "port": 2,
  "policy": {
    "type": "token_bucket",
    "rate": "50Mbps",
    "burst": "5MB"
  },
  "filters": [
    {
      "match": {
        "ip_dscp": 46
      },
      "action": "allow"
    },
    {
      "match": {
        "ip_dscp": 0
      },
      "action": "limit",
      "rate": "10Mbps"
    }
  ]
}
```

## Path Management

### Calculate Optimal Path

```http
POST /paths/calculate
Content-Type: application/json
```

**Request Body:**
```json
{
  "source": {
    "host": "00:00:00:00:00:01",
    "ip": "192.168.141.10"
  },
  "destination": {
    "host": "00:00:00:00:00:02",
    "ip": "192.168.141.20"
  },
  "constraints": {
    "bandwidth": "20Mbps",
    "latency": "50ms",
    "avoid_switches": ["of:0000000000000003"]
  },
  "optimization": "latency" // "bandwidth", "load_balance", "shortest"
}
```

**Response:**
```json
{
  "path": {
    "id": "path_001",
    "source": "192.168.141.10",
    "destination": "192.168.141.20",
    "hops": [
      {
        "switch": "of:0000000000000001",
        "in_port": 1,
        "out_port": 2
      },
      {
        "switch": "of:0000000000000002",
        "in_port": 1,
        "out_port": 2
      }
    ],
    "metrics": {
      "total_latency": "15ms",
      "available_bandwidth": "800Mbps",
      "hop_count": 2,
      "reliability": 0.99
    },
    "backup_paths": [
      {
        "hops": 3,
        "latency": "25ms",
        "bandwidth": "600Mbps"
      }
    ]
  }
}
```

### Install Path

```http
POST /paths/{path_id}/install
Content-Type: application/json
```

**Request Body:**
```json
{
  "priority": 100,
  "qos_class": "high",
  "backup_enabled": true,
  "monitoring": {
    "enabled": true,
    "interval": "30s",
    "alerts": {
      "latency_threshold": "100ms",
      "packet_loss_threshold": 0.01
    }
  }
}
```

### Get Path Status

```http
GET /paths/{path_id}
```

**Response:**
```json
{
  "path": {
    "id": "path_001",
    "status": "active",
    "installed_at": "2024-01-15T11:30:00Z",
    "flows_installed": 2,
    "current_metrics": {
      "latency": "12ms",
      "packet_loss": 0.0005,
      "throughput": "45Mbps",
      "utilization": 0.056
    },
    "alerts": [],
    "backup_status": "standby"
  }
}
```

## Network Monitoring

### Real-time Metrics

```http
GET /monitoring/realtime
```

**Query Parameters:**
- `switches`: Comma-separated switch IDs
- `metrics`: bandwidth,latency,packet_loss,flows
- `interval`: Update interval in seconds

**Response:**
```json
{
  "timestamp": "2024-01-15T11:35:00Z",
  "switches": [
    {
      "id": "of:0000000000000001",
      "metrics": {
        "cpu_usage": 25.5,
        "memory_usage": 45.2,
        "port_utilization": {
          "1": 12.5,
          "2": 34.8
        },
        "flow_table_usage": 0.33,
        "packet_rate": 1250,
        "error_rate": 0.001
      }
    }
  ],
  "network_wide": {
    "total_bandwidth": "10Gbps",
    "utilized_bandwidth": "3.2Gbps",
    "average_latency": "15ms",
    "packet_loss_rate": 0.0008,
    "active_flows": 45
  }
}
```

### WebSocket Monitoring

```javascript
const ws = new WebSocket('ws://localhost:8181/ws/monitoring');

ws.onopen = function() {
    ws.send(JSON.stringify({
        action: 'subscribe',
        events: ['topology_change', 'link_failure', 'flow_stats'],
        switches: ['of:0000000000000001']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'topology_change':
            console.log('Topology changed:', data.details);
            break;
        case 'link_failure':
            console.log('Link failure detected:', data.link);
            break;
        case 'flow_stats':
            console.log('Flow statistics:', data.statistics);
            break;
    }
};
```

### Historical Analytics

```http
GET /analytics/historical
```

**Query Parameters:**
- `metric`: bandwidth, latency, packet_loss, topology_changes
- `from`: Start time (ISO 8601)
- `to`: End time (ISO 8601)
- `granularity`: 1m, 5m, 1h, 1d
- `aggregation`: avg, max, min, sum

**Response:**
```json
{
  "metric": "bandwidth",
  "time_range": {
    "from": "2024-01-15T10:00:00Z",
    "to": "2024-01-15T11:00:00Z"
  },
  "granularity": "5m",
  "data_points": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "total_bandwidth": "10Gbps",
      "utilized_bandwidth": "2.8Gbps",
      "utilization_percentage": 28.0
    },
    {
      "timestamp": "2024-01-15T10:05:00Z",
      "total_bandwidth": "10Gbps",
      "utilized_bandwidth": "3.2Gbps",
      "utilization_percentage": 32.0
    }
  ],
  "summary": {
    "avg_utilization": 30.5,
    "peak_utilization": 42.8,
    "peak_time": "2024-01-15T10:35:00Z"
  }
}
```

## GNS3 Integration

### Get GNS3 Projects

```http
GET /gns3/projects
```

**Response:**
```json
{
  "projects": [
    {
      "id": "gns3_proj_001",
      "name": "FLOPY-NET Testbed",
      "status": "opened",
      "topology": {
        "nodes": 8,
        "links": 12,
        "switches": 3,
        "hosts": 5
      },
      "created_at": "2024-01-15T09:00:00Z",
      "last_modified": "2024-01-15T11:00:00Z"
    }
  ]
}
```

### Control GNS3 Node

```http
POST /gns3/nodes/{node_id}/control
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "start", // "start", "stop", "suspend", "reload"
  "wait_for_ready": true,
  "timeout": 30
}
```

### Inject Network Conditions

```http
POST /gns3/conditions/inject
Content-Type: application/json
```

**Request Body:**
```json
{
  "target": {
    "type": "link",
    "id": "link_001"
  },
  "conditions": {
    "latency": "100ms",
    "jitter": "10ms",
    "packet_loss": 0.05,
    "bandwidth_limit": "1Mbps"
  },
  "duration": "5m",
  "description": "Simulate network congestion during FL training"
}
```

## Error Handling

### Flow Installation Error

```json
{
  "error": {
    "code": "FLOW_INSTALLATION_FAILED",
    "message": "Failed to install flow rule",
    "details": {
      "switch_id": "of:0000000000000001",
      "reason": "Table full",
      "max_flows": 1000,
      "current_flows": 1000
    }
  }
}
```

### Controller Connection Error

```json
{
  "error": {
    "code": "CONTROLLER_UNREACHABLE",
    "message": "SDN controller is not responding",
    "details": {
      "controller_type": "onos",
      "endpoint": "http://localhost:8181",
      "last_successful_connection": "2024-01-15T11:20:00Z",
      "retry_available": true
    }
  }
}
```

## SDK Examples

### Python SDK

```python
from flopy_net_client import NetworkingClient

# Initialize client
network = NetworkingClient(
    base_url="http://localhost:8181/api/v1",
    api_key="networking_api_key"
)

# Get current topology
topology = network.get_topology()
print(f"Network has {len(topology.switches)} switches")

# Install QoS flow for FL traffic
flow = network.install_flow({
    "switch_id": "of:0000000000000001",
    "priority": 100,
    "match": {
        "tcp_dst": 8080,
        "ip_dscp": 46
    },
    "actions": [
        {"type": "set_queue", "queue_id": 1},
        {"type": "output", "port": 2}
    ]
})

# Monitor network metrics
for metrics in network.stream_metrics(['bandwidth', 'latency']):
    print(f"Network utilization: {metrics.utilization}%")
    if metrics.utilization > 80:
        print("High network utilization detected!")
```

### JavaScript SDK

```javascript
import { NetworkingClient } from 'flopy-net-client';

const network = new NetworkingClient({
    baseUrl: 'http://localhost:8181/api/v1',
    apiKey: 'networking_api_key'
});

// Calculate and install optimal path
const path = await network.calculatePath({
    source: '192.168.141.10',
    destination: '192.168.141.20',
    constraints: {
        bandwidth: '20Mbps',
        latency: '50ms'
    }
});

await network.installPath(path.id, {
    priority: 100,
    qos_class: 'high',
    backup_enabled: true
});

// Real-time topology monitoring  
const monitor = network.createTopologyMonitor();
monitor.on('switch_connected', (switch_info) => {
    console.log('Switch ' + switch_info.id + ' connected');
});

monitor.on('link_failure', (link_info) => {
    console.log('Link failure: ' + link_info.id);
    // Trigger failover logic
});
```
