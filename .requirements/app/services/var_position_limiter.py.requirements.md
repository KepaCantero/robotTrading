# Requirements: services/var_position_limiter.py

## Source File Analysis
- **File Path**: `app/services/var_position_limiter.py`
- **Lines of Code**: 637
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
VaR (Value-at-Risk) position limiter. Limits positions based on portfolio VaR calculations using real correlation matrices. Validates new positions don't exceed risk limits.

## Dependencies
- Internal:
  - `app.core.decimal_utils.to_decimal, validate_price` (Decimal utilities)
  - `app.engines.risk_engine.correlation_analyzers.CorrelationAnalyzer` (Correlation)
- External:
  - `logging`, `dataclasses`, `datetime`, `decimal`, `typing` (Standard library)
  - `numpy` (Numerical calculations)
  - `scipy.stats.norm` (Z-score calculation)

## Classes/Functions

### Data Classes
- `VaRConfig`: Configuration for VaR limits
  - max_var_limit_pct: 2% daily VaR limit
  - confidence_level: 95%
  - lookback_days: 60
  - warning_threshold_pct: 80% (warn at 80% of limit)

- `ValidationResult`: Result of position validation
  - passed, message, current_var, projected_var, var_limit, excess_var, utilization_pct, warnings

- `VaRMetrics`: Portfolio VaR metrics
  - var_95, var_99, portfolio_value, var_limit, utilization_pct, correlation_used

### Classes
- `VaRPositionLimiter`: Main VaR position limiter
  - `validate_position_with_var(symbol, quantity, current_price, side)`: Check position
  - `calculate_portfolio_var(confidence_level, lookback_days)`: Current portfolio VaR
  - `calculate_var_with_position(...)`: Projected VaR with new position
  - `get_var_utilization()`: Current utilization
  - `get_var_metrics()`: Comprehensive metrics
  - `calculate_max_position_size(...)`: Maximum allowed position
  - `update_volatility_cache(volatilities)`: Update cache

### Functions
- `get_var_position_limiter(portfolio, correlation_analyzer, config)`: Factory

## Business Logic

### VaR Formula
```
VaR = portfolio_value * sqrt(portfolio_variance) * z_score

where portfolio_variance = w' * Σ * w
(w = weights, Σ = covariance matrix)
```

### VaR Limit
- **Default**: 2% daily VaR (configurable)
- **Warning**: Alert at 80% utilization
- **Reject**: Position would exceed limit

### Correlation Usage
- **Real correlation**: From CorrelationAnalyzer if available
- **Identity matrix**: Fallback when no correlation data
- **Cached**: Per-symbol volatility cache

### Incremental VaR Calculation
Simplified (production should recalculate full covariance):
```
incremental_variance = w_new² * σ²_new + 2 * w_new * ρ_avg * σ_new * σ_avg
incremental_VaR = portfolio_value * sqrt(incremental_variance) * z_score
```

## Data Models
- Input: symbol, quantity, current_price, side
- Output: ValidationResult with pass/fail status
- State: portfolio, correlation_analyzer, config, caches

## API Contracts

### VaRPositionLimiter.validate_position_with_var()
```python
def validate_position_with_var(
    symbol: str,
    quantity: Decimal,
    current_price: Decimal,
    side: str = "LONG",
) -> ValidationResult
```

### VaRPositionLimiter.calculate_max_position_size()
```python
def calculate_max_position_size(
    symbol: str,
    current_price: Decimal,
    side: str = "LONG",
    target_utilization: Optional[Decimal] = None,
) -> Decimal
```

## Error Handling
- Validates quantity > 0
- Validates current_price via validate_price
- Catches ValueError, TypeError, KeyError, AttributeError, IndexError
- Returns failed ValidationResult on error

## Performance Considerations
- O(n²) for portfolio variance calculation (n=positions)
- Cached volatility values
- Efficient covariance matrix construction

## Testing Strategy
- Unit tests for VaR calculation accuracy
- Verify correlation matrix usage
- Test limit enforcement
- Edge cases: empty portfolio, single position, limit boundary

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Full type coverage with TYPE_CHECKING |
| Error Handling | ✅ PASS | Comprehensive exception handling |
| SOLID Principles | ✅ PASS | Single responsibility - VaR limiting |
| Logging | ✅ PASS | Debug/info logging |
| No Hardcoded Secrets | ✅ PASS | No secrets in code |
| Input Validation | ✅ PASS | Validates quantity, price via validate_price |
| Async Patterns | ✅ PASS | N/A - synchronous module |
| Documentation | ✅ PASS | Comprehensive docstrings with formulas |
| Financial Precision | ✅ PASS | Uses Decimal for monetary values |
| Numerical Methods | ✅ PASS | Correct numpy/scipy usage |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
