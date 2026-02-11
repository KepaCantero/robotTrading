# system_configuration.py

## Purpose
Complete Pydantic model combining strategy selection, risk parameters, and tax optimization as output of InputProfileRouter for trading system configuration.

---

## Type Definitions / Data Classes

### SystemConfiguration Class (Pydantic BaseModel)
```python
class SystemConfiguration(BaseModel):
    # Strategy selection
    strategy_type: StrategyType                 # REQUIRED - Selected trading strategy type

    # Risk configuration
    risk_config: RiskConfig                     # REQUIRED - Risk parameters from risk tolerance

    # Tax configuration
    tax_config: Optional[TaxConfig] = None      # OPTIONAL - Tax optimization parameters

    # Capital allocation
    initial_capital: Decimal                    # REQUIRED, x > 0 - Initial capital allocated
    capital_buffer: Decimal = 0.05              # OPTIONAL, 0 <= x <= 0.20 - Capital kept as cash

    # Investment horizon
    investment_horizon_months: int              # REQUIRED, x >= 1 - Horizon in months
    rebalance_frequency_days: int = 30          # OPTIONAL, x >= 1 - Rebalancing frequency

    # Optional constraints
    sector_limits: Optional[dict[str, Decimal]] = None  # OPTIONAL - Sector-specific limits
    exclude_symbols: Optional[set[str]] = None          # OPTIONAL - Symbols to exclude

    # Metadata
    config_version: str = "1.0"                 # OPTIONAL - Configuration version
```

**Model Config:**
- `strict=True` - Strict type checking
- `validate_assignment=True` - Validate on attribute assignment
- `extra="forbid"` - Forbid extra attributes (catch typos)

**Properties:**
- `deployable_capital: Decimal` - Capital available after buffer (initial_capital * (1 - capital_buffer))
- `requires_long_term_focus: bool` - True if strategy prefers long-term or tax_config.prefer_long_term
- `is_complex_strategy: bool` - True if strategy is MULTI_FACTOR or COVERED_CALL
- `expected_volatility: Decimal` - Annualized volatility based on strategy type (10%-25%)

**Expected Volatility Mapping:**
- LOW_VOLATILITY: 10%
- DIVIDEND: 15%
- COVERED_CALL: 12%
- MULTI_FACTOR: 18%
- MOMENTUM: 25%
- Default: 20%

**Methods:**
- `to_dict() -> dict` - Serialize configuration to dictionary for logging

**Validation Rules:**
- `initial_capital` must be > 0
- `capital_buffer` must be between 0% and 20%
- `investment_horizon_months` must be >= 1
- `rebalance_frequency_days` must be >= 1
- Uses composition (contains RiskConfig, TaxConfig, StrategyType)

---

## Function Signatures (Contracts)

### `SystemConfiguration.deployable_capital` (property)
**Pre:** SystemConfiguration instance is valid
**Post:** Returns capital available for deployment (initial - buffer)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `SystemConfiguration.requires_long_term_focus` (property)
**Pre:** SystemConfiguration instance is valid
**Post:** Returns True if strategy or tax config prefers long-term
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `SystemConfiguration.is_complex_strategy` (property)
**Pre:** SystemConfiguration instance is valid
**Post:** Returns True if strategy is MULTI_FACTOR or COVERED_CALL
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `SystemConfiguration.expected_volatility` (property)
**Pre:** SystemConfiguration instance is valid
**Post:** Returns expected annualized volatility based on strategy type
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only property)

### `SystemConfiguration.to_dict() -> dict`
**Pre:** SystemConfiguration instance is valid
**Post:** Returns dictionary with all key fields for logging
**Raises:** None
**Retry:** N/A
**Side Effects:** None (serialization method)

---

## Acceptance Criteria
- [ ] All required fields are mandatory (strategy_type, risk_config, initial_capital, investment_horizon_months)
- [ ] `extra="forbid"` prevents typos in field names
- [ ] `validate_assignment=True` ensures validation on all updates
- [ ] `initial_capital` must be > 0
- [ ] `capital_buffer` defaults to 5% (0.05)
- [ ] `capital_buffer` range is 0-20%
- [ ] `deployable_capital` correctly calculates initial - buffer
- [ ] `requires_long_term_focus` checks strategy and tax_config
- [ ] `is_complex_strategy` identifies MULTI_FACTOR and COVERED_CALL
- [ ] `expected_volatility` returns correct values per strategy
- [ ] `to_dict()` serializes all key fields for logging
- [ ] Model uses composition (contains nested models)

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | 08-configuration.md | Pydantic Settings for type-safe config | ✅ OK - Using Pydantic BaseModel |
| CFG-003 | 08-configuration.md | Validate all configuration values | ✅ OK - Field validation with ge/le/gt |
| CFG-004 | 08-configuration.md | Extra forbid to catch typos | ✅ OK - extra="forbid" set |
| TYP-001 | 02-type-hints.md | All fields have type hints | ✅ OK - All fields typed |
| ARCH-007 | 05-architecture.md | Composition > inheritance | ✅ OK - Contains nested models |
| RSK-001 | BASE_RULES.md | VaR calculation support | ✅ OK - Via risk_config |
| RSK-003 | BASE_RULES.md | Drawdown control | ✅ OK - Via risk_config |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ✅ OK - Via risk_config |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK - Field constraints validate inputs |

---

## Dependencies
- **External:** `decimal` (stdlib), `typing` (stdlib), `pydantic` (Pydantic 2.x)
- **Internal:**
  - `app.domain.models.risk_config.RiskConfig`
  - `app.domain.models.strategy_type.StrategyType`
  - `app.domain.models.tax_config.TaxConfig`

---

## Required Tests
- **test_system_configuration.py:**
  - Test valid SystemConfiguration creation with all fields
  - Test initial_capital validation (must be > 0)
  - Test capital_buffer validation (0 <= x <= 0.20)
  - Test capital_buffer defaults to 0.05 (5%)
  - Test investment_horizon_months validation (>= 1)
  - Test rebalance_frequency_days defaults to 30
  - Test tax_config is optional (defaults to None)
  - Test sector_limits is optional
  - Test exclude_symbols is optional
  - Test config_version defaults to "1.0"
  - Test deployable_capital calculates initial - buffer correctly
  - Test requires_long_term_focus when strategy is DIVIDEND
  - Test requires_long_term_focus when tax_config.prefer_long_term is True
  - Test is_complex_strategy for MULTI_FACTOR
  - Test is_complex_strategy for COVERED_CALL
  - Test is_complex_strategy is False for MOMENTUM
  - Test expected_volatility returns correct values per strategy
  - Test expected_volatility returns 0.20 for unknown strategy
  - Test to_dict() serialization includes all key fields
  - Test extra="forbid" rejects unknown fields
  - Test validate_assignment=True works on updates

---

## Notes
- SystemConfiguration is the complete output of InputProfileRouter
- Combines strategy selection, risk management, and tax optimization
- Uses composition to contain nested models (RiskConfig, TaxConfig)
- Expected volatility mapping is based on historical strategy characteristics
- Capital buffer ensures liquidity for rebalancing and emergencies
