# parameter_stability.py

## Purpose
Analyzes parameter stability across walk-forward windows using Mann-Kendall trend test, coefficient of variation calculation, and Kolmogorov-Smirnov distribution comparison. Detects parameter drift and provides actionable recommendations.

---

## Type Definitions / Data Classes

### ParameterStabilityAnalyzer Class
```python
class ParameterStabilityAnalyzer:
    stable_threshold: float      # Minimum score for "stable" (default: 70.0)
    moderate_threshold: float    # Minimum score for "moderate" (default: 40.0)
```

**Validation Rules:**
- `0 <= moderate_threshold <= stable_threshold <= 100`
- `stable_threshold > moderate_threshold` (hierarchical classification)

---

## Function Signatures (Contracts)

### `ParameterStabilityAnalyzer.__init__(stable_threshold: float = 70.0, moderate_threshold: float = 40.0)`
**Pre:** `0 <= moderate_threshold <= stable_threshold <= 100`
**Post:** Analyzer initialized with specified thresholds
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Sets instance attributes

### `ParameterStabilityAnalyzer.analyze(is_params: List[Dict[str, Any]], os_params: List[Dict[str, Any]]) -> List[ParameterStabilityResult]`
**Pre:** `is_params` is non-empty list of parameter dicts
**Post:** Returns list of stability results for each unique parameter
**Raises:** ❌ No (returns empty list if no IS params)
**Retry:** ❌ No
**Side Effects:** Logs warnings for missing parameter values

