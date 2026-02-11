# __init__.py (Domain Factories)

## Purpose
Implements Factory pattern for creating domain entities (Order, Portfolio, Position) following Percival's Architecture Patterns with Python, providing abstract factory, concrete factory, factory method, builder, and prototype patterns.

---

## Type Definitions / Data Classes

### AbstractEntityFactory (ABC)
```python
class AbstractEntityFactory(ABC):
    @abstractmethod
    def create_order(self, **kwargs) -> Order: pass

    @abstractmethod
    def create_portfolio(self, **kwargs) -> Portfolio: pass

    @abstractmethod
    def create_position(self, **kwargs) -> Position: pass
```

**Validation Rules:**
- All methods must be overridden by concrete implementations
- Returns valid domain entities

### TradingEntityFactory Class
```python
class TradingEntityFactory(AbstractEntityFactory):
    # Implements all abstract methods for creating trading entities
    # Handles validation, defaults, ID generation
```

### OrderFactory Class
```python
class OrderFactory:
    entity_factory: AbstractEntityFactory  # REQUIRED - Factory for creating entities

    # Methods for specific order types
    def create_market_order(...) -> Order
    def create_limit_order(...) -> Order
    def create_stop_loss_order(...) -> Order
    def create_take_profit_order(...) -> Order
    def create_stop_limit_order(...) -> Order
```

### OrderBuilder Class
```python
class OrderBuilder:
    # Fluent interface for building orders step-by-step
    # Stores intermediate state
    # Returns Order on build()
```

### OrderPrototype Class
```python
class OrderPrototype:
    _base_params: dict[str, Any]  # REQUIRED - Base parameters for cloning
    _factory: TradingEntityFactory  # REQUIRED - Factory for creating orders

    # Methods for creating variations
    def with_price(price: Decimal) -> OrderPrototype
    def with_quantity(quantity: Decimal) -> OrderPrototype
    def for_symbol(symbol: str) -> OrderPrototype
    def build(**overrides) -> Order
```

### FactoryRegistry Class
```python
class FactoryRegistry:
    _factories: Dict[str, Any]  # REQUIRED - Registered factories

    def register(name: str, factory: Any) -> None
    def get(name: str) -> Any
    def list_factories() -> List[str]
```

---

## Function Signatures (Contracts)

### `TradingEntityFactory.create_order(symbol, quantity, side, order_type, price, stop_price, portfolio_id, **kwargs) -> Order`
**Pre:** symbol non-empty, quantity > 0, side in ('buy', 'sell')
**Post:** Returns Order entity with valid initial state
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Logs debug message, generates order ID if not provided

### `TradingEntityFactory.create_portfolio(portfolio_id, initial_capital, currency, max_position_size_pct, max_portfolio_exposure_pct, **kwargs) -> Portfolio`
**Pre:** portfolio_id non-empty, initial_capital > 0
**Post:** Returns Portfolio entity with Capital and RiskParameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Logs debug message

### `TradingEntityFactory.create_position(symbol, quantity, entry_price, currency, side, **kwargs) -> Position`
**Pre:** symbol non-empty, quantity != 0, entry_price > 0
**Post:** Returns Position entity with correct side (auto-detected if not specified)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Logs debug message, converts negative quantity to positive with SHORT side

### `OrderBuilder.build() -> Order`
**Pre:** symbol and quantity are set
**Post:** Returns Order entity with all specified parameters
**Raises:** ValueError if required parameters missing
**Retry:** No
**Side Effects:** None

### `OrderPrototype.build(**overrides) -> Order`
**Pre:** Prototype has valid base_params
**Post:** Returns Order with base params merged with overrides
**Raises:** No exceptions (delegates to factory)
**Retry:** No
**Side Effects:** None

### `FactoryRegistry.register(name, factory) -> None`
**Pre:** name non-empty, factory is valid instance
**Post:** Factory is registered in registry
**Raises:** No exceptions
**Retry:** No
**Side Effects:** Logs debug message

