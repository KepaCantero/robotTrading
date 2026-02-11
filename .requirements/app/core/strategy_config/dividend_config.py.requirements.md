# dividend_config.py

## Purpose
Centralized configuration for the Dividend Strategy using Pydantic BaseModel. Contains all configurable parameters for dividend yield screening, portfolio construction, payout ratio validation, and signal strength calculations.

---

## Type Definitions / Data Classes

### DividendStrategyConfig Class (Pydantic BaseModel)
```python
class DividendStrategyConfig(BaseModel):
    # Dividend yield thresholds
    min_yield_default: float = 3.0            # Default minimum dividend yield (3%)
    max_yield_default: float = 15.0           # Default maximum dividend yield (15%)

    # Portfolio construction
    portfolio_size_default: int = 25          # Default portfolio size (25 stocks)
    max_sector_weight_default: float = 0.30   # Default max sector weight (30%)
    max_single_position_default: float = 0.05 # Default max single position (5%)

    # Payout ratio thresholds
    max_payout_ratio_default: float = 70.0    # Default max payout ratio (70%)
    payout_ratio_critical: float = 100.0      # Critical payout ratio threshold (100%)

    # Dividend coverage
    min_coverage_ratio: float = 0.8           # Minimum dividend coverage ratio (0.8)

    # Quality score thresholds
    quality_multiplier: float = 0.7           # Quality score multiplier for deterioration (70%)
    default_quality_score: float = 70.0       # Default quality score for signals (70%)

    # Dividend capture
    min_days_before_ex_dividend: int = 5      # Minimum days before ex-dividend for capture (5)

    # Signal strength thresholds
    strong_yield_threshold: float = 5.0       # Yield threshold for strong signal (5%)
    moderate_yield_threshold: float = 4.0     # Yield threshold for moderate signal (4%)

    # Priority calculation
    priority_confidence_weight: float = 0.6   # Confidence weight for priority (60%)
    priority_yield_weight: float = 5.0        # Yield weight for priority (5x)

    # Default scores
    default_liquidity_score: float = 80.0     # Default liquidity score (80%)
    sell_confidence: float = 70.0             # Default confidence for sell signals (70%)
    sell_priority: float = 60.0               # Default priority for sell signals (60%)
```

**Validation Rules:**
- All numeric fields have `ge` (greater than or equal) and `le` (less than or equal) constraints
- All fields are optional with sensible defaults
- Pydantic validates types automatically on instantiation

---

## Function Signatures (Contracts)

### Class instantiation: `DividendStrategyConfig(**kwargs) -> DividendStrategyConfig`
**Pre:** Field values must match Pydantic Field constraints (ge/le)
**Post:** Returns validated config instance
**Raises:** ValidationError from Pydantic if constraints violated
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All fields have Pydantic Field with description
- [ ] All numeric fields have ge/le constraints for validation
- [ ] All percentage fields are in decimal format (0-1 or 0-100 consistently)
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
| **Notes** | Excellent use of Pydantic for configuration. All constraints properly defined. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES | Pydantic Settings for type-safe config | ✅ OK - Uses Pydantic BaseModel |
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - Field constraints with ge/le |
| CFG-004 | BASE_RULES | Extra forbid to catch typos | ⚠️ ADD - Add `model_config = ConfigDict(extra="forbid")` |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Pydantic validates all fields |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All fields have type hints |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Field names clearly describe purpose |

---

## Dependencies
- **External:** pydantic (BaseModel, Field)

---

## Required Tests
- **tests/core/strategy_config/test_dividend_config.py:**
  - Test default values are correct
  - Test field validation (ge/le constraints work)
  - Test config instantiation with overrides
  - Test invalid values raise ValidationError
  - Test all fields are accessible

---

## Notes
This config follows the Task 22 requirement to centralize all hardcoded values from dividend strategy into a single configuration class. All values were extracted from dividend/dividend_strategy.py hardcoded values.

**Minor Suggestion (P2):** Consider adding `model_config = ConfigDict(extra="forbid")` to catch typos in field names during instantiation.
