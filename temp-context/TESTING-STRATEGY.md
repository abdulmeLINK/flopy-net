# FLOPY-NET Comprehensive Testing Strategy

## 📊 Current State Analysis

### Testing Infrastructure Status: ❌ Missing
- **No existing test files** found in the codebase
- **No pytest configuration** (no pytest.ini, pyproject.toml, or conftest.py)
- **No test directory structure** (no `tests/` folder)
- Only scenario-level tests exist (`topology_test.py`, `network_test.py`) which are integration scripts, not unit tests

### Key Components to Test (Priority Order)

| Component | File Location | Lines | Complexity | Priority |
|-----------|---------------|-------|------------|----------|
| NetworkAddressing | `src/core/config/network_addressing.py` | ~50 | Low | 🔴 P1 - Foundation |
| ConfigManager | `src/core/config/config_manager.py` | TBD | Medium | 🔴 P1 - Foundation |
| PolicyClient | `src/fl/common/policy_client.py` | 362 | Medium | 🔴 P1 - Core |
| PolicyEngine | `src/policy_engine/policy_engine_server.py` | 1040 | High | 🟡 P2 - Critical |
| FLServer | `src/fl/server/fl_server.py` | 1035 | High | 🟡 P2 - Critical |
| FLClient | `src/fl/client/fl_client.py` | 953 | High | 🟡 P2 - Critical |
| Collector API | `src/collector/api/server.py` | 1027 | High | 🟢 P3 - Important |
| FlowerClient | `src/fl/client/flower_client.py` | TBD | Medium | 🟢 P3 - Important |
| ModelHandler | `src/fl/common/model_handler.py` | TBD | Medium | 🟢 P3 - Important |

---

## 🎯 Testing Phases (Recommended Order)

### Phase 1: Foundation & Configuration (Week 1)
**Goal**: Test the configuration layer that everything depends on

#### 1.1 Network Addressing Tests
```
tests/unit/core/config/test_network_addressing.py
```
- Test singleton pattern
- Test IP address retrieval for all services
- Test service URL generation
- Test client IP generation (dynamic calculation)
- Test with missing/malformed config
- Test environment variable override

#### 1.2 Config Management Tests
```
tests/unit/core/config/test_config_manager.py
tests/unit/core/config/test_config_loader.py
```
- Test config loading from files
- Test default value handling
- Test config validation
- Test config merging (file + environment)

#### 1.3 Logging Utilities Tests
```
tests/unit/utils/test_logging_utils.py
```
- Test logger setup
- Test log formatting
- Test file handler creation

---

### Phase 2: Core Business Logic (Week 2-3)
**Goal**: Test critical business logic without external dependencies

#### 2.1 Policy System Tests
```
tests/unit/policy_engine/test_policies.py
tests/unit/policy_engine/test_policy_functions.py
tests/unit/policy_engine/evaluation/test_condition_evaluator.py
tests/unit/policy_engine/evaluation/test_policy_checker.py
```
- Test policy parsing and validation
- Test condition evaluation logic
- Test policy function execution (SECURITY: sandbox concerns!)
- Test application tracking
- Test policy conflict resolution

#### 2.2 Policy Client Tests
```
tests/unit/fl/common/test_policy_client.py
```
- Test policy checking logic
- Test retry mechanism
- Test caching behavior
- Test signature verification
- Test error handling

#### 2.3 Model Handler Tests
```
tests/unit/fl/common/test_model_handler.py
tests/unit/fl/client/models/test_minimal_model.py
```
- Test model loading/saving
- Test parameter serialization
- Test model validation
- Test configuration errors

---

### Phase 3: FL Core Components (Week 3-4)
**Goal**: Test FL training logic (mocked Flower)

#### 3.1 FL Server Tests
```
tests/unit/fl/server/test_fl_server.py
tests/unit/fl/server/test_fl_training_control.py
tests/unit/fl/server/test_fl_policy_enforcement.py
tests/unit/fl/server/strategies/test_metrics_tracking.py
```
- Test server initialization
- Test training round management
- Test policy enforcement hooks
- Test metrics aggregation strategies
- Test checkpoint save/restore

#### 3.2 FL Client Tests
```
tests/unit/fl/client/test_fl_client.py
tests/unit/fl/client/test_flower_client.py
tests/unit/fl/client/test_data_loader.py
tests/unit/fl/client/test_training_strategy.py
```
- Test client initialization
- Test server connection logic
- Test local training loop
- Test data loading for MNIST/CIFAR
- Test privacy mechanisms (if applicable)

