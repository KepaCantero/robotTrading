# Requirements: services/risk_management_chan.py

## Source File Analysis
- **File Path**: `app/services/risk_management_chan.py`
- **Lines of Code**: 897
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

**Ernest Chan's Risk Management Methodologies** - Implements comprehensive risk management for algorithmic trading.

Based on "Algorithmic Trading: A Practitioner's Guide" by Ernest P. Chan.

**Key Features**:
1. Stop-loss placement strategies (ATR-based, fixed percentage, trailing)
2. Maximum drawdown limits and control
3. Position sizing with risk limits
4. Kelly Criterion application
5. Risk parity and portfolio risk management
6. Value at Risk (VaR) and Conditional VaR
7. Risk of ruin calculations

---

## BASE_RULES Compliance

See [../BASE_RULES.md](../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **TYP-001**: 100% type coverage with type hints
- **CC-006**: Explicit error handling with try/except
- **TRD-002**: Risk validation - all inputs validated
- **TRD-003**: Position limits enforcement
- **RSK-001/RSK-002**: VaR and Expected Shortfall calculations
- **RSK-003**: Drawdown control implementation

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies
- None (standalone risk management module)

### External Dependencies
- `numpy` - Numerical operations
- `pandas` - Data manipulation
- `logging` - Structured logging
- `dataclasses` - Data structures (dataclass decorators)
- `typing` - Type hints (Optional, Tuple, Dict)
- `__future__` - Python 3.7+ compatibility (annotations)

---

## Classes/Functions

### 1. `StopLossResult` (Dataclass)
**Purpose**: Result from stop-loss calculation

**Attributes**:
- `stop_loss_price: float` - Calculated stop-loss price
- `stop_loss_distance: float` - Distance from entry
- `stop_loss_percentage: float` - As percentage
- `method_used: str` - Method used
- `risk_amount: float` - Dollar amount at risk
- `reason: str` - Explanation of calculation

### 2. `PositionSizeResult` (Dataclass)
**Purpose**: Result from position sizing calculation

**Attributes**:
- `shares: int` - Number of shares
- `dollar_amount: float` - Total position value
- `risk_amount: float` - Dollar amount at risk
- `risk_percentage: float` - Risk as % of capital
- `kelly_fraction: Optional[float]` - Kelly fraction (if applicable)
- `method_used: str` - Method used

### 3. `RiskMetrics` (Dataclass)
**Purpose**: Risk metrics for portfolio or strategy

**Attributes**:
- `daily_var_95: float` - Value at Risk at 95% confidence
- `daily_cvar_95: float` - Conditional VaR at 95% confidence
- `max_drawdown: float` - Maximum drawdown
- `max_drawdown_duration: int` - Duration of max DD in days
- `sharpe_ratio: float` - Sharpe ratio
- `sortino_ratio: float` - Sortino ratio
- `calmar_ratio: float` - Calmar ratio
- `risk_of_ruin: float` - Probability of ruin

### 4. `ChanStopLossCalculator` (Class)
**Purpose**: Stop-loss placement strategies per Ernest Chan

**Constants**:
- `DEFAULT_ATR_MULTIPLIER = 2.0` - Recommended 2-3x ATR
- `DEFAULT_FIXED_STOP_PCT = 0.05` - 5% fixed stop

**Methods**:

#### `__init__(atr_multiplier=2.0, fixed_stop_pct=0.05)`
- Initialize calculator with multipliers

#### `calculate_atr_stop_loss(entry_price, atr, direction="long", multiplier=None)`
- **PRIMARY METHOD**: Calculate ATR-based stop loss
- Formula: `stop_loss = entry_price ± (ATR * multiplier)`
- LONG: `stop_loss = entry_price - (ATR * multiplier)`
- SHORT: `stop_loss = entry_price + (ATR * multiplier)`
- Returns StopLossResult with full details
- Falls back to fixed stop on error

#### `calculate_fixed_percentage_stop(entry_price, direction="long", stop_pct=None)`
- Calculate fixed percentage stop loss
- Simpler but less adaptive than ATR
- LONG: `stop_loss = entry_price * (1 - stop_pct)`
- SHORT: `stop_loss = entry_price * (1 + stop_pct)`
- Returns StopLossResult

#### `calculate_trailing_stop(current_price, highest_price_since_entry, atr, direction="long", multiplier=None)`
- Calculate trailing stop loss
- Formula: `stop = highest_price - (ATR * multiplier)`
- Trails upward as price moves in favor
- Returns StopLossResult

### 5. `ChanPositionSizer` (Class)
**Purpose**: Position sizing methods per Ernest Chan

**Constants**:
- `DEFAULT_RISK_PER_TRADE = 0.02` - 1-2% recommended
- `DEFAULT_MAX_POSITION_PCT = 0.25` - 25% max position

**Methods**:

#### `__init__(risk_per_trade=0.02, max_position_pct=0.25)`
- Initialize sizer with risk parameters

#### `calculate_risk_based_position(capital, entry_price, stop_loss_price, risk_per_trade=None)`
- **PRIMARY METHOD**: Calculate position size based on risk
- Ernest Chan's formula:
  ```
  risk_amount = capital * risk_per_trade
  shares = risk_amount / (entry_price - stop_loss_price)
  ```
- Enforces max_position_pct limit
- Returns PositionSizeResult

#### `calculate_kelly_position(capital, entry_price, stop_loss_price, win_rate, avg_win, avg_loss, kelly_fraction=0.5)`
- Calculate position size using Kelly Criterion
- Ernest Chan's formula:
  ```
  f* = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
  ```
- Uses half-Kelly for safety (default)
- Enforces max_position_pct limit
- Returns PositionSizeResult with kelly_fraction

#### `calculate_volatility_adjusted_position(capital, entry_price, stop_loss_price, volatility, target_risk=0.02)`
- Calculate position size adjusted for volatility
- Higher volatility → smaller position
- Lower volatility → larger position
- Targets constant risk across trades
- Returns PositionSizeResult

### 6. `ChanDrawdownController` (Class)
**Purpose**: Maximum drawdown controller per Ernest Chan

**Constants**:
- `DEFAULT_MAX_DRAWDOWN = 0.25` - 20-25% recommended
- `DRAWDOWN_REDUCTION_LEVELS` - Position reduction schedule

**Methods**:

#### `__init__(max_drawdown=0.25, peak_equity=100000.0)`
- Initialize controller with drawdown limit

#### `update_equity(new_equity)`
- Update equity and track peak
- Automatically updates peak if new high

#### `get_current_drawdown()`
- Calculate current drawdown
- Formula: `(peak_equity - current_equity) / peak_equity`

#### `should_halt_trading()`
- Check if trading should be halted
- Returns True if max_drawdown exceeded
- Logs warning when halted

#### `get_position_size_multiplier()`
- Calculate position size multiplier based on drawdown
- Returns 0.0 if trading halted
- Returns reduced multiplier if drawdown high:
  - 10% DD → 0.75x
  - 15% DD → 0.50x
  - 20% DD → 0.25x

#### `calculate_risk_of_ruin(win_rate, avg_win, avg_loss, capital_units=100)`
- Calculate risk of ruin per Ernest Chan
- Formula approximation:
  ```
  RoR = ((1 - edge) / (1 + edge))^capital_units
  ```
  where edge = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
- Returns probability of ruin (0-1)

### 7. `ChanRiskMetrics` (Class)
**Purpose**: Risk metrics calculator per Ernest Chan

**Methods**:

#### `__init__(confidence_level=0.95)`
- Initialize with confidence level

#### `calculate_all_metrics(returns, equity_curve=None, risk_free_rate=0.02)`
- **PRIMARY METHOD**: Calculate all risk metrics
- Returns RiskMetrics with:
  - VaR and CVaR
  - Max drawdown and duration
  - Sharpe, Sortino, Calmar ratios
  - Risk of ruin

#### `_calculate_var(returns, confidence)`
- Calculate Value at Risk
- Returns percentile of returns

#### `_calculate_cvar(returns, confidence)`
- Calculate Conditional VaR (Expected Shortfall)
- Returns average of returns below VaR

#### `_calculate_max_drawdown(equity_curve)`
- Calculate maximum drawdown and duration
- Returns (max_dd, duration)

#### `_calculate_max_drawdown_from_returns(returns)`
- Calculate max drawdown from returns series
- Uses cumulative returns

#### `_calculate_sharpe(returns, risk_free_rate)`
- Calculate Sharpe ratio
- Formula: `mean(excess_returns) / std(excess_returns) * sqrt(252)`

#### `_calculate_sortino(returns, risk_free_rate)`
- Calculate Sortino ratio
- Uses downside deviation instead of std

### 8. Convenience Functions

#### `calculate_optimal_stop_loss(entry_price, atr, direction="long", method="atr")`
- Convenience function for stop loss calculation
- Routes to appropriate method

#### `calculate_optimal_position_size(capital, entry_price, stop_loss_price, method="risk_based", **kwargs)`
- Convenience function for position sizing
- Routes to appropriate method

---

## Business Logic

### Stop-Loss Strategies

**ATR-Based (Recommended)**:
- Adaptive to volatility
- Default: 2x ATR (range: 1-3x)
- LONG: `entry_price - (ATR * 2)`
- SHORT: `entry_price + (ATR * 2)`

**Fixed Percentage**:
- Simple but less adaptive
- Default: 5%
- LONG: `entry_price * 0.95`
- SHORT: `entry_price * 1.05`

**Trailing Stop**:
- Locks in profits as price moves favorably
- LONG: `highest_price - (ATR * 2)`
- SHORT: `lowest_price + (ATR * 2)`

### Position Sizing Strategies

**Risk-Based**:
- Constant risk per trade (default 2%)
- Formula: `shares = (capital * 0.02) / stop_distance`
- Enforces 25% max position

**Kelly Criterion**:
- Optimal growth sizing
- Uses half-Kelly for safety
- Enforces 25% max position
- Recommendation:
  - Kelly <= 0: AVOID
  - Kelly < 0.02: REDUCE
  - Kelly >= 0.02: BUY

**Volatility-Adjusted**:
- Adjusts size based on volatility
- High vol → smaller position
- Low vol → larger position
- Targets constant risk

### Drawdown Control

**Reduction Schedule**:
- At 10% DD: Reduce to 75% size
- At 15% DD: Reduce to 50% size
- At 20% DD: Reduce to 25% size
- At 25% DD: Halt trading

**Risk of Ruin**:
- Estimates probability of losing all capital
- Uses edge and capital units
- High edge + many units = low RoR

### Risk Metrics

**Value at Risk (VaR)**:
- Maximum expected loss at confidence level
- 95% VaR = 5th percentile of returns

**Conditional VaR (CVaR)**:
- Average loss beyond VaR
- Also called Expected Shortfall
- More informative than VaR

**Sharpe Ratio**:
- Risk-adjusted return
- Formula: `(mean_return - risk_free) / std_return * sqrt(252)`

**Sortino Ratio**:
- Uses downside deviation only
- Penalizes only downside volatility

**Calmar Ratio**:
- Annual return / max_drawdown
- Higher is better

---

## Data Models

### Stop Loss Result
```python
@dataclass
class StopLossResult:
    stop_loss_price: float
    stop_loss_distance: float
    stop_loss_percentage: float
    method_used: str
    risk_amount: float
    reason: str
```

### Position Size Result
```python
@dataclass
class PositionSizeResult:
    shares: int
    dollar_amount: float
    risk_amount: float
    risk_percentage: float
    kelly_fraction: Optional[float] = None
    method_used: str = ""
```

### Risk Metrics
```python
@dataclass
class RiskMetrics:
    daily_var_95: float
    daily_cvar_95: float
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    risk_of_ruin: float
```

---

## API Contracts

### Stop Loss Calculation
```python
calculator = ChanStopLossCalculator(atr_multiplier=2.0)

# ATR-based
result = calculator.calculate_atr_stop_loss(
    entry_price=100.0,
    atr=2.5,
    direction="long"
)
print(result.stop_loss_price)  # 95.0

# Trailing stop
result = calculator.calculate_trailing_stop(
    current_price=110.0,
    highest_price_since_entry=110.0,
    atr=2.5,
    direction="long"
)
print(result.stop_loss_price)  # 105.0
```

### Position Sizing
```python
sizer = ChanPositionSizer(risk_per_trade=0.02)

# Risk-based
result = sizer.calculate_risk_based_position(
    capital=100000,
    entry_price=100.0,
    stop_loss_price=95.0
)
print(result.shares)  # 400
print(result.risk_amount)  # 2000 (2% of 100k)

# Kelly
result = sizer.calculate_kelly_position(
    capital=100000,
    entry_price=100.0,
    stop_loss_price=95.0,
    win_rate=0.55,
    avg_win=5.0,
    avg_loss=3.0
)
print(result.kelly_fraction)  # e.g., 0.10
```

### Drawdown Control
```python
controller = ChanDrawdownController(max_drawdown=0.25)

controller.update_equity(90000)  # 10% drawdown
multiplier = controller.get_position_size_multiplier()
print(multiplier)  # 0.75

controller.update_equity(75000)  # 25% drawdown
should_halt = controller.should_halt_trading()
print(should_halt)  # True
```

### Risk Metrics
```python
metrics_calc = ChanRiskMetrics()

risk_metrics = metrics_calc.calculate_all_metrics(
    returns=returns_series,
    equity_curve=equity_series,
    risk_free_rate=0.02
)

print(f"VaR 95%: {risk_metrics.daily_var_95:.2%}")
print(f"CVaR 95%: {risk_metrics.daily_cvar_95:.2%}")
print(f"Max DD: {risk_metrics.max_drawdown:.2%}")
print(f"Sharpe: {risk_metrics.sharpe_ratio:.2f}")
```

---

## Error Handling

### Calculation Errors

When calculations fail:
- Logged with error level
- Return sensible defaults
- Don't crash the system

**Example** (stop loss calculation):
```python
try:
    # Calculate stop loss
    result = ...
except (ValueError, TypeError) as e:
    logger.error(f"Error calculating ATR stop loss: {e}")
    # Return fixed stop as fallback
    return StopLossResult(
        stop_loss_price=entry_price * 0.95,
        ...
        reason="Calculation error, using fixed stop"
    )
```

### Division by Zero

Handled in calculations:
- Check for zero denominator
- Return sensible defaults
- Log warnings

### Invalid Inputs

- Zero/negative prices: Handled with defaults
- Invalid directions: Raise ValueError
- Out-of-range percentages: Cap at reasonable limits

---

## Performance Considerations

1. **No External I/O**: All calculations in-memory
2. **Vectorized Operations**: Uses NumPy for efficiency
3. **Simple Formulas**: Fast computation
4. **No Database Queries**: Standalone calculations

---

## Testing Strategy

### Unit Tests Required

1. **Stop Loss Calculator**:
   - Test ATR-based for LONG/SHORT
   - Test fixed percentage for LONG/SHORT
   - Test trailing stop
   - Test error handling

2. **Position Sizer**:
   - Test risk-based sizing
   - Test Kelly calculation
   - Test volatility-adjusted sizing
   - Test max position capping

3. **Drawdown Controller**:
   - Test drawdown calculation
   - Test halt condition
   - Test position multiplier
   - Test risk of ruin

4. **Risk Metrics**:
   - Test VaR calculation
   - Test CVaR calculation
   - Test max drawdown
   - Test Sharpe/Sortino/Calmar

### Edge Cases to Test

1. Zero capital/prices
2. Zero volatility
3. Zero risk_per_share
4. Negative Kelly (edge < 0)
5. Perfect win rate (win_rate = 1)
6. Zero win rate

### Test Coverage Target: >85%

---

## Configuration

### Default Parameters

```yaml
risk_management:
  # Stop Loss
  atr_multiplier: 2.0  # 2-3x recommended
  fixed_stop_pct: 0.05  # 5%

  # Position Sizing
  risk_per_trade: 0.02  # 1-2% recommended
  max_position_pct: 0.25  # 25% max
  kelly_fraction: 0.5  # Half-Kelly

  # Drawdown Control
  max_drawdown: 0.25  # 20-25% recommended

  # Drawdown Reduction
  reduction_levels:
    0.10: 0.75  # At 10% DD, reduce to 75%
    0.15: 0.50  # At 15% DD, reduce to 50%
    0.20: 0.25  # At 20% DD, reduce to 25%

  # Risk Metrics
  confidence_level: 0.95
  risk_free_rate: 0.02
```

---

## Mathematical References

### Kelly Criterion

From **Ernest Chan, "Algorithmic Trading"**:

```
f* = (bp - q) / b

Where:
- f* = optimal fraction of capital
- b = avg_win / avg_loss (odds)
- p = win_rate
- q = 1 - win_rate
```

Rewritten:
```
Kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
```

### Risk of Ruin

Approximation:
```
RoR = ((1 - edge) / (1 + edge))^capital_units

Where:
- edge = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
- capital_units = account / risk_per_trade
```

### Half-Kelly

```
Half-Kelly = Kelly * 0.5
```

**Why Half-Kelly?**
- Reduces volatility
- Decreases drawdown
- Most of the growth with less risk

---

## Trading Applications

### Pre-Trade Risk Check

1. Calculate stop loss
2. Calculate position size
3. Check against max position size
4. Check drawdown controller
5. Execute if all checks pass

### Portfolio Risk Management

1. Calculate portfolio VaR
2. Calculate CVaR
3. Monitor drawdown
4. Reduce positions if drawdown high
5. Halt if max drawdown exceeded

### Strategy Evaluation

1. Calculate Sharpe ratio
2. Calculate Sortino ratio
3. Calculate Calmar ratio
4. Calculate max drawdown
5. Calculate risk of ruin
6. Only trade if metrics acceptable

---

## Security Considerations

1. **No External Calls**: Pure calculations
2. **No Secrets**: No API keys needed
3. **Input Validation**: All inputs validated
4. **Error Messages**: Don't leak sensitive info

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0105
**Violations**: 0
**Notes**: Excellent implementation of Ernest Chan's risk management methodologies. Clean code with comprehensive type hints. Proper error handling throughout with sensible fallbacks. Mathematical formulas well-documented. Half-Kelly safety approach demonstrates practical trading knowledge. Drawdown controller with position reduction is well-designed.

---
