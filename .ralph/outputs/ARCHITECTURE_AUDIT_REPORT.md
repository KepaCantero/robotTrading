# Architecture Audit Report - app/ vs ARCHITECTURE_REQUIREMENTS.md

**Date:** 2026-03-15
**Auditor:** Claude Code
**Reference:** `.requirements/ARCHITECTURE_REQUIREMENTS.md`

---

## Summary

| Category | Violations | Severity |
|----------|------------|----------|
| ARCH-DEP-001 (Domain purity) | 40+ | P0 - CRITICAL |
| ARCH-ANTI-006 (Framework in domain) | 1 (SQLAlchemy) | P0 - CRITICAL |
| ARCH-FILE-001 (Files > 300 lines) | 30+ | P1 - HIGH |
| Directory Structure | 9 non-standard dirs | P2 - MEDIUM |

---

## 1. CRITICAL: Domain Layer Purity Violations (ARCH-DEP-001)

**Rule:** Domain has NO dependencies on other layers (services, infrastructure, api)

### 1.1 Domain importing from app.services

| File | Line | Import |
|------|------|--------|
| `domain/strategies/carver_robust_rules.py` | 25 | `from app.application.scheduling.market_scheduler` |
| `domain/strategies/automated_backtest.py` | 18 | `from app.services.portfolio_config_manager` |
| `domain/strategies/momentum.py` | 22 | `from app.services.signal_scoring_engine` |
| `domain/strategies/optimization/hyperparameter_optimizer.py` | 304 | `from app.infrastructure.data.feeds` |
| `domain/optimization/multi_strategy_optimizer_v2.py` | 24-25 | `from app.services.multi_strategy_allocation`, `portfolio_config_manager` |
| `domain/optimization/multi_strategy_optimizer.py` | 21 | `from app.services.multi_strategy_allocation` |
| `domain/repositories/unit_of_work.py` | 432-433 | `from app.infrastructure.persistence.sql_*` |
| `domain/services/signals/scoring.py` | 7 | `from app.services.signal_scoring_engine` |
| `domain/services/compliance/compliance_engine.py` | Multiple | 20+ imports from app.services and app.infrastructure |
| `domain/services/compliance/service_registry.py` | Multiple | 10+ imports from app.services |
| `domain/services/execution/trading_bridge_adapter.py` | 17,21-22 | `from app.services.*` |
| `domain/services/execution/execution_adapter.py` | 18 | `from app.services.live_trading.*` |
| `domain/services/execution/order_manager_adapter.py` | 25-26 | `from app.services.live_trading.*` |

**Total: 40+ violations**

---

## 2. CRITICAL: Framework in Domain (ARCH-ANTI-006)

**Rule:** Domain has NO framework imports (FastAPI, SQLAlchemy, httpx)

### 2.1 SQLAlchemy in Domain

| File | Violation |
|------|-----------|
| `domain/tax/database/fifo_schema.py:36-38` | `from sqlalchemy.*` |

**This is a CRITICAL violation** - database schemas should be in `infrastructure/database/`, NOT in `domain/`.

### 2.2 NumPy/Pandas in Domain (Debatable)

**Note:** NumPy and Pandas are used extensively in domain for calculations.
- This may be acceptable for a quantitative trading application
- However, the architecture spec says "ONLY standard library + dataclasses + typing"
- 100+ files use numpy/pandas in domain

**Recommendation:** Update architecture spec to allow numpy/pandas as "domain-safe" libraries for quantitative applications.

---

## 3. HIGH: File Size Violations (ARCH-FILE-001)

**Rule:** Files < 300 lines

| File | Lines |
|------|-------|
| `domain/services/compliance/compliance_engine.py` | 3500+ |
| `services/optimization_chan.py` | 2612 |
| `services/risk_models_narang.py` | 2117 |
| `services/execution_narang.py` | 2089 |
| `services/portfolio_construction_narang.py` | 2066 |
| `services/transaction_costs.py` | 1998 |
| `services/regime_detection_chan.py` | 1952 |
| `services/alerting_system.py` | 1828 |
| `services/portfolio_optimizer.py` | 1799 |
| `services/live_trading/broker_connector.py` | 1721 |
| `services/live_trading/alert_to_trade_mapper.py` | 1702 |
| `services/execution_algorithms.py` | 1682 |
| `domain/portfolio/multi_asset/models.py` | 1625 |
| `domain/strategies/learning/deep_learning_engine.py` | 1539 |
| `domain/strategies/learning/transformer_engine.py` | 1530 |
| `services/multi_strategy_allocation.py` | 1530 |
| `backtesting/robust_engine/engine.py` | 1302 |

