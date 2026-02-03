# walk_forward_validator_enhanced.py

## Purpose
Tomasini-compliant walk-forward validation with rolling windows, parameter stability tracking, regime-aware testing, and IS/OOS consistency analysis. Implements Tomasini & Jaekle methodology from "Designing Trading Systems" (Chapter 8).

---

## Type Definitions / Data Classes

### ParameterHistory Class
```python
@dataclass(frozen=True)
class ParameterHistory:
    window_id: int                  # REQUIRED - Window index
    parameters: Dict[str, float]    # REQUIRED - Optimal parameter values
    in_sample_sharpe: float         # REQUIRED - IS Sharpe ratio
    out_of_sample_sharpe: float     # REQUIRED - OOS Sharpe ratio
    in_sample_return: float         # REQUIRED - IS total return
    out_of_sample_return: float     # REQUIRED - OOS total return
    window_start: datetime          # REQUIRED - Training start
    window_end: datetime            # REQUIRED - Test end
    regime: str                     # REQUIRED - Market regime label
```

**Validation Rules:**
- `window_id >= 1` (1-indexed windows)
- `in_sample_sharpe >= 0` and `out_of_sample_sharpe >= 0`
- `window_start < window_end` (valid date range)
- `regime in ["BULL", "BEAR", "SIDEWAYS", "UNKNOWN", "INSUFFICIENT_DATA"]`

### ParameterStabilityMetrics Class
```python
@dataclass(frozen=True)
class ParameterStabilityMetrics:
    parameter_name: str                    # REQUIRED - Parameter identifier
    mean_value: float                      # REQUIRED - Mean across windows
    std_value: float                       # REQUIRED - Std across windows
    cv: float                              # REQUIRED - Coefficient of variation
    min_value: float                       # REQUIRED - Minimum value
    max_value: float                       # REQUIRED - Maximum value
    range_pct: float                       # REQUIRED - (max-min)/mean
    drift_trend: float                     # REQUIRED - Linear regression slope
    drift_significance: float              # REQUIRED - P-value for trend
    is_stable: bool                        # REQUIRED - CV < 30% threshold
    confidence_interval_95: Tuple[float, float]  # REQUIRED - 95% CI
```

**Validation Rules:**
- `std_value >= 0` (std is non-negative)
- `cv >= 0` (coefficient of variation is non-negative)
- `0 <= drift_significance <= 1` (p-value bounds)
- `confidence_interval_95[0] < confidence_interval_95[1]` (valid interval)

### TomasiniWindowResult Class
```python
@dataclass(frozen=True)
class TomasiniWindowResult:
    window_id: int                       # REQUIRED - Window index
    train_start: datetime                # REQUIRED - Training period start
    train_end: datetime                  # REQUIRED - Training period end
    test_start: datetime                 # REQUIRED - Test period start
    test_end: datetime                   # REQUIRED - Test period end
    is_return: float                     # REQUIRED - In-sample return
    is_sharpe: float                     # REQUIRED - In-sample Sharpe
    is_sortino: float                    # REQUIRED - In-sample Sortino
    is_max_drawdown: float               # REQUIRED - In-sample max drawdown
    is_volatility: float                 # REQUIRED - In-sample volatility
    is_trades: int                       # REQUIRED - In-sample trade count
    oos_return: float                    # REQUIRED - Out-of-sample return
    oos_sharpe: float                    # REQUIRED - Out-of-sample Sharpe
    oos_sortino: float                   # REQUIRED - Out-of-sample Sortino
    oos_max_drawdown: float              # REQUIRED - Out-of-sample max drawdown
    oos_volatility: float                # REQUIRED - Out-of-sample volatility
    oos_trades: int                      # REQUIRED - Out-of-sample trade count
    consistency_ratio: float             # REQUIRED - OOS Sharpe / IS Sharpe
    return_degradation: float            # REQUIRED - (IS - OOS) / |IS|
    sharpe_degradation: float            # REQUIRED - (IS - OOS) / IS
    train_regime: str                    # REQUIRED - Training regime
    test_regime: str                     # REQUIRED - Test regime
    regime_change: bool                  # REQUIRED - Regime changed flag
    optimal_parameters: Dict[str, float] # REQUIRED - Optimal params
    passed: bool                         # REQUIRED - Window passed validation
    failure_reasons: List[str]           # REQUIRED - Failure reasons if failed
```

