# risk_configurator.py

## Purpose
Domain service that maps user risk tolerance to concrete risk parameters. Implements the Single Responsibility Principle by handling only risk configuration mapping.

---

## Type Definitions / Data Classes

### RiskConfigurator Class
```python
class RiskConfigurator:
    """Configure risk parameters based on risk tolerance."""
```

**Validation Rules:**
- Only accepts RiskTolerance enum values (BAJO, MEDIO, ALTO)
- Returns RiskConfig dataclass with validated Decimal parameters
- Raises ValueError for unrecognized risk tolerance levels

---

## Function Signatures (Contracts)

### `configure(tolerance: RiskTolerance) -> RiskConfig`
**Pre:** tolerance is valid RiskTolerance enum (BAJO, MEDIO, or ALTO)
**Post:** Returns RiskConfig with parameters mapped to tolerance level
**Raises:** ValueError if tolerance is not recognized
**Retry:** No
**Side Effects:** Logs debug message with configured level

**Risk Mapping Table:**
| tolerance | max_drawdown | max_position_size | leverage_allowed | max_leverage |
|-----------|--------------|-------------------|-----------------|--------------|
| BAJO      | 15%          | 5%                | False           | 1.0x         |
| MEDIO     | 25%          | 10%               | True            | 1.5x         |
| ALTO      | 40%          | 20%               | True            | 2.0x         |

### `configure_for_profile(risk_tolerance: str | RiskTolerance) -> RiskConfig`
**Pre:** risk_tolerance is valid string or RiskTolerance enum
**Post:** Returns RiskConfig with parameters mapped to tolerance level
**Raises:** ValueError if risk_tolerance string is not recognized
**Retry:** No
**Side Effects:** None

### `get_all_configs() -> dict[RiskTolerance, RiskConfig]`
**Pre:** None
**Post:** Returns dictionary mapping all risk tolerance levels to their configs
**Raises:** None
**Retry:** No
**Side Effects:** None

### `compare_configs(tolerance1: RiskTolerance, tolerance2: RiskTolerance) -> dict`
**Pre:** Both tolerances are valid RiskTolerance enum values
**Post:** Returns dictionary comparing key parameters between two levels
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] configure(RiskTolerance.BAJO) returns config with 15% max drawdown
- [ ] configure(RiskTolerance.MEDIO) returns config with 25% max drawdown
- [ ] configure(RiskTolerance.ALTO) returns config with 40% max drawdown
- [ ] configure raises ValueError for invalid tolerance
- [ ] configure_for_profile accepts both string and enum types
- [ ] All monetary values use Decimal type
- [ ] Type hints use modern syntax (str | RiskTolerance)
- [ ] Domain layer purity: no infrastructure imports

---

## Audit Status

**Status:** PASSED
**Date:** 2026-02-06
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. Template completed. Layer 7 fixes applied.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-001 | BASE_RULES.md | Domain layer has no infrastructure dependencies | ✅ OK |
| ARCH-003 | BASE_RULES.md | No framework imports in domain | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax (str \| RiskTolerance) | ✅ OK |
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ✅ OK - Only risk configuration |
| SOL-002 | BASE_RULES.md | Open/Closed Principle | ✅ OK - Extensible via new risk levels |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging | ⚠️ Uses standard logging |

---

## Dependencies
- **External:** logging, decimal, typing
- **Internal:**
  - app.core.models.input_profile.RiskTolerance
  - app.domain.configurators.risk_config.RiskConfig

---

## Required Tests
- **tests/domain/configurators/test_risk_configurator.py:**
  - Success paths:
    - test_configure_bajo_returns_correct_limits
    - test_configure_medio_returns_correct_limits
    - test_configure_alto_returns_correct_limits
    - test_configure_for_profile_with_enum
    - test_configure_for_profile_with_string
    - test_get_all_configs_returns_three_configs
    - test_compare_configs_returns_comparison
  - Error paths:
    - test_configure_raises_value_error_for_invalid_tolerance
    - test_configure_for_profile_raises_value_error_for_invalid_string
  - Edge cases:
    - test_all_configs_use_decimal_precision
    - test_leverage_only_allowed_for_medio_and_alto

---

## Notes
- Pure domain service with no external dependencies
- Risk parameters follow John Hull's risk management principles
- Configuration mapping is critical for user safety (prevents inappropriate risk levels)
- All limits are hardcoded as business rules (not configurable at runtime)
