# pairs_trading.py

## Purpose
Pairs Trading strategy domain service - statistical arbitrage based on cointegration between asset pairs that mean-revert.

---

## Type Definitions / Data Classes

### PairSignal (Enum)
```python
class PairSignal(str, Enum):
    LONG_SHORT = "long_short"              # Long A, Short B
    SHORT_LONG = "short_long"              # Short A, Long B
    CLOSE_LONG_SHORT = "close_long_short"  # Close long-short position
    CLOSE_SHORT_LONG = "close_short_long"  # Close short-long position
    NO_ACTION = "no_action"                # No trade
```

### CointegrationResult
```python
@dataclass
class CointegrationResult:
    is_cointegrated: bool       # REQUIRED - Whether series are cointegrated
    test_statistic: float       # REQUIRED - ADF test statistic
    p_value: float              # REQUIRED - Statistical significance
    critical_value: float       # REQUIRED - Critical value at 5%
    hedge_ratio: float          # REQUIRED - Optimal hedge ratio (beta)
    half_life: float            # REQUIRED - Expected mean reversion half-life
    confidence: float           # REQUIRED - Confidence in cointegration (0-1)
```

**Validation Rules:**
- `p_value` in [0, 1]
- `confidence` in [0, 1]
- `half_life` > 0 (or inf if no mean reversion)

### PairPosition
```python
@dataclass
class PairPosition:
    symbol_a: str                           # REQUIRED - First asset symbol
    symbol_b: str                           # REQUIRED - Second asset symbol
    signal: PairSignal                      # REQUIRED - Current signal
    weight_a: float                         # REQUIRED - Weight for asset A
    weight_b: float                         # REQUIRED - Weight for asset B
    spread: float                           # REQUIRED - Current spread value
    z_score: float                          # REQUIRED - Z-score of spread
    entry_spread: float                     # REQUIRED - Spread at entry
    stop_loss_spread: Optional[float]        # OPTIONAL - Stop loss level
    take_profit_spread: Optional[float]      # OPTIONAL - Take profit level
```

**Properties:**
- `net_exposure` - Returns |weight_a| + |weight_b|
- `is_long_short()` - True if LONG_SHORT signal
- `is_short_long()` - True if SHORT_LONG signal

### TradingPair
```python
@dataclass
class TradingPair:
    symbol_a: str                      # REQUIRED - First asset
    symbol_b: str                      # REQUIRED - Second asset
    coint_result: CointegrationResult  # REQUIRED - Cointegration test result
    p_value: float                     # REQUIRED - Historical p-value
    avg_half_life: float               # REQUIRED - Average half-life
    trade_count: int                   # REQUIRED - Number of historical trades
```

**Properties:**
- `pair_id` - Returns "symbolA_symbolB"
- `is_valid_pair()` - True if cointegrated, p<0.05, half_life<60

---

## Function Signatures (Contracts)

