# advanced_metrics.py

## Purpose
Advanced Financial Metrics Calculator (PHASE 4 MODULE 7) - calculates sophisticated financial metrics including Calmar Ratio, Omega Ratio, Ulcer Index, VaR, CVaR, skewness, and kurtosis.

---

## Type Definitions / Data Classes

### AdvancedMetricsCalculator Class
```python
class AdvancedMetricsCalculator:
    """Calculator for advanced financial metrics."""

    risk_free_rate: float                    # REQUIRED - Annual risk-free rate (float for numpy/scipy)
    confidence_level: float                  # REQUIRED - Confidence level for VaR/CVaR
```

**Note:** Uses float internally for numpy/scipy compatibility, converts from Decimal

---

## Function Signatures (Contracts)

### `__init__(self, risk_free_rate: Decimal = Decimal("0.02"), confidence_level: float = 0.95) -> None`
**Pre:** None
**Post:** Calculator initialized
**Raises:** No
**Retry:** No
**Side Effects:** None

**Defaults:** 2% risk-free rate, 95% confidence level

### `calculate_calmar_ratio(self, cagr: Decimal, max_drawdown: Decimal) -> Optional[Decimal]`
**Pre:** cagr not None, max_drawdown not None, max_drawdown != 0
**Post:** Returns Calmar Ratio or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** CAGR / |Max Drawdown|
- Values > 1.0: Good
- Values > 3.0: Excellent
- Penalizes large drawdowns

**Returns None if:** cagr is None, max_drawdown is None, or max_drawdown == 0

### `calculate_omega_ratio(self, returns: List[Decimal], threshold: float = 0.0) -> Optional[Decimal]`
**Pre:** returns has >= 2 values
**Post:** Returns Omega Ratio or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
- Measures probability-weighted ratio of gains to losses
- Values > 1.0: More upside than downside
- More sophisticated than Sharpe ratio

**Special Cases:**
- No losses (avg_loss == 0) with gains: Returns 999999 (infinite ratio)
- No gains, no losses: Returns 1
- Empty or single value: Returns None

### `calculate_ulcer_index(self, equity_curve: List[Decimal], rolling_window: int = 14) -> Optional[Decimal]`
**Pre:** equity_curve has >= 2 values
**Post:** Returns Ulcer Index or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** sqrt(mean(max(0, (Peak - Price) / Peak)^2))
- Penalizes duration and magnitude of underwater periods
- Only looks at drawdowns, not recovery
- More sensitive to deep drawdowns than max drawdown alone

**Calculation:**
1. Calculate rolling maximum (peak)
2. Calculate drawdown percentage from peak
3. Square all drawdowns
4. Take mean
5. Take square root

### `calculate_sortino_ratio(self, returns: List[Decimal], target_return: float = 0.0) -> Optional[Decimal]`
**Pre:** returns has >= 2 values
**Post:** Returns Sortino Ratio or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** (mean_return - target) / downside_deviation
- Downside deviation: Std dev of returns below target
- Penalizes only downside volatility
- Better than Sharpe for asymmetric returns

### `calculate_information_ratio(self, returns: List[Decimal], benchmark_returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns and benchmark_returns same length, >= 2 values
**Post:** Returns Information Ratio or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** (mean_return - mean_benchmark) / tracking_error
- Measures excess return per unit of tracking error
- Higher is better (positive alpha)

### `calculate_skewness(self, returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns has >= 3 values
**Post:** Returns skewness or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Interpretation:**
- Positive: Right tail longer (more upside)
- Negative: Left tail longer (more downside)
- Normal distribution: ~0

### `calculate_kurtosis(self, returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns has >= 4 values
**Post:** Returns kurtosis or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Interpretation:**
- > 3: Fat tails (more extreme outcomes)
- < 3: Thin tails (fewer extreme outcomes)
- Normal distribution: 3.0

