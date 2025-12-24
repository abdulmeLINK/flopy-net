# FLOPY-NET Testing Implementation Plan

## Phase 1: Quick Start - Getting Tests Running

### Step 1: Create pytest configuration

Create `pytest.ini` in the project root:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    -ra
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (may require services)
    e2e: End-to-end tests (require Docker/GNS3)
    slow: Slow tests (skip with -m "not slow")
    security: Security-related tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

### Step 2: Create conftest.py

```python
# tests/conftest.py
import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# === FIXTURES: Configuration ===

@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory for tests."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def mock_network_config() -> Dict[str, Any]:
    """Provide a mock network addressing configuration."""
    return {
        "subnet": "192.168.100.0/24",
        "subnet_prefix": "192.168.100",
        "gateway": "192.168.100.1",
        "services": {
            "fl_server": {
                "ip": "192.168.100.10",
                "port": 8080,
                "range": "192.168.100.10-19"
            },
            "policy_engine": {
                "ip": "192.168.100.20",
                "port": 5000,
                "range": "192.168.100.20-29"
            },
            "collector": {
                "ip": "192.168.100.40",
                "port": 8000,
                "range": "192.168.100.40-49"
            },
            "fl_clients": {
                "base_ip": "192.168.100.101",
                "range": "192.168.100.100-255",
                "max_clients": 155
            }
        }
    }


@pytest.fixture
def network_config_file(test_config_dir, mock_network_config):
    """Create a network config file for testing."""
    config_path = test_config_dir / "network_addressing.json"
    with open(config_path, 'w') as f:
        json.dump(mock_network_config, f)
    return str(config_path)


# === FIXTURES: FL Server ===

@pytest.fixture
def fl_server_config() -> Dict[str, Any]:
    """Provide a mock FL server configuration."""
    return {
        "host": "0.0.0.0",
        "port": 8080,
        "rounds": 3,
        "min_clients": 2,
        "min_available_clients": 2,
        "model": "cnn",
        "dataset": "mnist",
        "stay_alive_after_training": False,
        "results_dir": "./results",
        "metrics_host": "0.0.0.0",
        "metrics_port": 8081,
        "policy_engine_url": "http://localhost:5000"
    }


@pytest.fixture
def fl_client_config() -> Dict[str, Any]:
    """Provide a mock FL client configuration."""
    return {
        "client_id": "test_client_1",
        "server_host": "192.168.100.10",
        "server_port": 8080,
        "model": "cnn",
        "dataset": "mnist",
        "local_epochs": 1,
        "batch_size": 32,
        "learning_rate": 0.01
    }


# === FIXTURES: Policy Engine ===

@pytest.fixture
def policy_config() -> Dict[str, Any]:
    """Provide a mock policy configuration."""
    return {
        "policies": [
            {
                "id": "test_policy_1",
                "name": "Test Policy",
                "enabled": True,
                "priority": 1,
                "conditions": {
                    "model_size_mb": {"max": 100}
                },
                "actions": {
                    "allow": True
                }
            }
        ]
    }


# === FIXTURES: Mocks ===

@pytest.fixture
def mock_policy_engine():
    """Create a mock policy engine client."""
    mock = MagicMock()
    mock.check_policy.return_value = {
        "allowed": True,
        "policy_id": "test_policy",
        "reason": "Test allowed"
    }
    return mock


@pytest.fixture
def mock_flower_client():
    """Create a mock Flower client."""
    mock = MagicMock()
    mock.fit.return_value = ([], 100, {"loss": 0.5})
    mock.evaluate.return_value = (0.5, 100, {"accuracy": 0.95})
    return mock


@pytest.fixture
def mock_gns3_api():
    """Create a mock GNS3 API client."""
    mock = MagicMock()
    mock.get_project.return_value = {"project_id": "test-project"}
    mock.get_nodes.return_value = []
    return mock


# === FIXTURES: HTTP Responses ===

@pytest.fixture
def mock_http_responses():
    """Set up mock HTTP responses using responses library."""
    import responses
    
    @responses.activate
    def _mock_responses():
        return responses
    
    return _mock_responses


# === AUTOUSE FIXTURES ===

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset NetworkAddressing singleton
    from src.core.config.network_addressing import NetworkAddressing
    NetworkAddressing._instance = None
    yield


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Isolate environment variables for each test."""
    # Clear FL-related environment variables
    for key in list(os.environ.keys()):
        if key.startswith(('FL_', 'GNS3_', 'POLICY_', 'NETWORK_')):
            monkeypatch.delenv(key, raising=False)
```

---

## Phase 1 Implementation: First Test File

### test_network_addressing.py

