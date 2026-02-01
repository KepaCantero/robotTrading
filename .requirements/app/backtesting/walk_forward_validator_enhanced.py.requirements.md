# walk_forward_validator_enhanced.py

## Purpose
Tomasini-compliant walk-forward validation with rolling windows, parameter stability tracking, regime-aware testing, and IS/OOS consistency scoring.

---

## Type Definitions / Data Classes

### ParameterHistory
```python
@dataclass
class ParameterHistory:
    window_id: int  # REQUIRED - Window identifier
    parameters: dict[str, float]  # REQUIRED - Optimal parameters for this window
    in_sample_sharpe: float  # REQUIRED - In-sample Sharpe ratio
    out_of_sample_sharpe: float  # REQUIRED - Out-of-sample Sharpe ratio
    in_sample_return: float  # REQUIRED - In-sample total return
    out_of_sample_return: float  # REQUIRED - Out-of-sample total return
    window_start: datetime  # REQUIRED - Training window start
    window_end: datetime  # REQUIRED - Test window end
    regime: str  # REQUIRED - Market regime (BULL, BEAR, SIDEWAYS, UNKNOWN)
```

**Validation Rules:**
- window_id must be positive integer
- All Sharpe and return values are floats
- to_dict() method returns dictionary with ISO format dates

### ParameterStabilityMetrics
```python
@dataclass
class ParameterStabilityMetrics:
    parameter_name: str  # REQUIRED - Parameter name
    mean_value: float  # REQUIRED - Mean across windows
    std_value: float  # REQUIRED - Standard deviation
    cv: float  # REQUIRED - Coefficient of variation (std/mean)
    min_value: float  # REQUIRED - Minimum value
    max_value: float  # REQUIRED - Maximum value
    range_pct: float  # REQUIRED - Range as percentage of mean
    drift_trend: float  # REQUIRED - Linear regression slope
    drift_significance: float  # REQUIRED - P-value for trend
    is_stable: bool  # REQUIRED - Stable if CV < threshold (default 30%)
    confidence_interval_95: tuple[float, float]  # REQUIRED - 95% CI
```

**Validation Rules:**
- cv = std_value / mean_value (can be infinite if mean_value = 0)
- is_stable = (cv < 0.30) by default (Tomasini threshold)
- drift_significance from scipy.stats.linregress

### TomasiniWindowResult
```python
@dataclass
class TomasiniWindowResult:
    window_id: int  # REQUIRED - Window identifier
    train_start: datetime  # REQUIRED - Training start
    train_end: datetime  # REQUIRED - Training end
    test_start: datetime  # REQUIRED - Test start
    test_end: datetime  # REQUIRED - Test end
    # In-Sample metrics
    is_return: float  # REQUIRED - IS total return
    is_sharpe: float  # REQUIRED - IS Sharpe ratio
    is_sortino: float  # REQUIRED - IS Sortino ratio
    is_max_drawdown: float  # REQUIRED - IS max drawdown
    is_volatility: float  # REQUIRED - IS volatility
    is_trades: int  # REQUIRED - IS number of trades
    # Out-of-Sample metrics
    oos_return: float  # REQUIRED - OOS total return
    oos_sharpe: float  # REQUIRED - OOS Sharpe ratio
    oos_sortino: float  # REQUIRED - OOS Sortino ratio
    oos_max_drawdown: float  # REQUIRED - OOS max drawdown
    oos_volatility: float  # REQUIRED - OOS volatility
    oos_trades: int  # REQUIRED - OOS number of trades
    # Consistency metrics
    consistency_ratio: float  # REQUIRED - OOS Sharpe / IS Sharpe
    return_degradation: float  # REQUIRED - (IS Return - OOS Return) / |IS Return|
    sharpe_degradation: float  # REQUIRED - (IS Sharpe - OOS Sharpe) / IS Sharpe
    # Regime information
    train_regime: str  # REQUIRED - Training period regime
    test_regime: str  # REQUIRED - Test period regime
    regime_change: bool  # REQUIRED - True if regimes differ
    # Optimal parameters
    optimal_parameters: dict[str, float]  # REQUIRED - Optimal params for this window
    # Validation status
    passed: bool  # REQUIRED - Window passed validation
    failure_reasons: list[str]  # OPTIONAL - Reasons for failure
```