### `calculate_var(self, returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns has >= 2 values
**Post:** Returns Value at Risk or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** Historical VaR at confidence_level
- Returns the loss at the given percentile
- Default: 5% worst case (95% confidence)

### `calculate_cvar(self, returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** returns has >= 2 values
**Post:** Returns Conditional VaR (Expected Shortfall) or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** Average of returns beyond VaR
- Also called Expected Shortfall
- More conservative than VaR alone
- Captures tail risk better

### `calculate_recovery_factor(self, total_profit: Decimal, max_drawdown: Decimal) -> Optional[Decimal]`
**Pre:** total_profit and max_drawdown not None
**Post:** Returns Recovery Factor or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** Total Profit / |Max Drawdown|
- Higher is better
- Measures profit relative to drawdown

### `calculate_tail_ratio(self, returns: List[Decimal], tail_percentile: float = 0.05) -> Optional[Decimal]`
**Pre:** returns has >= 10 values
**Post:** Returns Tail Ratio or None
**Raises:** No (catches and logs exceptions)
**Retry:** No
**Side Effects:** None

**Formula:** (Percentile 95 - Mean) / (Mean - Percentile 5)
- Measures right tail vs left tail
- Higher is better (more upside than downside)

---

## Acceptance Criteria
- [ ] All metrics use Decimal for parameters
- [ ] All metrics return Decimal or None
- [ ] All metrics handle exceptions gracefully (return None)
- [ ] All metrics log errors
- [ ] Conversions to float for numpy/scipy compatibility
- [ ] Calmar ratio handles zero drawdown (returns None)
- [ ] Omega ratio handles no losses (returns large number)
- [ ] Ulcer index calculates rolling peaks
- [ ] VaR uses configurable confidence level
- [ ] CVaR averages tail losses
- [ ] Skewness uses scipy.stats.skew
- [ ] Kurtosis uses scipy.stats.kurtosis (excess=False)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Decimal Precision | CRITICAL_RULES.md | Use Decimal for parameters/returns | ✅ OK |
| Numpy/Scipy Integration | BASE_RULES.md | Convert to float for calc | ✅ OK |
| Error Handling | BASE_RULES.md | Catch exceptions, return None | ✅ OK |
| Logging | BASE_RULES.md | Log all errors | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation (length checks) | ✅ OK |
| Edge Cases | BASE_RULES.md | Handle None, empty, zero | ✅ OK |

---

## Dependencies
- **External:** logging, decimal, typing, numpy, scipy
- **Internal:** None (pure calculator)

---

## Required Tests
- **test_advanced_metrics.py:**
  - Test calculate_calmar_ratio with valid inputs
  - Test calculate_calmar_ratio with zero drawdown returns None
  - Test calculate_omega_ratio with returns
  - Test calculate_omega_ratio with no losses returns large number
  - Test calculate_omega_ratio with empty returns returns None
  - Test calculate_ulcer_index with equity curve
  - Test calculate_ulcer_index calculates rolling peaks
  - Test calculate_sortino_ratio with returns
  - Test calculate_information_ratio with benchmark
  - Test calculate_skewness interpretation
  - Test calculate_kurtosis interpretation
  - Test calculate_var at 95% confidence
  - Test calculate_cvar averages tail losses
  - Test calculate_recovery_factor
  - Test calculate_tail_ratio
  - Test all methods return None on exceptions
  - Test all methods log errors

---

## Notes
- CRITICAL: This is PHASE 4 MODULE 7
- Advanced financial metrics for performance analysis
- Uses numpy/scipy for statistical operations
- Converts Decimal to float for calculations (back to Decimal for results)
- All methods handle exceptions gracefully (return None)
- All edge cases handled (empty, None, zero, etc.)
- Comprehensive risk metrics (VaR, CVaR, Ulcer, etc.)
- Risk-adjusted return metrics (Calmar, Sortino, Omega, Information)
- Distribution metrics (skewness, kurtosis)
