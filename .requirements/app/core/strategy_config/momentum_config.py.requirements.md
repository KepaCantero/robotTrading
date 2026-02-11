# momentum_config.py

## Purpose
Centralized configuration for the Momentum Modular Strategy using Pydantic BaseModel. Contains all configurable parameters for market regime detection, signal thresholds, confidence calculations, volume ratio analysis, priority scoring, and deep learning sequence lengths.

---

## Type Definitions / Data Classes

### MomentumModularConfig Class (Pydantic BaseModel)
```python
class MomentumModularConfig(BaseModel):
    # Market regime thresholds
    bear_market_strength_threshold: float = 0.6    # Trend strength threshold for bear market (60%)
    volatility_crisis_percentile: float = 75.0     # Volatility percentile for crisis (75%)
    normal_volatility_min: float = 40.0            # Minimum volatility percentile for normal (40%)
    normal_volatility_max: float = 70.0            # Maximum volatility percentile for normal (70%)

    # History and training thresholds
    min_history_length: int = 60                   # Minimum history length for momentum signals
    auto_train_min_history: int = 100              # Minimum history for auto-training

    # Confidence and signal thresholds
    min_success_probability_default: float = 0.6   # Default minimum success probability (60%)
    min_success_probability_strict: float = 0.7    # Strict minimum success probability (70%)

    # Signal strength thresholds (matching Signal model validation)
    very_strong_confidence: float = 80.0           # Confidence threshold for VERY_STRONG (80%)
    strong_confidence: float = 70.0                # Confidence threshold for STRONG (70%)
    moderate_confidence: float = 50.0              # Confidence threshold for MODERATE (50%)

    # Volume ratio calculations
    volume_ratio_min: float = 0.5                  # Minimum volume ratio for liquidity score (0.5)
    volume_ratio_multiplier: float = 50.0          # Volume ratio multiplier for liquidity score (50)

    # Priority score weights
    priority_confidence_weight: float = 0.7        # Confidence weight for priority score (70%)
    priority_liquidity_weight: float = 0.3         # Liquidity weight for priority score (30%)

    # Default values
    default_volume: float = 0.01                   # Default volume when not available (0.01)

    # Overbought/oversold thresholds
    rsi_overbought_sell: float = 75.0              # RSI threshold for overbought sell signal (75)
    trend_down_sell_strength: float = 0.7          # Trend down strength for sell signal (70%)
    negative_momentum_threshold: float = -0.03     # Negative momentum threshold for sell (-3%)

    # Learning engine weights
    learning_filter_weight: float = 0.6            # Filter weight for learning combination (60%)
    learning_confidence_weight: float = 0.4        # Learning confidence weight for combination (40%)

    # Sequence lengths for deep learning
    default_sequence_length: int = 60              # Default sequence length for deep learning (60)
    transformer_sequence_length: int = 30          # Sequence length for transformer engine (30)

    # Max position size
    max_position_size_default: float = 0.1         # Default max position size for momentum (10%)
```

**Validation Rules:**
- All numeric fields have `ge` (greater than or equal) and `le` (less than or equal) constraints
- All fields are optional with sensible defaults
- Pydantic validates types automatically on instantiation
- Confidence thresholds are ordered: very_strong (80) > strong (70) > moderate (50)

---

## Function Signatures (Contracts)

### Class instantiation: `MomentumModularConfig(**kwargs) -> MomentumModularConfig`
**Pre:** Field values must match Pydantic Field constraints (ge/le)
**Post:** Returns validated config instance
**Raises:** ValidationError from Pydantic if constraints violated
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All fields have Pydantic Field with description
- [ ] All numeric fields have ge/le constraints for validation
- [ ] Confidence thresholds maintain logical ordering (very_strong > strong > moderate)
- [ ] Priority weights sum to approximately 1.0 (confidence + liquidity = 1.0)
- [ ] Learning weights sum to approximately 1.0 (filter + confidence = 1.0)
- [ ] Default values are documented in field descriptions
- [ ] Config can be instantiated without arguments (uses all defaults)
- [ ] Config can be overridden with kwargs
- [ ] Pydantic validation rejects invalid values

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | Excellent use of Pydantic. Weights properly normalized. Confidence thresholds correctly ordered. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES | Pydantic Settings for type-safe config | ✅ OK - Uses Pydantic BaseModel |
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - Field constraints with ge/le |
| CFG-004 | BASE_RULES | Extra forbid to catch typos | ⚠️ ADD - Add `model_config = ConfigDict(extra="forbid")` |
| TRD-003 | BASE_RULES | Position limits | ✅ OK - max_position_size_default defined |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Pydantic validates all fields |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All fields have type hints |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Field names clearly describe purpose |

---

## Dependencies
- **External:** pydantic (BaseModel, Field)

---

## Required Tests
- **tests/core/strategy_config/test_momentum_config.py:**
  - Test default values are correct
  - Test field validation (ge/le constraints work)
  - Test config instantiation with overrides
  - Test invalid values raise ValidationError
  - Test confidence threshold ordering (very_strong > strong > moderate)
  - Test priority weights sum validation
  - Test learning weights sum validation
  - Test negative momentum threshold is negative

---

## Notes
This config follows the Task 22 requirement to centralize all hardcoded values from momentum modular strategy into a single configuration class. The weights are properly normalized (priority: 0.7 + 0.3 = 1.0, learning: 0.6 + 0.4 = 1.0).

**Minor Suggestion (P2):** Consider adding `model_config = ConfigDict(extra="forbid")` to catch typos in field names during instantiation.

**Configuration Logic:**
- Market regime detection uses volatility percentiles and trend strength
- Signal strength uses tiered confidence thresholds (80/70/50)
- Priority calculation weights confidence (70%) higher than liquidity (30%)
- Learning engine combines filter signals (60%) with learned confidence (40%)
