# models.py

## Purpose
Data models for walk-forward validation, overfitting detection, regime detection, and parameter stability analysis (FASE 5.3). Provides type-safe data structures for validation workflows.

---

## Type Definitions / Data Classes

### OverfittingLevel Enum
```python
class OverfittingLevel(str, Enum):
    NONE = "none"      # No overfitting detected
    MILD = "mild"      # Slight overfitting, monitor
    MODERATE = "moderate"  # Moderate overfitting, action needed
    SEVERE = "severe"  # Severe overfitting, reject strategy
```

### StabilityLevel Enum
```python
class StabilityLevel(str, Enum):
    STABLE = "stable"       # Parameter is stable (CV < 30%)
    MODERATE = "moderate"   # Moderate variability
    UNSTABLE = "unstable"   # Highly unstable parameter
```

### RegimeType Enum
```python
class RegimeType(str, Enum):
    BULL = "bull"       # Bullish market with upward momentum
    BEAR = "bear"       # Bearish market with downward momentum
    NEUTRAL = "neutral" # Sideways/neutral market
```

### VolatilityRegime Enum
```python
class VolatilityRegime(str, Enum):
    LOW = "low"         # Volatility < historical median × 0.8
    NORMAL = "normal"   # Volatility within 0.8-1.2× median
    HIGH = "high"       # Volatility > historical median × 1.2
```

### TrendRegime Enum
```python
class TrendRegime(str, Enum):
    TREND = "trend"           # Strong trending market (R² > 0.7)
    RANGE = "range"           # Range-bound market
    TRANSITION = "transition" # Transitional phase
```

### WalkForwardConfig Class
```python
@dataclass
class WalkForwardConfig:
    train_period_months: int = 24    # REQUIRED - Training window size
    test_period_months: int = 6      # REQUIRED - Test window size
    step_months: int = 3             # REQUIRED - Roll-forward step size
    min_observations: int = 252      # REQUIRED - Min obs for training
    allow_overlap: bool = True       # OPTIONAL - Allow window overlap
    rebalance_frequency: str = "monthly"  # OPTIONAL - Rebalancing freq
    warmup_period: int = 20          # OPTIONAL - Warmup days
```

**Validation Rules:**
- `train_period_months >= 6` (minimum 6 months training)
- `test_period_months >= 1` (minimum 1 month testing)
- `step_months > 0` (must roll forward)
- `min_observations >= 100` (minimum statistical significance)

### PeriodResult Class
```python
@dataclass
class PeriodResult:
    period_id: UUID                  # REQUIRED - Unique identifier
    start_date: date                 # REQUIRED - Period start
    end_date: date                   # REQUIRED - Period end
    is_in_sample: bool               # REQUIRED - IS vs OS flag
    total_trades: int = 0            # REQUIRED - Trade count
    total_return: Decimal            # REQUIRED - Return percentage
    sharpe_ratio: Optional[Decimal]  # OPTIONAL - Sharpe ratio
    max_drawdown: Decimal            # REQUIRED - Max drawdown
    win_rate: Decimal                # REQUIRED - Win rate % (0-1)
    profit_factor: Optional[Decimal] # OPTIONAL - Profit factor
    parameters: Dict[str, Any]       # OPTIONAL - Strategy params
    trades: List[Any]                # OPTIONAL - Trade records
    equity_curve: List[Tuple[date, Decimal]]  # OPTIONAL - Daily equity
```

**Validation Rules:**
- `total_return >= -1` (cannot lose more than 100%)
- `max_drawdown <= 0` (drawdown is negative or zero)
- `0 <= win_rate <= 1` (percentage as decimal)
- `start_date < end_date` (valid date range)
- `len(equity_curve) > 0` implies dates are sequential

### WalkForwardResult Class
```python
@dataclass
class WalkForwardResult:
    is_results: List[PeriodResult]   # REQUIRED - In-sample results
    os_results: List[PeriodResult]   # REQUIRED - Out-of-sample results
    is_performance: Dict[str, Any]   # REQUIRED - IS aggregate metrics
    os_performance: Dict[str, Any]   # REQUIRED - OS aggregate metrics
    is_os_ratio: Decimal             # REQUIRED - OS/IS ratio
    consistency_score: Decimal       # REQUIRED - Consistency (0-100)
    num_periods: int                 # REQUIRED - Number of periods
    total_days: int                  # REQUIRED - Total test days
    recommendations: List[str]       # OPTIONAL - Action items
```

**Validation Rules:**
- `len(is_results) == len(os_results)` (paired periods)
- `num_periods == len(is_results)` (count consistency)
- `0 <= is_os_ratio <= 1` (degradation ratio)
- `0 <= consistency_score <= 100` (score bounds)
- `total_days > 0` (must test some days)

