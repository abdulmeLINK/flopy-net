# FL Framework API

The FL Framework in FLOPY-NET is based on the Flower federated learning framework and provides both gRPC communication (for FL training) and REST APIs (for monitoring and management). The FL Server runs an internal Flask metrics server alongside the Flower gRPC server.

## Architecture Overview

FLOPY-NET's FL implementation consists of:

- **FL Server**: Coordinates federated learning using Flower's custom `MetricsTrackingStrategy`
- **FL Clients**: Participate in training using Flower's ClientApp with `ModelHandler`
- **Policy Integration**: Policy Engine controls FL operations via real-time policy checks
- **Metrics Collection**: Both internal Flask server and external Collector service monitor FL progress
- **Persistent Storage**: SQLite database stores training rounds and metrics

## FL Server Implementation

The FL Server (`src/fl/server/fl_server.py`) combines Flower's gRPC server with a Flask metrics API:

### Docker Configuration
```yaml
environment:
  - SERVICE_TYPE=fl-server
  - SERVICE_VERSION=v1.0.0-alpha.8
  - HOST=0.0.0.0
  - FL_SERVER_PORT=8080        # Flower gRPC port
  - METRICS_PORT=9091          # Environment variable (not used by FL server)
  # Note: FL Server reads metrics_port from config/server_config.json (default: 8081)
  - POLICY_ENGINE_HOST=policy-engine
  - POLICY_ENGINE_PORT=5000
  - MIN_CLIENTS=1
  - MIN_AVAILABLE_CLIENTS=1
  - LOG_LEVEL=INFO
  - USE_STATIC_IP=true
```

### Key Environment Variables
- `FL_SERVER_PORT`: Port for Flower gRPC communication (default: 8080)
- `METRICS_PORT`: Environment variable set to 9091 (not used by FL server)
- **Note**: FL Server reads `metrics_port` from `config/server_config.json` (actual port: 8081)
- `MIN_CLIENTS`: Minimum clients required for training rounds
- `MIN_AVAILABLE_CLIENTS`: Minimum clients that must be available
- `POLICY_ENGINE_HOST`: Hostname of the Policy Engine service
- `POLICY_ENGINE_PORT`: Port of the Policy Engine service
- `HOST`: Server bind address (0.0.0.0 for all interfaces)

### Internal Components

**MetricsTrackingStrategy**: Custom Flower strategy that:
- Tracks detailed training metrics in `global_metrics` dictionary
- Integrates policy checks for every training round
- Stores round data in persistent SQLite storage via `FLRoundStorage`
- Supports training pause/resume based on policy decisions

**Flask Metrics Server**: Internal REST API running on port **8081** (from config file):
- `/metrics` - Current training metrics and status
- `/rounds` - Persistent training rounds with filtering
- `/events` - Training events from event buffer
- `/health` - Health check endpoint
- `/restart` - Manual training restart (POST)

## FL Client Implementation  

FL Clients (`src/fl/client/fl_client.py`) connect via Flower gRPC and use ModelHandler:

### Docker Configuration
```yaml
environment:
  - SERVICE_TYPE=fl-client
  - SERVICE_VERSION=v1.0.0-alpha.8
  - CLIENT_ID=client-1
  - SERVER_HOST=fl-server        # FL Server hostname
  - POLICY_ENGINE_HOST=policy-engine
  - MAX_RECONNECT_ATTEMPTS=-1    # Infinite reconnection
  - RETRY_INTERVAL=5             # 5 seconds between attempts
  - MAX_RETRIES=30
  - LOG_LEVEL=INFO
```

### Key Environment Variables
- `CLIENT_ID`: Unique identifier for the client (e.g., "client-1", "client-2")
- `SERVER_HOST`: Hostname of the FL Server for gRPC connection
- `POLICY_ENGINE_HOST`: Policy Engine hostname for policy checks
- `MAX_RECONNECT_ATTEMPTS`: Reconnection attempts (-1 for infinite)
- `RETRY_INTERVAL`: Seconds between reconnection attempts
- `MAX_RETRIES`: Maximum retries for operations

