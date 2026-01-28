# Advanced Design Patterns

Advanced Python design patterns for enterprise-grade production code.

## Table of Contents
1. Creational Patterns (Singleton, Factory, Builder)
2. Structural Patterns (Adapter, Decorator)
3. Behavioral Patterns (Strategy, Observer)
4. Repository Pattern
5. Dependency Injection

---

## Creational Patterns

### Singleton (Thread-Safe)

```python
# ✅ CORRECT - Thread-safe Singleton with double-checked locking
from threading import Lock
from typing import Any, ClassVar

class SingletonMeta(type):
    """Thread-safe Singleton metaclass with double-checked locking."""

    _instances: ClassVar[dict[type, object]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            with cls._lock:
                # Double-checked locking pattern
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class DatabaseConnection(metaclass=SingletonMeta):
    """Singleton database connection."""

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.connection: Any = self._create_connection()

    def _create_connection(self) -> Any:
        """Create database connection."""
        # Connection logic
        return None
```

### Factory Pattern

```python
# ✅ CORRECT - Factory with type safety
from abc import ABC, abstractmethod
from enum import Enum
from typing import Type

class VehicleType(Enum):
    """Vehicle types."""
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"


class Vehicle(ABC):
    """Abstract vehicle."""

    @abstractmethod
    def start(self) -> None:
        """Start vehicle."""
        pass


class Car(Vehicle):
    def start(self) -> None:
        print("Car started")


class Truck(Vehicle):
    def start(self) -> None:
        print("Truck started")


class Motorcycle(Vehicle):
    def start(self) -> None:
        print("Motorcycle started")


class VehicleFactory:
    """Factory for creating vehicles."""

    _creators: dict[VehicleType, Type[Vehicle]] = {
        VehicleType.CAR: Car,
        VehicleType.TRUCK: Truck,
        VehicleType.MOTORCYCLE: Motorcycle,
    }

    @classmethod
    def create_vehicle(cls, vehicle_type: VehicleType) -> Vehicle:
        """Create vehicle by type."""
        creator = cls._creators.get(vehicle_type)
        if creator is None:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")
        return creator()
```

### Builder Pattern

```python
# ✅ CORRECT - Builder with fluent interface
from dataclasses import dataclass, field

@dataclass
class Pizza:
    """Pizza product."""
    size: str
    cheese: bool = False
    pepperoni: bool = False
    mushrooms: bool = False
    olives: bool = False


class PizzaBuilder:
    """Builder for creating pizzas."""

    def __init__(self, size: str) -> None:
        self._pizza = Pizza(size=size)

    def add_cheese(self) -> "PizzaBuilder":
        """Add cheese."""
        self._pizza.cheese = True
        return self

    def add_pepperoni(self) -> "PizzaBuilder":
        """Add pepperoni."""
        self._pizza.pepperoni = True
        return self

    def add_mushrooms(self) -> "PizzaBuilder":
        """Add mushrooms."""
        self._pizza.mushrooms = True
        return self

    def add_olives(self) -> "PizzaBuilder":
        """Add olives."""
        self._pizza.olives = True
        return self

    def build(self) -> Pizza:
        """Build and return pizza."""
        return self._pizza


# Usage
pizza = (
    PizzaBuilder("large")
    .add_cheese()
    .add_pepperoni()
    .add_mushrooms()
    .build()
)
```

---

## Structural Patterns

### Adapter Pattern

```python
# ✅ CORRECT - Adapter for legacy code integration
from abc import ABC, abstractmethod

class LegacyRectangle:
    """Legacy rectangle class."""

    def __init__(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


class Shape(ABC):
    """Modern shape interface."""

    @abstractmethod
    def get_area(self) -> float:
        """Get shape area."""
        pass


class RectangleAdapter(Shape):
    """Adapter for legacy rectangle."""

    def __init__(self, rectangle: LegacyRectangle) -> None:
        self._rectangle = rectangle

    def get_area(self) -> float:
        """Calculate area from legacy rectangle."""
        width = abs(self._rectangle.x2 - self._rectangle.x1)
        height = abs(self._rectangle.y2 - self._rectangle.y1)
        return width * height
```

### Decorator Pattern

```python
# ✅ CORRECT - Decorators with proper typing
from functools import wraps
from time import time
from typing import Callable, Any, ParamSpec, TypeVar

P = ParamSpec('P')
R = TypeVar('R')


def timing_decorator(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator to measure function execution time."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time()
        result = func(*args, **kwargs)
        end = time()
        print(f"{func.__name__} took {end - start:.2f}s")
        return result

    return wrapper


def retry_decorator(max_attempts: int = 3) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to retry function on failure."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"Attempt {attempt + 1} failed: {e}")

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state")  # Should never reach

        return wrapper

    return decorator


@timing_decorator
@retry_decorator(max_attempts=3)
def fetch_data(url: str) -> dict[str, Any]:
    """Fetch data from URL with timing and retry."""
    return {}
```

---

## Behavioral Patterns

### Strategy Pattern