**Validation Rules:**
- consistency_ratio must be >= 0 (can be > 1 if OOS better than IS)
- sharpe_degradation in range [0, 1] (0% to 100% degradation)
- failure_reasons defaults to empty list
- to_dict() returns nested dictionary structure

### TomasiniWalkForwardResult
```python
@dataclass
class TomasiniWalkForwardResult:
    # Overall results
    passed: bool  # REQUIRED - Overall validation passed
    total_windows: int  # REQUIRED - Total windows tested
    passed_windows: int  # REQUIRED - Windows that passed
    # Aggregated metrics
    avg_is_return: float  # REQUIRED - Average IS return
    avg_oos_return: float  # REQUIRED - Average OOS return
    avg_is_sharpe: float  # REQUIRED - Average IS Sharpe
    avg_oos_sharpe: float  # REQUIRED - Average OOS Sharpe
    # Consistency metrics
    avg_consistency_ratio: float  # REQUIRED - Average OOS/IS Sharpe ratio
    avg_return_degradation: float  # REQUIRED - Average return degradation
    avg_sharpe_degradation: float  # REQUIRED - Average Sharpe degradation
    # Window results
    windows: list[TomasiniWindowResult]  # REQUIRED - All window results
    # Parameter stability
    parameter_stability: dict[str, ParameterStabilityMetrics]  # REQUIRED - Stability per parameter
    # Robustness metrics
    robustness_score: float  # REQUIRED - 0-1 robustness score
    regime_robustness: dict[str, float]  # REQUIRED - Performance by regime
    # Failure analysis
    failure_reasons: list[str]  # REQUIRED - Unique failure reasons
    # Tomasini-specific metrics
    tomasini_score: float  # REQUIRED - 0-100 overall score
    parameter_stability_score: float  # REQUIRED - 0-100 stability score
    consistency_score: float  # REQUIRED - 0-100 consistency score
```

**Validation Rules:**
- passed_windows <= total_windows
- robustness_score = passed_windows / total_windows
- tomasini_score = (robustness * 0.4 + parameter_stability * 0.3 + consistency * 0.3) * 100
- All scores in range [0, 100]

---

## Function Signatures (Contracts)

### `__init__(config: dict[str, Any] | None = None) -> None`
**Pre:** None
**Post:** TomasiniWalkForwardValidator initialized with default or custom config
**Raises:** No (defaults applied)
**Retry:** No
**Side Effects:** Initializes regime detector if available

### `create_rolling_windows(start_date: datetime, end_date: datetime, train_years: float | None = None) -> list[dict[str, datetime]]`
**Pre:** start_date < end_date, train_years > 0
**Post:** Returns list of window definitions with train_start, train_end, test_start, test_end
**Raises:** No (returns empty list if dates invalid)
**Retry:** No
**Side Effects:** None (pure function)

### `validate_strategy(quotes: list[Quote], signals: list[Any], config: BacktestConfig, start_date: datetime, end_date: datetime, param_grid: dict[str, list[Any]] | None = None) -> TomasiniWalkForwardResult`
**Pre:** quotes non-empty, signals correspond to quotes period, config valid
**Post:** Returns TomasiniWalkForwardResult with complete analysis
**Raises:** No (returns insufficient_windows_result on error)
**Retry:** No
**Side Effects:** Executes backtests for each window, updates parameter history

### `optimize_parameters(...) -> tuple[dict[str, Any], dict[str, float]]`
**Pre:** train_quotes non-empty, param_grid non-empty
**Post:** Returns (best_parameters, best_metrics) for optimization metric
**Raises:** No (returns empty dicts on error)
**Retry:** No
**Side Effects:** Runs grid search with SimpleBacktester

### `calculate_parameter_stability(history: list[ParameterHistory]) -> dict[str, ParameterStabilityMetrics]`
**Pre:** history non-empty with at least 2 windows
**Post:** Returns dict mapping parameter_name to stability metrics
**Raises:** No (returns empty dict if insufficient data)
**Retry:** No
**Side Effects:** Uses scipy.stats for statistical tests (linregress, t interval)

### `detect_regime(quotes: list[Quote], start_date: datetime, end_date: datetime) -> str`
**Pre:** quotes non-empty, start_date < end_date
**Post:** Returns regime label: 'BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN', or 'INSUFFICIENT_DATA'
**Raises:** No (returns 'UNKNOWN' on error)
**Retry:** No
**Side Effects:** Uses ClusteringRegimeDetector if available