### ModelHandler Integration

Each client uses `ModelHandler` from `src/fl/common/model_handler.py`:
- **Dynamic Model Loading**: Loads models from configurable modules
- **Training Simulation**: Realistic training metrics progression
- **Policy Integration**: Checks policies before local training
- **Error Handling**: Raises `ConfigurationError` for invalid setups

## FL Server REST API

The FL Server runs an internal Flask server providing REST endpoints for monitoring and management.

**Base URL**: `http://fl-server:8081` (internal) or `http://localhost:8081` (external)

### Server Status and Health

#### Get Server Status
```http
GET /
```

**Response:**
```json
{
  "status": "running",
  "endpoints": ["/health", "/metrics", "/events"]
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
  "timestamp": 1703596200.0
}
```

### Training Metrics

#### Get Current Metrics
```http
GET /metrics
```

**Query Parameters:**
- `include_rounds` (optional): Include historical rounds data (`true`/`false`)

**Response:**
```json
{
  "start_time": 1703596000.0,
  "current_round": 5,
  "connected_clients": 2,
  "aggregate_fit_count": 10,
  "aggregate_evaluate_count": 10,
  "last_round_metrics": {
    "accuracy": 0.87,
    "loss": 0.23,
    "fit_duration": 45.2,
    "evaluate_duration": 12.1
  },
  "policy_checks_performed": 25,
  "policy_checks_allowed": 23,
  "policy_checks_denied": 2,
  "training_complete": false,
  "training_end_time": null,
  "total_training_duration": 180.5,
  "data_state": "training",
  "model_size_mb": 2.1,
  "max_rounds": 10,
  "training_active": true
}
```

### Persistent Training Rounds

#### Get Training Rounds
```http
GET /rounds
```

**Query Parameters:**
- `start_round` (optional): Start round number (default: 1)
- `end_round` (optional): End round number (default: all)
- `limit` (optional): Maximum rounds to return (default: 1000, max: 10000)
- `offset` (optional): Number of rounds to skip (default: 0)
- `min_accuracy` (optional): Minimum accuracy filter
- `max_accuracy` (optional): Maximum accuracy filter

**Response:**
```json
{
  "rounds": [
    {
      "round": 1,
      "timestamp": "2025-01-16T10:30:00.000Z",
      "status": "complete",
      "accuracy": 0.75,
      "loss": 0.45,
      "training_duration": 42.1,
      "model_size_mb": 2.1,
      "clients": 2,
      "raw_metrics": {
        "fit_metrics": {"accuracy": 0.75, "loss": 0.45},
        "evaluate_metrics": {"accuracy": 0.73, "loss": 0.48}
      }
    }
  ],
  "total_rounds": 5,
  "returned_rounds": 1,
  "latest_round": 5,
  "pagination": {
    "limit": 1000,
    "offset": 0,
    "has_more": false
  },
  "filters": {
    "start_round": 1,
    "end_round": null,
    "min_accuracy": null,
    "max_accuracy": null
  }
}
```

#### Get Latest Rounds
```http
GET /rounds/latest
```

**Query Parameters:**
- `limit` (optional): Number of latest rounds (default: 50, max: 1000)

**Response:**
```json
{
  "rounds": [/* latest rounds array */],
  "latest_round": 5,
  "returned_rounds": 5
}
```

### Training Events

#### Get Training Events
```http
GET /events
```

**Query Parameters:**
- `since_event_id` (optional): Get events after this event ID
- `limit` (optional): Maximum events to return (default: 1000)

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "ROUND_START",
      "timestamp": 1703596200.0,
      "data": {
        "round": 1,
        "selected_clients": 2,
        "server_id": "fl-server"
      }
    },
    {
      "event_id": "evt_002", 
      "event_type": "TRAINING_PAUSED_BY_POLICY",
      "timestamp": 1703596250.0,
      "data": {
        "round": 2,
        "reason": "Training window closed",
        "policy_type": "fl_client_training"
      }
    }
  ],
  "last_event_id": "evt_002"
}
```

### Training Management

#### Restart Training
```http
POST /restart
```

Manually restart training if stopped by policy or completed.

**Response:**
```json
{
  "success": true,
  "message": "Training restarted successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "Training cannot be restarted. Current round: 10, Max rounds: 10, Training active: false"
}
```

## Collector API Integration

The Collector service (`src/collector/api/server.py`) provides comprehensive FL monitoring through event-based collection from the FL Server.

**Base URL**: `http://collector:8000` (internal) or `http://localhost:8000` (external)

