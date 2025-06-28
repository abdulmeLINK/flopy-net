# Troubleshooting Guide

This comprehensive troubleshooting guide helps you diagnose and resolve common issues in FLOPY-NET, covering system setup, experiment execution, network integration, and performance optimization.

## Quick Diagnostics

### 1. System Health Check

Run a comprehensive health check:

```powershell
# FLOPY-NET System Health Check for Windows PowerShell

Write-Host "=== FLOPY-NET System Health Check ===" -ForegroundColor Green
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "✓ Docker is installed" -ForegroundColor Green
      docker info 2>`$null | Out-Null
    if (`$LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker daemon is running" -ForegroundColor Green
    } else {
        Write-Host "✗ Docker daemon is not running" -ForegroundColor Red
        Write-Host "  Solution: Start Docker Desktop" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Docker is not installed" -ForegroundColor Red
    Write-Host "  Solution: Install Docker Desktop" -ForegroundColor Yellow
}
Write-Host ""

# Check services
Write-Host "Checking FLOPY-NET services..." -ForegroundColor Yellow
`$services = @{
    "policy-engine" = 5000
    "collector" = 8000
    "fl-server" = 8080
}

`$all_healthy = `$true
foreach (`$service in `$services.Keys) {
    `$port = `$services[`$service]
    
    try {
        `$url = "http://localhost:`$port/health"
        `$response = Invoke-WebRequest -Uri `$url -TimeoutSec 5 -UseBasicParsing 2>`$null
        if (`$response.StatusCode -eq 200) {
            Write-Host "✓ `$service is healthy (port `$port)" -ForegroundColor Green
        } else {
            Write-Host "✗ `$service is not responding (port `$port)" -ForegroundColor Red
            `$all_healthy = `$false
        }
    } catch {
        Write-Host "✗ `$service is not responding (port `$port)" -ForegroundColor Red
        `$all_healthy = `$false
    }
}