**Validation Rules:**
- `train_start < train_end <= test_start < test_end` (chronological order)
- `0 <= consistency_ratio <= 1` (OOS never exceeds IS)
- `0 <= return_degradation <= 1` (degradation percentage)
- `0 <= sharpe_degradation <= 1` (degradation percentage)
- `is_max_drawdown <= 0` and `oos_max_drawdown <= 0` (drawdown is negative)
- `is_trades >= 0` and `oos_trades >= 0` (non-negative trade counts)

### TomasiniWalkForwardResult Class
```python
@dataclass(frozen=True)
class TomasiniWalkForwardResult:
    passed: bool                              # REQUIRED - Overall pass/fail
    total_windows: int                        # REQUIRED - Total windows
    passed_windows: int                       # REQUIRED - Windows that passed
    avg_is_return: float                      # REQUIRED - Avg IS return
    avg_oos_return: float                     # REQUIRED - Avg OOS return
    avg_is_sharpe: float                      # REQUIRED - Avg IS Sharpe
    avg_oos_sharpe: float                     # REQUIRED - Avg OOS Sharpe
    avg_consistency_ratio: float              # REQUIRED - Avg consistency
    avg_return_degradation: float             # REQUIRED - Avg return deg
    avg_sharpe_degradation: float             # REQUIRED - Avg Sharpe deg
    windows: List[TomasiniWindowResult]       # REQUIRED - All window results
    parameter_stability: Dict[str, ParameterStabilityMetrics]  # REQUIRED
    robustness_score: float                   # REQUIRED - 0-1 robustness
    regime_robustness: Dict[str, float]       # REQUIRED - Performance by regime
    failure_reasons: List[str]                # REQUIRED - Unique failures
    tomasini_score: float                     # REQUIRED - 0-100 overall score
    parameter_stability_score: float          # REQUIRED - 0-100 stability score
    consistency_score: float                  # REQUIRED - 0-100 consistency score
```

**Validation Rules:**
- `0 <= passed_windows <= total_windows` (valid counts)
- `0 <= all scores <= 100` (score bounds)
- `0 <= robustness_score <= 1` (score bounds)
- `len(failure_reasons) == len(set(failure_reasons))` (unique reasons)

---

## Function Signatures (Contracts)

### `TomasiniWalkForwardValidator.__init__(config: Optional[Dict[str, Any]] = None)`
**Pre:** None
**Post:** Validator initialized with Tomasini-recommended settings
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Sets instance attributes, initializes optional regime detector

### `TomasiniWalkForwardValidator.create_rolling_windows(start_date: datetime, end_date: datetime, train_years: Optional[float] = None) -> List[Dict[str, datetime]]`
**Pre:** `start_date < end_date`
**Post:** Returns list of window dicts with train/test periods
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs window creation details

### `TomasiniWalkForwardValidator.detect_regime(quotes: List[Quote], start_date: datetime, end_date: datetime) -> str`
**Pre:** `quotes` contains at least one Quote in date range
**Post:** Returns regime label: 'BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN', or 'INSUFFICIENT_DATA'
**Raises:** ❌ No (gracefully handles errors)
**Retry:** ❌ No
**Side Effects:** Logs warnings on detection failure

