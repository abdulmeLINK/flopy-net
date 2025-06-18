# Policy Engine API

The Policy Engine provides REST APIs for managing security policies, compliance monitoring, and governance rules within the FLOPY-NET system.

## Base URL

```
http://localhost:5000/api/v1
```

## Authentication

The Policy Engine supports multiple authentication methods:

```http
# API Key Authentication
Authorization: Bearer <api-key>

# Basic Authentication  
Authorization: Basic <base64-encoded-credentials>

# JWT Token Authentication
Authorization: JWT <jwt-token>
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
  "uptime": 3600,
  "active_policies": 15,
  "policy_evaluations_per_minute": 45,
  "components": {
    "rule_engine": "operational",
    "trust_calculator": "operational",
    "event_processor": "operational"
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
  "system_status": "operational",
  "policy_engine_version": "1.0.0",
  "active_policies": 15,
  "enabled_policies": 12,
  "disabled_policies": 3,
  "total_evaluations": 12458,
  "successful_evaluations": 12234,
  "failed_evaluations": 224,
  "average_evaluation_time_ms": 15.2,
  "trust_scores": {
    "clients_monitored": 25,
    "average_trust_score": 0.87,
    "high_trust_clients": 18,
    "medium_trust_clients": 6,
    "low_trust_clients": 1
  },
  "last_policy_update": "2025-01-16T09:45:00Z"
}
```

### Policy Management

#### List All Policies
```http
GET /policies
```

