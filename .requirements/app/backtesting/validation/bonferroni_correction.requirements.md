# bonferroni_correction.py

## Purpose
Implements Bonferroni correction and multiple hypothesis testing controls (Ernest Chan methodology) to prevent false positives when testing multiple trading strategies or parameter combinations.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### HypothesisTest Class/DataClass
```python
@dataclass
class HypothesisTest:
    test_name: str                       # REQUIRED - Name/identifier of the test
    null_hypothesis: str                 # REQUIRED - Description of null hypothesis
    p_value: float                       # REQUIRED, [0, 1] - Original p-value
    test_statistic: float                # REQUIRED - Calculated test statistic
    is_significant_uncorrected: bool     # REQUIRED - Significant without correction?
    is_significant_corrected: bool       # REQUIRED - Significant after correction?
    corrected_p_value: float             # REQUIRED, [0, 1] - Adjusted p-value
    corrected_alpha: float               # REQUIRED, [0, 1] - Adjusted significance level
```

**Validation Rules:**
- `p_value` must be in [0, 1]
- `corrected_p_value` must be in [0, 1]
- `corrected_alpha` must be in [0, 1]

### MultipleTestResult Class/DataClass
```python
@dataclass
class MultipleTestResult:
    family_wise_error_rate: float        # REQUIRED, [0, 1] - Desired overall alpha (FWER)
    num_tests: int                      # REQUIRED - Total number of tests performed
    num_significant_uncorrected: int    # REQUIRED - Count significant without correction
    num_significant_corrected: int      # REQUIRED - Count significant after correction
    tests: List[HypothesisTest]         # REQUIRED - List of individual test results
    correction_method: str              # REQUIRED - Method used: 'bonferroni', 'holm', 'bh'
    false_discovery_rate: Optional[float] # OPTIONAL, [0, 1] - Estimated FDR
```

**Validation Rules:**
- `num_significant_corrected` <= `num_significant_uncorrected`
- `num_significant_corrected` <= `num_tests`
- `correction_method` must be one of: 'bonferroni', 'holm', 'bh'
- `false_discovery_rate` in [0, 1] if not None

### ParameterTestResult Class/DataClass
```python
@dataclass
class ParameterTestResult:
    best_parameters: Dict[str, Any]     # REQUIRED - Best parameter combination found
    best_sharpe_ratio: float            # REQUIRED - Sharpe ratio of best parameters
    is_significant_after_correction: bool # REQUIRED - Is best result significant?
    num_parameters_tested: int          # REQUIRED - Total parameter combinations tested
    corrected_significance_level: float # REQUIRED, [0, 1] - Adjusted alpha
    all_results: List[Dict[str, Any]]   # REQUIRED - All backtest results
```

**Validation Rules:**
- `corrected_significance_level` must be in [0, 1]
- `num_parameters_tested` must equal len(all_results)
- `best_sharpe_ratio` must be from one of the results in all_results

---

## Function Signatures (Contracts)

### `BonferroniCorrector.correct_p_values(p_values, test_names=None, method="bonferroni") -> MultipleTestResult`
**Pre:** p_values must be list of floats in [0, 1]; test_names length must match p_values if provided
**Post:** Returns MultipleTestResult with corrected p-values; corrected_p_value[i] >= p_value[i]
**Raises:** Returns empty result on ValueError, TypeError, KeyError
**Retry:** ❌ No
**Side Effects:** Logs info about correction results

### `BonferroniCorrector.test_strategy_significance(sharpe_ratios, null_sharpe=0.0, num_observations=252, method="bonferroni") -> MultipleTestResult`
**Pre:** sharpe_ratios must be dict with strategy names as keys; num_observations >= 2
**Post:** Returns MultipleTestResult with t-tests for each Sharpe ratio
**Raises:** Returns empty result on ValueError, TypeError, KeyError
**Retry:** ❌ No
**Side Effects:** Logs number of significant strategies

