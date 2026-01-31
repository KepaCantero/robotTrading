# statistical_arbitrage.py

## Purpose
Statistical Arbitrage / Mean Reversion strategy - generates signals when prices deviate significantly from historical mean and expects reversion.

---

## Type Definitions / Data Classes

### ReversionState (Enum)
```python
class ReversionState(str, Enum):
    OVERBOUGHT = "overbought"      # Price above mean, expect decline
    OVERSOLD = "oversold"          # Price below mean, expect rise
    NEUTRAL = "neutral"            # No clear deviation
    MEAN_CROSSING = "mean_crossing" # Price crossing mean
```

### ZScoreSignal
```python
@dataclass
class ZScoreSignal:
    symbol: str                           # REQUIRED - Asset symbol
    z_score: float                        # REQUIRED - Standard deviations from mean
    state: ReversionState                 # REQUIRED - Current state
    confidence: float                     # REQUIRED - Signal confidence (0-1)
    expected_reversion_target: float      # REQUIRED - Expected price after reversion
    stop_loss: Optional[float]            # OPTIONAL - Stop loss price
    take_profit: Optional[float]          # OPTIONAL - Take profit price
```

**Properties:**
- `is_long` - True if OVERSOLD
- `is_short` - True if OVERBOUGHT

### BollingerBandSignal
```python
@dataclass
class BollingerBandSignal:
    symbol: str                    # REQUIRED - Asset symbol
    price: float                   # REQUIRED - Current price
    upper_band: float              # REQUIRED - Upper Bollinger Band
    middle_band: float             # REQUIRED - Moving average (center)
    lower_band: float              # REQUIRED - Lower Bollinger Band
    bandwidth: float               # REQUIRED - (upper - lower) / middle
    percent_b: float               # REQUIRED - (price - lower) / (upper - lower)
    state: ReversionState          # REQUIRED - Current state
    strength: float                # REQUIRED - Signal strength (0-1)
```

### MeanReversionMetrics
```python
@dataclass
class MeanReversionMetrics:
    half_life: float                    # REQUIRED - Days for 50% reversion
    mean_reversion_speed: float         # REQUIRED - Speed of reversion (0-1)
    stationarity_test: float            # REQUIRED - ADF test statistic
    is_stationary: bool                 # REQUIRED - Whether series is stationary
    hit_rate: float                     # REQUIRED - Historical success rate
    average_reversion_time: float       # REQUIRED - Average days for reversion
```

---

## Function Signatures (Contracts)

