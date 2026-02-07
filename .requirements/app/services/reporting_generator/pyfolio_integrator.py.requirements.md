# Requirements: services/reporting_generator/pyfolio_integrator.py

## Source File Analysis
- **File Path**: `app/services/reporting_generator/pyfolio_integrator.py`
- **Lines of Code**: 704
- **Language**: Python 3
- **Purpose**: Integration with pyfolio library for advanced performance metrics

## Purpose
Wraps pyfolio library for advanced performance analytics:
- Risk-adjusted returns (Sharpe, Sortino)
- Drawdown analysis
- Transaction costs analysis
- Per-period statistics
- Tearsheet generation

## Dependencies
- **Internal**:
  - None (standalone integration)
- **External**:
  - `pyfolio` - Performance analytics
  - `pandas` - Data manipulation
  - `numpy` - Numerical computing
  - `typing` - Type hints
  - `logging` - Structured logging

## Classes/Functions

### PyfolioIntegrator
- **Purpose**: Main integration class
- **Key Methods**:
  - `calculate_returns()` - Calculate returns from prices
  - `create_tearsheet()` - Generate pyfolio tearsheet
  - `get_perf_stats()` - Get performance statistics
  - `get_rolling_stats()` - Rolling window statistics
  - `analyze_transactions()` - Transaction cost analysis

## Business Logic

### Pyfolio Integration
1. Format data for pyfolio (returns, positions, transactions)
2. Call pyfolio functions
3. Format results for internal use
4. Generate tearsheet HTML

### Metrics Calculated
- Cumulative returns
- Annual returns
- Monthly returns
- Daily returns
- Sharpe ratio
- Sortino ratio
- Max drawdown
- Calmar ratio
- Omega ratio
- Tail ratio

## Data Models
- Returns as pandas Series
- Positions as DataFrame
- Transactions as DataFrame

## API Contracts
```python
def create_tearsheet(
    returns: pd.Series,
    positions: Optional[pd.DataFrame] = None,
    transactions: Optional[pd.DataFrame] = None,
    live_start_date: Optional[str] = None
) -> str

def get_perf_stats(returns: pd.Series) -> Dict[str, float]
```

## Error Handling
- Validates pandas DataFrames
- Handles missing data
- Catches pyfolio exceptions

## Performance Considerations
- Pyfolio can be slow on large datasets
- Consider caching results
- Parallel computation where possible

## Testing Strategy
- Test with sample returns data
- Test tearsheet generation
- Test edge cases (empty data, single day)

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-003: Some Any types acceptable for pandas

### Clean Code
- CC-001: Descriptive names
- CC-006: Error handling

## Audit Status
**Status**: PASSED

### Strengths
1. Good integration with pyfolio
2. Proper pandas usage
3. Type hints where appropriate
4. Error handling for edge cases

### Minor Observations
1. Some Any types unavoidable with pandas
2. Could add more input validation

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready integration

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0080*
*Status: PASSED*