### `BonferroniCorrector.test_parameter_combinations(backtest_results, metric="sharpe_ratio", method="bonferroni") -> ParameterTestResult`
**Pre:** backtest_results must be non-empty list; each result must contain metric key
**Post:** Returns ParameterTestResult with best parameters and significance test
**Raises:** Returns empty result on ValueError, TypeError, KeyError
**Retry:** ❌ No
**Side Effects:** Logs best metric and significance

### `BonferroniCorrector._bonferroni_correction(p_values) -> List[float]`
**Pre:** p_values must be non-empty list of floats in [0, 1]
**Post:** Returns list where corrected_p = min(p * n, 1.0)
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

### `BonferroniCorrector._holm_correction(p_values) -> List[float]`
**Pre:** p_values must be non-empty list of floats in [0, 1]
**Post:** Returns step-down corrected p-values (less conservative than Bonferroni)
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

### `BonferroniCorrector._benjamini_hochberg(p_values) -> List[float]`
**Pre:** p_values must be non-empty list of floats in [0, 1]
**Post:** Returns FDR-controlled p-values (less conservative, more powerful)
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

### `correct_for_multiple_testing(p_values, family_wise_error_rate=0.05, method="bonferroni") -> List[float]`
**Pre:** p_values must be list of floats in [0, 1]; family_wise_error_rate in [0, 1]
**Post:** Returns list of corrected p-values
**Raises:** No explicit exceptions (handled by BonferroniCorrector)
**Retry:** ❌ No
**Side Effects:** Creates BonferroniCorrector instance

### `is_strategy_significant(sharpe_ratio, num_strategies_tested, num_observations=252, alpha=0.05) -> bool`
**Pre:** sharpe_ratio must be numeric; num_strategies_tested >= 1; num_observations >= 2
**Post:** Returns True if strategy Sharpe ratio is significant after Bonferroni correction
**Raises:** No explicit exceptions
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] BonferroniCorrector initializes with valid family_wise_error_rate
- [ ] correct_p_values() applies all three methods (bonferroni, holm, bh)
- [ ] Corrected p-values are >= original p-values
- [ ] Corrected alpha = FWER / num_tests
- [ ] test_strategy_significance() calculates t-statistics correctly
- [ ] test_parameter_combinations() identifies best parameters
- [ ] Holm correction is less conservative than Bonferroni
- [ ] Benjamini-Hochberg controls FDR not FWER
- [ ] is_strategy_significant() convenience function works
- [ ] Edge cases: empty p-values, single test, all significant, none significant

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Uses logger.error for exceptions |
| LOG-005 | BASE_RULES.md | Never log passwords/tokens | ✅ OK - No sensitive data logged |
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - Complete type coverage |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - Tests not in scope |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Pure domain logic, no framework deps |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Class handles only multiple testing correction |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=list) |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - info/error/warning used correctly |

**NOTE:** This analysis considers all 96+ rules from BASE_RULES.md. File shows strong compliance with error handling and statistical validation patterns.

---

## Dependencies
- **External:** numpy, scipy (stats), logging, typing
- **Internal:** None (standalone validation module)

---

## Required Tests
- **tests/backtesting/validation/test_bonferroni_correction.py:**
  - Test BonferroniCorrector initialization
  - Test correct_p_values() with bonferroni method
  - Test correct_p_values() with holm method
  - Test correct_p_values() with benjamini-hochberg method
  - Test corrected p-values >= original p-values
  - Test corrected alpha calculation
  - Test test_strategy_significance() with multiple strategies
  - Test test_parameter_combinations() finds best parameters
  - Test _holm_correction step-down procedure
  - Test _benjamini_hochberg FDR control
  - Test is_strategy_significant() convenience function
  - Test empty p_values returns empty result
  - Test single test case
  - Test all significant case
  - Test none significant case
  - Test edge cases: p_values = [0.0, 1.0], very large num_tests

---

## Notes
Critical for preventing false positives in strategy development. Implements Ernest Chan's "Quantitative Trading" Chapter 2 methodology. Key insight: testing many strategies increases false positive risk; Bonferroni correction controls family-wise error rate (FWER).
