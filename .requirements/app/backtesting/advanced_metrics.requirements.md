# advanced_metrics.py

## Purpose
Advanced financial metrics calculator for backtesting - Calmar ratio, Omega ratio, Ulcer index, annualized volatility, recovery factor, profit factor, skewness, kurtosis, VaR, CVaR, Sortino, tail ratio, SQN.

---

## Type Definitions / Data Classes

None - this module uses a calculator class with methods, no custom dataclasses.

---

## Function Signatures (Contracts)

### `AdvancedMetricsCalculator.__init__(risk_free_rate: Decimal = Decimal("0.02"), confidence_level: float = 0.95) -> None`
**Pre:** `risk_free_rate` in [0, 1]; `confidence_level` in (0, 1)
**Post:** Calculator initialized with provided parameters
**Raises:** None
**Retry:** No
**Side Effects:** None (initialization only)

### `AdvancedMetricsCalculator.calculate_calmar_ratio(cagr: Decimal, max_drawdown: Decimal) -> Optional[Decimal]`
**Pre:** `cagr` is not None; `max_drawdown` is not zero
**Post:** Returns `CAGR / |max_drawdown|` or None if calculation not possible
**Raises:** Returns None on error (division by zero, invalid inputs)
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_omega_ratio(returns: List[Decimal], threshold: float = 0.0) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements
**Post:** Returns `E[max(R - threshold, 0)] / E[max(threshold - R, 0)]` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_ulcer_index(equity_curve: List[Decimal], rolling_window: int = 14) -> Optional[Decimal]`
**Pre:** `equity_curve` has >= 2 elements
**Post:** Returns `sqrt(mean(max(0, (Peak - Price) / Peak)^2))` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_annualized_volatility(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements
**Post:** Returns `std(returns) * sqrt(252)` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_recovery_factor(total_pnl: Decimal, max_drawdown: Decimal) -> Optional[Decimal]`
**Pre:** `max_drawdown` is not zero
**Post:** Returns `total_pnl / |max_drawdown|` or None
**Raises:** Returns None on division by zero or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_profit_factor(gross_profit: Decimal, gross_loss: Decimal) -> Optional[Decimal]`
**Pre:** `gross_loss` is not None
**Post:** Returns `gross_profit / |gross_loss|` or 999 if no losses
**Raises:** Returns None on error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_skewness(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** `returns` has >= 3 elements
**Post:** Returns skewness using `scipy.stats.skew` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_kurtosis(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** `returns` has >= 4 elements
**Post:** Returns excess kurtosis using `scipy.stats.kurtosis` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_var(returns: List[Decimal], confidence: Optional[float] = None) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements; `confidence` in (0, 1) if provided
**Post:** Returns percentile at `(1 - confidence) * 100` or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_cvar(returns: List[Decimal], confidence: Optional[float] = None) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements; `confidence` in (0, 1) if provided
**Post:** Returns mean of returns <= VaR threshold (expected shortfall) or None
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_sortino_modified(returns: List[Decimal], target_return: float = 0.0) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements
**Post:** Returns `(mean_return - target) / downside_deviation` annualized or None
**Raises:** Returns None on error or zero downside deviation
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_tail_ratio(returns: List[Decimal]) -> Optional[Decimal]`
**Pre:** `returns` has >= 20 elements
**Post:** Returns `percentile_95 / |percentile_5|` or 999 if no extreme losses
**Raises:** Returns None on insufficient data or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_sqn(returns: List[Decimal], number_of_trades: Optional[int] = None) -> Optional[Decimal]`
**Pre:** `returns` has >= 2 elements
**Post:** Returns `(mean / stddev) * sqrt(N)` or None
**Raises:** Returns None on zero standard deviation or error
**Retry:** No
**Side Effects:** None

### `AdvancedMetricsCalculator.calculate_all_advanced_metrics(returns: List[Decimal], equity_curve: List[Decimal], cagr: Decimal, max_drawdown: Decimal, total_pnl: Decimal, gross_profit: Decimal, gross_loss: Decimal) -> dict`
**Pre:** All inputs are valid; `returns` and `equity_curve` have sufficient data
**Post:** Returns dict with all 11 advanced metrics
**Raises:** Returns dict with None values for failed metrics
**Retry:** No
**Side Effects:** None (calls all calculator methods)

---

## Acceptance Criteria
- [ ] All methods return `Optional[Decimal]` (None on error)
- [ ] All methods handle edge cases (empty lists, division by zero)
- [ ] Annualization uses `sqrt(252)` for daily data
- [ ] VaR uses historical method (percentile)
- [ ] CVaR is mean of tail returns (worse than VaR)
- [ ] Omega ratio handles zero loss case (returns 999)
- [ ] Ulcer index uses rolling maximum (peak calculation)
- [ ] Skewness and kurtosis use scipy.stats
- [ ] Tail ratio requires >= 20 data points
- [ ] SQN (System Quality Number) formula: `(mean / std) * sqrt(N)`
- [ ] All calculations logged on error
- [ ] Invalid exception types caught (FileNotFoundError, etc.)

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-007 | BASE_RULES.md | Annualization uses TRADING_DAYS = 252 | ✅ OK - Hardcoded sqrt(252) |
| RSK-001 | BASE_RULES.md | VaR calculation implemented | ✅ OK - calculate_var method |
| RSK-002 | BASE_RULES.md | Expected Shortfall (CVaR) implemented | ✅ OK - calculate_cvar method |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - try/except with logging |
| LOG-004 | BASE_RULES.md | Log all exceptions | ✅ OK - logger.error in all except blocks |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have hints |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each method calculates one metric |
| ARCH-004 | BASE_RULES.md | Small functions | ✅ OK - Most methods < 20 lines |

**NOTE:** All 96 BASE_RULES apply. Critical for risk metrics:
- **TRD-007:** Consistent annualization enables cross-strategy comparison
- **RSK-001/RSK-002:** VaR/CVaR are regulatory requirements for trading
- **CC-006:** Explicit error handling prevents silent metric failures

---

## Dependencies
- **External:** `numpy`, `scipy.stats`, `decimal` (Decimal), `logging`, `typing` (List, Optional)
- **Internal:** None (standalone metrics module)

---

## Required Tests
- **tests/backtesting/test_advanced_metrics.py:**
  - Test Calmar ratio with valid/invalid inputs
  - Test Omega ratio with various thresholds
  - Test Omega ratio with zero losses (returns 999)
  - Test Ulcer index calculation
  - Test annualized volatility (verify sqrt(252) factor)
  - Test recovery factor
  - Test profit factor with zero losses
  - Test skewness using scipy
  - Test kurtosis (excess kurtosis, not raw)
  - Test VaR at different confidence levels
  - Test CVaR as mean of tail returns
  - Test modified Sortino with target return
  - Test tail ratio (95th/5th percentile)
  - Test SQN calculation with trade count override
  - Test calculate_all_advanced_metrics returns dict with all 11 metrics
  - Test all methods return None on invalid inputs
  - Test division by zero handling

---

## Notes
- Module purpose: PHASE 4 MODULE 7 of backtesting system
- All metrics use Decimal for precision (financial calculations)
- VaR uses historical method (non-parametric, no distribution assumption)
- CVaR is Expected Shortfall (more conservative than VaR)
- Skewness: positive = right tail (gains), negative = left tail (losses)
- Kurtosis: excess kurtosis (0 = normal, positive = fat tails)
- SQN interpretation: >2 excellent, 1.5-2 good, 1-1.5 acceptable, <1 poor
- Tail ratio measures asymmetry: >1 means better upside than downside
- All methods are pure functions (no side effects)
- Error handling: catch specific exceptions, return None, log error
