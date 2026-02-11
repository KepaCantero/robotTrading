# limit_adjuster.py

## Purpose
Implementation for limit_adjuster

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### AdjustedLimit
**Purpose:** Adjusted position limit after scaling....
### LimitBreach
**Purpose:** Position limit breach detection....
### LimitAdjuster
**Purpose:** Manages position sizing and leverage limits.

Enforces constraints:
- Position size limits (max € pe...

---

## Function Signatures (Contracts)

### `LimitAdjuster.__init__(self, default_position_limit, default_max_leverage, default_max_allocation) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.adjust_position_limits(self, original_allocations, scaling_factor, portfolio_value) -> List[AdjustedLimit]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.detect_limit_breaches(self, current_positions, adjusted_limits) -> List[LimitBreach]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.apply_leverage_adjustment(self, base_leverage, scaling_factor, market_condition) -> Tuple[Decimal, str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.validate_position_within_limits(self, module_name, proposed_position, adjusted_limits) -> Tuple[bool, str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.validate_leverage_within_limits(self, current_leverage, max_leverage) -> Tuple[bool, str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.enforce_hard_stops(self, breaches, critical_action) -> Tuple[bool, Dict]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.set_position_limit(self, limit) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.set_max_leverage(self, leverage) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `LimitAdjuster.set_max_allocation(self, allocation_pct) -> None`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `get_limit_adjuster() -> LimitAdjuster`
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
- **test_limit_adjuster.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/services/risk_scaling_application/limit_adjuster.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
