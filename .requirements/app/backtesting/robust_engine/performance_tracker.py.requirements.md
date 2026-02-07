# Requirements: backtesting/robust_engine/performance_tracker.py

## Source File Analysis
- **File Path**: `app/backtesting/robust_engine/performance_tracker.py`
- **Lines of Code**: 650
- **Audit Status**: PASSED
- **Audit Date**: 2026-02-07T05:30:00Z

## Purpose
Performance Tracker for Robust Backtesting Engine. Provides comprehensive performance tracking for long-term backtests over 25+ year periods with year-by-year breakdown, rolling metrics, regime analysis, drawdown analysis, and risk-adjusted returns.

## Dependencies
- Internal: None (standalone tracker)
- External:
  - `logging` (for structured logging)
  - `dataclasses` (dataclass, field)
  - `datetime` (date, datetime)
  - `decimal` (Decimal)
  - `typing` (Any, Dict, List, Optional, Tuple)
  - `numpy` (np)
  - `pandas` (pd)
  - `scipy.stats` (stats)

## Classes/Functions
### Dataclasses
- `YearlyBreakdown`: Performance breakdown for a single year
- `RollingMetrics`: Rolling performance metrics over different windows
- `RegimeAnalysis`: Analysis of performance across market regimes
- `PerformanceMetrics`: Comprehensive performance metrics for backtesting results

### Main Class
- `PerformanceTracker`: Tracks and calculates comprehensive performance metrics
  - `__init__(initial_capital, risk_free_rate)`: Initialize tracker
  - `update(current_date, current_capital, trades)`: Update with new equity value
  - `calculate_metrics()`: Calculate comprehensive metrics
  - `get_yearly_breakdown()`: Get year-by-year breakdown
  - `get_rolling_metrics(windows)`: Calculate rolling metrics
  - Private methods for metric calculations

## Business Logic
- Real-time performance tracking during backtest execution
- Equity curve tracking with drawdown detection
- Trade tracking with win/loss analysis
- Streak tracking (winning/losing)
- Year-by-year performance breakdown
- Rolling metrics (1, 3, 5, 10 year windows)
- Risk-adjusted returns (Sharpe, Sortino, Calmar, Omega)
- Regime analysis (bull/bear/sideways markets)
- Value at Risk (VaR) and Conditional VaR

## Data Models
All return metrics use `float` for calculations:
- Basic returns: total_return, cagr, annualized_return
- Risk metrics: volatility, max_drawdown, calmar_ratio, ulcer_index
- Risk-adjusted: sharpe_ratio, sortino_ratio, omega_ratio
- Trade stats: win_rate, avg_win, avg_loss, profit_factor, expectancy
- Distribution: skewness, kurtosis, var_95, cvar_95

## API Contracts
- `update(date, capital, trades)`: Update tracker state
- `calculate_metrics() -> PerformanceMetrics`: Returns all metrics
- `get_yearly_breakdown() -> List[YearlyBreakdown]`: Year-by-year stats
- `get_rolling_metrics(windows) -> RollingMetrics`: Rolling window metrics

## Error Handling
- Handles insufficient data gracefully (returns empty/None values)
- Specific exception handling for edge cases
- Safe division with zero checks
- Proper handling of edge cases in statistical calculations

## Performance Considerations
- Uses pandas for efficient time series operations
- Vectorized numpy operations for calculations
- O(n) complexity for most operations
- Memory-efficient equity curve storage

## Testing Strategy
- Test metric calculations with known datasets
- Test drawdown detection and duration calculation
- Test yearly breakdown aggregation
- Test rolling metrics calculation
- Test edge cases (empty data, single data point)
- Test Sharpe/Sortino ratio calculations
- Test VaR/CVaR calculations

## Compliance with BASE_RULES.md
- ✅ FMT-001: Line length ≤ 100
- ✅ FMT-007: No mutable defaults
- ✅ TYP-001: 100% type coverage
- ✅ TYP-002: Modern type hints (Optional[T], List[T])
- ✅ TYP-003: Any used only in Dict[str, Any] context
- ✅ LOG-001: Uses logging module (not print)
- ✅ LOG-003: Appropriate log levels (debug, warning, error)
- ✅ LOG-004: Error logging with context
- ✅ CC-007: Functions are focused and single-purpose

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Audited on 2026-02-07T05:30:00Z - Status: PASSED*
