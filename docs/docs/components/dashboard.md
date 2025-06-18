---
sidebar_position: 1
---

# Dashboard Component

The **Dashboard** is the central web-based interface for monitoring and controlling the FLOPY-NET system. It provides real-time visualization of federated learning training progress, network topology, system metrics, and policy compliance through a modern React-based frontend with a FastAPI backend.

## Architecture

The Dashboard follows a three-tier architecture designed for scalability and maintainability:

```mermaid
graph TB
    subgraph "Frontend Layer"
        FE[React Frontend<br/>Port 8085]
        FE --> |TypeScript/Vite| UI[Material-UI Components]
        FE --> |Visualization| VIZ[Recharts/ReactFlow]
        FE --> |WebSocket| WS[Real-time Updates]
    end
    
    subgraph "Backend Layer"
        BE[FastAPI Backend<br/>Port 8001]
        BE --> |REST API| API[Endpoints]
        BE --> |Data Aggregation| AGG[Service Clients]
        BE --> |Caching| CACHE[In-Memory Cache]
    end
    
    subgraph "Data Sources"
        COLLECTOR[Collector Service<br/>Port 8002]
        GNS3[GNS3 Server<br/>Port 3080]
        POLICY[Policy Engine<br/>Port 5000]
        FL[FL Server<br/>Port 8080]
        SDN[SDN Controller<br/>Port 8181]
    end
    
    FE --> |HTTP/WS| BE
    BE --> |HTTP| COLLECTOR
    BE --> |HTTP| GNS3
    BE --> |HTTP| POLICY
    BE --> |HTTP| FL
    BE --> |HTTP| SDN
    
    style FE fill:#79c0ff,stroke:#1f6feb,color:#000
    style BE fill:#d2a8ff,stroke:#8b5cf6,color:#000
    style COLLECTOR fill:#56d364,stroke:#238636,color:#000
    style GNS3 fill:#f85149,stroke:#da3633,color:#fff
    style POLICY fill:#ffa657,stroke:#fb8500,color:#000
```

### Components Overview

#### 1. React Frontend (Port 8085)
- **Technology**: React 18, TypeScript, Vite, Material-UI
- **Purpose**: Interactive web interface for system monitoring
- **Features**: Real-time charts, network topology, responsive design

#### 2. FastAPI Backend (Port 8001)
- **Technology**: FastAPI, Python 3.8+, asyncio
- **Purpose**: REST API server and data aggregation layer
- **Features**: Service health monitoring, data caching, WebSocket support

#### 3. Alternative Dash Interface (Port 8050)
- **Technology**: Dash, Plotly
- **Purpose**: Alternative dashboard implementation
- **Features**: Real-time charts, simplified interface

## Frontend Architecture

### Technology Stack

```json
{
  "dependencies": {
    "@mui/material": "^5.14.18",
    "@mui/icons-material": "^5.14.18",
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "reactflow": "^11.10.1", 
    "recharts": "^2.10.1",
    "chart.js": "^4.4.1",
    "socket.io-client": "^4.8.1",
    "axios": "^1.6.2"
  }
}
```

### Key Features

#### Real-time Monitoring
- **Training Progress**: Live federated learning metrics
- **Network Status**: SDN topology and device health
- **System Metrics**: Resource utilization and performance
- **Policy Compliance**: Security and governance status

#### Interactive Visualization
- **Charts**: Line charts, bar charts, scatter plots, heatmaps
- **Network Topology**: Drag-and-drop graph visualization
- **Data Tables**: Sortable, filterable system information
- **Dashboards**: Customizable widget layouts

#### Responsive Design
- **Mobile-First**: Optimized for all screen sizes
- **Dark Theme**: Modern neon aesthetic matching landing page
- **Accessibility**: WCAG 2.1 AA compliant
- **Performance**: Lazy loading and virtualization

## Backend Architecture

### FastAPI Application Structure

```python
# Core application setup
app = FastAPI(
    title="FLOPY-NET Backend",
    description="API for the Federated Learning SDN Dashboard", 
    version="0.1.0",
    redirect_slashes=False
)

# Service connection management
connection_status = {
    "policy_engine": {"connected": False, "last_check": None, "error": None},
    "gns3": {"connected": False, "last_check": None, "error": None}, 
    "collector": {"connected": False, "last_check": None, "error": None}
}
```

### Service Clients

#### Collector Client
```python
class CollectorApiClient:
    """Client for interacting with the Collector service."""
    
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        
    async def get_metrics(self, params: dict = None) -> dict:
        """Fetch metrics from collector service."""
        
    async def get_fl_metrics(self, params: dict = None) -> dict:
        """Fetch FL-specific metrics."""
        
    async def get_events(self, params: dict = None) -> dict:
        """Fetch system events with pagination."""
```