### OverfittingMetrics Class
```python
@dataclass
class OverfittingMetrics:
    is_sharpe: Decimal                       # REQUIRED - In-sample Sharpe
    os_sharpe: Decimal                       # REQUIRED - Out-of-sample Sharpe
    degradation_ratio: Decimal               # REQUIRED - OS/IS Sharpe ratio
    is_return: Decimal                       # REQUIRED - In-sample return
    os_return: Decimal                       # REQUIRED - Out-of-sample return
    return_degradation: Decimal              # REQUIRED - OS/IS return ratio
    overfitting_probability: float           # REQUIRED - Probability (0-1)
    overfitting_level: OverfittingLevel      # REQUIRED - Severity level
    recommendations: List[str]               # OPTIONAL - Recommendations
    whites_reality_pvalue: Optional[float]   # OPTIONAL - White's test p-value
    mcs_pvalue: Optional[float]              # OPTIONAL - MCS test p-value
    parameter_stability_score: Decimal       # REQUIRED - Stability (0-100)
```

**Validation Rules:**
- `is_sharpe >= 0` (Sharpe cannot be negative for valid comparison)
- `0 <= degradation_ratio <= 1` (OS is always worse than IS)
- `0 <= overfitting_probability <= 1` (probability bounds)
- `0 <= parameter_stability_score <= 100` (score bounds)

### MarketRegime Class
```python
@dataclass
class MarketRegime:
    regime_type: RegimeType             # REQUIRED - Bull/bear/neutral
    volatility_regime: VolatilityRegime  # REQUIRED - Vol regime
    trend_regime: TrendRegime            # REQUIRED - Trend type
    confidence: float                    # REQUIRED - Detection confidence (0-1)
    start_date: date                     # REQUIRED - Regime start
    end_date: Optional[date]             # OPTIONAL - Regime end (None if ongoing)
    expected_duration: Optional[int]     # OPTIONAL - Expected days
    characteristics: Dict[str, Any]      # OPTIONAL - Additional metrics
```

**Validation Rules:**
- `0 <= confidence <= 1` (probability bounds)
- `end_date is None or end_date > start_date` (valid if provided)
- `expected_duration > 0` if provided (positive days)

### RegimeConfig Class
```python
@dataclass
class RegimeConfig:
    lookback_period: int = 50        # REQUIRED - Analysis lookback days
    volatility_threshold: float = 1.2 # REQUIRED - Volatility multiplier
    trend_threshold: float = 0.01    # REQUIRED - Minimum slope
    sma_short: int = 50              # REQUIRED - Short SMA period
    sma_long: int = 200              # REQUIRED - Long SMA period
    volatility_window: int = 20      # REQUIRED - Volatility window
    use_hmm: bool = False            # OPTIONAL - Use Hidden Markov Models
```

**Validation Rules:**
- `lookback_period > 0` (must look back at least 1 day)
- `volatility_threshold > 1.0` (threshold must be > 1)
- `sma_short < sma_long` (short must be shorter than long)
- `volatility_window > 0` (must calculate vol over window)

### ParameterStabilityResult Class
```python
@dataclass
class ParameterStabilityResult:
    parameter_name: str           # REQUIRED - Parameter identifier
    is_mean: Decimal              # REQUIRED - In-sample mean
    is_std: Decimal               # REQUIRED - In-sample std
    os_mean: Decimal              # REQUIRED - Out-of-sample mean
    os_std: Decimal               # REQUIRED - Out-of-sample std
    stability_score: Decimal      # REQUIRED - Stability (0-100)
    stability_level: StabilityLevel # REQUIRED - Classification
    drift_detected: bool          # REQUIRED - Drift flag
    recommendation: str           # REQUIRED - Action recommendation
    coefficient_of_variation: Decimal # REQUIRED - CV = std/mean
```

**Validation Rules:**
- `is_std >= 0` and `os_std >= 0` (std is non-negative)
- `0 <= stability_score <= 100` (score bounds)
- `coefficient_of_variation >= 0` (CV is non-negative)

### RegimeTransitionMatrix Class
```python
@dataclass
class RegimeTransitionMatrix:
    matrix: Dict[str, Dict[str, float]]  # REQUIRED - 3x3 transition matrix
    regimes: List[str]                    # REQUIRED - Regime names
    expected_durations: Dict[str, float]  # REQUIRED - Duration per regime (days)
    last_update: datetime                 # REQUIRED - Last update time
```

**Validation Rules:**
- `len(matrix) == 3` (3x3 matrix for bull/bear/neutral)
- For each row in matrix: `abs(sum(row.values()) - 1.0) < 0.01` (probabilities sum to 1)
- `all(0 <= p <= 1 for p in matrix.values())` (valid probabilities)
- `all(d > 0 for d in expected_durations.values())` (positive durations)

