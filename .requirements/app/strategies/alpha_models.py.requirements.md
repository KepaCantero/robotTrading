# alpha_models.py

## Purpose
Implements the Alpha Model architecture from Rishi Narang's "Inside the Black Box" framework. Provides alpha generation, signal generation with confidence levels, alpha decay analysis, and multi-factor alpha models for quantitative trading strategies.

---

## Type Definitions / Data Classes

### AlphaType (Enum)
```python
class AlphaType(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MACRO = "macro"
    MACHINE_LEARNING = "machine_learning"
```

### AlphaDecayRegime (Enum)
```python
class AlphaDecayRegime(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"
    NONE = "none"
```

### AlphaSignal (dataclass)
```python
@dataclass
class AlphaSignal:
    symbol: str                              # REQUIRED - Trading symbol
    alpha_type: AlphaType                    # REQUIRED - Type of alpha model
    direction: SignalType                    # REQUIRED - BUY or SELL
    raw_alpha: float                         # REQUIRED - Raw alpha value (expected return)
    confidence: float                        # REQUIRED - 0-1, probability of positive return
    expected_return: float                   # REQUIRED - Expected return in basis points
    holding_period_days: int                 # REQUIRED - Expected holding period
    decay_regime: AlphaDecayRegime           # REQUIRED - Decay pattern
    decay_half_life: Optional[int] = None    # OPTIONAL - Days until alpha loses half value
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### AlphaDecayMetrics (dataclass)
```python
@dataclass
class AlphaDecayMetrics:
    symbol: str                              # REQUIRED - Symbol analyzed
    alpha_type: AlphaType                    # REQUIRED - Alpha model type
    total_observations: int                  # REQUIRED - Number of observations
    decay_regime: AlphaDecayRegime           # REQUIRED - Detected decay pattern
    half_life_days: float                    # REQUIRED - Half-life in days
    decay_rate: float                        # REQUIRED - For exponential decay
    predictive_power_by_day: Dict[int, float] # REQUIRED - Day -> R²
    is_significant: bool                     # REQUIRED - Statistical significance
```

---

## Function Signatures (Contracts)

### `AlphaModel.generate_alpha(symbol: str, market_data: pd.DataFrame, timestamp: datetime) -> Optional[AlphaSignal]`
**Pre:** market_data contains required columns (close, volume)
**Post:** Returns AlphaSignal if alpha detected, None otherwise
**Raises:** None (returns None on error)
**Retry:** No
**Side Effects:** Appends to signal_history

### `AlphaModel.analyze_alpha_decay(symbol: str, realized_returns: pd.Series, signal_dates: List[datetime], min_observations: int = 30) -> Optional[AlphaDecayMetrics]`
**Pre:** realized_returns length >= min_observations
**Post:** Returns AlphaDecayMetrics with decay analysis
**Raises:** None (returns None on insufficient data)
**Retry:** No
**Side Effects:** None

### `AlphaModel.combine_alpha_signals(signals: List[AlphaSignal], method: str = "weighted") -> Optional[AlphaSignal]`
**Pre:** signals is non-empty list
**Post:** Returns combined AlphaSignal or None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `AlphaSignal.to_signal(price: Decimal) -> Signal`
**Pre:** price > 0
**Post:** Returns trading Signal with mapped fields
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_alpha_model(config: Dict[str, Any]) -> AlphaModel`
**Pre:** config contains 'model_type' key
**Post:** Returns AlphaModel instance
**Raises:** ValueError if unknown model_type
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Alpha signal generation includes direction, confidence, and expected return
- [ ] Alpha decay analysis correctly identifies linear/exponential/step/none regimes
- [ ] Half-life calculation uses predictive power threshold
- [ ] Multi-factor ensemble combines signals using weighted or voting method
- [ ] Factory function creates correct model type based on config
- [ ] Signal conversion maps AlphaType to SignalSource correctly
- [ ] Volatility calculation uses annualized standard deviation
- [ ] Confidence scoring normalizes to 0-1 range

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T12:00:00Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-python-expert (via Tech Lead Orchestrator) |
| **GAPs Fixed** | 0 / ? total |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| LOG-001 | BASE_RULES | Structured logging | ❌ GAP - Uses f-strings in logger calls (line 191, 622) |
| LOG-004 | BASE_RULES | Error logging with stack traces | ✅ FIXED - Added exc_info=True (line 191, 622) |
| CC-006 | BASE_RULES | Explicit error handling | ❌ GAP - Generic Exception caught (line 190, 621) |
| TRD-001 | BASE_RULES | Validate mathematical relationships | ✅ OK - Formulas validated |
| ARCH-004 | BASE_RULES | Small functions (<20 lines) | ⚠️ PARTIAL - Some functions >20 lines |
| TYP-003 | BASE_RULES | No Any without justification | ⚠️ PARTIAL - Uses Any in metadata (line 78) |

---

## Dependencies
- **External:** numpy, pandas, decimal, datetime, enum, typing, logging, abc, dataclasses
- **Internal:** app.models.signal (Signal, SignalSource, SignalStrength, SignalType)

---

## Required Tests
- **tests/strategies/test_alpha_models.py:**
  - Test AlphaSignal.to_signal conversion
  - Test MomentumAlphaModel.generate_alpha with sufficient data
  - Test MomentumAlphaModel.generate_alpha with insufficient data
  - Test MeanReversionAlphaModel.generate_alpha with z-score threshold
  - Test analyze_alpha_decay with exponential regime
  - Test analyze_alpha_decay with insufficient observations
  - Test combine_alpha_signals weighted method
  - Test combine_alpha_signals voting method
  - Test get_alpha_model factory with valid types
  - Test get_alpha_model factory with invalid type

---

## Notes
- Reference: Rishi Narang "Inside the Black Box" Chapter 3
- Alpha decay is critical for optimal holding period selection
- Confidence levels should be calibrated against historical performance
- Multi-factor models should use orthogonal alpha sources
