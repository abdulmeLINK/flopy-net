# Collector API

The Collector service provides REST APIs for retrieving metrics, events, and system monitoring data from all FLOPY-NET components.

## Base URL

```
http://localhost:8002/api/v1
```

## Authentication

The Collector service supports API key authentication:

```http
Authorization: Bearer <api-key>
```

## Core Endpoints

### Health and Status

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-16T10:30:00Z",
  "uptime": 7200,
  "metrics_collected": 125847,
  "events_processed": 8745,
  "storage": {
    "influxdb_status": "connected",
    "redis_status": "connected",
    "disk_usage": "45%",
    "memory_usage": "512MB"
  },
  "data_sources": {
    "fl_server": "connected",
    "policy_engine": "connected", 
    "sdn_controller": "connected",
    "gns3_server": "connected"
  }
}
```

#### System Status
```http
GET /status
```

**Response:**
```json
{
  "collector_status": "operational",
  "version": "1.0.0",
  "collection_stats": {
    "total_metrics": 125847,
    "metrics_per_minute": 45,
    "events_processed": 8745,
    "events_per_minute": 12,
    "last_collection": "2025-01-16T10:29:00Z",
    "collection_success_rate": 0.987
  },
  "storage_stats": {
    "influxdb": {
      "status": "healthy",
      "database_size": "2.5GB",
      "retention_days": 30,
      "write_throughput": "1.2MB/s"
    },
    "redis": {
      "status": "healthy",
      "memory_usage": "128MB",
      "cache_hit_rate": 0.85
    }
  },
  "data_source_status": {
    "fl_server": {
      "status": "connected",
      "last_successful_collection": "2025-01-16T10:29:00Z",
      "success_rate": 0.99
    },
    "policy_engine": {
      "status": "connected", 
      "last_successful_collection": "2025-01-16T10:29:15Z",
      "success_rate": 0.97
    },
    "sdn_controller": {
      "status": "connected",
      "last_successful_collection": "2025-01-16T10:28:45Z", 
      "success_rate": 0.94
    }
  }
}
```

### Metrics Retrieval

#### Get Latest Metrics
```http
GET /metrics/latest
```

**Query Parameters:**
- `component` (optional): Filter by component (`fl_server`, `policy_engine`, `sdn_controller`)
- `metric_type` (optional): Filter by metric type (`performance`, `training`, `network`)
- `limit` (optional): Number of results (default: 100)

**Response:**
```json
{
  "timestamp": "2025-01-16T10:30:00Z",
  "metrics": [
    {
      "component": "fl_server",
      "metric_type": "training",
      "timestamp": "2025-01-16T10:29:30Z",
      "experiment_id": "exp_2025_001",
      "data": {
        "current_round": 5,
        "global_accuracy": 0.78,
        "global_loss": 0.45,
        "active_clients": 8,
        "round_duration": 120
      }
    },
    {
      "component": "policy_engine",
      "metric_type": "security",
      "timestamp": "2025-01-16T10:29:45Z",
      "data": {
        "evaluations_per_minute": 15,
        "trust_score_updates": 8,
        "violations_detected": 0,
        "average_trust_score": 0.87
      }
    }
  ],
  "total_count": 2,
  "collection_metadata": {
    "collection_interval": 30,
    "next_collection": "2025-01-16T10:30:30Z"
  }
}
```

#### Get Historical Metrics
```http
GET /metrics/history
```

**Query Parameters:**
- `component` (required): Component name
- `metric_type` (optional): Metric type
- `start_time` (required): Start timestamp (ISO 8601)
- `end_time` (required): End timestamp (ISO 8601)
- `aggregation` (optional): Aggregation interval (`1m`, `5m`, `1h`, `1d`)
- `limit` (optional): Maximum number of data points

**Response:**
```json
{
  "component": "fl_server",
  "metric_type": "training",
  "time_range": {
    "start": "2025-01-16T09:00:00Z",
    "end": "2025-01-16T10:30:00Z"
  },
  "aggregation": "5m",
  "data_points": [
    {
      "timestamp": "2025-01-16T09:00:00Z",
      "metrics": {
        "global_accuracy": 0.65,
        "global_loss": 0.67,
        "active_clients": 10,
        "round_duration": 135
      }
    },
    {
      "timestamp": "2025-01-16T09:05:00Z", 
      "metrics": {
        "global_accuracy": 0.68,
        "global_loss": 0.62,
        "active_clients": 9,
        "round_duration": 128
      }
    }
  ],
  "total_points": 18,
  "summary": {
    "avg_accuracy": 0.74,
    "max_accuracy": 0.78,
    "min_accuracy": 0.65,
    "accuracy_trend": "increasing"
  }
}
```

#### Get FL Metrics
```http
GET /metrics/fl
```

**Query Parameters:**
- `experiment_id` (optional): Filter by experiment
- `client_id` (optional): Filter by specific client
- `round` (optional): Filter by training round
- `metric_name` (optional): Specific metric (`accuracy`, `loss`, `round_duration`)

**Response:**
```json
{
  "experiment_id": "exp_2025_001",
  "current_round": 5,
  "total_rounds": 10,
  "global_metrics": {
    "accuracy": [0.45, 0.58, 0.67, 0.73, 0.78],
    "loss": [0.89, 0.76, 0.62, 0.51, 0.45],
    "round_durations": [125, 118, 132, 127, 120]
  },
  "client_metrics": {
    "client-001": {
      "rounds_participated": 5,
      "avg_local_accuracy": 0.79,
      "avg_training_time": 42.5,
      "trust_score": 0.95,
      "contribution_score": 0.87
    },
    "client-002": {
      "rounds_participated": 4,
      "avg_local_accuracy": 0.76,
      "avg_training_time": 38.2,
      "trust_score": 0.82,
      "contribution_score": 0.79
    }
  },
  "aggregated_stats": {
    "total_clients": 12,
    "avg_participation_rate": 0.75,
    "convergence_rate": 0.12,
    "training_efficiency": 0.89
  },
  "timestamp": "2025-01-16T10:30:00Z"
}
```

#### Get Network Metrics
```http
GET /metrics/network
```

**Query Parameters:**
- `timeframe` (optional): Time window (`1h`, `6h`, `24h`, `7d`)
- `device_id` (optional): Filter by network device
- `metric_type` (optional): Filter by type (`latency`, `bandwidth`, `packet_loss`)

**Response:**
```json
{
  "timeframe": "1h",
  "timestamp": "2025-01-16T10:30:00Z",
  "topology_stats": {
    "total_devices": 5,
    "total_hosts": 12,
    "total_links": 8,
    "active_flows": 145,
    "topology_changes": 2
  },
  "performance_metrics": {
    "average_latency_ms": 23.5,
    "peak_latency_ms": 45.2,
    "average_bandwidth_mbps": 287.3,
    "peak_bandwidth_mbps": 850.2,
    "packet_loss_rate": 0.001,
    "jitter_ms": 2.1
  },
  "device_metrics": [
    {
      "device_id": "switch-001",
      "device_type": "openflow_switch",
      "status": "active",
      "cpu_usage": 0.25,
      "memory_usage": 0.34,
      "port_stats": [
        {
          "port": 1,
          "rx_bytes": 1250000,
          "tx_bytes": 980000,
          "rx_packets": 8500,
          "tx_packets": 7200,
          "errors": 0
        }
      ]
    }
  ],
  "flow_stats": {
    "total_flows": 145,
    "active_flows": 142,
    "expired_flows": 3,
    "flow_table_utilization": 0.65,
    "priority_distribution": {
      "high": 45,
      "medium": 67,
      "low": 30
    }
  },
  "traffic_analysis": {
    "fl_traffic_percentage": 78.3,
    "control_traffic_percentage": 12.1,
    "background_traffic_percentage": 9.6,
    "top_flows": [
      {
        "src": "192.168.141.100",
        "dst": "192.168.141.200",
        "bytes": 125000,
        "packets": 850,
        "protocol": "TCP",
        "application": "FL_training"
      }
    ]
  }
}
```

### Events and Logs

#### Get Recent Events
```http
GET /events
```

**Query Parameters:**
- `component` (optional): Filter by component
- `event_type` (optional): Filter by event type
- `severity` (optional): Filter by severity (`info`, `warning`, `error`, `critical`)
- `limit` (optional): Number of results (default: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt_12345",
      "timestamp": "2025-01-16T10:29:45Z",
      "component": "fl_server",
      "event_type": "round_completed",
      "severity": "info",
      "message": "Training round 5 completed successfully",
      "details": {
        "experiment_id": "exp_2025_001",
        "round": 5,
        "participating_clients": 8,
        "accuracy": 0.78,
        "duration_seconds": 120
      },
      "tags": ["training", "completion", "success"]
    },
    {
      "event_id": "evt_12346",
      "timestamp": "2025-01-16T10:28:30Z",
      "component": "policy_engine", 
      "event_type": "violation_detected",
      "severity": "warning",
      "message": "Client exceeded model update frequency",
      "details": {
        "client_id": "client-003",
        "policy_id": 5,
        "violation_type": "frequency_limit",
        "expected": "1 per round",
        "actual": "3 updates"
      },
      "tags": ["policy", "violation", "frequency"]
    }
  ],
  "total_count": 8745,
  "summary": {
    "info": 7234,
    "warning": 1245,
    "error": 245,
    "critical": 21
  },
  "filters_applied": {
    "component": null,
    "event_type": null,
    "severity": null
  }
}
```

