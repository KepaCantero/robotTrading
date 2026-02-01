# pairs_trading.py

## Purpose
Implements statistical arbitrage based on cointegration between pairs of assets that move together in the long run, trading mean reversion of the spread.

---

## Type Definitions / Data Classes

### PairSignal Class (Enum)
```python
class PairSignal(str, Enum):
    LONG_SHORT = "long_short"              # Long asset A, Short asset B
    SHORT_LONG = "short_long"              # Short asset A, Long asset B
    CLOSE_LONG_SHORT = "close_long_short"  # Close existing position
    CLOSE_SHORT_LONG = "close_short_long"  # Close existing position
    NO_ACTION = "no_action"
```

**Validation Rules:**
- Enum values validated by Python's Enum system

### CointegrationResult Class
```python
@dataclass
class CointegrationResult:
    is_cointegrated: bool           # REQUIRED - Whether series are cointegrated
    test_statistic: float           # REQUIRED - Engle-Granger or Johansen statistic
    p_value: float                  # REQUIRED - Statistical significance (0-1)
    critical_value: float           # REQUIRED - Critical value at confidence level
    hedge_ratio: float              # REQUIRED - Optimal hedge ratio (beta)
    half_life: float                # REQUIRED - Expected half-life of spread
    confidence: float               # REQUIRED - Confidence in cointegration (0-1)
```

**Validation Rules:**
- p_value in [0, 1]
- confidence in [0, 1]
- half_life > 0 (or inf for no cointegration)
- NaN/inf handling for test_statistic, hedge_ratio

### PairPosition Class
```python
@dataclass
class PairPosition:
    symbol_a: str                   # REQUIRED - First asset symbol
    symbol_b: str                   # REQUIRED - Second asset symbol
    signal: PairSignal              # REQUIRED - Trading signal
    weight_a: float                 # REQUIRED - Weight for asset A
    weight_b: float                 # REQUIRED - Weight for asset B
    spread: float                   # REQUIRED - Current spread
    z_score: float                  # REQUIRED - Z-score of spread
    entry_spread: float             # REQUIRED - Spread at entry
    stop_loss_spread: Optional[float] = None  # OPTIONAL - Stop loss based on spread
    take_profit_spread: Optional[float] = None  # OPTIONAL - Take profit based on spread
```

**Validation Rules:**
- weight_a and weight_b can be positive or negative (long/short)
- spread, z_score, entry_spread must be finite
- Optional fields default to None

### TradingPair Class
```python
@dataclass
class TradingPair:
    symbol_a: str                   # REQUIRED - First asset symbol
    symbol_b: str                   # REQUIRED - Second asset symbol
    coint_result: CointegrationResult  # REQUIRED - Cointegration test results
    p_value: float                  # REQUIRED - Historical p-value
    avg_half_life: float            # REQUIRED - Average historical half-life
    trade_count: int                # REQUIRED - Number of historical trades
```

**Validation Rules:**
- p_value in [0, 1]
- avg_half_life > 0
- trade_count >= 0

---

## Function Signatures (Contracts)

### `PairsTrading.__init__(formation_period, trading_period, z_score_entry, z_score_exit, min_half_life, max_half_life, num_pairs) -> None`
**Pre:** All parameters are positive and valid
**Post:** Strategy instance initialized with validated parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `find_cointegrated_pairs(price_data: Dict[str, np.ndarray]) -> List[TradingPair]`
**Pre:** price_data is valid dictionary with sufficient history
**Post:** Returns list of TradingPair sorted by p-value (up to num_pairs)
**Raises:** None
**Retry:** No
**Side Effects:** Tests all possible pairs for cointegration

### `_test_cointegration(prices_a: np.ndarray, prices_b: np.ndarray) -> CointegrationResult`
**Pre:** prices_a and prices_b are price series
**Post:** Returns CointegrationResult with test results (uses fallback on error)
**Raises:** None (falls back to simple test on error)
**Retry:** No
**Side Effects:** May import statsmodels.tsa.stattools.adfuller

