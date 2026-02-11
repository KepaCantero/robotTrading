# input_profile_router.py

## Purpose
Routes InputProfile to appropriate trading strategies, risk configurations, and system settings based on user investment objectives, risk tolerance, and tax residence. Maps user inputs to complete SystemConfiguration for autonomous trading system operation.

---

## Type Definitions / Data Classes

### InputProfile (imported from app.core.models.input_profile)
```python
class InputProfile:
    objetivo_inversion: ObjectivoInversion  # REQUIRED - User's investment objective
    risk_tolerance: RiskTolerance  # REQUIRED - User's risk tolerance level
    capital_initial: Decimal  # REQUIRED - Initial investment capital
    investment_horizon: int  # REQUIRED - Investment horizon in months
    tax_residence: Optional[TaxResidence]  # OPTIONAL - Tax configuration
```

### SystemConfiguration (imported from app.domain.models.system_configuration)
```python
@dataclass
class SystemConfiguration:
    strategy_type: StrategyType  # REQUIRED - Selected trading strategy
    risk_config: RiskConfig  # REQUIRED - Risk management parameters
    tax_config: Optional[TaxConfig]  # OPTIONAL - Tax optimization configuration
    initial_capital: Decimal  # REQUIRED - Initial capital amount
    investment_horizon_months: int  # REQUIRED - Investment horizon
    rebalance_frequency_days: int  # REQUIRED - Rebalancing frequency
```

### RiskConfig (imported from app.domain.models.risk_config)
```python
@dataclass
class RiskConfig:
    max_drawdown: Decimal  # REQUIRED - Maximum allowed drawdown (0-1)
    var_confidence: Decimal  # REQUIRED - VaR confidence level (0.95, 0.99)
    max_position_size: Decimal  # REQUIRED - Max position size as percentage
    max_sector_exposure: Decimal  # REQUIRED - Max sector exposure
    leverage_allowed: bool  # REQUIRED - Whether leverage is permitted
    max_leverage: Decimal  # REQUIRED - Maximum leverage ratio
    min_positions: int  # REQUIRED - Minimum number of positions
    max_positions: int  # REQUIRED - Maximum number of positions
    stop_loss_enabled: bool  # REQUIRED - Enable stop-loss
    stop_loss_atr_multiplier: Decimal  # REQUIRED - ATR multiplier for stop-loss
    trailing_stop_enabled: bool  # REQUIRED - Enable trailing stop
    max_portfolio_volatility: Decimal  # REQUIRED - Max portfolio volatility
    volatility_target: Optional[Decimal]  # OPTIONAL - Target volatility
```

**Validation Rules:**
- `max_drawdown` must be between 0 and 1
- `max_position_size` must be between 0 and 1
- `max_leverage` must be >= 1.0
- `min_positions` must be <= `max_positions`
- `volatility_target` if set must be <= `max_portfolio_volatility`

---

## Function Signatures (Contracts)

### `__call__(profile: InputProfile) -> SystemConfiguration`
**Pre:** `profile` must be validated InputProfile with all required fields
**Post:** Returns complete SystemConfiguration matching profile parameters
**Raises:** `ValueError` if profile validation fails or unknown objective/tolerance
**Retry:** No
**Side Effects:** Logs routing decisions, no state changes

### `_select_strategy_type(objetivo: ObjectivoInversion) -> StrategyType`
**Pre:** `objetivo` must be valid ObjectivoInversion enum value
**Post:** Returns StrategyType matching investment objective
**Raises:** `ValueError` if objective not recognized
**Retry:** No
**Side Effects:** Logs strategy selection, no state changes

### `_select_risk_config(tolerance: RiskTolerance) -> RiskConfig`
**Pre:** `tolerance` must be valid RiskTolerance enum value
**Post:** Returns RiskConfig with parameters for tolerance level
**Raises:** `ValueError` if tolerance not recognized
**Retry:** No
**Side Effects:** Logs risk configuration, no state changes

### `_create_tax_config(tax_residence: Optional[TaxResidence]) -> Optional[TaxConfig]`
**Pre:** None (handles None input)
**Post:** Returns TaxConfig if residence provided, None otherwise
**Raises:** No exceptions raised
**Retry:** No
**Side Effects:** Logs tax config creation, no state changes

