# Collector API Reference

The Collector API provides access to system metrics, monitoring data, and real-time performance information from all FLOPY-NET components.

## Base URL

```
http://localhost:8000/
```

## Service Information

**Container**: `abdulmelik/flopynet-collector:v1.0.0-alpha.8`  
**Network IP**: `192.168.100.40`  
**Port**: `8000` (exposed as `8083` on host)  
**Technology**: Flask REST API with APScheduler  
**Storage**: SQLite database (`metrics.db`) and JSON logs (`events.jsonl`)  

## API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "collector",
  "version": "v1.0.0-alpha.8",
  "uptime_seconds": 3600,
  "last_collection": "2025-06-16T10:30:00Z"
}
```

### System Metrics

```http
GET /metrics
```

**Response:**
```json
{
  "timestamp": "2025-06-16T10:30:00Z",
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 1024,
    "disk_usage": 2048,
    "network_io": {
      "bytes_sent": 1048576,
      "bytes_received": 2097152
    }
  },
  "services": {
    "policy_engine": {
      "status": "healthy",
      "response_time_ms": 15,
      "last_check": "2025-06-16T10:29:55Z"
    },
    "fl_server": {
      "status": "healthy", 
      "response_time_ms": 32,
      "last_check": "2025-06-16T10:29:55Z"
    }
  }
}
```

## Federated Learning Metrics

### FL Training Status

```http
GET /fl/status
```

**Response:**
```json
{
  "server_status": "training",
  "current_round": 5,
  "total_rounds": 10,
  "active_clients": 2,
  "training_progress": 50.0,
  "last_updated": "2025-06-16T10:30:00Z"
}
```

### FL Client Information  

```http
GET /fl/clients
```

**Response:**
```json
{
  "clients": [
    {
      "client_id": "client-1",
      "ip_address": "192.168.100.101",
      "status": "training",
      "last_seen": "2025-06-16T10:29:45Z",
      "round_participation": 5,
      "training_time_avg": 120.5
    },
    {
      "client_id": "client-2", 
      "ip_address": "192.168.100.102",
      "status": "idle",
      "last_seen": "2025-06-16T10:29:30Z",
      "round_participation": 4,
      "training_time_avg": 98.2
    }
  ]
}
```

## Network Monitoring

### Network Statistics

```http
GET /network/stats  
```

**Response:**
```json
{
  "topology": {
    "devices": 5,
    "active_connections": 4,
    "last_topology_update": "2025-06-16T10:25:00Z"
  },
  "traffic": {
    "total_bytes": 104857600,
    "fl_traffic_bytes": 52428800,
    "control_traffic_bytes": 1048576,
    "last_measurement": "2025-06-16T10:30:00Z"
  },
  "quality": {
    "average_latency_ms": 12.5,
    "packet_loss_percentage": 0.01,
    "bandwidth_utilization": 25.8
  }
}
```

### SDN Controller Status

```http
GET /network/sdn
```

**Response:**
```json
{
  "controller": {
    "status": "active",
    "ip_address": "192.168.100.41",
    "openflow_version": "1.3",
    "connected_switches": 1,
    "active_flows": 12,
    "last_contact": "2025-06-16T10:29:50Z"
  },
  "switches": [
    {
      "switch_id": "ovs-1",
      "ip_address": "192.168.100.60", 
      "status": "connected",
      "flow_count": 12,
      "port_count": 4
    }
  ]
}
```

## Policy Engine Monitoring

### Policy Events

```http
GET /policy/events
```

**Query Parameters:**
- `limit`: Number of events to return (default: 50)
- `since`: ISO timestamp to filter events since

**Response:**
```json
{
  "events": [
    {
      "timestamp": "2025-06-16T10:29:45Z",
      "policy_id": "client_validation",
      "event_type": "policy_executed",
      "target": "fl-client-1",
      "result": "allowed",
      "details": {
        "client_id": "client-1",
        "validation_result": "passed"
      }
    },
    {
      "timestamp": "2025-06-16T10:29:30Z", 
      "policy_id": "network_quality",
      "event_type": "policy_violation",
      "target": "network_link_1",
      "result": "warning",
      "details": {
        "metric": "latency",
        "value": 105,
        "threshold": 100
      }
    }
  ],
  "total": 2,
  "since": "2025-06-16T10:00:00Z"
}
```

## Data Export

### Export Historical Data

```http
GET /export/metrics
```

**Query Parameters:**
- `start_date`: ISO timestamp (required)  
- `end_date`: ISO timestamp (required)
- `format`: `json` or `csv` (default: json)
- `metrics`: Comma-separated list of metric types

**Response:**
```json
{
  "export_id": "exp_20250616_103000",
  "status": "completed",
  "download_url": "/download/exp_20250616_103000.json",
  "file_size_bytes": 2048576,
  "records_count": 10000,
  "generated_at": "2025-06-16T10:30:00Z"
}
```

## Real-time Monitoring

### WebSocket Connection

```javascript
// Connect to real-time metrics stream
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Real-time metrics:', data);
};
```

## Error Responses

All API endpoints return consistent error responses:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Requested metric not available",
    "timestamp": "2025-06-16T10:30:00Z"
  }
}
```