---

## Function Signatures (Contracts)

### `WalkForwardResult.get_degradation_summary() -> Dict[str, Any]`
**Pre:** `is_performance` and `os_performance` contain valid metrics
**Post:** Returns dict with `sharpe_degradation`, `return_degradation`, `avg_degradation`
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `OverfittingMetrics.is_overfitted() -> bool`
**Pre:** None
**Post:** Returns True if `overfitting_level in [MODERATE, SEVERE]`
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `MarketRegime.description() -> str`
**Pre:** None
**Post:** Returns human-readable regime description with all three components
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `MarketRegime.is_favorable_for_trend_following() -> bool`
**Pre:** None
**Post:** Returns True if `regime_type == BULL and trend_regime == TREND`
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `MarketRegime.is_favorable_for_mean_reversion() -> bool`
**Pre:** None
**Post:** Returns True if `volatility_regime == HIGH and trend_regime == RANGE`
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `ParameterStabilityResult.is_stable() -> bool`
**Pre:** None
**Post:** Returns True if `stability_level == STABLE`
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeTransitionMatrix.get_transition_probability(from_regime: str, to_regime: str) -> float`
**Pre:** `from_regime` and `to_regime` are valid regime names
**Post:** Returns transition probability (0-1) or 0.0 if not found
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `RegimeTransitionMatrix.get_expected_duration(regime: str) -> Optional[float]`
**Pre:** None
**Post:** Returns expected duration in days or None if regime not found
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] All enums have string values matching their keys (e.g., `BULL.value == "bull"`)
- [ ] All dataclass fields with `Decimal` defaults use `Decimal("0")` not `0`
- [ ] All optional fields have `Optional` type hint and default `None` or empty collection
- [ ] `WalkForwardResult.get_degradation_summary()` handles zero division safely
- [ ] `OverfittingMetrics.is_overfitted()` returns False for NONE and MILD levels
- [ ] `MarketRegime.description()` returns non-empty string for all combinations
- [ ] `RegimeTransitionMatrix` validates probabilities sum to ~1.0 (±0.01)
- [ ] All dataclasses use `field(default=...)` for defaults (not `=` directly)
- [ ] UUID fields use `field(default_factory=uuid4)` not `default=None`
- [ ] All `Dict[str, Any]` fields use `field(default_factory=dict)`

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
| TYP-002 | 02-type-hints.md | Use modern syntax (list, dict, X \| None) | ✅ OK |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - Uses field(default_factory=list/dict) |
| ARCH-006 | 05-architecture.md | Value objects immutable | ⚠️ NOT APPLIED - Uses @dataclass without frozen=True |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK |
| BT-002 | BASE_RULES.md | Out-of-sample testing required | ✅ OK - PeriodResult has is_in_sample flag |
| TRD-007 | BASE_RULES.md | Annualization documented | ✅ OK - TRADING_DAYS = 252 referenced |
| RSK-001 | BASE_RULES.md | VaR calculation | ⚠️ NOT APPLIED - Not in scope for models |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:**
  - `dataclasses` (standard library)
  - `datetime` (standard library)
  - `decimal.Decimal` (standard library)
  - `enum.Enum` (standard library)
  - `typing` (standard library)
  - `uuid.UUID, uuid4` (standard library)
  - `pydantic` (optional - with fallback)

- **Internal:** None (pure models module)

---

## Required Tests
- **tests/unit/backtesting/validation/test_models.py:**
  - Test enum values match keys
  - Test dataclass field defaults (especially mutable collections)
  - Test `WalkForwardResult.get_degradation_summary()` with zero Sharpe/return
  - Test `OverfittingMetrics.is_overfitted()` for all levels
  - Test `MarketRegime.description()` for all regime combinations
  - Test `MarketRegime.is_favorable_for_trend_following()` logic
  - Test `MarketRegime.is_favorable_for_mean_reversion()` logic
  - Test `ParameterStabilityResult.is_stable()` for all levels
  - Test `RegimeTransitionMatrix.get_transition_probability()` with valid/invalid regimes
  - Test `RegimeTransitionMatrix.get_expected_duration()` with valid/invalid regimes
  - Test validation of transition probabilities (sum to 1.0)
  - Test Pydantic fallback when not available
  - Test UUID generation is unique
  - Test Decimal precision preservation

---

## Notes
- This is a pure data models module with no business logic
- All models are serializable via `to_dict()` methods (TomasiniWindowResult, etc.)
- Pydantic is optional with fallback to standard dataclasses
- All enums use string values for JSON serialization compatibility
- Decimal type used for financial precision (no floating point rounding errors)
- These models support Tomasini walk-forward validation methodology
