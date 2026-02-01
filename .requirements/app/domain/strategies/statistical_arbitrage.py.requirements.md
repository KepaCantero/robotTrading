# statistical_arbitrage.py

## Purpose
Implements mean reversion strategies based on statistical analysis of price deviations from fundamental values using Z-scores and Bollinger Bands.

---

## Type Definitions / Data Classes

### ReversionState Class (Enum)
```python
class ReversionState(str, Enum):
    OVERBOUGHT = "overbought"        # Price above mean, expect decline
    OVERSOLD = "oversold"            # Price below mean, expect rise
    NEUTRAL = "neutral"
    MEAN_CROSSING = "mean_crossing"  # Price crossing mean
```

**Validation Rules:**
- Enum values validated by Python's Enum system

### ZScoreSignal Class
```python
@dataclass
class ZScoreSignal:
    symbol: str                           # REQUIRED - Asset symbol
    z_score: float                        # REQUIRED - Standard deviations from mean
    state: ReversionState                 # REQUIRED - Current reversion state
    confidence: float                     # REQUIRED - Confidence (0-1)
    expected_reversion_target: float      # REQUIRED - Expected price after reversion
    stop_loss: Optional[float] = None     # OPTIONAL - Stop loss price
    take_profit: Optional[float] = None   # OPTIONAL - Take profit price
```

**Validation Rules:**
- confidence in [0, 1]
- expected_reversion_target > 0
- z_score must be finite
- Optional fields default to None

### BollingerBandSignal Class
```python
@dataclass
class BollingerBandSignal:
    symbol: str                   # REQUIRED - Asset symbol
    price: float                  # REQUIRED - Current price
    upper_band: float             # REQUIRED - Upper Bollinger Band
    middle_band: float            # REQUIRED - Moving average
    lower_band: float             # REQUIRED - Lower Bollinger Band
    bandwidth: float              # REQUIRED - (upper - lower) / middle
    percent_b: float              # REQUIRED - (price - lower) / (upper - lower)
    state: ReversionState         # REQUIRED - Current reversion state
    strength: float               # REQUIRED - Signal strength (0-1)
```

**Validation Rules:**
- All bands and price must be finite
- bandwidth >= 0
- percent_b typically in [0, 1]
- strength in [0, 1]

### MeanReversionMetrics Class
```python
@dataclass
class MeanReversionMetrics:
    half_life: float                      # REQUIRED - Expected time to revert (days)
    mean_reversion_speed: float           # REQUIRED - Speed of reversion (0-1)
    stationarity_test: float              # REQUIRED - ADF test statistic
    is_stationary: bool                   # REQUIRED - Whether series is stationary
    hit_rate: float                       # REQUIRED - Historical success rate
    average_reversion_time: float         # REQUIRED - Average days for reversion
```

**Validation Rules:**
- mean_reversion_speed in [0, 1]
- hit_rate in [0, 1]
- half_life > 0 (or inf for no reversion)

---

## Function Signatures (Contracts)

### `StatisticalArbitrage.__init__(lookback_period, z_score_threshold, entry_threshold, exit_threshold, min_half_life, max_half_life, confidence_level) -> None`
**Pre:** All parameters are valid (positive for periods/days, 0-1 for thresholds)
**Post:** Strategy instance initialized with validated parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_zscore_signal(prices: np.ndarray, symbol: str) -> ZScoreSignal`
**Pre:** prices is array of price history
**Post:** Returns ZScoreSignal with trading recommendation (NEUTRAL for insufficient/invalid data)
**Raises:** None (returns NEUTRAL signal on error)
**Retry:** No
**Side Effects:** Logs warnings for invalid inputs

### `generate_bollinger_signal(prices: np.ndarray, symbol: str, num_std: float = 2.0) -> BollingerBandSignal`
**Pre:** prices is array of price history
**Post:** Returns BollingerBandSignal with recommendation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_half_life(prices: np.ndarray) -> float`
**Pre:** prices is array of price history
**Post:** Returns half-life in days (inf if no mean reversion)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `test_stationarity(prices: np.ndarray) -> Tuple[bool, float]`
**Pre:** prices is array of price history
**Post:** Returns (is_stationary, test_statistic) tuple
**Raises:** None (falls back to variance ratio test)
**Retry:** No
**Side Effects:** May import statsmodels.tsa.stattools.adfuller