**Query Parameters:**
- `status` (optional): Filter by status (`enabled`, `disabled`, `draft`)
- `category` (optional): Filter by category (`security`, `performance`, `compliance`)
- `limit` (optional): Number of results (default: 50)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "policies": [
    {
      "id": 1,
      "name": "Client Trust Threshold",
      "description": "Minimum trust score required for client participation",
      "category": "security",
      "status": "enabled",
      "priority": 100,
      "conditions": [
        {
          "field": "client.trust_score",
          "operator": ">=",
          "value": 0.7
        }
      ],
      "actions": [
        {
          "type": "allow_participation",
          "parameters": {}
        }
      ],
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-16T08:30:00Z",
      "evaluation_count": 245,
      "success_rate": 0.92
    }
  ],
  "total_count": 15,
  "has_more": false
}
```

#### Get Policy by ID
```http
GET /policies/{policy_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "Client Trust Threshold",
  "description": "Minimum trust score required for client participation",
  "category": "security",
  "status": "enabled",
  "priority": 100,
  "conditions": [
    {
      "field": "client.trust_score",
      "operator": ">=",
      "value": 0.7,
      "description": "Trust score must be at least 0.7"
    }
  ],
  "actions": [
    {
      "type": "allow_participation",
      "parameters": {},
      "description": "Allow client to participate in training"
    },
    {
      "type": "log_event",
      "parameters": {
        "level": "info",
        "message": "Client allowed based on trust score"
      }
    }
  ],
  "metadata": {
    "author": "admin",
    "version": "1.2",
    "tags": ["trust", "security", "client-validation"]
  },
  "evaluation_history": {
    "total_evaluations": 245,
    "successful_evaluations": 226,
    "failed_evaluations": 19,
    "last_evaluation": "2025-01-16T10:25:00Z",
    "average_evaluation_time_ms": 12.5
  }
}
```

#### Create Policy
```http
POST /policies
```

**Request Body:**
```json
{
  "name": "Model Size Limit",
  "description": "Prevent oversized model updates",
  "category": "performance",
  "status": "enabled",
  "priority": 80,
  "conditions": [
    {
      "field": "model.size_mb",
      "operator": "<=",
      "value": 100,
      "description": "Model size must not exceed 100MB"
    }
  ],
  "actions": [
    {
      "type": "reject_update",
      "parameters": {
        "reason": "Model size exceeds limit"
      }
    },
    {
      "type": "alert",
      "parameters": {
        "severity": "warning",
        "message": "Large model update rejected"
      }
    }
  ],
  "metadata": {
    "tags": ["performance", "model-validation"],
    "author": "system_admin"
  }
}
```

**Response:**
```json
{
  "id": 16,
  "name": "Model Size Limit",
  "status": "created",
  "created_at": "2025-01-16T10:30:00Z",
  "validation_status": "passed",
  "enabled": true
}
```

#### Update Policy
```http
PUT /policies/{policy_id}
```

**Request Body:** Same as create policy

#### Delete Policy
```http
DELETE /policies/{policy_id}
```

**Response:**
```json
{
  "id": 16,
  "status": "deleted",
  "deleted_at": "2025-01-16T10:30:00Z",
  "cascade_effects": {
    "removed_from_evaluations": 5,
    "affected_clients": 12
  }
}
```

### Policy Evaluation

#### Evaluate Policy
```http
POST /policies/evaluate
```

**Request Body:**
```json
{
  "context": {
    "event_type": "client_registration",
    "client": {
      "id": "client-001",
      "trust_score": 0.85,
      "location": "us-east-1",
      "capabilities": {
        "compute_power": "high",
        "memory": "8GB"
      }
    },
    "experiment": {
      "id": "exp_2025_001",
      "sensitivity": "medium"
    }
  },
  "policies": [1, 2, 5],  // Optional: specific policies to evaluate
  "evaluation_mode": "strict"  // strict, permissive, advisory
}
```

**Response:**
```json
{
  "evaluation_id": "eval_12345",
  "timestamp": "2025-01-16T10:30:00Z",
  "overall_decision": "allow",
  "confidence": 0.92,
  "policy_results": [
    {
      "policy_id": 1,
      "policy_name": "Client Trust Threshold",
      "decision": "allow",
      "confidence": 0.95,
      "condition_results": [
        {
          "condition": "client.trust_score >= 0.7",
          "result": true,
          "actual_value": 0.85,
          "expected_value": 0.7
        }
      ],
      "actions_taken": [
        {
          "action": "allow_participation",
          "status": "executed",
          "timestamp": "2025-01-16T10:30:00Z"
        }
      ],
      "evaluation_time_ms": 12.3
    }
  ],
  "warnings": [],
  "recommendations": [
    "Consider monitoring client performance during training"
  ]
}
```

#### Batch Evaluation
```http
POST /policies/evaluate/batch
```

**Request Body:**
```json
{
  "evaluations": [
    {
      "context": {
        "event_type": "client_registration",
        "client": {"id": "client-001", "trust_score": 0.85}
      }
    },
    {
      "context": {
        "event_type": "model_update",
        "client": {"id": "client-002"},
        "model": {"size_mb": 45.2}
      }
    }
  ],
  "evaluation_mode": "strict"
}
```

### Trust Management

#### Get Trust Scores
```http
GET /trust/scores
```

**Query Parameters:**
- `client_id` (optional): Filter by specific client
- `threshold` (optional): Filter by minimum trust score
- `limit` (optional): Number of results

**Response:**
```json
{
  "trust_scores": [
    {
      "client_id": "client-001",
      "current_trust_score": 0.85,
      "previous_trust_score": 0.82,
      "trend": "increasing",
      "factors": {
        "performance_consistency": 0.90,
        "model_quality": 0.85,
        "availability": 0.95,
        "security_compliance": 0.88
      },
      "last_updated": "2025-01-16T10:25:00Z",
      "evaluation_count": 45,
      "risk_level": "low"
    }
  ],
  "summary": {
    "total_clients": 25,
    "average_trust_score": 0.87,
    "distribution": {
      "high_trust": 18,
      "medium_trust": 6,
      "low_trust": 1
    }
  }
}
```

#### Update Trust Score
```http
POST /trust/scores/{client_id}
```

**Request Body:**
```json
{
  "event_type": "training_completion",
  "performance_metrics": {
    "accuracy": 0.78,
    "training_time": 45.2,
    "model_quality_score": 0.85
  },
  "behavioral_data": {
    "availability": 0.95,
    "responsiveness": 0.92,
    "compliance": true
  },
  "context": {
    "experiment_id": "exp_2025_001",
    "round": 5
  }
}
```

**Response:**
```json
{
  "client_id": "client-001",
  "previous_trust_score": 0.82,
  "new_trust_score": 0.85,
  "change": 0.03,
  "factors_updated": [
    "performance_consistency",
    "model_quality"
  ],
  "updated_at": "2025-01-16T10:30:00Z"
}
```

### Compliance and Monitoring

#### Get Compliance Status
```http
GET /compliance/status
```

**Response:**
```json
{
  "overall_compliance": 0.94,
  "compliance_by_category": {
    "security": 0.98,
    "performance": 0.89,
    "data_governance": 0.95
  },
  "active_violations": 3,
  "recent_violations": [
    {
      "violation_id": "viol_001",
      "policy_id": 5,
      "policy_name": "Model Update Frequency",
      "client_id": "client-003",
      "severity": "medium",
      "description": "Client exceeded model update frequency limit",
      "occurred_at": "2025-01-16T09:45:00Z",
      "status": "active"
    }
  ],
  "compliance_trends": {
    "last_24h": 0.94,
    "last_7d": 0.92,
    "last_30d": 0.89
  }
}
```

#### Get Violations
```http
GET /compliance/violations
```

**Query Parameters:**
- `severity` (optional): Filter by severity (`low`, `medium`, `high`, `critical`)
- `status` (optional): Filter by status (`active`, `resolved`, `acknowledged`)
- `client_id` (optional): Filter by client
- `from_date` (optional): Start date filter
- `to_date` (optional): End date filter

**Response:**
```json
{
  "violations": [
    {
      "violation_id": "viol_001",
      "policy_id": 5,
      "policy_name": "Model Update Frequency",
      "client_id": "client-003",
      "severity": "medium",
      "description": "Client exceeded model update frequency limit",
      "details": {
        "expected_frequency": "max 1 per round",
        "actual_frequency": "3 updates in round 5",
        "excess_updates": 2
      },
      "occurred_at": "2025-01-16T09:45:00Z",
      "detected_at": "2025-01-16T09:45:15Z",
      "status": "active",
      "impact": "minimal",
      "recommended_actions": [
        "Throttle client updates",
        "Review client configuration"
      ]
    }
  ],
  "total_count": 15,
  "severity_breakdown": {
    "critical": 0,
    "high": 2,
    "medium": 8,
    "low": 5
  }
}
```

#### Acknowledge Violation
```http
POST /compliance/violations/{violation_id}/acknowledge
```

**Request Body:**
```json
{
  "acknowledged_by": "admin_user",
  "note": "Client configuration has been reviewed and updated",
  "action_taken": "configuration_update"
}
```

### Event Management

#### Get Policy Events
```http
GET /events
```

**Query Parameters:**
- `event_type` (optional): Filter by event type
- `client_id` (optional): Filter by client
- `policy_id` (optional): Filter by policy
- `from_date` (optional): Start date
- `to_date` (optional): End date
- `limit` (optional): Number of results

**Response:**
```json
{
  "events": [
    {
      "event_id": "evt_12345",
      "event_type": "policy_evaluation",
      "timestamp": "2025-01-16T10:30:00Z",
      "client_id": "client-001",
      "policy_id": 1,
      "decision": "allow",
      "context": {
        "experiment_id": "exp_2025_001",
        "event_trigger": "client_registration"
      },
      "evaluation_time_ms": 12.3,
      "metadata": {
        "ip_address": "192.168.141.100",
        "user_agent": "FL-Client/1.0"
      }
    }
  ],
  "total_count": 1247,
  "event_types": [
    "policy_evaluation",
    "trust_score_update",
    "violation_detected",
    "policy_created",
    "policy_updated"
  ]
}
```

#### Create Custom Event
```http
POST /events
```

**Request Body:**
```json
{
  "event_type": "custom_security_check",
  "client_id": "client-001",
  "severity": "info",
  "description": "Custom security validation completed",
  "metadata": {
    "check_type": "malware_scan",
    "result": "clean",
    "scan_duration_ms": 1250
  },
  "tags": ["security", "custom", "validation"]
}
```

### Configuration

#### Get Configuration
```http
GET /config
```

**Response:**
```json
{
  "trust_calculation": {
    "algorithm": "weighted_average",
    "factors": {
      "performance_consistency": 0.3,
      "model_quality": 0.25,
      "availability": 0.2,
      "security_compliance": 0.25
    },
    "decay_factor": 0.95,
    "update_frequency": "per_round"
  },
  "policy_evaluation": {
    "default_mode": "strict",
    "timeout_ms": 5000,
    "cache_results": true,
    "cache_ttl_seconds": 300
  },
  "thresholds": {
    "trust_score_minimum": 0.7,
    "violation_severity_mapping": {
      "critical": 0.95,
      "high": 0.8,
      "medium": 0.6,
      "low": 0.4
    }
  },
  "integrations": {
    "fl_server_url": "http://fl-server:8080",
    "collector_url": "http://collector:8002",
    "dashboard_webhook": "http://dashboard:8001/api/policy-events"
  }
}
```

#### Update Configuration
```http
PUT /config
```

**Request Body:** Same structure as GET response

### Real-time Streaming

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/events');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'policy_evaluation':
            handlePolicyEvaluation(data);
            break;
        case 'trust_score_update':
            handleTrustScoreUpdate(data);
            break;
        case 'violation_detected':
            handleViolation(data);
            break;
    }
};

// Subscribe to specific event types
ws.send(JSON.stringify({
    action: 'subscribe',
    event_types: ['violation_detected', 'trust_score_update']
}));
```