#### Get Events Summary
```http
GET /events/summary
```

**Query Parameters:**
- `timeframe` (optional): Time window (`1h`, `24h`, `7d`, `30d`)

**Response:**
```json
{
  "timeframe": "24h",
  "timestamp": "2025-01-16T10:30:00Z",
  "total_events": 2156,
  "event_breakdown": {
    "by_severity": {
      "info": 1834,
      "warning": 267,
      "error": 48,
      "critical": 7
    },
    "by_component": {
      "fl_server": 856,
      "policy_engine": 423,
      "sdn_controller": 398,
      "collector": 289,
      "dashboard": 190
    },
    "by_type": {
      "training_events": 445,
      "policy_events": 378,
      "network_events": 334,
      "system_events": 256,
      "security_events": 89
    }
  },
  "trends": {
    "events_per_hour": [
      {"hour": "2025-01-16T09:00:00Z", "count": 92},
      {"hour": "2025-01-16T10:00:00Z", "count": 87}
    ],
    "error_rate": 0.025,
    "critical_events_today": 7
  },
  "recent_critical": [
    {
      "timestamp": "2025-01-16T08:45:00Z",
      "component": "sdn_controller",
      "message": "Network partition detected"
    }
  ]
}
```

#### Stream Events (WebSocket)
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/events');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'metric_update':
            handleMetricUpdate(data);
            break;
        case 'system_event':
            handleSystemEvent(data);
            break;
        case 'alert':
            handleAlert(data);
            break;
    }
};