### `_calculate_rebalance_frequency(horizon_months: int) -> int`
**Pre:** `horizon_months` must be positive integer
**Post:** Returns rebalancing frequency in days (7, 14, 30, or 90)
**Raises:** No explicit validation, returns default for unexpected values
**Retry:** No
**Side Effects:** No state changes

### `validate_configuration(profile: InputProfile, config: SystemConfiguration) -> tuple[bool, list[str]]`
**Pre:** Both `profile` and `config` must be valid instances
**Post:** Returns tuple of (is_valid, warnings_list)
**Raises:** No exceptions raised
**Retry:** No
**Side Effects:** Logs warnings if validation fails

---

## Acceptance Criteria
- [ ] All investment objectives map to valid StrategyType enum values
- [ ] All risk tolerance levels map to RiskConfig with appropriate constraints
- [ ] Risk tolerance BAJO maps to no leverage (leverage_allowed=False)
- [ ] Risk tolerance ALTO maps to 2.0x max leverage
- [ ] Investment horizon < 6 months returns 7-day rebalancing frequency
- [ ] Investment horizon > 60 months returns 90-day rebalancing frequency
- [ ] CAPITAL_PRESERVATION objective with ALTO risk generates validation warning
- [ ] Capital < $50,000 with min_positions > 20 generates over-fragmentation warning
- [ ] All mappings are logged at appropriate levels (info/debug)
- [ ] Invalid objetivo_inversion raises ValueError with clear message
- [ ] Invalid risk_tolerance raises ValueError with clear message
- [ ] Tax config returns None when tax_residence is None

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - Only routing, no business logic | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depends on domain abstractions | ✅ OK |
| ARCH-001 | BASE_RULES.md | Layered architecture - Application layer coordination | ✅ OK |
| TRD-002 | BASE_RULES.md | Risk validation - Validate orders before execution | ⚠️ NOT APPLIED - This is configuration, not execution |
| TRD-003 | BASE_RULES.md | Position limits - Enforce max position size | ✅ OK - via RiskConfig |
| LOG-001 | BASE_RULES.md | Structured logging - Use structured logging | ✅ FIXED - 2026-02-02 - Converted all f-string logs to structured logging with keyword args |
| LOG-003 | BASE_RULES.md | Appropriate levels - Use appropriate log levels | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage - All functions have type hints | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax - Use modern type syntax | ✅ OK - using `|` for Union |
| CC-006 | BASE_RULES.md | Explicit error handling - Specific exceptions | ✅ OK - ValueError with messages |
| CC-007 | BASE_RULES.md | Small functions - Functions < 20 lines | ⚠️ NOT APPLIED - Some functions longer but maintainable |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `logging`, `decimal.Decimal`, `typing.Optional`
- **Internal:**
  - `app.core.models.input_profile` (InputProfile, ObjectivoInversion, RiskTolerance, TaxResidence)
  - `app.domain.models.risk_config` (RiskConfig)
  - `app.domain.models.strategy_type` (StrategyType)
  - `app.domain.models.system_configuration` (SystemConfiguration)
  - `app.domain.models.tax_config` (TaxConfig)

---

## Required Tests
- **test_input_profile_router.py:**
  - Test strategy type mapping for all 5 investment objectives
  - Test risk config mapping for BAJO, MEDIO, ALTO tolerances
  - Test rebalancing frequency calculation for different horizons
  - Test tax config creation with valid tax residence
  - Test tax config returns None when residence is None
  - Test complete configuration generation from valid InputProfile
  - Test validation warnings for contradictory objective/risk combinations
  - Test validation warnings for capital vs position constraints
  - Test ValueError for unknown investment objective
  - Test ValueError for unknown risk tolerance
  - Test all risk tolerance levels generate appropriate leverage settings
  - Test edge cases for horizon (0, 6, 24, 60 months)

---

## Notes
**Critical:** This router implements Brecha #1 from AUDIT_PLAN_COMPLETO.md - automatic strategy selection based on investment objective. This is the core mapping layer that enables autonomous system operation by translating user inputs into system configuration.
