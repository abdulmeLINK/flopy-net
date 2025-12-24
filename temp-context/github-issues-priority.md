# FLOPY-NET GitHub Issues - Testing Priority Analysis

## 🔴 Critical Issues (Must Cover in Tests First)

### 1. **Issue #7** - FL Server training loop fails to continue after TRAINING_RESUMED event
- **Labels**: `bug`, `critical`, `fl-server`, `policy-engine`
- **Impact**: Core functionality broken - training resumption doesn't work
- **Test Coverage Needed**:
  - `test_fl_training_control.py` - Training restart logic
  - `test_fl_server.py` - State management after stop/resume
  - Integration test for stop → policy change → resume flow

**Root Cause from Issue**:
- State not properly reset between stop and resume
- `global_metrics["training_active"]` flags not cleared
- Flower server lifecycle issues

**Tests to Write**:
```
tests/unit/fl/server/test_fl_training_control.py
  - test_restart_training_resets_state
  - test_resume_after_policy_stop
  - test_training_state_flags_cleared
  - test_flower_server_cleanup_before_restart

tests/integration/test_training_resumption.py
  - test_stop_resume_flow
  - test_metrics_after_resume
  - test_round_continuation
```

---

### 2. **Issue #22, #23, #24** - IP Centralization Trilogy
- **Labels**: `enhancement`, `good first issue`
- **Status**: #22 assigned, in progress
- **Impact**: 60+ hardcoded IPs across codebase

**Test Coverage Needed** (already in our plan!):
- `test_network_addressing.py` - Core NetworkAddressing class
- Tests for config file migration
- Tests for Docker ENV generation

**Note**: `config/network_addressing.json` and `src/core/config/network_addressing.py` already exist!

---

### 3. **Issue #4** - Default policies block training during demos
- **Labels**: `bug`, `scenario`, `ux`, `demo`
- **Impact**: Training fails at certain times of day

**Test Coverage Needed**:
```
tests/unit/policy_engine/test_policies.py
  - test_time_based_policy_evaluation
  - test_policy_override_mechanism
  - test_missing_policy_handling

tests/integration/test_demo_scenario.py
  - test_training_without_time_restrictions
```

---

## 🟡 Important Issues (Should Cover)

### 4. **Issue #5** - System Events filtering doesn't work
- **Labels**: `bug`, `dashboard`, `frontend`, `ux`
- **Impact**: Cannot filter events by level/time

**Test Coverage Needed**:
```
tests/unit/policy_engine/utils/test_event_buffer.py
  - test_event_filtering_by_level
  - test_event_filtering_by_time_range
  - test_since_event_id_filtering
```

---

### 5. **Issue #13, #14** - Dashboard calculation bugs
- **Labels**: `bug`, `dashboard`, `frontend`
- **Impact**: Wrong metrics displayed

**Test Coverage Needed**:
```
tests/unit/collector/test_fl_response_builder.py
  - test_allow_rate_calculation
  - test_policy_trend_formatting
```

---

### 6. **Issue #8** - FL Clients need event reporting
- **Labels**: `enhancement`, `fl-client`, `collector`
- **Impact**: Missing debugging capability

**Test Coverage Needed**:
```
tests/unit/fl/client/test_fl_client.py
  - test_event_reporting_to_collector
  - test_client_metrics_emission
```

---

### 7. **Issue #9** - Network monitoring events
- **Labels**: `enhancement`, `network`, `monitoring`, `sdn`
- **Impact**: No alerts for network anomalies

**Test Coverage Needed**:
```
tests/unit/collector/test_network_monitor.py
  - test_abnormal_latency_event
  - test_bandwidth_threshold_detection
```

---

## 🟢 Lower Priority Issues (Later)

| Issue | Title | Priority |
|-------|-------|----------|
| #11, #19, #30, #31, #33 | Documentation updates | Low (no tests needed) |
| #15, #17 | Docker CI/CD | Medium (infra) |
| #25, #26, #27, #28 | Feature requests | Low (future) |
| #29 | Live event tracking fix | Medium |
| #12 | Landing page button | Low (UI only) |

---

## 📊 Issue-to-Test Mapping

| Issue | Test File(s) | Priority | Sprint |
|-------|--------------|----------|--------|
| #7 | `test_fl_training_control.py`, `test_training_resumption.py` | 🔴 Critical | 1 |
| #22-24 | `test_network_addressing.py` | 🔴 Critical | 1 |
| #4 | `test_policies.py`, `test_demo_scenario.py` | 🔴 Critical | 1 |
| #5 | `test_event_buffer.py` | 🟡 Important | 2 |
| #13-14 | `test_fl_response_builder.py` | 🟡 Important | 2 |
| #8 | `test_fl_client.py` | 🟡 Important | 2 |
| #9 | `test_network_monitor.py` | 🟡 Important | 3 |

---

## 🎯 Recommended Test Implementation Order (Updated)

### Sprint 1: Foundation + Critical Bugs
1. `test_network_addressing.py` (#22-24) - Config foundation ✅
2. `test_fl_training_control.py` (#7) - Critical bug
3. `test_policies.py` (#4) - Policy time restrictions
4. `test_policy_client.py` - Security boundary

### Sprint 2: Core FL + Dashboard Fixes
5. `test_fl_server.py` - Server core
6. `test_fl_client.py` (#8) - Client + event reporting
7. `test_event_buffer.py` (#5) - Event filtering
8. `test_fl_response_builder.py` (#13-14) - Dashboard calculations

### Sprint 3: Network + Integration
9. `test_network_monitor.py` (#9) - Network events
10. Integration tests for training resumption (#7)
11. Integration tests for policy enforcement

---

## 📝 Notes

### Issues Already Addressed by Existing Code:
- **#22**: `config/network_addressing.json` exists
- **#22**: `src/core/config/network_addressing.py` exists
- **#22**: Just needs tests and validation!

### Issues That Will Be Caught by Tests:
- **#7**: Will be caught by training control tests
- **#4**: Will be caught by policy evaluation tests
- **#5**: Will be caught by event buffer tests

### Issues That Need Feature Implementation First:
- **#8**: FL Client event reporting (feature)
- **#9**: Network monitoring events (feature)
- **#25-28**: New features (future)
