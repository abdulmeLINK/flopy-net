---
sidebar_position: 1
---

# Development Setup

Set up your development environment for contributing to FLOPY-NET, including local development, testing, and debugging configurations.

## Prerequisites

Before setting up the development environment, ensure you have:

- **Python 3.8+** with pip and virtualenv
- **PowerShell** (Windows) or **Bash** (Linux/macOS) 
- **Docker** and **Docker Compose**
- **Git** for version control
- **VS Code** or similar IDE (recommended)
- **GNS3** (optional, for network simulation development)

## Repository Setup

### Clone the Repository

```powershell
# Clone the main repository
git clone https://github.com/abdulmelink/flopy-net.git
cd flopy-net

# For Windows, run the Git initialization script
.\init-git.ps1

# Or for Linux/macOS
chmod +x init-git.sh
./init-git.sh
```

### Development Branch Strategy

FLOPY-NET follows a simplified GitFlow approach:

- **main**: Production-ready code
- **dev**: Development branch for integration
- **feature/***: Individual feature development
- **fix/***: Bug fixes

```powershell
# Create your feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name
```

## Python Development Environment

### Virtual Environment Setup

```powershell
# Create virtual environment
python -m venv micro_fl_sdn

# Activate virtual environment (Windows)
.\micro_fl_sdn\Scripts\activate

# Verify Python version
python --version  # Should be 3.8+
```

### Install Dependencies

```powershell
# Install core dependencies
pip install -r requirements.txt

# Or use the Docker requirements for development
pip install -r docker/requirements/requirements-docker.txt

# Install FLOPY-NET in development mode
pip install -e .
```

## Project Structure

Understanding the codebase structure:

```
d:\dev\microfed\codebase\
├── src\                        # Core Python source code
│   ├── main.py                 # Main CLI entry point
│   ├── collector\              # Metrics collection service
│   ├── core\                   # Core utilities and common code
│   ├── fl\                     # Federated learning framework
│   ├── networking\             # Network simulation and SDN
│   ├── policy_engine\          # Policy management and enforcement
│   ├── scenarios\              # Experiment scenarios
│   └── utils\                  # Utility functions
├── config\                     # Configuration files
│   ├── policies\               # Policy definitions
│   ├── gns3\                   # GNS3 templates and settings
│   └── scenarios\              # Scenario configurations
├── docker\                     # Docker build files
│   ├── *.Dockerfile           # Service Dockerfiles
│   ├── entrypoints\           # Container entry scripts
│   └── requirements\          # Python dependencies
├── scripts\                    # Utility and management scripts
├── dashboard\                  # Web dashboard (separate component)
└── docs\                      # Documentation (Docusaurus)
```

```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files (optional)
pre-commit run --all-files
```

#### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--config=.flake8]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
```

#### Code Formatting Configuration

```ini
# .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude = 
    .git,
    __pycache__,
    venv,
    .venv,
    dist,
    build,
    *.egg-info

# pyproject.toml (for black and isort)
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 88
```

## Dashboard Frontend Development

### Setup Node.js Environment

```bash
# Navigate to dashboard frontend
cd dashboard/frontend

# Install dependencies
npm install

# Install development dependencies
npm install --save-dev @types/react @types/react-dom typescript eslint prettier
```

### Development Server

```bash
# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Frontend Configuration

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx",
    "lint:fix": "eslint src --ext ts,tsx --fix",
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.45.0",
    "eslint-plugin-react": "^7.32.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "prettier": "^3.0.0"
  }
}
```

## Docker Development Environment

### Development Docker Compose

Create a development-specific Docker Compose configuration:

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Override services for development
  fl-server:
    build:
      context: .
      dockerfile: docker/flopynet_fl_server.Dockerfile
      target: development  # Multi-stage build target
    volumes:
      - ./src:/app/src:ro
      - ./configs:/app/configs:ro
      - dev_data:/app/data
    environment:
      - PYTHONPATH=/app
      - FLASK_ENV=development
      - LOG_LEVEL=DEBUG
    ports:
      - "8080:8080"
      - "5678:5678"  # Debug port
    
  policy-engine:
    build:
      context: .
      dockerfile: docker/flopynet_policy_engine.Dockerfile
      target: development
    volumes:
      - ./policy_engine:/app/policy_engine:ro
      - ./configs:/app/configs:ro
    environment:
      - PYTHONPATH=/app
      - FASTAPI_ENV=development
      - LOG_LEVEL=DEBUG
    ports:
      - "5000:5000"
      - "5679:5678"  # Debug port
    
  dashboard-backend:
    build:
      context: ./dashboard/backend
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./dashboard/backend/app:/app/app:ro
    environment:
      - PYTHONPATH=/app
      - LOG_LEVEL=DEBUG
    ports:
      - "8001:8001"
      - "5680:5678"  # Debug port
    
  dashboard-frontend:
    build:
      context: ./dashboard/frontend
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./dashboard/frontend/src:/app/src:ro
      - ./dashboard/frontend/public:/app/public:ro
    ports:
      - "3000:3000"  # Development server
    environment:
      - NODE_ENV=development
      - VITE_BACKEND_URL=http://localhost:8001

volumes:
  dev_data:
```

### Multi-stage Dockerfile for Development

```dockerfile
# docker/flopynet_fl_server.Dockerfile
FROM python:3.9-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt requirements-dev.txt ./

# Production stage
FROM base as production
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "src.main", "run", "--component", "fl-server"]

# Development stage
FROM base as development
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
RUN pip install debugpy  # Python debugger

# Install development tools
RUN pip install black flake8 mypy pytest

# Enable debugging
ENV PYTHONPATH=/app
EXPOSE 5678

CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m", "src.main", "run", "--component", "fl-server"]
```

## Testing Setup

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_fl_server.py
│   ├── test_policy_engine.py
│   └── test_client.py
├── integration/            # Integration tests
│   ├── test_api_integration.py
│   └── test_component_integration.py
├── e2e/                    # End-to-end tests
│   ├── test_complete_experiment.py
│   └── test_dashboard_workflow.py
├── fixtures/               # Test data and fixtures
│   ├── sample_configs/
│   └── mock_data/
└── conftest.py            # Pytest configuration
```

### Pytest Configuration

```python
# conftest.py
import pytest
import asyncio
import tempfile
import os
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test configurations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_policy_engine():
    """Mock policy engine for testing."""
    mock = MagicMock()
    mock.evaluate_request.return_value = {
        "decision": "allow",
        "confidence": 1.0,
        "policies_applied": []
    }
    return mock

@pytest.fixture
def sample_fl_config():
    """Sample FL configuration for testing."""
    return {
        "server_id": "test-server",
        "port": 8080,
        "algorithm": "fedavg",
        "rounds": 5,
        "min_clients": 2
    }
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run tests with specific markers
pytest -m "not slow"  # Skip slow tests
pytest -m "integration"  # Run only integration tests

# Run tests in parallel
pytest -n auto  # Requires pytest-xdist
```

### Test Configuration

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
    -v
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests that take more than 5 seconds
    network: Tests that require network access
```

## Debugging Setup

### VS Code Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [        {
            "name": "FL Server Debug",
            "type": "python",
            "request": "launch",
            "program": "`${workspaceFolder}/src/main.py",
            "args": ["run", "--component", "fl-server", "--debug"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "`${workspaceFolder}",
                "LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Policy Engine Debug",
            "type": "python", 
            "request": "launch",
            "program": "`${workspaceFolder}/policy_engine/main.py",
            "args": ["--debug"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "`${workspaceFolder}",
                "LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Attach to Docker Container",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },            "pathMappings": [
                {
                    "localRoot": "`${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "`${workspaceFolder}"
            }
        }
    ]
}
```

### Remote Debugging with Docker

```python
# For remote debugging in Docker containers
import debugpy

# Enable debugging
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger to attach...")
debugpy.wait_for_client()
print("Debugger attached!")
```

## Development Workflow

### Daily Development Process

1. **Start Development Environment**
   ```bash
   # Start development services
   docker-compose -f docker-compose.dev.yml up -d
   
   # Activate Python virtual environment
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

2. **Make Changes and Test**
   ```bash
   # Run relevant tests
   pytest tests/unit/test_your_component.py -v
   
   # Check code quality
   black src/
   flake8 src/
   mypy src/
   ```

3. **Integration Testing**
   ```bash
   # Test with other components
   pytest tests/integration/ -v
   
   # Manual testing with development environment
   python -m src.scenarios.run_scenario --scenario basic_test
   ```

4. **Commit Changes**
   ```bash
   # Pre-commit hooks will run automatically
   git add .
   git commit -m "feat: add new feature X"
   
   # Push to feature branch
   git push origin feature/your-feature-name
   ```

### Code Review Process

Before submitting a pull request:

1. **Self Review**
   - Run all tests: `pytest`
   - Check code coverage: `pytest --cov=src`
   - Verify documentation: Update relevant docs
   - Test in development environment

2. **Submit Pull Request**
   - Target the `develop` branch
   - Provide clear description
   - Include test results
   - Link related issues

3. **Address Review Comments**
   - Make requested changes
   - Re-run tests
   - Update documentation if needed

## Environment Configuration

### Development Environment Variables

```bash
# .env.development
# Core settings
PYTHONPATH=/path/to/flopy-net
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Service URLs (development)
FL_SERVER_URL=http://localhost:8080
POLICY_ENGINE_URL=http://localhost:5000
COLLECTOR_URL=http://localhost:8083
DASHBOARD_BACKEND_URL=http://localhost:8001

# Database settings (development)
DATABASE_URL=sqlite:///dev_flopynet.db
REDIS_URL=redis://localhost:6379/0

# GNS3 settings (optional)
GNS3_SERVER_URL=http://localhost:3080
GNS3_USERNAME=admin
GNS3_PASSWORD=admin

# Development flags
ENABLE_DEBUG_ENDPOINTS=true
ENABLE_MOCK_DATA=true
DISABLE_AUTH=true  # For development only
```

### IDE Settings

#### VS Code Settings

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    },
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

## Troubleshooting Development Issues

### Common Problems

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH is set correctly
   export PYTHONPATH=/path/to/flopy-net
   
   # Install in development mode
   pip install -e .
   ```

2. **Docker Build Issues**
   ```bash
   # Clean Docker cache
   docker system prune -a
   
   # Rebuild without cache
   docker-compose build --no-cache
   ```

3. **Port Conflicts**
   ```bash
   # Find processes using ports
   netstat -an | findstr :8080  # Windows
   lsof -i :8080  # macOS/Linux
   
   # Kill processes if needed
   taskkill /PID <PID> /F  # Windows
   kill -9 <PID>  # macOS/Linux
   ```

4. **Test Failures**
   ```bash
   # Run tests in verbose mode to see details
   pytest -v -s
   
   # Run specific failing test
   pytest tests/unit/test_specific.py::test_function -v
   
   # Check test dependencies
   pip list | grep pytest
   ```

### Development Tools

#### Useful Scripts

```bash
# scripts/dev-setup.sh
#!/bin/bash
# Development environment setup script

set -e

echo "Setting up FLOPY-NET development environment..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# Setup pre-commit hooks
pre-commit install

# Create development database
python scripts/create_dev_db.py

echo "Development environment setup complete!"
echo "Activate the virtual environment with: source venv/bin/activate"
```

#### Database Management

```python
# scripts/create_dev_db.py
#!/usr/bin/env python3
"""Create development database with sample data."""

import sqlite3
import json
import os

def create_dev_database():
    """Create development database with sample data."""
    db_path = "dev_flopynet.db"
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (simplified schema)
    cursor.execute("""
        CREATE TABLE experiments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            config TEXT NOT NULL,
            status TEXT DEFAULT 'created',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE metrics (
            id INTEGER PRIMARY KEY,
            experiment_id INTEGER,
            round_number INTEGER,
            client_id TEXT,
            metric_type TEXT,
            value REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id)
        )
    """)
    
    # Insert sample data
    sample_experiment = {
        "algorithm": "fedavg",
        "rounds": 10,
        "clients": 3
    }
    
    cursor.execute(
        "INSERT INTO experiments (name, config) VALUES (?, ?)",
        ("Development Test", json.dumps(sample_experiment))
    )
    
    conn.commit()
    conn.close()
    
    print(f"Development database created: {db_path}")

if __name__ == "__main__":
    create_dev_database()
```

This development setup guide provides comprehensive instructions for:

1. **Environment Setup**: Python, Node.js, Docker environments
2. **Code Quality**: Linting, formatting, pre-commit hooks
3. **Testing**: Unit, integration, and end-to-end testing
4. **Debugging**: Local and remote debugging configurations
5. **Development Workflow**: Daily development and code review processes
6. **Troubleshooting**: Common issues and solutions

Following this guide ensures a consistent development experience across all contributors to FLOPY-NET.