### Collector FL Endpoints

#### Get FL Training Status
```http
GET /api/metrics/fl/status
```

**Response:**
```json
{
  "status": "training",
  "current_round": 5,
  "max_rounds": 10,
  "accuracy": 0.87,
  "loss": 0.23,
  "clients_connected": 2,
  "training_duration": 180.5,
  "data_state": "training",
  "last_updated": "2025-01-16T10:30:00Z"
}
```

#### Get FL Metrics
```http
GET /api/metrics/fl
```

**Query Parameters:**
- `rounds_only` (optional): Return only rounds data (`true`/`false`)
- `include_raw` (optional): Include raw metrics (`true`/`false`)
- `start_round` (optional): Filter from round number
- `end_round` (optional): Filter to round number

**Response:**
```json
{
  "current_metrics": {
    "round": 5,
    "accuracy": 0.87,
    "loss": 0.23,
    "training_duration": 180.5,
    "model_size_mb": 2.1,
    "clients_connected": 2
  },
  "rounds": [
    {
      "round": 1,
      "accuracy": 0.65,
      "loss": 0.55,
      "timestamp": "2025-01-16T10:25:00Z",
      "training_duration": 35.2,
      "clients": 2
    }
  ],
  "summary": {
    "total_rounds": 5,
    "best_accuracy": 0.87,
    "worst_accuracy": 0.65,
    "average_round_duration": 36.1,
    "training_complete": false
  }
}
```

#### Get FL Rounds
```http  
GET /api/metrics/fl/rounds
```

**Query Parameters:**
- `limit` (optional): Maximum rounds to return
- `offset` (optional): Skip number of rounds
- `min_accuracy` (optional): Minimum accuracy filter
- `format` (optional): Response format (`json`, `csv`)

**Response:**
```json
{
  "rounds": [/* FL rounds array */],
  "total_count": 5,
  "filters": {
    "min_accuracy": null,
    "limit": 1000,
    "offset": 0
  },
  "metadata": {
    "collection_method": "event_based",
    "last_updated": "2025-01-16T10:30:00Z",
    "data_source": "fl_server_events"
  }
}
```

#### Get FL Configuration  
```http
GET /api/metrics/fl/config
```

**Response:**
```json
{
  "server_config": {
    "min_clients": 1,
    "min_available_clients": 1,
    "max_rounds": 10,
    "fl_server_port": 8080,
    "metrics_port": 9091
  },
  "client_config": {
    "total_clients": 2,
    "active_clients": 2,
    "client_ids": ["client-1", "client-2"],
    "reconnect_attempts": -1,
    "retry_interval": 5
  },
  "policy_integration": {
    "policy_engine_enabled": true,
    "policy_checks_performed": 25,
    "policy_checks_allowed": 23,
    "policy_checks_denied": 2
  }
}
```

## Policy Engine Integration

The FL Server integrates with the Policy Engine for real-time governance:

### Policy Check Types

**fl_client_training**: Controls when training rounds can execute
```python
policy_context = {
    "operation": "model_training",
    "server_id": "default-server",  
    "current_round": 5,
    "current_hour": 14,  # Dynamic time check
    "available_clients": 2,
    "model": "cnn",
    "dataset": "cifar10"
}
```

**fl_server_control**: Controls server behavior and round limits
```python
policy_context = {
    "operation": "decide_next_round",
    "current_round": 5,
    "max_rounds": 10,
    "accuracy": 0.87,
    "accuracy_improvement": 0.05,
    "available_clients": 2
}
```

**fl_training_parameters**: Sets training configuration
```python  
policy_context = {
    "operation": "training_configuration",
    "server_id": "default-server",
    "model": "cnn", 
    "dataset": "cifar10"
}
```

