# Clean Architecture Quick Reference

## Dependency Rule

**The dependency rule: Dependencies must point inward.**

```
┌─────────────────────────────────────────┐
│           API Layer                     │  ← Can depend on anything
├─────────────────────────────────────────┤
│       Infrastructure                    │  ← Can depend on Application, Domain
├─────────────────────────────────────────┤
│       Application                       │  ← Can depend only on Domain
├─────────────────────────────────────────┤
│          Domain                         │  ← NO dependencies (core)
└─────────────────────────────────────────┘
```

## File Structure

```
app/
├── domain/                    # Core business logic (NO dependencies)
│   ├── entities/             # Business entities
│   │   ├── order.py
│   │   ├── portfolio.py
│   │   └── backtest.py
│   ├── value_objects/        # Value objects
│   │   ├── money.py
│   │   ├── capital.py
│   │   └── risk_parameters.py
│   ├── repositories/         # Repository interfaces (contracts)
│   │   ├── order_repository.py
│   │   └── portfolio_repository.py
│   └── interfaces/           # Domain service interfaces
│       ├── market_data_source.py
│       └── broker.py
│
├── application/              # Use cases and orchestration
│   ├── use_cases/           # Business use cases
│   │   ├── run_backtest_use_case.py
│   │   └── analyze_results_use_case.py
│   └── interfaces/          # Application interfaces
│       └── backtest_presenter.py
│
├── infrastructure/           # External implementations
│   ├── persistence/         # Repository implementations
│   │   ├── postgres_order_repository.py
│   │   └── in_memory_portfolio_repository.py
│   └── external/            # External service adapters
│       ├── yahoo_finance_adapter.py
│       └── alpaca_broker_adapter.py
│
└── api/                     # External interface
    ├── portfolio.py         # Portfolio endpoints
    └── trading.py           # Trading endpoints
```

## Code Examples

### 1. Domain Entity

```python
# app/domain/entities/order.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from enum import Enum

# NO external imports allowed!

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"

@dataclass
class Order:
    """Pure domain entity with business rules."""
    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = None

    def __post_init__(self):
        """Validate invariants."""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def fill(self) -> None:
        """Business rule: Fill the order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be filled")
        self.status = OrderStatus.FILLED

    def cancel(self) -> None:
        """Business rule: Cancel the order."""
        if self.status == OrderStatus.FILLED:
            raise ValueError("Filled orders cannot be cancelled")
        self.status = OrderStatus.CANCELLED
```

### 2. Value Object

```python
# app/domain/value_objects/money.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)  # Immutable
class Money:
    """Value object representing money."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        """Validate money invariants."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency is required")

    def add(self, other: 'Money') -> 'Money':
        """Add two money amounts."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, factor: Decimal) -> 'Money':
        """Multiply money by a factor."""
        return Money(self.amount * factor, self.currency)
```

### 3. Repository Interface (Domain)

```python
# app/domain/repositories/order_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.order import Order

class OrderRepository(ABC):
    """Interface for order data access."""

    @abstractmethod
    async def save(self, order: Order) -> None:
        """Save an order."""
        pass

    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        """Find order by ID."""
        pass

    @abstractmethod
    async def find_by_portfolio(self, portfolio_id: str) -> List[Order]:
        """Find all orders for a portfolio."""
        pass
```

### 4. Repository Implementation (Infrastructure)

