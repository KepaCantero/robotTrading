# Design Patterns in Python

Common design patterns with Python-specific implementations and best practices.

## Creational Patterns

### Singleton Pattern

Ensure a class has only one instance.

#### ✅ CORRECT - Module-level singleton (Pythonic)

```python
# config.py - simplest singleton
class Config:
    """Configuration singleton."""

    def __init__(self) -> None:
        self.settings: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value


# Module-level instance
config = Config()

# Usage - always the same instance
from config import config
config.set("api_key", "secret")
```

#### ✅ CORRECT - Class-based singleton with metaclass

```python
from typing import Any, ClassVar

class SingletonMeta(type):
    """Metaclass for singleton pattern."""

    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Database(metaclass=SingletonMeta):
    """Database singleton."""

    def __init__(self) -> None:
        self.connection = None

    def connect(self, connection_string: str) -> None:
        if self.connection is None:
            self.connection = create_connection(connection_string)

# Both instances are the same
db1 = Database()
db2 = Database()
assert db1 is db2  # True
```

### Factory Pattern

Create objects without specifying exact class.

#### ✅ CORRECT

```python
from abc import ABC, abstractmethod
from typing import Protocol

class PaymentProcessor(Protocol):
    def process(self, amount: float) -> bool:
        ...


class CreditCardProcessor:
    def process(self, amount: float) -> bool:
        print(f"Processing ${amount} via credit card")
        return True


class PayPalProcessor:
    def process(self, amount: float) -> bool:
        print(f"Processing ${amount} via PayPal")
        return True


class CryptoProcessor:
    def process(self, amount: float) -> bool:
        print(f"Processing ${amount} via crypto")
        return True


# Factory function
def create_processor(payment_type: str) -> PaymentProcessor:
    """Factory function creating appropriate processor."""
    processors: dict[str, type[PaymentProcessor]] = {
        "credit_card": CreditCardProcessor,
        "paypal": PayPalProcessor,
        "crypto": CryptoProcessor,
    }

    processor_class = processors.get(payment_type)
    if processor_class is None:
        raise ValueError(f"Unknown payment type: {payment_type}")

    return processor_class()


# Usage
processor = create_processor("paypal")
processor.process(100.0)
```

### Builder Pattern

Construct complex objects step by step.

#### ✅ CORRECT

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SQLQuery:
    """Built query object."""
    select: list[str]
    from_table: str
    where: Optional[str] = None
    join: Optional[str] = None
    order_by: Optional[str] = None
    limit: Optional[int] = None

    def build(self) -> str:
        """Build the SQL query."""
        query = f"SELECT {', '.join(self.select)} FROM {self.from_table}"

        if self.join:
            query += f" {self.join}"
        if self.where:
            query += f" WHERE {self.where}"
        if self.order_by:
            query += f" ORDER BY {self.order_by}"
        if self.limit:
            query += f" LIMIT {self.limit}"

        return query


class QueryBuilder:
    """Builder for SQL queries."""

    def __init__(self) -> None:
        self._select: list[str] = ["*"]
        self._from_table: str = ""
        self._where: Optional[str] = None
        self._join: Optional[str] = None
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None

    def select(self, *columns: str) -> "QueryBuilder":
        self._select = list(columns)
        return self

    def from_(self, table: str) -> "QueryBuilder":
        self._from_table = table
        return self

    def where(self, condition: str) -> "QueryBuilder":
        self._where = condition
        return self

    def join(self, join_clause: str) -> "QueryBuilder":
        self._join = join_clause
        return self

    def order_by(self, column: str) -> "QueryBuilder":
        self._order_by = column
        return self

    def limit(self, count: int) -> "QueryBuilder":
        self._limit = count
        return self

    def build(self) -> SQLQuery:
        return SQLQuery(
            select=self._select,
            from_table=self._from_table,
            where=self._where,
            join=self._join,
            order_by=self._order_by,
            limit=self._limit,
        )


# Usage - fluent interface
query = (
    QueryBuilder()
    .select("name", "email", "created_at")
    .from_("users")
    .where("status = 'active'")
    .order_by("created_at DESC")
    .limit(10)
    .build()
)

print(query.build())
# SELECT name, email, created_at FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 10
```

## Structural Patterns

### Adapter Pattern

Make incompatible interfaces work together.

#### ✅ CORRECT

```python
from typing import Protocol

# Target interface
class DataStorage(Protocol):
    def save(self, key: str, value: str) -> None:
        ...

    def load(self, key: str) -> str | None:
        ...


# Adaptee - incompatible interface
class LegacyDatabase:
    """Legacy system with different interface."""

    def write_record(self, table: str, record_id: int, data: str) -> bool:
        print(f"Writing to {table}, id={record_id}")
        return True

    def read_record(self, table: str, record_id: int) -> str | None:
        return f"Data from {table}, id={record_id}"


