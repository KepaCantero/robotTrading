# chan_metrics.py

## Purpose
Implements Ernest Chan's performance metrics from "Algorithmic Trading" including Sharpe ratio with confidence intervals, drawdown analysis, Calmar ratio, return distribution analysis, and strategy comparison.

---

## Type Definitions / Data Classes

### SharpeRatioResult DataClass
```python
@dataclass
class SharpeRatioResult:
    sharpe_ratio: float                    # REQUIRED - Daily Sharpe ratio (not annualized)
    annualized_sharpe: float               # REQUIRED - Annualized Sharpe (daily * sqrt(252))
    daily_mean_return: float               # REQUIRED - Mean daily return
    daily_std_return: float                # REQUIRED - Std dev of daily returns
    skewness: float                        # REQUIRED - Third moment (asymmetry)
    excess_kurtosis: float                 # REQUIRED - Fourth moment - 3 (tail behavior)
    confidence_interval_low: float         # REQUIRED - CI lower bound (default 95%)
    confidence_interval_high: float        # REQUIRED - CI upper bound
    is_statistically_significant: bool     # REQUIRED - Sharpe > 2 * SE
```

**Validation Rules:**
- `annualized_sharpe` = `sharpe_ratio` * sqrt(252)
- `excess_kurtosis` can be negative (platykurtic) or positive (leptokurtic)
- `is_statistically_significant` = True if |sharpe| > 2 * SE

### DrawdownResult DataClass
```python
@dataclass
class DrawdownResult:
    max_drawdown: float                    # REQUIRED - Maximum drawdown (decimal, e.g., -0.15)
    max_drawdown_percentage: float         # REQUIRED - Max DD as percentage (e.g., -15.0)
    max_drawdown_duration_days: int        # REQUIRED - Duration of max DD in days
    average_drawdown: float                # REQUIRED - Average of all negative drawdowns
    recovery_factor: float                 # REQUIRED - (final - peak) / |max_dd|
    drawdown_distribution: Dict[str, float]  # REQUIRED - Percentiles (p5, p25, p50, p75, p95)
    drawdown_periods: List[Dict[str, Any]]  # REQUIRED - List of all DD periods
```

**Validation Rules:**
- `max_drawdown` should be <= 0 (negative or zero)
- `max_drawdown_percentage` = `max_drawdown` * 100
- `drawdown_distribution` keys: p5, p25, p50, p75, p95 (all negative values)
- `drawdown_periods` each has: start_idx, end_idx, drawdown, duration_days

### CalmarRatioResult DataClass
```python
@dataclass
class CalmarRatioResult:
    calmar_ratio: float                    # REQUIRED - Annual Return / Max Drawdown
    annual_return: float                   # REQUIRED - Annualized return
    max_drawdown: float                    # REQUIRED - Maximum drawdown (absolute value)
    interpretation: str                    # REQUIRED - Text assessment: "Excellent", "Good", "Fair", "Poor"
```

**Validation Rules:**
- `calmar_ratio` >= 0
- Interpretation thresholds: >3 (Excellent), >1 (Good), >0.5 (Fair), <=0.5 (Poor)

### ReturnDistributionMetrics DataClass
```python
@dataclass
class ReturnDistributionMetrics:
    mean_return: float                     # REQUIRED - Arithmetic mean
    median_return: float                   # REQUIRED - Median return
    std_return: float                      # REQUIRED - Standard deviation
    positive_return_pct: float             # REQUIRED - % of positive returns
    negative_return_pct: float             # REQUIRED - % of negative returns
    best_day_return: float                 # REQUIRED - Maximum daily return
    worst_day_return: float                # REQUIRED - Minimum daily return
    up_capture_ratio: float                # REQUIRED - Strategy return / Benchmark when benchmark > 0
    down_capture_ratio: float              # REQUIRED - Strategy return / Benchmark when benchmark < 0
    tail_ratio: float                      # REQUIRED - 95th percentile / |5th percentile|
```

**Validation Rules:**
- `positive_return_pct` + `negative_return_pct` may not equal 100% (zero returns excluded)
- `tail_ratio` >= 0 (absolute value of denominator)
- Capture ratios can be negative (strategy moves opposite to benchmark)