---

### Phase 4: API Layer Tests (Week 4-5)
**Goal**: Test HTTP endpoints with mocked services

#### 4.1 Policy Engine API Tests
```
tests/integration/policy_engine/test_policy_api.py
tests/integration/policy_engine/test_function_api.py
tests/integration/policy_engine/test_metrics_api.py
```
- Test all REST endpoints
- Test request validation
- Test response formats
- Test authentication (if enabled)
- Test error responses

#### 4.2 Collector API Tests
```
tests/integration/collector/test_collector_api.py
tests/integration/collector/test_fl_routes.py
tests/integration/collector/test_network_routes.py
```
- Test metrics endpoints
- Test FL metrics aggregation
- Test network metrics
- Test filtering and pagination
- Test caching behavior

#### 4.3 FL Server Metrics API Tests
```
tests/integration/fl/test_fl_server_api.py
```
- Test metrics endpoint
- Test events endpoint
- Test status endpoint

---

### Phase 5: Integration Tests (Week 5-6)
**Goal**: Test component interactions

#### 5.1 FL System Integration
```
tests/integration/test_fl_system.py
```
- Test server-client communication (mocked gRPC)
- Test policy enforcement flow
- Test metrics collection pipeline
- Test round completion flow

#### 5.2 Policy Integration
```
tests/integration/test_policy_enforcement.py
```
- Test FL server ↔ Policy Engine integration
- Test FL client ↔ Policy Engine integration
- Test policy updates during training

#### 5.3 Collector Integration
```
tests/integration/test_collector_pipeline.py
```
- Test metrics ingestion from FL components
- Test event streaming
- Test storage persistence

---

### Phase 6: GNS3 & Network Tests (Week 6-7)
**Goal**: Test network simulation layer (requires GNS3 or mocks)

#### 6.1 GNS3 Client Tests
```
tests/unit/networking/gns3/test_gns3_client.py
tests/unit/networking/gns3/test_gns3_api.py
```
- Test GNS3 API wrapper
- Test project management
- Test node operations
- Test link management

#### 6.2 SDN Flow Manager Tests
```
tests/unit/networking/sdn/test_flow_manager.py
```
- Test flow rule creation
- Test network condition simulation
- Test latency/packet loss injection

---

### Phase 7: End-to-End Tests (Week 7-8)
**Goal**: Full system tests (Docker-based)

```
tests/e2e/test_full_scenario.py
tests/e2e/test_docker_deployment.py
```
- Test full training scenario
- Test network impairment scenarios
- Test dashboard data flow
- Test system recovery

---

## 📁 Recommended Test Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── pytest.ini                     # Pytest configuration
├── __init__.py
│
├── fixtures/                      # Test data and fixtures
│   ├── configs/
│   │   ├── test_network_addressing.json
│   │   ├── test_policy_config.json
│   │   └── test_server_config.json
│   ├── policies/
│   │   └── test_policies.json
│   └── models/
│       └── test_model_weights.pkl
│
├── mocks/                         # Mock objects
│   ├── __init__.py
│   ├── mock_gns3.py
│   ├── mock_flower.py
│   ├── mock_policy_engine.py
│   └── mock_network.py
│
├── unit/                          # Unit tests
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config/
│   │       ├── test_network_addressing.py
│   │       ├── test_config_manager.py
│   │       └── test_config_loader.py
│   │
│   ├── fl/
│   │   ├── __init__.py
│   │   ├── common/
│   │   │   ├── test_policy_client.py
│   │   │   └── test_model_handler.py
│   │   ├── server/
│   │   │   ├── test_fl_server.py
│   │   │   ├── test_training_control.py
│   │   │   └── strategies/
│   │   │       └── test_metrics_tracking.py
│   │   └── client/
│   │       ├── test_fl_client.py
│   │       ├── test_flower_client.py
│   │       └── test_data_loader.py
│   │
│   ├── policy_engine/
│   │   ├── __init__.py
│   │   ├── test_policies.py
│   │   ├── test_policy_functions.py
│   │   └── evaluation/
│   │       ├── test_condition_evaluator.py
│   │       └── test_policy_checker.py
│   │
│   ├── collector/
│   │   ├── __init__.py
│   │   ├── test_storage.py
│   │   └── test_fl_response_builder.py
│   │
│   ├── networking/
│   │   ├── __init__.py
│   │   ├── gns3/
│   │   │   └── test_gns3_client.py
│   │   └── sdn/
│   │       └── test_flow_manager.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── test_logging_utils.py
│       └── test_config_loader.py
│
├── integration/                   # Integration tests
│   ├── __init__.py
│   ├── conftest.py               # Integration fixtures
│   ├── policy_engine/
│   │   ├── test_policy_api.py
│   │   └── test_function_api.py
│   ├── collector/
│   │   └── test_collector_api.py
│   ├── fl/
│   │   └── test_fl_system.py
│   └── test_policy_enforcement.py
│
└── e2e/                          # End-to-end tests
    ├── __init__.py
    ├── conftest.py               # E2E fixtures (Docker setup)
    ├── test_full_scenario.py
    └── test_docker_deployment.py