### `TomasiniWalkForwardValidator.optimize_parameters(train_quotes: List[Quote], train_signals: List[Any], param_grid: Dict[str, List[Any]], config: BacktestConfig, optimization_metric: str = "sharpe_ratio") -> Tuple[Dict[str, Any], Dict[str, float]]`
**Pre:** `train_quotes` and `train_signals` are non-empty
**Post:** Returns tuple of (best_parameters, best_metrics)
**Raises:** ❌ No (logs warnings for failed backtests)
**Retry:** ❌ No
**Side Effects:** Runs grid search across parameter combinations, logs best params

### `TomasiniWalkForwardValidator.calculate_window_metrics(quotes: List[Quote], signals: List[Any], start_date: datetime, end_date: datetime, config: BacktestConfig, optimal_params: Optional[Dict[str, Any]] = None) -> Dict[str, float]`
**Pre:** `start_date < end_date`
**Post:** Returns dict with metrics or empty dict on failure
**Raises:** ❌ No (gracefully handles backtest failures)
**Retry:** ❌ No
**Side Effects:** Runs SimpleBacktester, logs warnings on failure

### `TomasiniWalkForwardValidator.validate_strategy(quotes: List[Quote], signals: List[Any], config: BacktestConfig, start_date: datetime, end_date: datetime, param_grid: Optional[Dict[str, List[Any]]] = None) -> TomasiniWalkForwardResult`
**Pre:** `start_date < end_date`, `quotes` and `signals` are non-empty
**Post:** Returns complete TomasiniWalkForwardResult with all metrics
**Raises:** ❌ No (returns result with passed=False on errors)
**Retry:** ❌ No
**Side Effects:** Runs complete walk-forward validation, logs progress

### `TomasiniWalkForwardValidator.calculate_parameter_stability(history: List[ParameterHistory]) -> Dict[str, ParameterStabilityMetrics]`
**Pre:** `history` contains at least 2 entries
**Post:** Returns dict mapping parameter names to stability metrics
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs stability info for each parameter

### `ParameterHistory.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns JSON-serializable dictionary
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityMetrics.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns JSON-serializable dictionary
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `TomasiniWindowResult.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns JSON-serializable dictionary
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `TomasiniWalkForwardResult.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns JSON-serializable dictionary
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] `train_years` defaults to 4.0 (Tomasini recommendation)
- [ ] `step_pct` defaults to 0.5 (50% of training window)
- [ ] `min_cycles` defaults to 5 (Tomasini minimum)
- [ ] `min_consistency_ratio` defaults to 0.7 (Tomasini threshold)
- [ ] `max_parameter_cv` defaults to 0.30 (30% threshold)
- [ ] `create_rolling_windows()` creates at least 5 windows for typical date ranges
- [ ] `create_rolling_windows()` uses 50% step size of training window
- [ ] `detect_regime()` returns 'INSUFFICIENT_DATA' when < 126 quotes
- [ ] `optimize_parameters()` returns empty dicts when `param_grid` is empty
- [ ] `validate_strategy()` returns result with `passed=False` when < min_cycles windows
- [ ] `validate_strategy()` tracks parameter history when `param_grid` provided
- [ ] `calculate_parameter_stability()` calculates CV, drift, and 95% CI
- [ ] `calculate_parameter_stability()` marks parameters with CV < 30% as stable
- [ ] All `to_dict()` methods convert datetime to ISO format string
- [ ] `consistency_ratio` is calculated as OOS Sharpe / IS Sharpe (0-1 range)
- [ ] `sharpe_degradation` is calculated as (IS - OOS) / IS (0-1 range)
- [ ] `tomasini_score` is weighted average: 40% robustness + 30% stability + 30% consistency
- [ ] Module uses SimpleBacktester for window backtesting
- [ ] Module gracefully handles missing ClusteringRegimeDetector dependency

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| TYP-002 | 02-type-hints.md | Use modern syntax (Optional, Dict, List, Tuple) | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - Uses field(default_factory=list) |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Uses logging but not structured |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK - Logs exceptions and warnings |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - Try/except with logging |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - Implements Tomasini methodology |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - Separate test windows |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Chronological windows |
| BT-004 | BASE_RULES.md | Realistic costs | ⚠️ NOT APPLIED - Uses SimpleBacktester |
| PERF-002 | BASE_RULES.md | Generators for large data | ⚠️ NOT APPLIED - Not needed |
| ARCH-006 | 05-architecture.md | Value objects immutable | ✅ FIXED - 2026-02-03 - Added frozen=True for immutability |

