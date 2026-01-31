# risk_config.py

## Purpose
Risk Configuration value object - contains concrete risk parameters (drawdown limits, position sizes, leverage, VaR, stop loss) derived from risk tolerance level.

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** Pydantic model with complete schema validation.

### `RiskConfig` Pydantic Model (Immutable Value Object)
```python
class RiskConfig(BaseModel):
    # Portfolio-level risk limits
    max_drawdown: Decimal              # REQUIRED, 0.0-1.0 - Maximum portfolio drawdown (e.g., 0.15 = 15%)
    max_daily_loss: Decimal            # REQUIRED, 0.0-1.0 - Daily circuit breaker (e.g., 0.05 = 5%)

    # Position-level risk limits
    max_position_size: Decimal         # REQUIRED, 0.0-1.0 - Max single position as portfolio % (e.g., 0.05 = 5%)

    # VaR-based risk limits
    portfolio_var_limit: Decimal       # REQUIRED, 0.0-1.0 - Value-at-Risk as portfolio % (e.g., 0.02 = 2%)

    # Leverage controls
    leverage_allowed: bool             # REQUIRED - Whether leverage is permitted
    max_leverage: Decimal              # REQUIRED, 1.0-3.0 - Maximum leverage multiplier

    # Stop loss parameters (ATR-based)
    stop_loss_atr_multiplier: Decimal  # REQUIRED, 0.5-5.0 - Stop loss distance as ATR multiplier
    trailing_stop_atr_multiplier: Decimal  # REQUIRED, 1.0-10.0 - Trailing stop distance as ATR multiplier
```

**Validation Rules:**
- `max_drawdown`: Must be between 0.0 and 1.0 (0-100%)
- `max_daily_loss`: Must be between 0.0 and 1.0 (0-100%)
- `max_position_size`: Must be between 0.0 and 1.0 (0-100%)
- `portfolio_var_limit`: Must be between 0.0 and 1.0 (0-100%)
- `max_leverage`: Must be between 1.0 and 3.0
  - **Custom validator:** Must be 1.0 when `leverage_allowed` is False
- `stop_loss_atr_multiplier`: Must be between 0.5 and 5.0
- `trailing_stop_atr_multiplier`: Must be between 1.0 and 10.0
  - **Custom validator:** Must be greater than `stop_loss_atr_multiplier`
- Model is **immutable** (frozen=True) - value object pattern
- **extra="forbid"** - prevents typos in field names
- **strict=True** - enforces type validation

**Risk Tolerance Mapping:**
| Tolerance | Drawdown | Position | Leverage | max_leverage |
|-----------|----------|----------|----------|--------------|
| BAJO      | < 15%    | 5%       | No       | 1.0x         |
| MEDIO     | < 25%    | 10%      | Yes      | 1.5x         |
| ALTO      | < 40%    | 20%      | Yes      | 2.0x         |

---

## Function Signatures (Contracts)

### `RiskConfig.validate_leverage_consistency(v: Decimal, info) -> Decimal`
**Pre:** Called during Pydantic validation
**Post:** Returns v if leverage_allowed is True or v is 1.0
**Raises:** ValueError if leverage_allowed is False and v != 1.0
**Retry:** N/A (validation-time check)
**Side Effects:** None (validation only)

### `RiskConfig.validate_trailing_stop_greater_than_stop_loss(v: Decimal, info) -> Decimal`
**Pre:** Called during Pydantic validation
**Post:** Returns v if v > stop_loss_atr_multiplier
**Raises:** ValueError if trailing_stop <= stop_loss
**Retry:** N/A (validation-time check)
**Side Effects:** None (validation only)

### `RiskConfig.is_conservative -> bool` (property)
**Pre:** None
**Post:** Returns True if no leverage and max_position_size <= 5%
**Raises:** None
**Retry:** N/A
**Side Effects:** None

### `RiskConfig.is_aggressive -> bool` (property)
**Pre:** None
**Post:** Returns True if max_position_size >= 15% and leverage allowed
**Raises:** None
**Retry:** N/A
**Side Effects:** None

### `RiskConfig.risk_level -> str` (property)
**Pre:** None
**Post:** Returns "BAJO" if conservative, "ALTO" if aggressive, else "MEDIO"
**Raises:** None
**Retry:** N/A
**Side Effects:** None

### `RiskConfig.get_position_limit_for_capital(capital: Decimal) -> Decimal`
**Pre:** capital is positive Decimal value
**Post:** Returns maximum position value in currency units (capital * max_position_size)
**Raises:** None (capital validation assumed by caller)
**Retry:** N/A
**Side Effects:** None

### `RiskConfig.get_var_limit_for_capital(capital: Decimal) -> Decimal`
**Pre:** capital is positive Decimal value
**Post:** Returns VaR limit in currency units (capital * portfolio_var_limit)
**Raises:** None (capital validation assumed by caller)
**Retry:** N/A
**Side Effects:** None

