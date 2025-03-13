# FL-SDN Dashboard

This dashboard provides a comprehensive visualization and management interface for the Federated Learning and Software-Defined Networking (FL-SDN) integration system.

## Features

- **Scenario Visualization**: Simulate and visualize different FL-SDN scenarios, each with distinct use cases, network conditions, and policies
- **Network Topology**: Interactive visualization of the network topology, showing servers, gateways, clients, and connections
- **FL Metrics**: Track federated learning progress including accuracy, loss, and training times
- **Policy Monitoring**: View active policies and their execution history
- **Real-time Updates**: Auto-refresh capability for real-time monitoring

## Scenarios

The dashboard includes the following pre-configured scenarios:

1. **Smart City Traffic Management**
   - Use case: Optimizing traffic signals using FL from distributed traffic cameras and sensors
   - Network: Normal operation with stable conditions
   - Key metrics: Traffic flow improvement, prediction accuracy, signal timing efficiency

2. **Healthcare IoT Monitoring**
   - Use case: Medical device data aggregation for patient monitoring
   - Network: Experiencing congestion due to high data volume
   - Key metrics: Alert latency, anomaly detection rate, false alarm rate

3. **Financial Fraud Detection**
   - Use case: Cross-institutional fraud detection
   - Network: Contains potentially malicious nodes attempting to compromise the model
   - Key metrics: Fraud detection rate, false positive rate, model robustness

4. **Mobile Keyboard Prediction**
   - Use case: Next word prediction on mobile devices
   - Network: Resource-constrained environments (limited battery, computing resources)
   - Key metrics: Word prediction accuracy, battery consumption, model size

## Installation

Ensure you have all required dependencies installed:

```bash
pip install -r requirements.txt
```

## Running the Dashboard

The dashboard consists of two components:
1. A Dash web application for the user interface
2. A FastAPI backend that serves data to the UI

You can run both components with a single command:

```bash
python -m dashboard.run
```

This will start:
- The web interface at http://localhost:8050
- The API server at http://localhost:8051

### Command-line Options

- `--dash-only`: Run only the web interface
- `--api-only`: Run only the API server
- `--dash-port PORT`: Specify a custom port for the web interface (default: 8050)
- `--api-port PORT`: Specify a custom port for the API server (default: 8051)
- `--debug`: Run in debug mode

Example:
```bash
python -m dashboard.run --dash-port 8080 --api-port 8081 --debug
```

## Dashboard Usage

1. **Selecting a Scenario**:
   - Use the radio buttons in the "Simulation Scenarios" panel to choose a scenario
   - The dashboard will update all visualizations to reflect the selected scenario

2. **Refreshing Data**:
   - Click the "Refresh Data" button to manually update all metrics
   - Toggle "Auto-Refresh" to enable/disable automatic updates every 10 seconds

3. **Exploring Metrics**:
   - Navigate through the different tabs in each panel to explore different aspects of the system
   - Hover over visualizations for detailed information

## API Endpoints

The dashboard API provides the following endpoints:

- `GET /metrics/all`: Get all metrics for the dashboard
- `GET /fl/metrics`: Get Federated Learning metrics
- `GET /network/metrics`: Get network metrics
- `GET /policies`: Get policy information
- `GET /app/metrics`: Get application-specific metrics
- `GET /scenarios/list`: List available simulation scenarios
- `POST /scenarios/set/{scenario_id}`: Set the active scenario

## Architecture

The dashboard follows a modular architecture:

- `app.py`: Dash web application
- `api.py`: FastAPI backend
- `scenarios.py`: Scenario simulation engine
- `run.py`: CLI runner for both components

## Customization

To add new scenarios or extend existing ones, modify the `ScenarioManager` class in `scenarios.py`. The class provides a framework for defining:

- Network topologies
- FL model behavior
- Application-specific metrics
- Policies and their activation conditions

## Contributing

Contributions to enhance the dashboard are welcome. Please ensure that any new features maintain compatibility with the existing architecture. 