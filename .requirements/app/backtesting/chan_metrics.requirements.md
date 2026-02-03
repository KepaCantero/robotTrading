# chan_metrics.py

## Purpose
Implement Ernest Chan's performance metrics from "Algorithmic Trading: A Practitioner's Guide" including Sharpe ratio optimization, maximum drawdown analysis, Calmar ratio calculation, return distribution analysis, and strategy comparison metrics.

---

## Type Definitions / Data Classes

### SharpeRatioResult (dataclass)
```python
@dataclass
class SharpeRatioResult:
    sharpe_ratio: float                    # Daily Sharpe ratio
    annualized_sharpe: float               # Annualized Sharpe (daily * sqrt(252))
    daily_mean_return: float               # Mean daily return
    daily_std_return: float                # Std dev of daily returns
    skewness: float                        # Return distribution skewness
    excess_kurtosis: float                 # Excess kurtosis (kurtosis - 3)
    confidence_interval_low: float         # CI lower bound
    confidence_interval_high: float        # CI upper bound
    is_statistically_significant: bool     # True if Sharpe > 2*SE
```

### DrawdownResult (dataclass)
```python
@dataclass
class DrawdownResult:
    max_drawdown: float                    # Maximum drawdown (negative)
    max_drawdown_percentage: float         # Maximum drawdown %
    max_drawdown_duration_days: int        # Duration of max DD in days
    average_drawdown: float                # Average of all drawdowns
    recovery_factor: float                 # Final value / max drawdown
    drawdown_distribution: Dict[str, float] # Percentiles (p5, p25, p50, p75, p95)
    drawdown_periods: List[Dict[str, Any]]  # Individual DD periods
```

### CalmarRatioResult (dataclass)
```python
@dataclass
class CalmarRatioResult:
    calmar_ratio: float                    # Annual return / max drawdown
    annual_return: float                   # Annualized return
    max_drawdown: float                    # Maximum drawdown
    interpretation: str                    # Text interpretation
```

### ReturnDistributionMetrics (dataclass)
```python
@dataclass
class ReturnDistributionMetrics:
    mean_return: float                     # Mean return
    median_return: float                   # Median return
    std_return: float                      # Standard deviation
    positive_return_pct: float             # % of positive returns
    negative_return_pct: float             # % of negative returns
    best_day_return: float                 # Best single day return
    worst_day_return: float                # Worst single day return
    up_capture_ratio: float                # Strategy vs benchmark in up markets
    down_capture_ratio: float              # Strategy vs benchmark in down markets
    tail_ratio: float                      # P95 / |P5| tail ratio
```

### StrategyComparisonResult (dataclass)
```python
@dataclass
class StrategyComparisonResult:
    strategy1_sharpe: float
    strategy2_sharpe: float
    sharpe_difference: float
    is_significant: bool                   # True if CIs don't overlap
    tracking_error: float                  # Annualized tracking error
    information_ratio: float               # Annualized information ratio
    recommended_strategy: str
```

---

## Function Signatures (Contracts)

### `ChanSharpeRatioCalculator.__init__(risk_free_rate: float = 0.02, trading_days: int = 252)`
**Pre:** risk_free_rate >= 0, trading_days > 0
**Post:** Calculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_sharpe_ratio(returns: Union[pd.Series, np.ndarray, List[float]], confidence_level: float = 0.95) -> SharpeRatioResult`
**Pre:** returns has at least 2 values
**Post:** Returns SharpeRatioResult with comprehensive statistics
**Raises:** None (returns empty result on error)
**Retry:** No
**Side Effects:** None

### `ChanDrawdownAnalyzer.__init__()`
**Pre:** None
**Post:** Analyzer initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `analyze_drawdown(equity_curve: Union[pd.Series, np.ndarray, List[float]], dates: Optional[Union[pd.DatetimeIndex, List[datetime]]] = None) -> DrawdownResult`
**Pre:** equity_curve has at least 2 values
**Post:** Returns DrawdownResult with comprehensive analysis
**Raises:** None (returns empty result on error)
**Retry:** No
**Side Effects:** None

### `ChanCalmarRatioCalculator.__init__(trading_days: int = 252)`
**Pre:** trading_days > 0
**Post:** Calculator initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_calmar_ratio(returns: Union[pd.Series, np.ndarray, List[float]], equity_curve: Optional[Union[pd.Series, np.ndarray, List[float]]] = None) -> CalmarRatioResult`
**Pre:** returns has at least 2 values
**Post:** Returns CalmarRatioResult
**Raises:** None (returns result with error message on exception)
**Retry:** No
**Side Effects:** None