// Subscribe to specific event streams
ws.send(JSON.stringify({
    action: 'subscribe',
    streams: ['fl_metrics', 'network_events', 'policy_violations']
}));
```

### Data Export

#### Export Metrics
```http
POST /export/metrics
```

**Request Body:**
```json
{
  "export_config": {
    "components": ["fl_server", "policy_engine"],
    "metric_types": ["training", "security"],
    "time_range": {
      "start": "2025-01-15T00:00:00Z",
      "end": "2025-01-16T23:59:59Z"
    },
    "format": "json",
    "aggregation": "1h",
    "include_metadata": true
  },
  "delivery": {
    "method": "download",
    "compression": "gzip"
  }
}
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "processing",
  "estimated_completion": "2025-01-16T10:35:00Z",
  "estimated_size_mb": 125.5,
  "download_url": "/exports/download/export_12345",
  "expires_at": "2025-01-23T10:30:00Z",
  "format": "json",
  "compression": "gzip"
}
```

#### Get Export Status
```http
GET /export/{export_id}/status
```

**Response:**
```json
{
  "export_id": "export_12345",
  "status": "completed",
  "created_at": "2025-01-16T10:30:00Z",
  "completed_at": "2025-01-16T10:33:45Z",
  "processing_time_seconds": 225,
  "file_size_mb": 118.2,
  "records_exported": 15847,
  "download_url": "/exports/download/export_12345",
  "expires_at": "2025-01-23T10:30:00Z"
}
```

#### Download Export
```http
GET /exports/download/{export_id}
```

**Response:** Binary file (JSON, CSV, or Parquet based on export configuration)

### Analytics and Aggregations

#### Get Performance Analytics
```http
GET /analytics/performance
```

**Query Parameters:**
- `timeframe` (optional): Analysis window (`1h`, `24h`, `7d`, `30d`)
- `component` (optional): Focus on specific component

**Response:**
```json
{
  "timeframe": "24h",
  "timestamp": "2025-01-16T10:30:00Z",
  "fl_performance": {
    "training_efficiency": 0.89,
    "convergence_rate": 0.12,
    "average_round_duration": 125.5,
    "client_participation_rate": 0.78,
    "model_improvement_trend": "positive"
  },
  "network_performance": {
    "average_latency_ms": 25.3,
    "bandwidth_utilization": 0.67,
    "packet_loss_rate": 0.001,
    "qos_compliance": 0.94
  },
  "system_health": {
    "component_availability": 0.998,
    "error_rate": 0.012,
    "resource_utilization": 0.65,
    "performance_score": 0.92
  },
  "recommendations": [
    "Consider increasing client selection ratio to improve convergence",
    "Network latency is within acceptable bounds",
    "System performance is optimal"
  ]
}
```

#### Get Trend Analysis
```http
GET /analytics/trends
```

**Query Parameters:**
- `metric` (required): Metric to analyze (`accuracy`, `loss`, `latency`, `trust_scores`)
- `timeframe` (optional): Analysis period (`7d`, `30d`, `90d`)
- `component` (optional): Component filter

**Response:**
```json
{
  "metric": "accuracy",
  "timeframe": "7d",
  "trend_analysis": {
    "direction": "increasing",
    "slope": 0.025,
    "correlation": 0.87,
    "confidence": 0.92,
    "r_squared": 0.78
  },
  "data_points": [
    {"timestamp": "2025-01-10T00:00:00Z", "value": 0.65},
    {"timestamp": "2025-01-11T00:00:00Z", "value": 0.68},
    {"timestamp": "2025-01-12T00:00:00Z", "value": 0.71}
  ],
  "statistics": {
    "mean": 0.72,
    "median": 0.71,
    "std_deviation": 0.045,
    "min": 0.58,
    "max": 0.82
  },
  "predictions": {
    "next_24h": 0.785,
    "next_7d": 0.823,
    "confidence_interval": [0.75, 0.85]
  }
}
```

### Configuration and Management

#### Get Collection Configuration
```http
GET /config/collection
```

**Response:**
```json
{
  "collection_intervals": {
    "fl_server": 30,
    "policy_engine": 45,
    "sdn_controller": 15,
    "gns3_server": 60
  },
  "data_retention": {
    "raw_metrics": "7d",
    "aggregated_1m": "30d",
    "aggregated_1h": "90d",
    "aggregated_1d": "1y"
  },
  "storage_config": {
    "influxdb": {
      "host": "localhost",
      "port": 8086,
      "database": "flopynet_metrics"
    },
    "redis": {
      "host": "localhost", 
      "port": 6379,
      "ttl_seconds": 300
    }
  },
  "alerting": {
    "enabled": true,
    "thresholds": {
      "collection_failure_rate": 0.1,
      "storage_usage": 0.8,
      "response_time_ms": 1000
    }
  }
}
```

#### Update Collection Settings
```http
PUT /config/collection
```

**Request Body:** Same structure as GET response

### Monitoring and Alerting

#### Get Alerts
```http
GET /alerts
```

**Query Parameters:**
- `severity` (optional): Filter by severity
- `status` (optional): Filter by status (`active`, `resolved`, `acknowledged`)
- `component` (optional): Filter by component

**Response:**
```json
{
  "alerts": [
    {
      "alert_id": "alert_001",
      "timestamp": "2025-01-16T10:15:00Z",
      "severity": "warning",
      "component": "collector",
      "title": "High Collection Latency",
      "description": "Metric collection is taking longer than expected",
      "details": {
        "average_latency_ms": 1250,
        "threshold_ms": 1000,
        "affected_components": ["fl_server", "policy_engine"]
      },
      "status": "active",
      "duration": "15m",
      "recommended_actions": [
        "Check component connectivity",
        "Review system resources"
      ]
    }
  ],
  "summary": {
    "total_alerts": 5,
    "active_alerts": 3,
    "critical_alerts": 0,
    "alerts_last_24h": 12
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "METRIC_NOT_FOUND",
    "message": "Requested metric data not found",
    "details": "No data available for the specified time range",
    "timestamp": "2025-01-16T10:30:00Z",
    "trace_id": "trace_xyz789"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_TIME_RANGE` | Invalid start/end time parameters |
| 401 | `UNAUTHORIZED` | Invalid API key |
| 404 | `METRIC_NOT_FOUND` | Requested metric data not found |
| 404 | `COMPONENT_NOT_FOUND` | Specified component does not exist |
| 422 | `INVALID_AGGREGATION` | Invalid aggregation interval |
| 429 | `RATE_LIMITED` | Too many API requests |
| 500 | `COLLECTION_ERROR` | Error collecting metrics from source |
| 503 | `STORAGE_UNAVAILABLE` | Database temporarily unavailable |

## SDK Examples

### Python SDK

```python
import requests
from datetime import datetime, timedelta

class CollectorClient:
    def __init__(self, base_url="http://localhost:8002", api_key=None):
        self.base_url = f"{base_url}/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}" if api_key else None
        }
    
    def get_latest_metrics(self, component=None, metric_type=None):
        """Get latest metrics from collector."""
        params = {}
        if component:
            params['component'] = component
        if metric_type:
            params['metric_type'] = metric_type
            
        response = requests.get(
            f"{self.base_url}/metrics/latest",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def get_fl_metrics(self, experiment_id=None):
        """Get FL training metrics."""
        params = {}
        if experiment_id:
            params['experiment_id'] = experiment_id
            
        response = requests.get(
            f"{self.base_url}/metrics/fl",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def export_metrics(self, components, start_time, end_time, format='json'):
        """Export historical metrics."""
        payload = {
            "export_config": {
                "components": components,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "format": format
            }
        }
        
        response = requests.post(
            f"{self.base_url}/export/metrics",
            headers=self.headers,
            json=payload
        )
        return response.json()
```

### JavaScript SDK

```javascript
class CollectorAPI {
    constructor(baseUrl = 'http://localhost:8002', apiKey = null) {
        this.baseUrl = `${baseUrl}/api/v1`;
        this.headers = {
            ...(apiKey && { 'Authorization': `Bearer ${apiKey}` })
        };
    }
    
    async getLatestMetrics(component = null, metricType = null) {
        const params = new URLSearchParams();
        if (component) params.append('component', component);
        if (metricType) params.append('metric_type', metricType);
        
        const response = await fetch(
            `${this.baseUrl}/metrics/latest?${params}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    async getNetworkMetrics(timeframe = '1h') {
        const response = await fetch(
            `${this.baseUrl}/metrics/network?timeframe=${timeframe}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    // WebSocket connection for real-time metrics
    connectMetricsStream() {
        this.ws = new WebSocket('ws://localhost:8002/ws/events');
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMetricUpdate(data);
        };
        
        return this.ws;
    }
    
    handleMetricUpdate(data) {
        switch (data.type) {
            case 'metric_update':
                console.log('Metric update:', data);
                break;
            case 'alert':
                console.log('Alert:', data);
                break;
        }
    }
}
```

This comprehensive Collector API reference provides developers with all the tools needed to retrieve, analyze, and export metrics and events from the FLOPY-NET system.