### `calculate_mean_reversion_metrics(prices: np.ndarray) -> MeanReversionMetrics`
**Pre:** prices is array of price history
**Post:** Returns MeanReversionMetrics with calculated statistics
**Raises:** None
**Retry:** No
**Side Effects:** None

### `should_trade(signal: ZScoreSignal, metrics: MeanReversionMetrics) -> bool`
**Pre:** signal and metrics are valid
**Post:** Returns True if signal should be traded
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_position_size(signal: ZScoreSignal, metrics: MeanReversionMetrics, max_position: float = 0.1) -> float`
**Pre:** signal and metrics are valid, 0 < max_position <= 1
**Post:** Returns position size as fraction of capital (<= max_position)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_atr(prices: np.ndarray, period: int = 14) -> float`
**Pre:** prices is array of price history
**Post:** Returns Average True Range
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_portfolio_signals(price_data: Dict[str, np.ndarray]) -> List[ZScoreSignal]`
**Pre:** price_data is valid dictionary of symbol -> prices
**Post:** Returns list of tradeable ZScoreSignals
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] generate_zscore_signal handles empty/NaN price arrays (returns NEUTRAL)
- [ ] generate_zscore_signal validates all calculated values (mean, std, z_score)
- [ ] generate_bollinger_signal calculates correct bands and percent_b
- [ ] calculate_half_life returns inf for non-mean-reverting series
- [ ] test_stationarity falls back to variance ratio test on statsmodels error
- [ ] calculate_mean_reversion_metrics returns valid metrics for all inputs
- [ ] should_trade filters by state, confidence, half_life, stationarity, speed
- [ ] calculate_position_size adjusts by confidence, z_score, speed, hit_rate
- [ ] ZScoreSignal.is_long and .is_short properties work correctly
- [ ] All dataclass fields have type hints
- [ ] No mutable default arguments
- [ ] Input validation uses np.isfinite() and NaN filtering

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X \| None) | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Uses returns/defaults (valid pattern) |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - Logs warnings for invalid inputs |
| ARCH-003 | BASE_RULES | No framework in domain | ⚠️ GAP - Imports scipy, statsmodels (scientific libs OK but should be abstracted) |
| TRD-002 | BASE_RULES | Risk validation | ✅ OK - Validates prices, calculates stop-loss |
| PERF-004 | BASE_RULES | Profile before optimizing | ⚠️ NOT APPLIED - Domain service |

**NOTE:** This analysis considers universal rules from BASE_RULES.md

---

## Dependencies
- **External:** numpy, scipy.stats, logging, dataclasses, decimal, enum, typing
- **Conditional:** statsmodels.tsa.stattools (imported in function, has fallback)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/unit/domain/strategies/test_statistical_arbitrage.py:**
  - Test ZScoreSignal properties (is_long, is_short)
  - Test generate_zscore_signal with valid prices
  - Test generate_zscore_signal with empty/NaN prices (defensive behavior)
  - Test generate_zscore_signal OVERBOUGHT/OVERSOLD/NEUTRAL states
  - Test generate_zscore_signal stop_loss/take_profit calculation
  - Test generate_bollinger_signal band calculations
  - Test generate_bollinger_signal bandwidth and percent_b
  - Test calculate_half_life with mean-reverting series
  - Test calculate_half_life with random walk (returns inf)
  - Test test_stationarity with stationary/non-stationary series
  - Test test_stationarity fallback to variance ratio
  - Test calculate_mean_reversion_metrics
  - Test should_trade filtering logic
  - Test calculate_position_size adjustment factors
  - Test _calculate_atr
  - Test generate_portfolio_signals
  - Test edge cases (single price point, all NaN)

---

## Notes
- Pure domain service with no infrastructure dependencies
- Uses statsmodels for ADF test with variance ratio fallback
- Extensive NaN/inf filtering for robustness
- Defensive programming (returns defaults rather than raising)
- Decimal imported but not used (uses float)
- Z-score threshold of 2.0 for entry, 0.5 for exit
- Half-life calculated from Ornstein-Uhlenbeck process
- ATR used for stop-loss calculation (2% from current price)
- Confidence scales with z-score magnitude
- Position size adjusted by multiple factors (confidence, z-score, speed, hit-rate)
