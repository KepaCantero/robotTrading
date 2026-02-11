# exit_monitor.py

## Purpose
Implementation for exit_monitor

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### ExitConditionMonitor
**Purpose:** Monitor and trigger stop-loss and take-profit exits.

This service handles:
- Stop-loss monitoring
-...

---

## Function Signatures (Contracts)

### `ExitConditionMonitor.__init__(self, config, position_manager, apply_slippage_func) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.check_exit_conditions(self, market_data, trades, close_position_func) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.check_all_symbols_exit_conditions(self, market_data, trades, close_position_func) -> int`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.calculate_stop_loss_price(self, entry_price) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.calculate_take_profit_price(self, entry_price) -> Optional[Decimal]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.is_stop_loss_hit(self, market_data, stop_loss_price) -> tuple[bool, Optional[Decimal]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ExitConditionMonitor.is_take_profit_hit(self, market_data, take_profit_price) -> tuple[bool, Optional[Decimal]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD


---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports (if domain) | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_exit_monitor.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/backtesting/services/exit_monitor.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
