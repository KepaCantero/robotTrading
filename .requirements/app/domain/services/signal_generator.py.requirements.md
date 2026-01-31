# signal_generator.py

## Purpose
Domain service for generating trading signals based on technical indicators, price action, momentum, and mean reversion strategies. Supports multiple signal types (BUY/SELL/HOLD/CLOSE) with strength and confidence scoring, and combines multiple signals into consensus recommendations.

---

## Type Definitions / Data Classes

### SignalType Enum (str, Enum)
```python
class SignalType(str, Enum):
    BUY = "buy"      # Action: Enter long position
    SELL = "sell"    # Action: Enter short position or exit long
    HOLD = "hold"    # Action: No action, wait
    CLOSE = "close"  # Action: Exit current position
```

**Validation Rules:**
- Only four valid values
- Used in Signal.signal_type
- Determines is_buy, is_sell, is_actionable properties

### SignalStrength Enum (str, Enum)
```python
class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"
```

**Validation Rules:**
- Four levels of conviction
- Used in Signal.strength
- Derived from indicator calculations (MA distance, RSI extremes, etc.)

### Signal Class (DataClass)
```python
@dataclass
class Signal:
    symbol: str                    # REQUIRED - Trading symbol
    signal_type: SignalType        # REQUIRED - Type of signal
    strength: SignalStrength       # REQUIRED - Conviction level
    confidence: Decimal            # REQUIRED - Confidence score 0-1
    target_price: Optional[Decimal] = None     # OPTIONAL - Suggested entry/exit price
    stop_loss: Optional[Decimal] = None        # OPTIONAL - Risk management level
    take_profit: Optional[Decimal] = None      # OPTIONAL - Profit target
    quantity: Optional[Decimal] = None         # OPTIONAL - Suggested position size
    reason: str = ""               # REQUIRED - Human-readable explanation
    metadata: Dict[str, Any] = None            # OPTIONAL - Additional signal data
```

**Validation Rules:**
- confidence in range [0, 1]
- reason defaults to "" but should be populated
- metadata defaults to {} via __post_init__
- is_buy = (signal_type == SignalType.BUY)
- is_sell = (signal_type == SignalType.SELL)
- is_actionable = (signal_type in [BUY, SELL])

### IndicatorValues Class (DataClass)
```python
@dataclass
class IndicatorValues:
    price: Decimal                     # REQUIRED - Current market price
    sma_20: Optional[Decimal] = None   # OPTIONAL - 20-period Simple Moving Average
    sma_50: Optional[Decimal] = None   # OPTIONAL - 50-period Simple Moving Average
    ema_12: Optional[Decimal] = None   # OPTIONAL - 12-period Exponential Moving Average
    ema_26: Optional[Decimal] = None   # OPTIONAL - 26-period Exponential Moving Average
    rsi: Optional[Decimal] = None      # OPTIONAL - Relative Strength Index (0-100)
    macd: Optional[Decimal] = None     # OPTIONAL - MACD line
    macd_signal: Optional[Decimal] = None # OPTIONAL - MACD signal line
    bollinger_upper: Optional[Decimal] = None  # OPTIONAL - Upper Bollinger Band
    bollinger_lower: Optional[Decimal] = None  # OPTIONAL - Lower Bollinger Band
    volume: Optional[Decimal] = None   # OPTIONAL - Current trading volume
    volume_ma: Optional[Decimal] = None # OPTIONAL - Volume moving average
```

**Validation Rules:**
- price is required
- RSI in range [0, 100] if present
- bollinger_lower < bollinger_upper if both present
- All indicators Optional to support different strategies

---

## Function Signatures (Contracts)

### `__init__(confidence_threshold: Decimal = Decimal("0.6")) -> None`
**Pre:** confidence_threshold in range [0, 1]
**Post:** SignalGenerator instance initialized with threshold
**Raises:** None
**Retry:** No
**Side Effects:** None (state initialization only)

### `generate_ma_crossover_signal(indicators: IndicatorValues, symbol: str = "") -> Signal`
**Pre:** indicators has valid price; symbol is valid ticker (can be empty)
**Post:** Returns Signal based on SMA crossover (BUY if fast > slow, SELL if fast < slow, HOLD otherwise)
**Raises:** None (returns HOLD if MAs missing)
**Retry:** No
**Side Effects:** None (pure calculation)

### `generate_rsi_signal(indicators: IndicatorValues, symbol: str = "") -> Signal`
**Pre:** indicators has valid price and RSI; symbol is valid ticker
**Post:** Returns Signal (BUY if RSI < 30 oversold, SELL if RSI > 70 overbought, HOLD if neutral)
**Raises:** None (returns HOLD if RSI missing)
**Retry:** No
**Side Effects:** None (pure calculation)

