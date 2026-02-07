# Requirements: services/risk_scaling/risk_scaling_orchestrator.py

## Source File Analysis
- **File Path**: `app/services/risk_scaling/risk_scaling_orchestrator.py`
- **Lines of Code**: 651
- **Language**: Python 3
- **Purpose**: Orchestrates all 4 risk scaling monitors (Hull Chapter 18 compliant)

## Purpose
Orchestrates all risk scaling monitors into unified risk management system:
- Coordinates 4 monitors: Volatility, Sharpe, Loss, Drawdown
- Calculates combined scaling factor
- Adjusts position sizes and stop losses
- Kelly Criterion position sizing
- ATR-based position sizing
- Hull Chapter 18 compliance (Component VaR, EWMA VaR)

## Dependencies
- **Internal**:
  - `app.services.risk_scaling.drawdown_monitor.DrawdownMonitor`
  - `app.services.risk_scaling.loss_monitor.LossMonitor`
  - `app.services.risk_scaling.sharpe_ratio_monitor.SharpeRatioMonitor`
  - `app.services.risk_scaling.volatility_monitor.VolatilityMonitor`
  - `app.services.risk_scaling.models` - Data models
- **External**:
  - `logging` - Structured logging
  - `decimal.ROUND_HALF_UP` - Financial rounding
  - `typing` - Type hints

## Classes/Functions

### RiskScalingOrchestrator
- **Purpose**: Main orchestrator for all risk monitors
- **Key Methods**:
  - `calculate_scaling_factors()` - Calculate all 4 factors
  - `apply_dynamic_scaling()` - Apply scaling to signals
  - `get_scaling_state()` - Complete state snapshot
  - `generate_scaling_report()` - Human-readable report
  - `calculate_position_size()` - Kelly Criterion sizing
  - `calculate_position_size_from_volatility()` - ATR-based sizing
  - `_generate_alert()` - Create risk alert
  - `_generate_summary()` - Generate status summary

## Business Logic

### Combined Scaling Formula
```python
combined_scale = volatility_scale × sharpe_scale × loss_scale × drawdown_scale
```

### Individual Scale Calculations
1. **Volatility Scale** (0.5 to 1.5):
   - Based on ATR vs. average ATR
   - High vol = lower scale (reduce exposure)
   - Low vol = higher scale (increase exposure)

2. **Sharpe Scale** (0.2 to 1.0):
   - Based on rolling Sharpe ratio
   - High Sharpe = higher scale
   - Low Sharpe = lower scale

3. **Loss Scale** (0.5 to 1.0):
   - Based on consecutive losses
   - 0-2 losses = 1.0
   - 3+ losses = decreasing scale

4. **Drawdown Scale** (0.0 to 1.0):
   - Based on portfolio drawdown
   - < 5% = 1.0
   - > 20% = 0.0 (halt trading)

### Kelly Criterion Position Sizing
```python
kelly_fraction = (p × b - q) / b
half_kelly = kelly_fraction / 2
adjusted_size = half_kelly × combined_scale
```
Where:
- p = win rate
- b = win/loss ratio (avg_win / avg_loss)
- q = 1 - p

### ATR-Based Position Sizing
```python
risk_amount = capital × risk_per_trade_pct
stop_distance = atr × atr_multiplier
shares = risk_amount / stop_distance
```

### Signal Adjustment
- If `drawdown_scale = 0`: Reject all signals (trading halted)
- If `combined_scale < 0.2`: Reject (size too small)
- Otherwise: Adjust size by `combined_scale`
- Adjust stop loss by `volatility_scale`

## Data Models
Uses models from `app.services.risk_scaling.models`:
- RiskScalingFactors - All scaling factors
- AdjustedSignal - Signal after scaling
- RiskScalingState - Complete state
- RiskScalingReport - Report

## API Contracts
```python
async def calculate_scaling_factors(
    symbol: str,
    prices: List[PriceData],
    daily_returns: List[Decimal],
    trade_results: Optional[List[TradeResult]] = None,
    equity_curve: Optional[List[Decimal]] = None
) -> RiskScalingFactors

async def apply_dynamic_scaling(
    signal: Dict,
    base_position_size: Decimal,
    stop_loss_price: Optional[Decimal],
    scaling_factors: RiskScalingFactors,
    current_price: Optional[Decimal] = None
) -> AdjustedSignal
```

## Error Handling
- Wraps each monitor calculation in try/except
- Logs errors and returns safe defaults
- Handles division by zero
- Validates inputs

## Performance Considerations
- Sequential monitor calculation (could be parallel)
- O(n) for price/returns iteration
- Efficient Decimal operations
- Minimal state overhead

## Testing Strategy
- Test scaling factor calculations
- Test position sizing with known values
- Test signal adjustment logic
- Test alert generation

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within limits
- FMT-002: Proper imports
- FMT-006: F-strings used
- FMT-007: No mutable defaults

### Type Hints
- TYP-001: All functions typed
- TYP-002: Modern syntax
- TYP-005: Models properly typed

### Async
- ASYNC-001: Proper async functions
- ASYNC-002: Proper await usage

### SOLID Principles
- SOL-001: Single Responsibility (orchestration only)
- SOL-005: Dependency Inversion (injects monitors)

### Clean Code
- CC-001: Descriptive names
- CC-006: Comprehensive error handling
- CC-007: Reasonable function length

### Security
- SEC-007: Input validation on Decimals
- No hardcoded secrets

### Logging
- LOG-001: Structured logging
- LOG-003: Appropriate levels (info, warning)
- LOG-004: Error logging with context

### Financial Best Practices
- Uses Decimal for all calculations
- ROUND_HALF_UP for financial rounding
- Kelly Criterion with half-Kelly safety
- ATR-based position sizing

## Audit Status
**Status**: PASSED**

### Strengths
1. Excellent orchestration of 4 risk monitors
2. Kelly Criterion implementation (best practice)
3. ATR-based position sizing (industry standard)
4. Hull Chapter 18 compliance mentioned
5. Comprehensive error handling
6. Good alert generation
7. Proper Decimal usage throughout
8. Clean async implementation
9. Well-documented formulas
10. Combined scaling factor logic is sound

### Minor Observations
1. Monitor calculations could be parallel (asyncio.gather)
2. Could add more Hull-specific metrics (Component VaR)
3. Some magic numbers could be constants

### No Critical Gaps Found
- All P0 and P1 rules satisfied
- Production-ready risk orchestrator
- Financial best practices followed
- Proper use of Decimal for precision

### Integration Points
- SignalExecutionEngine: Adjust signal sizes
- PositionSizingEngine: Apply Kelly/ATR sizing
- TrailingStopManager: Adjust stop distances
- PortfolioRiskManager: Validate positions

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0081*
*Status: PASSED*
