# walk_forward_validator_enhanced.py

## Purpose
Implements Tomasini & Jaekle's walk-forward optimization methodology with parameter stability tracking, regime-aware validation, and rolling window optimization for robust backtesting validation.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### ParameterHistory Class/DataClass
```python
@dataclass
class ParameterHistory:
    window_id: int                       # REQUIRED - Unique window identifier
    parameters: Dict[str, float]         # REQUIRED - Optimized parameters for this window
    in_sample_sharpe: float              # REQUIRED - In-sample Sharpe ratio
    out_of_sample_sharpe: float          # REQUIRED - Out-of-sample Sharpe ratio
    in_sample_return: float              # REQUIRED - In-sample return
    out_of_sample_return: float          # REQUIRED - Out-of-sample return
    window_start: datetime               # REQUIRED - Training window start date
    window_end: datetime                 # REQUIRED - Test window end date
    regime: str                          # REQUIRED - Market regime label (BULL/BEAR/SIDEWAYS)
```

**Validation Rules:**
- `parameters` dict must contain at least one parameter
- Sharpe ratios must be finite values (no NaN or Inf)
- `window_end` must be after `window_start`
- `regime` must be one of: 'BULL', 'BEAR', 'SIDEWAYS', 'UNKNOWN', 'INSUFFICIENT_DATA'

### ParameterStabilityMetrics Class/DataClass
```python
@dataclass
class ParameterStabilityMetrics:
    parameter_name: str                  # REQUIRED - Name of parameter being tracked
    mean_value: float                    # REQUIRED - Mean value across windows
    std_value: float                     # REQUIRED - Standard deviation
    cv: float                            # REQUIRED - Coefficient of variation (std/mean)
    min_value: float                     # REQUIRED - Minimum value observed
    max_value: float                     # REQUIRED - Maximum value observed
    range_pct: float                     # REQUIRED - Range as percentage of mean
    drift_trend: float                   # REQUIRED - Linear regression slope
    drift_significance: float            # REQUIRED - P-value for trend significance
    is_stable: bool                      # REQUIRED - True if CV < max_parameter_cv threshold
    confidence_interval_95: Tuple[float, float]  # REQUIRED - 95% CI bounds
```

**Validation Rules:**
- `cv` must be non-negative
- `is_stable` must be False if `cv >= 0.30` (Tomasini threshold)
- `confidence_interval_95` must have lower < upper bounds
- `drift_significance` must be in range [0, 1]

### TomasiniWindowResult Class/DataClass
```python
@dataclass
class TomasiniWindowResult:
    window_id: int                       # REQUIRED - Sequential window number
    train_start: datetime                # REQUIRED - Training period start
    train_end: datetime                  # REQUIRED - Training period end
    test_start: datetime                 # REQUIRED - Test period start
    test_end: datetime                   # REQUIRED - Test period end
    is_return: float                     # REQUIRED - In-sample total return
    is_sharpe: float                     # REQUIRED - In-sample Sharpe ratio
    is_sortino: float                    # REQUIRED - In-sample Sortino ratio
    is_max_drawdown: float               # REQUIRED - In-sample max drawdown (negative)
    is_volatility: float                 # REQUIRED - In-sample volatility
    is_trades: int                       # REQUIRED - In-sample trade count, min(0)
    oos_return: float                    # REQUIRED - Out-of-sample total return
    oos_sharpe: float                    # REQUIRED - Out-of-sample Sharpe ratio
    oos_sortino: float                   # REQUIRED - Out-of-sample Sortino ratio
    oos_max_drawdown: float              # REQUIRED - Out-of-sample max drawdown
    oos_volatility: float                # REQUIRED - Out-of-sample volatility
    oos_trades: int                      # REQUIRED - Out-of-sample trade count, min(0)
    consistency_ratio: float             # REQUIRED - OOS Sharpe / IS Sharpe ratio
    return_degradation: float            # REQUIRED - (IS - OOS) / |IS| return degradation
    sharpe_degradation: float            # REQUIRED - (IS - OOS) / IS Sharpe degradation
    train_regime: str                    # REQUIRED - Regime during training
    test_regime: str                     # REQUIRED - Regime during testing
    regime_change: bool                  # REQUIRED - True if regimes differ
    optimal_parameters: Dict[str, float] # REQUIRED - Best parameters for this window
    passed: bool                         # REQUIRED - Whether window passed validation
    failure_reasons: List[str]           # OPTIONAL - Reasons for failure, empty if passed
```

