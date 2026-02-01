# create_portfolio_use_case.py

## Purpose
Application layer use case for creating new portfolio entities with appropriate capital and risk parameters using the TradingEntityFactory.

---

## Type Definitions / Data Classes

### Portfolio (imported from app.domain.entities.portfolio)
```python
class Portfolio:
    portfolio_id: str  # REQUIRED - Unique portfolio identifier
    initial_capital: Decimal  # REQUIRED - Initial capital amount
    currency: str  # REQUIRED - Currency code (default: "USD")
    max_position_size_pct: Decimal  # OPTIONAL - Max position size as percentage
    max_portfolio_exposure_pct: Decimal  # OPTIONAL - Max portfolio exposure as percentage
```

**Validation Rules:**
- `portfolio_id` must be non-empty string
- `initial_capital` must be positive Decimal
- `currency` must be valid ISO 4217 code
- `max_position_size_pct` must be between 0 and 1
- `max_portfolio_exposure_pct` must be between 0 and 1

---

## Function Signatures (Contracts)

### `__init__(factory: Optional[TradingEntityFactory] = None)`
**Pre:** None (handles None factory with default)
**Post:** Use case initialized with factory (default or provided)
**Raises:** No explicit validation
**Retry:** No
**Side Effects:** Stores factory as private attribute

### `execute(portfolio_id: str, initial_capital: Decimal, currency: str = "USD", max_position_size_pct: Decimal = Decimal("0.2"), max_portfolio_exposure_pct: Decimal = Decimal("0.8")) -> Portfolio`
**Pre:** `portfolio_id` non-empty, `initial_capital` > 0, `currency` valid code
**Post:** Returns created Portfolio entity
**Raises:** No explicit validation (delegated to factory)
**Retry:** No
**Side Effects:** Delegates creation to TradingEntityFactory

---

## Acceptance Criteria
- [ ] execute() creates Portfolio via factory
- [ ] execute() passes all parameters to factory.create_portfolio()
- [ ] execute() uses default currency "USD" when not specified
- [ ] execute() uses default max_position_size_pct of 0.2 (20%)
- [ ] execute() uses default max_portfolio_exposure_pct of 0.8 (80%)
- [ ] execute() returns Portfolio entity from factory
- [ ] Constructor creates default factory when None provided
- [ ] Constructor uses provided factory when supplied
- [ ] All parameters are passed through without modification

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (12 categories with 96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility - Portfolio creation only | ✅ OK |
| SOL-005 | BASE_RULES.md | Dependency Inversion - Depends on factory abstraction | ✅ OK |
| ARCH-001 | BASE_RULES.md | Layered architecture - Application layer use case | ✅ OK |
| DP-004 | BASE_RULES.md | Dependency injection - Factory injected | ✅ OK |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses `|` for Optional |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses None for optional |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** `typing.Optional`, `decimal.Decimal`
- **Internal:**
  - `app.domain.entities.portfolio` (Portfolio)
  - `app.domain.factories` (TradingEntityFactory)

---

## Required Tests
- **test_create_portfolio_use_case.py:**
  - Test execute() creates portfolio with all parameters
  - Test execute() uses default currency "USD"
  - Test execute() uses default max_position_size_pct of 0.2
  - Test execute() uses default max_portfolio_exposure_pct of 0.8
  - Test execute() passes portfolio_id to factory
  - Test execute() passes initial_capital to factory
  - Test execute() returns Portfolio from factory
  - Test constructor creates default factory when None
  - Test constructor uses provided factory
  - Test execute() delegates to factory.create_portfolio()

---

## Notes
**Simple Use Case:** This is a straightforward use case that delegates all portfolio creation logic to the TradingEntityFactory. This follows the "Humble Object" pattern by keeping the use case thin and testable.

**Factory Pattern:** The use case depends on the TradingEntityFactory abstraction rather than concrete portfolio instantiation, following the Dependency Inversion Principle.

**Default Parameters:** The use case provides sensible defaults for optional parameters (currency, position size limits) while allowing callers to override them.

**Repository Note:** Unlike some use cases, this use case does NOT persist the portfolio to a repository. It only creates the entity. Persistence should be handled by the calling code or a separate use case if needed.
