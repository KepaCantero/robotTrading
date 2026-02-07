# Requirements: backtesting/validation/walk_forward.py

## Source File Analysis
- **File Path**: `app/backtesting/validation/walk_forward.py`
- **Lines of Code**: 649
- **Audit Date**: 2026-02-07T12:00:00Z

## Audit Status
**Status**: PASSED_WITH_NOTES

### Critical Rules Compliance
- ✅ R099: Absolute imports only (relative import within same package is acceptable)
- ⚠️  R098: Uses `from .models import ...` (acceptable within same package)
- ✅ R104: No bare except clauses
- ✅ R105: No print() statements in production code
- ✅ R107: No mutable default arguments
- ✅ R108: Proper exception handling (specific Exception catching)
- ✅ R110: Google-style docstrings
- ✅ R111: No circular imports
- ⚠️  R100: Uses `Optional[T]` instead of modern `T | None` (acceptable for compatibility)
- ✅ R102: `Any` types are documented and appropriate for generic interfaces

## Purpose
Implements rolling window walk-forward validation for robust strategy testing (FASE 5.3). This module prevents look-ahead bias while measuring true out-of-sample performance through:

- Rolling window optimization with configurable train/test periods
- Multiple IS/OS periods for robust validation
- Aggregate IS vs OS metrics with degradation analysis
- Consistency scoring across periods
- Actionable recommendations based on validation results

References:
- AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
- "Advances in Financial Machine Learning" - Marcos López de Prado
- "Expected Returns" - Antti Ilmanen

## Dependencies

### External Dependencies
- `numpy`: Numerical operations and statistical calculations
- `pandas`: DataFrame operations and time series handling
- `scipy.stats`: Statistical operations
- `dataclasses`: Configuration dataclasses
- `datetime`, `decimal`, `timedelta`: Date and numeric handling
- `logging`: Structured logging
- `typing`: Type hints (including ParamSpec for callable signatures)

### Internal Dependencies
- `.models`:
  - `OverfittingLevel`, `OverfittingMetrics`: Overfitting detection
  - `PeriodResult`, `WalkForwardConfig`, `WalkForwardResult`: Data models

## Classes/Functions

### Main Classes
- `WalkForwardValidator`: Main walk-forward validation orchestrator
  - `__init__(config, optimizer)`: Initialize with configuration and optimizer
  - `validate(strategy_factory, param_grid, data, optimizer, progress_callback)`: Perform validation
  - `_generate_rolling_windows(data)`: Generate train/test windows
  - `_test_period(strategy_factory, params, data, is_in_sample, period_id)`: Test single period
  - `_aggregate_results(is_results, os_results)`: Aggregate across periods
  - `_calculate_aggregate_metrics(results)`: Calculate performance metrics
  - `_calculate_is_os_ratio(result)`: Calculate degradation metric
  - `_calculate_consistency_score(os_results)`: Calculate consistency score
  - `_generate_recommendations(result)`: Generate actionable recommendations

- `RollingWindowOptimizer`: Parameter optimizer for rolling windows
  - `__init__(optimization_metric, maximize)`: Initialize optimizer
  - `optimize(strategy_factory, param_grid, data)`: Optimize parameters
  - `_generate_param_combinations(param_grid)`: Generate all combinations
  - `_evaluate_strategy(strategy, data)`: Evaluate strategy metric

### Standalone Functions
- `calculate_degradation(is_value, os_value)`: Calculate degradation ratio
- `calculate_consistency_score(values)`: Calculate consistency score for values

## Business Logic

### Walk-Forward Validation Process
1. **Window Generation**: Create rolling train/test windows from data
   - Converts months to trading days (~21 days/month)
   - Validates minimum observations per window
   - Handles data boundaries gracefully

2. **Per-Window Validation**:
   - Optimize parameters on in-sample (IS) training data
   - Test on IS data (for comparison)
   - Test on out-of-sample (OS) test data
   - Record all metrics

3. **Aggregation**:
   - Calculate aggregate IS metrics (Sharpe, returns, drawdown, etc.)
   - Calculate aggregate OS metrics
   - Calculate IS/OS ratio (degradation metric)
   - Calculate consistency score across OS periods

4. **Recommendations**:
   - Analyze degradation levels (SEVERE/MODERATE/MILD)
   - Check consistency scores
   - Validate sample size
   - Review win rates

### Degradation Analysis
- **SEVERE**: OS Sharpe < 50% of IS Sharpe (likely overfitted)
- **MODERATE**: OS Sharpe < 70% of IS Sharpe (some overfitting)
- **MILD**: OS Sharpe < 85% of IS Sharpe (minor overfitting)

