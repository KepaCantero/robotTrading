# Requirements: services/strategy_stock_allocation/orchestrator.py

## Source File Analysis
- **File Path**: `app/services/strategy_stock_allocation/orchestrator.py`
- **Lines of Code**: 583
- **Status**: Analysis Complete
- **Audit Date**: 2026-02-07

## Purpose
Main orchestrator for stock allocation across trading strategies. Coordinates filtering, scoring, strategy assignment, and ERC capital allocation.

## Dependencies
- Internal:
  - `app.core.centralized_config.StockAllocationSettings` (Configuration)
  - Multiple internal modules (calculators, scorers, validators)
- External:
  - `logging` (Standard library)
  - `typing`, `collections` (Standard library)
  - `pandas` (Data manipulation)
  - `pydantic` (Data validation)

## Classes/Functions

### Classes
- `StockMetrics`: Metrics for single stock (Pydantic model)
- `PairMetrics`: Metrics for trading pair (Pydantic model)
- `AllocationResult`: Result of allocation (Pydantic model)
- `StrategyStockAllocator`: Main orchestrator
  - `allocate(historical_data, total_capital, strategy_allocations)`: Main pipeline
  - Dependencies: StockFilter, HurstCalculator, HalfLifeCalculator, etc.

## Business Logic

### Allocation Pipeline
1. **Filter stocks**: Validation and liquidity checks
2. **Calculate WCM scores**: Momentum, mean reversion, pairs
3. **Assign strategies**: Resolve conflicts, prioritize pairs
4. **Allocate capital**: ERC (Equal Risk Contribution) within strategies
5. **Validate**: Check constraints
6. **Generate output**: Results and logs

### Strategy Assignment Logic
- Pairs trading prioritized (highest cointegration)
- Momentum vs mean reversion based on scores
- Minimum tickers per strategy (capital utilization)

### Capital Redistribution
- Residual capital redistributed proportionally
- Respects MAX_STRATEGY_EXPOSURE limits
- Floating-point correction applied

## Data Models
- **StockMetrics**: ticker, strategy, weight, capital, scores
- **PairMetrics**: ticker1, ticker2, cointegration, correlation
- **AllocationResult**: allocations, pairs, residual, validation status

## API Contracts

### StrategyStockAllocator.allocate()
```python
def allocate(
    historical_data: Dict[str, pd.DataFrame],
    total_capital: float,
    strategy_allocations: Optional[Dict[str, float]] = None,
) -> AllocationResult
```

## Error Handling
- ValueError, TypeError, KeyError, AttributeError caught
- Returns AllocationResult with validation errors
- Comprehensive logging throughout

## Performance Considerations
- O(n²) for pair cointegration checks
- Pandas vectorized operations
- In-memory caching of metrics

## Testing Strategy
- Integration tests for full pipeline
- Edge cases: empty data, single stock, failed filters
- Verify ERC allocation correctness
- Test redistribution logic

## Audit Status

| **Aspect** | **Status** | **Notes** |
|------------|------------|-----------|
| Type Hints | ✅ PASS | Modern syntax with Optional, Dict, List |
| Error Handling | ✅ PASS | Comprehensive exception handling |
| SOLID Principles | ✅ PASS | Dependency injection via constructor |
| Logging | ✅ PASS | Info/debug logging throughout |
| No Hardcoded Secrets | ✅ PASS | Configuration from YAML/Pydantic |
| Input Validation | ✅ PASS | Pydantic models, validation checks |
| Async Patterns | ✅ PASS | N/A - synchronous module |
| Documentation | ✅ PASS | Detailed docstrings |
| Data Validation | ✅ PASS | Pydantic BaseModel for data models |
| Overall Compliance | ✅ PASS | All BASE_RULES critical requirements met |

**Audit Date**: 2026-02-07
**Auditor**: Claude (Backend Developer Agent)
**Status**: PASSED

---
*Last updated: 2026-02-07*