### `ParameterStabilityAnalyzer.calculate_stability_score(is_std: Decimal, is_mean: Decimal) -> Decimal`
**Pre:** `is_std >= 0`
**Post:** Returns stability score (0-100) = 100 × (1 - CV)
**Raises:** ❌ No (returns 0 if `is_mean == 0`)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityAnalyzer.detect_drift(param_values: List[float]) -> bool`
**Pre:** None
**Post:** Returns True if Mann-Kendall test shows significant trend (p < 0.05)
**Raises:** ❌ No (returns False if < 3 values)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityAnalyzer.compare_parameter_distributions(is_params: List[Dict[str, Any]], os_params: List[Dict[str, Any]]) -> Dict[str, Any]`
**Pre:** Both lists have at least 3 observations per parameter
**Post:** Returns dict with KS test results (statistic, p_value, same_distribution)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityAnalyzer.calculate_parameter_correlation(params_history: List[Dict[str, Any]]) -> pd.DataFrame`
**Pre:** `params_history` contains numeric parameter values
**Post:** Returns correlation matrix DataFrame
**Raises:** ❌ No (returns empty DataFrame if no numeric data)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityAnalyzer.find_redundant_parameters(params_history: List[Dict[str, Any]], threshold: float = 0.9) -> List[Tuple[str, str]]`
**Pre:** `params_history` has numeric parameters
**Post:** Returns list of (param1, param2) tuples with |correlation| >= threshold
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `calculate_parameter_stability(param_values: List[float]) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with mean, std, cv, stability_score, stability_level
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `detect_parameter_drift_simple(param_values: List[float], window: int = 3) -> bool`
**Pre:** None
**Post:** Returns True if early/late window means differ by > 20%
**Raises:** ❌ No (returns False if < window + 1 values)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `rank_parameters_by_stability(stability_results: List[ParameterStabilityResult]) -> List[ParameterStabilityResult]`
**Pre:** `stability_results` is non-empty
**Post:** Returns results sorted by stability_score (descending)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `filter_stable_parameters(stability_results: List[ParameterStabilityResult], min_score: float = 70.0) -> List[str]`
**Pre:** None
**Post:** Returns list of parameter names with score >= min_score and no drift
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] `stable_threshold` defaults to 70.0
- [ ] `moderate_threshold` defaults to 40.0
- [ ] `analyze()` returns empty list when `is_params` is empty
- [ ] `analyze()` processes all unique parameter names from both IS and OS
- [ ] `calculate_stability_score()` returns 0 when `is_mean == 0`
- [ ] `calculate_stability_score()` clamps result to [0, 100]
- [ ] `detect_drift()` uses Mann-Kendall test (significance at p < 0.05, |z| > 1.96)
- [ ] `detect_drift()` returns False when < 3 values
- [ ] `compare_parameter_distributions()` uses Kolmogorov-Smirnov test
- [ ] `compare_parameter_distributions()` skips parameters with < 3 values
- [ ] `calculate_parameter_correlation()` uses pandas DataFrame.corr()
- [ ] `find_redundant_parameters()` returns tuples with |correlation| >= threshold
- [ ] `calculate_parameter_stability()` returns "stable" for score >= 70
- [ ] `calculate_parameter_stability()` returns "moderate" for score >= 40
- [ ] `calculate_parameter_stability()` returns "unstable" for score < 40
- [ ] `detect_parameter_drift_simple()` uses 20% change threshold
- [ ] `detect_parameter_drift_simple()` requires window + 1 values minimum
- [ ] `rank_parameters_by_stability()` sorts descending (most stable first)
- [ ] `filter_stable_parameters()` excludes parameters with drift_detected=True

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| TYP-002 | 02-type-hints.md | Use modern syntax (List, Dict, Optional) | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Uses logging but not structured |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK - Logs warnings |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - Try/except in _extract_param_values |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - Analyzes WF parameters |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Sequential analysis |

**GAPS Found:**
- **LOG-001 (P1):** Not using structured logging (no JSON format)
- **TYP-003 (P1):** Uses `Dict[str, Any]` without more specific types for parameter dicts

---

## Dependencies
- **External:**
  - `numpy` (numerical calculations: mean, std, polyfit)
  - `pandas` (DataFrame for correlation matrix)
  - `scipy.stats` (statistical tests: ks_2samp)
  - `decimal.Decimal` (financial precision)
  - `dataclasses` (standard library)
  - `logging` (standard library)
  - `typing` (standard library)

- **Internal:**
  - `.models.ParameterStabilityResult`
  - `.models.StabilityLevel`

---

## Required Tests
- **tests/unit/backtesting/validation/test_parameter_stability.py:**
  - Test `analyze()` returns empty list for empty IS params
  - Test `analyze()` extracts all unique parameter names
  - Test `analyze()` calculates correct mean and std for each parameter
  - Test `analyze()` classifies stability levels correctly
  - Test `analyze()` detects drift using Mann-Kendall test
  - Test `calculate_stability_score()` with zero mean
  - Test `calculate_stability_score()` clamps to [0, 100]
  - Test `detect_drift()` returns False for < 3 values
  - Test `detect_drift()` detects monotonic increasing trend
  - Test `detect_drift()` detects monotonic decreasing trend
  - Test `detect_drift()` returns False for no trend
  - Test `compare_parameter_distributions()` performs KS test
  - Test `compare_parameter_distributions()` sets same_distribution correctly
  - Test `calculate_parameter_correlation()` returns correct correlation matrix
  - Test `find_redundant_parameters()` finds highly correlated pairs
  - Test `find_redundant_parameters()` uses correct threshold
  - Test `calculate_parameter_stability()` returns correct stability_level
  - Test `detect_parameter_drift_simple()` detects > 20% change
  - Test `detect_parameter_drift_simple()` handles zero mean
  - Test `rank_parameters_by_stability()` sorts descending
  - Test `filter_stable_parameters()` filters by score and drift
  - Test `_extract_param_values()` handles non-numeric values gracefully
  - Test `_generate_recommendation()` provides actionable recommendations
  - Test Mann-Kendall Z-score calculation correctness
  - Test coefficient of variation calculation

---

## Notes
- **Mann-Kendall Trend Test:**
  - Non-parametric test for monotonic trends
  - Robust to non-normal distributions
  - Significance: p < 0.05 (|z| > 1.96)
  - Formula: Z = (S - sign(S)) / sqrt(Var(S))
- **Stability Score Formula:**
  - Score = 100 × (1 - CV) where CV = std / mean
  - Higher score = more stable
  - Clamped to [0, 100] range
- **Recommendations Logic:**
  - Drift detected: Consider adaptive parameters or removal
  - Stable: Good candidate for fixed parameters
  - Moderate: Consider periodic reoptimization
  - Unstable: Strongly consider removal or regime-specific values
- **References:**
  - López de Prado, "Advances in Financial Machine Learning"
  - Mann, H. B. (1945). "Nonparametric tests against trend"
- This is a FASE 5.3 Validation module
- Module provides both class-based and functional API