### `RiskConfig.get_daily_loss_limit_for_capital(capital: Decimal) -> Decimal`
**Pre:** capital is positive Decimal value
**Post:** Returns daily loss limit in currency units (capital * max_daily_loss)
**Raises:** None (capital validation assumed by caller)
**Retry:** N/A
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-VAL-001:** All Decimal fields validated for range (ge, le constraints)
- [ ] **AC-VAL-002:** max_leverage must be 1.0 when leverage_allowed is False
- [ ] **AC-VAL-003:** trailing_stop must be greater than stop_loss multiplier
- [ ] **AC-IMM-001:** Model is frozen (immutable) - value object pattern
- [ ] **AC-FORBID-001:** extra="forbid" prevents typos in field names
- [ ] **AC-STRICT-001:** strict=True enforces type validation
- [ ] **AC-PROP-001:** is_conservative returns True for BAJO (no leverage, <=5% position)
- [ ] **AC-PROP-002:** is_aggressive returns True for ALTO (>=15% position, leverage allowed)
- [ ] **AC-PROP-003:** risk_level returns correct label (BAJO/MEDIO/ALTO)
- [ ] **AC-CALC-001:** get_position_limit_for_capital returns capital * max_position_size
- [ ] **AC-CALC-002:** get_var_limit_for_capital returns capital * portfolio_var_limit
- [ ] **AC-CALC-003:** get_daily_loss_limit_for_capital returns capital * max_daily_loss
- [ ] **AC-REF-001:** References Hull Chapter 18 risk management limits
- [ ] **AC-BRECHA-001:** Addresses AUDIT_PLAN_COMPLETO.md Brecha #2

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Value Object | 05-architecture.md (ARCH-006) | Immutable dataclass/frozen=True | ✅ OK |
| Pydantic Validation | 08-configuration.md (CFG-001) | Use Pydantic for type-safe config | ✅ OK |
| Extra Forbid | 08-configuration.md (CFG-004) | Set extra="forbid" to catch typos | ✅ OK |
| Field Validators | 08-configuration.md (CFG-006) | Add field validators for complex validation | ✅ OK |
| Decimal Precision | 02-type-hints.md (TYP-001) | Use Decimal for financial values | ✅ OK |
| Range Constraints | 08-configuration.md (CFG-003) | Validate all configuration values | ✅ OK |
| No Mutable Defaults | 01-formatting-style.md (FMT-007) | No mutable default arguments | ✅ OK |
| Domain Layer Purity | 05-architecture.md (ARCH-003) | No framework imports in domain | ✅ OK |
| Risk Management | rules/trading/papers/13-john-hull-risk-management.md | Hull Chapter 18 risk limits | ✅ OK |
| Brecha #2 | AUDIT_PLAN_COMPLETO.md Section 4.2 | Risk tolerance mapping to concrete parameters | ✅ OK |
| Type Coverage | 02-type-hints.md (TYP-001) | 100% type coverage | ✅ OK |
| Properties | 05-architecture.md (ARCH-004) | Use @property for derived values | ✅ OK |

**NOTE:** This analysis applies all 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `decimal.Decimal` - Precise decimal arithmetic for financial calculations
  - `pydantic` - Data validation and settings management
    - `BaseModel` - Base model class
    - `ConfigDict` - Model configuration
    - `Field` - Field definitions with validation
    - `field_validator` - Custom field validators
- **Internal:**
  - None (this is a standalone domain value object)

---

## Required Tests
- **tests/domain/configurators/test_risk_config.py:**
  - Test RiskConfig creation with valid BAJO parameters
  - Test RiskConfig creation with valid MEDIO parameters
  - Test RiskConfig creation with valid ALTO parameters
  - Test max_drawdown validation (must be 0.0-1.0)
  - Test max_daily_loss validation (must be 0.0-1.0)
  - Test max_position_size validation (must be 0.0-1.0)
  - Test portfolio_var_limit validation (must be 0.0-1.0)
  - Test max_leverage validation (must be 1.0-3.0)
  - Test stop_loss_atr_multiplier validation (must be 0.5-5.0)
  - Test trailing_stop_atr_multiplier validation (must be 1.0-10.0)
  - Test max_leverage must be 1.0 when leverage_allowed is False
  - Test trailing_stop must be greater than stop_loss multiplier
  - Test model is frozen (immutable) - raises error on modification
  - Test extra fields are forbidden (raises validation error)
  - Test is_conservative returns True for BAJO config
  - Test is_conservative returns False for MEDIO config
  - Test is_aggressive returns True for ALTO config
  - Test is_aggressive returns False for MEDIO config
  - Test risk_level returns "BAJO" for conservative config
  - Test risk_level returns "MEDIO" for medium config
  - Test risk_level returns "ALTO" for aggressive config
  - Test get_position_limit_for_capital calculates correctly
  - Test get_var_limit_for_capital calculates correctly
  - Test get_daily_loss_limit_for_capital calculates correctly
  - Test Decimal precision is maintained (no floating point errors)

---

## Notes
- This is a **Value Object** (DDD pattern) - immutable, identified by its values
- Addresses **Brecha #2** from AUDIT_PLAN_COMPLETO.md - automatic risk configuration based on risk_tolerance
- References **John Hull "Options, Futures, and Other Derivatives" Chapter 18** - Risk Management limits
- Decimal type used for all financial values to avoid floating-point precision errors
- Risk tolerance mapping is hardcoded but follows documented specifications
- Stop loss and trailing stop use ATR (Average True Range) multiplier approach
- VaR (Value-at-Risk) limit provides portfolio-level risk control
- Daily circuit breaker (max_daily_loss) prevents catastrophic single-day losses
- Position size limit (max_position_size) controls concentration risk
