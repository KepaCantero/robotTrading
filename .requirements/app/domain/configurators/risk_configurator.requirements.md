# risk_configurator.py

## Purpose
Maps risk tolerance levels (BAJO/MEDIO/ALTO) to concrete RiskConfig parameters - implements Single Responsibility Principle for risk parameter translation.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** No Pydantic models defined in this file (uses RiskConfig from risk_config.py).

### Input Types
```python
# From app.core.models.input_profile
class RiskTolerance(Enum):
    BAJO = "bajo"     # Low risk tolerance
    MEDIO = "medio"   # Medium risk tolerance
    ALTO = "alto"     # High risk tolerance
```

### Return Type
```python
# Returns RiskConfig value object (see risk_config.requirements.md for schema)
RiskConfig(
    max_drawdown: Decimal,
    max_daily_loss: Decimal,
    max_position_size: Decimal,
    portfolio_var_limit: Decimal,
    leverage_allowed: bool,
    max_leverage: Decimal,
    stop_loss_atr_multiplier: Decimal,
    trailing_stop_atr_multiplier: Decimal
)
```

**Risk Tolerance Mapping:**
| risk_tolerance | max_drawdown | max_position_size | leverage_allowed | max_leverage |
|---------------|--------------|-------------------|------------------|--------------|
| BAJO          | 15% (0.15)   | 5% (0.05)         | False            | 1.0x         |
| MEDIO         | 25% (0.25)   | 10% (0.10)        | True             | 1.5x         |
| ALTO          | 40% (0.40)   | 20% (0.20)        | True             | 2.0x         |

---

## Function Signatures (Contracts)

### `RiskConfigurator.configure(tolerance: RiskTolerance) -> RiskConfig`
**Pre:** tolerance is valid RiskTolerance enum value (BAJO, MEDIO, or ALTO)
**Post:** Returns RiskConfig with concrete parameters for given tolerance
**Raises:** ValueError if tolerance is not recognized
**Retry:** ❌ No (deterministic mapping)
**Side Effects:** None (pure function, logs at DEBUG level)

### `RiskConfigurator.configure_for_profile(risk_tolerance: str | RiskTolerance) -> RiskConfig`
**Pre:** risk_tolerance is valid string ("bajo", "medio", "alto") or RiskTolerance enum
**Post:** Returns RiskConfig with concrete parameters for given tolerance
**Raises:** ValueError if risk_tolerance string is not recognized
**Retry:** ❌ No (deterministic mapping)
**Side Effects:** None (pure function)

### `RiskConfigurator.get_all_configs() -> dict[RiskTolerance, RiskConfig]`
**Pre:** None
**Post:** Returns dictionary mapping all three RiskTolerance levels to their RiskConfig instances
**Raises:** None
**Retry:** ❌ No (deterministic)
**Side Effects:** None (pure function)

### `RiskConfigurator.compare_configs(tolerance1: RiskTolerance, tolerance2: RiskTolerance) -> dict[str, dict[str, Decimal | bool]]`
**Pre:** tolerance1 and tolerance2 are valid RiskTolerance enum values
**Post:** Returns dictionary comparing key parameters between two tolerance levels
**Raises:** ValueError if either tolerance is not recognized
**Retry:** ❌ No (deterministic)
**Side Effects:** None (pure function)

---