```

---

## 🔧 Testing Tools & Dependencies

### Required Additions to `requirements.txt` or `requirements-dev.txt`:

```
# Testing Framework
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0
pytest-timeout>=2.2.0
pytest-xdist>=3.3.0          # Parallel test execution

# Mocking & Fixtures
responses>=0.23.0            # Mock HTTP requests
factory-boy>=3.3.0           # Test factories
faker>=19.0.0                # Fake data generation
freezegun>=1.2.0             # Time mocking

# API Testing
httpx>=0.24.0                # Async HTTP for FastAPI testing
flask-testing>=0.8.1         # Flask test utilities

# Code Quality
coverage>=7.3.0              # Code coverage
hypothesis>=6.82.0           # Property-based testing
mypy>=1.5.0                  # Type checking

# Integration Testing
testcontainers>=3.7.0        # Docker container testing
docker>=6.1.0                # Docker SDK
```

---

## ⚠️ Critical Testing Considerations

### 1. Security Concerns in Tests
- **`exec()` in policy functions**: Tests MUST NOT execute arbitrary code
- Mock the policy function executor to prevent code execution
- Use sandbox patterns for testing policy functions

### 2. Configuration Isolation
- Tests must NOT modify `config/` files
- Use `fixtures/configs/` for test configurations
- Environment variable isolation per test

### 3. Network Testing Challenges
- GNS3 tests require either:
  - Running GNS3 server (integration/e2e only)
  - Complete GNS3 API mocking (unit tests)
- Use `responses` library to mock HTTP calls to GNS3

### 4. Flower Framework Mocking
- Mock `flwr` client/server for unit tests
- Use actual Flower for integration tests
- gRPC mocking is complex - prefer high-level mocks

### 5. Docker Dependencies
- E2E tests require Docker
- Use `testcontainers` for spinning up services
- Consider CI/CD Docker-in-Docker requirements

---

## 📈 Testing Metrics Goals

| Metric | Target | Phase |
|--------|--------|-------|
| Unit Test Coverage | ≥80% | Phase 1-4 |
| Integration Coverage | ≥60% | Phase 5-6 |
| Critical Path Coverage | 100% | All Phases |
| Mutation Score | ≥70% | Phase 4+ |

---

## 🚀 Implementation Roadmap

### Week 1: Foundation
1. Create `tests/` directory structure
2. Add pytest configuration
3. Create `conftest.py` with shared fixtures
4. Implement `test_network_addressing.py` (Priority 1)
5. Implement `test_config_manager.py`

### Week 2: Policy Layer
1. Implement policy system unit tests
2. Create policy client tests
3. Add condition evaluator tests

### Week 3: FL Core
1. Implement FL server unit tests
2. Create FL client unit tests
3. Add training control tests

### Week 4: API Layer
1. Policy Engine API tests
2. Collector API tests
3. FL Server API tests

### Week 5: Integration
1. FL system integration tests
2. Policy enforcement integration
3. Collector pipeline tests

### Week 6-7: Network & E2E
1. GNS3 client tests
2. SDN flow manager tests
3. Full E2E scenario tests

---

## 📝 Next Steps

1. **Create pytest.ini** with configuration
2. **Create conftest.py** with initial fixtures
3. **Start with Phase 1**: `test_network_addressing.py`

See `testing-implementation-plan.md` for detailed implementation guide.