### `ChanReturnDistributionAnalyzer.__init__()`
**Pre:** None
**Post:** Analyzer initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `analyze_return_distribution(returns: Union[pd.Series, np.ndarray, List[float]], benchmark_returns: Optional[Union[pd.Series, np.ndarray, List[float]]] = None) -> ReturnDistributionMetrics`
**Pre:** returns has at least 2 values
**Post:** Returns ReturnDistributionMetrics
**Raises:** None (returns empty result on error)
**Retry:** No
**Side Effects:** None

### `ChanStrategyComparator.__init__()`
**Pre:** None
**Post:** Comparator initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `compare_strategies(returns1: Union[pd.Series, np.ndarray, List[float]], returns2: Union[pd.Series, np.ndarray, List[float]], confidence_level: float = 0.95) -> StrategyComparisonResult`
**Pre:** Both return series have at least 2 values
**Post:** Returns StrategyComparisonResult
**Raises:** None (returns error result on exception)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Sharpe ratio uses daily returns and annualizes with sqrt(252)
- [ ] Sharpe ratio subtracts risk-free rate
- [ ] Confidence intervals calculated using standard error approach
- [ ] Statistical significance test (Sharpe > 2*SE)
- [ ] Skewness and excess kurtosis calculated
- [ ] Maximum drawdown calculated from rolling peak
- [ ] Drawdown distribution percentiles (p5, p25, p50, p75, p95)
- [ ] Recovery factor calculated (final value / max DD)
- [ ] Calmar ratio = annual return / max drawdown
- [ ] Calmar interpretation: >3 excellent, >1 good, >0.5 fair, <0.5 poor
- [ ] Return distribution: mean, median, std, positive/negative %
- [ ] Up/down capture ratios vs benchmark
- [ ] Tail ratio = P95 / |P5|
- [ ] Strategy comparison: tracking error and information ratio
- [ ] Recommendation based on significant Sharpe difference

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

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some functions > 20 lines |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Each class one metric |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| MATH-003 | Custom | Chan's Sharpe formula: (mean - rf) / std | ✅ OK |
| MATH-004 | Custom | Annualize with sqrt(252) | ✅ OK |
| MATH-005 | Custom | Standard error: sqrt((1 + 0.5*Sharpe^2) / n) | ✅ OK |

**Ernest Chan Methodologies:**
- ✅ Daily returns for Sharpe calculation
- ✅ Annualization with sqrt(252)
- ✅ Risk-free rate subtraction
- ✅ Confidence intervals using SE approach
- ✅ Maximum drawdown from rolling peak
- ✅ Calmar ratio for risk-adjusted return
- ✅ Skewness and kurtosis for non-normality
- ✅ Tracking error for strategy comparison
- ✅ Information ratio for excess return

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, dataclasses, datetime, typing, numpy, pandas, scipy (optional, for z-scores)
- **Internal:** None (standalone metrics module)

---

## Required Tests
- **test_chan_metrics.py:**
  - Success: Sharpe ratio calculation (daily returns)
  - Success: Sharpe ratio annualization (sqrt(252))
  - Success: Sharpe ratio with risk-free rate subtraction
  - Success: Confidence interval calculation
  - Success: Statistical significance test (Sharpe > 2*SE)
  - Success: Skewness calculation (third moment)
  - Success: Excess kurtosis (fourth moment - 3)
  - Success: Maximum drawdown from rolling peak
  - Success: Drawdown duration calculation
  - Success: Drawdown distribution percentiles
  - Success: Recovery factor calculation
  - Success: Calmar ratio (annual return / max DD)
  - Success: Calmar interpretation thresholds
  - Success: Return distribution (mean, median, std)
  - Success: Up/down capture ratios
  - Success: Tail ratio calculation
  - Success: Strategy comparison (tracking error)
  - Success: Information ratio calculation
  - Edge: Empty returns (returns zero result)
  - Edge: Single data point (returns zero result)
  - Edge: Zero volatility (Sharpe = 0)
  - Edge: All positive returns (no drawdown)

---

## Notes
- Implements Ernest Chan's methodologies from "Algorithmic Trading" (2013)
- Default risk-free rate: 2% (Treasury yield)
- Trading days per year: 252
- Sharpe significance threshold: > 2 * standard error
- Calmar interpretation: >3 excellent, >1 good, >0.5 fair, <0.5 poor
- Convenience functions: calculate_sharpe_ratio, calculate_max_drawdown, calculate_calmar_ratio