### StrategyComparisonResult DataClass
```python
@dataclass
class StrategyComparisonResult:
    strategy1_sharpe: float                # REQUIRED - Annualized Sharpe of strategy 1
    strategy2_sharpe: float                # REQUIRED - Annualized Sharpe of strategy 2
    sharpe_difference: float               # REQUIRED - strategy1 - strategy2
    is_significant: bool                   # REQUIRED - True if CIs don't overlap
    tracking_error: float                  # REQUIRED - Std of return differences (annualized)
    information_ratio: float               # REQUIRED - Mean excess return / std (annualized)
    recommended_strategy: str              # REQUIRED - "Strategy 1", "Strategy 2", or "No significant difference"
```

**Validation Rules:**
- `tracking_error` >= 0
- `sharpe_difference` can be negative (strategy 2 better)
- `is_significant` True when one strategy's CI doesn't overlap other's CI

---

## Function Signatures (Contracts)

### `ChanSharpeRatioCalculator.__init__(risk_free_rate: float = 0.02, trading_days: int = 252)`
**Pre:** risk_free_rate >= 0, trading_days > 0
**Post:** Calculator initialized with parameters
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanSharpeRatioCalculator.calculate_sharpe_ratio(returns: Union[pd.Series, np.ndarray, List[float]], confidence_level: float = 0.95) -> SharpeRatioResult`
**Pre:** returns has >= 2 non-NaN values; confidence_level in (0, 1)
**Post:** SharpeRatioResult with annualized Sharpe and confidence interval
**Raises:** Returns empty result on error
**Retry:** ❌ No
**Side Effects:** None (pure calculation)

### `ChanSharpeRatioCalculator._calculate_skewness(returns: np.ndarray) -> float`
**Pre:** returns has >= 3 values
**Post:** Skewness (third standardized moment)
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanSharpeRatioCalculator._calculate_excess_kurtosis(returns: np.ndarray) -> float`
**Pre:** returns has >= 4 values
**Post:** Excess kurtosis (fourth moment - 3)
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanSharpeRatioCalculator._calculate_sharpe_confidence_interval(sharpe: float, n_obs: int, confidence_level: float) -> Tuple[float, float]`
**Pre:** n_obs > 0, confidence_level in (0, 1)
**Post:** (CI_low, CI_high) using Chan's SE formula: sqrt((1 + 0.5*Sharpe²)/n)
**Raises:** Returns (sharpe*0.8, sharpe*1.2) on scipy import error
**Retry:** ❌ No
**Side Effects:** Imports scipy.stats

### `ChanSharpeRatioCalculator._test_sharpe_significance(sharpe: float, n_obs: int, confidence_level: float) -> bool`
**Pre:** n_obs > 0
**Post:** True if |sharpe| > 2 * SE (Chan's significance test)
**Raises:** Returns False on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanSharpeRatioCalculator._empty_sharpe_result() -> SharpeRatioResult`
**Pre:** None
**Post:** SharpeRatioResult with all zeros
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanDrawdownAnalyzer.__init__()`
**Pre:** None
**Post:** Analyzer initialized
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanDrawdownAnalyzer.analyze_drawdown(equity_curve: Union[pd.Series, np.ndarray, List[float]], dates: Optional[Union[pd.DatetimeIndex, List[datetime]]] = None) -> DrawdownResult`
**Pre:** equity_curve has >= 2 non-NaN values
**Post:** DrawdownResult with comprehensive DD analysis
**Raises:** Returns empty result on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanDrawdownAnalyzer._calculate_drawdown_distribution(drawdown: np.ndarray) -> Dict[str, float]`
**Pre:** drawdown is numpy array
**Post:** Dict with percentiles: p5, p25, p50, p75, p95 (negative DD only)
**Raises:** Returns zeros on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanDrawdownAnalyzer._identify_drawdown_periods(drawdown: np.ndarray, dates: Optional[pd.DatetimeIndex] = None) -> List[Dict[str, Any]]`
**Pre:** drawdown is numpy array
**Post:** List of DD periods with indices and durations
**Raises:** Returns empty list on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanDrawdownAnalyzer._empty_drawdown_result() -> DrawdownResult`
**Pre:** None
**Post:** DrawdownResult with zeros/empty collections
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanCalmarRatioCalculator.__init__(trading_days: int = 252)`
**Pre:** trading_days > 0
**Post:** Calculator initialized
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanCalmarRatioCalculator.calculate_calmar_ratio(returns: Union[pd.Series, np.ndarray, List[float]], equity_curve: Optional[Union[pd.Series, np.ndarray, List[float]]] = None) -> CalmarRatioResult`
**Pre:** returns has >= 2 non-NaN values
**Post:** CalmarRatioResult with ratio and interpretation
**Raises:** Returns error result on exception
**Retry:** ❌ No
**Side Effects:** None

### `ChanReturnDistributionAnalyzer.analyze_return_distribution(returns: Union[pd.Series, np.ndarray, List[float]], benchmark_returns: Optional[Union[pd.Series, np.ndarray, List[float]]] = None) -> ReturnDistributionMetrics`
**Pre:** returns has >= 2 non-NaN values
**Post:** ReturnDistributionMetrics with comprehensive analysis
**Raises:** Returns empty result on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanReturnDistributionAnalyzer._empty_distribution_result() -> ReturnDistributionMetrics`
**Pre:** None
**Post:** ReturnDistributionMetrics with all zeros
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `ChanStrategyComparator.compare_strategies(returns1: Union[pd.Series, np.ndarray, List[float]], returns2: Union[pd.Series, np.ndarray, List[float]], confidence_level: float = 0.95) -> StrategyComparisonResult`
**Pre:** Both returns have >= 2 non-NaN values; confidence_level in (0, 1)
**Post:** StrategyComparisonResult with comparison metrics
**Raises:** Returns error result on exception
**Retry:** ❌ No
**Side Effects:** None

