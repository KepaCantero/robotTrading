# Directory Consolidation Plan

**Date:** 2026-03-15
**Status:** PHASE 2/3 PLANNING DOCUMENT
**Source:** ARCHITECTURE_AUDIT_REPORT.md + FILE_SYSTEM_AUDIT_REPORT.md

---

## Executive Summary

This document outlines the consolidation plan for non-standard directories in the `app/` folder. The target architecture follows Clean Architecture with 5 core layers:

```
app/
├── core/           # Cross-cutting concerns, protocols, config
├── domain/         # Business logic, entities, value objects
├── services/       # Application services, use case orchestration
├── infrastructure/ # External integrations, persistence
└── api/            # HTTP endpoints, controllers
```

**Current State:** 14 top-level directories (9 non-standard)
**Target State:** 5 standard directories + 2 justified exceptions

---

## Non-Standard Directories Analysis

| Directory | Files | Issue | Phase | Action |
|-----------|-------|-------|-------|--------|
| `app/application/` | 34 | Overlaps with `services/` | 2 | Merge into `services/` |
| `app/engines/` | 105 | Overlaps with `services/` | 2 | Merge into `services/` |
| `app/models/` | 2 | Should be in `domain/` | 3 | Move to `domain/models/` |
| `app/presentation/` | 63 | Overlaps with `api/` | 3 | Merge into `api/` |
| `app/security/` | 16 | Not in spec | 2 | Move to `services/security/` |
| `app/shared/` | 68 | Overlaps with `core/` | 2 | Merge into `core/` |
| `app/simulation/` | 6 | Not in spec | 2 | Move to `services/simulation/` |
| `app/sre/` | 37 | Not in spec | 3 | Move to `infrastructure/monitoring/` |
| `app/backtesting/` | 165 | Not in spec | KEEP | Justified - quant-specific |

---

## Phase 2 Migrations (Medium Priority)

### 2.1 Merge `app/application/` into `app/services/`

**Current Structure:**
```
app/application/
├── dto/              # Data Transfer Objects
├── routers/          # API routing logic
├── alerting/         # Alert handling
├── reconciliation/   # Trade reconciliation
├── reporting/        # Report generation
├── scheduling/       # Job scheduling
├── orchestration/    # Workflow orchestration
└── use_cases/        # Use case implementations
```

**Target Structure:**
```
app/services/
├── dto/              # (merge from application/dto/)
├── alerting/         # (merge from application/alerting/)
├── reconciliation/   # (merge from application/reconciliation/)
├── reporting/        # (merge from application/reporting/)
├── scheduling/       # (merge from application/scheduling/)
├── orchestration/    # (merge from application/orchestration/)
└── use_cases/        # (merge from application/use_cases/)
```

**Migration Steps:**
1. Create target directories in `app/services/`
2. Move files using `git mv`
3. Update all import statements
4. Run tests to verify
5. Delete empty `app/application/` directory

**Import Updates Required:**
```python
# BEFORE
from app.application.scheduling.market_scheduler import MarketScheduler
from app.application.dto.trade_dto import TradeDTO

# AFTER
from app.services.scheduling.market_scheduler import MarketScheduler
from app.services.dto.trade_dto import TradeDTO
```

**Estimated Impact:** ~200 import statements across codebase

---

### 2.2 Merge `app/engines/` into `app/services/`

**Current Structure:**
```
app/engines/
└── risk_engine/
    ├── exposure_managers/
    ├── correlation_analyzers/
    ├── risk_attribution/
    ├── stress_testers/
    ├── var_calculators/
    └── drawdown_controllers/
```

**Target Structure:**
```
app/services/
└── risk_engine/      # (rename from engines/risk_engine/)
    ├── exposure_managers/
    ├── correlation_analyzers/
    ├── risk_attribution/
    ├── stress_testers/
    ├── var_calculators/
    └── drawdown_controllers/
```

**Migration Steps:**
1. Move `app/engines/risk_engine/` to `app/services/risk_engine/`
2. Update all import statements
3. Run tests to verify
4. Delete empty `app/engines/` directory

**Import Updates Required:**
```python
# BEFORE
from app.engines.risk_engine.var_calculators import VaRCalculator

# AFTER
from app.services.risk_engine.var_calculators import VaRCalculator
```

**Estimated Impact:** ~150 import statements

---

### 2.3 Move `app/security/` to `app/services/security/`

**Current Structure:**
```
app/security/
├── auth/
├── encryption/
└── validation/
```

**Target Structure:**
```
app/services/security/
├── auth/
├── encryption/
└── validation/
```

**Migration Steps:**
1. Move entire directory to `app/services/security/`
2. Update imports
3. Run tests

**Estimated Impact:** ~30 import statements

---

### 2.4 Merge `app/shared/` into `app/core/`

**Current Structure:**
```
app/shared/
├── config/
│   ├── params/
│   └── base/
├── decorators/
├── constants/
├── utils/
└── exceptions/
```

