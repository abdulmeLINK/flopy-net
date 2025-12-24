# FLOPY-NET Testing Quick Reference

## 📋 Summary

| Document | Purpose |
|----------|---------|
| [testing-strategy.md](./testing-strategy.md) | Full testing plan with phases |
| [testing-implementation-plan.md](./testing-implementation-plan.md) | Code examples and setup |
| [critical-tests-analysis.md](./critical-tests-analysis.md) | Priority matrix |

---

## 🚀 Quick Start Commands

```powershell
# 1. Install test dependencies
pip install pytest pytest-cov pytest-mock responses

# 2. Create test directory structure
mkdir tests
mkdir tests\unit
mkdir tests\unit\core
mkdir tests\unit\core\config
mkdir tests\unit\fl
mkdir tests\unit\fl\common
mkdir tests\unit\fl\server
mkdir tests\unit\fl\client
mkdir tests\unit\policy_engine
mkdir tests\integration
mkdir tests\e2e
mkdir tests\fixtures
mkdir tests\mocks

# 3. Run tests (once created)
pytest -v

# 4. Run with coverage
pytest --cov=src --cov-report=html
```

---

## ✅ Testing Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create `pytest.ini`
- [ ] Create `tests/conftest.py`
- [ ] Implement `test_network_addressing.py`
- [ ] Implement `test_config_manager.py`

### Phase 2: Policy Layer (Week 2)
- [ ] Implement `test_policy_client.py`
- [ ] Implement `test_condition_evaluator.py`
- [ ] Implement `test_policies.py`

### Phase 3: FL Core (Week 3)
- [ ] Implement `test_fl_server.py`
- [ ] Implement `test_fl_client.py`
- [ ] Implement `test_flower_client.py`

### Phase 4: APIs (Week 4)
- [ ] Implement `test_policy_engine_api.py`
- [ ] Implement `test_collector_api.py`

---

## 🎯 Top 5 Most Important Tests

1. **`test_network_addressing.py`** - Config foundation
2. **`test_policy_client.py`** - Security boundary
3. **`test_fl_server.py`** - Training orchestration
4. **`test_fl_client.py`** - Local training
5. **`test_condition_evaluator.py`** - Policy logic

---

## ⚠️ Testing Gotchas

1. **Singleton Reset**: `NetworkAddressing` is a singleton - reset between tests
2. **sys.path hacks**: Many files use `sys.path.insert` - may need imports after fixture setup
3. **exec() security**: Mock policy function execution, never run real code
4. **GNS3 dependency**: Mock all GNS3 API calls in unit tests
5. **Flower mocking**: Mock `flwr` at high level, don't test gRPC directly

---

## 📊 Current Status

| Metric | Current | Target |
|--------|---------|--------|
| Test Files | 0 | 20+ |
| Unit Tests | 0 | 100+ |
| Coverage | 0% | 80% |
| CI/CD | ❌ | ✅ |
