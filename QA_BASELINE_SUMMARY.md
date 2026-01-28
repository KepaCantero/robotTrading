# QA Baseline Summary - Quick Reference

## Overall Status: CRITICAL (26/100)

```
███░░░░░░░ 26% Code Formatting
███░░░░░░░ 31% Import Sorting
░░░░░░░░░░  0% Type Hints (BLOCKED)
██░░░░░░░░  7% Linting
████████░░ 80% Complexity
```

---

## Critical Numbers

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Files Needing Format | 289 | 0 | -289 |
| Import Issues | 219 | 0 | -219 |
| Syntax Errors | 5 | 0 | -5 ⚠️ |
| Undefined Names | 1,137 | 0 | -1,137 |
| Unused Imports | 604 | 0 | -604 |
| Grade F Functions | 10 | 0 | -10 |
| Grade E Functions | 13 | 0 | -13 |

---

## 5 Files with Syntax Errors (BLOCKING TYPE CHECKING)

1. `app/middleware/logging_middleware.py` - Line 7 code outside function
2. `app/dashboard/meta_dashboard_page.py` - Line 14 improper indent
3. `app/services/numba_risk.py` - Line 37 improper import indent
4. `app/optimization/momentum_auto_optimizer.py` - Line 139 import in wrong place
5. `app/sre/oncall/handoff.py` - Line 392 malformed string

---

## Top 10 Problematic Files

| File | Complexity | Ruff Errors | Main Issue |
|------|------------|-------------|------------|
| `app/dashboard/advanced_dashboard.py` | 259 (F) | - | Monolithic |
| `app/backtesting/comprehensive_backtest_runner.py` | 43 (F) | 441 | God object |
| `app/services/strategy_stock_allocator.py` | 66 (F) | - | Too complex |
| `app/backtesting/walk_forward_validator.py` | 52 (F) | - | Nested logic |
| `app/backtesting/engine.py` | 48 (F) | - | Multiple SRP |
| `app/services/live_trading/order_persistence.py` | - | 60 | Missing imports |
| `app/services/live_trading/trade_persistence.py` | - | 55 | Missing imports |
| `app/core/compliance_integration.py` | - | 45 | Missing imports |
| `app/backtesting/metrics.py` | 43 (F) | - | Too many metrics |
| `app/strategies/momentum.py` | 43 (F) | - | Complex signals |

---

## Quick Fix Commands

```bash
# Phase 0: Fix syntax errors manually
# (Edit the 5 files listed above)

# Phase 1: Auto-fix (30 min)
source .venv/bin/activate
isort app/ --fix-only     # Fix 219 import issues
black app/                # Fix 289 formatting issues
ruff check app/ --fix     # Fix 578 fixable errors

# Phase 2: Manual fixes (4-8 hours)
# Fix remaining 1,137 undefined name errors (mostly missing imports)

# Phase 3: Refactoring (20-40 hours)
# Break down 23 functions with D-F complexity
```

---

## Estimated Effort

| Phase | Task | Time |
|-------|------|------|
| 0 | Fix 5 syntax errors | 2-4h |
| 1 | Run auto-fixers | 0.5h |
| 2 | Fix undefined names | 4-8h |
| 3 | Refactor complexity | 20-40h |
| 4 | Add type hints | 16-24h |
| **TOTAL** | | **40-80h** |

---

## Priority Order

1. ⚠️ **CRITICAL:** Fix 5 syntax errors (blocks everything else)
2. 🔴 **HIGH:** Fix 1,137 undefined name errors
3. 🟠 **HIGH:** Run auto-fixers (isort, black, ruff)
4. 🟡 **MEDIUM:** Refactor 10 Grade F functions
5. 🟢 **LOW:** Add type hints

---

## Files Created

- `QA_BASELINE_REPORT.md` - Full detailed report
- `QA_BASELINE_SUMMARY.md` - This quick reference
- `run_qa_checks.sh` - Script to re-run checks
- `/tmp/black_output.txt` - Raw black output
- `/tmp/isort_output.txt` - Raw isort output
- `/tmp/mypy_output.txt` - Raw mypy output
- `/tmp/ruff_output.txt` - Raw ruff output
- `/tmp/radon_output.txt` - Raw radon output

---

## Key Issues by Type

### Formatting (Black)
- 289/710 files need reformatting (40.7%)
- 5 files have syntax errors

### Imports (isort)
- 219/716 files have issues (30.6%)

### Type Hints (mypy)
- BLOCKED by 5 syntax errors

### Linting (ruff)
- 1,900 total errors
- 578 auto-fixable (30.4%)
- Top issue: F821 undefined name (1,137)

### Complexity (radon)
- 10,175 blocks analyzed
- Average: 3.74 (Grade A)
- 23 blocks with D-F grade (need refactoring)

---

## Compliance Status

| Rule | Status | Score |
|------|--------|-------|
| 01-formatting-style | ❌ FAILED | 28.8% |
| 02-type-hints | ⛔ BLOCKED | N/A |
| 03-solid-principles | ⚠️ WARNING | N/A |
| 04-design-patterns | ⚠️ WARNING | N/A |
| 05-architecture | ⚠️ WARNING | N/A |

---

**Generated:** 2026-01-30
**Analyzed:** 716 Python files
