# Architecture Patterns with Python - Implementation Guide

This guide documents the implementation of architecture patterns following Percival & Gregory's "Architecture Patterns with Python" (Cosmic Python).

## Table of Contents

1. [Overview](#overview)
2. [Repository Pattern](#repository-pattern)
3. [Unit of Work Pattern](#unit-of-work-pattern)
4. [Service Layer Pattern](#service-layer-pattern)
5. [Factory Pattern](#factory-pattern)
6. [Strategy Pattern](#strategy-pattern)
7. [Usage Examples](#usage-examples)
8. [Testing](#testing)
9. [Best Practices](#best-practices)

---

## Overview

This implementation applies the key architecture patterns from "Architecture Patterns with Python" to create a maintainable, testable trading system.

### Key Principles

- **Dependency Inversion**: Domain layer defines interfaces, infrastructure provides implementations
- **Separation of Concerns**: Each pattern has a single, well-defined responsibility
- **Testability**: All patterns support dependency injection and mocking
- **Domain-Centric**: Business logic lives in domain entities, not services or repositories

### Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│                  (API, Dashboard, CLI)                   │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                       │
│            (Use Cases, Services, Commands)                │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Domain Layer                         │
│         (Entities, Value Objects, Repositories)           │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                     │
│         (Database, External APIs, File System)           │
└─────────────────────────────────────────────────────────┘
```

---

## Repository Pattern

### Purpose

The Repository pattern provides a collection-like interface for accessing domain objects, abstracting the details of data persistence.

### Key Concepts

- Repositories are domain-layer interfaces
- Infrastructure layer provides concrete implementations
- Repositories behave like in-memory collections
- No business logic in repositories

### Implementation

```python
# Domain layer (interface)
from app.domain.repositories.base_repository import AbstractRepository

class OrderRepository(AbstractRepository[Order, str]):
    @abstractmethod
    async def add(self, order: Order) -> None:
        pass

    @abstractmethod
    async def get(self, order_id: str) -> Optional[Order]:
        pass

# Infrastructure layer (implementation)
class SqlOrderRepository(OrderRepository):
    def __init__(self, session):
        self.session = session

    async def add(self, order: Order) -> None:
        # SQL implementation
        record = OrderRecord.from_entity(order)
        self.session.add(record)

    async def get(self, order_id: str) -> Optional[Order]:
        # SQL implementation
        record = self.session.query(OrderRecord).filter_by(id=order_id).first()
        return record.to_entity() if record else None
```

### Features

1. **Generic Repository**: Type-safe base repository with common CRUD operations
2. **Queryable Repository**: Supports filtering with criteria and specifications
3. **Cached Repository**: Transparent caching layer for performance
4. **Streamable Repository**: Efficient streaming of large result sets

### Example Usage

```python
# Using repository
async with unit_of_work as uow:
    # Add order
    order = Order(order_id="ORD123", symbol="AAPL", ...)
    await uow.orders.add(order)

    # Get order
    order = await uow.orders.get("ORD123")

    # Find by criteria
    orders = await uow.orders.find_by_criteria(
        status=OrderStatus.PENDING,
        symbol="AAPL"
    )

    # Find by specification
    def is_high_value(o: Order) -> bool:
        return o.quantity * o.price > Decimal('10000')

    high_value_orders = await uow.orders.find_by_specification(is_high_value)
```

---

## Unit of Work Pattern

### Purpose

The Unit of Work pattern tracks changes to objects during a business transaction and writes them out to the database in a single atomic operation.

### Key Concepts

- Tracks new, dirty, and deleted entities
- Commits all changes atomically
- Supports rollback on errors
- Collects domain events for processing
- Manages repository lifecycle

### Implementation

```python
from app.domain.repositories.unit_of_work import AbstractUnitOfWork

class TradingUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()
        self.orders = SqlOrderRepository(self.session)
        self.portfolios = SqlPortfolioRepository(self.session)
        return self

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def collect_new_events(self):
        events = []
        for entity in self._tracked_entities:
            events.extend(entity.events)
        return events
```

### Example Usage

```python
# Simple transaction
async with unit_of_work as uow:
    order = await uow.orders.get("ORD123")
    order.submit()
    # Automatically committed on exit

# Error handling
try:
    async with unit_of_work as uow:
        order = await uow.orders.get("ORD123")
        portfolio = await uow.portfolios.get("PORT123")
        order.submit()
        portfolio.add_position_from_order(order)
        # All changes committed atomically
except Exception as e:
    # Automatically rolled back
    logger.error(f"Transaction failed: {e}")

# Collecting events
async with unit_of_work as uow:
    order = await uow.orders.get("ORD123")
    order.submit()

events = uow.collect_new_events()
for event in events:
    await event_handler.handle(event)
```

---

## Service Layer Pattern

### Purpose

The Service Layer defines an application's boundary and its set of available operations from the perspective of interfacing client layers.

### Key Concepts

- Application services orchestrate use cases
- Implement CQRS (Command Query Responsibility Segregation)
- Coordinate between domain entities and repositories
- Manage transaction boundaries
- Handle cross-cutting concerns

### Implementation

```python
from app.application.services import (
    Command,
    Query,
    ApplicationService,
    CreateOrderCommand,
    GetOrderQuery,
)

class OrderApplicationService(ApplicationService):
    async def create_order(self, command: CreateOrderCommand) -> str:
        async def _create(uow):
            # Validate command
            command.validate()

            # Load portfolio
            portfolio = await uow.portfolios.get(command.portfolio_id)

            # Create order entity
            order = Order(
                order_id=self.generate_id(),
                symbol=command.symbol,
                quantity=command.quantity,
                ...
            )

            # Domain validates business rules
            if not order.validate():
                raise ValidationError(order.validation_errors)

            # Portfolio validates risk limits
            if portfolio.is_risk_limit_exceeded(...):
                raise BusinessRuleError("Exceeds risk limits")

            # Save order
            await uow.orders.add(order)
            return order.order_id

        return await self._execute_in_transaction(_create)

    async def get_order(self, query: GetOrderQuery) -> Optional[Order]:
        async with self.uow_factory() as uow:
            return await query.execute(uow)
```

### CQRS Pattern

```python
# Commands (change state)
class CreateOrderCommand(Command):
    def __init__(self, symbol, quantity, side, ...):
        self.symbol = symbol
        self.quantity = quantity
        self.side = side

    def validate(self) -> bool:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        return True

# Queries (read state)
class GetOrderQuery(Query[Optional[Order]]):
    def __init__(self, order_id: str):
        self.order_id = order_id

    async def execute(self, uow: AbstractUnitOfWork) -> Optional[Order]:
        return await uow.orders.get(self.order_id)
```

### Example Usage

```python
# Using application service
order_service = OrderApplicationService(uow_factory)

# Create order (command)
command = CreateOrderCommand(
    symbol="AAPL",
    quantity=Decimal("100"),
    price=Decimal("150.00"),
    side="buy",
    order_type="limit",
    portfolio_id="PORT123"
)
order_id = await order_service.create_order(command)

# Get order (query)
query = GetOrderQuery(order_id)
order = await order_service.get_order(query)

# Submit order (command)
await order_service.submit_order(SubmitOrderCommand(order_id))
```

---

## Factory Pattern

### Purpose

The Factory pattern encapsulates object creation logic, providing a clean interface for creating complex objects with valid initial state.

### Key Concepts

- Abstract Factory: Creates families of related objects
- Factory Method: Parameterized creation methods
- Builder: Step-by-step construction
- Prototype: Cloning existing objects

### Implementation

```python
from app.domain.factories import (
    AbstractEntityFactory,
    TradingEntityFactory,
    OrderBuilder,
    OrderPrototype,
)

# Abstract Factory
factory = TradingEntityFactory()

# Factory Methods
order = factory.create_order(
    symbol="AAPL",
    quantity=Decimal("100"),
    side="buy",
    order_type="limit",
    price=Decimal("150.00")
)

# Builder Pattern
order = (OrderBuilder()
    .for_symbol("AAPL")
    .buy()
    .quantity(Decimal("100"))
    .limit_price(Decimal("150.00"))
    .with_time_in_force("GTC")
    .build())

# Prototype Pattern
prototype = OrderPrototype(symbol="AAPL", quantity=Decimal("100"), side="buy")
order1 = prototype.with_price(Decimal("150.00")).build()
order2 = prototype.with_price(Decimal("151.00")).build()
```

### Example Usage

```python
# Creating entities with factory
factory = TradingEntityFactory()

# Create portfolio
portfolio = factory.create_portfolio(
    portfolio_id="PORT123",
    initial_capital=Decimal("100000"),
    currency="USD",
    max_position_size_pct=Decimal("0.2"),
    max_portfolio_exposure_pct=Decimal("0.8")
)

# Create different order types
order_factory = OrderFactory()

market_order = order_factory.create_market_order(
    symbol="AAPL",
    quantity=Decimal("100"),
    side="buy"
)

limit_order = order_factory.create_limit_order(
    symbol="AAPL",
    quantity=Decimal("100"),
    price=Decimal("150.00"),
    side="buy"
)

stop_loss = order_factory.create_stop_loss_order(
    symbol="AAPL",
    quantity=Decimal("100"),
    stop_price=Decimal("145.00"),
    side="sell"
)
```

---

## Strategy Pattern

### Purpose

The Strategy pattern defines a family of algorithms, encapsulates each one, and makes them interchangeable.

### Key Concepts

- Strategy interface defines contract
- Concrete strategies implement algorithms
- Context delegates to strategy
- Registry for dynamic strategy discovery
- Runtime strategy switching

### Implementation

```python
from app.strategies.strategy_registry import (
    BaseStrategy,
    StrategyContext,
    StrategyRegistry,
    register_strategy,
)

# Define strategy
class MovingAverageStrategy(BaseStrategy):
    async def execute(self, market_data):
        short_ma = self.calculate_ma(market_data, self.short_period)
        long_ma = self.calculate_ma(market_data, self.long_period)

        if short_ma > long_ma:
            return Signal(type="buy", strength=0.8)
        elif short_ma < long_ma:
            return Signal(type="sell", strength=0.8)
        else:
            return Signal(type="hold", strength=0.0)

# Register strategy
registry = StrategyRegistry()
registry.register(
    name="ma_crossover",
    strategy_class=MovingAverageStrategy,
    description="Moving average crossover strategy",
    category="trend",
    tags=["ma", "crossover"]
)

# Or use decorator
@register_strategy(
    name="rsi_strategy",
    description="RSI-based strategy",
    category="momentum"
)
class RSIStrategy(BaseStrategy):
    async def execute(self, market_data):
        rsi = self.calculate_rsi(market_data)
        # ...
```

### Example Usage

```python
# Using registry
registry = StrategyRegistry()

# Create strategy
strategy = registry.create(
    name="ma_crossover",
    config={
        "short_period": 10,
        "long_period": 30,
        "name": "My MA Strategy"
    }
)

# Execute with context
context = StrategyContext()
context.set_strategy(strategy)

result = await context.execute_strategy(market_data)

# Switch strategies at runtime
rsi_strategy = registry.create("rsi_strategy", {...})
context.set_strategy(rsi_strategy)
result = await context.execute_strategy(market_data)

# Find strategies by category
trend_strategies = registry.list_strategies(
    category="trend",
    enabled_only=True
)
```

---

## Usage Examples

### Complete Order Lifecycle

```python
# Setup
uow_factory = SqlAlchemyUnitOfWork(session_factory)
order_service = OrderApplicationService(uow_factory)

# Create order
command = CreateOrderCommand(
    symbol="AAPL",
    quantity=Decimal("100"),
    price=Decimal("150.00"),
    side="buy",
    order_type="limit",
    portfolio_id="PORT123"
)
order_id = await order_service.create_order(command)

# Submit order
await order_service.submit_order(SubmitOrderCommand(order_id))

# Fill order (simulated)
async with uow_factory() as uow:
    order = await uow.orders.get(order_id)
    order.acknowledge(broker_order_id="BRK123")
    order.fill(
        fill_price=Decimal("150.00"),
        fill_quantity=Decimal("100")
    )
    uow.commit()
```

### Portfolio Management

```python
# Create portfolio
portfolio_service = PortfolioApplicationService(uow_factory)

portfolio_id = await portfolio_service.create_portfolio(
    portfolio_id="PORT123",
    initial_capital=Decimal("100000"),
    currency="USD"
)

# Add positions
await portfolio_service.add_position(
    portfolio_id="PORT123",
    symbol="AAPL",
    quantity=Decimal("100"),
    price=Decimal("150.00")
)

# Update prices
await portfolio_service.update_position_prices(
    portfolio_id="PORT123",
    prices={"AAPL": Decimal("155.00"), "MSFT": Decimal("300.00")}
)
```

### Strategy Execution

```python
# Register strategies
registry = StrategyRegistry()
registry.register("ma_crossover", MovingAverageStrategy)
registry.register("rsi", RSIStrategy)

# Create ensemble
factory = StrategyFactory(registry)
ensemble = factory.create_context("weighted_ensemble", {
    "min_strategies_for_signal": 2
})

# Add strategies
ensemble.add_strategy("ma_short", ma_strategy, weight=0.4)
ensemble.add_strategy("ma_long", ma_strategy, weight=0.3)
ensemble.add_strategy("rsi", rsi_strategy, weight=0.3)

# Execute
result = await ensemble.execute_strategy(market_data)
```

---

## Testing

### Repository Testing

```python
@pytest.mark.asyncio
async def test_repository_add_and_get():
    repo = InMemoryOrderRepository()
    order = Order(order_id="ORD123", symbol="AAPL", ...)

    await repo.add(order)
    retrieved = await repo.get("ORD123")

    assert retrieved.order_id == "ORD123"
```

### Unit of Work Testing

```python
@pytest.mark.asyncio
async def test_unit_of_work_commits_on_success():
    uow = TestUnitOfWork()

    with uow:
        order = Order(order_id="ORD123", symbol="AAPL", ...)
        uow.track_entity(order, state='new')

    assert uow.committed is True
```

### Service Layer Testing

```python
@pytest.mark.asyncio
async def test_create_order_service():
    service = OrderApplicationService(MockUnitOfWorkFactory())
    command = CreateOrderCommand(
        symbol="AAPL",
        quantity=Decimal("100"),
        price=Decimal("150.00"),
        side="buy",
        order_type="limit",
        portfolio_id="PORT123"
    )

    order_id = await service.create_order(command)

    assert order_id is not None
```

---

## Best Practices

### 1. Dependency Inversion

- Domain layer defines interfaces
- Infrastructure implements interfaces
- Application depends on abstractions

```python
# Good - depends on abstraction
class OrderService:
    def __init__(self, uow_factory: Callable[[], AbstractUnitOfWork]):
        self.uow_factory = uow_factory

# Bad - depends on concrete implementation
class OrderService:
    def __init__(self):
        self.uow = SqlAlchemyUnitOfWork()
```

### 2. Domain-Centric Design

- Business logic in entities, not services
- Services orchestrate, entities validate

```python
# Good - entity validates
class Order:
    def validate(self) -> bool:
        if self.quantity <= 0:
            self.validation_errors.append("Quantity must be positive")
        return len(self.validation_errors) == 0

# Bad - service validates
class OrderService:
    def create_order(self, symbol, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
```

### 3. Transaction Boundaries

- Use Unit of Work for transactions
- Keep transactions short
- Handle errors properly

```python
# Good - clear transaction boundary
async with uow_factory() as uow:
    order = await uow.orders.get(order_id)
    order.submit()
    # Automatic commit/rollback

# Bad - manual transaction management
uow = uow_factory()
try:
    order = uow.orders.get(order_id)
    order.submit()
    uow.commit()
except:
    uow.rollback()
```

### 4. Testing Strategy

- Use mock repositories for unit tests
- Test business logic in isolation
- Integration tests for persistence

```python
# Unit test with mocks
@pytest.mark.asyncio
async def test_order_validation():
    service = OrderApplicationService(MockUnitOfWorkFactory())
    # Test business logic only

# Integration test with real DB
@pytest.mark.asyncio
async def test_order_persistence():
    service = OrderApplicationService(SqlAlchemyUnitOfWork)
    # Test full stack
```

---

## References

- "Architecture Patterns with Python" by Percival & Gregory
- "Domain-Driven Design" by Evans
- "Clean Architecture" by Martin
- "Patterns of Enterprise Application Architecture" by Fowler

---

## File Structure

```
app/
├── domain/
│   ├── entities/
│   │   ├── order.py
│   │   ├── portfolio.py
│   │   └── backtest.py
│   ├── value_objects/
│   │   ├── capital.py
│   │   ├── money.py
│   │   └── risk_parameters.py
│   ├── repositories/
│   │   ├── base_repository.py      # NEW: Generic repository
│   │   ├── unit_of_work.py          # NEW: Unit of Work
│   │   ├── order_repository.py
│   │   ├── portfolio_repository.py
│   │   └── position_repository.py
│   └── factories/
│       └── __init__.py              # NEW: Factory patterns
├── application/
│   ├── services/
│   │   └── __init__.py              # NEW: Service layer
│   └── use_cases/
│       ├── run_backtest_use_case.py
│       └── analyze_backtest_results_use_case.py
├── strategies/
│   ├── strategy_registry.py         # NEW: Strategy registry
│   └── base.py
└── infrastructure/
    └── persistence/
        ├── sql_order_repository.py
        └── sql_portfolio_repository.py

tests/
├── unit/
│   ├── domain/
│   │   ├── repositories/
│   │   │   ├── test_base_repository.py    # NEW
│   │   │   └── test_unit_of_work.py       # NEW
│   │   └── factories/
│   │       └── test_factories.py          # NEW
│   ├── application/
│   │   └── test_service_layer.py          # NEW
│   └── strategies/
│       └── test_strategy_registry.py      # NEW
```

---

## Conclusion

This implementation provides a solid foundation for building maintainable, testable trading systems using Python architecture patterns. The patterns work together to create a clean separation of concerns while maintaining flexibility for future evolution.

For more details, refer to:
- "Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory
- The inline documentation in each module
- The test files for usage examples
