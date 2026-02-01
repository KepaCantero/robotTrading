# base.py

## Purpose
Abstract base class defining the common interface for all trading strategies, enabling hot-swapping and dynamic strategy management.

---

## Type Definitions / Data Classes

### No Pydantic models or dataclasses defined in this file.
This file defines an abstract base class (ABC) with concrete methods.

---

## Function Signatures (Contracts)

### `__init__(config: Dict[str, Any]) -> None`
**Pre:** config is a valid dictionary with strategy parameters
**Post:** Strategy instance initialized with config, name, description, version, is_active=False, created_at set
**Raises:** None
**Retry:** No
**Side Effects:** Sets instance attributes from config dict

### `generate_signals(market_data: Quote) -> List[Signal]` (abstractmethod)
**Pre:** market_data contains valid price data
**Post:** Returns list of trading signals (may be empty)
**Raises:** NotImplementedError if not implemented by subclass
**Retry:** No
**Side Effects:** None (pure calculation)

### `risk_check(signal: Signal, portfolio: Portfolio) -> bool` (abstractmethod)
**Pre:** signal and portfolio are valid objects
**Post:** Returns True if signal passes risk validation, False otherwise
**Raises:** NotImplementedError if not implemented by subclass
**Retry:** No
**Side Effects:** May log rejection reasons

### `get_parameters() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns copy of config dictionary (not reference)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `update_parameters(params: Dict[str, Any]) -> None`
**Pre:** params is a valid dictionary
**Post:** Config dict updated with new key-value pairs
**Raises:** None
**Retry:** No
**Side Effects:** Modifies self.config in-place

### `validate_config() -> bool`
**Pre:** None
**Post:** Returns True if all required parameters present in config
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_required_parameters() -> List[str]` (abstractmethod)
**Pre:** None
**Post:** Returns list of required parameter names
**Raises:** NotImplementedError if not implemented by subclass
**Retry:** No
**Side Effects:** None

### `get_position_size(signal: Signal, portfolio: Portfolio) -> Decimal`
**Pre:** signal has valid price, portfolio has valid cash
**Post:** Returns position size in shares (minimum 1), calculated from available cash and max_position_size
**Raises:** Decimal division errors if price=0
**Retry:** No
**Side Effects:** None

### `get_stop_loss_price(signal: Signal) -> Optional[Decimal]`
**Pre:** signal has valid price
**Post:** Returns stop loss price based on ATR*2 or fixed percentage
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_take_profit_price(signal: Signal) -> Optional[Decimal]`
**Pre:** signal has valid price
**Post:** Returns take profit price based on fixed percentage
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All abstract methods are implemented by concrete strategy subclasses
- [ ] get_position_size correctly calculates BUY sizes based on available cash and max_position_size
- [ ] get_position_size correctly returns existing position quantity for SELL signals
- [ ] get_stop_loss_price uses ATR from signal.metadata when available, falls back to percentage
- [ ] validate_config returns False when required parameters are missing
- [ ] All Decimal operations use quantize with ROUND_HALF_UP for financial precision
- [ ] Type hints are present on all public methods (100% coverage)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage on all functions | ✅ OK - All methods have type hints |
| TYP-002 | 02-type-hints.md | Use modern syntax (X \| None, list[T]) | ⚠️ NOT APPLIED - Uses typing.Optional, typing.List (legacy but valid) |
| FMT-007 | 01-formatting-style.md | No mutable defaults | ✅ OK - No mutable defaults found |
| SOL-001 | 03-solid-principles.md | Single Responsibility - One class, one reason to change | ✅ OK - Base class only defines interface |
| SOL-005 | 03-solid-principles.md | Dependency Inversion - Depend on abstractions | ✅ OK - Uses ABC, Protocol-like interface |
| CC-001 | 05-architecture.md | Descriptive names | ✅ OK - All names are clear and descriptive |
| TRD-002 | 13-trading-specific | Risk validation required before trading | ✅ OK - risk_check abstract method enforced |
| TRD-003 | 13-trading-specific | Position limits enforced | ✅ OK - get_position_size enforces max_position_size |
| ARCH-002 | 05-architecture.md | Domain layer purity - no framework dependencies | ✅ OK - Only imports from app.models (domain entities) |
| LOG-004 | 09-logging-observability.md | Error logging with stack traces | ❌ GAP - No logging in base class (subclasses should implement) |

**GAP Analysis:**
- **LOG-004**: Base class doesn't include logging. This is acceptable as base class should be framework-agnostic. Subclasses implement logging. Marked as GAP but not critical for base class.

---

## Dependencies
- **External:** decimal (Decimal, ROUND_HALF_UP), typing (Any, Dict, List, Optional), abc (ABC, abstractmethod), datetime (datetime)
- **Internal:** app.models.market_data.Quote, app.models.portfolio.Portfolio, app.models.signal (Signal, SignalType)

---

## Required Tests
- **tests/unit/strategies/test_base_strategy.py:**
  - Test initialization with valid config
  - Test that abstract methods raise NotImplementedError
  - Test get_position_size calculation for BUY signals
  - Test get_position_size calculation for SELL signals with existing position
  - Test get_position_size returns 0 for SELL without position
  - Test get_stop_loss_price with ATR in metadata
  - Test get_stop_loss_price fallback to percentage
  - Test get_take_profit_price calculation
  - Test validate_config with missing parameters
  - Test validate_config with all required parameters
  - Test update_parameters modifies config dict
  - Test get_parameters returns copy (not reference)

---

## Notes
- This is the foundational base class for ALL trading strategies in the system
- All concrete strategies MUST inherit from BaseStrategy and implement abstract methods
- Position sizing logic uses Decimal for financial precision (critical for trading)
- ATR-based dynamic stop losses are supported via signal.metadata
- Base class is intentionally lightweight - subclasses add strategy-specific logic
