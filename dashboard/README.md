# FLOPY-NET Dashboard

The FLOPY-NET Dashboard is a comprehensive web-based monitoring and control interface for the Federated Learning and SDN Observatory Platform. It provides real-time visualization of Flower-based federated learning training progress, network topology, system metrics, and policy compliance across the entire FLOPY-NET ecosystem.

## Architecture Overview

The dashboard consists of three main components integrated with the FLOPY-NET microservices:

### 1. Frontend (React + TypeScript)
- **Location**: `dashboard/frontend/`
- **Technology Stack**: React 18, TypeScript, Vite, Material-UI, Recharts, ReactFlow
- **Purpose**: Client-side application for data visualization, user interaction, and real-time monitoring
- **Port**: 8085 (default)
- **Features**: Interactive network topology visualization, FL training progress charts, system health monitoring

### 2. Backend (FastAPI)
- **Location**: `dashboard/backend/`
- **Technology Stack**: FastAPI, Python 3.8+, SQLite integration
- **Purpose**: REST API server that aggregates data from Collector (Port 8000), Policy Engine (Port 5000), and SDN Controller (Port 8181)
- **Port**: 8001 (default)
- **API Documentation**: Custom endpoint documentation (not automatic OpenAPI/Swagger)
- **Integration**: Direct communication with all FLOPY-NET microservices via static IP addresses

### 3. Standalone Dashboard (Dash)
- **Location**: `dashboard/app.py`, `dashboard/api.py`, `dashboard/utils.py`
- **Technology Stack**: Dash, Plotly, FastAPI
- **Purpose**: Alternative dashboard implementation with real-time charts and metrics for development/testing
- **Port**: 8050 (Dash), 8051 (API)

## Key Features

### Flower-based Federated Learning Monitoring
- **Training Progress**: Real-time accuracy and loss curves across Flower FL training rounds
- **Client Management**: Monitor participating FL clients (192.168.100.101-102), their status, and training contributions
- **Model Metrics**: Track PyTorch model performance, convergence statistics, and parameter distribution
- **Round Analytics**: Detailed analysis of each federated learning round with Flower framework integration
- **Training Orchestration**: Monitor FL server coordination and client selection policies

### Network Visualization & SDN Integration
- **Topology Mapping**: Interactive network topology visualization using ReactFlow with real-time updates
- **SDN Controller Integration**: Live status of Ryu OpenFlow controller (192.168.100.41) and flow rule monitoring
- **Traffic Analysis**: Network latency, bandwidth utilization, and performance metrics from OpenVSwitch (192.168.100.60)
- **GNS3 Integration**: Live status of GNS3 nodes, links, and network simulation environment
- **Network Policy Visualization**: Flow rules, QoS policies, and traffic shaping status

### Policy Engine Dashboard  
- **Policy Status**: Real-time policy compliance and enforcement status from Policy Engine (192.168.100.20)
- **Security Metrics**: Trust scores, anomaly detection, and security events with detailed event logs
- **Policy Management**: View and monitor active policies, policy decisions, and enforcement actions
- **Compliance Reports**: Historical policy compliance tracking and violation analysis with audit trails
- **Real-time Events**: Live policy evaluation results and decision logging

### System Monitoring
- **Component Health**: Status monitoring of all system components
- **Resource Usage**: CPU, memory, and network resource utilization
- **Event Timeline**: System events, errors, and important notifications
- **Performance Analytics**: Historical performance data and trends

## Quick Start

### Using Docker Compose (Recommended)

1. **Start the entire platform**:
   ```powershell
   docker-compose up -d
   ```

2. **Access the dashboard**:
   - Main Dashboard: http://localhost:8085
   - API Documentation: http://localhost:8001/docs
   - Alternative Dash Interface: http://localhost:8050

### Local Development

#### Frontend Development

