# Policy Engine API Reference

The Policy Engine API provides policy management capabilities for federated learning governance, network control, and system compliance monitoring.

## Base URL

```
http://localhost:5000/
```

## Service Information

**Container**: `abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8`  
**Network IP**: `192.168.100.20`  
**Port**: `5000`  
**Technology**: Flask REST API  
**Storage**: SQLite database and JSON files  

## API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "policy-engine",
  "version": "v1.0.0-alpha.8",
  "timestamp": "2025-06-16T10:30:00Z"
}
```

### Root Endpoint

```http
GET /
```

**Response:**
```json
{
  "message": "Policy Engine API",
  "version": "1.0.0"
}
```

## Policy Management

### List All Policies

```http
GET /policies
```

**Response:**
```json
{
  "policies": [
    {
      "id": 1,
      "name": "Client Validation Policy",
      "description": "Validate FL client parameters before allowing participation",
      "rules": [
        {
          "condition": "client_id exists",
          "action": "allow_participation"
        }
      ],
      "enabled": true
    }
  ]
}
```

### Create Policy

```http
POST /policies
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Network Quality Policy",
  "description": "Monitor network quality for FL training",
  "rules": [
    {
      "condition": "latency < 100ms",
      "action": "allow_training"
    },
    {
      "condition": "packet_loss > 5%",
      "action": "pause_training"
    }
  ],
  "enabled": true
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Network Quality Policy",
  "description": "Monitor network quality for FL training",
  "rules": [
    {
      "condition": "latency < 100ms",
      "action": "allow_training"
    },
    {
      "condition": "packet_loss > 5%",
      "action": "pause_training"
    }
  ],  "enabled": true
}
```

## Policy Management

### Create Complex Policy

**Request:**
```http
POST /api/v1/policies
Content-Type: application/json
```

```json
{
  "name": "Adaptive Bandwidth Policy",
  "description": "Dynamically allocate bandwidth based on training performance",
  "rules": [
    {
      "condition": "network_utilization > 70",
      "priority": "high"
    }
  ],
  "actions": [
    {
      "type": "allocate_bandwidth",
      "parameters": {
        "min_bandwidth": "5Mbps",
        "max_bandwidth": "20Mbps",
        "adaptive": true
      }
    },
    {
      "type": "log_event",
      "parameters": {
        "level": "info",
        "message": "Bandwidth allocated for model aggregation"
      }
    }
  ],
  "enabled": true,
  "schedule": {
    "type": "always"
  }
}
```

**Response:**
```json
{
  "policy": {
    "id": "pol_002",
    "name": "Adaptive Bandwidth Allocation",
    "status": "draft",
    "version": 1,
    "created_at": "2024-01-15T11:00:00Z",
    "validation": {
      "valid": true,
      "warnings": [
        "Consider adding fallback action for high network utilization"
      ]
    }
  }
}
```

### Get Policy Details

```http
GET /policies/{policy_id}
```

**Response:**
```json
{
  "policy": {
    "id": "pol_001",
    "name": "FL Traffic Priority",
    "description": "Prioritize federated learning traffic during training rounds",
    "category": "network_qos",
    "status": "active",
    "priority": "high",
    "conditions": [
      {
        "field": "traffic_type",
        "operator": "equals",
        "value": "fl_communication",
        "description": "Match FL communication traffic"
      }
    ],
    "actions": [
      {
        "type": "set_qos_class",
        "parameters": {
          "dscp": "AF41",
          "bandwidth_guarantee": "10Mbps"
        },
        "description": "Apply high-priority QoS marking"
      }
    ],
    "metadata": {
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "version": 2,
      "author": "admin",
      "tags": ["fl", "qos", "priority"]
    },
    "enforcement_stats": {
      "total_enforcements": 156,
      "successful_enforcements": 154,
      "failed_enforcements": 2,
      "last_enforcement": "2024-01-15T10:45:00Z",
      "average_execution_time": "15ms"
    },
    "dependencies": [
      "sdn_controller",
      "fl_server"
    ]
  }
}
```

### Update Policy

```http
PUT /policies/{policy_id}
Content-Type: application/json
```

**Request Body:**
```json
{
  "description": "Updated: Prioritize federated learning traffic with dynamic bandwidth allocation",
  "actions": [
    {
      "type": "set_qos_class",
      "parameters": {
        "dscp": "AF41",
        "bandwidth_guarantee": "15Mbps"
      }
    }
  ]
}
```

### Activate/Deactivate Policy

```http
POST /policies/{policy_id}/activate
POST /policies/{policy_id}/deactivate
```

**Request Body (optional):**
```json
{
  "reason": "Testing updated bandwidth allocation",
  "scheduled_at": "2024-01-15T12:00:00Z"
}
```

### Delete Policy

```http
DELETE /policies/{policy_id}
```

**Query Parameters:**
- `force`: Force deletion even if policy is active

**Response:**
```json
{
  "status": "deleted",
  "policy_id": "pol_002",
  "timestamp": "2024-01-15T11:30:00Z"
}
```

## Policy Evaluation

### Evaluate Policies

```http
POST /policies/evaluate
Content-Type: application/json
```

**Request Body:**
```json
{
  "context": {
    "traffic_type": "fl_communication",
    "experiment_status": "running",
    "experiment_id": "exp_001",
    "client_id": "client_003",
    "network_utilization": 65,
    "fl_training_phase": "local_training",
    "timestamp": "2024-01-15T11:00:00Z"
  },
  "dry_run": false
}
```

**Response:**
```json
{
  "evaluation_id": "eval_abc123",
  "timestamp": "2024-01-15T11:00:01Z",
  "matched_policies": [
    {
      "policy_id": "pol_001",
      "policy_name": "FL Traffic Priority",
      "match_score": 1.0,
      "conditions_met": [
        "traffic_type equals fl_communication",
        "experiment_status in [running, active]"
      ],
      "actions_executed": [
        {
          "type": "set_qos_class",
          "status": "success",
          "execution_time": "12ms",
          "result": {
            "dscp_applied": "AF41",
            "bandwidth_reserved": "10Mbps"
          }
        }
      ]
    }
  ],
  "total_execution_time": "18ms",
  "dry_run": false,
  "warnings": [],
  "errors": []
}
```

### Batch Policy Evaluation

```http
POST /policies/evaluate/batch
Content-Type: application/json
```

**Request Body:**
```json
{
  "evaluations": [
    {
      "id": "eval_001",
      "context": {
        "traffic_type": "fl_communication",
        "experiment_id": "exp_001"
      }
    },
    {
      "id": "eval_002",
      "context": {
        "traffic_type": "general",
        "experiment_id": "exp_001"
      }
    }
  ],
  "dry_run": true
}
```

## Policy Templates

### List Policy Templates

```http
GET /policies/templates
```

**Response:**
```json
{
  "templates": [
    {
      "id": "tpl_fl_priority",
      "name": "FL Traffic Prioritization",
      "description": "Template for prioritizing FL communication traffic",
      "category": "network_qos",
      "parameters": [
        {
          "name": "bandwidth_guarantee",
          "type": "string",
          "default": "10Mbps",
          "description": "Minimum bandwidth guarantee"
        },
        {
          "name": "dscp_marking",
          "type": "string",
          "default": "AF41",
          "options": ["AF41", "AF42", "AF43"],
          "description": "DSCP marking for traffic classification"
        }
      ]
    }
  ]
}
```

### Create Policy from Template

```http
POST /policies/from-template
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_id": "tpl_fl_priority",
  "name": "Custom FL Priority Policy",
  "parameters": {
    "bandwidth_guarantee": "15Mbps",
    "dscp_marking": "AF42"
  }
}
```

## Event and Trigger Management

### List Policy Events

```http
GET /events
```

**Query Parameters:**
- `policy_id`: Filter by policy ID
- `event_type`: trigger, evaluation, action_executed, error
- `from`: Start time (ISO 8601)
- `to`: End time (ISO 8601)
- `severity`: info, warning, error, critical

**Response:**
```json
{
  "events": [
    {
      "id": "evt_001",
      "type": "policy_triggered",
      "policy_id": "pol_001",
      "policy_name": "FL Traffic Priority",
      "timestamp": "2024-01-15T11:00:00Z",
      "severity": "info",
      "context": {
        "experiment_id": "exp_001",
        "client_id": "client_003",
        "trigger_reason": "FL communication detected"
      },
      "execution_result": {
        "status": "success",
        "actions_executed": 1,
        "execution_time": "15ms"
      }
    }
  ],
  "total": 1
}
```

### Create Custom Trigger

```http
POST /triggers
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "High Network Utilization Alert",
  "description": "Trigger when network utilization exceeds threshold",
  "condition": {
    "field": "network_utilization",
    "operator": "greater_than",
    "value": 80
  },
  "actions": [
    {
      "type": "webhook",
      "parameters": {
        "url": "https://alerts.example.com/webhook",
        "method": "POST",
        "headers": {
          "Content-Type": "application/json"
        },        "payload": {
          "alert": "High network utilization detected",
          "value": "`{`{network_utilization`}`}",
          "timestamp": "`{`{timestamp`}`}"
        }
      }
    }
  ],
  "enabled": true
}
```

## Policy Simulation

### Simulate Policy Changes

```http
POST /policies/simulate
Content-Type: application/json
```

**Request Body:**
```json
{
  "scenario": {
    "name": "Network Congestion Test",
    "duration": "1h",
    "events": [
      {
        "timestamp": "2024-01-15T12:00:00Z",
        "context": {
          "network_utilization": 85,
          "active_experiments": 3
        }
      },
      {
        "timestamp": "2024-01-15T12:30:00Z",
        "context": {
          "network_utilization": 95,
          "active_experiments": 5
        }
      }
    ]
  },
  "policy_changes": [
    {
      "policy_id": "pol_001",
      "changes": {
        "actions": [
          {
            "type": "set_qos_class",
            "parameters": {
              "bandwidth_guarantee": "20Mbps"
            }
          }
        ]
      }
    }
  ]
}
```

**Response:**
```json
{
  "simulation_id": "sim_001",
  "status": "completed",
  "duration": "1h",
  "results": {
    "total_evaluations": 150,
    "policy_triggers": 25,
    "successful_actions": 24,
    "failed_actions": 1,
    "performance_impact": {
      "average_response_time": "18ms",
      "peak_response_time": "45ms",
      "resource_utilization": "medium"
    },
    "recommendations": [
      "Consider implementing fallback policies for high utilization scenarios",
      "Bandwidth guarantee of 20Mbps may be excessive for current traffic patterns"
    ]
  }
}
```

## System Configuration

### Get Engine Configuration

```http
GET /config
```

**Response:**
```json
{
  "engine": {
    "evaluation_timeout": "30s",
    "max_concurrent_evaluations": 100,
    "policy_cache_ttl": "300s",
    "enable_metrics_collection": true
  },
  "storage": {
    "policy_retention": "1y",
    "event_retention": "90d",
    "backup_interval": "24h"
  },
  "integrations": {
    "sdn_controller": {
      "enabled": true,
      "endpoint": "http://localhost:8181",
      "timeout": "10s"
    },
    "fl_server": {
      "enabled": true,
      "endpoint": "http://localhost:8080",
      "timeout": "5s"
    },
    "collector": {
      "enabled": true,
      "endpoint": "http://localhost:8081",
      "metrics_interval": "30s"
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
  "engine": {
    "evaluation_timeout": "45s",
    "max_concurrent_evaluations": 150
  }
}
```

## Monitoring and Analytics

### Policy Performance Metrics

```http
GET /metrics/policies
```

**Query Parameters:**
- `policy_id`: Specific policy ID
- `from`: Start time
- `to`: End time
- `metric`: execution_time, success_rate, trigger_count

**Response:**
```json
{
  "policies": [
    {
      "policy_id": "pol_001",
      "policy_name": "FL Traffic Priority",
      "metrics": {
        "execution_time": {
          "avg": "15ms",
          "min": "8ms",
          "max": "45ms",
          "p95": "25ms"
        },
        "success_rate": 0.987,
        "trigger_count": 156,
        "error_count": 2,
        "last_execution": "2024-01-15T11:45:00Z"
      }
    }
  ]
}
```

### System Health

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "3d 8h 15m",
  "components": {
    "policy_evaluator": {
      "status": "healthy",
      "active_evaluations": 5,
      "queue_size": 12,
      "processing_rate": "150 evaluations/min"
    },
    "rule_engine": {
      "status": "healthy",
      "loaded_policies": 25,
      "active_triggers": 8
    },
    "storage": {
      "status": "connected",
      "database_size": "125MB",
      "connection_pool": "8/10"
    }
  },
  "integrations": {
    "sdn_controller": {
      "status": "connected",
      "response_time": "12ms",
      "last_check": "2024-01-15T11:59:30Z"
    },
    "fl_server": {
      "status": "connected",
      "response_time": "8ms",
      "last_check": "2024-01-15T11:59:30Z"
    }
  }
}
```

## Error Handling

### Validation Errors

```json
{
  "error": {
    "code": "POLICY_VALIDATION_FAILED",
    "message": "Policy validation failed",
    "details": {
      "conditions": [
        "Field 'traffic_type' is required"
      ],
      "actions": [
        "Action type 'invalid_action' is not supported"
      ]
    }
  }
}
```

### Execution Errors

```json
{
  "error": {
    "code": "POLICY_EXECUTION_FAILED",
    "message": "Failed to execute policy action",
    "details": {
      "policy_id": "pol_001",
      "action_type": "set_qos_class",
      "error": "SDN controller unreachable",
      "retry_available": true
    }
  }
}
```

## SDK Examples

### Python SDK

```python
from flopy_net_client import PolicyEngineClient

# Initialize client
policy_engine = PolicyEngineClient(
    base_url="http://localhost:5000/api/v1",
    api_key="policy_engine_api_key"
)

# Create a new policy
policy = policy_engine.create_policy({
    "name": "Dynamic QoS Policy",
    "category": "network_qos",
    "conditions": [
        {
            "field": "experiment_priority",
            "operator": "equals",
            "value": "high"
        }
    ],
    "actions": [
        {
            "type": "allocate_bandwidth",
            "parameters": {
                "min_bandwidth": "20Mbps"
            }
        }
    ]
})

# Evaluate policies for current context
evaluation = policy_engine.evaluate_policies({
    "experiment_priority": "high",
    "network_utilization": 60,
    "active_clients": 8
})

print(f"Matched {len(evaluation.matched_policies)} policies")

# Monitor policy events
for event in policy_engine.stream_events():
    if event.type == "policy_triggered":
        print(f"Policy {event.policy_name} triggered")
```

### JavaScript SDK

```javascript
import { PolicyEngineClient } from 'flopy-net-client';

const policyEngine = new PolicyEngineClient({
    baseUrl: 'http://localhost:5000/api/v1',
    apiKey: 'policy_engine_api_key'
});

// Create policy from template
const policy = await policyEngine.createFromTemplate({
    templateId: 'tpl_fl_priority',
    name: 'My FL Priority Policy',
    parameters: {
        bandwidth_guarantee: '25Mbps'
    }
});

// Real-time policy evaluation
const context = {
    traffic_type: 'fl_communication',
    experiment_status: 'running'
};

const evaluation = await policyEngine.evaluate(context);
console.log('Actions executed: ' + evaluation.matched_policies.length);

// WebSocket for real-time events
const eventStream = policyEngine.createEventStream();
eventStream.on('policy_triggered', (event) => {
    console.log('Policy ' + event.policy_name + ' executed');
});
```