### `generate_bollinger_signal(indicators: IndicatorValues, symbol: str = "") -> Signal`
**Pre:** indicators has valid price, bollinger_upper, bollinger_lower
**Post:** Returns Signal (BUY if price <= lower * 0.1, SELL if price >= upper * 0.9, HOLD otherwise)
**Raises:** None (returns HOLD if bands missing or zero width)
**Retry:** No
**Side Effects:** None (pure calculation)

### `generate_macd_signal(indicators: IndicatorValues, symbol: str = "") -> Signal`
**Pre:** indicators has valid MACD and MACD signal line
**Post:** Returns Signal (BUY if MACD > signal, SELL if MACD < signal, HOLD if near zero)
**Raises:** None (returns HOLD if MACD missing)
**Retry:** No
**Side Effects:** None (pure calculation)

### `combine_signals(signals: List[Signal], symbol: str = "") -> Signal`
**Pre:** signals is non-empty list of Signal objects for the same symbol
**Post:** Returns consensus Signal (majority vote with averaged confidence)
**Raises:** None (returns HOLD if signals empty)
**Retry:** No
**Side Effects:** None (pure calculation)

### `_hold_signal(symbol: str, reason: str) -> Signal`
**Pre:** symbol is valid ticker; reason is non-empty string
**Post:** Returns HOLD signal with zero confidence
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_ma_strength(fast_ma: Decimal, slow_ma: Decimal) -> SignalStrength`
**Pre:** fast_ma and slow_ma are positive values
**Post:** Returns SignalStrength based on % distance (>5% = VERY_STRONG, >3% = STRONG, >1% = MODERATE)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_macd_strength(histogram: Decimal) -> SignalStrength`
**Pre:** histogram is absolute MACD histogram value
**Post:** Returns SignalStrength based on magnitude (>2 = VERY_STRONG, >1 = STRONG, >0.5 = MODERATE)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_consensus_strength(signals: List[Signal]) -> SignalStrength`
**Pre:** signals is non-empty list of same-type signals
**Post:** Returns consensus strength (VERY_STRONG if all strong, STRONG if majority strong, else MODERATE)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-SIG-001:** generate_ma_crossover_signal returns BUY when price > fast_ma > slow_ma
- [ ] **AC-SIG-002:** generate_ma_crossover_signal returns SELL when price < fast_ma < slow_ma
- [ ] **AC-SIG-003:** generate_rsi_signal returns BUY when RSI < 30 (oversold)
- [ ] **AC-SIG-004:** generate_rsi_signal returns SELL when RSI > 70 (overbought)
- [ ] **AC-SIG-005:** generate_rsi_signal strength is STRONG when RSI < 20 or > 80
- [ ] **AC-SIG-006:** generate_bollinger_signal returns BUY when price position < 0.1 (near lower band)
- [ ] **AC-SIG-007:** generate_bollinger_signal returns SELL when price position > 0.9 (near upper band)
- [ ] **AC-SIG-008:** generate_macd_signal returns BUY when MACD > signal line and histogram > 0
- [ ] **AC-SIG-009:** generate_macd_signal returns SELL when MACD < signal line and histogram < 0
- [ ] **AC-SIG-010:** combine_signals returns majority signal type with averaged confidence
- [ ] **AC-SIG-011:** combine_signals returns HOLD when no majority (tie or all HOLD)
- [ ] **AC-SIG-012:** All confidence values in range [0, 1]
- [ ] **AC-SIG-013:** All monetary calculations use Decimal (no float precision)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules across 14 categories)

### Reglas ESPECIFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES | Domain layer has no infrastructure dependencies | ✅ OK - Pure domain logic |
| ARCH-003 | BASE_RULES | No framework imports in domain (FastAPI, SQLAlchemy) | ✅ OK - Only numpy |
| TYP-001 | BASE_RULES | 100% type coverage on all functions | ✅ OK - All typed |
| FMT-007 | BASE_RULES | No mutable defaults in function signatures | ✅ OK - None defaults used |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - metadata: Dict[str, Any] justified |
| CC-006 | BASE_RULES | Explicit error handling for edge cases | ✅ OK - Returns HOLD on missing data |
| SOL-001 | BASE_RULES | Single Responsibility Principle | ✅ OK - Only signal generation |
| SOL-005 | BASE_RULES | Dependency Inversion (inject config) | ✅ OK - Constructor injection |
| CC-001 | BASE_RULES | Descriptive names revealing intent | ✅ OK - Clear naming |
| TRD-005 | BASE_RULES | Price validation at boundaries | ⚠️ NOT APPLIED - Assumes valid indicators |

### Signal Generation Specific Rules (Technical Analysis)

| Rule ID | Rule | Priority | Status |
|---------|------|----------|--------|
| SIG-001 | Return HOLD when indicators are missing (graceful degradation) | **P0** | ✅ OK |
| SIG-002 | Confidence scores must be in range [0, 1] | **P0** | ✅ OK |
| SIG-003 | RSI oversold/overbought thresholds (30/70) are standard | P1 | ✅ OK |
| SIG-004 | Bollinger Band position uses 0.1/0.9 thresholds (10% bands) | P1 | ✅ OK |
| SIG-005 | MA crossover requires both price and MAs aligned | **P0** | ✅ OK |
| SIG-006 | MACD signal confirms histogram direction (not just crossover) | **P0** | ✅ OK |
| SIG-007 | Consensus requires majority vote (not unanimity) | P1 | ✅ OK |
| SIG-008 | All monetary values use Decimal for precision | **P0** | ✅ OK |
| SIG-009 | Signal metadata provides diagnostic info (indicator values) | P2 | ✅ OK |
| SIG-010 | Confidence threshold filters weak signals (default 0.6) | P2 | ⚠️ NOT APPLIED - Stored but not used |

---

## Dependencies
- **External:**
  - `dataclasses` (stdlib) - for Signal, IndicatorValues
  - `decimal.Decimal` (stdlib) - for precise monetary calculations
  - `enum.Enum` (stdlib) - for SignalType, SignalStrength
  - `typing.Any`, `typing.Dict`, `typing.List`, `typing.Optional` (stdlib) - type hints
  - `numpy` (third-party) - imported but not used in current code (GAP - remove or use)
- **Internal:**
  - None (pure domain service with no entity dependencies)

---

## Required Tests
- **tests/domain/services/test_signal_generator.py:**
  - **Success paths:**
    - test_generate_ma_crossover_signal_bullish: Returns BUY when price > SMA20 > SMA50
    - test_generate_ma_crossover_signal_bearish: Returns SELL when price < SMA20 < SMA50
    - test_generate_ma_crossover_signal_mixed: Returns HOLD when MAs misaligned
    - test_generate_ma_crossover_signal_strength_very_strong: Returns VERY_STRONG when MA distance > 5%
    - test_generate_rsi_signal_oversold: Returns BUY when RSI < 30
    - test_generate_rsi_signal_overbought: Returns SELL when RSI > 70
    - test_generate_rsi_signal_neutral: Returns HOLD when 30 <= RSI <= 70
    - test_generate_rsi_signal_extreme_oversold: Returns STRONG when RSI < 20
    - test_generate_bollinger_signal_lower_band: Returns BUY when price position < 0.1
    - test_generate_bollinger_signal_upper_band: Returns SELL when price position > 0.9
    - test_generate_bollinger_signal_within_bands: Returns HOLD when price in middle
    - test_generate_macd_signal_bullish: Returns BUY when MACD > signal and histogram > 0
    - test_generate_macd_signal_bearish: Returns SELL when MACD < signal and histogram < 0
    - test_combine_signals_buy_majority: Returns BUY when most signals are BUY
    - test_combine_signals_no_majority: Returns HOLD when tie between BUY and SELL
    - test_combine_signals_confidence_averaged: Averages confidence for majority signals
  - **Error paths:**
    - test_generate_ma_crossover_signal_missing_ma: Returns HOLD when SMA20 or SMA50 is None
    - test_generate_rsi_signal_missing_rsi: Returns HOLD when RSI is None
    - test_generate_bollinger_signal_missing_bands: Returns HOLD when bands are None
    - test_generate_macd_signal_missing_macd: Returns HOLD when MACD is None
    - test_combine_signals_empty_list: Returns HOLD with reason "No signals to combine"
  - **Edge cases:**
    - test_signal_properties_is_buy: Returns True for BUY signal type
    - test_signal_properties_is_sell: Returns True for SELL signal type
    - test_signal_properties_is_actionable: Returns True for BUY/SELL, False for HOLD/CLOSE
    - test_signal_post_init_metadata: Initializes metadata to {} if None
    - test_calculate_ma_strength_boundary_5_percent: Returns VERY_STRONG at exactly 5% threshold
    - test_calculate_macd_strength_boundary_2: Returns VERY_STRONG at exactly 2.0
    - test_generate_bollinger_signal_zero_width: Returns HOLD when band_width == 0
    - test_confidence_threshold_initialization: Accepts custom confidence threshold
    - test_indicator_values_all_optional_except_price: Accepts only price with None indicators

---

## Notes
- **Gap:** `numpy` is imported but not used. Should be removed or utilized for vector calculations.
- **Unused Parameter:** `confidence_threshold` is stored in `__init__` but never used. Should be applied to filter weak signals or removed.
- **Strategy Independence:** Each signal generation method is independent. No cross-validation between strategies (e.g., RSI + MACD confirmation).
- **Extensibility:** New signal strategies can be added without modifying existing code (Open/Closed Principle).
- **Signal Metadata:** metadata field provides diagnostic information but is not standardized. Consider schema for common indicators.
- **Confidence Scoring:** Confidence calculations vary by strategy (MA: strength/100, RSI: distance from threshold, etc.). May need normalization for consensus.
- **Target Price/Stop Loss:** Signal has fields for target_price, stop_loss, take_profit, quantity but none are populated by generator methods. These should be calculated or remain optional.
- **Performance:** All calculations are O(1) per signal. Suitable for real-time trading.
