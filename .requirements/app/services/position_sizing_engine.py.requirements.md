# Requirements: services/position_sizing_engine.py

## Source File Analysis
- **File Path**: `app/services/position_sizing_engine.py`
- **Lines of Code**: 861
- **Status**: PASSED
- **Audit Date**: 2026-02-07

---

## Purpose

Implements **Ernest Chan's position sizing methodologies** with ATR-based dynamic stop loss and Kelly Criterion optimization.

**Key Features**:
1. ATR-based dynamic stop loss (TASK-IND-2)
2. Kelly Criterion position sizing with Half-Kelly safety (RULE-01-1.9)
3. Meta-labeling position sizing (López de Prado Chapters 3 & 10)
4. Configuration-driven via centralized config

---

## BASE_RULES Compliance

See [../BASE_RULES.md](../BASE_RULES.md) for universal rules.

### Critical Rules Applied
- **TYP-001**: 100% type coverage with comprehensive type hints
- **CC-006**: Explicit error handling with ValueError for invalid inputs
- **TRD-002**: Risk validation - all inputs validated before calculation
- **TRD-004**: Audit trail - calculations logged appropriately
- **CFG-002**: Uses centralized configuration (strategy_config_loader)

### Audit Status: **PASSED**

---

## Dependencies

### Internal Dependencies
- `app.core.config.strategy_config_loader.get_strategy_config` - Centralized configuration (optional)
- `app.backtesting.labeling.bet_sizing` - ML-based bet sizing (lazy import)
- `app.backtesting.labeling.meta_labeling` - Meta-labeling framework (lazy import)

### External Dependencies
- `decimal.Decimal` - Precise financial calculations
- `numpy` - Array operations for meta-labeling
- `logging` - Structured logging
- `typing` - Type hints (Dict, Optional, Union)
- `math` - NaN and infinity checks

---

## Classes/Functions

### 1. `PositionSizingEngine` (Class)
**Purpose**: Calculates dynamic stop loss and position sizing based on ATR and Kelly Criterion

**Key Methods**:

#### `__init__(atr_multiplier: Optional[float] = None)`
- Initialize calculator with ATR multiplier
- Loads from centralized config if available (2.0 default)

#### `calculate_stop_loss_price(...)`
- **TASK-IND-2**: Calculate dynamic stop loss price
- Priority: ATR-based > percentage-based > None
- Args: entry_price, direction, atr, stop_loss_pct
- Returns: Stop loss price or None

```python
# ATR-based: stop_distance = ATR * multiplier
# LONG: stop_loss = entry_price - stop_distance
# SHORT: stop_loss = entry_price + stop_distance
```

#### `calculate_position_size_from_atr(...)`
- **TASK-IND-4**: Calculate position size based on ATR
- Formula: `risk_per_trade = 2% capital / (ATR * 2)`
- Args: capital, risk_per_trade_pct, entry_price, atr
- Validates: stop distance <= 20% of entry price (sanity check)
- Returns: Number of shares or None

