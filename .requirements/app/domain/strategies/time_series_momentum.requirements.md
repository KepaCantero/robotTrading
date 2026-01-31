# time_series_momentum.py

## Purpose
Time-Series Momentum (TSM) strategy domain service - generates trading signals based on moving average crossovers and trend following for individual assets.

---

## Type Definitions / Data Classes

### TrendState (Enum)
```python
class TrendState(str, Enum):
    UPTREND = "uptrend"      # Price trending up
    DOWNTREND = "downtrend"  # Price trending down
    NEUTRAL = "neutral"      # No clear trend
    VOLATILE = "volatile"    # High volatility state
```

### TimeSeriesSignal
```python
@dataclass
class TimeSeriesSignal:
    symbol: str                      # REQUIRED - Asset symbol
    state: TrendState                # REQUIRED - Current trend state
    strength: float                  # REQUIRED - Signal strength (0-1)
    position_size: float             # REQUIRED - Suggested position (-1 to 1)
    stop_loss: Optional[float]        # OPTIONAL - Stop loss price
    take_profit: Optional[float]      # OPTIONAL - Take profit price
```

**Properties:**
- `is_long` - Returns True if uptrend with positive position
- `is_short` - Returns True if downtrend with negative position

**Validation Rules:**
- `strength` must be in [0, 1]
- `position_size` must be in [-1, 1]
- `stop_loss` and `take_profit` must be positive prices (if set)

---

## Function Signatures (Contracts)

### `TimeSeriesMomentum.__init__(fast_period, slow_period, volatility_period, volatility_threshold, position_sizing) -> None`
**Pre:** fast_period >= 1, slow_period > fast_period, volatility_period >= 1, volatility_threshold > 0, position_sizing in ["volatility_target", "kelly", "fixed"]
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `generate_signal(prices, symbol) -> TimeSeriesSignal`
**Pre:** prices is numpy array with most recent last; prices length >= 2
**Post:** Returns TimeSeriesSignal based on MA crossover and volatility
**Raises:** None (returns NEUTRAL signal if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_ma(prices, period) -> float` (private)
**Pre:** prices is non-empty array
**Post:** Returns simple moving average of last `period` prices
**Raises:** None (returns mean of all prices if len < period)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_signal_strength(fast_ma, slow_ma, current_price, volatility) -> float` (private)
**Pre:** fast_ma, slow_ma, current_price, volatility >= 0
**Post:** Returns strength in [0, 1] based on MA separation and price position
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_position_size(strength, volatility, direction) -> float` (private)
**Pre:** strength in [0, 1], volatility >= 0, direction in {-1, 1}
**Post:** Returns position size in [-1, 1] scaled by sizing method
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_atr(prices, period) -> float` (private)
**Pre:** prices length >= 2
**Post:** Returns Average True Range (volatility metric)
**Raises:** None (returns 0.0 if len < 2)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_portfolio_signals(price_data) -> List[TimeSeriesSignal]`
**Pre:** price_data is dict of symbol -> prices array
**Post:** Returns list of signals (only UPTREND/DOWNTREND, excludes NEUTRAL)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Input validation - prices array has minimum required length
- [ ] **AC-002:** Edge case handling - empty prices, single price, NaN values
- [ ] **AC-003:** Position size bounded to [-1, 1] regardless of calculation
- [ ] **AC-004:** Stop loss/take profit only set when ATR is calculable
- [ ] **AC-005:** All public methods have complete type hints
- [ ] **AC-006:** NumPy 2.0 compatibility
- [ ] **AC-007:** All functions have docstrings following Google style
- [ ] **AC-008:** Signal strength clamped to [0, 1]

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Time-Series Momentum):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate prices array length | ✅ OK - Checks slow_period |
| NaN handling | BASE_RULES.md (TRD-015) | Handle NaN in price data | ❌ GAP - No NaN handling |
| Position bounds | BASE_RULES.md (TRD-003) | Position size in [-1, 1] | ✅ OK - Clamped |
| Stop loss | BASE_RULES.md (RSK-004) | Implement stop loss for risk control | ✅ OK - 2% stop |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/scipy |
| MA crossover signal | Moskowitz (2012) | Fast MA > Slow MA = long | ✅ OK - Implemented |
| Volatility filter | Moskowitz (2012) | Minimum vol for signal generation | ✅ OK - volatility_threshold |
| Volatility targeting | Carver (2017) | Size ∝ 1/σ (inverse vol) | ✅ OK - Implemented |
| ATR-based stops | Wilder (1978) | Use ATR for stop loss calculation | ✅ OK - Implemented |
| Signal strength | TSM standard | MA separation + price position | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Moskowitz et al. (2012) for TSM rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (stats), `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_time_series_momentum.py:**
  - `test_uptrend_signal()` - Fast MA > Slow MA generates long signal
  - `test_downtrend_signal()` - Fast MA < Slow MA generates short signal
  - `test_neutral_low_volatility()` - Low vol returns neutral signal
  - `test_neutral_insufficient_data()` - Short prices returns neutral
  - `test_position_size_volatility_target()` - Inverse vol sizing
  - `test_position_size_fixed()` - Fixed sizing method
  - `test_signal_strength_clamping()` - Strength in [0, 1]
  - `test_stop_loss_calculation()` - ATR-based stops
  - `test_atr_calculation()` - ATR formula correctness
  - `test_portfolio_signals()` - Multi-asset signal generation
  - `test_nan_handling()` - NaN in prices
  - `test_empty_prices()` - Empty array handling
  - `test_single_price()` - Single element array

---

## Notes
- **Critical:** Time-series momentum works best with liquid, continuously traded assets
- **Moskowitz Reference:** "Time Series Momentum" (2012) - TSM across asset classes
- **MA Crossover:** Fast > Slow = uptrend (long); Fast < Slow = downtrend (short)
- **Volatility Filter:** Signals only generated when vol exceeds threshold (avoids whipsaw)
- **Position Sizing:** Three methods - volatility_target (inverse vol), fixed, or Kelly
- **Stop Loss:** 2% below entry (long) or above entry (short) based on ATR
- **Take Profit:** 6% target (3:1 reward-risk ratio)
- **Signal Strength:** Combination of MA separation and price position relative to MAs
- **ATR Period:** Default 14 periods (standard Wilder setting)
- **Carver Reference:** "Systematic Trading" (2017) - Volatility targeting for position sizing

---

**File Reference:** `app/domain/strategies/time_series_momentum.py`
**Last Audited:** 2026-02-01