### `_simple_cointegration_test(prices_a: np.ndarray, prices_b: np.ndarray) -> CointegrationResult`
**Pre:** prices_a and prices_b are price series
**Post:** Returns CointegrationResult based on correlation
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_half_life(spread: np.ndarray) -> float`
**Pre:** spread is array of spread values
**Post:** Returns half-life in periods (inf if no mean reversion)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_spread_z_score(trading_pair: TradingPair, prices_a: np.ndarray, prices_b: np.ndarray) -> float`
**Pre:** trading_pair is valid, prices arrays are valid
**Post:** Returns Z-score of current spread
**Raises:** None (returns 0.0 if std < 1e-10)
**Retry:** No
**Side Effects:** None

### `generate_signal(trading_pair: TradingPair, prices_a: np.ndarray, prices_b: np.ndarray, current_position: Optional[PairPosition] = None) -> PairSignal`
**Pre:** trading_pair is valid, prices arrays are valid
**Post:** Returns appropriate PairSignal
**Raises:** None
**Retry:** No
**Side Effects:** None

### `create_pair_position(trading_pair: TradingPair, signal: PairSignal, prices_a: np.ndarray, prices_b: np.ndarray, capital: float = 100000.0) -> PairPosition`
**Pre:** trading_pair is valid, prices are valid, signal is valid
**Post:** Returns PairPosition with weights and risk levels
**Raises:** None
**Retry:** No
**Side Effects:** None

### `update_pair_position(position: PairPosition, prices_a: np.ndarray, prices_b: np.ndarray) -> PairPosition`
**Pre:** position is valid, prices are valid
**Post:** Returns updated PairPosition with recalculated spread
**Raises:** None
**Retry:** No
**Side Effects:** Modifies position.spread in place

---

## Acceptance Criteria
- [ ] _test_cointegration handles NaN/inf values in price data
- [ ] _test_cointegration falls back to simple test on statsmodels import error
- [ ] _calculate_half_life returns inf for non-mean-reverting series
- [ ] find_cointegrated_pairs returns top num_pairs sorted by p-value
- [ ] generate_signal correctly handles existing positions (close conditions)
- [ ] create_pair_position sets stop_loss and take_profit based on spread std
- [ ] TradingPair.is_valid_pair checks p_value < 0.05 and half_life < 60
- [ ] All dataclass fields have type hints
- [ ] No mutable default arguments
- [ ] Input validation filters NaN/inf values

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X \| None) | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Uses fallback methods (valid pattern) |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - Logs warnings for errors |
| ARCH-003 | BASE_RULES | No framework in domain | ⚠️ GAP - Imports scipy, statsmodels (scientific libs OK but should be abstracted) |
| TRD-002 | BASE_RULES | Risk validation | ✅ OK - Validates data, handles errors |
| PERF-004 | BASE_RULES | Profile before optimizing | ⚠️ NOT APPLIED - Domain service |

**NOTE:** This analysis considers universal rules from BASE_RULES.md

---

## Dependencies
- **External:** numpy, scipy.stats, logging, dataclasses, decimal, enum, typing
- **Conditional:** statsmodels.tsa.stattools (imported in function, has fallback)
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/unit/domain/strategies/test_pairs_trading.py:**
  - Test PairPosition properties (net_exposure, is_long_short, is_short_long)
  - Test TradingPair properties (pair_id, is_valid_pair)
  - Test _test_cointegration with cointegrated series
  - Test _test_cointegration with non-cointegrated series
  - Test _test_cointegration with NaN/inf values
  - Test _simple_cointegration_test fallback
  - Test _calculate_half_life with mean-reverting series
  - Test _calculate_half_life with random walk (returns inf)
  - Test find_cointegrated_pairs sorting and filtering
  - Test calculate_spread_z_score calculation
  - Test generate_signal for entry (LONG_SHORT, SHORT_LONG)
  - Test generate_signal for exit (close conditions)
  - Test generate_signal with existing positions
  - Test create_pair_position weight calculation
  - Test create_pair_position stop_loss/take_profit calculation
  - Test update_pair_position spread recalculation
  - Test edge cases (short series, single pair)

---

## Notes
- Pure domain service with no infrastructure dependencies
- Uses statsmodels for ADF test with correlation-based fallback
- Extensive NaN/inf filtering for robustness
- Defensive programming (fallback methods, returns defaults)
- Decimal imported but not used (uses float)
- Hedge ratio calculated via OLS regression on log prices
- Spread calculated as log_a - hedge_ratio * log_b
- Supports stop-loss and take-profit based on spread standard deviation