### Policy Integration Flow

1. **Round Start**: Server checks `fl_client_training` policy before each round
2. **Training Pause**: If policy denies, training pauses and rechecks every 10 seconds  
3. **Parameter Updates**: Policy can modify `total_rounds` and `max_rounds` dynamically
4. **Event Logging**: All policy decisions logged to event system

### Policy Response Handling

**Allowed Training:**
```json
{
  "allowed": true,
  "reason": "Training permitted during business hours",
  "parameters": {
    "total_rounds": 15
  }
}
```

**Denied Training:**
```json
{
  "allowed": false, 
  "reason": "Training blocked outside business hours (current: 22:30)",
  "retry_after": 600
}
```

## Flower Framework Implementation

### Server Strategy (MetricsTrackingStrategy)

The FL Server uses a custom `MetricsTrackingStrategy` extending Flower's `FedAvg`:

**Key Features:**
- **Policy Integration**: Checks policies before every training round
- **Metrics Tracking**: Updates `global_metrics` dictionary with training progress
- **Event Logging**: Logs all training events to event buffer
- **Persistent Storage**: Stores round data in SQLite via `FLRoundStorage`
- **Training Control**: Supports pause/resume based on policy decisions

**Policy Check Flow:**
1. Before each round, checks `fl_client_training` policy
2. If denied, pauses training and logs `TRAINING_PAUSED_BY_POLICY` event
3. Rechecks policy every 10 seconds until allowed
4. Resumes training and logs `TRAINING_RESUMED` event

### Client Implementation (FlowerClient)

FL Clients use custom `FlowerClient` class with `ModelHandler`:

**Key Features:**
- **ModelHandler Integration**: Dynamic model loading and training simulation
- **Policy Checks**: Validates policies before local training
- **Realistic Metrics**: Progressive accuracy improvement over rounds
- **Error Handling**: Graceful handling of model loading failures
- **Reconnection Logic**: Automatic reconnection with configurable retry logic

### Communication Protocol

**gRPC Communication**: Flower's standard gRPC protocol for FL
- Port: 8080 (FL_SERVER_PORT)
- Protocol: HTTP/2 with protobuf serialization
- Security: Policy-based access control

**REST API Communication**: Flask server for monitoring
- Port: 9091 (METRICS_PORT) 
- Protocol: HTTP/1.1 with JSON
- Security: Internal service communication

## Configuration Guide

### Complete Docker Compose Example