### `PairsTrading.__init__(formation_period, trading_period, z_score_entry, z_score_exit, min_half_life, max_half_life, num_pairs) -> None`
**Pre:** formation_period >= 60; trading_period >= 30; z_entry > z_exit > 0; min_half_life < max_half_life; num_pairs >= 1
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `find_cointegrated_pairs(price_data) -> List[TradingPair]`
**Pre:** price_data has at least 2 assets; each asset has >= formation_period observations
**Post:** Returns list of cointegrated pairs sorted by p-value (best first), up to num_pairs
**Raises:** None (skips insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_test_cointegration(prices_a, prices_b) -> CointegrationResult` (private)
**Pre:** prices_a and prices_b are non-empty arrays
**Post:** Returns cointegration test using Engle-Granger ADF test
**Raises:** None (falls back to simple correlation test on error)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_simple_cointegration_test(prices_a, prices_b) -> CointegrationResult` (private)
**Pre:** prices_a and prices_b are non-empty arrays
**Post:** Returns simple cointegration based on correlation > 0.7
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_half_life(spread) -> float` (private)
**Pre:** spread has at least 2 elements
**Post:** Returns half-life in periods (or inf if no mean reversion)
**Raises:** None (returns 0 or inf)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `calculate_spread_z_score(trading_pair, prices_a, prices_b) -> float`
**Pre:** trading_pair has valid hedge_ratio; prices arrays have recent data
**Post:** Returns Z-score of current spread relative to historical mean
**Raises:** None (returns 0.0 if std < 1e-10)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `generate_signal(trading_pair, prices_a, prices_b, current_position) -> PairSignal`
**Pre:** trading_pair is valid; prices arrays have recent data
**Post:** Returns signal based on Z-score thresholds (entry/exit)
**Raises:** None (returns NO_ACTION if conditions not met)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `create_pair_position(trading_pair, signal, prices_a, prices_b, capital) -> PairPosition`
**Pre:** trading_pair valid; signal is entry signal (LONG_SHORT or SHORT_LONG)
**Post:** Returns PairPosition with dollar-neutral weights (±50%)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `update_pair_position(position, prices_a, prices_b) -> PairPosition`
**Pre:** position valid; prices have latest data
**Post:** Returns position with updated spread value
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Input validation - prices arrays have minimum required length
- [ ] **AC-002:** Cointegration test correctly identifies stationary spreads (ADF test)
- [ ] **AC-003:** Hedge ratio calculated via OLS regression (log prices)
- [ ] **AC-004:** Z-score entry/exit signals trigger correctly
- [ ] **AC-005:** Half-life calculation uses AR(1) coefficient
- [ ] **AC-006:** All public methods have complete type hints
- [ ] **AC-007:** NumPy 2.0 compatibility
- [ ] **AC-008:** All functions have docstrings following Google style

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Pairs Trading):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate prices length >= formation_period | ✅ OK - Checks formation_period |
| Cointegration test | Gatev et al. (2006) | Use Engle-Granger ADF test | ✅ OK - Implemented with fallback |
| Hedge ratio OLS | Gatev et al. (2006) | β from regression of log prices | ✅ OK - np.polyfit on log prices |
| Half-life calculation | Pairs standard | HL = ln(2) / θ from AR(1) | ✅ OK - Implemented |
| Z-score entry | Gatev et al. (2006) | Entry at |Z| > 2.0 | ✅ OK - z_score_entry parameter |
| Z-score exit | Gatev et al. (2006) | Exit at |Z| < 0.5 | ✅ OK - z_score_exit parameter |
| Dollar neutral | Pairs standard | Long + Short = 0 | ✅ OK - ±50% weights |
| Stop loss / take profit | Risk management | ±3σ and ±1σ levels | ✅ OK - Implemented |
| Formation period | Gatev et al. (2006) | 12 months (252 days) to form pairs | ✅ OK - formation_period=252 |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ⚠️ PARTIAL - statsmodels is external lib |
| NaN handling | BASE_RULES.md (TRD-015) | Handle NaN in price data | ✅ FIXED - Filters NaN/inf with logging |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Gatev et al. (2006) for pairs trading rules.

---

## Dependencies
- **External:** `numpy`, `scipy` (stats), `statsmodels` (tsa.stattools), `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_pairs_trading.py:**
  - `test_cointegration_detection()` - ADF test correctly identifies cointegrated pairs
  - `test_hedge_ratio_calculation()` - OLS regression gives correct beta
  - `test_half_life_calculation()` - AR(1) coefficient gives correct HL
  - `test_z_score_entry_signal()` - Z > 2 triggers SHORT_LONG
  - `test_z_score_exit_signal()` - |Z| < 0.5 triggers close
  - `test_find_cointegrated_pairs()` - Returns top N pairs by p-value
  - `test_create_pair_position()` - Dollar-neutral weights (±50%)
  - `test_stop_loss_levels()` - ±3σ spread stops
  - `test_take_profit_levels()` - ±1σ spread targets
  - `test_simple_fallback_cointegration()` - Correlation-based fallback
  - `test_insufficient_data_handling()` - Skips pairs with < formation_period
  - `test_spread_calculation()` - Spread = log(A) - β*log(B)
  - `test_is_valid_pair()` - Validates cointegration + p-value + half-life

---

## Notes
- **Critical:** Pairs trading requires assets with strong economic relationship (same sector, commodity pairs)
- **Gatev et al. Reference:** "Pairs Trading: Performance of a Relative-Value Arbitrage Rule" (2006)
- **Cointegration:** Two series are cointegrated if spread is stationary (mean-reverting)
- **Engle-Granger Test:** (1) Estimate hedge ratio via OLS, (2) Test residuals for stationarity via ADF
- **Hedge Ratio:** β from regression log(price_A) = α + β × log(price_B) + ε
- **Spread:** Residuals from cointegration regression
- **Half-Life:** Time for spread to revert halfway to mean = ln(2)/θ
- **Z-Score Entry:** Default |Z| > 2.0 (spread is 2σ from mean)
- **Z-Score Exit:** Default |Z| < 0.5 (spread near mean)
- **Dollar Neutral:** Equal long/short exposure (e.g., +50%/-50%)
- **Formation Period:** 12 months (252 trading days) to identify pairs
- **Trading Period:** 6 months (126 trading days) to trade identified pairs
- **Maximum Half-Life:** 60 days (pairs with longer HL are too slow to trade)

---

**File Reference:** `app/domain/strategies/pairs_trading.py`
**Last Audited:** 2026-02-01
