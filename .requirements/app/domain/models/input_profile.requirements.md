# input_profile.py

## Purpose
Immutable domain model capturing validated user investment parameters (capital, horizon, objective, risk tolerance) as entry point to parametrization framework.

---

## Type Definitions / Data Classes

### InvestmentObjective (Enum)
```python
class InvestmentObjective(str, Enum):
    MAXIMIZE_CAPITAL = "maximize_capital"        # Growth-focused objective
    MAXIMIZE_DIVIDENDS = "maximize_dividends"    # Income-focused objective
    CAPITAL_PRESERVATION = "capital_preservation" # Safety-focused objective
    BALANCED_GROWTH = "balanced_growth"          # Balanced objective
    INCOME_GENERATION = "income_generation"      # Income generation objective
```

### RiskTolerance (Enum)
```python
class RiskTolerance(str, Enum):
    LOW = "low"      # Conservative risk tolerance
    MEDIUM = "medium" # Moderate risk tolerance
    HIGH = "high"    # Aggressive risk tolerance
```

### InputProfile (Dataclass - frozen)
```python
@dataclass(frozen=True)
class InputProfile:
    # Core investment parameters (required)
    capital: Capital                              # REQUIRED - Value object with amount and tier
    horizon: InvestmentHorizon                    # REQUIRED - Value object with months and category
    objective: InvestmentObjective                # REQUIRED - Investment goal
    risk_tolerance: RiskTolerance                 # REQUIRED - Risk tolerance level

    # Optional parameters
    constraints: Optional[Dict[str, Any]] = None  # OPTIONAL - Additional investment constraints
    tax_residence: Optional[Any] = None           # OPTIONAL - TaxResidence value object

    # Identification (auto-generated)
    input_id: str = <factory: uuid4>              # AUTO - Unique identifier
    created_at: str = <factory: datetime.isoformat> # AUTO - ISO format timestamp
```

**Validation Rules (in __post_init__):**
- CAPITAL_PRESERVATION objective incompatible with HIGH risk tolerance (raises ValueError)
- Short-term horizon with HIGH risk tolerance allowed but documented
- Uses value objects (Capital, InvestmentHorizon) for type safety

**Properties:**
- `capital_tier: CapitalTier` - Returns capital tier for strategy gating
- `is_small_capital: bool` - True if capital < €50,000
- `is_large_capital: bool` - True if capital >= €250,000
- `is_institutional: bool` - True if capital tier is INSTITUTIONAL
- `max_position_size: Decimal` - Max position based on capital and risk (2.5%-10%)
- `max_portfolio_exposure: Decimal` - Max deployable capital (60%-100%)
- `requires_diversification: bool` - True if large capital or LOW risk tolerance

**Methods:**
- `allows_strategy(strategy_type: str) -> bool` - Check if strategy allowed for profile
- `requires_hedging() -> bool` - Check if currency hedging recommended
- `validate_consistency() -> list[str]` - Return warnings for parameter inconsistencies
- `to_dict() -> Dict[str, Any]` - Serialize to dictionary for logging

**Factory Methods:**
- `create(...) -> InputProfile` - Create with type conversions and enum mapping

### InputProfileValidator (Class)
```python
class InputProfileValidator:
    """Validator for creating InputProfile from user input."""

    def validate(user_input: Dict[str, Any]) -> tuple[InputProfile, list[str]]
        # REQUIRED - Validates and creates InputProfile from user input
        # Returns: (InputProfile, warnings)
```

**Validation Rules:**
- Required fields: capital_initial, investment_horizon, objetivo_inversion, risk_tolerance
- Supports Spanish and English objective names
- Supports Spanish and English risk tolerance names
- Maps to factory methods for TaxResidence (ES, US, UK)

---

## Function Signatures (Contracts)

### `InputProfile.__post_init__()`
**Pre:** All required fields provided with valid types
**Post:** Validates invariants, raises ValueError if CAPITAL_PRESERVATION + HIGH risk
**Raises:** ValueError if objective and risk tolerance incompatible
**Retry:** N/A
**Side Effects:** None (validation only in frozen dataclass)

### `InputProfile.allows_strategy(strategy_type: str) -> bool`
**Pre:** strategy_type is a valid strategy identifier
**Post:** Returns True if strategy allowed for this profile
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only method)