## Usage Examples

### Monitor FL Training Progress

```powershell
# Check FL server status
curl http://localhost:8000/fl/status

# Get client information
curl http://localhost:8000/fl/clients

# Monitor policy events
curl "http://localhost:8000/policy/events?limit=10"
```

### Network Health Monitoring

```powershell
# Get network statistics
curl http://localhost:8000/network/stats

# Check SDN controller status  
curl http://localhost:8000/network/sdn

# Export historical data
curl "http://localhost:8000/export/metrics?start_date=2025-06-16T09:00:00Z&end_date=2025-06-16T10:00:00Z"
``` Reference

The Collector API provides access to the central metrics aggregation system, enabling real-time data collection, historical analysis, and custom monitoring solutions.

## Base URL

```
http://localhost:8081/api/v1
```

## Authentication

Include API key in the Authorization header:

```http
Authorization: Bearer collector_api_key_here
```

## Metrics Collection

### Submit Metrics

```http
POST /metrics
Content-Type: application/json
```

**Request Body:**
```json
{
  "source": "fl_server",
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": [
    {
      "name": "cpu_usage",
      "value": 45.2,
      "unit": "percent",
      "tags": {
        "host": "fl-server-01",
        "experiment_id": "exp_001"
      }
    },
    {
      "name": "memory_usage",
      "value": 512.5,
      "unit": "MB",
      "tags": {
        "host": "fl-server-01",
        "experiment_id": "exp_001"
      }
    },
    {
      "name": "active_clients",
      "value": 5,
      "unit": "count",
      "tags": {
        "experiment_id": "exp_001"
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "metrics_accepted": 3,
  "timestamp": "2024-01-15T10:30:01Z",
  "batch_id": "batch_abc123"
}
```

### Batch Metrics Submission

```http
POST /metrics/batch
Content-Type: application/json
```

**Request Body:**
```json
{
  "batches": [
    {
      "source": "policy_engine",
      "timestamp": "2024-01-15T10:30:00Z",
      "metrics": [
        {
          "name": "policies_evaluated",
          "value": 150,
          "unit": "count"
        }
      ]
    },
    {
      "source": "sdn_controller",
      "timestamp": "2024-01-15T10:30:00Z",
      "metrics": [
        {
          "name": "flows_installed",
          "value": 25,
          "unit": "count"
        }
      ]
    }
  ]
}
```

## Metrics Querying

### Query Time Series Data

```http
GET /metrics/query
```

**Query Parameters:**
- `metric`: Metric name (required)
- `source`: Data source filter
- `from`: Start time (ISO 8601)
- `to`: End time (ISO 8601)
- `granularity`: Time granularity (1m, 5m, 1h, 1d)
- `aggregation`: Aggregation function (avg, sum, max, min, count)
- `tags`: Tag filters (key:value format)

**Example:**
```http
GET /metrics/query?metric=cpu_usage&source=fl_server&from=2024-01-15T10:00:00Z&to=2024-01-15T11:00:00Z&granularity=5m&aggregation=avg&tags=experiment_id:exp_001
```

**Response:**
```json
{
  "metric": "cpu_usage",
  "source": "fl_server",
  "granularity": "5m",
  "aggregation": "avg",
  "data_points": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "value": 42.5
    },
    {
      "timestamp": "2024-01-15T10:05:00Z",
      "value": 45.2
    },
    {
      "timestamp": "2024-01-15T10:10:00Z",
      "value": 48.1
    }
  ],
  "total_points": 3,
  "query_time_ms": 15
}
```

### Multi-Metric Query

