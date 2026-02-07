# Requirements: backtesting/metrics.py

## Source File Analysis
- **File Path**: `app/backtesting/metrics.py`
- **Lines of Code**: 1320
- **Module**: Backtesting - Performance Metrics

## Purpose
Comprehensive performance metrics calculator for backtesting.

Calculates:
- Basic metrics: CAGR, Sharpe ratio, Sortino ratio, Max Drawdown
- Trade statistics: Win Rate, Profit Factor, Expectancy
- Risk-adjusted returns: Calmar ratio, Omega ratio, Ulcer index
- Advanced metrics: Skewness, Kurtosis, VaR, CVaR
- López de Prado metrics: Stability, Concentration, Turnover-adjusted Sharpe
- Imbalanced classification metrics: F1 Score, MCC

## Dependencies

### External Dependencies
- `numpy` - Numerical computations
- `empyrical` (optional) - Industry-standard financial metrics
- `logging` - Structured logging
- `decimal` - Precise financial calculations
- `datetime` - Time calculations
- `sklearn` - Classification metrics (F1, MCC)
- `scipy` - Statistical functions

### Internal Dependencies
- `app.backtesting.advanced_metrics.AdvancedMetricsCalculator`
- `app.backtesting.lopez_de_prado_metrics` - All López de Prado classes
- `app.backtesting.models.PerformanceMetrics`, `app.backtesting.models.Trade`

## Classes/Functions

### Main Classes
- `MetricsCalculator` - Main performance metrics calculator
  - `calculate_all_metrics()` - Calculate all performance metrics
  - `calculate_cagr()` - Compound Annual Growth Rate
  - `_calculate_sharpe_ratio()` - Sharpe with empyrical fallback
  - `_calculate_sortino_ratio()` - Sortino with downside deviation
  - `_calculate_risk_reward_ratio()` - Average win/loss ratio
  - `_calculate_max_drawdown()` - Maximum peak-to-trough decline

- `LopezDePradoMetricsCalculator` - López de Prado advanced metrics
  - `combine_strategy_sharpes()` - Combine multiple strategies
  - `validate_portfolio_stability()` - Portfolio stability analysis
  - `calculate_turnover_adjusted_metrics()` - Turnover-adjusted Sharpe
  - `analyze_portfolio_concentration()` - HHI, Gini, Entropy
  - `generate_comprehensive_report()` - Complete LPd metrics report

### Standalone Functions
- `calculate_profit_factor()` - Gross profit / gross loss
- `calculate_expectancy()` - Expected value per trade
- `calculate_expectancy_with_confidence()` - Expectancy with CI
- `calculate_f1_score()` - F1 for imbalanced classification
- `calculate_matthews_corrcoef()` - MCC for imbalanced data
- `calculate_classification_metrics_imbalanced()` - Comprehensive metrics
- `calculate_imbalanced_metrics_from_trades()` - Trade-based metrics
- `create_lopez_de_prado_calculator()` - Factory function

## Business Logic

### Sharpe Ratio Calculation
1. Uses empyrical if available (industry standard)
2. Falls back to manual calculation: (Annualized Return - RF) / Annualized Std
3. Handles NaN and Inf values
4. Daily risk-free rate: annual_rate / 252

### Sortino Ratio Calculation
1. Uses empyrical if available
2. Manual: Uses downside deviation (not standard deviation)
3. Target return: daily risk-free rate
4. Penalizes only returns below target

### Expectancy Calculation
```
Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
```
- Positive: Strategy profitable per trade
- Negative: Strategy loses money per trade
- Zero: Break-even (before costs)

### López de Prado Metrics Integration
- Sharpe combination: optimal, hierarchical, spectral methods
- Portfolio stability: turnover, autocorrelation, drift analysis
- Concentration: HHI, effective N, Gini, Shannon entropy
- Turnover-adjusted: Transaction cost impact on Sharpe

## Data Models

### PerformanceMetrics (Pydantic model)
All standard backtesting metrics including:
- Total trades, win rate, P&L metrics
- Risk metrics: max drawdown, Sharpe, Sortino
- Advanced: Calmar, Omega, Ulcer, VaR, CVaR

### Trade (Pydantic model)
Individual trade with entry/exit times, P&L, status

## API Contracts

### Input Validation
- `initial_capital` must be positive (raises ValueError)
- `start_date` must be before `end_date`
- Handles empty trades gracefully (returns empty metrics)

### Return Values
- All metrics return `Decimal` for financial precision
- Optional metrics return `None` if insufficient data
- `PerformanceMetrics` object with all calculated values

## Error Handling
- Empty trades: returns empty metrics (no exception)
- Invalid initial_capital: raises ValueError with message
- empyrical not available: falls back to manual calculation
- Calculation errors: logs error, returns None or 0

## Performance Considerations
- Uses Decimal for all financial calculations (precision)
- empyrical used when available (C-accelerated)
- NumPy vectorization for array operations
- Fallback implementations for graceful degradation

## Testing Strategy
- Unit tests for each metric calculation
- Validate against empyrical reference implementation
- Edge cases: empty trades, zero volatility, negative capital
- Test expectancy calculation with various win/loss patterns

## Critical Rules (BASE_RULES.md)

### Compliance Status: ✅ PASSED

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| R099 | Absolute imports | ✅ PASS | All imports are absolute |
| R104 | No bare except | ✅ PASS | Uses specific exceptions |
| R105 | No print statements | ✅ PASS | Uses `logger` throughout |
| R108 | Exception handling | ✅ PASS | Comprehensive error handling |
| R110 | Docstrings | ✅ PASS | Google-style docstrings |
| R111 | No circular imports | ✅ PASS | Well-structured dependency tree |

### Notes
- Spanish comments in code (lines 120, 123, 387, 440, 668) - acceptable for international project
- Graceful handling of optional dependencies (empyrical)
- Uses legacy type hint syntax - acceptable for compatibility
- `Any` types used appropriately for Dict returns

## Trading-Specific Rules Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| TRD-006 | Transaction costs | ✅ PASS | Turnover-adjusted metrics implemented |
| TRD-007 | Annualization | ✅ PASS | TRADING_DAYS = 252 documented |
| BT-004 | Realistic costs | ✅ PASS | Transaction costs in turnover analysis |
| RSK-001 | VaR calculation | ✅ PASS | var_95 calculated |
| RSK-002 | Expected Shortfall | ✅ PASS | cvar_95 calculated |

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:55:00Z |
| **Audit Status** | PASSED |
| **Auditor** | Ralph GAP Audit Automation |
| **Violations** | 0 critical violations |

---
*Generated on 2026-02-07T05:55:00Z*