#### GNS3 Client
```python
class AsyncGNS3Client:
    """Async client for GNS3 server communication."""
    
    def __init__(self, base_url: str = "http://localhost:3080"):
        self.base_url = base_url
        
    async def get_projects(self) -> List[dict]:
        """Get all GNS3 projects."""
        
    async def get_project_topology(self, project_id: str) -> dict:
        """Get network topology for a project."""
        
    async def get_nodes(self, project_id: str) -> List[dict]:
        """Get all nodes in a project."""
```

#### Policy Engine Client
```python
class AsyncPolicyEngineClient:
    """Client for Policy Engine REST API."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        
    async def get_policies(self) -> List[dict]:
        """Get all active policies."""
        
    async def get_policy_compliance(self) -> dict:
        """Get policy compliance status."""
        
    async def get_violations(self) -> List[dict]:
        """Get policy violations log."""
```

## API Endpoints

### Overview Endpoints
- `GET /api/overview/status` - System-wide status overview
- `GET /api/overview/stats` - Key performance indicators
- `GET /api/overview/health` - Service health summary

### FL Monitoring Endpoints
- `GET /api/fl-monitoring/status` - Current training status
- `GET /api/fl-monitoring/metrics` - Training metrics and progress
- `GET /api/fl-monitoring/clients` - Connected client information
- `GET /api/fl-monitoring/rounds` - Historical round data

### Network Endpoints
- `GET /api/network/topology` - Network topology data from GNS3
- `GET /api/network/devices` - Device status and metrics
- `GET /api/network/links` - Link information and statistics
- `GET /api/network/metrics` - Network performance metrics

### Policy Engine Endpoints
- `GET /api/policy-engine/policies` - Active policies
- `GET /api/policy-engine/compliance` - Compliance status
- `GET /api/policy-engine/violations` - Policy violations
- `GET /api/policy-engine/security` - Security metrics

### Events and Logs
- `GET /api/events` - System events with filtering
- `GET /api/events/summary` - Events summary by category
- `WS /ws/logs` - Real-time log streaming
- `GET /api/log/recent` - Recent log entries

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COLLECTOR_URL` | Collector service URL | `http://localhost:8002` |
| `POLICY_ENGINE_URL` | Policy Engine URL | `http://localhost:5000` |
| `GNS3_URL` | GNS3 server URL | `http://localhost:3080` |
| `FL_SERVER_URL` | FL Server URL | `http://localhost:8080` |
| `SDN_CONTROLLER_URL` | SDN Controller URL | `http://localhost:8181` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CONNECTION_RETRIES` | Service connection retries | `3` |
| `HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | `30` |

### Frontend Configuration

```typescript
// src/config/api.ts
export const API_CONFIG = {
  baseURL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001',
  timeout: 10000,
  retries: 3
};

// src/config/websocket.ts
export const WS_CONFIG = {
  url: import.meta.env.VITE_WS_URL || 'ws://localhost:8001',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10
};
```

## Service Integration

### Connection Management

The backend implements sophisticated connection management with health monitoring:

```python
async def test_connection_with_retry(url: str, service_name: str, 
                                   timeout: int = 5, 
                                   max_retries: Optional[int] = None) -> bool:
    """Test connection to a service with retry logic"""
    
    # Service-specific retry logic
    if max_retries is None:
        if service_name == "gns3":
            max_retries = 1  # GNS3 is optional
        else:
            max_retries = settings.CONNECTION_RETRIES
    
    for attempt in range(max_retries):
        try:
            # Service-specific endpoints
            test_url = url
            if service_name == "policy_engine":
                test_url = f"{url}/health"
            elif service_name == "collector": 
                test_url = f"{url}/api/metrics/latest"
            elif service_name == "gns3":
                test_url = f"{url}/v2/version"
                
            # Test connection with timeout
            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, timeout=timeout) as response:
                    if response.status == 200:
                        connection_status[service_name]["connected"] = True
                        return True
                        
        except Exception as e:
            connection_status[service_name]["error"] = str(e)
            if attempt < max_retries - 1:
                await asyncio.sleep(settings.RETRY_DELAY * (2 ** attempt))
    
    return False
```

### Background Health Checks

```python
async def background_health_checks():
    """Background task to periodically check service health"""
    while True:
        await asyncio.sleep(settings.HEALTH_CHECK_INTERVAL)
        
        # Check essential services
        essential_tasks = [
            test_connection_with_retry(settings.POLICY_ENGINE_URL, "policy_engine", 3, 1),
            test_connection_with_retry(settings.COLLECTOR_URL, "collector", 3, 1)
        ]
        
        # Check optional services separately
        gns3_task = test_connection_with_retry(settings.GNS3_URL, "gns3", 2, 1)
        
        await asyncio.gather(*essential_tasks, gns3_task, return_exceptions=True)
```

## Data Visualization

### Chart Components

#### Training Progress
```typescript
// Real-time FL training metrics
const TrainingChart = () => {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    const fetchMetrics = async () => {
      const response = await api.get('/api/fl-monitoring/metrics');
      setData(response.data.rounds);
    };
    
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <LineChart width={600} height={300} data={data}>
      <XAxis dataKey="round" />
      <YAxis />
      <Line type="monotone" dataKey="accuracy" stroke="#79c0ff" />
      <Line type="monotone" dataKey="loss" stroke="#f85149" />
    </LineChart>
  );
};
```

