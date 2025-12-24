# FLOPY-NET Most Important Tests Analysis

## 🔴 Critical Tests (Must Have First)

These tests protect the **core functionality** that, if broken, would make the system unusable.

---

### 1. Configuration Tests (Foundation - Week 1)

**Why Critical**: Every component depends on configuration. If config loading breaks, nothing works.

| Test | Risk if Missing | Effort |
|------|-----------------|--------|
| `test_network_addressing.py` | Services can't find each other | Low |
| `test_config_loader.py` | Components fail to start | Low |

**Impact**: 100% of components depend on this.

---

### 2. Policy Client Tests (FL Core - Week 1-2)

**Why Critical**: Policy enforcement is the security boundary between components.

| Test | Risk if Missing | Effort |
|------|-----------------|--------|
| `test_policy_client.py` | Training without authorization | Medium |
| `test_policy_checker.py` | Policy bypass vulnerabilities | Medium |

**Impact**: FL Server & FL Client both use PolicyClient for authorization.

**Security Note**: The policy system uses `exec()` for custom functions - tests must mock this!

---

### 3. FL Server Core Tests (Week 2-3)

**Why Critical**: The FL Server orchestrates all training. Breaking it stops all experiments.

| Test | Risk if Missing | Effort |
|------|-----------------|--------|
| `test_fl_server.py` (init, config) | Server won't start | Medium |
| `test_fl_training_control.py` | Training loops fail | High |
| `test_metrics_tracking.py` | No experiment data recorded | Medium |

**Known Bug (Issue #7)**: Training resumption is broken - tests should cover this.

---

### 4. FL Client Core Tests (Week 2-3)

**Why Critical**: Without working clients, no local training happens.

| Test | Risk if Missing | Effort |
|------|-----------------|--------|
| `test_fl_client.py` (init, connect) | Clients can't join | Medium |
| `test_flower_client.py` | Training round failures | Medium |
| `test_data_loader.py` | No data for training | Medium |

---

### 5. API Endpoint Tests (Week 3-4)

**Why Critical**: Dashboard and external integrations depend on APIs.

| Test | Risk if Missing | Effort |
|------|-----------------|--------|
| Policy Engine `/check` endpoint | Authorization fails | Medium |
| Policy Engine `/events` endpoint | Monitoring breaks | Low |
| Collector `/metrics/fl` endpoint | Dashboard shows no data | Medium |
| FL Server `/metrics` endpoint | Can't monitor training | Low |

---

## 🟡 Important Tests (Should Have)

| Test | Purpose | Effort |
|------|---------|--------|
| `test_storage.py` (FL Server) | Checkpoint/resume | Medium |
| `test_model_handler.py` | Model serialization | Medium |
| `test_gns3_client.py` | Network emulation | High |
| `test_event_buffer.py` | Event streaming | Low |

---

## 🟢 Nice-to-Have Tests (Later)

| Test | Purpose | Effort |
|------|---------|--------|
| Dashboard API tests | UI data validation | Medium |
| SDN flow manager tests | Network control | High |
| E2E Docker tests | Full system validation | Very High |

---

## 📊 Test Priority Matrix

```
                    HIGH IMPACT
                         │
         Policy Client   │   FL Server
         ████████████   │   ████████████
                         │
LOW ─────────────────────┼───────────────────── HIGH
EFFORT                   │                     EFFORT
                         │
         Config Tests    │   GNS3 Tests
         ████████        │   ████
                         │
                    LOW IMPACT
```

**Recommendation**: Start with HIGH IMPACT, LOW EFFORT (upper left quadrant).

---

## 📌 Test Execution Priority

### Sprint 1 (First 2 Weeks)
```
1. test_network_addressing.py     [2h]  ✓ Config foundation
2. test_config_manager.py         [2h]  ✓ Config loading
3. test_policy_client.py          [4h]  ✓ Security boundary
4. test_condition_evaluator.py    [3h]  ✓ Policy logic
```

### Sprint 2 (Weeks 3-4)
```
5. test_fl_server.py              [6h]  ✓ Server core
6. test_fl_training_control.py    [4h]  ✓ Training orchestration
7. test_fl_client.py              [4h]  ✓ Client core
8. test_flower_client.py          [3h]  ✓ Flower integration
```

### Sprint 3 (Weeks 5-6)
```
9. test_policy_engine_api.py      [4h]  ✓ Policy REST API
10. test_collector_api.py         [4h]  ✓ Metrics REST API
11. test_fl_server_api.py         [2h]  ✓ FL metrics endpoint
12. test_data_loader.py           [2h]  ✓ Dataset loading
```

---

## 🚨 Risk-Based Prioritization

### If you only have time for 5 tests:

1. **`test_network_addressing.py`** - Everything breaks without it
2. **`test_policy_client.py`** - Security boundary
3. **`test_fl_server.py`** (init only) - Core component
4. **`test_fl_client.py`** (init only) - Core component
5. **`test_condition_evaluator.py`** - Policy logic

### If you have time for 10 tests:

Add:
6. **`test_fl_training_control.py`** - Training loop
7. **`test_flower_client.py`** - FL communication
8. **`test_policy_engine_api.py`** - API layer
9. **`test_metrics_tracking.py`** - Experiment data
10. **`test_data_loader.py`** - Training data

---

## 🔍 Coverage Goals by Component

| Component | Target | Critical Paths |
|-----------|--------|----------------|
| `src/core/config/` | 90% | Singleton, loading, validation |
| `src/fl/common/` | 85% | PolicyClient, ModelHandler |
| `src/fl/server/` | 75% | Init, training loop, metrics |
| `src/fl/client/` | 75% | Init, connect, train |
| `src/policy_engine/` | 70% | Evaluation, API, events |
| `src/collector/` | 60% | API, storage |
| `src/networking/` | 50% | GNS3 client (mocked) |