```yaml
version: '3.8'

services:
  fl-server:
    image: abdulmelink/flopynet-server:v1.0.0-alpha.8
    container_name: fl-server
    environment:
      - SERVICE_TYPE=fl-server
      - SERVICE_VERSION=v1.0.0-alpha.8
      - HOST=0.0.0.0
      - FL_SERVER_PORT=8080
      - METRICS_PORT=9091
      - POLICY_ENGINE_HOST=policy-engine
      - POLICY_ENGINE_PORT=5000
      - MIN_CLIENTS=1
      - MIN_AVAILABLE_CLIENTS=1
      - LOG_LEVEL=INFO
      - USE_STATIC_IP=true
    networks:
      flopynet_network:
        ipv4_address: 192.168.100.10
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      policy-engine:
        condition: service_healthy

  fl-client-1:
    image: abdulmelink/flopynet-client:v1.0.0-alpha.8
    container_name: fl-client-1
    environment:
      - SERVICE_TYPE=fl-client
      - SERVICE_VERSION=v1.0.0-alpha.8
      - CLIENT_ID=client-1
      - SERVER_HOST=fl-server
      - POLICY_ENGINE_HOST=policy-engine
      - MAX_RECONNECT_ATTEMPTS=-1
      - RETRY_INTERVAL=5
      - MAX_RETRIES=30
      - LOG_LEVEL=INFO
    networks:
      flopynet_network:
        ipv4_address: 192.168.100.101
    depends_on:
      fl-server:
        condition: service_healthy

  fl-client-2:
    image: abdulmelink/flopynet-client:v1.0.0-alpha.8
    container_name: fl-client-2
    environment:
      - SERVICE_TYPE=fl-client
      - SERVICE_VERSION=v1.0.0-alpha.8
      - CLIENT_ID=client-2
      - SERVER_HOST=fl-server
      - POLICY_ENGINE_HOST=policy-engine
      - MAX_RECONNECT_ATTEMPTS=-1
      - RETRY_INTERVAL=5
      - MAX_RETRIES=30
      - LOG_LEVEL=INFO
    networks:
      flopynet_network:
        ipv4_address: 192.168.100.102
    depends_on:
      fl-server:
        condition: service_healthy

  policy-engine:
    image: abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8
    container_name: policy-engine
    environment:
      - SERVICE_TYPE=policy-engine
      - POLICY_PORT=5000
      - LOG_LEVEL=INFO
    networks:
      flopynet_network:
        ipv4_address: 192.168.100.20
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  collector:
    image: abdulmelink/flopynet-collector:v1.0.0-alpha.8
    container_name: collector
    environment:
      - SERVICE_TYPE=collector
      - METRICS_API_PORT=8000
      - FL_SERVER_HOST=fl-server
      - FL_SERVER_METRICS_PORT=9091
      - POLICY_ENGINE_HOST=policy-engine
      - FL_MONITOR_ENABLED=true
      - COLLECTION_INTERVAL=30
    networks:
      flopynet_network:
        ipv4_address: 192.168.100.40
    depends_on:
      - fl-server
      - policy-engine

networks:
  flopynet_network:
    driver: bridge
    ipam:
      config:
        - subnet: 192.168.100.0/24
```

### Environment Variables Reference

#### FL Server Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_TYPE` | - | Must be "fl-server" |
| `HOST` | 0.0.0.0 | Server bind address |  
| `FL_SERVER_PORT` | 8080 | Flower gRPC port |
| `METRICS_PORT` | 9091 | Flask metrics API port |
| `MIN_CLIENTS` | 1 | Minimum clients for training |
| `MIN_AVAILABLE_CLIENTS` | 1 | Minimum available clients |
| `POLICY_ENGINE_HOST` | - | Policy Engine hostname |
| `POLICY_ENGINE_PORT` | 5000 | Policy Engine port |
| `LOG_LEVEL` | INFO | Logging level |

#### FL Client Variables  
| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_TYPE` | - | Must be "fl-client" |
| `CLIENT_ID` | - | Unique client identifier |
| `SERVER_HOST` | - | FL Server hostname |
| `POLICY_ENGINE_HOST` | - | Policy Engine hostname |
| `MAX_RECONNECT_ATTEMPTS` | -1 | Reconnection attempts (-1 = infinite) |
| `RETRY_INTERVAL` | 5 | Seconds between reconnection attempts |
| `MAX_RETRIES` | 30 | Maximum operation retries |
| `LOG_LEVEL` | INFO | Logging level |

## How to Start FL Training

### Method 1: Using Docker Compose (Recommended)

```bash
# Navigate to the FLOPY-NET directory
cd d:\dev\microfed\codebase

# Start all services including FL components
docker-compose up -d

# Check that FL services are running
docker-compose ps | grep fl-

# View FL server logs
docker-compose logs -f fl-server

# View FL client logs  
docker-compose logs -f fl-client-1
```

### Method 2: Using Docker Compose (Recommended)

```bash
# Start all components together
docker-compose up -d

# Or start specific components
docker-compose up fl-server fl-client-1 fl-client-2
```

### Method 3: Using Scenario Execution

```bash
# Run a complete simulation scenario
python -m src.scenarios.run_scenario --scenario config/scenarios/basic_main.json
```

### Method 4: Direct Python Execution

**Start FL Server:**
```bash
cd src/fl/server
python fl_server.py --host 0.0.0.0 --port 8080 --policy-engine-host policy-engine
```

**Start FL Clients:**
```bash
cd src/fl/client  
python fl_client.py --client-id client-1 --server-host fl-server --server-port 8080
python fl_client.py --client-id client-2 --server-host fl-server --server-port 8080
```
