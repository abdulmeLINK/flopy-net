# FL Framework API

The FL Framework provides REST APIs for managing federated learning experiments, including client registration, training coordination, and model management.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

Currently, the FL Framework uses basic authentication or API keys for securing endpoints. Include the authentication header in all requests:

```http
Authorization: Bearer <api-key>
```

## Core Endpoints

### Server Status

#### Get Server Status
```http
GET /status
```

**Description**: Get current FL server status and configuration.

**Response:**
```json
{
  "status": "running",
  "version": "1.0.0",
  "current_round": 5,
  "total_rounds": 10,
  "active_clients": 8,
  "registered_clients": 12,
  "experiment_id": "exp_2025_001",
  "model_config": {
    "architecture": "CNN",
    "dataset": "CIFAR-10",
    "batch_size": 32
  },
  "training_config": {
    "rounds": 10,
    "min_clients": 5,
    "client_fraction": 0.8,
    "local_epochs": 3
  },
  "timestamp": "2025-01-16T10:30:00Z"
}
```

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:30:00Z",
  "uptime": 3600,
  "memory_usage": "512MB",
  "cpu_usage": "25%"
}
```

### Client Management

#### Register Client
```http
POST /clients/register
```

**Request Body:**
```json
{
  "client_id": "client-001",
  "client_config": {
    "batch_size": 32,
    "local_epochs": 3,
    "learning_rate": 0.01
  },
  "capabilities": {
    "compute_power": "high",
    "memory": "8GB",
    "network_bandwidth": "100Mbps"
  },
  "location": {
    "ip_address": "192.168.141.100",
    "region": "us-east-1"
  }
}
```

**Response:**
```json
{
  "client_id": "client-001",
  "registration_id": "reg_12345",
  "status": "registered",
  "assigned_round": 1,
  "client_config": {
    "batch_size": 32,
    "local_epochs": 3,
    "learning_rate": 0.01
  },
  "timestamp": "2025-01-16T10:30:00Z"
}
```

#### Get Client Status
```http
GET /clients/{client_id}
```

**Response:**
```json
{
  "client_id": "client-001",
  "status": "active",
  "current_round": 5,
  "last_update": "2025-01-16T10:28:30Z",
  "performance_metrics": {
    "local_accuracy": 0.78,
    "training_time": 45.2,
    "communication_time": 3.1,
    "data_size": 1000
  },
  "trust_score": 0.95,
  "contribution_score": 0.87
}
```

#### List All Clients
```http
GET /clients
```

**Query Parameters:**
- `status` (optional): Filter by client status (`active`, `inactive`, `registered`)
- `round` (optional): Filter by specific round participation

**Response:**
```json
{
  "clients": [
    {
      "client_id": "client-001",
      "status": "active",
      "current_round": 5,
      "trust_score": 0.95
    },
    {
      "client_id": "client-002", 
      "status": "inactive",
      "current_round": 4,
      "trust_score": 0.82
    }
  ],
  "total_count": 12,
  "active_count": 8,
  "timestamp": "2025-01-16T10:30:00Z"
}
```

### Training Management

#### Start Training
```http
POST /training/start
```

**Request Body:**
```json
{
  "experiment_config": {
    "experiment_id": "exp_2025_001",
    "rounds": 10,
    "min_clients": 5,
    "client_fraction": 0.8,
    "dataset": "CIFAR-10",
    "model_architecture": "CNN"
  },
  "training_config": {
    "local_epochs": 3,
    "batch_size": 32,
    "learning_rate": 0.01,
    "optimizer": "SGD"
  },
  "aggregation_config": {
    "strategy": "FedAvg",
    "weighted": true,
    "min_updates": 5
  }
}
```

**Response:**
```json
{
  "experiment_id": "exp_2025_001",
  "status": "started",
  "start_time": "2025-01-16T10:30:00Z",
  "total_rounds": 10,
  "current_round": 1,
  "selected_clients": ["client-001", "client-003", "client-007"],
  "estimated_duration": "45 minutes"
}
```

#### Stop Training
```http
POST /training/stop
```

**Request Body:**
```json
{
  "experiment_id": "exp_2025_001",
  "reason": "manual_stop"
}
```

#### Get Training Status
```http
GET /training/status
```

**Response:**
```json
{
  "experiment_id": "exp_2025_001",
  "status": "running",
  "current_round": 5,
  "total_rounds": 10,
  "progress": 0.5,
  "start_time": "2025-01-16T09:30:00Z",
  "estimated_completion": "2025-01-16T10:15:00Z",
  "selected_clients": ["client-001", "client-003", "client-007"],
  "round_metrics": {
    "accuracy": 0.78,
    "loss": 0.45,
    "round_duration": 120,
    "participating_clients": 8
  }
}
```

### Model Management

#### Get Global Model
```http
GET /model/global
```

**Query Parameters:**
- `round` (optional): Specific round number (default: latest)
- `format` (optional): Model format (`pytorch`, `tensorflow`, `onnx`)

**Response:**
```json
{
  "model_id": "model_exp_2025_001_round_5",
  "round": 5,
  "accuracy": 0.78,
  "loss": 0.45,
  "parameters_count": 1234567,
  "model_size_mb": 45.2,
  "created_at": "2025-01-16T10:25:00Z",
  "download_url": "/model/download/model_exp_2025_001_round_5"
}
```

#### Download Model
```http
GET /model/download/{model_id}
```

**Response**: Binary model file

#### Upload Model Update
```http
POST /model/update/{client_id}
```

**Content-Type**: `multipart/form-data`

**Form Data:**
- `model_file`: Binary model file
- `metrics`: JSON string with training metrics

**Example metrics:**
```json
{
  "local_accuracy": 0.82,
  "local_loss": 0.35,
  "training_time": 45.2,
  "data_samples": 1000,
  "epochs_completed": 3
}
```

**Response:**
```json
{
  "update_id": "update_12345",
  "client_id": "client-001",
  "round": 5,
  "status": "received",
  "model_size_mb": 45.2,
  "received_at": "2025-01-16T10:28:00Z",
  "validation_status": "pending"
}
```

### Metrics and Monitoring

#### Get Training Metrics
```http
GET /metrics/training
```

**Query Parameters:**
- `experiment_id` (optional): Filter by experiment
- `from_round` (optional): Start round
- `to_round` (optional): End round
- `client_id` (optional): Filter by specific client

**Response:**
```json
{
  "experiment_id": "exp_2025_001",
  "rounds": [
    {
      "round": 1,
      "global_accuracy": 0.45,
      "global_loss": 0.89,
      "participating_clients": 8,
      "round_duration": 125,
      "aggregation_time": 5.2,
      "client_metrics": {
        "client-001": {
          "local_accuracy": 0.48,
          "local_loss": 0.85,
          "training_time": 42.1,
          "data_samples": 1000
        }
      }
    }
  ],
  "summary": {
    "total_rounds": 5,
    "best_accuracy": 0.78,
    "convergence_rate": 0.12,
    "avg_round_duration": 120
  }
}
```

#### Get Client Performance
```http
GET /metrics/clients/{client_id}
```

**Response:**
```json
{
  "client_id": "client-001",
  "performance_history": [
    {
      "round": 1,
      "local_accuracy": 0.48,
      "training_time": 42.1,
      "communication_time": 3.2
    }
  ],
  "statistics": {
    "avg_accuracy": 0.76,
    "avg_training_time": 43.5,
    "total_rounds_participated": 5,
    "reliability_score": 0.95,
    "contribution_score": 0.87
  }
}
```

### Experiment Management

#### Create Experiment
```http
POST /experiments
```

**Request Body:**
```json
{
  "name": "CIFAR-10 CNN Experiment",
  "description": "Federated learning experiment with CNN on CIFAR-10",
  "dataset_config": {
    "name": "CIFAR-10",
    "split_strategy": "iid",
    "clients_count": 10
  },
  "model_config": {
    "architecture": "CNN",
    "input_shape": [32, 32, 3],
    "num_classes": 10
  },
  "training_config": {
    "rounds": 10,
    "local_epochs": 3,
    "batch_size": 32,
    "learning_rate": 0.01
  },
  "policy_config": {
    "min_clients": 5,
    "max_client_failures": 2,
    "trust_threshold": 0.7
  }
}
```

**Response:**
```json
{
  "experiment_id": "exp_2025_001",
  "name": "CIFAR-10 CNN Experiment",
  "status": "created",
  "created_at": "2025-01-16T10:30:00Z",
  "estimated_duration": "45 minutes",
  "resource_requirements": {
    "min_clients": 5,
    "estimated_compute": "high",
    "network_bandwidth": "100Mbps"
  }
}
```

#### List Experiments
```http
GET /experiments
```

**Query Parameters:**
- `status` (optional): Filter by status (`created`, `running`, `completed`, `failed`)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "experiments": [
    {
      "experiment_id": "exp_2025_001",
      "name": "CIFAR-10 CNN Experiment",
      "status": "running",
      "created_at": "2025-01-16T09:30:00Z",
      "progress": 0.5
    }
  ],
  "total_count": 15,
  "has_more": true
}
```