```python
# app/infrastructure/persistence/postgres_order_repository.py
from typing import List, Optional
from app.domain.entities.order import Order
from app.domain.repositories.order_repository import OrderRepository

class PostgresOrderRepository(OrderRepository):
    """PostgreSQL implementation of order repository."""

    def __init__(self, db_session):
        self._db = db_session

    async def save(self, order: Order) -> None:
        """Save order to PostgreSQL."""
        query = """
            INSERT INTO orders (order_id, symbol, quantity, price, status)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (order_id) DO UPDATE
            SET symbol = $2, quantity = $3, price = $4, status = $5
        """
        await self._db.execute(
            query,
            order.order_id,
            order.symbol,
            order.quantity,
            order.price,
            order.status.value
        )

    async def find_by_id(self, order_id: str) -> Optional[Order]:
        """Find order by ID in PostgreSQL."""
        query = "SELECT * FROM orders WHERE order_id = $1"
        row = await self._db.fetchrow(query, order_id)
        if not row:
            return None
        return Order(
            order_id=row['order_id'],
            symbol=row['symbol'],
            quantity=row['quantity'],
            price=row['price'],
            status=OrderStatus(row['status'])
        )

    async def find_by_portfolio(self, portfolio_id: str) -> List[Order]:
        """Find all orders for a portfolio."""
        query = "SELECT * FROM orders WHERE portfolio_id = $1"
        rows = await self._db.fetch(query, portfolio_id)
        return [self._row_to_order(row) for row in rows]
```

### 5. Use Case (Application)

```python
# app/application/use_cases/execute_trade_use_case.py
from typing import Optional
from app.domain.entities.order import Order
from app.domain.repositories.order_repository import OrderRepository
from app.domain.value_objects.money import Money

class ExecuteTradeUseCase:
    """Use case for executing trades."""

    def __init__(self, order_repository: OrderRepository):
        """Initialize with required dependencies."""
        self._order_repository = order_repository

    async def execute(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Order:
        """
        Execute a trade.

        This use case orchestrates the trade execution process:
        1. Create order entity
        2. Validate business rules
        3. Save to repository
        4. Return result
        """
        # Create order (domain logic)
        order = Order(
            order_id=self._generate_order_id(),
            symbol=symbol,
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price))
        )

        # Business rules
        self._validate_order(order)

        # Persist (infrastructure)
        await self._order_repository.save(order)

        return order

    def _validate_order(self, order: Order) -> None:
        """Validate order business rules."""
        if order.quantity < 100:
            raise ValueError("Minimum quantity is 100")
        if order.price <= 0:
            raise ValueError("Price must be positive")

    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        import uuid
        return f"order_{uuid.uuid4().hex[:8]}"
```

### 6. External Interface (Domain)

```python
# app/domain/interfaces/market_data_source.py
from abc import ABC, abstractmethod
from datetime import datetime
import pandas as pd

class MarketDataSourceInterface(ABC):
    """Interface for market data sources."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Fetch OHLCV data."""
        pass
```

### 7. External Adapter (Infrastructure)

```python
# app/infrastructure/external/yahoo_finance_adapter.py
from datetime import datetime
import pandas as pd
import yfinance as yf
from app.domain.interfaces.market_data_source import MarketDataSourceInterface

class YahooFinanceAdapter(MarketDataSourceInterface):
    """Yahoo Finance implementation of market data source."""

    async def fetch_ohlcv(
        self,
        symbol: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame:
        """Fetch data from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start, end=end)
        return data
```

### 8. API Endpoint

```python
# app/api/trading.py
from fastapi import APIRouter, Depends
from app.application.use_cases.execute_trade_use_case import ExecuteTradeUseCase

router = APIRouter()

@router.post("/trade")
async def execute_trade(
    symbol: str,
    quantity: float,
    price: float,
    use_case: ExecuteTradeUseCase = Depends()
):
    """Execute a trade."""
    order = await use_case.execute(symbol, quantity, price)
    return {"order_id": order.order_id, "status": order.status.value}
```

## Testing Examples

### Testing Use Cases

```python
# tests/unit/application/test_execute_trade_use_case.py
import pytest
from app.application.use_cases.execute_trade_use_case import ExecuteTradeUseCase
from app.domain.entities.order import Order

class MockOrderRepository:
    """Mock repository for testing."""
    def __init__(self):
        self.saved_orders = []

    async def save(self, order: Order) -> None:
        self.saved_orders.append(order)

    async def find_by_id(self, order_id: str):
        pass

    async def find_by_portfolio(self, portfolio_id: str):
        pass

@pytest.mark.asyncio
async def test_execute_trade():
    """Test trade execution use case."""
    # Arrange
    mock_repo = MockOrderRepository()
    use_case = ExecuteTradeUseCase(mock_repo)

    # Act
    order = await use_case.execute("AAPL", 100, 150.0)

    # Assert
    assert order.symbol == "AAPL"
    assert order.quantity == 100
    assert len(mock_repo.saved_orders) == 1
    assert mock_repo.saved_orders[0].order_id == order.order_id
```

