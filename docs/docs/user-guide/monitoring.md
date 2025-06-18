# Monitoring and Troubleshooting

This guide provides comprehensive monitoring capabilities and troubleshooting procedures for FLOPY-NET experiments, helping you identify issues, optimize performance, and maintain system health.

## Monitoring Overview

FLOPY-NET provides multi-layered monitoring through:

- **Real-time Dashboard**: Web-based visualization and alerts
- **Metrics Collection**: Time-series data aggregation and storage
- **Log Aggregation**: Centralized logging from all components
- **Health Checks**: Automated service health monitoring
- **Alert System**: Proactive issue detection and notification

## Dashboard Monitoring

### 1. Main Dashboard

Access the main monitoring dashboard at `http://localhost:3001`:

**System Overview Panel:**
- Service health status (green/yellow/red indicators)
- Resource utilization (CPU, memory, network)
- Active experiments count
- System uptime and version info

**Experiment Monitoring Panel:**
- Current experiment status and progress
- Real-time accuracy and loss graphs
- Client participation and status
- Network performance metrics

**Network Topology Panel:**
- Live network topology visualization
- Switch and link status indicators
- Traffic flow visualization
- QoS policy enforcement status

### 2. Detailed Monitoring Views

**FL Training Metrics:**
```javascript
// Real-time FL metrics
const flMetrics = {
    current_round: 12,
    global_accuracy: 0.89,
    global_loss: 0.34,
    convergence_rate: 0.02,
    active_clients: 5,
    client_metrics: [
        {
            id: "client_001",
            local_accuracy: 0.87,
            local_loss: 0.38,
            training_time: "45s",
            communication_time: "12s"
        }
    ]
};
```

**Network Performance Metrics:**
```javascript
// Network monitoring data
const networkMetrics = {
    bandwidth_utilization: 45.2,
    average_latency: "15ms",
    packet_loss_rate: 0.001,
    qos_enforcements: 156,
    flow_modifications: 12,
    topology_changes: 0
};
```

### 3. Custom Dashboards

Create custom monitoring dashboards:

```bash
curl -X POST http://localhost:3001/api/v1/dashboards \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FL Performance Dashboard",
    "layout": {
      "panels": [
        {
          "type": "line_chart",
          "title": "Global Model Accuracy",
          "metrics": ["global_accuracy"],
          "time_range": "1h"
        },
        {
          "type": "gauge",
          "title": "Network Utilization",
          "metrics": ["bandwidth_utilization"],
          "thresholds": [70, 90]
        }
      ]
    }
  }'
```

## Metrics Collection and Analysis

### 1. Time-Series Metrics

Query historical metrics using the Collector API:

```bash
# Get FL training progress over time
curl "http://localhost:8081/api/v1/metrics/query?metric=global_accuracy&from=2024-01-15T10:00:00Z&to=2024-01-15T11:00:00Z&granularity=1m"

# Get network utilization statistics
curl "http://localhost:8081/api/v1/metrics/summary?metric=bandwidth_utilization&from=2024-01-15T10:00:00Z&to=2024-01-15T11:00:00Z"
```

### 2. Performance Analytics

**Convergence Analysis:**
```python
import requests
import matplotlib.pyplot as plt

# Fetch convergence data
response = requests.get(
    "http://localhost:8081/api/v1/metrics/query",
    params={
        "metric": "global_accuracy",
        "experiment_id": "exp_001",
        "granularity": "1m"
    }
)

data = response.json()["data_points"]
rounds = [point["round"] for point in data]
accuracy = [point["value"] for point in data]

# Plot convergence curve
plt.plot(rounds, accuracy)
plt.xlabel("Training Round")
plt.ylabel("Global Accuracy")
plt.title("FL Model Convergence")
plt.show()
```

**Communication Overhead Analysis:**
```python
# Analyze communication patterns
response = requests.get(
    "http://localhost:8081/api/v1/metrics/query",
    params={
        "metric": "communication_overhead",
        "experiment_id": "exp_001"
    }
)

# Calculate efficiency metrics
total_data = sum(point["value"] for point in data)
training_time = data[-1]["timestamp"] - data[0]["timestamp"]
efficiency = final_accuracy / (total_data / 1024**2)  # Accuracy per MB

print(f"Communication Efficiency: {efficiency:.4f} accuracy/MB")
```

### 3. Anomaly Detection

Set up automated anomaly detection:

```bash
curl -X POST http://localhost:8081/api/v1/metrics/anomalies \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "global_accuracy",
    "algorithm": "isolation_forest",
    "sensitivity": 0.1,
    "alert_threshold": 0.8
  }'
```

## Log Management

### 1. Centralized Logging

All FLOPY-NET components use structured logging:

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker logs flopy-net-fl-server -f
docker logs flopy-net-policy-engine -f
docker logs flopy-net-sdn-controller -f

# Filter logs by level
docker logs flopy-net-dashboard 2>&1 | grep ERROR
```

### 2. Log Analysis

**Parse structured logs:**
```python
import json
import subprocess