### WebSocket Events

The FL Framework provides real-time updates via WebSocket connections:

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:8080/ws/events');
```

#### Event Types

**Training Progress**
```json
{
  "type": "training_progress",
  "experiment_id": "exp_2025_001",
  "round": 5,
  "progress": 0.5,
  "metrics": {
    "accuracy": 0.78,
    "loss": 0.45
  },
  "timestamp": "2025-01-16T10:30:00Z"
}
```

**Client Update**
```json
{
  "type": "client_update",
  "client_id": "client-001",
  "status": "training_completed",
  "round": 5,
  "metrics": {
    "local_accuracy": 0.82,
    "training_time": 45.2
  },
  "timestamp": "2025-01-16T10:28:00Z"
}
```

**Round Completion**
```json
{
  "type": "round_completed",
  "experiment_id": "exp_2025_001",
  "round": 5,
  "global_metrics": {
    "accuracy": 0.78,
    "loss": 0.45
  },
  "participating_clients": 8,
  "round_duration": 120,
  "timestamp": "2025-01-16T10:30:00Z"
}
```

## Error Handling

All API endpoints use standard HTTP status codes and return error details in a consistent format:

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_CLIENT_ID",
    "message": "Client ID not found",
    "details": "The specified client ID 'client-999' is not registered",
    "timestamp": "2025-01-16T10:30:00Z"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource already exists or state conflict |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server internal error |
| 503 | `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

