# signal_generator.py

## Purpose
Domain service for generating trading signals based on technical indicators (MA crossover, RSI, Bollinger Bands, MACD) with confidence scoring and signal combination.

---

## Type Definitions / Data Classes

### SignalType (Enum)
```python
BUY = "buy"      # Long entry signal
SELL = "sell"    # Short entry or exit signal
HOLD = "hold"    # No action
CLOSE = "close"  # Close position
```

### SignalStrength (Enum)
```python
WEAK = "weak"
MODERATE = "moderate"
STRONG = "strong"
VERY_STRONG = "very_strong"
```

### Signal (dataclass)
```python
symbol: str                      # Trading symbol
signal_type: SignalType          # BUY, SELL, HOLD, CLOSE
strength: SignalStrength         # Signal strength level
confidence: Decimal              # Confidence 0-1
target_price: Optional[Decimal]  # Target price
stop_loss: Optional[Decimal]     # Stop loss level
take_profit: Optional[Decimal]   # Take profit level
quantity: Optional[Decimal]      # Suggested quantity
reason: str                      # Signal explanation
metadata: Dict[str, Any]         # Additional context
```

**Properties:**
- is_buy: True if signal_type == BUY
- is_sell: True if signal_type == SELL
- is_actionable: True if BUY or SELL

### IndicatorValues (dataclass)
```python
price: Decimal                    # Current price
sma_20: Optional[Decimal]         # 20-period SMA
sma_50: Optional[Decimal]         # 50-period SMA
ema_12: Optional[Decimal]         # 12-period EMA
ema_26: Optional[Decimal]         # 26-period EMA
rsi: Optional[Decimal]            # RSI indicator
macd: Optional[Decimal]           # MACD line
macd_signal: Optional[Decimal]    # MACD signal line
bollinger_upper: Optional[Decimal] # Bollinger upper band
bollinger_lower: Optional[Decimal] # Bollinger lower band
volume: Optional[Decimal]         # Trading volume
volume_ma: Optional[Decimal]      # Volume MA
```

### SignalGenerator (class)
```python
_confidence_threshold: Decimal  # Minimum confidence for actionable signals
```

---

## Function Signatures (Contracts)

### `SignalGenerator.__init__(confidence_threshold)`
**Pre:** confidence_threshold in [0, 1]
**Post:** Generator initialized with threshold
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_ma_crossover_signal(indicators, symbol) -> Signal`
**Pre:** indicators contains sma_20, sma_50, price
**Post:** Returns Signal based on MA crossover
**Raises:** None (returns HOLD if insufficient data)
**Retry:** No
**Side Effects:** None

### `generate_rsi_signal(indicators, symbol) -> Signal`
**Pre:** indicators contains rsi
**Post:** Returns Signal: BUY if RSI < 30, SELL if RSI > 70
**Raises:** None (returns HOLD if RSI unavailable)
**Retry:** No
**Side Effects:** None

### `generate_bollinger_signal(indicators, symbol) -> Signal`
**Pre:** indicators contains bollinger_upper, bollinger_lower, price
**Post:** Returns Signal: BUY near lower band, SELL near upper band
**Raises:** None (returns HOLD if unavailable)
**Retry:** No
**Side Effects:** None

### `generate_macd_signal(indicators, symbol) -> Signal`
**Pre:** indicators contains macd, macd_signal
**Post:** Returns Signal based on MACD crossover
**Raises:** None (returns HOLD if unavailable)
**Retry:** No
**Side Effects:** None

### `combine_signals(signals, symbol) -> Signal`
**Pre:** signals is list of Signal objects
**Post:** Returns consensus Signal (BUY if majority BUY, etc.)
**Raises:** None (returns HOLD if empty or no consensus)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] MA crossover: BUY when fast > slow and price > fast, SELL when opposite
- [ ] RSI: BUY when < 30 (oversold), SELL when > 70 (overbought)
- [ ] Bollinger Bands: BUY when position < 0.1, SELL when > 0.9
- [ ] MACD: BUY when MACD > signal and histogram > 0
- [ ] Signal strength calculated from indicator magnitude
- [ ] Confidence bounded in [0, 1]
- [ ] HOLD signals have zero confidence
- [ ] Signal combination uses majority voting
- [ ] Consensus strength calculated from agreeing signals
- [ ] All signals include reason explanation
- [ ] Metadata includes indicator values
- [ ] Insufficient data returns HOLD signal
- [ ] Pure functions (no side effects)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES | Domain layer purity | ✅ OK - No infrastructure imports |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - dataclass with __post_init__ |
| TYP-001 | BASE_RULES | Type hints | ✅ OK - Full type coverage |
| SOL-001 | BASE_RULES | Single Responsibility | ✅ OK - Each method generates one signal type |
| CC-007 | BASE_RULES | Small functions | ✅ OK - Most methods < 30 lines |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear indicator/signal names |

---

## Dependencies
- **External:** dataclasses, decimal, enum, typing
- **Internal:** None (domain layer)

---

## Required Tests
- **test_signal_generator.py:**
  - MA crossover BUY signal (fast > slow, price > fast)
  - MA crossover SELL signal (fast < slow, price < fast)
  - MA crossover HOLD signal (mixed signals)
  - MA crossover with insufficient data
  - RSI oversold BUY signal (RSI < 30)
  - RSI very oversold BUY signal (RSI < 20)
  - RSI overbought SELL signal (RSI > 70)
  - RSI very overbought SELL signal (RSI > 80)
  - RSI neutral HOLD signal (30 < RSI < 70)
  - RSI with unavailable data
  - Bollinger BUY near lower band (position < 0.1)
  - Bollinger SELL near upper band (position > 0.9)
  - Bollinger HOLD within bands
  - Bollinger with zero width
  - MACD BUY signal (MACD > signal, histogram > 0)
  - MACD SELL signal (MACD < signal, histogram < 0)
  - MACD HOLD (no clear trend)
  - Signal combination: BUY consensus
  - Signal combination: SELL consensus
  - Signal combination: HOLD (no consensus)
  - Signal combination: empty list
  - Confidence threshold validation
  - Signal properties (is_buy, is_sell, is_actionable)
  - MA strength calculation
  - MACD strength calculation
  - Consensus strength calculation

---

## Notes
Pure domain service for signal generation. No external dependencies. Signals are deterministic based on indicator values. Confidence scoring helps filter weak signals. Combination logic enables multi-indicator strategies.