def analyze_fl_logs():
    # Get FL server logs
    result = subprocess.run(
        ["docker", "logs", "flopy-net-fl-server"],
        capture_output=True, text=True
    )
    
    errors = []
    warnings = []
    
    for line in result.stdout.split('\n'):
        if line.strip():
            try:
                log_entry = json.loads(line)
                if log_entry.get("level") == "ERROR":
                    errors.append(log_entry)
                elif log_entry.get("level") == "WARNING":
                    warnings.append(log_entry)
            except json.JSONDecodeError:
                continue
    
    return {"errors": errors, "warnings": warnings}

analysis = analyze_fl_logs()
print(f"Found {len(analysis['errors'])} errors and {len(analysis['warnings'])} warnings")
```

### 3. Log Aggregation with ELK Stack

Set up centralized logging (optional):

```yaml
# docker-compose.elk.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash/config:/usr/share/logstash/pipeline
    ports:
      - "5044:5044"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
```

## Health Monitoring

### 1. Service Health Checks

Monitor individual service health:

```bash
# Check all services - Note: Replace with actual port numbers
services=("dashboard:3001" "collector:8081" "policy-engine:5000" "fl-server:8080" "sdn-controller:8181")
for service_port in "\${services[@]}"; do
  service_name=\$(echo \$service_port | cut -d: -f1)
  port=\$(echo \$service_port | cut -d: -f2)
  echo "Checking \$service_name on port \$port..."
  curl -s http://localhost:\$port/api/v1/health | jq '.status'
done

# Automated health check script
#!/bin/bash
services=(
  "dashboard:3001"
  "collector:8081" 
  "policy-engine:5000"
  "fl-server:8080"
  "sdn-controller:8181"
)

for service_port in "\${services[@]}"; do
  service=\${service_port%:*}
  port=\${service_port#*:}
  
  if curl -s -f http://localhost:\$port/api/v1/health > /dev/null; then
    echo "✓ \$service is healthy"
  else
    echo "✗ \$service is unhealthy"
  fi
done
```

### 2. Dependency Health

Check external dependencies:

```bash
# Check database connections
curl http://localhost:8081/api/v1/health/dependencies

# Check network connectivity
curl http://localhost:8181/api/v1/topology

# Check GNS3 integration
curl http://localhost:3080/v2/projects
```

### 3. Resource Monitoring

Monitor system resources:

```bash
# Docker container resources
docker stats --no-stream

# System resources
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
free -m | awk 'NR==2{printf "Memory Usage: %s/%sMB (%.2f%%)\n", $3,$2,$3*100/$2 }'
df -h | awk '$NF=="/"{printf "Disk Usage: %d/%dGB (%s)\n", $3,$2,$5}'

# Network interface statistics
cat /proc/net/dev | grep eth0 | awk '{print "RX bytes: " $2 ", TX bytes: " $10}'
```

## Alert System

### 1. Configure Alerts

Set up proactive alerting:

```bash
curl -X POST http://localhost:8081/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Network Utilization",
    "condition": {
      "metric": "bandwidth_utilization",
      "operator": "greater_than",
      "threshold": 80,
      "duration": "5m"
    },
    "actions": [
      {
        "type": "webhook",
        "url": "https://alerts.example.com/webhook",
        "payload": {
          "message": "Network utilization exceeded 80%",
          "severity": "warning"
        }
      },
      {
        "type": "email",
        "recipients": ["admin@example.com"],
        "subject": "FLOPY-NET Alert: High Network Utilization"
      }
    ]
  }'
```

### 2. Alert Types

**Performance Alerts:**
- FL convergence stalled
- High communication overhead
- Poor client participation
- Network congestion

**System Alerts:**
- Service unavailable
- High resource usage
- Database connection failure
- Policy enforcement failure

**Security Alerts:**
- Unauthorized access attempts
- Anomalous client behavior
- Network intrusion detection
- Data integrity violations

### 3. Alert Management

```bash
# List active alerts
curl http://localhost:8081/api/v1/alerts?status=active

# Acknowledge alert
curl -X POST http://localhost:8081/api/v1/alerts/alert_001/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"comment": "Investigating high network usage"}'

# Resolve alert
curl -X POST http://localhost:8081/api/v1/alerts/alert_001/resolve \
  -H "Content-Type: application/json" \
  -d '{"resolution": "Network optimized, utilization reduced"}'
```

## Troubleshooting Guide

### 1. Common Issues

**Issue: Experiment Won't Start**

*Symptoms:*
- Experiment status stuck in "initializing"
- No client connections
- FL server not responding

*Diagnosis:*
```bash
# Check FL server status
curl http://localhost:8080/api/v1/health

# Check client connectivity
docker exec flopy-net-client-001 ping fl-server

# Review FL server logs
docker logs flopy-net-fl-server --tail=50
```

*Solutions:*
```bash
# Restart FL server
docker restart flopy-net-fl-server

# Check network configuration
docker network inspect flopy-net-network