#### Stream Events

**Policy Evaluation Event:**
```json
{
  "type": "policy_evaluation",
  "evaluation_id": "eval_12345",
  "timestamp": "2025-01-16T10:30:00Z",
  "client_id": "client-001",
  "policy_id": 1,
  "decision": "allow",
  "confidence": 0.92,
  "evaluation_time_ms": 12.3
}
```

**Violation Event:**
```json
{
  "type": "violation_detected",
  "violation_id": "viol_001",
  "timestamp": "2025-01-16T10:30:00Z",
  "policy_id": 5,
  "client_id": "client-003",
  "severity": "medium",
  "description": "Model update frequency exceeded"
}
```

**Trust Score Update:**
```json
{
  "type": "trust_score_update",
  "timestamp": "2025-01-16T10:30:00Z",
  "client_id": "client-001",
  "previous_score": 0.82,
  "new_score": 0.85,
  "change": 0.03,
  "factors_updated": ["performance_consistency", "model_quality"]
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "POLICY_NOT_FOUND",
    "message": "Policy with ID 999 not found",
    "details": "The specified policy ID does not exist in the system",
    "timestamp": "2025-01-16T10:30:00Z",
    "trace_id": "trace_abc123"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_POLICY_SYNTAX` | Policy condition or action syntax error |
