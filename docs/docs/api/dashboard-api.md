# Dashboard API Reference

The Dashboard API provides programmatic access to FLOPY-NET's web interface backend, enabling real-time monitoring, system configuration, and data visualization through a FastAPI-based REST service.

## Base URL

```
http://localhost:8001/api
```

## Service Information

**Backend**: FastAPI REST API (Port 8001)  
**Frontend**: Vite/React SPA (Port 8085)  
**Authentication**: None (currently open access)  
**Technology**: FastAPI with async/await support  
**WebSocket Support**: Real-time event streaming  

## Authentication

Currently, the Dashboard API does not implement authentication. All endpoints are accessible without authorization headers.

**Note**: Authentication features are planned for future releases.

## Core Endpoints

### Health and Status

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-16T10:30:00Z",
  "services": {
    "collector": "healthy",
    "policy_engine": "healthy",
    "fl_server": "degraded"
  },
  "uptime": 7200
}
```

### Overview Dashboard

#### Get FL Status
```http
GET /overview/fl-status
```

**Response:**
```json
{
  "round": 5,
  "clients_connected": 2,
  "clients_total": 2,
  "accuracy": 87.5,
  "loss": 0.23,
  "status": "active",
  "max_rounds": 10
}
```

#### Get Network Status
```http
GET /overview/network-status
```

**Response:**
```json
{
  "switches": 3,
  "hosts": 8,
  "active_flows": 45,
  "utilization": 38.5,
  "status": "operational"
}
```

#### Get Policy Status
```http
GET /overview/policy-status
```

**Response:**
```json
{
  "active_policies": 15,
  "policy_checks_total": 2450,
  "policy_checks_allowed": 2200,
  "policy_checks_denied": 250,
  "status": "operational"
}
```

### FL Monitoring

#### Get FL Metrics
```http
GET /fl-monitoring/metrics
```

**Query Parameters:**
- `limit` (optional): Number of metrics to return (default: 100)
- `offset` (optional): Pagination offset
- `start_round` (optional): Filter from round number
- `end_round` (optional): Filter to round number

**Response:**
```json
{
  "metrics": [
    {
      "round": 5,
      "accuracy": 0.87,
      "loss": 0.23,
      "training_duration": 45.2,
      "clients": 2,
      "timestamp": "2025-01-16T10:30:00Z"
    }
  ],
  "total_count": 50,
  "pagination": {
    "limit": 100,
    "offset": 0,
    "has_more": false
  }
}
```

#### Get FL Latest Round
```http
GET /fl-monitoring/latest
```

**Response:**
```json
{
  "round": 5,
  "accuracy": 87.5,
  "loss": 0.23,
  "training_duration": 45.2,
  "clients_connected": 2,
  "timestamp": "2025-01-16T10:30:00Z",
  "status": "completed"
}
```
}
```

### Get Experiment Details

```http
GET /experiments/{experiment_id}
```

**Response:**
```json
{
  "experiment": {
    "id": "exp_001",
    "name": "MNIST Federated Learning",
    "status": "running",
    "configuration": {
      "dataset": "mnist",
      "model": "cnn",
      "rounds": 20,
      "clients_per_round": 3,
      "local_epochs": 5,
      "learning_rate": 0.01,
      "batch_size": 32
    },
    "metrics": {
      "current_round": 12,
      "global_accuracy": 0.89,
      "global_loss": 0.34,
      "convergence_rate": 0.02,
      "communication_overhead": "45MB"
    },
    "clients": [
      {
        "id": "client_001",
        "status": "training",
        "accuracy": 0.87,
        "loss": 0.38,
        "last_update": "2024-01-15T10:15:00Z"
      }
    ],
    "timeline": [
      {
        "timestamp": "2024-01-15T10:05:00Z",
        "event": "experiment_started",
        "details": "Experiment started with 5 clients"
      }
    ]
  }
}
```

### Control Experiment

```http
POST /experiments/{experiment_id}/control
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "pause", // "start", "pause", "resume", "stop", "abort"
  "reason": "Network maintenance scheduled"
}
```

**Response:**
```json
{
  "status": "paused",
  "message": "Experiment paused successfully",
  "timestamp": "2024-01-15T10:20:00Z"
}
```

## Real-time Metrics

### Get Live Metrics

```http
GET /metrics/live
```

**Query Parameters:**
- `services`: Comma-separated list of services (fl_server,collector,policy_engine,sdn)
- `metrics`: Comma-separated list of metric types (cpu,memory,network,custom)
- `interval`: Update interval in seconds (default: 5)