```http
POST /metrics/query/multi
Content-Type: application/json
```

**Request Body:**
```json
{
  "queries": [
    {
      "metric": "cpu_usage",
      "source": "fl_server",
      "aggregation": "avg"
    },
    {
      "metric": "memory_usage",
      "source": "fl_server",
      "aggregation": "avg"
    },
    {
      "metric": "active_clients",
      "source": "fl_server",
      "aggregation": "last"
    }
  ],
  "from": "2024-01-15T10:00:00Z",
  "to": "2024-01-15T11:00:00Z",
  "granularity": "5m"
}
```

**Response:**
```json
{
  "results": [
    {
      "metric": "cpu_usage",
      "data_points": [
        {
          "timestamp": "2024-01-15T10:00:00Z",
          "value": 42.5
        }
      ]
    },
    {
      "metric": "memory_usage",
      "data_points": [
        {
          "timestamp": "2024-01-15T10:00:00Z",
          "value": 510.2
        }
      ]
    }
  ]
}
```

## Real-time Streaming

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8081/ws/metrics');

ws.onopen = function() {
    // Subscribe to specific metrics
    ws.send(JSON.stringify({
        action: 'subscribe',
        metrics: ['cpu_usage', 'memory_usage'],
        sources: ['fl_server', 'policy_engine'],
        tags: {
            experiment_id: 'exp_001'
        }
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Real-time metric:', data);
};
```

**Real-time Message Format:**
```json
{
  "type": "metric_update",
  "source": "fl_server",
  "timestamp": "2024-01-15T10:30:00Z",
  "metric": {
    "name": "cpu_usage",
    "value": 47.8,
    "unit": "percent",
    "tags": {
      "host": "fl-server-01",
      "experiment_id": "exp_001"
    }
  }
}
```

### Server-Sent Events (SSE)

```http
GET /metrics/stream
Accept: text/event-stream
```

**Query Parameters:**
- `metrics`: Comma-separated metric names
- `sources`: Comma-separated source names
- `interval`: Update interval in seconds (default: 5)

**Response Stream:**
```
data: {"metric": "cpu_usage", "value": 45.2, "timestamp": "2024-01-15T10:30:00Z"}

data: {"metric": "memory_usage", "value": 512.5, "timestamp": "2024-01-15T10:30:01Z"}
```

## Aggregations and Analytics

### Statistical Summary

```http
GET /metrics/summary
```

**Query Parameters:**
- `metric`: Metric name (required)
- `source`: Data source filter
- `from`: Start time
- `to`: End time
- `tags`: Tag filters

**Response:**
```json
{
  "metric": "cpu_usage",
  "source": "fl_server",
  "time_range": {
    "from": "2024-01-15T10:00:00Z",
    "to": "2024-01-15T11:00:00Z"
  },
  "statistics": {
    "count": 60,
    "min": 35.2,
    "max": 68.5,
    "avg": 47.3,
    "median": 46.8,
    "std_dev": 8.2,
    "percentiles": {
      "p50": 46.8,
      "p90": 58.4,
      "p95": 62.1,
      "p99": 66.8
    }
  }
}
```

### Anomaly Detection

```http
POST /metrics/anomalies
Content-Type: application/json
```

**Request Body:**
```json
{
  "metric": "cpu_usage",
  "source": "fl_server",
  "from": "2024-01-15T10:00:00Z",
  "to": "2024-01-15T11:00:00Z",
  "algorithm": "isolation_forest",
  "sensitivity": 0.1
}
```

**Response:**
```json
{
  "anomalies": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "value": 85.2,
      "score": 0.95,
      "severity": "high",
      "context": {
        "baseline_avg": 47.3,
        "deviation": 37.9
      }
    }
  ],
  "total_anomalies": 1,
  "analysis_time_ms": 250
}
```

## Data Export

### Export Historical Data

```http
GET /metrics/export
```

**Query Parameters:**
- `format`: Export format (csv, json, parquet)
- `metric`: Metric name (required)
- `source`: Data source filter
- `from`: Start time (required)
- `to`: End time (required)
- `granularity`: Time granularity

**Response Headers:**
```http
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="cpu_usage_export.csv"
```

**CSV Format:**
```csv
timestamp,value,source,experiment_id,host
2024-01-15T10:00:00Z,42.5,fl_server,exp_001,fl-server-01
2024-01-15T10:05:00Z,45.2,fl_server,exp_001,fl-server-01
```

### Custom Data Pipeline

```http
POST /metrics/pipeline
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "experiment_summary",
  "pipeline": [
    {
      "operation": "filter",
      "params": {
        "tags": {
          "experiment_id": "exp_001"
        }
      }
    },
    {
      "operation": "aggregate",
      "params": {
        "window": "5m",
        "functions": ["avg", "max"]
      }
    },
    {
      "operation": "transform",
      "params": {
        "formula": "avg_cpu + max_memory"
      }
    }
  ],
  "output": {
    "destination": "webhook",
    "url": "https://your-system.com/webhook"
  }
}
```

## System Status

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "5d 12h 30m",
  "components": {
    "influxdb": {
      "status": "connected",
      "response_time": "5ms",
      "database_size": "2.5GB"
    },
    "redis": {
      "status": "connected",
      "response_time": "1ms",
      "memory_usage": "128MB"
    },
    "metrics_processor": {
      "status": "running",
      "queue_size": 45,
      "processing_rate": "1250 metrics/sec"
    }
  }
}
```