**Target Structure:**
```
app/core/
├── config/           # (merge from shared/config/)
│   ├── params/
│   └── base/
├── decorators/       # (merge from shared/decorators/)
├── constants/        # (merge from shared/constants/)
├── utils/            # (merge with existing core/utils/)
└── exceptions/       # (merge from shared/exceptions/)
```

**Migration Steps:**
1. Merge `shared/config/` into `core/config/`
2. Merge `shared/decorators/` into `core/decorators/`
3. Merge `shared/constants/` into `core/constants/`
4. Merge `shared/utils/` into `core/utils/`
5. Merge `shared/exceptions/` into `core/exceptions/`
6. Update all imports
7. Delete `app/shared/`

**Estimated Impact:** ~100 import statements

---

### 2.5 Move `app/simulation/` to `app/services/simulation/`

**Current Structure:**
```
app/simulation/
├── market_simulator.py
├── order_simulator.py
└── ...
```

**Target Structure:**
```
app/services/simulation/
├── market_simulator.py
├── order_simulator.py
└── ...
```

**Migration Steps:**
1. Move directory to `app/services/simulation/`
2. Update imports

**Estimated Impact:** ~15 import statements

---

## Phase 3 Migrations (Lower Priority)

### 3.1 Move `app/models/` to `app/domain/models/`

**Current:** 2 files in `app/models/`
**Target:** `app/domain/models/`

**Migration Steps:**
1. Move files to `app/domain/models/`
2. Update imports

**Estimated Impact:** ~10 import statements

---

### 3.2 Merge `app/presentation/` into `app/api/`

**Current Structure:**
```
app/presentation/
├── dto/
├── dashboard/
│   └── frontend/
├── api/
├── controllers/
└── views/
```

**Target Structure:**
```
app/api/
├── dto/              # (merge from presentation/dto/)
├── dashboard/        # (move from presentation/dashboard/)
│   └── frontend/
├── controllers/      # (merge from presentation/controllers/)
├── views/            # (merge from presentation/views/)
└── [existing endpoints]
```

**Migration Steps:**
1. Move `presentation/dto/` to `api/dto/`
2. Move `presentation/dashboard/` to `api/dashboard/`
3. Move `presentation/controllers/` to `api/controllers/`
4. Move `presentation/views/` to `api/views/`
5. Merge `presentation/api/` into existing `api/`
6. Update all imports
7. Delete `app/presentation/`

**Estimated Impact:** ~150 import statements

---

### 3.3 Move `app/sre/` to `app/infrastructure/monitoring/`

**Current Structure:**
```
app/sre/
├── oncall/
│   └── runbooks/
├── observability/
└── incident/
```

**Target Structure:**
```
app/infrastructure/monitoring/
├── oncall/
│   └── runbooks/
├── observability/
└── incident/
```

**Migration Steps:**
1. Create `app/infrastructure/monitoring/`
2. Move all SRE components
3. Update imports

**Estimated Impact:** ~50 import statements

---

## Justified Exceptions

### `app/backtesting/` - KEEP AS-IS

**Rationale:**
- Domain-specific for quantitative trading
- Contains 165 files with complex interdependencies
- Deep nesting (depth 10) is justified by the domain complexity
- Well-isolated from other components
- Moving would disrupt a mature, working subsystem

**Recommendation:** Keep as top-level directory. Document as exception in architecture spec.

---

## Implementation Order

### Phase 2 (Recommended First)
1. `app/shared/` → `app/core/` (largest impact on shared utilities)
2. `app/application/` → `app/services/` (aligns with Clean Architecture)
3. `app/engines/` → `app/services/` (consolidates engine logic)
4. `app/security/` → `app/services/security/`
5. `app/simulation/` → `app/services/simulation/`

### Phase 3 (Follow-up)
1. `app/models/` → `app/domain/models/`
2. `app/presentation/` → `app/api/`
3. `app/sre/` → `app/infrastructure/monitoring/`

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking imports | Use IDE refactoring tools, run tests after each migration |
| Circular imports | Analyze dependency graph before moving |
| Test failures | Run full test suite after each directory migration |
| Git history loss | Use `git mv` to preserve history |
| Deployment issues | Deploy incrementally, one directory at a time |

---

## Verification Checklist

After each migration:
- [ ] All imports updated
- [ ] Tests pass: `pytest`
- [ ] Type check passes: `mypy app/`
- [ ] Lint passes: `ruff check app/`
- [ ] No circular imports: `python -c "import app"`
- [ ] Empty source directory deleted

---

## Summary

| Phase | Directories | Files Moved | Import Updates |
|-------|-------------|-------------|----------------|
| 2 | 5 | ~223 | ~495 |
| 3 | 3 | ~102 | ~210 |
| **Total** | **8** | **~325** | **~705** |

**Recommended Approach:** Execute one directory migration per sprint to minimize risk and allow thorough testing.

---

*Generated by Claude Code - Directory Consolidation Planner*