# Adapter
class DatabaseAdapter:
    """Adapts legacy database to DataStorage interface."""

    def __init__(self, legacy_db: LegacyDatabase, table: str) -> None:
        self._db = legacy_db
        self._table = table

    def save(self, key: str, value: str) -> None:
        """Convert key to record_id and save."""
        record_id = hash(key) % 1000000
        self._db.write_record(self._table, record_id, value)

    def load(self, key: str) -> str | None:
        """Convert key to record_id and load."""
        record_id = hash(key) % 1000000
        return self._db.read_record(self._table, record_id)


# Usage
legacy_db = LegacyDatabase()
storage: DataStorage = DatabaseAdapter(legacy_db, "users")

storage.save("user:123", "Alice")
data = storage.load("user:123")
```

### Decorator Pattern

Add behavior to objects dynamically.

#### ✅ CORRECT

```python
from typing import Callable, Protocol
from functools import wraps
import time

class Cacheable(Protocol):
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str) -> None:
        ...


class MemoryCache:
    """Simple in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._cache.get(key)

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value


# Function decorators
def timed(func: Callable) -> Callable:
    """Decorator to time function execution."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result

    return wrapper


def cached(cache: Cacheable) -> Callable[[Callable], Callable]:
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create cache key from arguments
            key = f"{func.__name__}:{args}:{kwargs}"

            # Try cache first
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # Execute and cache result
            result = func(*args, **kwargs)
            cache.set(key, str(result))
            return result

        return wrapper

    return decorator


# Usage
cache = MemoryCache()

@timed
@cached(cache)
def expensive_calculation(n: int) -> int:
    """Simulate expensive calculation."""
    time.sleep(0.1)
    return sum(range(n))


# Class decorators
class LoggedCache:
    """Decorator that adds logging to cache."""

    def __init__(self, cache: Cacheable) -> None:
        self._cache = cache

    def get(self, key: str) -> str | None:
        value = self._cache.get(key)
        print(f"Cache GET: {key} -> {value}")
        return value

    def set(self, key: str, value: str) -> None:
        print(f"Cache SET: {key} -> {value}")
        self._cache.set(key, value)


# Usage
logged_cache = LoggedCache(cache)
```

## Behavioral Patterns

### Strategy Pattern

Define family of algorithms, make them interchangeable.

#### ✅ CORRECT

```python
from typing import Protocol

class SortingStrategy(Protocol):
    """Sorting strategy interface."""

    def sort(self, data: list[int]) -> list[int]:
        ...


class BubbleSort:
    """Bubble sort implementation."""

    def sort(self, data: list[int]) -> list[int]:
        n = len(data)
        for i in range(n):
            for j in range(0, n - i - 1):
                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
        return data


class QuickSort:
    """Quick sort implementation."""

    def sort(self, data: list[int]) -> list[int]:
        if len(data) <= 1:
            return data

        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]

        return self.sort(left) + middle + self.sort(right)


class MergeSort:
    """Merge sort implementation."""

    def sort(self, data: list[int]) -> list[int]:
        if len(data) <= 1:
            return data

        mid = len(data) // 2
        left = self.sort(data[:mid])
        right = self.sort(data[mid:])

        return self._merge(left, right)

    def _merge(self, left: list[int], right: list[int]) -> list[int]:
        result = []
        i = j = 0

        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1

        result.extend(left[i:])
        result.extend(right[j:])
        return result


# Context
class Sorter:
    """Sorter that uses a strategy."""

    def __init__(self, strategy: SortingStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: SortingStrategy) -> None:
        self._strategy = strategy

    def sort(self, data: list[int]) -> list[int]:
        return self._strategy.sort(data)


# Usage
data = [64, 34, 25, 12, 22, 11, 90]

sorter = Sorter(BubbleSort())
result1 = sorter.sort(data.copy())

sorter.set_strategy(QuickSort())
result2 = sorter.sort(data.copy())

sorter.set_strategy(MergeSort())
result3 = sorter.sort(data.copy())
```

### Observer Pattern

Define one-to-many dependency between objects.

#### ✅ CORRECT

```python
from typing import Protocol, Callable
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    PRICE_UPDATE = "price_update"
    ORDER_FILLED = "order_filled"
    ERROR = "error"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]


class Observer(Protocol):
    """Observer interface."""

    def notify(self, event: Event) -> None:
        ...


class Subject:
    """Subject that observers can subscribe to."""

    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self, event: Event) -> None:
        """Notify all observers."""
        for observer in self._observers:
            observer.notify(event)


# Concrete observers
class LoggingObserver:
    """Logs all events."""

    def notify(self, event: Event) -> None:
        print(f"[LOG] {event.type.value}: {event.data}")