## Acceptance Criteria
- [ ] **AC-SOL-001:** Single Responsibility - only maps tolerance to config (SRP)
- [ ] **AC-OCP-001:** Open/Closed - open for extension (new risk levels), closed for modification
- [ ] **AC-MAP-001:** BAJO maps to 15% drawdown, 5% position, no leverage
- [ ] **AC-MAP-002:** MEDIO maps to 25% drawdown, 10% position, 1.5x leverage
- [ ] **AC-MAP-003:** ALTO maps to 40% drawdown, 20% position, 2.0x leverage
- [ ] **AC-ERR-001:** configure raises ValueError for unrecognized tolerance
- [ ] **AC-CONV-001:** configure_for_profile accepts both string and enum
- [ ] **AC-CONV-002:** configure_for_profile handles case-insensitive strings
- [ ] **AC-COMP-001:** compare_configs returns structured comparison dictionary
- [ ] **AC-LOG-001:** Configuration logged at DEBUG level
- [ ] **AC-BRECHA-001:** Addresses Brecha #2 - NO routing from InputProfile to Risk Config (direct mapping)
- [ ] **AC-REF-001:** References AUDIT_PLAN_COMPLETO.md Section 4.2
- [ ] **AC-REF-002:** References John Hull risk management principles

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Single Responsibility | 03-solid-principles.md (SOL-001) | One class, one reason to change | ✅ OK |
| Open/Closed Principle | 03-solid-principles.md (SOL-002) | Open for extension, closed for modification | ✅ OK |
| Pure Function | 05-architecture.md (ARCH-001) | No side effects in configure() | ✅ OK |
| Type Hints | 02-type-hints.md (TYP-001) | 100% type coverage | ✅ OK |
| Error Handling | 00-checklist.md (CC-006) | Specific exceptions (ValueError) | ✅ OK |
| Logging | 09-logging-observability.md (LOG-003) | Appropriate log levels (debug/error) | ✅ OK |
| Domain Layer Purity | 05-architecture.md (ARCH-003) | No framework imports | ✅ OK |
| Union Types | 02-type-hints.md (TYP-002) | Use str | RiskTolerance for flexibility | ✅ OK |
| Enum Usage | 05-architecture.md (ARCH-004) | Use RiskTolerance enum for type safety | ✅ OK |
| Brecha #2 | AUDIT_PLAN_COMPLETO.md Section 4.2 | NO routing InputProfile → Risk Config | ✅ OK |
| Risk Mapping | rules/trading/papers/13-john-hull-risk-management.md | Hull Chapter 18 risk limits | ✅ OK |
| No Hardcoding | 08-configuration.md (CFG-002) | Parameters should be configurable (future) | ⚠️ NOT APPLIED - Hardcoded is intentional for domain logic |

**NOTE:** This analysis applies all 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `logging` - Standard library logging
  - `decimal.Decimal` - Precise decimal arithmetic
- **Internal:**
  - `app.core.models.input_profile.RiskTolerance` - Risk tolerance enum
  - `app.domain.configurators.risk_config.RiskConfig` - Risk configuration value object

---

## Required Tests
- **tests/domain/configurators/test_risk_configurator.py:**
  - Test configure returns BAJO config with correct parameters (15% drawdown, 5% position, no leverage)
  - Test configure returns MEDIO config with correct parameters (25% drawdown, 10% position, 1.5x leverage)
  - Test configure returns ALTO config with correct parameters (40% drawdown, 20% position, 2.0x leverage)
  - Test configure raises ValueError for unrecognized tolerance
  - Test configure logs at DEBUG level
  - Test configure_for_profile with RiskTolerance enum
  - Test configure_for_profile with lowercase string ("bajo", "medio", "alto")
  - Test configure_for_profile with uppercase string ("BAJO", "MEDIO", "ALTO")
  - Test configure_for_profile raises ValueError for invalid string
  - Test configure_for_profile raises descriptive error with valid values
  - Test get_all_configs returns all three risk tolerance levels
  - Test get_all_configs returns valid RiskConfig instances
  - Test compare_configs returns structured comparison
  - Test compare_configs includes all key parameters (max_drawdown, max_position_size, leverage_allowed, max_leverage)
  - Test compare_configs handles same tolerance levels
  - Test all BAJO parameters match specifications
  - Test all MEDIO parameters match specifications
  - Test all ALTO parameters match specifications
  - Test BAJO has no leverage (leverage_allowed=False, max_leverage=1.0)
  - Test MEDIO has moderate leverage (leverage_allowed=True, max_leverage=1.5)
  - Test ALTO has high leverage (leverage_allowed=True, max_leverage=2.0)
  - Test stop_loss and trailing_stop multipliers increase with risk tolerance
  - Test VaR limits increase with risk tolerance

---

## Notes
- Implements **Brecha #2** from AUDIT_PLAN_COMPLETO.md - automatic risk configuration based on risk_tolerance
- **NO ROUTING** from InputProfile to Risk Config - direct mapping only
- Follows **Single Responsibility Principle (SRP)** - only maps tolerance to config
- Follows **Open/Closed Principle (OCP)** - new risk levels can be added without modifying existing code
- Parameters are **intentionally hardcoded** as domain logic (not configuration)
- Risk tolerance mapping based on **John Hull's "Options, Futures, and Other Derivatives" Chapter 18**
- Logging at DEBUG level for configuration decisions
- `configure_for_profile` provides convenience method accepting both string and enum types
- `get_all_configs` useful for UI display or configuration validation
- `compare_configs` useful for demonstrating impact of changing risk tolerance
- All parameters use Decimal type for financial precision
