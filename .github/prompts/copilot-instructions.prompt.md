# FLOPY-NET AI Coding Instructions

You are working on **FLOPY-NET**, a Federated Learning research platform with GNS3 Network Emulation.

## 🎯 Project Context
- **Target Users**: FL researchers (not end users)
- **Current Version**: `v1.0.0-alpha.9-dev` (branch: `v1.0.0-alpha.9-dev`)
- **Purpose**: Test Federated Learning under realistic network conditions (latency, packet loss)
- **Alpha Notice**: Expect incomplete features. Verify behavior by reading source code, not docs.

## 🏗️ Architecture
**Microservices** (Docker + GNS3):
- `policy-engine` → Central control, security/resource policies (Flask)
- `fl-server` → FL coordinator (Flower + Flask metrics)
- `fl-client` → Local training (Flower + PyTorch)
- `collector` → Metrics aggregation (FastAPI)
- `dashboard` → React/Vite monitoring frontend

**Network**: Subnet `192.168.100.0/24` with static IPs defined in `config/network_addressing.json`.

## 📂 Key Paths
| Path | Purpose |
|------|---------|
| `src/` | Python source (main.py entry point) |
| `config/` | JSON configs — **single source of truth** |
| `config/network_addressing.json` | **Centralized IP registry** |
| `config/version.json` | Version info for all components |
| `docker/` | Dockerfiles + entrypoints |
| `dashboard/frontend/` | React frontend |
| `scripts/` | GNS3 utilities |

## 🚨 Active Refactoring Priorities (v1.0.0-alpha.9)

### Priority 1: Configuration Centralization
**Issues**: #22, #23, #24, #16
- `config/network_addressing.json` exists — use it via `src/core/config/network_addressing.py`
- `config/gns3_connection.json` exists — centralize GNS3 config loading
- **Goal**: Eliminate 60+ hardcoded IPs across codebase
- **Status**: #22 assigned to contributor, #23/#24 pending

### Priority 2: Split Fat Files (Before Testing Infrastructure)
**Files over 1000 lines needing refactor:**
| File | Lines | Action |
|------|-------|--------|
| `src/policy_engine/policy_engine_server.py` | 2844 | Split into routes, services, handlers |
| `src/fl/server/fl_server.py` | 2788 | Extract strategies, metrics, API |
| `src/collector/api/server.py` | 2756 | Split endpoints, services |
| `src/networking/sdn/flow_manager.py` | 1966 | Modularize |
| `src/fl/client/fl_client.py` | 1737 | Extract training, metrics |

### Priority 3: Docker/Entrypoints (After Config Centralization)
- `docker/entrypoints/*.sh` depend heavily on current component structure
- Fix configs and fat files first, then refactor Docker layer

## 📏 Coding Standards

### Configuration
```python
# ✅ CORRECT: Use centralized config
from src.core.config.network_addressing import network_addressing
policy_url = network_addressing.get_service_url('policy_engine')

# ❌ WRONG: Hardcoded IPs
policy_url = "http://192.168.100.20:5000"
```

### Logging
```python
# ✅ Use src/utils/logging_utils.py
from src.utils.logging_utils import setup_logging
logger = setup_logging(app_name="my-component")

# ❌ Don't create custom logging in main.py
```

### Imports
```python
# ❌ AVOID: sys.path manipulation (19 occurrences exist - legacy)
sys.path.insert(0, os.path.abspath(...))

# ✅ FUTURE: Use proper package with pyproject.toml
```

## ⚠️ Known Technical Debt
1. **`exec()` in policy functions** — Security concern, needs sandboxing
2. **Credentials in config** — `config/gns3_connection.json` has default passwords
3. **Dual logging setups** — `main.py` vs `logging_utils.py`
4. **No pyproject.toml** — Causes `sys.path` hacks everywhere
5. **Version sprawl** — `v1.0.0-alpha.8` hardcoded in 50+ places


## 🔗 Key GitHub Issues
- **#22-24**: IP centralization trilogy (in progress)
- **#16**: GNS3 config centralization
- **#7**: FL Server training resumption bug (critical)
- **#17**: CI/CD for Docker builds

Use "temp-context" directory to save and plan your progress.