**Validation Rules:**
- `consistency_ratio` must be in range [0, 1] for stable strategies
- `sharpe_degradation` must be non-negative
- `oos_trades` must be >= `min_trades_per_window` (default: 10)
- All Sharpe ratios must be finite
- Dates must be sequential: train_start < train_end <= test_start < test_end

### TomasiniWalkForwardResult Class/DataClass
```python
@dataclass
class TomasiniWalkForwardResult:
    passed: bool                         # REQUIRED - Overall pass/fail status
    total_windows: int                   # REQUIRED - Total windows tested
    passed_windows: int                  # REQUIRED - Windows that passed validation
    avg_is_return: float                 # REQUIRED - Average in-sample return
    avg_oos_return: float                # REQUIRED - Average out-of-sample return
    avg_is_sharpe: float                 # REQUIRED - Average in-sample Sharpe
    avg_oos_sharpe: float                # REQUIRED - Average out-of-sample Sharpe
    avg_consistency_ratio: float         # REQUIRED - Average OOS/IS consistency
    avg_return_degradation: float        # REQUIRED - Average return degradation
    avg_sharpe_degradation: float        # REQUIRED - Average Sharpe degradation
    windows: List[TomasiniWindowResult]  # REQUIRED - All window results
    parameter_stability: Dict[str, ParameterStabilityMetrics]  # REQUIRED - Stability by param
    robustness_score: float              # REQUIRED - Pass rate (0-1)
    regime_robustness: Dict[str, float]  # REQUIRED - Performance by regime
    failure_reasons: List[str]           # OPTIONAL - Aggregated failure reasons
    tomasini_score: float                # REQUIRED - Overall score 0-100
    parameter_stability_score: float     # REQUIRED - Parameter stability 0-100
    consistency_score: float             # REQUIRED - Consistency score 0-100
```

**Validation Rules:**
- `total_windows` must be >= `min_cycles` (default: 5)
- `passed_windows` <= `total_windows`
- `robustness_score` = `passed_windows / total_windows`
- All scores must be in range [0, 100]
- `passed` requires: robustness >= 0.6 AND parameter_stability >= 0.6 AND consistency >= 0.7

---

## Function Signatures (Contracts)

### `TomasiniWalkForwardValidator.__init__(config: Optional[Dict[str, Any]] = None) -> None`
**Pre:** config is None or contains valid keys (train_years, step_percentage, min_cycles, thresholds)
**Post:** Validator initialized with Tomasini-compliant settings (step_pct=0.5, min_cycles=5)
**Raises:** None
**Retry:** No
**Side Effects:** Initializes regime_detector if REGIME_DETECTOR_AVAILABLE and regime_aware=True

### `create_rolling_windows(start_date: datetime, end_date: datetime, train_years: Optional[float] = None) -> List[Dict[str, datetime]]`
**Pre:** start_date < end_date, train_years >= 1.0
**Post:** Returns list of windows with train/test periods, step size = 50% of training window
**Raises:** None
**Retry:** No
**Side Effects:** None

### `optimize_parameters(train_quotes: List[Quote], train_signals: List[Any], param_grid: Dict[str, List[Any]], config: BacktestConfig, optimization_metric: str = "sharpe_ratio") -> Tuple[Dict[str, Any], Dict[str, float]]`
**Pre:** train_quotes not empty, param_grid not empty, config valid
**Post:** Returns (best_parameters, best_metrics) where best_parameters maximizes optimization_metric
**Raises:** Exception if backtest fails for all parameter combinations
**Retry:** No
**Side Effects:** Runs multiple backtests (one per parameter combination)

### `validate_strategy(quotes: List[Quote], signals: List[Any], config: BacktestConfig, start_date: datetime, end_date: datetime, param_grid: Optional[Dict[str, List[Any]]] = None) -> TomasiniWalkForwardResult`
**Pre:** quotes sorted by timestamp, start_date <= min(quotes).timestamp, end_date >= max(quotes).timestamp
**Post:** Returns complete walk-forward result with >= min_cycles windows if sufficient data
**Raises:** None (returns insufficient_windows_result if too few windows)
**Retry:** No
**Side Effects:** Creates windows, optimizes parameters per window, runs backtests