### `StatisticalArbitrage.__init__(lookback_period, z_score_threshold, entry_threshold, exit_threshold, min_half_life, max_half_life, confidence_level) -> None`
**Pre:** lookback_period >= 10; z_score_threshold > 0; entry_threshold > exit_threshold > 0; min_half_life < max_half_life; confidence_level in (0, 1]
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `generate_zscore_signal(prices, symbol) -> ZScoreSignal`
**Pre:** prices is non-empty array
**Post:** Returns ZScoreSignal based on deviation from mean
**Raises:** None (returns NEUTRAL if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `generate_bollinger_signal(prices, symbol, num_std) -> BollingerBandSignal`
**Pre:** prices is non-empty array; num_std > 0
**Post:** Returns BollingerBandSignal with band levels
**Raises:** None (returns neutral signal if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_half_life(prices) -> float`
**Pre:** prices length >= 2
**Post:** Returns half-life in periods (or inf if no mean reversion)
**Raises:** None (returns 0.0 or inf)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `test_stationarity(prices) -> Tuple[bool, float]`
**Pre:** prices has at least 2 elements
**Post:** Returns (is_stationary, test_statistic) using ADF test
**Raises:** None (falls back to variance ratio test)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_mean_reversion_metrics(prices) -> MeanReversionMetrics`
**Pre:** prices is non-empty array
**Post:** Returns comprehensive mean reversion metrics
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `should_trade(signal, metrics) -> bool`
**Pre:** signal and metrics are valid
**Post:** Returns True if signal meets all trading criteria
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_position_size(signal, metrics, max_position) -> float`
**Pre:** signal and metrics valid; max_position in (0, 1]
**Post:** Returns position size as fraction of capital
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `generate_portfolio_signals(price_data) -> List[ZScoreSignal]`
**Pre:** price_data is dict of symbol -> prices array
**Post:** Returns list of tradeable signals
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Input validation - prices array has minimum required length
- [ ] **AC-002:** Z-score calculated correctly as (price - mean) / std
- [ ] **AC-003:** Bollinger Bands use ±num_std around moving average
- [ ] **AC-004:** Half-life uses Ornstein-Uhlenbeck process formula
- [ ] **AC-005:** Stationarity test uses ADF test (with fallback)
- [ ] **AC-006:** All public methods have complete type hints
- [ ] **AC-007:** NumPy 2.0 compatibility
- [ ] **AC-008:** All functions have docstrings following Google style

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Statistical Arbitrage):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate prices array length | ✅ OK - Checks lookback |
| NaN handling | BASE_RULES.md (TRD-015) | Handle NaN in price data | ❌ GAP - No NaN handling |
| Z-score calculation | Stats standard | (price - mean) / std | ✅ OK - Implemented |
| Half-life OU process | Mean reversion | HL = ln(2) / θ | ✅ OK - Implemented |
| ADF stationarity test | Stats standard | Augmented Dickey-Fuller | ✅ OK - With fallback |
| Entry threshold | Mean reversion | |Z| > 2.0 for entry | ✅ OK - entry_threshold |
| Exit threshold | Mean reversion | |Z| < 0.5 for exit | ✅ OK - exit_threshold |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ⚠️ PARTIAL - statsmodels is external lib |
| Bollinger Bands | Technical analysis | MA ± num_std | ✅ OK - Implemented |
| Position sizing | Risk management | Size ∝ confidence × metrics | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Balakrishnan et al. (2018) for statistical arbitrage rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (stats), `statsmodels` (tsa.stattools), `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_statistical_arbitrage.py:**
  - `test_zscore_signal_oversold()` - Z < -2 triggers OVERSOLD (long)
  - `test_zscore_signal_overbought()` - Z > 2 triggers OVERBOUGHT (short)
  - `test_zscore_signal_neutral()` - |Z| < 0.5 is NEUTRAL
  - `test_bollinger_bands()` - Bands at MA ± 2std
  - `test_half_life_calculation()` - OU process formula
  - `test_stationarity_test()` - ADF test detects stationary series
  - `test_should_trade()` - Filters by half-life and stationarity
  - `test_position_size_calculation()` - Size based on confidence
  - `test_insufficient_data()` - Handles short price arrays
  - `test_zero_std_handling()` - Handles constant prices
  - `test_no_mean_reversion()` - Returns inf HL for random walk
  - `test_portfolio_signals()` - Multi-asset signal generation

---

## Notes
- **Critical:** Mean reversion only works for stationary series (not trending assets)
- **Balakrishnan Reference:** "Machine Learning for Statistical Arbitrage" (2018)
- **Z-Score Entry:** Default |Z| > 2.0 (2 sigma from mean)
- **Z-Score Exit:** Default |Z| < 0.5 (near mean)
- **Half-Life Formula:** HL = ln(2) / θ where θ is mean reversion speed from OU process
- **OU Process:** dx = θ(μ - x)dt + σdW (mean-reverting stochastic process)
- **Stationarity:** Required for mean reversion (tested via ADF)
- **Bollinger Bands:** MA ± num_std (default 2 std)
- **Percent B:** Position within bands (0 = lower, 1 = upper)
- **Stop Loss:** 2% from entry price
- **Take Profit:** Mean reversion target

---

**File Reference:** `app/domain/strategies/statistical_arbitrage.py`
**Last Audited:** 2026-02-01
