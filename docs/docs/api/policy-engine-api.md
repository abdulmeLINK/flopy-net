# Policy Engine API Reference

The Policy Engine API provides policy management and enforcement capabilities for federated learning governance, network control, and system compliance monitoring.

## Base URL

```
http://localhost:5000/
```

## Service Information

**Container**: `abdulmelink/flopynet-policy-engine:v1.0.0-alpha.8`  
**Network IP**: `192.168.100.20`  
**Port**: `5000`  
**Technology**: Flask REST API  
**Storage**: JSON configuration files  

## API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

## Policy Management

### List All Policies

```http
GET /policies
```

**Query Parameters:**
- `type` (optional): Filter policies by type (e.g., `network_security`, `model_validation`)

**Response:**
```json
{
  "default-net-sec-001": {
    "id": "default-net-sec-001",
    "name": "base_network_security",
    "type": "network_security",
    "description": "Base network security policy allowing essential FL system communication",
    "priority": 100,
    "rules": [
      {
        "action": "allow",
        "description": "Allow FL clients to connect to FL server",
        "match": {
          "protocol": "tcp",
          "src_type": "fl-client",
          "dst_type": "fl-server",
          "dst_port": 8080
        }
      }
    ]
  }
}
```

### Get Policy by ID

```http
GET /policies/{policy_id}
```

**Response:**
```json
{
  "id": "default-net-sec-001",
  "name": "base_network_security",
  "type": "network_security",
  "description": "Base network security policy allowing essential FL system communication",
  "priority": 100,
  "rules": [
    {
      "action": "allow",
      "description": "Allow FL clients to connect to FL server",
      "match": {
        "protocol": "tcp",
        "src_type": "fl-client",
        "dst_type": "fl-server",
        "dst_port": 8080
      }
    }
  ]
}
```

**Error Response (404):**
```json
{
  "error": "Policy {policy_id} not found"
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
  "type": "network_security",
  "data": {
    "name": "custom_policy",
    "description": "Custom network security policy",
    "rules": [
      {
        "action": "allow",
        "description": "Allow custom traffic",
        "match": {
          "protocol": "tcp",
          "dst_port": 9000
        }
      }
    ]
  }
}
```

**Response (201):**
```json
{
  "id": "custom-policy-001",
  "type": "network_security",
  "data": {
    "name": "custom_policy",
    "description": "Custom network security policy",
    "rules": [
      {
        "action": "allow",
        "description": "Allow custom traffic",
        "match": {
          "protocol": "tcp",
          "dst_port": 9000
        }
      }
    ]
  }
}
```

**Error Response (400):**
```json
{
  "error": "Missing policy type or data"
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
  "data": {
    "name": "updated_policy",
    "description": "Updated policy description",
    "rules": [
      {
        "action": "deny",
        "description": "Block suspicious traffic",
        "match": {
          "protocol": "tcp",
          "dst_port": 8080
        }
      }
    ]
  }
}
```

**Response:**
```json
{
  "id": "policy-001",
  "data": {
    "name": "updated_policy",
    "description": "Updated policy description",
    "rules": [
      {
        "action": "deny",
        "description": "Block suspicious traffic",
        "match": {
          "protocol": "tcp",
          "dst_port": 8080
        }
      }
    ]
  }
}
```

**Error Response (404):**
```json
{
  "error": "Policy {policy_id} not found"
}
```

### Delete Policy

```http
DELETE /policies/{policy_id}
```

**Response:**
```json
{
  "id": "policy-001",
  "deleted": true
}
```

**Error Response (404):**
```json
{
  "error": "Policy {policy_id} not found"
}
```

## Event Management

### Get Events

```http
GET /events
```

**Query Parameters:**
- `since_event_id` (optional): Get events after this event ID
- `limit` (optional): Maximum number of events to return (default: 1000)