```python
# tests/unit/core/config/test_network_addressing.py
"""
Unit tests for NetworkAddressing configuration management.

Tests the centralized network addressing singleton that provides
IP addresses and URLs for all FLOPY-NET services.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open


class TestNetworkAddressing:
    """Test suite for NetworkAddressing class."""

    def test_singleton_pattern(self, network_config_file, monkeypatch):
        """Test that NetworkAddressing follows singleton pattern."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None  # Reset singleton
        
        instance1 = NetworkAddressing()
        instance2 = NetworkAddressing()
        
        assert instance1 is instance2

    def test_get_service_ip_fl_server(self, network_config_file, monkeypatch):
        """Test getting FL server IP address."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        ip = addressing.get_service_ip("fl_server")
        
        assert ip == "192.168.100.10"

    def test_get_service_ip_policy_engine(self, network_config_file, monkeypatch):
        """Test getting policy engine IP address."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        ip = addressing.get_service_ip("policy_engine")
        
        assert ip == "192.168.100.20"

    def test_get_service_port(self, network_config_file, monkeypatch):
        """Test getting service port."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        port = addressing.get_service_port("fl_server")
        
        assert port == 8080

    def test_get_service_url(self, network_config_file, monkeypatch):
        """Test getting full service URL."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        url = addressing.get_service_url("policy_engine")
        
        assert url == "http://192.168.100.20:5000"

    def test_get_service_url_https(self, network_config_file, monkeypatch):
        """Test getting service URL with HTTPS protocol."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        url = addressing.get_service_url("collector", protocol="https")
        
        assert url == "https://192.168.100.40:8000"

    def test_get_client_ip_first_client(self, network_config_file, monkeypatch):
        """Test getting first FL client IP address."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        ip = addressing.get_client_ip(1)
        
        assert ip == "192.168.100.101"

    def test_get_client_ip_second_client(self, network_config_file, monkeypatch):
        """Test getting second FL client IP address."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        ip = addressing.get_client_ip(2)
        
        assert ip == "192.168.100.102"

    def test_get_subnet(self, network_config_file, monkeypatch):
        """Test getting subnet CIDR."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        subnet = addressing.get_subnet()
        
        assert subnet == "192.168.100.0/24"

    def test_missing_config_file(self, monkeypatch, tmp_path):
        """Test behavior with missing config file."""
        monkeypatch.setenv("NETWORK_CONFIG", str(tmp_path / "nonexistent.json"))
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        with pytest.raises(FileNotFoundError):
            NetworkAddressing()

    def test_malformed_config_file(self, monkeypatch, tmp_path):
        """Test behavior with malformed JSON config."""
        config_path = tmp_path / "bad_config.json"
        config_path.write_text("{ invalid json }")
        monkeypatch.setenv("NETWORK_CONFIG", str(config_path))
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        with pytest.raises(json.JSONDecodeError):
            NetworkAddressing()

    def test_missing_service_key(self, network_config_file, monkeypatch):
        """Test behavior when requesting unknown service."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        from src.core.config.network_addressing import NetworkAddressing
        NetworkAddressing._instance = None
        
        addressing = NetworkAddressing()
        
        with pytest.raises(KeyError):
            addressing.get_service_ip("unknown_service")

    def test_global_instance(self, network_config_file, monkeypatch):
        """Test the module-level global instance."""
        monkeypatch.setenv("NETWORK_CONFIG", network_config_file)
        
        # Reset singleton before importing
        from src.core.config import network_addressing as na_module
        na_module.NetworkAddressing._instance = None
        
        # Re-import to get fresh instance
        from importlib import reload
        reload(na_module)
        
        # The module should export a ready-to-use instance
        assert na_module.network_addressing is not None
```

---

## Running Tests

### Basic Commands

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest -m unit

# Run specific test file
pytest tests/unit/core/config/test_network_addressing.py

# Run with verbose output
pytest -v

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### CI/CD Integration

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Priority Test Implementation Order

### Week 1 - Foundation (Must Have)
1. ✅ `test_network_addressing.py` - Config foundation
2. `test_config_manager.py` - Config loading
3. `test_logging_utils.py` - Logging setup

### Week 2 - Policy Layer (Critical)
4. `test_policy_client.py` - FL-Policy communication
5. `test_condition_evaluator.py` - Policy evaluation
6. `test_policies.py` - Policy management

### Week 3 - FL Core (Critical)
7. `test_fl_server.py` - Server core
8. `test_fl_client.py` - Client core
9. `test_model_handler.py` - Model management

### Week 4+ - Integration
10. API integration tests
11. System integration tests
12. E2E tests (Docker)