```python
# ✅ CORRECT - Strategy with Protocol
from typing import Protocol

class SortStrategy(Protocol):
    """Abstract sorting strategy."""

    def sort(self, data: list[int]) -> list[int]:
        """Sort data."""
        pass


class BubbleSortStrategy:
    """Bubble sort implementation."""

    def sort(self, data: list[int]) -> list[int]:
        """Sort using bubble sort."""
        result = data.copy()
        n = len(result)
        for i in range(n):
            for j in range(0, n - i - 1):
                if result[j] > result[j + 1]:
                    result[j], result[j + 1] = result[j + 1], result[j]
        return result


class QuickSortStrategy:
    """Quick sort implementation."""

    def sort(self, data: list[int]) -> list[int]:
        """Sort using quick sort."""
        if len(data) <= 1:
            return data

        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]

        return self.sort(left) + middle + self.sort(right)


class Sorter:
    """Context that uses a sorting strategy."""

    def __init__(self, strategy: SortStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: SortStrategy) -> None:
        """Change sorting strategy."""
        self._strategy = strategy

    def sort(self, data: list[int]) -> list[int]:
        """Sort using current strategy."""
        return self._strategy.sort(data)
```

### Observer Pattern

```python
# ✅ CORRECT - Observer with Protocol
from abc import ABC, abstractmethod
from typing import Protocol

class Observer(Protocol):
    """Abstract observer."""

    def update(self, message: str) -> None:
        """Receive update from subject."""
        pass


class Subject:
    """Subject that notifies observers."""

    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Detach an observer."""
        self._observers.remove(observer)

    def notify(self, message: str) -> None:
        """Notify all observers."""
        for observer in self._observers:
            observer.update(message)


class EmailNotifier:
    """Observer that sends emails."""

    def update(self, message: str) -> None:
        """Send email notification."""
        print(f"Email sent: {message}")


class SMSNotifier:
    """Observer that sends SMS."""

    def update(self, message: str) -> None:
        """Send SMS notification."""
        print(f"SMS sent: {message}")
```

---

## Repository Pattern

```python
# ✅ CORRECT - Generic Repository
from typing import TypeVar, Generic, Protocol, TypeAlias

T = TypeVar('T')
Id: TypeAlias = int | str


class Repository(Protocol[T]):
    """Generic repository interface."""

    def add(self, entity: T) -> None:
        """Add entity to repository."""
        ...

    def get(self, entity_id: Id) -> T | None:
        """Get entity by ID."""
        ...

    def get_all(self) -> list[T]:
        """Get all entities."""
        ...

    def update(self, entity: T) -> None:
        """Update entity."""
        ...

    def delete(self, entity_id: Id) -> None:
        """Delete entity by ID."""
        ...


class InMemoryRepository(Generic[T]):
    """In-memory repository implementation."""

    def __init__(self) -> None:
        self._items: dict[Id, T] = {}

    def add(self, entity: T) -> None:
        entity_id = getattr(entity, "id", None)
        if entity_id is not None:
            self._items[entity_id] = entity

    def get(self, entity_id: Id) -> T | None:
        return self._items.get(entity_id)

    def get_all(self) -> list[T]:
        return list(self._items.values())

    def update(self, entity: T) -> None:
        entity_id = getattr(entity, "id", None)
        if entity_id is not None and entity_id in self._items:
            self._items[entity_id] = entity

    def delete(self, entity_id: Id) -> None:
        self._items.pop(entity_id, None)
```

---

## Dependency Injection

```python
# ✅ CORRECT - Dependency Injection with Protocol
from typing import Protocol, Callable

class Database(Protocol):
    """Database interface."""

    def query(self, sql: str) -> list[dict]:
        ...

    def execute(self, sql: str) -> None:
        ...


class Logger(Protocol):
    """Logger interface."""

    def log(self, message: str) -> None:
        ...


class PostgreSQLDatabase:
    def query(self, sql: str) -> list[dict]:
        return []

    def execute(self, sql: str) -> None:
        pass


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


# FastAPI-style dependency injection
from fastapi import Depends

def get_database() -> Database:
    return PostgreSQLDatabase()


def get_logger() -> Logger:
    return FileLogger()


async def endpoint(
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> dict:
    return user_service.get_user(1)
```

---

## Anti-Patterns to Avoid

```python
# ❌ God Object - class doing too much
class GodObject:
    def save_to_db(self): pass
    def send_email(self): pass
    def validate_input(self): pass
    def render_ui(self): pass

# ❌ Singleton abuse
class CacheSingleton:
    instance = None

# ❌ Premature abstraction
class AbstractStrategyFactory(ABC):
    @abstractmethod
    def create_strategy(self) -> Strategy:
        pass
```

## When to Use Patterns

| Pattern | Use When |
|---------|----------|
| **Singleton** | Exactly one instance needed (config, DB connection) |
| **Factory** | Object type unknown until runtime |
| **Builder** | Complex objects with optional parts |
| **Adapter** | Integrating external/legacy systems |
| **Decorator** | Adding behavior without modifying class |
| **Strategy** | Multiple interchangeable algorithms |
| **Observer** | One-to-many event notification |
| **Repository** | Separating data access from business logic |