### `InputProfile.requires_hedging() -> bool`
**Pre:** None
**Post:** Returns True if tax residence currency != USD and hedging recommended
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only method)

### `InputProfile.validate_consistency() -> list[str]`
**Pre:** None
**Post:** Returns list of warnings (empty if consistent)
**Raises:** None
**Retry:** N/A
**Side Effects:** None (read-only validation)

### `InputProfile.create(...) -> InputProfile` (classmethod)
**Pre:** capital_amount convertible to Decimal, horizon_months > 0
**Post:** Returns validated InputProfile with proper value objects
**Raises:** ValueError if invalid parameters
**Retry:** N/A
**Side Effects:** None (factory method creates new instance)

### `InputProfileValidator.validate(user_input: Dict[str, Any]) -> tuple[InputProfile, list[str]]`
**Pre:** user_input contains all required fields
**Post:** Returns (InputProfile, warnings)
**Raises:** ValueError if missing required fields
**Retry:** N/A
**Side Effects:** Increments internal validation counters

---

## Acceptance Criteria
- [ ] InputProfile is immutable (frozen=True)
- [ ] Required fields: capital, horizon, objective, risk_tolerance
- [ ] CAPITAL_PRESERVATION + HIGH risk tolerance raises ValueError
- [ ] max_position_size returns 2.5%-10% based on risk tolerance
- [ ] max_portfolio_exposure returns 60%-100% based on risk tolerance
- [ ] allows_strategy blocks high-risk strategies for small capital
- [ ] create() factory handles Spanish/English enum values
- [ ] to_dict() serializes all fields for logging
- [ ] InputProfileValidator supports Spanish field names

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ARCH-003 | 05-architecture.md | Domain has no framework dependencies | ✅ OK - Pure domain model |
| ARCH-006 | 05-architecture.md | Value objects immutable | ✅ OK - frozen=True |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK - All methods typed |
| TYP-002 | 02-type-hints.md | Modern syntax (X \| None) | ✅ OK - Using Optional |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - InputProfile: model, Validator: validation |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK - ValueError for invalid params |
| TRD-003 | BASE_RULES.md | Position limits enforcement | ✅ OK - max_position_size property |
| TRD-004 | BASE_RULES.md | Audit trail | ✅ OK - input_id, created_at, to_dict() |
| SEC-007 | 28-security-and-secrets.md | Input validation | ✅ OK - __post_init__, validate_consistency |

---

## Dependencies
- **External:** `dataclasses` (stdlib), `decimal` (stdlib), `enum` (stdlib), `typing` (stdlib), `uuid` (stdlib)
- **Internal:**
  - `app.domain.value_objects.capital` (Capital, CapitalTier)
  - `app.domain.value_objects.investment_horizon` (InvestmentHorizon, HorizonCategory)
  - `app.domain.value_objects.money` (Money)
  - `app.domain.value_objects.tax_residence` (TaxResidence - optional, imported in create())

---

## Required Tests
- **test_input_profile.py:**
  - Test valid InputProfile creation
  - Test immutability (frozen=True prevents modification)
  - Test CAPITAL_PRESERVATION + HIGH risk raises ValueError
  - Test capital_tier returns correct tier
  - Test is_small_capital (< €50k)
  - Test is_large_capital (>= €250k)
  - Test is_institutional (INSTITUTIONAL tier)
  - Test max_position_size calculations (2.5%, 5%, 10%)
  - Test max_portfolio_exposure (60%, 80%, 100%)
  - Test requires_diversification (large capital or LOW risk)
  - Test allows_strategy blocks leveraged_etf for small capital
  - Test allows_strategy blocks options for short horizon
  - Test requires_hedging when tax_residence currency != USD
  - Test validate_consistency returns warnings
  - Test to_dict() serialization
  - Test create() factory with Decimal conversion
  - Test create() factory with Spanish objective names
  - Test create() factory with Spanish risk tolerance names
  - Test InputProfileValidator.validate() required fields
  - Test InputProfileValidator.validate() Spanish field mapping
  - Test InputProfileValidator statistics tracking

---

## Notes
- InputProfile is the entry point to the parametrization framework
- Uses value objects (Capital, InvestmentHorizon) for type safety and encapsulation
- Frozen dataclass ensures immutability (prevents unintended state changes)
- Supports both Spanish and English input for user-facing flexibility
- Validation returns warnings (non-blocking) vs errors (blocking)
