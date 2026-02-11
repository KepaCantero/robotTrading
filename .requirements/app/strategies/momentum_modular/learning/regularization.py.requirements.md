# regularization.py

## Purpose
 file for regularization

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### RegularizationType
**Purpose:** Types of regularization....
### RegularizationResult
**Purpose:** Results from regularization analysis....
### RegularizationPathPoint
**Purpose:** Single point on regularization path....
### RegularizationPath
**Purpose:** Regularization path analysis....
### L1Regularization
**Purpose:** L1 Regularization (Lasso).

Implements Lasso regression as described in ESL Section 3.4.2.
L1 penalt...
### L2Regularization
**Purpose:** L2 Regularization (Ridge).

Implements Ridge regression as described in ESL Section 3.4.1.
L2 penalt...
### ElasticNetRegularization
**Purpose:** Elastic Net Regularization.

Implements Elastic Net as described in ESL Section 3.4.3.
Combines L1 a...
### AdaptiveLasso
**Purpose:** Adaptive Lasso.

Implements Adaptive Lasso as described in ESL.
Uses weights to penalize coefficient...
### RegularizationAnalyzer
**Purpose:** Comprehensive regularization analysis.

This class provides tools for analyzing and comparing differ...

---

## Function Signatures (Contracts)

### `RegularizationResult.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationPath.to_dict(self) -> Dict[str, Any]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.fit(self, X, y, sample_weight) -> 'L1Regularization'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.predict(self, X) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.score(self, X, y) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.get_coefficients(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.get_intercept(self) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.get_sparsity_mask(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L1Regularization.get_selected_features(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L2Regularization.fit(self, X, y, sample_weight) -> 'L2Regularization'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L2Regularization.predict(self, X) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L2Regularization.score(self, X, y) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L2Regularization.get_coefficients(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `L2Regularization.get_intercept(self) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.fit(self, X, y, sample_weight) -> 'ElasticNetRegularization'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.predict(self, X) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.score(self, X, y) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.get_coefficients(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.get_intercept(self) -> float`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `ElasticNetRegularization.get_sparsity_mask(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdaptiveLasso.fit(self, X, y) -> 'AdaptiveLasso'`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdaptiveLasso.predict(self, X) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `AdaptiveLasso.get_coefficients(self) -> np.ndarray`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationAnalyzer.analyze_l1_regularization(self, X, y, alpha, feature_names) -> RegularizationResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationAnalyzer.analyze_l2_regularization(self, X, y, alpha, feature_names) -> RegularizationResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationAnalyzer.analyze_elastic_net(self, X, y, alpha, l1_ratio, feature_names) -> RegularizationResult`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationAnalyzer.compute_regularization_path(self, X, y, regularization_type, n_alphas, alpha_range, l1_ratio, feature_names) -> RegularizationPath`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `RegularizationAnalyzer.compare_regularization_methods(self, X, y, alphas, l1_ratios, feature_names) -> Dict[str, List[RegularizationResult]]`
**Pre:** TBD
**Post:** TBD
**Raises:** TBD
**Retry:** ❌ No
**Side Effects:** TBD

### `optimize_regularization(X, y, method, cv_folds, feature_names) -> RegularizationResult`
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
- **test_regularization.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/strategies/momentum_modular/learning/regularization.py`
**Created:** 2026-02-05
**Status:** ⚠️ PENDING FULL AUDIT