if (`$all_healthy) {
    Write-Host "✓ All services are healthy" -ForegroundColor Green
} else {
    Write-Host "⚠ Some services need attention" -ForegroundColor Yellow
}
Write-Host ""

# Check Docker containers
Write-Host "Checking Docker containers..." -ForegroundColor Yellow
`$containers = @("policy-engine", "fl-server", "fl-client-1", "fl-client-2", "collector", "sdn-controller")

foreach (`$container in `$containers) {
    `$status = docker ps --filter "name=`$container" --format "`{`{.Status`}`}" 2>`$null
    if (`$status) {
        Write-Host "✓ `$container is running: `$status" -ForegroundColor Green
    } else {
        Write-Host "✗ `$container is not running" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Health Check Complete ===" -ForegroundColor Green
```

### 2. Service Status Check

Check individual service status:

```powershell
# Quick service check
`$services = @("policy-engine", "fl-server", "fl-client-1", "fl-client-2", "collector", "sdn-controller")

foreach (`$service in `$services) {
    `$status = docker ps --filter "name=`$service" --format "`{`{.Status`}`}"
    if (`$status) {
        Write-Host "✓ `$service container is running: `$status" -ForegroundColor Green
        
        # Check specific health endpoints
        switch (`$service) {
            "policy-engine" { 
                try { 
                    Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing | Out-Null
                    Write-Host "  ✓ Policy Engine API responding" -ForegroundColor Green
                } catch {
                    Write-Host "  ✗ Policy Engine API not responding" -ForegroundColor Red
                }
            }
            "collector" { 
                try { 
                    Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Out-Null
                    Write-Host "  ✓ Collector API responding" -ForegroundColor Green
                } catch {
                    Write-Host "  ✗ Collector API not responding" -ForegroundColor Red
                }
            }
        }
    } else {
        Write-Host "✗ `$service container is not running" -ForegroundColor Red
    }
}
```
            "collector") port=8083 ;;
            "policy-engine") port=5000 ;;
            "fl-server") port=8080 ;;
            "sdn-controller") port=8181 ;;        esac
        
        if curl -s -f "http://localhost:\$port/api/v1/health" > /dev/null; then
            echo "✓ \$service API is responding"
        else
            echo "✗ \$service API is not responding"
        fi
    else
        echo "✗ \$service container is not running"
    fi
    echo
done
```

## Common Issues and Solutions

### 1. System Startup Issues

**Issue: Services Won't Start**

*Symptoms:*
- Docker containers not starting
- Port binding errors
- Out of memory errors

*Diagnosis:*
```bash
# Check Docker daemon
sudo systemctl status docker

# Check container logs
docker-compose logs

# Check port conflicts
sudo netstat -tulpn | grep -E "(8001|8085|5000|8080|8083|8181)"

# Check resource availability
free -m
df -h
```

*Solutions:*
```bash
# Restart Docker daemon
sudo systemctl restart docker

# Free up ports (if needed)
sudo fuser -k 8001/tcp  # Dashboard Backend
sudo fuser -k 8085/tcp  # Dashboard Frontend
sudo fuser -k 5000/tcp  # Policy Engine  
sudo fuser -k 8080/tcp  # FL Server
sudo fuser -k 8083/tcp  # Collector
sudo fuser -k 8181/tcp  # SDN Controller

# Increase system limits
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Restart services
docker-compose down
docker-compose up -d
```

**Issue: Database Connection Failures**

*Symptoms:*
- Services can't connect to databases
- Data not persisting
- Database-related errors in logs

*Diagnosis:*
```bash
# Check storage services
docker ps | grep -E "(collector|policy-engine)"

# Check data files
ls -la logs/metrics.db
ls -la logs/events.jsonl

# Check collector storage health (if available)
curl http://localhost:8083/api/health

# Check collector logs
docker logs flopy-net-collector
docker logs flopy-net-policy-engine
```

*Solutions:*
```bash
# Restart core services
docker restart flopy-net-collector flopy-net-policy-engine

# Check if data files exist and are accessible
ls -la logs/
ls -la config/

# Check storage directories
docker exec flopy-net-collector ls -la /app/logs/
docker exec flopy-net-collector ls -la /app/config/
```

### 2. Experiment Execution Issues

**Issue: Experiments Won't Start**

*Symptoms:*
- Experiment stuck in "initializing" state
- No client connections
- FL server not responding

*Diagnosis:*
```bash
# Check FL server status
curl http://localhost:8080/api/v1/health

# Check FL server status and training info
curl http://localhost:8080/health

# Check client connectivity
docker exec flopy-net-client-001 ping flopy-net-fl-server
docker exec flopy-net-client-001 curl http://flopy-net-fl-server:8080/api/v1/health

# Check FL server logs
docker logs flopy-net-fl-server --tail=50

# Check client logs
docker logs flopy-net-client-001 --tail=50
```

*Solutions:*
```bash
# Restart FL server
docker restart flopy-net-fl-server

# Reset FL server if needed
curl -X POST http://localhost:8080/reset

# Check network connectivity between containers
docker network inspect flopy-net-network

# Restart clients
docker-compose restart fl-client-001 fl-client-002 fl-client-003
```

**Issue: Poor FL Performance**

*Symptoms:*
- Slow convergence
- High communication overhead
- Frequent client disconnections

*Diagnosis:*
```bash
# Analyze FL metrics
curl http://localhost:8083/api/v1/metrics/query?metric=global_accuracy&experiment_id=$experiment_id

# Check network statistics
curl http://localhost:8181/api/v1/statistics

# Monitor resource usage
docker stats

# Check policy enforcement
curl http://localhost:5000/api/v1/events?experiment_id=$experiment_id
```

*Solutions:*
```bash
# Configure FL server parameters
curl -X POST http://localhost:8080/configure \
  -H "Content-Type: application/json" \
  -d '{
    "local_epochs": 3,
    "batch_size": 64,
    "clients_per_round": 3
  }'

# Improve network conditions
curl -X POST http://localhost:5000/api/v1/policies/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "experiment_id": "'$experiment_id'",
      "performance_issue": "slow_convergence"
    }
  }'

# Scale resources
docker-compose up --scale fl-client=5
```

### 3. Network and Policy Issues

**Issue: Policies Not Enforcing**

*Symptoms:*
- QoS not applied
- Traffic not prioritized
- Policy events missing

*Diagnosis:*
```bash
# Check policy engine status
curl http://localhost:5000/api/v1/health

# List active policies
curl http://localhost:5000/api/v1/policies?status=active

# Check policy evaluation events
curl http://localhost:5000/api/v1/events?type=evaluation&limit=10

# Verify SDN controller connection
curl http://localhost:8181/api/v1/health

# Check flow rules
curl http://localhost:8181/api/v1/flows
```

*Solutions:*
```bash
# Restart policy engine
docker restart flopy-net-policy-engine

# Force policy evaluation
curl -X POST http://localhost:5000/api/v1/policies/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "traffic_type": "fl_communication",
      "experiment_status": "running"
    },
    "dry_run": false
  }'

# Sync with SDN controller
curl -X POST http://localhost:5000/api/v1/sync

# Validate policy configuration
policy_id="your_policy_id"
curl http://localhost:5000/api/v1/policies/$policy_id/validate
```

**Issue: Network Connectivity Problems**  

*Symptoms:*
- Clients can't reach server
- High latency/packet loss
- Network partitions

*Diagnosis:*
```bash
# Test connectivity
docker exec flopy-net-client-001 ping flopy-net-fl-server
docker exec flopy-net-client-001 traceroute flopy-net-fl-server

# Check network configuration
docker network ls
docker network inspect flopy-net-network

# Monitor network interface
docker exec flopy-net-sdn-controller ip addr show
docker exec flopy-net-sdn-controller ss -tulpn

# Check flow tables
docker exec flopy-net-sdn-controller ovs-ofctl dump-flows br0
```

*Solutions:*
```bash
# Recreate network
docker network rm flopy-net-network
docker-compose up -d

# Reset SDN controller
docker restart flopy-net-sdn-controller

# Clear flow tables
docker exec flopy-net-sdn-controller ovs-ofctl del-flows br0

# Restart networking
docker-compose restart sdn-controller
```

### 4. Performance Issues

**Issue: High Resource Usage**

*Symptoms:*
- High CPU/memory usage
- Slow response times
- System becoming unresponsive

*Diagnosis:*
```bash
# Monitor resource usage
docker stats --no-stream

# Check system resources
top -bn1 | head -20
free -m
iostat -x 1 5

# Check disk I/O
iotop -a -o

# Monitor network usage
iftop -t -s 60
```

*Solutions:*
```bash
# Optimize container resources
docker-compose down
# Edit docker-compose.yml to add resource limits:
# deploy:
#   resources:
#     limits:
#       cpus: '2.0'
#       memory: 4G
docker-compose up -d

# Clean up logs
docker system prune -f
sudo journalctl --vacuum-time=1week

# Check SQLite database size and performance
ls -lh logs/metrics.db
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA integrity_check;"

# Scale down if necessary
docker-compose up --scale fl-client=3
```

**Issue: Slow Database Operations**

*Symptoms:*
- Slow metrics queries
- Database timeouts  
- High storage I/O

*Diagnosis:*
```bash
# Check SQLite database performance
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA quick_check;"
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA table_info(metrics);"

# Check storage usage
du -sh logs/
docker exec flopy-net-collector df -h /app/logs/

# Check collector logs for slow queries
docker logs flopy-net-collector --tail=100 | grep -i "slow\|timeout"
```

*Solutions:*
```bash
# Optimize SQLite performance
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA optimize;"
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA journal_mode=WAL;"
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA synchronous=NORMAL;"

# Clean up old data (if cleanup is not working)
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "DELETE FROM metrics WHERE timestamp < datetime('now', '-7 days');"

# Check database size
docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA page_count; PRAGMA page_size;"
```

## Advanced Troubleshooting

### 1. Debug Mode

Enable comprehensive debugging:

```bash
# Set debug environment variables
export FLOPY_NET_DEBUG=true
export FLOPY_NET_LOG_LEVEL=debug
export FLOPY_NET_METRICS_DETAILED=true

# Update docker-compose.yml with debug settings
cat >> docker-compose.override.yml << EOF
version: '3.8'
services:
  dashboard:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
  
  collector:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
      
  policy-engine:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
      
  fl-server:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
EOF

# Restart with debug mode
docker-compose down
docker-compose up -d
```

### 2. Log Analysis

Comprehensive log analysis:

```bash
#!/bin/bash
# Log Analysis Script

echo "Analyzing FLOPY-NET logs..."

# Create log directory
mkdir -p logs
cd logs

# Collect logs from all services
services=("dashboard" "collector" "policy-engine" "fl-server" "sdn-controller")
for service in "\${services[@]}"; do
    echo "Collecting logs for \$service..."
    docker logs flopy-net-\$service > \${service}.log 2>&1
done

# Analyze error patterns
echo "Error Analysis:"
echo "=============="
for service in "\${services[@]}"; do
    error_count=\$(grep -c "ERROR\\|Exception\\|Failed" \${service}.log)
    if [ \$error_count -gt 0 ]; then
        echo "\$service: \$error_count errors found"
        echo "Recent errors:"
        grep "ERROR\\|Exception\\|Failed" \${service}.log | tail -5
        echo
    fi
done

# Find performance issues
echo "Performance Issues:"
echo "=================="
grep -i "slow\|timeout\|memory\|cpu" *.log | head -10

# Network connectivity issues
echo "Network Issues:"
echo "=============="
grep -i "connection\|refused\|unreachable" *.log | head -10
```

### 3. Network Debugging

Deep network troubleshooting:

```bash
#!/bin/bash
# Network Debugging Script

echo "Network Debugging for FLOPY-NET"
echo "==============================="

# Check Docker networks
echo "Docker Networks:"
docker network ls
echo

# Inspect FLOPY-NET network
echo "FLOPY-NET Network Details:"
docker network inspect flopy-net-network | jq '.[0].Containers'
echo

# Test connectivity between services
services=("dashboard" "collector" "policy-engine" "fl-server" "sdn-controller")
echo "Service Connectivity Test:"
for src in "\${services[@]}"; do
    for dst in "\${services[@]}"; do
        if [ "\$src" != "\$dst" ]; then
            if docker exec flopy-net-\$src ping -c 1 flopy-net-\$dst > /dev/null 2>&1; then
                echo "✓ \$src -> \$dst"
            else
                echo "✗ \$src -> \$dst"
            fi
        fi
    done
done
echo

# Check port accessibility
echo "Port Accessibility:"
ports=("8001:dashboard-backend" "8083:collector" "5000:policy-engine" "8080:fl-server" "8181:sdn-controller")
for port_service in "\${ports[@]}"; do
    port=\${port_service%:*}
    service=\${port_service#*:}    
    if nc -z localhost \$port; then
        echo "✓ Port \$port (\$service) is accessible"
    else
        echo "✗ Port \$port (\$service) is not accessible"
    fi
done

# Check SDN network state
echo
echo "SDN Network State:"
if docker exec flopy-net-sdn-controller ovs-vsctl show 2>/dev/null; then
    echo "OpenVSwitch is running"
    docker exec flopy-net-sdn-controller ovs-ofctl dump-flows br0 2>/dev/null | head -10
else
    echo "OpenVSwitch is not running or not configured"
fi
```

### 4. Performance Profiling

Profile system performance:

```python
#!/usr/bin/env python3
"""
FLOPY-NET Performance Profiler
"""

import time
import requests
import psutil
import docker
from datetime import datetime, timedelta

class FLOPYProfiler:
    def __init__(self):
        self.client = docker.from_env()
        self.services = [
            'flopy-net-dashboard',
            'flopy-net-collector', 
            'flopy-net-policy-engine',
            'flopy-net-fl-server',
            'flopy-net-sdn-controller'
        ]
    
    def profile_system(self, duration_minutes=5):
        """Profile system performance for specified duration"""
        
        print(f"Starting {duration_minutes}-minute performance profile...")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        metrics = []
        
        while datetime.now() < end_time:
            timestamp = datetime.now()
            
            # System metrics
            system_metrics = {
                'timestamp': timestamp,
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_io': psutil.disk_io_counters(),
                'network_io': psutil.net_io_counters()
            }
            
            # Container metrics
            container_metrics = {}
            for service in self.services:
                try:
                    container = self.client.containers.get(service)
                    stats = container.stats(stream=False)
                    
                    container_metrics[service] = {
                        'cpu_percent': self.calculate_cpu_percent(stats),
                        'memory_usage': stats['memory_stats'].get('usage', 0),
                        'memory_limit': stats['memory_stats'].get('limit', 0),
                        'network_rx': stats['networks']['eth0']['rx_bytes'],
                        'network_tx': stats['networks']['eth0']['tx_bytes']
                    }
                except Exception as e:
                    print(f"Error getting stats for {service}: {e}")
            
            # API response times
            api_metrics = self.measure_api_response_times()
            
            metrics.append({
                'system': system_metrics,
                'containers': container_metrics,
                'api': api_metrics
            })
            
            time.sleep(30)  # Sample every 30 seconds
        
        self.generate_report(metrics)
    
    def calculate_cpu_percent(self, stats):
        """Calculate CPU percentage from Docker stats"""
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        
        if system_delta > 0 and cpu_delta > 0:
            return (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
        return 0
    
    def measure_api_response_times(self):
        """Measure API response times"""
        apis = [
            ('dashboard', 'http://localhost:8001/api/health'),
            ('collector', 'http://localhost:8083/api/v1/health'),
            ('policy-engine', 'http://localhost:5000/api/v1/health'),
            ('fl-server', 'http://localhost:8080/api/v1/health'),
            ('sdn-controller', 'http://localhost:8181/api/v1/health')
        ]
        
        response_times = {}
        
        for service, url in apis:
            try:
                start = time.time()
                response = requests.get(url, timeout=5)
                end = time.time()
                
                response_times[service] = {
                    'response_time': (end - start) * 1000,  # ms
                    'status_code': response.status_code,
                    'success': response.status_code == 200
                }
            except Exception as e:
                response_times[service] = {
                    'response_time': None,
                    'status_code': None,
                    'success': False,
                    'error': str(e)
                }
        
        return response_times
    
    def generate_report(self, metrics):
        """Generate performance report"""
        
        print("\nPerformance Profile Report")
        print("=" * 50)
        
        # System summary
        cpu_avg = sum(m['system']['cpu_percent'] for m in metrics) / len(metrics)
        memory_avg = sum(m['system']['memory_percent'] for m in metrics) / len(metrics)
        
        print(f"Average CPU Usage: {cpu_avg:.2f}%")
        print(f"Average Memory Usage: {memory_avg:.2f}%")
        
        # Container summary
        print("\nContainer Performance:")
        for service in self.services:
            service_metrics = [m['containers'].get(service, {}) for m in metrics if service in m['containers']]
            if service_metrics:
                avg_cpu = sum(m.get('cpu_percent', 0) for m in service_metrics) / len(service_metrics)
                avg_memory = sum(m.get('memory_usage', 0) for m in service_metrics) / len(service_metrics) / 1024 / 1024  # MB
                print(f"  {service}: CPU {avg_cpu:.2f}%, Memory {avg_memory:.2f}MB")
        
        # API performance
        print("\nAPI Response Times:")
        for service in ['dashboard', 'collector', 'policy-engine', 'fl-server', 'sdn-controller']:
            api_metrics = [m['api'].get(service, {}) for m in metrics if service in m['api']]
            response_times = [m.get('response_time') for m in api_metrics if m.get('response_time')]
            
            if response_times:
                avg_response = sum(response_times) / len(response_times)
                success_rate = sum(1 for m in api_metrics if m.get('success', False)) / len(api_metrics)
                print(f"  {service}: {avg_response:.2f}ms avg, {success_rate:.2%} success rate")

if __name__ == "__main__":
    profiler = FLOPYProfiler()
    profiler.profile_system(duration_minutes=5)
```

## Recovery Procedures

### 1. Service Recovery

Automated service recovery:

```bash
#!/bin/bash
# Service Recovery Script

recover_service() {
    local service=$1
    local port=$2
    
    echo "Recovering $service..."
    
    # Stop service
    docker stop flopy-net-$service 2>/dev/null
    
    # Remove container
    docker rm flopy-net-$service 2>/dev/null
    
    # Recreate and start service
    docker-compose up -d $service
    
    # Wait for service to start
    echo "Waiting for $service to start..."
    for i in {1..30}; do        if curl -s -f http://localhost:\$port/api/v1/health > /dev/null; then
            echo "✓ \$service is healthy"
            return 0
        fi
        sleep 2
    done
    
    echo "✗ \$service failed to recover"
    return 1
}

# Recover all services
services=(
    "dashboard-backend:8001"
    "collector:8083"
    "policy-engine:5000"
    "fl-server:8080"
    "sdn-controller:8181"
)

for service_port in "\${services[@]}"; do
    service=\${service_port%:*}
    port=\${service_port#*:}
    
    if ! curl -s -f http://localhost:\$port/api/v1/health > /dev/null; then
        recover_service \$service \$port
    else
        echo "✓ \$service is already healthy"
    fi
done
```

### 2. Data Recovery

Backup and restore procedures:

```bash
#!/bin/bash
# Data Backup and Recovery

backup_data() {
    echo "Creating data backup..."
      backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    
    # Backup SQLite database and logs
    echo "Backing up data files..."
    cp logs/metrics.db $backup_dir/metrics.db 2>/dev/null || echo "No metrics.db found"
    cp logs/events.jsonl $backup_dir/events.jsonl 2>/dev/null || echo "No events.jsonl found"
    cp -r logs/ $backup_dir/logs/ 2>/dev/null || echo "No logs directory found"
    
    # Backup configurations
    echo "Backing up configurations..."
    cp -r config/ $backup_dir/config/
    
    echo "Backup completed: $backup_dir"
}

restore_data() {
    local backup_dir=$1
    
    if [ ! -d "$backup_dir" ]; then
        echo "Backup directory not found: $backup_dir"
        return 1
    fi
    
    echo "Restoring data from $backup_dir..."
      # Stop services
    docker-compose down
    
    # Restore data files
    if [ -f "$backup_dir/metrics.db" ]; then
        echo "Restoring SQLite database..."
        cp $backup_dir/metrics.db logs/metrics.db
    fi
    
    if [ -f "$backup_dir/events.jsonl" ]; then
        echo "Restoring events log..."
        cp $backup_dir/events.jsonl logs/events.jsonl
    fi
    
    if [ -d "$backup_dir/logs" ]; then
        echo "Restoring log files..."
        cp -r $backup_dir/logs/* logs/ 2>/dev/null || true
    fi
    
    # Restore configurations
    if [ -d "$backup_dir/config" ]; then
        echo "Restoring configurations..."
        cp -r $backup_dir/config/* config/
    fi
    
    # Start all services
    docker-compose up -d
    
    echo "Data restoration completed"
}

# Usage examples:
# backup_data
# restore_data "backups/20240115_143000"
```

### 3. Complete System Recovery

Full system recovery procedure:

```bash
#!/bin/bash
# Complete System Recovery

echo "Starting complete system recovery..."

# 1. Stop all services
echo "Stopping all services..."
docker-compose down -v

# 2. Clean up Docker resources
echo "Cleaning up Docker resources..."
docker system prune -f
docker volume prune -f
docker network prune -f

# 3. Remove and recreate network
echo "Recreating network..."
docker network rm flopy-net-network 2>/dev/null
docker network create flopy-net-network

# 4. Pull latest images
echo "Pulling latest images..."
docker-compose pull

# 5. Rebuild services
echo "Rebuilding services..."
docker-compose build --no-cache

# 6. Start services in order
echo "Starting core services..."
docker-compose up -d collector policy-engine sdn-controller
sleep 20

echo "Starting FL services..."
docker-compose up -d fl-server
sleep 20

echo "Starting FL services..."
docker-compose up -d fl-server dashboard
sleep 10

echo "Starting clients..."
docker-compose up -d

# 7. Verify system health
echo "Verifying system health..."
sleep 30

healthy=true
services=("collector:8083" "policy-engine:5000" "fl-server:8080" "sdn-controller:8181")
for service_port in "\${services[@]}"; do
    service=\${service_port%:*}
    port=\${service_port#*:}
    
    if curl -s -f http://localhost:\$port/health > /dev/null; then
        echo "✓ \$service is healthy"
    else
        echo "✗ \$service is not healthy"
        healthy=false
    fi
done

if [ "\$healthy" = true ]; then
    echo "✓ System recovery completed successfully"
else
    echo "⚠ System recovery completed with issues"
    echo "Check individual service logs for details"
fi
```

## Prevention and Monitoring

### 1. Proactive Monitoring

Set up continuous monitoring:

```bash
#!/bin/bash
# Continuous Health Monitoring

monitor_system() {
    while true; do
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
          # Check service health        all_healthy=true
        services=("collector:8083" "policy-engine:5000" "fl-server:8080" "sdn-controller:8181")
        
        for service_port in "\${services[@]}"; do
            service=\${service_port%:*}
            port=\${service_port#*:}
            
            if ! curl -s -f --max-time 10 http://localhost:\$port/health > /dev/null; then
                echo "[\$timestamp] ALERT: \$service is unhealthy"
                all_healthy=false
                
                # Attempt automatic recovery
                echo "[\$timestamp] Attempting to recover \$service..."
                docker restart flopy-net-\$service
            fi
        done
        
        if [ "\$all_healthy" = true ]; then
            echo "[\$timestamp] All services healthy"
        fi
        
        # Check resource usage
        cpu_usage=\$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | cut -d'%' -f1)
        memory_percent=\$(free | awk 'NR==2{printf "%.0f", \$3*100/\$2 }')
        
        if (( \$(echo "\$cpu_usage > 90" | bc -l) )); then
            echo "[\$timestamp] ALERT: High CPU usage: \${cpu_usage}%"
        fi        
        if [ "\$memory_percent" -gt 90 ]; then
            echo "[\$timestamp] ALERT: High memory usage: \${memory_percent}%"
        fi
        
        sleep 60  # Check every minute
    done
}

# Run in background
monitor_system &
echo $! > monitor.pid
echo "Health monitoring started (PID: $(cat monitor.pid))"
```

### 2. Automated Maintenance

Schedule regular maintenance:

```bash
#!/bin/bash
# Automated Maintenance Script

perform_maintenance() {
    echo "Starting automated maintenance..."
      # Clean up old logs
    echo "Cleaning up logs..."
    find logs/ -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Optimize SQLite database
    echo "Optimizing database..."
    docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "PRAGMA optimize;"
    docker exec flopy-net-collector sqlite3 /app/logs/metrics.db "VACUUM;"
    
    # Update container images
    echo "Checking for image updates..."
    docker-compose pull
    
    # Clean up Docker resources
    echo "Cleaning up Docker resources..."
    docker system prune -f
    docker volume prune -f
    
    # Create backup
    echo "Creating backup..."
    backup_data
    
    echo "Maintenance completed"
}

# Add to crontab for weekly execution:
# 0 2 * * 0 /path/to/maintenance.sh
```

## Getting Help

### 1. Collecting Debug Information

Gather comprehensive debug information:

```bash
#!/bin/bash
# Debug Information Collection

debug_info_dir="debug_$(date +%Y%m%d_%H%M%S)"
mkdir -p $debug_info_dir

echo "Collecting debug information..."

# System information
echo "System Information:" > $debug_info_dir/system_info.txt
uname -a >> $debug_info_dir/system_info.txt
lsb_release -a >> $debug_info_dir/system_info.txt
docker version >> $debug_info_dir/system_info.txt
docker-compose version >> $debug_info_dir/system_info.txt

# Resource usage
echo "Resource Usage:" > $debug_info_dir/resources.txt
free -m >> $debug_info_dir/resources.txt
df -h >> $debug_info_dir/resources.txt
docker stats --no-stream >> $debug_info_dir/resources.txt

# Service logs
echo "Collecting service logs..."
services=("dashboard" "collector" "policy-engine" "fl-server" "sdn-controller")
for service in "${services[@]}"; do
    docker logs flopy-net-$service > $debug_info_dir/${service}_logs.txt 2>&1
done

# Configuration files
echo "Collecting configuration..."
cp -r config/ $debug_info_dir/
cp docker-compose.yml $debug_info_dir/
cp .env $debug_info_dir/ 2>/dev/null

# Network information
echo "Network Information:" > $debug_info_dir/network.txt
docker network ls >> $debug_info_dir/network.txt
docker network inspect flopy-net-network >> $debug_info_dir/network.txt

# Create archive
tar -czf ${debug_info_dir}.tar.gz $debug_info_dir/
rm -rf $debug_info_dir

echo "Debug information collected: ${debug_info_dir}.tar.gz"
echo "Please attach this file when reporting issues"
```

### 2. Support Channels

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the comprehensive documentation
- **Community Forum**: Get help from the community
- **Email Support**: Do not prefer :) If urgent use -> abdulmeliksaylan@gmail.com

### 3. Reporting Issues

When reporting issues, please include:

1. Debug information archive
2. Steps to reproduce the issue
3. Expected vs actual behavior
4. Environment details (OS, hardware, etc.)
5. Error messages and stack traces

## Next Steps

- [Policy Management](./policy-management.md) - Advanced policy troubleshooting
- [GNS3 Integration](./gns3-integration.md) - Network simulation troubleshooting  
- [Development Guide](../development/setup.md) - Setting up development environment
- [API Reference](../api/overview.md) - Complete API documentation