#### Network Topology
```typescript
// Interactive network graph
const NetworkTopology = () => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  
  const onNodeClick = (event, node) => {
    // Handle node selection
    console.log('Node clicked:', node);
  };
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={onNodeClick}
      fitView
    >
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
};
```

### Real-time Updates

```typescript
// WebSocket connection for live updates
const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState(null);
  const [data, setData] = useState(null);
  
  useEffect(() => {
    const ws = io(url);
    
    ws.on('connect', () => {
      console.log('WebSocket connected');
    });
    
    ws.on('data', (newData) => {
      setData(newData);
    });
    
    ws.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });
    
    setSocket(ws);
    
    return () => {
      ws.close();
    };
  }, [url]);
  
  return { socket, data };
};
```

## Deployment

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  dashboard-backend:
    build: ./dashboard/backend
    ports:
      - "8001:8001"
    environment:
      - COLLECTOR_URL=http://collector:8002
      - POLICY_ENGINE_URL=http://policy-engine:5000
      - GNS3_URL=http://gns3:3080
    depends_on:
      - collector
      - policy-engine
      
  dashboard-frontend:
    build: ./dashboard/frontend
    ports:
      - "8085:80"
    environment:
      - VITE_BACKEND_URL=http://localhost:8001
    depends_on:
      - dashboard-backend
```

### Production Deployment

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Health check
curl http://localhost:8001/api/health

# Access dashboard
open http://localhost:8085
```

## Development

### Frontend Development

```bash
# Setup
cd dashboard/frontend
npm install

# Development server
npm run dev

# Build for production
npm run build

# Type checking
npm run build:strict
```

### Backend Development  

```bash
# Setup
cd dashboard/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Development server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run tests
pytest
```

## Monitoring and Debugging

### Health Monitoring

The dashboard provides comprehensive health monitoring:

```python
@app.get("/api/health")
async def health_check():
    """Check the health of the API and connected services."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": connection_status,
        "uptime": time.time() - app.state.start_time
    }
```

### Debug Endpoints

```python
@app.get("/api/test/collector")
async def test_collector_connection():
    """Test endpoint to check collector connectivity."""
    client = CollectorApiClient()
    connected = await client.test_connection()
    
    if not connected:
        return {"status": "error", "message": "Could not connect to collector"}
    
    # Test various collector endpoints
    events = await client.get_events({"limit": 5})
    metrics = await client.get_metrics({"limit": 5})
    summary = await client.get_events_summary()
    
    return {
        "status": "success",
        "connection": "OK",
        "events_count": len(events.get("events", [])),
        "metrics_count": len(metrics.get("metrics", [])),
        "summary": summary
    }
```

### Logging

```python
# Structured logging configuration
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

# Service startup logging
logger.info("🚀 Starting Dashboard API backend...")
logger.info(f"📍 Service URLs:")
logger.info(f"   Collector: {settings.COLLECTOR_URL}")
logger.info(f"   Policy Engine: {settings.POLICY_ENGINE_URL}")
logger.info(f"   GNS3: {settings.GNS3_URL}")
```

## Security

### CORS Configuration

```python
# CORS middleware for cross-origin requests
origins = [
    "http://localhost:8085",    # Local development
    "http://127.0.0.1:8085",    # Alternative local
    "http://localhost:3000",    # Common dev port
]

if os.environ.get("ENVIRONMENT") == "production":
    production_domain = os.environ.get("PRODUCTION_DOMAIN")
    if production_domain:
        origins.append(f"https://{production_domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Input Validation

```python
from pydantic import BaseModel, validator

class MetricsQuery(BaseModel):
    limit: int = 100
    offset: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @validator('limit')
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError('limit cannot exceed 1000')
        return v
```

## Integration with System Components

### Policy Engine Integration
- **Access Control**: Dashboard access governed by policy rules
- **Compliance Monitoring**: Real-time policy compliance status
- **Security Metrics**: Trust scores and security events
- **Violation Alerts**: Automated policy violation notifications

### Collector Integration  
- **Metrics Aggregation**: All system metrics centralized through Collector
- **Event Streaming**: Real-time event data for monitoring
- **Historical Data**: Time-series data for trend analysis
- **Performance Monitoring**: System and component performance metrics

### GNS3 Integration
- **Network Topology**: Live network topology visualization
- **Node Status**: Real-time device status and health
- **Simulation Control**: Basic simulation management capabilities
- **Performance Metrics**: Network performance and latency data

### FL Framework Integration
- **Training Progress**: Real-time federated learning metrics
- **Client Management**: Monitor participating clients
- **Model Performance**: Track accuracy, loss, and convergence
- **Round Analytics**: Detailed analysis of training rounds

The Dashboard serves as the central control plane for the entire FLOPY-NET system, providing administrators and researchers with comprehensive visibility into all aspects of the federated learning and networking infrastructure.
