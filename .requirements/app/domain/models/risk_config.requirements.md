# risk_config.py

## Purpose
Pydantic model defining risk parameters derived from user risk tolerance based on John Hull's risk management principles.

---

## Type Definitions / Data Classes

### RiskConfig Class (Pydantic BaseModel)
```python
class RiskConfig(BaseModel):
    # Drawdown controls
    max_drawdown: Decimal                      # REQUIRED, 0 <= x <= 1 - Maximum allowed drawdown
    var_confidence: Decimal = 0.95             # OPTIONAL, 0.90 <= x <= 0.99 - VaR confidence level

    # Position sizing
    max_position_size: Decimal                 # REQUIRED, 0.01 <= x <= 1 - Max position as fraction of portfolio
    max_sector_exposure: Decimal = 0.30        # OPTIONAL, 0 <= x <= 1 - Max exposure to any single sector

    # Leverage controls
    leverage_allowed: bool = False             # OPTIONAL - Whether leverage is permitted
    max_leverage: Decimal = 1.0                # OPTIONAL, 1.0 <= x <= 3.0 - Maximum leverage multiplier

    # Portfolio controls
    min_positions: int = 5                     # OPTIONAL, 1 <= x <= 100 - Minimum number of positions
    max_positions: int = 50                    # OPTIONAL, 1 <= x <= 500 - Maximum number of positions

    # Risk management triggers
    stop_loss_enabled: bool = True             # OPTIONAL - Whether automatic stop-loss is enabled
    stop_loss_atr_multiplier: Decimal = 2.0    # OPTIONAL, 1.0 <= x <= 5.0 - ATR multiplier for stop-loss
    trailing_stop_enabled: bool = False        # OPTIONAL - Whether trailing stop-loss is enabled

    # Volatility controls
    max_portfolio_volatility: Decimal = 0.20   # OPTIONAL, 0.05 <= x <= 0.50 - Max annualized volatility
    volatility_target: Optional[Decimal] = None # OPTIONAL, 0.05 <= x <= 0.50 - Target volatility (None = no targeting)
```

**Model Config:**
- `strict=True` - Strict type checking
- `validate_assignment=True` - Validate on attribute assignment
- `extra="forbid"` - Forbid extra attributes (catch typos)

**Properties:**
- `is_conservative: bool` - True if max_drawdown <= 20% and no leverage
- `is_aggressive: bool` - True if max_drawdown >= 30% or (leverage_allowed and max_leverage >= 1.5)
- `effective_max_leverage: Decimal` - Returns max_leverage if allowed, else 1.0

**Validation Rules:**
- `max_drawdown` must be between 0 and 1 (0-100%)
- `var_confidence` must be between 0.90 and 0.99
- `max_position_size` must be at least 1% and at most 100%
- `max_leverage` minimum is 1.0 (no negative leverage)
- All Decimal fields use precise decimal arithmetic (no float)

---

## Function Signatures (Contracts)

### `RiskConfig.is_conservative` (property)
**Pre:** RiskConfig instance is valid
**Post:** Returns True if conservative profile (<=20% drawdown, no leverage)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `RiskConfig.is_aggressive` (property)
**Pre:** RiskConfig instance is valid
**Post:** Returns True if aggressive profile (>=30% drawdown or leverage >=1.5)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `RiskConfig.effective_max_leverage` (property)
**Pre:** RiskConfig instance is valid
**Post:** Returns max_leverage if leverage_allowed, else Decimal("1.0")
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

---

## Acceptance Criteria
- [ ] All Decimal fields use precise decimal arithmetic (no float)
- [ ] `extra="forbid"` prevents typos in field names
- [ ] `validate_assignment=True` ensures validation on all updates
- [ ] `max_drawdown` range is 0-1 (0-100%)
- [ ] `leverage_allowed=False` by default (conservative default)
- [ ] `effective_max_leverage` returns 1.0 when leverage not allowed
- [ ] Model is serializable to dict for logging

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | 08-configuration.md | Pydantic Settings for type-safe config | ✅ OK - Using Pydantic BaseModel |
| CFG-003 | 08-configuration.md | Validate all configuration values | ✅ OK - Field validation with ge/le |
| CFG-004 | 08-configuration.md | Extra forbid to catch typos | ✅ OK - extra="forbid" set |
| TYP-001 | 02-type-hints.md | All fields have type hints | ✅ OK - All fields typed |
| RSK-001 | BASE_RULES.md | VaR calculation support | ✅ OK - var_confidence field |
| RSK-003 | BASE_RULES.md | Drawdown control | ✅ OK - max_drawdown field |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ✅ OK - max_position_size field |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK - Field constraints validate inputs |

---

## Dependencies
- **External:** `decimal` (stdlib), `typing` (stdlib), `pydantic` (Pydantic 2.x)
- **Internal:** None

---

## Required Tests
- **test_risk_config.py:**
  - Test valid RiskConfig creation with all fields
  - Test max_drawdown validation (0 <= x <= 1)
  - Test var_confidence validation (0.90 <= x <= 0.99)
  - Test max_position_size validation (0.01 <= x <= 1)
  - Test max_leverage validation (1.0 <= x <= 3.0)
  - Test leverage_allowed=False by default
  - Test is_conservative property (<=20% drawdown, no leverage)
  - Test is_aggressive property (>=30% drawdown or leverage >=1.5)
  - Test effective_max_leverage returns 1.0 when leverage not allowed
  - Test extra="forbid" rejects unknown fields
  - Test validate_assignment=True works on updates
  - Test serialization to dict

---

## Notes
- Based on John Hull's "Risk Management" (13-john-hull-risk-management.md)
- Risk tolerance mapping: BAJO (conservative), MEDIO (moderate), ALTO (aggressive)
- Decimal type prevents floating-point precision issues in financial calculations