| 401 | `UNAUTHORIZED` | Invalid authentication credentials |
| 403 | `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| 404 | `POLICY_NOT_FOUND` | Specified policy does not exist |
| 409 | `POLICY_CONFLICT` | Policy name already exists |
| 422 | `POLICY_VALIDATION_FAILED` | Policy failed validation checks |
| 429 | `RATE_LIMITED` | Too many evaluation requests |
| 500 | `EVALUATION_ERROR` | Policy evaluation engine error |

## SDK Examples

### Python SDK

```python
import requests
import json

class PolicyEngineClient:
    def __init__(self, base_url="http://localhost:5000", api_key=None):
        self.base_url = f"{base_url}/api/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else None
        }
    
    def evaluate_policy(self, context, policies=None):
        """Evaluate policies against given context."""
        payload = {
            "context": context,
            "evaluation_mode": "strict"
        }
        if policies:
            payload["policies"] = policies
            
        response = requests.post(
            f"{self.base_url}/policies/evaluate",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_trust_score(self, client_id):
        """Get trust score for a client."""
        response = requests.get(
            f"{self.base_url}/trust/scores?client_id={client_id}",
            headers=self.headers
        )
        return response.json()
    
    def create_policy(self, policy_definition):
        """Create a new policy."""
        response = requests.post(
            f"{self.base_url}/policies",
            headers=self.headers,
            json=policy_definition
        )
        return response.json()
```

### JavaScript SDK

```javascript
class PolicyEngineAPI {
    constructor(baseUrl = 'http://localhost:5000', apiKey = null) {
        this.baseUrl = baseUrl + '/api/v1';
        this.headers = {
            'Content-Type': 'application/json',
            ...(apiKey && { 'Authorization': 'Bearer ' + apiKey })
        };
    }
    
    async evaluatePolicy(context, policies = null) {
        const payload = {
            context,
            evaluation_mode: 'strict',
            ...(policies && { policies })
        };
          const response = await fetch(this.baseUrl + '/policies/evaluate', {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(payload)
        });
        
        return response.json();
    }
    
    async getTrustScores(clientId = null) {
        const url = clientId 
            ? this.baseUrl + '/trust/scores?client_id=' + clientId
            : this.baseUrl + '/trust/scores';
            
        const response = await fetch(url, {
            headers: this.headers
        });
        
        return response.json();
    }
    
    // WebSocket connection for real-time events
    connectEvents() {
        this.ws = new WebSocket('ws://localhost:5000/ws/events');
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
        };
        
        return this.ws;
    }
}
```

This comprehensive Policy Engine API reference provides developers with all the tools needed to integrate policy management, trust calculation, and compliance monitoring into federated learning applications.