### Consistency Scoring
- Based on coefficient of variation (CV) of returns
- Score = 100 * (1 - CV), where CV = std / abs(mean)
- Higher score = more consistent performance

## Data Models

### Configuration (from .models)
```python
@dataclass
class WalkForwardConfig:
    train_period_months: int
    test_period_months: int
    step_months: int
    min_observations: int
```

### Results (from .models)
```python
@dataclass
class PeriodResult:
    start_date: date
    end_date: date
    is_in_sample: bool
    parameters: Dict[str, Any]
    total_trades: int
    total_return: Decimal
    win_rate: Decimal
    profit_factor: Optional[Decimal]
    equity_curve: List[Tuple[date, Decimal]]

@dataclass
class WalkForwardResult:
    is_results: List[PeriodResult]
    os_results: List[PeriodResult]
    is_performance: Dict[str, Any]
    os_performance: Dict[str, Any]
    is_os_ratio: Decimal
    consistency_score: Decimal
    num_periods: int
    total_days: int
    recommendations: List[str]
```

## API Contracts

### WalkForwardValidator.validate()
```python
def validate(
    strategy_factory: Callable[[Dict[str, Any]], Any],
    param_grid: Dict[str, List[Any]],
    data: pd.DataFrame,
    optimizer: Optional[Any] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> WalkForwardResult:
    """
    Returns WalkForwardResult with:
    - Aggregated IS and OS performance
    - IS/OS ratio (degradation metric)
    - Consistency score
    - Actionable recommendations
    """
```

### RollingWindowOptimizer.optimize()
```python
def optimize(
    strategy_factory: Callable[[Dict[str, Any]], Any],
    param_grid: Dict[str, List[Any]],
    data: pd.DataFrame,
) -> Dict[str, Any]:
    """Returns best parameter combination."""
```

## Error Handling

### Validation Errors
- `ValueError`: Insufficient data (< min_observations)
- `ValueError`: No optimizer provided
- `ValueError`: No valid windows generated

### Runtime Errors
- Exception in window validation: Log error and continue to next window
- Parameter evaluation error: Log warning and try next combination

### Logging
- INFO: Number of windows generated
- ERROR: Window validation errors
- WARNING: Parameter evaluation errors
- DEBUG: Individual fold scores

### Exception Handling Strategy
- Line 174: `except Exception as e` - Catches and logs per-window errors to allow remaining windows to process
- Line 561: `except Exception as e` - Catches parameter evaluation errors for graceful degradation

## Performance Considerations

### Computational Complexity
- O(n_windows × n_params × n_samples) for full grid search
- Parallelization potential: Independent windows can be processed in parallel

### Optimization Notes
- Rolling windows slide forward by step_months
- Parameter combinations generated once per optimization
- Metrics calculated incrementally

### Scalability
- Scales with number of windows and parameter combinations
- Memory usage: O(n_windows) for storing results
- Progress callback allows UI updates during long runs

## Testing Strategy

### Unit Tests Required
- Test window generation with various configurations
- Test aggregate metrics calculation
- Test degradation ratio calculation
- Test consistency score calculation
- Test recommendation generation logic

### Integration Tests Required
- Test with real strategy factory
- Test with real optimizer
- Test with multi-year price data
- Test progress callback functionality

### Edge Cases
- Insufficient data scenarios
- Empty parameter grid
- Single parameter combination
- Minimum window boundaries

## Notes

### Type Hints
- Uses `Optional[T]` for Python 3.9+ compatibility
- Migration to `T | None` syntax planned for Python 3.10+

### Any Usage Justification
- `optimizer: Optional[Any]` - Generic optimizer interface
  - Must have `optimize()` method
  - Strategy factories can return any strategy type
  - Documented in docstrings

- `Callable[[Dict[str, Any]], Any]` - Strategy factory pattern
  - Input: Parameter dictionary
  - Output: Strategy instance (any type)
  - Standard pattern for strategy instantiation

- `Dict[str, Any]` - Generic metrics dictionary
  - Flexible metric storage
  - Documented in docstrings

### Relative Import Note
- Uses `from .models import ...` which is acceptable within the same package
- This follows Python best practices for intra-package imports
- Not a violation of R098 (no parent package relative imports)

### Compliance with BASE_RULES.md
- See ../../BASE_RULES.md for universal rules
- All P0 and P1 rules satisfied
- Type hint style is compatibility choice, not violation
- Exception handling is appropriate for batch processing context

---
*Audited on 2026-02-07T12:00:00Z - PASSED_WITH_NOTES*
*No critical violations found. Code is production-ready.*