### FL-Specific Error Codes

| Error Code | Description |
|------------|-------------|
| `CLIENT_NOT_REGISTERED` | Client not registered with server |
| `EXPERIMENT_NOT_ACTIVE` | No active experiment running |
| `ROUND_NOT_ACTIVE` | Specified round is not currently active |
| `MODEL_VALIDATION_FAILED` | Uploaded model failed validation |
| `INSUFFICIENT_CLIENTS` | Not enough clients for training |
| `TRAINING_ALREADY_RUNNING` | Cannot start - training already in progress |

## Rate Limiting

The FL Framework implements rate limiting to prevent abuse:

- **General API**: 100 requests per minute per client
- **Model Upload**: 10 uploads per minute per client
- **Training Start**: 5 requests per hour per user
- **WebSocket**: 1 connection per client

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Window reset time (Unix timestamp)

## SDK Examples

### Python Client

```python
import requests
import json

class FLClient:
    def __init__(self, server_url="http://localhost:8080", api_key=None):
        self.base_url = f"{server_url}/api/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else None
        }
    
    def register_client(self, client_id, config):
        """Register a new FL client."""
        payload = {
            "client_id": client_id,
            "client_config": config
        }
        response = requests.post(
            f"{self.base_url}/clients/register",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_training_status(self):
        """Get current training status."""
        response = requests.get(
            f"{self.base_url}/training/status",
            headers=self.headers
        )
        return response.json()
    
    def upload_model_update(self, client_id, model_file, metrics):
        """Upload model update after local training."""
        files = {'model_file': model_file}
        data = {'metrics': json.dumps(metrics)}
        
        response = requests.post(
            f"{self.base_url}/model/update/{client_id}",
            headers={"Authorization": self.headers["Authorization"]},
            files=files,
            data=data
        )
        return response.json()
```

### JavaScript Client

```javascript
class FLAPIClient {
    constructor(serverUrl = 'http://localhost:8080', apiKey = null) {
        this.baseUrl = `${serverUrl}/api/v1`;
        this.headers = {
            'Content-Type': 'application/json',
            ...(apiKey && { 'Authorization': `Bearer ${apiKey}` })
        };
    }
    
    async getServerStatus() {
        const response = await fetch(`${this.baseUrl}/status`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async startTraining(experimentConfig) {
        const response = await fetch(`${this.baseUrl}/training/start`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(experimentConfig)
        });
        return response.json();
    }
    
    async getTrainingMetrics(experimentId) {
        const response = await fetch(
            `${this.baseUrl}/metrics/training?experiment_id=${experimentId}`,
            { headers: this.headers }
        );
        return response.json();
    }
    
    // WebSocket connection for real-time updates
    connectWebSocket() {
        this.ws = new WebSocket('ws://localhost:8080/ws/events');
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
        };
        
        return this.ws;
    }
    
    handleEvent(event) {
        switch (event.type) {
            case 'training_progress':
                console.log('Training progress:', event);
                break;
            case 'client_update':
                console.log('Client update:', event);
                break;
            case 'round_completed':
                console.log('Round completed:', event);
                break;
        }
    }
}
```

## Integration with Policy Engine

The FL Framework integrates with the Policy Engine for governance and security:

### Policy-Aware Client Selection
```http
GET /clients/select?round=5&policy_check=true
```

**Response:**
```json
{
  "selected_clients": ["client-001", "client-003", "client-007"],
  "policy_results": {
    "client-001": {
      "trust_score": 0.95,
      "compliance": true,
      "policies_applied": ["trust_threshold", "resource_requirements"]
    }
  },
  "excluded_clients": ["client-002"],
  "exclusion_reasons": {
    "client-002": "Trust score below threshold (0.65 < 0.70)"
  }
}
```

### Model Validation
```http
POST /model/validate/{client_id}
```

The Policy Engine validates model updates according to configured policies before aggregation.

This comprehensive API reference provides developers with all the information needed to integrate with the FL Framework and build federated learning applications on top of FLOPY-NET.