1. **Navigate to frontend directory**:
   ```powershell
   cd dashboard\frontend
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

3. **Set environment variables** (create `.env.local`):
   ```env
   VITE_BACKEND_URL=http://localhost:8001
   ```

4. **Start development server**:
   ```powershell
   npm run dev
   ```

#### Backend Development

1. **Navigate to backend directory**:
   ```powershell
   cd dashboard\backend
   ```

2. **Create virtual environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set environment variables** (create `.env`):
   ```env
   GNS3_URL=http://localhost:3080
   POLICY_ENGINE_URL=http://localhost:5000
   COLLECTOR_URL=http://localhost:8002
   ```

5. **Start development server**:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## API Endpoints

The dashboard backend provides the following REST API endpoints:

### Federated Learning
- `GET /fl/status` - Current FL training status
- `GET /fl/metrics` - Training metrics and progress
- `GET /fl/clients` - Connected FL clients information
- `GET /fl/rounds` - Historical round data

### Network Monitoring
- `GET /network/topology` - Network topology data
- `GET /network/devices` - Network device status
- `GET /network/links` - Network link information
- `GET /network/metrics` - Network performance metrics

### Policy Engine
- `GET /policies` - Active policies
- `GET /policies/compliance` - Policy compliance status
- `GET /policies/violations` - Policy violations log

### System Monitoring
- `GET /system/status` - Overall system health
- `GET /system/components` - Component status
- `GET /system/metrics` - System performance metrics

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_URL` | Dashboard backend URL | `http://localhost:8001` |
| `GNS3_URL` | GNS3 server URL | `http://localhost:3080` |
| `POLICY_ENGINE_URL` | Policy Engine URL | `http://localhost:5000` |
| `COLLECTOR_URL` | Collector service URL | `http://localhost:8002` |
| `FL_SERVER_URL` | FL Server URL | `http://localhost:8080` |
| `SDN_CONTROLLER_URL` | SDN Controller URL | `http://localhost:8181` |

### Dashboard Configuration

The dashboard can be configured through:
- Environment variables (highest priority)
- Configuration files in `config/` directory
- Default values in the application code

## Data Sources

The dashboard aggregates data from multiple sources:

1. **Collector Service**: Primary source for metrics, logs, and time-series data
2. **GNS3 API**: Network topology, node status, and simulation data
3. **Policy Engine**: Policy status, compliance data, and security metrics
4. **FL Server**: Training progress, model metrics, and client information
5. **SDN Controller**: Network device status and traffic statistics

## Visualization Components

### Charts and Graphs
- **Line Charts**: Training progress, loss curves, network latency over time
- **Bar Charts**: Trust scores, resource utilization, policy compliance
- **Scatter Plots**: Client performance distribution, network analysis
- **Heatmaps**: Network traffic patterns, correlation matrices

### Network Topology
- **Interactive Graph**: Drag-and-drop network visualization
- **Real-time Updates**: Live status updates for nodes and links
- **Filtering**: Filter by node type, status, or properties
- **Zoom and Pan**: Navigate large network topologies

### Data Tables
- **Client Status**: Sortable and filterable client information
- **Event Logs**: Searchable system events and notifications
- **Policy Violations**: Detailed policy violation reports
- **Performance Metrics**: Tabular system performance data

## Development Guidelines

### Adding New Features

1. **Backend**: Add new API endpoints in `dashboard/backend/app/`
2. **Frontend**: Create new React components in `dashboard/frontend/src/`
3. **Visualization**: Use Recharts for charts, ReactFlow for network graphs
4. **Styling**: Follow Material-UI design system and existing patterns

### Data Integration

1. **Use DashboardConnector**: Centralized data fetching utility
2. **Handle Errors**: Implement proper error handling and fallbacks
3. **Cache Data**: Use appropriate caching strategies for performance
4. **Real-time Updates**: Implement WebSocket or polling for live data

### Testing

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test API endpoints and data flow
- **E2E Tests**: Test complete user workflows
- **Performance Tests**: Monitor dashboard loading and responsiveness

## Troubleshooting

### Common Issues

1. **Dashboard not loading**: Check if backend services are running
2. **No data showing**: Verify service URLs and network connectivity
3. **Slow performance**: Check data caching and update intervals
4. **Layout issues**: Verify browser compatibility and responsive design

### Debugging

- Check browser console for frontend errors
- Monitor backend logs for API issues
- Verify service connectivity using provided test scripts
- Use API documentation at `/docs` for endpoint testing

## Integration with System Components

The dashboard integrates seamlessly with other FLOPY-NET components:

- **Policy Engine**: Enforces dashboard access policies and security rules
- **Collector**: Provides all metrics and time-series data
- **GNS3 Simulator**: Real-time network topology and node status
- **FL Framework**: Training progress, model metrics, and client management
- **SDN Controller**: Network device status and traffic control

For more information about the overall system architecture, see the main project README.md.