### Performance Metrics

```http
GET /system/performance
```

**Response:**
```json
{
  "ingestion": {
    "rate": "1250 metrics/sec",
    "peak_rate": "2500 metrics/sec",
    "total_metrics": 15678900,
    "queue_size": 45,
    "queue_max": 10000
  },
  "storage": {
    "total_size": "2.5GB",
    "compression_ratio": 0.25,
    "retention_policy": "30 days",
    "oldest_data": "2024-01-01T00:00:00Z"
  },
  "queries": {
    "avg_response_time": "15ms",
    "queries_per_minute": 120,
    "cache_hit_rate": 0.85
  }
}
```

## Configuration

### Get Configuration

```http
GET /config
```

**Response:**
```json
{
  "storage": {
    "retention_days": 30,
    "compression_enabled": true,
    "batch_size": 1000
  },
  "processing": {
    "buffer_size": 10000,
    "flush_interval": "5s",
    "worker_threads": 4
  },
  "alerting": {
    "enabled": true,
    "thresholds": {
      "queue_size": 8000,
      "ingestion_rate": 5000
    }
  }
}
```

### Update Configuration

```http
PUT /config
Content-Type: application/json
```

**Request Body:**
```json
{
  "storage": {
    "retention_days": 60
  },
  "processing": {
    "worker_threads": 8
  }
}
```

## Error Handling

### Rate Limit Exceeded

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60,
    "limit": 5000,
    "window": "1h"
  }
}
```

### Invalid Query

```json
{
  "error": {
    "code": "INVALID_QUERY",
    "message": "Invalid time range",
    "details": {
      "issue": "Start time must be before end time",
      "from": "2024-01-15T11:00:00Z",
      "to": "2024-01-15T10:00:00Z"
    }
  }
}
```

## SDK Examples

### Python SDK

```python
from flopy_net_client import CollectorClient
import time

# Initialize client
collector = CollectorClient(
    base_url="http://localhost:8081/api/v1",
    api_key="collector_api_key"
)

# Submit metrics
collector.submit_metric(
    source="custom_app",
    name="request_count",
    value=150,
    tags={"endpoint": "/api/users"}
)

# Query historical data
data = collector.query_metrics(
    metric="cpu_usage",
    source="fl_server",
    from_time="2024-01-15T10:00:00Z",
    to_time="2024-01-15T11:00:00Z",
    granularity="5m"
)

# Real-time streaming
for metric in collector.stream_metrics(["cpu_usage", "memory_usage"]):
    print(f"{metric.name}: {metric.value}")
```

### JavaScript SDK

```javascript
import { CollectorClient } from 'flopy-net-client';

const collector = new CollectorClient({
    baseUrl: 'http://localhost:8081/api/v1',
    apiKey: 'collector_api_key'
});

// Submit metrics
await collector.submitMetrics([
    {
        name: 'page_views',
        value: 25,
        tags: { page: '/dashboard' }
    }
]);

// Query data
const data = await collector.queryMetrics({
    metric: 'cpu_usage',
    from: '2024-01-15T10:00:00Z',
    to: '2024-01-15T11:00:00Z'
});

// WebSocket streaming
const stream = collector.createStream(['cpu_usage', 'memory_usage']);
stream.on('metric', (metric) => {
    console.log(metric.name + ': ' + metric.value);
});
```