### Testing Entities

```python
# tests/unit/domain/test_order.py
import pytest
from decimal import Decimal
from app.domain.entities.order import Order, OrderStatus

def test_order_creation():
    """Test order creation with valid data."""
    order = Order(
        order_id="order_123",
        symbol="AAPL",
        quantity=Decimal("100"),
        price=Decimal("150.0")
    )
    assert order.status == OrderStatus.PENDING

def test_order_fill():
    """Test filling an order."""
    order = Order(
        order_id="order_123",
        symbol="AAPL",
        quantity=Decimal("100"),
        price=Decimal("150.0")
    )
    order.fill()
    assert order.status == OrderStatus.FILLED

def test_order_invalid_quantity():
    """Test order with invalid quantity."""
    with pytest.raises(ValueError, match="Quantity must be positive"):
        Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=Decimal("-100"),
            price=Decimal("150.0")
        )
```

## Common Patterns

### Dependency Injection in FastAPI

```python
# app/main.py
from fastapi import FastAPI
from app.infrastructure.persistence.postgres_order_repository import PostgresOrderRepository
from app.application.use_cases.execute_trade_use_case import ExecuteTradeUseCase

app = FastAPI()

# Setup dependencies
@app.on_event("startup")
async def startup():
    """Initialize dependencies."""
    db_session = get_db_session()
    order_repository = PostgresOrderRepository(db_session)

    # Register as dependency
    app.dependency_overrides[ExecuteTradeUseCase] = lambda: ExecuteTradeUseCase(order_repository)
```

### Factory Pattern

```python
# app/application/factories/repository_factory.py
from app.domain.repositories.order_repository import OrderRepository
from app.infrastructure.persistence.postgres_order_repository import PostgresOrderRepository
from app.infrastructure.persistence.in_memory_order_repository import InMemoryOrderRepository

class RepositoryFactory:
    """Factory for creating repository instances."""

    @staticmethod
    def create_order_repository(config: dict) -> OrderRepository:
        """Create order repository based on config."""
        if config.get("env") == "test":
            return InMemoryOrderRepository()
        else:
            return PostgresOrderRepository(config["db_session"])
```

## Architecture Tests

```python
# tests/architecture/test_dependencies.py
import pytest
from pathlib import Path

def test_domain_layer_has_no_external_dependencies():
    """Domain layer must not import from outer layers."""
    domain_dir = Path("app/domain")

    for py_file in domain_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file) as f:
            content = f.read()

        # Check for forbidden imports
        assert "from app.infrastructure" not in content
        assert "from app.application" not in content
        assert "from app.api" not in content
        assert "from app.services" not in content

def test_file_size_limits():
    """No file should exceed 300 lines."""
    app_dir = Path("app")

    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file) as f:
            lines = sum(1 for _ in f)

        assert lines <= 300, f"{py_file} has {lines} lines (max: 300)"
```

## Checklist for New Features

- [ ] Start in domain layer (entities, value objects)
- [ ] Define repository interfaces in domain
- [ ] Implement use cases in application layer
- [ ] Create infrastructure implementations
- [ ] Add API endpoints (if needed)
- [ ] Write unit tests for entities
- [ ] Write integration tests for use cases
- [ ] Run architecture tests
- [ ] Update documentation

## Quick Tips

1. **Always depend on abstractions** (interfaces), not concretions
2. **Domain entities have no dependencies** on outer layers
3. **Use cases orchestrate** but don't contain business logic
4. **Infrastructure implements** domain interfaces
5. **API layer is thin** - just handles HTTP, delegates to use cases
6. **Test the domain** thoroughly - it's the most important layer
7. **Mock dependencies** when testing use cases
8. **Keep files small** - max 300 lines per file
9. **Value objects are immutable** - use @dataclass(frozen=True)
10. **Entities have identity** - value objects don't
