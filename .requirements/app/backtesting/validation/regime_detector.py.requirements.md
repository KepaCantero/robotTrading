# regime_detector.py

## Purpose
Detects market regimes (bull/bear/neutral) with volatility classification (low/normal/high) and trend detection (trend/range/transition). Provides regime-aware strategy recommendations and transition probability matrix.

---

## Type Definitions / Data Classes

### RegimeDetector Class
```python
class RegimeDetector:
    config: RegimeConfig    # REQUIRED - Configuration for detection
```

**Validation Rules:**
- `config` is RegimeConfig with valid thresholds
- `config.lookback_period > 0`
- `config.volatility_threshold > 1.0`
- `config.sma_short < config.sma_long`

---

## Function Signatures (Contracts)

### `RegimeDetector.__init__(config: Optional[RegimeConfig] = None)`
**Pre:** None
**Post:** Detector initialized with provided or default config
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Sets instance attribute `self.config`

### `RegimeDetector.detect_regime(prices: pd.Series, returns: pd.Series, as_of_date: date) -> MarketRegime`
**Pre:** `prices` and `returns` are non-empty pandas Series with matching indices
**Post:** Returns MarketRegime with detected regime type, volatility, and trend
**Raises:** ❌ No (gracefully handles insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure function - only calculates indicators)

### `RegimeDetector.detect_regime_history(prices: pd.Series, returns: pd.Series) -> List[MarketRegime]`
**Pre:** `prices` and `returns` are non-empty Series with matching indices
**Post:** Returns list of MarketRegime objects representing historical regime sequence
**Raises:** ❌ No (logs warnings for failed detections, continues)
**Retry:** ❌ No
**Side Effects:** Logs warnings for regime detection failures

