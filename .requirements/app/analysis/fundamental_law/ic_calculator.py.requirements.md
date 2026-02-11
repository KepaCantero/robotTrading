# ic_calculator.py

## Purpose
Calculate and analyze the Information Coefficient (IC), which measures the correlation between forecasted returns and actual realized returns. This is a key measure of forecasting skill in active portfolio management.

---

## Type Definitions / Data Classes

### ICMetrics Class/DataClass (imported from models.py)
```python
@dataclass
class ICMetrics:
    ic: Decimal                    # REQUIRED - Pearson correlation coefficient (forecast vs actual)
    ic_rank: Decimal               # REQUIRED - Spearman rank correlation
    ic_decay: List[Decimal]        # OPTIONAL - IC values over different forward horizons
    statistical_significance: float # REQUIRED - P-value for statistical test
    confidence_interval: Tuple[Decimal, Decimal]  # REQUIRED - 95% CI bounds
```

**Validation Rules:**
- ic must be in [-1, 1] range
- ic_rank must be in [-1, 1] range
- statistical_significance must be in [0, 1] range
- confidence_interval lower <= upper

---

## Function Signatures (Contracts)

### `__init__(min_observations: int = 20) -> ICCalculator`
**Pre:** min_observations >= 10
**Post:** Calculator initialized with minimum observation threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_ic(forecasts: pd.Series, returns: pd.Series, method: str = "pearson") -> ICMetrics`
**Pre:** len(forecasts) == len(returns) >= min_observations
**Post:** ICMetrics with IC, rank IC, significance, and confidence interval
**Raises:** ValueError if lengths differ or insufficient data
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_ic_decay(forecasts: pd.Series, returns: pd.Series, periods: List[int] = [1, 5, 10, 20]) -> List[Decimal]`
**Pre:** len(forecasts) >= max(periods) + min_observations
**Post:** List of IC values for each forward period
**Raises:** ValueError if insufficient data for any period
**Retry:** No
**Side Effects:** None

### `test_significance(ic: float, n_observations: int) -> Tuple[float, bool]`
**Pre:** n_observations >= 3
**Post:** Returns (p_value, is_significant) where is_significant = p_value < 0.05
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_confidence_interval(ic: float, n: int, confidence: float = 0.95) -> Tuple[float, float]`
**Pre:** -1 <= ic <= 1, n >= 4
**Post:** Returns (lower_bound, upper_bound) using Fisher's z-transformation
**Raises:** ValueError if ic outside valid range
**Retry:** No
**Side Effects:** None

### `calculate_rolling_ic(forecasts: pd.Series, returns: pd.Series, window: int = 60, method: str = "pearson") -> pd.Series`
**Pre:** len(forecasts) == len(returns) >= window
**Post:** Series of rolling IC values with DatetimeIndex
**Raises:** ValueError if lengths differ or insufficient data
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] IC calculation handles NaN values by removing them before computation
- [ ] Zero variance series returns IC of 0 with appropriate warning
- [ ] Both Pearson and Spearman methods produce valid results
- [ ] Confidence intervals use Fisher's z-transformation for normality
- [ ] Rolling IC maintains original index alignment
- [ ] IC decay properly handles forward return calculations
- [ ] Statistical significance test uses t-distribution with n-2 degrees of freedom
- [ ] All Decimal conversions preserve 4 decimal places precision

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-05 |
| **Auditor** | Claude Code (GAP Fix) |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. LOG-004 fixed: Added error logging with exc_info=True. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96 rules across 12 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance/IC calculations are statistically sound | ✅ OK - Uses scipy.stats for validation |
| TRD-005 | BASE_RULES | Validate price/return inputs | ✅ OK - Validates series lengths and NaN handling |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-002 | BASE_RULES | Modern syntax (X \| None) | ✅ OK - Uses modern X | None syntax |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ OK - Uses logger.error with exc_info=True |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear variable naming |
| PERF-002 | BASE_RULES | Use generators for large data | ✅ OK - Uses pandas vectorized operations |

---

## Dependencies
- **External:** numpy, pandas, scipy.stats, logging, decimal
- **Internal:** app.core.decimal_utils.to_decimal, app.analysis.fundamental_law.models.ICMetrics

---

## Required Tests
- **test_ic_calculator.py:**
  - Test IC calculation with Pearson correlation (success path)
  - Test IC calculation with Spearman correlation (success path)
  - Test IC with NaN values (edge case)
  - Test IC with zero variance series (edge case)
  - Test IC decay over multiple periods (success path)
  - Test statistical significance calculation (success path)
  - Test confidence interval calculation (success path)
  - Test rolling IC calculation (success path)
  - Test insufficient observations error case (error path)
  - Test mismatched series lengths error case (error path)

---

## Notes
Reference: Grinold, R., & Kahn, R. (2000). "Active Portfolio Management" Chapter 9.