**Response:**
```json
{
  "timestamp": "2024-01-15T10:25:00Z",
  "services": {
    "fl_server": {
      "status": "healthy",
      "cpu_usage": 45.2,
      "memory_usage": 512.5,
      "active_clients": 5,
      "current_round": 12,
      "throughput": "15MB/s"
    },
    "collector": {
      "status": "healthy",
      "cpu_usage": 23.1,
      "memory_usage": 256.8,
      "metrics_processed": 1250,
      "queue_size": 45
    }
  }
}
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:3001/ws/dashboard');

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    
    switch(update.type) {
        case 'experiment_update':
            console.log('Experiment update:', update.data);
            break;
        case 'metrics_update':
            console.log('Metrics update:', update.data);
            break;
        case 'alert':
            console.log('Alert:', update.data);
            break;
    }
};

// Subscribe to specific updates
ws.send(JSON.stringify({
    action: 'subscribe',
    topics: ['experiments', 'metrics', 'alerts'],
    experiment_ids: ['exp_001', 'exp_002']
}));
```

## Service Health

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "2d 4h 15m 30s",
  "services": {
    "collector": {
      "status": "healthy",
      "response_time": "5ms",
      "last_check": "2024-01-15T10:25:00Z"
    },
    "policy_engine": {
      "status": "healthy",
      "response_time": "12ms",
      "last_check": "2024-01-15T10:25:00Z"
    },
    "fl_server": {
      "status": "degraded",
      "response_time": "150ms",
      "last_check": "2024-01-15T10:25:00Z",
      "issues": ["High memory usage: 85%"]
    }
  }
}
```

### Service Dependencies

```http
GET /health/dependencies
```

**Response:**
```json
{
  "dependencies": {
    "influxdb": {
      "status": "connected",
      "response_time": "8ms",
      "version": "2.6.0"
    },
    "redis": {
      "status": "connected",
      "response_time": "2ms",
      "version": "7.0.5"
    },
    "mongodb": {
      "status": "connected",
      "response_time": "15ms",
      "version": "6.0.2"
    }
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
  "dashboard": {
    "refresh_interval": 5000,
    "max_experiments": 10,
    "retention_days": 30
  },
  "features": {
    "real_time_metrics": true,
    "experiment_scheduling": true,
    "alert_notifications": true
  },
  "integration": {
    "collector_url": "http://localhost:8081",
    "policy_engine_url": "http://localhost:5000",
    "fl_server_url": "http://localhost:8080"
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
  "dashboard": {
    "refresh_interval": 3000,
    "max_experiments": 15
  }
}
```

## Alerts and Notifications

### List Alerts

```http
GET /alerts
```

**Query Parameters:**
- `severity`: critical, warning, info
- `status`: active, resolved, acknowledged
- `from`: Start date (ISO 8601)
- `to`: End date (ISO 8601)

**Response:**
```json
{
  "alerts": [
    {
      "id": "alert_001",
      "severity": "warning",
      "status": "active",
      "title": "High Memory Usage",
      "description": "FL Server memory usage exceeded 80% threshold",
      "service": "fl_server",
      "experiment_id": "exp_001",
      "created_at": "2024-01-15T10:20:00Z",
      "threshold": 80,
      "current_value": 85.2
    }
  ]
}
```

### Acknowledge Alert

```http
POST /alerts/{alert_id}/acknowledge
Content-Type: application/json
```

**Request Body:**
```json
{
  "comment": "Investigating high memory usage"
}
```

## Error Responses

### Validation Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid experiment configuration",
    "details": {
      "rounds": "Must be between 1 and 100",
      "clients_per_round": "Must be greater than 0"
    }
  }
}
```

### Service Unavailable

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "FL Server is currently unavailable",
    "retry_after": 30
  }
}
```

## Rate Limiting

The Dashboard API implements rate limiting:

- **Standard endpoints**: 1000 requests/hour
- **Real-time metrics**: 5000 requests/hour
- **WebSocket connections**: 10 concurrent connections

Rate limit headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1705315200
```

## SDK Example

```python
from flopy_net_client import DashboardClient

# Initialize client
client = DashboardClient(
    base_url="http://localhost:3001/api/v1",
    api_key="your_api_key"
)

# Create experiment
experiment = client.experiments.create({
    "name": "Python SDK Test",
    "scenario": "basic_fl",
    "configuration": {
        "dataset": "mnist",
        "rounds": 10,
        "clients_per_round": 3
    }
})

# Monitor experiment
for update in client.experiments.monitor(experiment.id):
    print(f"Round {update.current_round}: Accuracy {update.accuracy}")
    if update.status == "completed":
        break
```