**Total: 30+ files exceed 300 lines**

---

## 4. MEDIUM: Non-Standard Directory Structure

**Expected:**
```
app/
├── core/
├── domain/
├── services/
├── infrastructure/
└── api/
```

**Actual:**
```
app/
├── api/              ✅
├── application/      ❌ (should be part of services/)
├── backtesting/      ❌ (not in spec)
├── core/             ✅
├── domain/           ✅
├── engines/          ❌ (not in spec)
├── infrastructure/   ✅
├── models/           ❌ (should be in domain/)
├── presentation/     ❌ (should be api/)
├── security/         ❌ (not in spec)
├── services/         ✅
├── shared/           ❌ (should be core/)
├── simulation/       ❌ (not in spec)
└── sre/              ❌ (not in spec)
```

### Recommendations:
1. **application/** → Merge into `services/`
2. **backtesting/** → Keep as special domain (quantitative)
3. **engines/** → Move to `services/` or `infrastructure/`
4. **models/** → Move to `domain/models/`
5. **presentation/** → Merge into `api/`
6. **security/** → Move to `infrastructure/security/`
7. **shared/** → Move to `core/`
8. **simulation/** → Move to `backtesting/` or `services/`
9. **sre/** → Move to `infrastructure/monitoring/`

---

## 5. Specific File Violations

### 5.1 God Class: compliance_engine.py (3500+ lines)

**File:** `app/domain/services/compliance/compliance_engine.py`
**Lines:** 3500+
**Violations:**
- ARCH-FILE-001: File > 300 lines
- ARCH-FILE-003: Class > 300 lines
- ARCH-DEP-001: Imports from services/infrastructure

**Recommendation:** Split into:
- `ComplianceChecker` (domain)
- `ComplianceService` (services)
- `ComplianceRepository` (infrastructure)

### 5.2 Misplaced Database Schema

**File:** `app/domain/tax/database/fifo_schema.py`
**Issue:** SQLAlchemy models in domain layer
**Fix:** Move to `app/infrastructure/database/schemas/fifo_schema.py`

---

## 6. Action Items

### P0 - Immediate (Week 1)
1. [ ] Move `domain/tax/database/fifo_schema.py` to `infrastructure/database/`
2. [ ] Remove services/infrastructure imports from domain entities
3. [ ] Create Protocol interfaces for domain dependencies

### P1 - Short Term (Week 2-4)
1. [ ] Split `compliance_engine.py` into smaller modules
2. [ ] Reduce file sizes to < 300 lines
3. [ ] Consolidate directory structure

### P2 - Medium Term (Month 2)
1. [ ] Merge `application/` into `services/`
2. [ ] Merge `presentation/` into `api/`
3. [ ] Move `shared/` to `core/`
4. [ ] Update architecture spec to allow numpy/pandas in domain

---

## 7. Compliance Score

| Rule | Status | Score |
|------|--------|-------|
| ARCH-DEP-001 | FAIL | 30% |
| ARCH-DEP-002 | PARTIAL | 60% |
| ARCH-DEP-003 | PARTIAL | 50% |
| ARCH-DEP-004 | PASS | 80% |
| ARCH-DEP-005 | FAIL | 40% |
| ARCH-FILE-001 | FAIL | 40% |
| Directory Structure | PARTIAL | 50% |

**Overall: 50% - NEEDS IMPROVEMENT**

---

## 8. Files Requiring Immediate Attention

1. `app/domain/services/compliance/compliance_engine.py` - 3500 lines, 20+ violations
2. `app/domain/tax/database/fifo_schema.py` - SQLAlchemy in domain
3. `app/domain/services/compliance/service_registry.py` - 10+ service imports
4. `app/domain/repositories/unit_of_work.py` - Infrastructure imports
5. `app/services/optimization_chan.py` - 2612 lines

---

*Generated by Claude Code Architecture Audit*
