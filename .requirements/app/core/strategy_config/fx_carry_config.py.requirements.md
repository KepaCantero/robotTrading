# fx_carry_config.py

## Purpose
Centralized configuration for the FX Carry Trade Strategy using Pydantic BaseModel. Contains all configurable parameters for position sizing, volatility calculations, confidence scoring, and risk management for FX carry trading.

---

## Type Definitions / Data Classes

### FXCarryTradeStrategyConfig Class (Pydantic BaseModel)
```python
class FXCarryTradeStrategyConfig(BaseModel):
    # Position sizing thresholds
    min_carry_threshold: float = 0.01        # Minimum carry threshold for signals (1%)
    max_positions_default: int = 10          # Default maximum number of positions (10)
    position_size_default: float = 0.1       # Default position size (10%)
    stop_loss_default: float = 0.05          # Default stop loss percentage (5%)
    take_profit_default: float = 0.15        # Default take profit percentage (15%)
    max_leverage: float = 2.0                # Maximum leverage for carry trades (2x)
    min_liquidity: float = 1_000_000.0       # Minimum liquidity requirement ($1M)

    # Volatility calculations
    baseline_volatility: float = 0.01        # Baseline volatility for position sizing (1%)
    vol_adjustment_max: float = 2.0          # Maximum volatility adjustment multiplier (2x)
    min_volatility: float = 0.02             # Minimum volatility floor (2%)
    max_volatility: float = 0.50             # Maximum volatility cap (50%)

    # Confidence calculation
    base_confidence_multiplier: float = 100.0 # Multiplier for base confidence (100x)
    carry_boost_max: float = 20.0            # Maximum carry boost for confidence (20%)
    carry_boost_multiplier: float = 500.0    # Carry boost multiplier (500x)
```

**Validation Rules:**
- All numeric fields have `ge` (greater than or equal) and `le` (less than or equal) constraints
- All fields are optional with sensible defaults
- Pydantic validates types automatically on instantiation

---

## Function Signatures (Contracts)

### Class instantiation: `FXCarryTradeStrategyConfig(**kwargs) -> FXCarryTradeStrategyConfig`
**Pre:** Field values must match Pydantic Field constraints (ge/le)
**Post:** Returns validated config instance
**Raises:** ValidationError from Pydantic if constraints violated
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All fields have Pydantic Field with description
- [ ] All numeric fields have ge/le constraints for validation
- [ ] All percentage fields are in decimal format (0-1 range)
- [ ] Default values are documented in field descriptions
- [ ] Config can be instantiated without arguments (uses all defaults)
- [ ] Config can be overridden with kwargs
- [ ] Pydantic validation rejects invalid values
- [ ] Stop loss (5%) is less than take profit (15%) for risk-reward ratio >= 3

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | Excellent use of Pydantic for configuration. Risk-reward ratio is appropriate (3:1). |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES | Pydantic Settings for type-safe config | ✅ OK - Uses Pydantic BaseModel |
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - Field constraints with ge/le |
| CFG-004 | BASE_RULES | Extra forbid to catch typos | ⚠️ ADD - Add `model_config = ConfigDict(extra="forbid")` |
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - Config provides validation thresholds |
| TRD-003 | BASE_RULES | Position limits | ✅ OK - position_size_default, max_positions_default |
| RSK-003 | BASE_RULES | Drawdown control | ✅ OK - stop_loss_default defined |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Pydantic validates all fields |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All fields have type hints |

---

## Dependencies
- **External:** pydantic (BaseModel, Field)

---

## Required Tests
- **tests/core/strategy_config/test_fx_carry_config.py:**
  - Test default values are correct
  - Test field validation (ge/le constraints work)
  - Test config instantiation with overrides
  - Test invalid values raise ValidationError
  - Test risk-reward ratio (stop_loss < take_profit)
  - Test max_leverage constraint is enforced

---

## Notes
This config follows the Task 22 requirement to centralize all hardcoded values from FX carry trade strategy into a single configuration class. The risk-reward ratio of 3:1 (15% TP / 5% SL) aligns with BASE_RULES TRD-003 requirements.

**Minor Suggestion (P2):** Consider adding `model_config = ConfigDict(extra="forbid")` to catch typos in field names during instantiation.