---

## Acceptance Criteria
- [ ] AC-001: Rolling windows use Tomasini methodology (50% step size of training window)
- [ ] AC-002: Minimum 5 cycles required for statistical significance
- [ ] AC-003: Step size = 50% of training window (default 2 years for 4-year training)
- [ ] AC-004: Rolling windows (not anchored) move forward by step size
- [ ] AC-005: IS/OOS consistency ratio > 0.7 required for robust strategies
- [ ] AC-006: Parameter stability: CV < 30% indicates stable parameters
- [ ] AC-007: At least 60% of parameters must be stable
- [ ] AC-008: Regime-aware testing detects BULL, BEAR, SIDEWAYS regimes
- [ ] AC-009: Linear regression detects parameter drift (slope, p-value)
- [ ] AC-010: 95% confidence intervals calculated for parameter means
- [ ] AC-011: Tomasini score = robustness * 0.4 + stability * 0.3 + consistency * 0.3
- [ ] AC-012: Minimum 10 trades per window required
- [ ] AC-013: Thresholds: min_consistency_ratio=0.7, max_sharpe_degradation=0.30, max_parameter_cv=0.30
- [ ] AC-014: Grid search optimization with param_grid (all combinations tested)
- [ ] AC-015: to_dict() methods return JSON-serializable dictionaries (ISO format dates)
- [ ] AC-016: Type hints cover all methods (mypy --strict)
- [ ] AC-017: Fallback to 'UNKNOWN' regime when detector unavailable

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage for all methods | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK (try/except throughout) |
| BT-001 | 13-trading-specific-rules | Walk-forward validation required | ✅ OK (Tomasini methodology) |
| BT-002 | 13-trading-specific-rules | Out-of-sample testing required | ✅ OK (50% step size) |
| BT-003 | 13-trading-specific-rules | No look-ahead bias | ✅ OK (temporal windowing) |
| BT-005 | 13-trading-specific-rules | Multiple periods tested | ✅ OK (rolling windows) |
| PERF-006 | 19-sre-performance.md | Async I/O for concurrency | ❌ GAP - Not using async (sync is OK for this use case) |
| ARCH-004 | 05-architecture.md | Small functions < 20 lines | ⚠️ NOT APPLIED - Complex calculations |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, scipy (stats)
- **Internal:**
  - app.backtesting.engine.SimpleBacktester
  - app.backtesting.models.BacktestConfig
  - app.models.market_data.Quote
  - app.engines.context_engine.regime_detectors.clustering_regime_detector.ClusteringRegimeDetector (optional)

---

## Required Tests
- **tests/unit/backtesting/test_walk_forward_validator_enhanced.py:**
  - Test rolling window creation (Tomasini 50% step size)
  - Test minimum 5 cycles requirement
  - Test IS/OOS consistency ratio calculation
  - Test parameter stability calculation (CV, drift, CI)
  - Test parameter stability score (60% threshold)
  - Test regime detection (BULL, BEAR, SIDEWAYS, UNKNOWN)
  - Test regime detector fallback when unavailable
  - Test optimize_parameters grid search
  - Test window metrics calculation (IS and OOS)
  - Test aggregate results calculation
  - Test Tomasini score calculation (weighted formula)
  - Test threshold validation (consistency, degradation, stability)
  - Test to_dict() methods return JSON-serializable output
  - Test insufficient windows result (< 5 cycles)
  - Test empty parameter stability handling

- **tests/integration/backtesting/test_walk_forward_validator_integration.py:**
  - Test full walk-forward workflow with real data
  - Test parameter evolution tracking across windows
  - Test regime-aware validation (performance by regime)
  - Test statistical tests (linregress for drift, t interval for CI)
  - Test grid search optimization convergence
  - Test backtest execution per window
  - Test failure reason aggregation
  - Test robustness score calculation
  - Test overall validation decision logic

---

## Notes
- Implements Tomasini & Jaekle methodology from "Designing Trading Systems" (Chapter 8)
- Does NOT use numba JIT (computational bottleneck is in SimpleBacktester, not here)
- If performance optimization needed, use numba_metrics for hot paths
- Uses dataclasses instead of domain value objects for serialization simplicity
- Optional regime detector dependency (gracefully degrades if unavailable)
- All statistical tests use scipy.stats (linregress, ttest_rel, t interval)
