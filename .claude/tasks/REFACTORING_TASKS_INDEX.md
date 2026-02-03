# Refactoring Tasks Index

This index contains all architectural refactoring tasks identified during the GAP audit.

## Overview

These tasks address **architectural violations** found during the comprehensive GAP audit:
- **DP-004**: Direct instantiation violations (Dependency Injection required)
- **ARCH-001**: Layering violations (business logic in wrong layer)

---

## Tasks by Priority

### P1 (High Priority) - 4 Tasks

| # | Task | File | Issue | Estimated Effort |
|---|------|------|-------|------------------|
| 1 | [refactor_portfolio_di.md](./refactor_portfolio_di.md) | `app/api/portfolio.py` | DP-004 | 2-3 hours |
| 2 | [refactor_signals_di.md](./refactor_signals_di.md) | `app/api/signals.py` | DP-004 | 2-3 hours |
| 3 | [refactor_strategies_di.md](./refactor_strategies_di.md) | `app/api/strategies.py` | DP-004 | 3-4 hours |
| 4 | [refactor_health_db_layer.md](./refactor_health_db_layer.md) | `app/api/health.py` | ARCH-001 | 2-3 hours |

---

## Tasks by Issue Type

### DP-004: Dependency Injection Violations (3 tasks)

**Issue:** Direct instantiation in API layer violates Dependency Inversion Principle

1. **[refactor_portfolio_di.md](./refactor_portfolio_di.md)** - `app/api/portfolio.py`
   - Line 43: Direct instantiation of `PaperTradingPortfolioProvider`
   - Solution: Create DI container with `PortfolioService`

2. **[refactor_signals_di.md](./refactor_signals_di.md)** - `app/api/signals.py`
   - Lines 36-38: Direct instantiation chain for `SignalScorerService`
   - Solution: Extend DI container with `SignalScorerService` (depends on PortfolioService)

3. **[refactor_strategies_di.md](./refactor_strategies_di.md)** - `app/api/strategies.py`
   - Lines 32, 41, 50, 62: Four singleton getter functions with direct instantiation
   - Solution: Extend DI container with all 4 strategy services

### ARCH-001: Layering Violations (1 task)

**Issue:** Infrastructure/database logic in API layer

4. **[refactor_health_db_layer.md](./refactor_health_db_layer.md)** - `app/api/health.py`
   - Lines 87-93: SQLite connection and queries in API layer
   - Solution: Move to `app/infrastructure/health/` service layer

---

## Dependency Graph

```
refactor_portfolio_di.md (Foundation)
    │
    ├─→ refactor_signals_di.md (depends on PortfolioService)
    │
    └─→ refactor_strategies_di.md (depends on DI pattern)

refactor_health_db_layer.md (Independent)
```

### Execution Order

1. **First:** `refactor_portfolio_di.md` - Establishes DI container pattern
2. **Second:** `refactor_signals_di.md` - Extends DI container (depends on #1)
3. **Third:** `refactor_strategies_di.md` - Extends DI container further
4. **Anytime:** `refactor_health_db_layer.md` - Independent of others

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Tasks** | 4 |
| **P1 (High)** | 4 |
| **P2 (Medium)** | 0 |
| **P3 (Low)** | 0 |
| **Total Estimated Effort** | 9-13 hours |
| **Files to Modify** | 5 API files + 1 new infrastructure file |
| **New Files to Create** | 2 (DI container, health checker) |
| **Test Files to Create/Update** | 4 |

---

## Quick Start

To execute all refactoring tasks in order:

```bash
# 1. Start with portfolio DI (foundation)
cd /Users/kepa.cantero/Projects/algoTrading
cat .claude/tasks/refactor_portfolio_di.md

# 2. Continue with signals DI
cat .claude/tasks/refactor_signals_di.md

# 3. Continue with strategies DI
cat .claude/tasks/refactor_strategies_di.md

# 4. Complete with health DB layer (can be done anytime)
cat .claude/tasks/refactor_health_db_layer.md
```

---

## BASE_RULES Compliance

| Rule | Current | After Refactoring |
|------|---------|-------------------|
| DP-004 | ❌ VIOLATED | ✅ PASS |
| ARCH-001 | ❌ VIOLATED | ✅ PASS |
| ARCH-003 | ⚠️ PARTIAL | ✅ PASS |
| SOL-001 | ⚠️ PARTIAL | ✅ PASS |
| SOL-005 | ❌ VIOLATED | ✅ PASS |
| TEST-001 | ⚠️ PARTIAL | ✅ PASS |

---

**Last Updated:** 2026-02-02
**GAP Audit Reference:** COMPREHENSIVE_AUDIT_SUMMARY.md
