# API Tests

This directory contains test utilities for the Federated Learning Metrics API.

## Test Metrics Generator

The `test_metrics.py` script generates sample metrics and sends them to the metrics API server. This is useful for:

1. Testing the API server without running a full simulation
2. Generating realistic-looking metrics for development and debugging
3. Demonstrating the API functionality to users

## Using with Real or Mock Data

The API can work with both real and mock data:

### Real Data Mode

When using real data from a simulation:

1. Configure your system to use real components:
```python
# In config/fl_config.py:
DEFAULT_CONFIG = {
    "use_real_data": True,
    "use_real_model": True, 
    "use_real_training": True,
    "track_real_resources": True,
    "log_real_metrics": True,
    # ...
}
```

2. Launch the FL system with the API enabled:
```bash
python src/run_fl_system.py --enable-api
```

This will collect and expose actual training metrics through the API.

### Mock Data Mode

For development and testing:

1. Start the API server with mock data generation:
```bash
python scripts/start_api_server.py --generate-mock-data
```

2. Or configure mock data in config:
```python
# In config/fl_config.py:
DEFAULT_CONFIG = {
    "enable_api": True,
    "api_host": "localhost",
    "api_port": 5000,
    "use_mock_data": True,
    "mock_rounds": 10,
    "mock_interval": 2.0
}
```

## Running Tests Directly

You can also run the test metrics generator directly:

```bash
cd tests/api
python test_metrics.py --api-url http://localhost:5000 --rounds 10 --interval 2.0
```

This will generate and send mock metrics to the API server.

## Accessing Metrics

Once the API is running (with either real or mock data), you can access metrics:

1. Through the REST API:
```bash
curl http://localhost:5000/metrics/current
curl http://localhost:5000/all
```

2. Using the client library:
```python
from src.api.client import FLMetricsClient

client = FLMetricsClient()
metrics = client.get_all_metrics()
print(f"Current accuracy: {metrics['current'].get('accuracy', 0)}")
```

3. Via WebSockets for real-time updates (see `docs/metrics_api.md` for examples) 