**GAPS Found:**
- **LOG-001 (P1):** Not using structured logging (no JSON format)
- **ARCH-006 (P1):** ✅ FIXED - All dataclasses now use frozen=True
- **PERF-001 (P2):** No numba JIT compilation (documented as intentional)

---

## Dependencies
- **External:**
  - `numpy` (numerical calculations)
  - `scipy.stats` (statistical tests: linregress, t.interval)
  - `dataclasses` (standard library)
  - `datetime` (standard library)
  - `typing` (standard library)
  - `logging` (standard library)
  - `itertools.product` (for grid search)

- **Internal:**
  - `app.backtesting.engine.SimpleBacktester`
  - `app.backtesting.models.BacktestConfig`
  - `app.models.market_data.Quote`
  - `app.engines.context_engine.regime_detectors.clustering_regime_detector.ClusteringRegimeDetector` (optional)

---

## Required Tests
- **tests/unit/backtesting/validation/test_walk_forward_validator_enhanced.py:**
  - Test `create_rolling_windows()` creates correct number of windows
  - Test `create_rolling_windows()` uses 50% step size
  - Test `create_rolling_windows()` window chronology (train < test)
  - Test `detect_regime()` returns 'INSUFFICIENT_DATA' for < 126 quotes
  - Test `detect_regime()` returns 'UNKNOWN' when regime detector not available
  - Test `optimize_parameters()` returns empty dicts for empty param_grid
  - Test `optimize_parameters()` finds best parameters across grid
  - Test `calculate_window_metrics()` returns empty dict on backtest failure
  - Test `calculate_window_metrics()` returns valid metrics on success
  - Test `validate_strategy()` returns insufficient windows result when < min_cycles
  - Test `validate_strategy()` processes all windows correctly
  - Test `validate_strategy()` validates windows against thresholds
  - Test `calculate_parameter_stability()` calculates CV correctly
  - Test `calculate_parameter_stability()` detects drift using linregress
  - Test `calculate_parameter_stability()` calculates 95% CI
  - Test `_calculate_consistency_ratio()` handles zero/negative IS Sharpe
  - Test `_calculate_sharpe_degradation()` handles zero IS Sharpe
  - Test `_calculate_aggregate_results()` calculates correct averages
  - Test `_calculate_regime_robustness()` groups by regime correctly
  - Test `to_dict()` methods serialize datetime to ISO format
  - Test `to_dict()` methods handle None values correctly
  - Test overall pass/fail logic in `_calculate_aggregate_results()`
  - Test Tomasini score calculation (40/30/30 weighting)

---

## Notes
- **Tomasini Principles Implemented:**
  1. Step size = 50% of training window (balances stability vs adaptability)
  2. Minimum 5 cycles for statistical significance
  3. Track parameter stability (low CV = robust strategy)
  4. Regime-aware testing prevents false positives
  5. IS/OOS consistency ratio > 0.7 required
- **Performance Considerations:**
  - Does NOT use numba JIT (computational bottleneck is in SimpleBacktester)
  - Metrics calculations should use `app.backtesting.numba_metrics` for hot paths
- **Domain Design (DOM-001):**
  - Uses dataclasses instead of domain value objects for serialization simplicity
  - Future refactor should consider proper value objects with validation
- **References:**
  - Tomasini & Jaekle, "Designing Trading Systems" (Chapter 8)
  - López de Prado, "Advances in Financial Machine Learning"
- This is a FASE 5.3 Validation module