# Verify port bindings
docker port flopy-net-fl-server
```

**Issue: Poor FL Performance**

*Symptoms:*
- Slow convergence
- High communication overhead
- Frequent client disconnections

*Diagnosis:*
```bash
# Check network metrics
curl http://localhost:8181/api/v1/statistics

# Analyze client performance
curl http://localhost:3001/api/v1/experiments/exp_001/clients

# Review policy enforcement
curl http://localhost:5000/api/v1/events?severity=warning
```

*Solutions:*
```bash
# Optimize network policies
curl -X PUT http://localhost:5000/api/v1/policies/pol_001 \
  -d '{"actions": [{"type": "allocate_bandwidth", "parameters": {"min_bandwidth": "20Mbps"}}]}'

# Adjust FL parameters
curl -X PUT http://localhost:3001/api/v1/experiments/exp_001 \
  -d '{"configuration": {"local_epochs": 3, "batch_size": 64}}'
```

**Issue: Network Policies Not Enforcing**

*Symptoms:*
- QoS not applied
- Traffic not prioritized
- Policy events missing

*Diagnosis:*
```bash
# Check policy engine status
curl http://localhost:5000/api/v1/health

# Verify SDN controller connection
curl http://localhost:8181/api/v1/health

# Review policy evaluation logs
curl http://localhost:5000/api/v1/events?type=evaluation
```

*Solutions:*
```bash
# Restart policy engine
docker restart flopy-net-policy-engine

# Re-sync with SDN controller
curl -X POST http://localhost:5000/api/v1/sync

# Validate policy configuration
curl http://localhost:5000/api/v1/policies/pol_001/validate
```

### 2. Performance Optimization

**FL Training Optimization:**
```bash
# Reduce communication frequency
curl -X PUT http://localhost:8080/api/v1/config \
  -d '{"aggregation_interval": 120}'  # 2 minutes

# Enable model compression
curl -X PUT http://localhost:8080/api/v1/config \
  -d '{"compression": {"enabled": true, "algorithm": "gzip"}}'

# Optimize client selection
curl -X PUT http://localhost:8080/api/v1/config \
  -d '{"client_selection": {"strategy": "fastest", "max_clients": 5}}'
```

**Network Optimization:**
```bash
# Increase buffer sizes
docker exec flopy-net-sdn-controller \
  ovs-vsctl set Bridge br0 other_config:flow-limit=200000

# Optimize flow table
curl -X POST http://localhost:8181/api/v1/flows/optimize

# Enable hardware offloading
docker exec flopy-net-sdn-controller \
  ethtool -K eth0 rx on tx on
```

### 3. Debug Mode

Enable comprehensive debugging:

```bash
# Enable debug logging
export FLOPY_NET_DEBUG=true
export FLOPY_NET_LOG_LEVEL=debug

# Enable metrics collection
export FLOPY_NET_METRICS_DETAILED=true

# Enable profiling
export FLOPY_NET_PROFILING=true

# Restart with debug settings
docker-compose down
docker-compose up -d
```

**Debug Tools:**
```bash
# Network packet capture
docker exec flopy-net-sdn-controller tcpdump -i any -w /tmp/capture.pcap

# Flow table analysis
docker exec flopy-net-sdn-controller ovs-ofctl dump-flows br0

# Performance profiling
curl http://localhost:8080/api/v1/debug/profile > profile.json
```

### 4. Recovery Procedures

**Experiment Recovery:**
```bash
# Save experiment state
curl http://localhost:3001/api/v1/experiments/exp_001/checkpoint

# Restart from checkpoint
curl -X POST http://localhost:3001/api/v1/experiments/exp_001/recover \
  -d '{"checkpoint_id": "checkpoint_001"}'
```

**System Recovery:**
```bash
# Full system restart
docker-compose down
docker system prune -f
docker-compose up -d

# Database recovery
docker exec flopy-net-collector influx restore --bucket primary backup.tar.gz

# Configuration restore
curl -X POST http://localhost:5000/api/v1/config/restore \
  --data-binary @backup_config.json
```

## Monitoring Best Practices

### 1. Proactive Monitoring

- Set up comprehensive alerts for all critical metrics
- Monitor trends, not just current values
- Use predictive analytics to identify potential issues
- Regularly review and update monitoring thresholds

### 2. Performance Baselines

- Establish baseline performance metrics
- Compare experiments against baselines
- Track performance degradation over time
- Document known performance characteristics

### 3. Documentation

- Document all monitoring procedures
- Maintain troubleshooting runbooks
- Record solutions to common issues
- Keep monitoring configuration in version control

### 4. Automation

- Automate routine monitoring tasks
- Use scripts for common diagnostic procedures
- Implement self-healing where possible
- Create automated reporting and dashboards

## Next Steps

- [Policy Management](./policy-management.md) - Advanced policy configuration and troubleshooting
- [GNS3 Integration](./gns3-integration.md) - Network simulation monitoring
- [Advanced Configurations](../tutorials/advanced-configuration.md) - Expert monitoring setups
- [API Reference](../api/overview.md) - Detailed API documentation for monitoring