**Response:**
```json
{
  "events": [
    {
      "event_id": "uuid-string",
      "timestamp": "2025-06-22T10:30:00.000Z",
      "source_component": "POLICY_ENGINE",
      "event_type": "POLICY_LOADED",
      "details": {
        "policy_id": "default-net-sec-001",
        "policy_type": "network_security"
      }
    }
  ],
  "last_event_id": "uuid-string"
}
```

## Policy Checking

### Check Policy (Main Endpoint)

```http
POST /check
Content-Type: application/json
```

**Request Body:**
```json
{
  "type": "network_security",
  "context": {
    "src_ip": "192.168.1.100",
    "dst_ip": "192.168.1.200",
    "dst_port": 8080,
    "protocol": "tcp"
  }
}
```

**Response:**
```json
{
  "allowed": true,
  "policy_id": "default-net-sec-001",
  "rule_matched": {
    "action": "allow",
    "description": "Allow FL clients to connect to FL server"
  },
  "request_id": "uuid-string"
}
```

### Check Policy (API Alias)

```http
POST /api/check_policy
Content-Type: application/json
```

**Request Body:**
```json
{
  "policy_type": "network_security",
  "context": {
    "src_ip": "192.168.1.100",
    "dst_ip": "192.168.1.200",
    "dst_port": 8080,
    "protocol": "tcp"
  }
}
```

Response format is the same as `/check`.

### Check Policy (API v1)

```http
POST /api/v1/check
Content-Type: application/json
```

This endpoint is an alias for `/api/check_policy` and accepts the same request format.

## Policy Types

The Policy Engine supports several policy types:

### Network Security Policies
- **Type**: `network_security`
- **Purpose**: Control network traffic between components
- **Match Fields**: `protocol`, `src_type`, `dst_type`, `src_ip`, `dst_ip`, `dst_port`
- **Actions**: `allow`, `deny`

### Model Validation Policies
- **Type**: `model_validation`
- **Purpose**: Validate federated learning models
- **Match Fields**: `model_size`, `accuracy_threshold`, `client_id`
- **Actions**: `accept`, `reject`

### Client Selection Policies
- **Type**: `client_selection`
- **Purpose**: Control client participation in training rounds
- **Match Fields**: `client_capabilities`, `data_quality`, `network_conditions`
- **Actions**: `select`, `skip`

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200**: Success
- **201**: Created (for POST requests)
- **400**: Bad Request (missing or invalid parameters)
- **404**: Not Found (policy not found)
- **500**: Internal Server Error

Error responses include a descriptive error message:
```json
{
  "error": "Description of the error"
}
```

## Configuration

The Policy Engine loads policies from:
- **Default**: `config/policies/policies.json`
- **Environment**: `POLICY_FILE` environment variable

Policy configuration files use JSON format with the following structure:
```json
{
  "version": 2,
  "policies": {
    "policy-id": {
      "id": "policy-id",
      "name": "policy_name",
      "type": "policy_type",
      "description": "Policy description",
      "priority": 100,
      "rules": [
        {
          "action": "allow|deny",
          "description": "Rule description",
          "match": {
            "field": "value"
          }
        }
      ]
    }
  }
}
```

## Examples

### Checking Network Traffic Policy

```bash
curl -X POST http://localhost:5000/check \
  -H "Content-Type: application/json" \
  -d '{
    "type": "network_security",
    "context": {
      "protocol": "tcp",
      "src_type": "fl-client",
      "dst_type": "fl-server",
      "dst_port": 8080
    }
  }'
```

### Creating a Custom Policy

```bash
curl -X POST http://localhost:5000/policies \
  -H "Content-Type: application/json" \
  -d '{
    "type": "network_security",
    "data": {
      "name": "block_port_22",
      "description": "Block SSH traffic",
      "rules": [
        {
          "action": "deny",
          "description": "Block SSH",
          "match": {
            "protocol": "tcp",
            "dst_port": 22
          }
        }
      ]
    }
  }'
```

### Getting Events Since Last Check

```bash
curl "http://localhost:5000/events?since_event_id=last-known-id&limit=100"
```