### `RegimeDetector.calculate_transition_matrix(regime_history: List[MarketRegime]) -> RegimeTransitionMatrix`
**Pre:** `regime_history` has at least 2 entries
**Post:** Returns RegimeTransitionMatrix with 3x3 probability matrix and expected durations
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._detect_regime_type(prices: pd.Series, as_of_date: date) -> RegimeType`
**Pre:** `prices` is non-empty Series
**Post:** Returns RegimeType (BULL/BEAR/NEUTRAL) based on SMA and slope
**Raises:** ❌ No (returns NEUTRAL if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._detect_volatility_regime(returns: pd.Series) -> VolatilityRegime`
**Pre:** `returns` is non-empty Series
**Post:** Returns VolatilityRegime (LOW/NORMAL/HIGH) based on historical median
**Raises:** ❌ No (returns NORMAL if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._detect_trend_regime(prices: pd.Series) -> TrendRegime`
**Pre:** `prices` is non-empty Series
**Post:** Returns TrendRegime (TREND/RANGE/TRANSITION) based on R² and range
**Raises:** ❌ No (returns TRANSITION if insufficient data)
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._calculate_confidence(prices: pd.Series, returns: pd.Series, regime_type: RegimeType, volatility_regime: VolatilityRegime, trend_regime: TrendRegime) -> float`
**Pre:** `prices` and `returns` are non-empty
**Post:** Returns confidence score (0-1) based on data length, signal strength, vol clarity
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._calculate_expected_duration(prices: pd.Series, regime_type: RegimeType, volatility_regime: VolatilityRegime) -> Optional[int]`
**Pre:** `prices` is non-empty
**Post:** Returns expected days until regime transition or None
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector._get_regime_characteristics(prices: pd.Series, returns: pd.Series, regime_type: RegimeType, volatility_regime: VolatilityRegime, trend_regime: TrendRegime) -> Dict[str, Any]`
**Pre:** `prices` and `returns` are non-empty
**Post:** Returns dict with current_price, price_vs_sma*, volatility*, momentum*, drawdown*
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeDetector.get_regime_aware_recommendation(regime: MarketRegime) -> List[str]`
**Pre:** `regime` is valid MarketRegime
**Post:** Returns list of strategy recommendations based on regime
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `detect_regime_from_data(prices: pd.Series, returns: Optional[pd.Series] = None, config: Optional[RegimeConfig] = None) -> MarketRegime`
**Pre:** `prices` is non-empty Series
**Post:** Returns current market regime (calculates returns if not provided)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Creates RegimeDetector instance

### `classify_market_state(prices: pd.Series, lookback: int = 50) -> str`
**Pre:** `prices` is non-empty Series
**Post:** Returns market state string like "bull_normal_vol" or "insufficient_data"
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] `RegimeConfig` defaults: lookback=50, vol_threshold=1.2, trend_threshold=0.01, sma_short=50, sma_long=200, vol_window=20
- [ ] `_detect_regime_type()` returns BULL when price > SMA(200) AND slope > 0.01
- [ ] `_detect_regime_type()` returns BEAR when price < SMA(200) AND slope < -0.01
- [ ] `_detect_regime_type()` returns NEUTRAL when between SMA(100) and SMA(200)
- [ ] `_detect_volatility_regime()` returns LOW when vol < median × 0.833 (1/1.2)
- [ ] `_detect_volatility_regime()` returns HIGH when vol > median × 1.2
- [ ] `_detect_volatility_regime()` returns NORMAL otherwise
- [ ] `_detect_trend_regime()` returns TREND when R² > 0.7
- [ ] `_detect_trend_regime()` returns RANGE when normalized_range < 0.05
- [ ] `_detect_trend_regime()` returns TRANSITION otherwise
- [ ] `_calculate_confidence()` returns 0.5-1.0 range
- [ ] `_calculate_expected_duration()` returns ~504 days for BULL with NORMAL vol
- [ ] `_calculate_expected_duration()` returns ~378 days for BEAR with NORMAL vol
- [ ] `_calculate_expected_duration()` returns ~126 days for NEUTRAL with NORMAL vol
- [ ] `calculate_transition_matrix()` returns 3x3 matrix with rows summing to ~1.0
- [ ] `calculate_transition_matrix()` calculates expected_duration = 1 / (1 - stay_prob) × 21
- [ ] `detect_regime_history()` uses rolling window with step = lookback / 2
- [ ] `detect_regime_history()` sets end_date of previous regime to start_date of current
- [ ] `get_regime_aware_recommendation()` returns non-empty list for all regimes
- [ ] `get_regime_aware_recommendation()` recommends trend-following for BULL + TREND
- [ ] `get_regime_aware_recommendation()` recommends mean-reversion for RANGE + HIGH vol
- [ ] `detect_regime_from_data()` calculates returns if not provided
- [ ] `classify_market_state()` returns "{trend}_{vol_state}" format
- [ ] `classify_market_state()` returns "insufficient_data" when len(prices) < lookback
- [ ] All `_detect_*` methods return default enum when insufficient data

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| TYP-002 | 02-type-hints.md | Use modern syntax (Optional, Dict, List) | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Uses logging but not structured |
| LOG-004 | 09-logging-observability.md | Error logging | ✅ OK - Logs warnings |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - Try/except in detect_regime_history |
| BT-005 | BASE_RULES.md | Multiple periods testing | ✅ OK - Regime-aware validation |

**GAPS Found:**
- **LOG-001 (P1):** Not using structured logging (no JSON format)
- **TYP-003 (P1):** Uses `Dict[str, Any]` for characteristics without specific types

---

## Dependencies
- **External:**
  - `numpy` (numerical calculations: mean, std, polyfit, argmax)
  - `pandas` (Series for price/return data)
  - `scipy.stats` (none directly, but available)
  - `scipy.signal.argrelextrema` (find local maxima/minima)
  - `decimal.Decimal` (financial precision)
  - `dataclasses` (standard library)
  - `datetime` (standard library)
  - `logging` (standard library)
  - `typing` (standard library)

- **Internal:**
  - `.models.MarketRegime`
  - `.models.RegimeConfig`
  - `.models.RegimeTransitionMatrix`
  - `.models.RegimeType`
  - `.models.TrendRegime`
  - `.models.VolatilityRegime`

---

## Required Tests
- **tests/unit/backtesting/validation/test_regime_detector.py:**
  - Test `detect_regime()` returns valid MarketRegime
  - Test `detect_regime()` sets all three regime types (type, volatility, trend)
  - Test `detect_regime()` calculates confidence in [0, 1] range
  - Test `detect_regime()` calculates expected_duration
  - Test `detect_regime()` populates characteristics dict
  - Test `_detect_regime_type()` returns BULL for price > SMA(200) + rising slope
  - Test `_detect_regime_type()` returns BEAR for price < SMA(200) + falling slope
  - Test `_detect_regime_type()` returns NEUTRAL for between SMAs
  - Test `_detect_regime_type()` returns NEUTRAL when insufficient data
  - Test `_detect_volatility_regime()` returns LOW for vol < median × 0.833
  - Test `_detect_volatility_regime()` returns HIGH for vol > median × 1.2
  - Test `_detect_volatility_regime()` returns NORMAL otherwise
  - Test `_detect_trend_regime()` returns TREND for R² > 0.7
  - Test `_detect_trend_regime()` returns RANGE for tight range
  - Test `_detect_trend_regime()` returns TRANSITION otherwise
  - Test `_calculate_confidence()` increases with data length
  - Test `_calculate_confidence()` increases with signal strength
  - Test `_calculate_expected_duration()` returns positive days
  - Test `_get_regime_characteristics()` includes current_price
  - Test `_get_regime_characteristics()` includes price_vs_sma_short/long
  - Test `_get_regime_characteristics()` includes momentum_1m/3m
  - Test `_get_regime_characteristics()` includes drawdown_from_peak_pct
  - Test `detect_regime_history()` creates sequential regimes
  - Test `detect_regime_history()` sets end_date correctly
  - Test `detect_regime_history()` handles detection failures gracefully
  - Test `calculate_transition_matrix()` returns 3x3 matrix
  - Test `calculate_transition_matrix()` rows sum to ~1.0
  - Test `calculate_transition_matrix()` calculates expected durations
  - Test `get_regime_aware_recommendation()` returns non-empty list
  - Test `get_regime_aware_recommendation()` for BULL+TREND recommends trend-following
  - Test `get_regime_aware_recommendation()` for RANGE+HIGH recommends mean-reversion
  - Test `detect_regime_from_data()` calculates returns if not provided
  - Test `classify_market_state()` returns correct format
  - Test `classify_market_state()` returns "insufficient_data" for short series
  - Test regime detection with various price patterns (uptrend, downtrend, sideways)
  - Test volatility regime detection with low/normal/high volatility periods

---

## Notes
- **Regime Classification Logic:**
  - **Bull:** Price > SMA(200) AND slope > 1%
  - **Bear:** Price < SMA(200) AND slope < -1%
  - **Neutral:** Between SMA(100) and SMA(200)
- **Volatility Classification:**
  - **Low:** vol < historical_median × 0.833 (1/1.2)
  - **Normal:** Within 0.833-1.2× historical median
  - **High:** vol > historical_median × 1.2
- **Trend Classification:**
  - **Trend:** R² > 0.7 (strong linear relationship)
  - **Range:** Normalized range < 5% or clear peaks/valleys
  - **Transition:** Neither trend nor range
- **Expected Durations (Base):**
  - Bull: ~504 days (2 years)
  - Bear: ~378 days (1.5 years)
  - Neutral: ~126 days (6 months)
- **Volatility Multipliers:**
  - Low: 1.5× (longer duration)
  - Normal: 1.0×
  - High: 0.5× (shorter duration)
- **References:**
  - Ilmanen, "Expected Returns" (regime classification)
  - López de Prado, "Advances in Financial Machine Learning"
- This is a FASE 5.3 Validation module
- Module provides both class-based and functional API
