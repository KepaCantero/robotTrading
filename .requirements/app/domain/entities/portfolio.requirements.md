# portfolio.py

## Purpose
Portfolio Entity - Core domain business object representing a collection of positions with capital, risk parameters, and trading constraints.

---

## Type Definitions / Data Classes

### PortfolioStatus (Enum)
```python
class PortfolioStatus(str, Enum):
    ACTIVE = "active"        # Portfolio is active and trading
    SUSPENDED = "suspended"  # Trading suspended (positions held)
    CLOSED = "closed"        # Portfolio closed and liquidated
    FROZEN = "frozen"        # Frozen (no new positions allowed)
```

### Portfolio
```python
@dataclass
class Portfolio:
    # Identity
    portfolio_id: str                    # REQUIRED - Unique portfolio identifier

    # Capital and risk
    capital: Capital                     # REQUIRED - Capital value object
    risk_parameters: RiskParameters      # REQUIRED - Risk constraints

    # State
    status: PortfolioStatus              # Default: ACTIVE
    positions: Dict[str, Position]       # Symbol -> Position mapping

    # Metadata
    broker: str                          # Default: ""
    currency: str                        # Default: "USD"
    created_at: datetime                 # Default: utcnow()
    updated_at: datetime                 # Default: utcnow()
```

**Invariants (enforced in __post_init__):**
- `portfolio_id` must be non-empty
- `capital.amount` must be positive

---

## Function Signatures (Contracts)

### `Portfolio.__post_init__() -> None`
**Pre:** None
**Post:** Portfolio validated and initialized
**Raises:** `ValueError` if portfolio_id is empty or capital <= 0
**Retry:** No
**Side Effects:** Validates invariants

### `add_position(position) -> None`
**Pre:** position is valid Position object
**Post:** Position added to portfolio (or merged with existing)
**Raises:** `ValueError` if position exceeds risk limits
**Retry:** No
**Side Effects:** Updates positions dict, marks updated

### `remove_position(symbol, quantity) -> None`
**Pre:** symbol exists in positions
**Post:** Position removed (full) or reduced (partial)
**Raises:** `ValueError` if symbol not found
**Retry:** No
**Side Effects:** Deletes position or updates quantity, marks updated

### `update_position_price(symbol, new_price) -> None`
**Pre:** symbol exists in positions; new_price > 0
**Post:** Position's current_price updated
**Raises:** `ValueError` if symbol not found
**Retry:** No
**Side Effects:** Updates position, marks updated

### `get_position(symbol) -> Optional[Position]`
**Pre:** None
**Post:** Returns Position or None if not found
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_open_positions() -> List[Position]`
**Pre:** None
**Post:** Returns list of positions with status OPEN
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_closed_positions() -> List[Position]`
**Pre:** None
**Post:** Returns list of positions with status CLOSED
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `iterate_positions() -> Iterator[Position]`
**Pre:** None
**Post:** Returns iterator over all positions
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `get_total_value() -> Money`
**Pre:** None
**Post:** Returns Money with cash + positions_value
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_cash() -> Decimal`
**Pre:** None
**Post:** Returns capital - deployed in positions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_positions_value() -> Decimal`
**Pre:** None
**Post:** Returns sum of position values at current prices
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_total_pnl() -> Money`
**Pre:** None
**Post:** Returns absolute value of realized + unrealized P&L
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_unrealized_pnl() -> Money`
**Pre:** None
**Post:** Returns absolute value of unrealized P&L from open positions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_realized_pnl() -> Money`
**Pre:** None
**Post:** Returns absolute value of realized P&L from closed positions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_total_return_percent() -> Decimal`
**Pre:** None
**Post:** Returns (current_value - capital) / capital × 100
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_exposure() -> Decimal`
**Pre:** None
**Post:** Returns net exposure (long - short)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_gross_exposure() -> Decimal`
**Pre:** None
**Post:** Returns sum of absolute position values
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_portfolio_beta() -> Decimal`
**Pre:** None
**Post:** Returns 1.0 (placeholder for weighted beta calculation)
**Raises:** None
**Retry:** No
**Side Effects:** None (getter)

### `is_risk_limit_exceeded(additional_exposure) -> bool`
**Pre:** additional_exposure >= 0
**Post:** Returns True if gross_exposure + additional > max_exposure
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_concentration(symbol) -> Decimal`
**Pre:** None
**Post:** Returns position value / total_value × 100
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `get_max_concentration() -> Tuple[str, Decimal]`
**Pre:** None
**Post:** Returns (symbol, concentration) of highest concentration position
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `is_position_size_allowed(position_value) -> bool`
**Pre:** position_value >= 0
**Post:** Returns True if position_value <= max_position_size
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `can_add_position(position) -> Tuple[bool, str]`
**Pre:** position is valid
**Post:** Returns (allowed, reason) - checks size, exposure, max_positions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `freeze() -> None`
**Pre:** None
**Post:** status = FROZEN
**Raises:** None
**Retry:** No
**Side Effects:** Updates status, marks updated