### `calculate_parameter_stability(history: List[ParameterHistory]) -> Dict[str, ParameterStabilityMetrics]`
**Pre:** history has >= 2 entries with same parameter names
**Post:** Returns stability metrics for each parameter (mean, std, CV, drift, CI)
**Raises:** None
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Rolling windows use Tomasini step size (50% of training window)
- [ ] Minimum 5 complete walk-forward cycles for statistical significance
- [ ] Consistency ratio (OOS/IS Sharpe) >= 0.7 for passing strategies
- [ ] Parameter stability calculated with CV < 30% threshold
- [ ] Regime-aware validation detects BULL/BEAR/SIDEWAYS regimes
- [ ] Overall Tomasini score combines robustness (40%), stability (30%), consistency (30%)
- [ ] Returns pass/fail based on: min_cycles met, robustness >= 0.6, stability >= 0.6, consistency >= 0.7
- [ ] Parameter drift tracked via linear regression with p-value significance
- [ ] Gracefully handles insufficient data (returns failed result with explanation)
- [ ] Optional regime_detector only used if REGIME_DETECTOR_AVAILABLE

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 No mutable defaults | 01-formatting-style.md | Use None instead of [] or {} in defaults | ✅ OK - Uses `field(default_factory=list)` |
| TYP-001 100% type coverage | 02-type-hints.md | All functions have type hints | ✅ OK - All functions typed |
| SOL-001 Single Responsibility | 03-solid-principles.md | One class, one reason to change | ✅ OK - Class handles walk-forward validation only |
| ERR-001 Exception handling | 05-error-handling.md | Catch specific exceptions, log context | ⚠️ NOT APPLIED - Uses generic Exception in optimize_parameters (line 538) |
| LOG-001 Structured logging | 06-logging.md | Use structured logs with context | ✅ OK - Uses logger.info/warning with context |
| PERF-001 Numba for hot paths | 07-performance.md | Use JIT compilation for performance-critical code | ✅ FIXED - 2026-02-01 - Documented numba usage rationale |
| VAL-001 Input validation | 08-validation.md | Validate all inputs before processing | ⚠️ NOT APPLIED - No validation of quotes/signals ordering |
| DOM-001 Use value objects | 09-domain.md | Use domain value objects instead of primitives | ✅ FIXED - 2026-02-01 - Documented dataclass vs VO decision |
| TEST-001 Deterministic tests | 10-testing.md | Tests must be deterministic and reproducible | ✅ OK - Uses fixed config parameters |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, scipy.stats, yaml, dataclasses, typing, datetime, logging, itertools
- **Internal:**
  - `app.backtesting.engine.SimpleBacktester`
  - `app.backtesting.models.BacktestConfig`
  - `app.models.market_data.Quote`
  - `app.engines.context_engine.regime_detectors.clustering_regime_detector.ClusteringRegimeDetector` (optional)

---

## Required Tests
- **test_walk_forward_validator.py:**
  - Success: Creates correct number of rolling windows with 50% step size
  - Success: Parameter stability calculates CV, drift, CI correctly
  - Success: Regime detection labels periods as BULL/BEAR/SIDEWAYS
  - Success: Pass/fail determination based on thresholds
  - Edge: Insufficient data (< 5 windows) returns failed result
  - Edge: Empty param_grid skips optimization
  - Error: Invalid date ranges handled gracefully
  - Integration: Full walk-forward cycle with parameter optimization
  - Integration: Tomasini score calculation weights components correctly

---

## Notes
This is the enhanced walk-forward validator implementing Tomasini & Jaekle methodology. Key improvements over standard implementation: (1) Rolling windows with 50% step size, (2) Parameter stability tracking across windows, (3) Regime-aware validation when detector available, (4) IS/OOS consistency ratio >= 0.7 requirement, (5) Minimum 5 cycles for statistical significance. The regime_detector import is optional - gracefully degrades if not available.

## GAP Fixes (2026-02-01)

### PERF-001 - Numba Usage Documentation
✅ FIXED - Added comprehensive performance considerations documentation in module docstring:
- Explained why numba is NOT used (bottleneck is in SimpleBacktester, not here)
- Documented how to use numba_metrics for performance-critical operations
- Provided specific recommendations for future optimization

### DOM-001 - Value Objects vs Dataclasses
✅ FIXED - Added domain design documentation:
- Explained use of dataclasses instead of domain value objects
- Documented to_dict() methods return plain dictionaries for JSON serialization
- Provided future refactoring guidance for proper value objects

### Implementation Details
The module header now includes:
- Performance Considerations section explaining numba usage rationale
- Domain Design section documenting dataclass vs VO trade-off
- Specific recommendations for using numba_metrics.py for hot paths
- Future refactoring path toward proper domain entities
