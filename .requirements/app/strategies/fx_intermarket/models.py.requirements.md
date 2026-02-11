# models.py

## Purpose
 file for models

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### AssetClass
**Purpose:** Asset class enumeration for external markets.

Defines the major asset classes that can have interma...
### RelationshipType
**Purpose:** Types of intermarket relationships.

Defines the various ways FX pairs can correlate with external a...
### FXCorrelationPair
**Purpose:** Correlation between two FX pairs.

Stores statistical metrics for the correlation between two curren...
### IntermarketRelationship
**Purpose:** Relationship between an FX pair and an external asset.

Stores the correlation metrics and relations...
### IntermarketSignal
**Purpose:** Trading signal based on intermarket relationships.

Represents a trading signal generated from inter...
### FXIntermarketConfig
**Purpose:** Configuration for FX Intermarket strategy.

Defines all configurable parameters for the intermarket ...

---

## Function Signatures (Contracts)

### `FXCorrelationPair.validate_correlation(cls, v) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXCorrelationPair.is_significant(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXCorrelationPair.is_strong(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXCorrelationPair.direction(self) -> str`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketRelationship.validate_correlation(cls, v) -> Decimal`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketRelationship.validate_relationship_consistency(self) -> 'IntermarketRelationship'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketRelationship.is_active(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketRelationship.strength(self) -> str`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketSignal.validate_signal_consistency(self) -> 'IntermarketSignal'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketSignal.is_buy(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketSignal.is_sell(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `IntermarketSignal.is_actionable(self) -> bool`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXIntermarketConfig.validate_risk_parameters(self) -> 'FXIntermarketConfig'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXIntermarketConfig.get_fx_pairs(self) -> list[str]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXIntermarketConfig.get_external_assets(self) -> dict[str, AssetClass]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FXIntermarketConfig.get_active_relationship_types(self) -> list[RelationshipType]`
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
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_models.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/fx_intermarket/models.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