#### `calculate_kelly_position_size(...)`
- **RULE-01-1.9**: Calculate Kelly Criterion position size
- Conservative constraints per Ernest Chan:
  - Half-Kelly: Reduces volatility while maintaining growth
  - Max position: 25% of capital
  - Min position: 0% (negative Kelly = don't trade)
- Formula: `Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win`
- Comprehensive input validation:
  - NaN checking
  - Infinity checking
  - Range validation (win_rate: 0-1, avg_win > 0, avg_loss > 0)
- Returns: Dict with kelly_fraction, half_kelly_fraction, position_percentage, position_value, recommendation

#### `calculate_kelly_from_backtest(...)`
- Convenience method extracting metrics from backtest results
- Handles win_rate in percentage form (0-100) or decimal (0-1)
- Fallback to 2% rule when metrics unavailable
- Args: performance_metrics dict, capital
- Returns: Same as calculate_kelly_position_size

### 2. `MetaLabelingPositionSizer` (Class)
**Purpose**: Use meta-labeling probabilities for position sizing (López de Prado)

**Key Methods**:

#### `__init__(config: Optional[Dict] = None)`
- Initialize with configuration
- Lazy import of ML modules (bet_sizing, meta_labeling)
- Graceful fallback when ML unavailable

#### `calculate_position_size(...)`
- Calculate position sizes using meta-labeling probabilities
- Uses meta-model confidence to size positions
- Args: signals, meta_proba, expected_returns, capital
- Validates: signals and meta_proba have same length
- Returns: Position sizes array

#### `calculate_position_size_with_meta_model(...)`
- End-to-end position sizing with trained meta-model
- Args: X (features), primary_predictions, meta_model, expected_returns, capital
- Returns: Position sizes array

#### `fit_meta_model(...)`
- Train meta-labeling model on training data
- Returns: Training results with metrics

#### `_fallback_sizing(...)`
- Fallback when ML modules unavailable
- Simple confidence-based sizing

### 3. `PositionSizingEngineWithMetaLabeling` (Class)
**Purpose**: Extended position sizing combining traditional and ML methods

**Key Methods**:

#### `calculate_meta_labeling_sizes(...)`
- Calculate using meta-labeling approach

#### `calculate_hybrid_sizes(...)`
- Combine meta-labeling + Kelly approach
- Meta-labeling for filtering
- Kelly for sizing (optimal position size)
- Returns: Dict with position_sizes, meta_sizes, kelly_fraction, filter_mask

---

## Business Logic

### ATR-Based Stop Loss (TASK-IND-2)

**Formula**: `stop_loss_distance = ATR * multiplier`

**Advantages**:
- Adaptive to volatility
- Higher volatility = wider stops
- Lower volatility = tighter stops

**Default Multiplier**: 2.0 (from centralized config)

### Kelly Criterion (RULE-01-1.9)

**Raw Kelly Formula**:
```
Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
```

**Half-Kelly**:
```
Half-Kelly = Raw Kelly * 0.5
```

**Capping**:
```
Capped Kelly = max(0, min(Half-Kelly, 0.25))
```

**Recommendations**:
- `Kelly <= 0`: AVOID trade (negative expectancy)
- `Kelly < 0.02`: REDUCE position (marginal edge)
- `Kelly >= 0.02`: BUY (favorable edge)

### Meta-Labeling Position Sizing (López de Prado)

**Concept**:
1. Primary model predicts DIRECTION (buy/sell/hold)
2. Meta model predicts whether primary will be CORRECT
3. Position size based on meta-model confidence

**Benefits**:
- Separates signal direction from position sizing
- Reduces overbetting on low-confidence signals
- Increases position size on high-confidence signals

### Risk Per Trade Calculation

**Formula**: `shares = risk_amount / stop_distance`

Where:
- `risk_amount = capital * risk_per_trade_pct` (typically 2%)
- `stop_distance = ATR * multiplier` (for ATR-based)
- `stop_distance = entry_price * stop_pct` (for percentage-based)

---

## Data Models

### Kelly Position Size Result
```python
{
    "kelly_fraction": Decimal,      # Raw Kelly (-0.1 to 1.0+)
    "half_kelly_fraction": Decimal, # Half-Kelly capped at 0.25
    "position_percentage": Decimal, # As % of capital
    "position_value": Decimal,      # Dollar amount (if capital provided)
    "recommendation": str,          # "BUY", "REDUCE", or "AVOID"
}
```

### Meta-Labeling Config
```python
{
    "bet_sizing_method": str,      # 'meta_kelly', 'meta_probability', etc.
    "confidence_threshold": float, # Minimum confidence (default: 0.5)
    "max_bet_size": float,         # Maximum position size (default: 1.0)
    "min_bet_size": float,         # Minimum position size (default: 0.0)
}
```

---

## API Contracts

### Stop Loss Calculation
```python
engine = PositionSizingEngine(atr_multiplier=2.0)

# ATR-based
stop_loss = engine.calculate_stop_loss_price(
    entry_price=Decimal("100.0"),
    direction="buy",
    atr=2.5
)
# Returns: Decimal("95.0")

# Percentage-based fallback
stop_loss = engine.calculate_stop_loss_price(
    entry_price=Decimal("100.0"),
    direction="sell",
    stop_loss_pct=0.05
)
# Returns: Decimal("105.0")
```

### Position Sizing from ATR
```python
shares = engine.calculate_position_size_from_atr(
    capital=Decimal("100000"),
    entry_price=Decimal("100"),
    atr=Decimal("2.0")
)
# Returns: Decimal("1000")  # Risk amount $2000 / $4 stop distance
```

### Kelly Criterion
```python
result = engine.calculate_kelly_position_size(
    win_rate=0.55,
    avg_win=100.0,
    avg_loss=75.0,
    capital=Decimal("10000")
)
# Returns:
# {
#     "kelly_fraction": Decimal("0.10"),
#     "half_kelly_fraction": Decimal("0.05"),
#     "position_percentage": Decimal("5.0"),
#     "position_value": Decimal("500"),
#     "recommendation": "BUY"
# }
```

### Meta-Labeling
```python
sizer = MetaLabelingPositionSizer()

sizes = sizer.calculate_position_size(
    signals=np.array([1, -1, 1, 0]),
    meta_proba=np.array([0.7, 0.6, 0.8, 0.4]),
    expected_returns=np.array([0.02, -0.015, 0.025, 0.0]),
    capital=Decimal("10000")
)
```

---

## Error Handling

### Input Validation

**calculate_kelly_position_size**:
- Type checking (must be numeric)
- NaN checking (using `math.isnan`)
- Infinity checking (using `math.isinf`)
- Range validation (win_rate 0-1, positive avg_win/avg_loss)
- Raises `ValueError` with descriptive message

**calculate_stop_loss_price**:
- Entry price must be > 0
- Direction must be "buy" or "sell"
- Returns None for invalid inputs (graceful degradation)

**calculate_position_size_from_atr**:
- Capital must be > 0
- Entry price must be > 0
- Sanity check: stop distance <= 20% of entry price
- Returns None for invalid inputs

### Error Messages
- Clear, descriptive error messages
- Include actual values received
- Suggest valid ranges

### Logging
- Warning logs for negative Kelly (AVOID recommendation)
- Info logs for marginal edge (REDUCE recommendation)
- Debug logs for favorable Kelly (BUY recommendation)
- Warning logs for stop distance capping

---

## Performance Considerations

1. **Decimal Precision**: All financial calculations use Decimal for precision
2. **Lazy Imports**: ML modules imported only when needed
3. **Configuration Loading**: Config loaded once at initialization
4. **No External I/O**: All calculations are in-memory
5. **Vectorized Operations**: Meta-labeling uses NumPy for efficiency

---

## Testing Strategy

### Unit Tests Required

1. **PositionSizingEngine**:
   - Test ATR-based stop loss for LONG/SHORT
   - Test percentage-based stop loss
   - Test position sizing from ATR
   - Test Kelly calculation with various inputs
   - Test Kelly edge cases (NaN, infinity, negative)
   - Test Kelly recommendations (BUY/REDUCE/AVOID)
   - Test fallback to 2% rule

2. **MetaLabelingPositionSizer**:
   - Test position size calculation
   - Test meta-model integration
   - Test fallback sizing
   - Test confidence threshold

3. **PositionSizingEngineWithMetaLabeling**:
   - Test hybrid sizing
   - Test Kelly cap application

### Edge Cases to Test

1. Zero/negative values for all inputs
2. NaN and infinity values
3. Win rate outside 0-1 range
4. Very high volatility (ATR > 20% of price)
5. Very low capital (position size capping)
6. Missing configuration (fallback to defaults)

### Integration Tests

1. Test with real config loader
2. Test ML module integration (when available)
3. Test backtest result extraction

### Test Coverage Target: >85%

---

## Configuration

### Centralized Configuration (Optional)

```yaml
# config/risk_management.yaml
atr_multipliers:
  default_stop: 2.0
  tight: 1.0
  wide: 3.0

position_sizing:
  risk_per_trade:
    default: 0.02  # 2%
    conservative: 0.01
    aggressive: 0.03

kelly:
  half_kelly_multiplier: 0.5
  max_position: 0.25  # 25%
  min_recommendation_threshold: 0.02

meta_labeling:
  bet_sizing_method: "meta_kelly"
  confidence_threshold: 0.5
  max_bet_size: 1.0
  min_bet_size: 0.0
```

### Defaults (when config unavailable)

- ATR multiplier: 2.0
- Risk per trade: 2%
- Half-Kelly: 50% of full Kelly
- Max position: 25% of capital
- Confidence threshold: 0.5

---

## Mathematical References

### Kelly Criterion Derivation

From **Ernest Chan, "Algorithmic Trading"**:

```
f* = (bp - q) / b

Where:
- f* = optimal fraction of capital to wager
- b = odds received on the wager (avg_win / avg_loss)
- p = probability of winning (win_rate)
- q = probability of losing (1 - win_rate)
```

Rewritten in our notation:
```
Kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
```

### Half-Kelly Safety

**Why Half-Kelly?**
- Reduces volatility of returns
- Decreases probability of ruin
- Most of the growth with less drawdown
- Recommended by Ernest Chan for practical trading

### Meta-Labeling

From **López de Prado, "Advances in Financial Machine Learning"**:
- Chapter 3: Meta-Labeling
- Chapter 10: Bet Sizing

Key insight: Separate **when to trade** (primary model) from **how much to trade** (meta model).

---

## Trading-Specific Compliance

### TRD-002: Risk Validation
- All inputs validated before calculation
- Sanity checks on stop distances
- Position size capping at 25%

### TRD-006: Transaction Costs
- Position sizing accounts for risk (stop distance)
- Can incorporate transaction costs in avg_loss calculation

### Ernest Chan Best Practices
- Half-Kelly for safety
- 25% maximum position size
- ATR-based adaptive stops
- 2% risk per trade default

---

## Security Considerations

1. **No Hardcoded Values**: Uses centralized config
2. **Input Validation**: All inputs validated
3. **Type Safety**: Comprehensive type hints
4. **Error Messages**: Don't leak sensitive information

---

## Audit Status: **PASSED**

**Date**: 2026-02-07
**Auditor**: GAP Audit Batch 0103
**Violations**: 0
**Notes**: Excellent implementation of Ernest Chan's methodologies with comprehensive input validation, clear mathematical documentation, and proper error handling. The Half-Kelly safety approach and 25% cap show understanding of practical trading constraints. Meta-labeling integration demonstrates advanced ML-based position sizing.

---
