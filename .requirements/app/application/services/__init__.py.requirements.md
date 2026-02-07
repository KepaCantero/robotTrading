# Requirements: application/services/__init__.py

## Source File Analysis
- **File Path**: `app/application/services/__init__.py`
- **Lines of Code**: 778
- **Layer**: Application Layer
- **Purpose**: Service Layer Pattern implementation following CQRS

## Purpose

This module implements the Service Layer pattern as described in "Architecture Patterns with Python" (Cosmic Python) by Percival & Gregory. It provides:

1. **CQRS Pattern**: Separate Command (write) and Query (read) base classes
2. **Application Services**: Orchestration layer for use cases
3. **Trading Services**: Order and Portfolio application services
4. **Service Orchestration**: Multi-service workflow coordination

## Dependencies

### Internal
- `app.domain.entities.order` - Order, OrderStatus entities
- `app.domain.entities.portfolio` - Portfolio, Position entities
- `app.domain.repositories.unit_of_work` - AbstractUnitOfWork
- `.input_profile_router` - InputProfileRouter, SystemConfiguration
- `.risk_configurator` - RiskConfigurator, RiskLimit, VaRResult
- `.tax_optimizer` - TaxOptimizer, TaxLot, TaxCalculation

### External
- `abc` - ABC, abstractmethod
- `dataclasses` - dataclass
- `datetime` - datetime
- `decimal` - Decimal
- `typing` - Any, Dict, Generic, List, Optional, TypeVar
- `logging` - logger

## Classes/Functions

### CQRS Base Classes
- `Command(ABC)` - Base class for commands (state-changing operations)
- `Query[T](ABC, Generic)` - Base class for queries (read operations)
- `CommandHandler(ABC)` - Base class for command handlers
- `ApplicationService(ABC)` - Base class for application services
- `ServiceOrchestrator` - Coordinates multiple application services

### Commands
- `CreateOrderCommand(Command)` - Command to create new orders
- `SubmitOrderCommand(Command)` - Command to submit orders for execution
- `CancelOrderCommand(Command)` - Command to cancel pending orders

### Queries
- `GetOrderQuery(Query[Optional[Order]])` - Query to get order by ID
- `GetPortfolioOrdersQuery(Query[List[Order]])` - Query to get all portfolio orders

### Services
- `OrderApplicationService(ApplicationService)` - Order management service
- `PortfolioApplicationService(ApplicationService)` - Portfolio management service

### Exceptions
- `ValidationError(Exception)` - Command validation failures
- `BusinessRuleError(Exception)` - Business rule violations
- `NotFoundError(Exception)` - Entity not found

## Business Logic

The Service Layer follows these principles:
1. **No business logic in services** - delegates to domain entities
2. **Transaction boundaries** - uses Unit of Work pattern
3. **Input validation** - validates commands before execution
4. **Orchestration** - coordinates between aggregates and repositories

### Order Management Flow
1. User creates `CreateOrderCommand`
2. `OrderApplicationService.create_order()` validates command
3. Loads portfolio, creates order entity
4. Domain validates business rules
5. Portfolio checks risk limits
6. Saves order via repository

## Data Models

Commands use dataclass pattern:
- `CreateOrderCommand`: symbol, quantity, price, order_type, side, portfolio_id
- `SubmitOrderCommand`: order_id
- `CancelOrderCommand`: order_id, reason (optional)

## API Contracts

### Create Order
```python
command = CreateOrderCommand(
    symbol="AAPL",
    quantity=Decimal('100'),
    price=Decimal('150.00'),
    order_type='limit',
    side='buy',
    portfolio_id='PORT123'
)
order_id = await order_service.create_order(command)
```

### Submit Order
```python
command = SubmitOrderCommand(order_id="ORD_20260207...")
await order_service.submit_order(command)
```

## Error Handling

- `ValidationError` - Raised when command validation fails
- `BusinessRuleError` - Raised when business rule is violated
- `NotFoundError` - Raised when entity is not found
- `ValueError` - Used for various validation errors (consider using custom exceptions)

## Performance Considerations

1. **Async operations** - All service methods are async
2. **Transaction management** - Uses Unit of Work for atomic operations
3. **Query optimization** - Separate query path from command path (CQRS)

## Testing Strategy

1. **Unit tests** - Test each service method independently
2. **Mock repositories** - Mock Unit of Work and repositories
3. **Command validation** - Test command validation rules
4. **Transaction boundaries** - Verify rollback on errors

## Critical Rules (from BASE_RULES.md)

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| ARCH-001 | Layered architecture | ✅ PASS | Application layer coordinates domain/infrastructure |
| ARCH-003 | No framework in domain | ✅ PASS | No framework imports in domain dependencies |
| DP-004 | Dependency injection | ✅ PASS | Uses uow_factory injection |
| ASYNC-001 | Use async def | ✅ PASS | All service methods properly async |
| ASYNC-003 | Async context managers | ✅ PASS | Uses `async with` for UoW |
| CC-006 | Explicit error handling | ⚠️ NOTE | Uses ValueError in places (could use custom exceptions) |
| LOG-004 | Error logging | ✅ PASS | Uses logger.info for operations |
| TRD-002 | Risk validation | ✅ PASS | Portfolio risk limits enforced |

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-07T05:35:00Z |
| **Audit Status** | PASSED |

## Notes

1. **Type Safety**: Some uses of `Any` type (uow_factory) are acceptable for factory pattern
2. **Callable Type**: Line 216 uses `callable` instead of `Callable` - minor type hint improvement possible
3. **Error Types**: Uses `ValueError` in several places - custom exception types could improve error handling
4. **Documentation**: Excellent docstrings with examples
5. **Architecture**: Properly implements Service Layer pattern with CQRS

## Acceptance Criteria

- [x] Follows Service Layer pattern (Percival & Gregory)
- [x] CQRS separation (Command vs Query)
- [x] Dependency injection via constructor
- [x] Async/await properly used
- [x] Unit of Work pattern for transactions
- [x] No business logic in service layer
- [x] Proper error handling and logging

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Last updated: 2026-02-07T05:35:00Z*