### `unfreeze() -> None`
**Pre:** status == FROZEN
**Post:** status = ACTIVE
**Raises:** None
**Retry:** No
**Side Effects:** Updates status, marks updated

### `suspend() -> None`
**Pre:** None
**Post:** status = SUSPENDED
**Raises:** None
**Retry:** No
**Side Effects:** Updates status, marks updated

### `activate() -> None`
**Pre:** status in [SUSPENDED, FROZEN]
**Post:** status = ACTIVE
**Raises:** None
**Retry:** No
**Side Effects:** Updates status, marks updated

### `close() -> None`
**Pre:** None
**Post:** status = CLOSED; all positions marked CLOSED
**Raises:** None
**Retry:** No
**Side Effects:** Updates status and all positions, marks updated

### `_validate_position_risk(position) -> bool` (private)
**Pre:** position is valid
**Post:** Returns True if position passes all risk checks
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_mark_updated() -> None` (private)
**Pre:** None
**Post:** updated_at = datetime.utcnow()
**Raises:** None
**Retry:** No
**Side Effects:** Updates timestamp

### `create(portfolio_id, initial_capital, currency, max_position_size_pct, max_portfolio_exposure_pct) -> Portfolio` (classmethod)
**Pre:** portfolio_id non-empty; initial_capital > 0; max_*_pct in (0, 1]
**Post:** Returns new Portfolio instance with Capital and RiskParameters
**Raises:** None
**Retry:** No
**Side Effects:** None (factory method)

### `to_dict() -> dict`
**Pre:** None
**Post:** Returns dict representation of portfolio
**Raises:** None
**Retry:** No
**Side Effects:** None (serialization)

---

## Acceptance Criteria
- [ ] **AC-001:** Portfolio ID must be non-empty
- [ ] **AC-002:** Initial capital must be positive
- [ ] **AC-003:** Position size cannot exceed max_position_size % of capital
- [ ] **AC-004:** Portfolio exposure cannot exceed max_portfolio_exposure % of capital
- [ ] **AC-005:** Maximum positions limit enforced
- [ ] **AC-006:** Total value = cash + positions_value
- [ ] **AC-007:** Return % = (current_value - initial_capital) / initial_capital × 100
- [ ] **AC-008:** Gross exposure = sum(|position_values|)
- [ ] **AC-009:** Net exposure = long_values - short_values
- [ ] **AC-010:** All public methods have complete type hints

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Portfolio Entity):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Entity invariants | DDD (Evans) | Validate invariants in __post_init__ | ✅ OK - Implemented |
| Identity immutability | DDD (Evans) | portfolio_id cannot change | ✅ OK - No setter |
| Aggregate root | DDD (Evans) | Portfolio owns Position lifecycle | ✅ OK - add/remove/update |
| Encapsulation | BASE_RULES.md (ARCH-004) | Private methods with _ prefix | ✅ OK - _validate_position_risk |
| Risk limits | Trading standard | Max position size % of capital | ✅ OK - max_position_size |
| Risk limits | Trading standard | Max portfolio exposure % of capital | ✅ OK - max_portfolio_exposure |
| Position limit | Risk management | Max number of positions | ✅ OK - max_positions |
| Cash calculation | Portfolio math | Capital - deployed in positions | ✅ OK - get_cash() |
| P&L calculation | Portfolio math | Realized + unrealized | ✅ OK - get_total_pnl() |
| Concentration | Risk management | Position % of total value | ✅ OK - get_concentration() |
| State transitions | State machine | Valid status transitions only | ✅ OK - freeze/unfreeze/etc |
| Factory method | GoF patterns | create() for construction | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain entity purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only domain types |
| Value objects | DDD (Evans) | Capital, Money, RiskParameters are value objects | ✅ OK - Used correctly |

**NOTE:** This analysis references BASE_RULES.md for universal rules and DDD (Evans 2003) for entity design patterns.

---

## Dependencies
- **External:** `dataclasses` (std), `datetime` (std), `decimal` (std), `enum` (std), `typing` (std)
- **Internal:**
  - `app.domain.entities.position` (Position, PositionSide, PositionStatus)
  - `app.domain.value_objects.capital` (Capital)
  - `app.domain.value_objects.money` (Money)
  - `app.domain.value_objects.risk_parameters` (RiskParameters)

---

## Required Tests
- **test_portfolio_entity.py:**
  - `test_create_portfolio_success()` - Valid portfolio created
  - `test_create_portfolio_empty_id()` - Raises ValueError
  - `test_create_portfolio_zero_capital()` - Raises ValueError
  - `test_add_position_success()` - Position added
  - `test_add_position_exceeds_max_size()` - Raises ValueError
  - `test_add_position_exceeds_max_exposure()` - Raises ValueError
  - `test_add_position_max_positions_reached()` - Raises ValueError
  - `test_add_position_merge_existing()` - Merges with existing position
  - `test_remove_position_full()` - Position deleted
  - `test_remove_position_partial()` - Position quantity reduced
  - `test_remove_position_not_found()` - Raises ValueError
  - `test_update_position_price()` - Price updated
  - `test_get_open_positions()` - Returns only open positions
  - `test_get_closed_positions()` - Returns only closed positions
  - `test_get_total_value()` - Cash + positions
  - `test_get_cash()` - Capital - deployed
  - `test_get_positions_value()` - Sum of position values
  - `test_get_total_pnl()` - Realized + unrealized (absolute)
  - `test_get_unrealized_pnl()` - Open positions only
  - `test_get_realized_pnl()` - Closed positions only
  - `test_get_total_return_percent()` - (value - capital) / capital × 100
  - `test_get_exposure()` - Long - Short
  - `test_get_gross_exposure()` - Sum of absolute values
  - `test_is_risk_limit_exceeded()` - True if exposure > max
  - `test_get_concentration()` - Position % of total
  - `test_get_max_concentration()` - Returns highest concentration
  - `test_is_position_size_allowed()` - Checks max_position_size
  - `test_can_add_position()` - Returns (allowed, reason)
  - `test_freeze_portfolio()` - Status = FROZEN
  - `test_unfreeze_portfolio()` - Status = ACTIVE
  - `test_suspend_portfolio()` - Status = SUSPENDED
  - `test_activate_portfolio()` - Status = ACTIVE
  - `test_close_portfolio()` - Status = CLOSED, positions closed
  - `test_to_dict()` - Serialization
  - `test_updated_at_changes()` - Timestamp updates on mutations

---

## Notes
- **Critical:** Portfolio is an Aggregate Root in DDD terminology - it owns the Position entities
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003)
- **Entity Invariants:** portfolio_id non-empty, capital positive
- **Position Size Limit:** max_position_size is a percentage of capital (e.g., 0.2 = 20%)
- **Portfolio Exposure Limit:** max_portfolio_exposure is a multiplier of capital (e.g., 1.5 = 150%)
- **Cash Calculation:** Simplified as capital - deployed (not tracking cash flows)
- **Total Value:** cash + positions_value (current market value)
- **P&L:** Absolute value used (total magnitude, not signed)
- **Gross Exposure:** Sum of absolute position values (|long| + |short|)
- **Net Exposure:** Long positions - Short positions
- **Concentration:** Position value / Total portfolio value × 100%
- **Status Transitions:** ACTIVE → FROZEN → ACTIVE, ACTIVE → SUSPENDED → ACTIVE, ACTIVE → CLOSED (terminal)
- **Factory Method:** `create()` encapsulates Capital and RiskParameters construction
- **Placeholder:** `get_portfolio_beta()` returns 1.0 (should calculate weighted beta from positions)
- **Timestamps:** `created_at` and `updated_at` tracked for audit purposes

---

**File Reference:** `app/domain/entities/portfolio.py`
**Last Audited:** 2026-02-01