### `ChanStrategyComparator._test_sharpe_difference(returns1: np.ndarray, returns2: np.ndarray, confidence_level: float) -> bool`
**Pre:** Both arrays non-empty
**Post:** True if confidence intervals don't overlap
**Raises:** Returns False on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanStrategyComparator._calculate_tracking_error(returns1: np.ndarray, returns2: np.ndarray) -> float`
**Pre:** Both arrays non-empty
**Post:** Annualized std of return differences
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None

### `ChanStrategyComparator._calculate_information_ratio(returns1: np.ndarray, returns2: np.ndarray) -> float`
**Pre:** Both arrays non-empty
**Post:** Annualized information ratio (mean excess / std excess)
**Raises:** Returns 0.0 on error (including zero division)
**Retry:** ❌ No
**Side Effects:** None

### `calculate_sharpe_ratio(returns: Union[pd.Series, np.ndarray, List[float]], risk_free_rate: float = 0.02) -> float`
**Pre:** returns has >= 2 non-NaN values
**Post:** Annualized Sharpe ratio
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None (convenience function)

### `calculate_max_drawdown(equity_curve: Union[pd.Series, np.ndarray, List[float]]) -> float`
**Pre:** equity_curve has >= 2 non-NaN values
**Post:** Maximum drawdown percentage
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None (convenience function)

### `calculate_calmar_ratio(returns: Union[pd.Series, np.ndarray, List[float]]) -> float`
**Pre:** returns has >= 2 non-NaN values
**Post:** Calmar ratio
**Raises:** Returns 0.0 on error
**Retry:** ❌ No
**Side Effects:** None (convenience function)

---

## Acceptance Criteria
- [ ] Sharpe ratio annualized by multiplying by sqrt(252) (Chan's TRADING_DAYS_PER_YEAR)
- [ ] Sharpe confidence interval uses Chan's SE formula: sqrt((1 + 0.5*Sharpe²)/n)
- [ ] Sharpe significant if |Sharpe| > 2 * SE (Chan's significance test)
- [ ] Drawdown calculated from rolling peak: (equity - peak) / peak
- [ ] Drawdown duration calculated as trough_date - peak_date (if dates provided)
- [ ] Recovery factor = (final_value - peak_value) / |max_drawdown|
- [ ] Calmar ratio = annual_return / abs(max_drawdown)
- [ ] Calmar interpretation: >3 (Excellent), >1 (Good), >0.5 (Fair), <=0.5 (Poor)
- [ ] Skewness = mean[((x - mean) / std)³]
- [ ] Excess kurtosis = mean[((x - mean) / std)⁴] - 3
- [ ] Up capture = mean(strategy_return) / mean(benchmark_return) when benchmark > 0
- [ ] Down capture = mean(strategy_return) / mean(benchmark_return) when benchmark < 0
- [ ] Tail ratio = percentile_95 / |percentile_5|
- [ ] Tracking error = std(returns1 - returns2) * sqrt(252)
- [ ] Information ratio = mean(excess) / std(excess) * sqrt(252)
- [ ] All error cases return valid result objects (not raise exceptions)
- [ ] Type hints present on all methods

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All functions have type hints |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Returns default results on errors |
| LOG-004 | BASE_RULES.md | Log exceptions | ⚠️ PARTIAL - Logs errors without exc_info |
| TRD-007 | BASE_RULES.md | Document TRADING_DAYS | ✅ OK - Hardcoded 252, documented as Chan's |
| PERF-001 | BASE_RULES.md | Vectorized operations | ✅ OK - Uses numpy vectorized ops |
| ARCH-004 | BASE_RULES.md | Functions < 20 lines | ❌ GAP - Many functions exceed 20 lines |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each class has single purpose |

**GAP Analysis:**

1. **ARCH-004 (Function Length):** Multiple functions exceed 20-line guideline:
   - `calculate_sharpe_ratio`: 62 lines
   - `analyze_drawdown`: 67 lines
   - `analyze_return_distribution`: 82 lines
   - `compare_strategies`: 49 lines
   - Impact: Low (functions are readable and well-structured)
   - Recommendation: Extract private helper methods for sub-calculations

2. **LOG-004 (Exception Logging):** Error logging uses `logger.error(f"Error: {e}")` without stack traces.
   - Impact: Low (errors are rare in pure calculation functions)
   - Recommendation: Add `exc_info=True` to better diagnose edge cases

---

## Dependencies
- **External:**
  - numpy (array operations, statistical calculations)
  - pandas (Series operations, time series alignment)
  - scipy.stats (norm.ppf for confidence intervals) - optional with fallback
  - logging (warning logging for insufficient data)
  - dataclasses (result objects)
  - datetime (timestamps for drawdown duration)
  - typing (Union, Optional, List, Dict, Tuple type hints)
- **Internal:** None (standalone metrics utilities)

---

## Required Tests
- **tests/unit/backtesting/test_chan_metrics.py:**
  - Test ChanSharpeRatioCalculator with normal returns
  - Test ChanSharpeRatioCalculator with zero std (returns 0.0)
  - Test ChanSharpeRatioCalculator annualization (multiply by sqrt(252))
  - Test ChanSharpeRatioCalculator confidence interval calculation
  - Test ChanSharpeRatioCalculator significance test (|Sharpe| > 2*SE)
  - Test ChanSharpeRatioCalculator skewness calculation
  - Test ChanSharpeRatioCalculator excess kurtosis calculation
  - Test ChanSharpeRatioCalculator with insufficient data (< 2 returns)
  - Test ChanDrawdownAnalyzer with rising equity (no drawdown)
  - Test ChanDrawdownAnalyzer with falling equity (drawdown)
  - Test ChanDrawdownAnalyzer drawdown duration calculation
  - Test ChanDrawdownAnalyzer recovery factor calculation
  - Test ChanDrawdownAnalyzer drawdown distribution percentiles
  - Test ChanDrawdownAnalyzer drawdown periods identification
  - Test ChanCalmarRatioCalculator with positive returns
  - Test ChanCalmarRatioCalculator interpretation thresholds
  - Test ChanCalmarRatioCalculator with zero max drawdown
  - Test ChanReturnDistributionAnalyzer capture ratios
  - Test ChanReturnDistributionAnalyzer tail ratio
  - Test ChanReturnDistributionAnalyzer with benchmark
  - Test ChanStrategyComparator with identical strategies
  - Test ChanStrategyComparator with different strategies
  - Test ChanStrategyComparator tracking error calculation
  - Test ChanStrategyComparator information ratio calculation
  - Test ChanStrategyComparator significance detection
  - Test convenience functions (calculate_sharpe_ratio, calculate_max_drawdown, calculate_calmar_ratio)
  - Test all error handling returns valid results (not exceptions)

---

## Notes
- Implements Ernest Chan's methodologies from "Algorithmic Trading: A Practitioner's Guide" (2013)
- Chapter 3: Backtesting; Chapter 8: Risk and Performance Metrics
- TRADING_DAYS_PER_YEAR = 252 (Chan's standard for US markets)
- DEFAULT_RISK_FREE_RATE = 0.02 (2% Treasury yield, Chan's typical assumption)
- Sharpe significance test: |Sharpe| > 2 * SE (Chan's simplified approach)
- Calmar interpretation thresholds from Chan's experience: >3 excellent, >1 good, >0.5 fair
- All error paths return default/empty results instead of raising (fail-safe design)
- scipy import optional with fallback for confidence interval calculation
- All calculations use numpy for vectorized performance
- Handles NaN values by filtering them out before calculations
- Zero division handled by returning 0.0 or safe defaults
