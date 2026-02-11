# factor_models.py

## Purpose
 file for factor models

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### FactorModelResult
**Purpose:** Result from factor model regression....
### BaseFactorModel
**Purpose:** Base class for factor models....
### CAPMModel
**Purpose:** Capital Asset Pricing Model (single-factor).

R_i - R_f = β_MKT * (R_M - R_f)...
### FF3FactorModel
**Purpose:** Fama-French 3-Factor Model.

R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML

Factors:
- MKT: Ma...
### FF5FactorModel
**Purpose:** Fama-French 5-Factor Model.

R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_RMW * RMW + β_C...
### Carhart4FactorModel
**Purpose:** Carhart 4-Factor Model (FF3 + Momentum).

R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_WM...
### FF6FactorModel
**Purpose:** Complete 6-Factor Model (FF5 + Momentum).

R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_R...
### SimpleOLSResult
**Purpose:** Simple OLS regression result....
### FactorModelManager
**Purpose:** Manager for factor model operations.

Provides unified interface for fitting different factor models...

---

## Function Signatures (Contracts)

### `BaseFactorModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `BaseFactorModel.predict(self, factor_returns, coefficients, alpha) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `CAPMModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FF3FactorModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FF5FactorModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `Carhart4FactorModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FF6FactorModel.fit(self, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FactorModelManager.fit_model(self, model_name, returns, factor_returns) -> FactorModelResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FactorModelManager.compare_models(self, returns, factor_returns) -> Dict[str, FactorModelResult]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FactorModelManager.get_best_model(self, results, metric) -> Tuple[str, FactorModelResult]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `FactorModelManager.calculate_factor_exposures_from_scores(self, factor_scores, method) -> Dict[str, float]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `sm_add_constant(x) -> np.ndarray`
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
- **test_factor_models.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/multi_factor/factor_models.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