class AlertObserver:
    """Sends alerts for important events."""

    def __init__(self, min_price: float) -> None:
        self._min_price = min_price

    def notify(self, event: Event) -> None:
        if event.type == EventType.PRICE_UPDATE:
            price = event.data.get("price", 0)
            if price < self._min_price:
                print(f"[ALERT] Price dropped: {price}")


class MetricsObserver:
    """Tracks metrics for events."""

    def __init__(self) -> None:
        self._counts: dict[EventType, int] = {}

    def notify(self, event: Event) -> None:
        self._counts[event.type] = self._counts.get(event.type, 0) + 1

    def get_counts(self) -> dict[EventType, int]:
        return self._counts.copy()


# Usage
market = Subject()

market.attach(LoggingObserver())
market.attach(AlertObserver(min_price=50.0))
market.attach(MetricsObserver())

market.notify(Event(EventType.PRICE_UPDATE, {"symbol": "AAPL", "price": 45.0}))
market.notify(Event(EventType.ORDER_FILLED, {"order_id": "123", "quantity": 100}))
```

## Additional Patterns

### Repository Pattern

Abstract data access logic.

#### ✅ CORRECT

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class User:
    id: int
    name: str
    email: str


class Repository(ABC, Generic[T]):
    """Generic repository interface."""

    @abstractmethod
    def add(self, entity: T) -> None:
        pass

    @abstractmethod
    def get(self, entity_id: int) -> T | None:
        pass

    @abstractmethod
    def get_all(self) -> list[T]:
        pass

    @abstractmethod
    def update(self, entity: T) -> None:
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> None:
        pass


class UserRepository(Repository[User]):
    """User repository implementation."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    def add(self, entity: User) -> None:
        self._users[entity.id] = entity

    def get(self, entity_id: int) -> User | None:
        return self._users.get(entity_id)

    def get_all(self) -> list[User]:
        return list(self._users.values())

    def update(self, entity: User) -> None:
        if entity.id in self._users:
            self._users[entity.id] = entity

    def delete(self, entity_id: int) -> None:
        self._users.pop(entity_id, None)

    def find_by_email(self, email: str) -> User | None:
        """Custom query method."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None


# Usage
repo = UserRepository()
repo.add(User(1, "Alice", "alice@example.com"))
repo.add(User(2, "Bob", "bob@example.com"))

user = repo.get(1)
all_users = repo.get_all()
alice = repo.find_by_email("alice@example.com")
```

### Dependency Injection Pattern

Inject dependencies rather than create them internally.

#### ✅ CORRECT - Constructor injection

```python
from typing import Protocol

class Database(Protocol):
    def query(self, sql: str) -> list[dict]:
        ...


class Logger(Protocol):
    def log(self, message: str) -> None:
        ...


class PostgreSQLDatabase:
    def query(self, sql: str) -> list[dict]:
        # Actual DB logic
        return []


class FileLogger:
    def log(self, message: str) -> None:
        with open("app.log", "a") as f:
            f.write(f"{message}\n")


class UserService:
    """Service with injected dependencies."""

    def __init__(self, database: Database, logger: Logger) -> None:
        self._database = database
        self._logger = logger

    def get_user(self, user_id: int) -> dict | None:
        self._logger.log(f"Fetching user {user_id}")
        results = self._database.query(f"SELECT * FROM users WHERE id = {user_id}")
        return results[0] if results else None


# Usage - dependencies injected from outside
db = PostgreSQLDatabase()
logger = FileLogger()
service = UserService(db, logger)
```

#### ✅ CORRECT - FastAPI dependency injection

```python
from fastapi import Depends
from typing import Annotated

async def get_database() -> Database:
    return PostgreSQLDatabase()


async def get_logger() -> Logger:
    return FileLogger()


# Injected automatically by FastAPI
async def endpoint(
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    return user_service.get_user(1)
```

## When to Use Patterns

| Pattern | Use When |
|---------|----------|
| **Singleton** | You need exactly one instance (config, database connection) |
| **Factory** | You don't know exact type until runtime |
| **Builder** | Constructing complex objects with many optional parts |
| **Adapter** | Integrating with external/legacy systems |
| **Decorator** | Adding behavior without modifying original class |
| **Strategy** | Multiple interchangeable algorithms |
| **Observer** | One-to-many event notification |
| **Repository** | Separating data access from business logic |

## Anti-Patterns to Avoid

```python
# ❌ God Object - class doing too much
class GodObject:
    def save_to_db(self): pass
    def send_email(self): pass
    def validate_input(self): pass
    def render_ui(self): pass

# ✅ Separate classes with single responsibilities

# ❌ Singleton abuse - using singleton for convenience
class Cache:
    instance = None
    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

# ✅ Pass dependencies explicitly or use DI container

# ❌ Premature abstraction
class AbstractStrategyFactory(ABC):
    @abstractmethod
    def create_strategy(self) -> Strategy:
        pass

# ✅ Keep it simple until you actually need multiple implementations
```