### `FactoryRegistry.get(name) -> Any`
**Pre:** None
**Post:** Returns registered factory
**Raises:** KeyError if factory not registered
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Type hints coverage: 100% of functions have return type hints (AC-TYPE-001)
- [ ] All factory methods validate inputs before creating entities
- [ ] Order creation enforces business rules (limit orders need price, stop orders need stop_price)
- [ ] Portfolio creation creates Capital and RiskParameters value objects
- [ ] Position creation auto-detects side from quantity sign for backward compatibility
- [ ] OrderBuilder provides fluent interface for complex order construction
- [ ] OrderPrototype supports cloning with variations
- [ ] FactoryRegistry manages multiple factories
- [ ] All factory methods log debug messages (AC-LOG-001)
- [ ] Domain layer purity: no infrastructure imports (AC-ARCH-001)
- [ ] SOLID principles: Single Responsibility, Dependency Inversion (SOL-001, SOL-005)
- [ ] Black formatting compliance (AC-FMT-001)

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 2 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 2 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| ARCH-003 | BASE_RULES.md | No framework imports in domain | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ⚠️ NOT APPLIED - Uses standard logging |
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ✅ OK - Each class has one responsibility |
| SOL-005 | BASE_RULES.md | Dependency Inversion Principle | ✅ OK - AbstractEntityFactory for DI |
| DP-002 | BASE_RULES.md | Factory pattern | ✅ OK - Multiple factory implementations |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Constructor injection |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Raises ValueError with clear messages |
| TYP-003 | BASE_RULES.md | No Any without justification | ⚠️ NOT APPLIED - FactoryRegistry uses Any for flexibility |
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - RiskParameters created in factory |

**GAP violations found:**
- ❌ GAP LOG-001: Uses standard logging instead of structured logging (priority P1)
  - Impact: Reduced observability in production
  - Recommendation: Use structlog for structured logging
- ⚠️ GAP TYP-003: FactoryRegistry uses Any type (priority P1)
  - Impact: Reduced type safety
  - Recommendation: Use TypeVar or Protocol for better type safety

---

## Dependencies
- **External:** logging, abc, dataclasses, datetime, decimal, typing
- **Internal:**
  - `..entities.order` (Order, OrderSide, OrderStatus, OrderType)
  - `..entities.portfolio` (Portfolio, PortfolioStatus, Position)
  - `..entities.position` (PositionSide)
  - `..value_objects.capital` (Capital)
  - `..value_objects.money` (Money)
  - `..value_objects.risk_parameters` (RiskParameters)

---

## Required Tests
- **test_factories.py:**
  - Success paths:
    - `test_trading_entity_factory_create_order` - Creates valid order with defaults
    - `test_trading_entity_factory_create_portfolio` - Creates portfolio with capital and risk params
    - `test_trading_entity_factory_create_position_long` - Creates long position
    - `test_trading_entity_factory_create_position_short` - Creates short position from negative quantity
    - `test_order_factory_market_order` - Creates market order
    - `test_order_factory_limit_order` - Creates limit order with price
    - `test_order_factory_stop_loss_order` - Creates stop-loss order
    - `test_order_builder_fluent_interface` - Builds order using fluent interface
    - `test_order_prototype_cloning` - Creates variations from prototype
    - `test_factory_registry` - Registers and retrieves factories
  - Error paths:
    - `test_create_order_empty_symbol` - Raises ValueError for empty symbol
    - `test_create_order_zero_quantity` - Raises ValueError for zero quantity
    - `test_create_order_invalid_side` - Raises ValueError for invalid side
    - `test_create_limit_order_without_price` - Raises ValueError
    - `test_create_stop_order_without_stop_price` - Raises ValueError
    - `test_create_portfolio_empty_id` - Raises ValueError for empty ID
    - `test_create_portfolio_non_positive_capital` - Raises ValueError
    - `test_create_position_zero_quantity` - Raises ValueError for zero quantity
    - `test_create_position_non_positive_price` - Raises ValueError
    - `test_order_builder_missing_symbol` - Raises ValueError when symbol not set
    - `test_order_builder_missing_quantity` - Raises ValueError when quantity not set
    - `test_factory_registry_not_registered` - Raises KeyError for unregistered factory
  - Edge cases:
    - `test_position_side_auto_detection` - Auto-detects SHORT from negative quantity
    - `test_position_explicit_side` - Uses explicit side parameter
    - `test_position_quantity_abs` - Always stores positive quantity
    - `test_order_builder_with_factory_injection` - Supports custom factory injection
    - `test_order_prototype_with_overrides` - Merges overrides with base params
    - `test_global_registry` - Global registry persists across imports

---

## Notes
Reference: Percival & Gregory "Architecture Patterns with Python" (Cosmic Python) Chapter 5. Implements comprehensive factory patterns with proper validation, dependency injection, and backward compatibility for position side detection.
