# Python Type Hints Rules

Type hinting standards using Mypy in strict mode with 100% coverage.

## Tool Configuration

### Mypy (Strict Type Checker)

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_configs = true
warn_unreachable = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

## Rule 1: All Functions Must Have Type Hints

Every function must have type hints for all parameters and return type.

### ✅ CORRECT

```python
from typing import Optional

def calculate_profit(revenue: float, costs: float) -> float:
    """Calculate profit from revenue and costs."""
    return revenue - costs

def find_user(user_id: int) -> Optional[dict[str, Any]]:
    """Find user by ID, returns None if not found."""
    return database.query(user_id)

def process_items(items: list[str]) -> dict[str, int]:
    """Process items and return counts."""
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts
```

### ❌ INCORRECT

```python
# No type hints - fails Mypy strict mode!
def calculate_profit(revenue, costs):
    return revenue - costs

# Missing return type
def find_user(user_id: int):
    return database.query(user_id)

# Missing parameter types
def process_items(items) -> dict:
    ...
```

## Rule 2: Use Modern Type Syntax (Python 3.10+)

Use `list[T]`, `dict[K, V]`, `X | None` instead of `List[T]`, `Dict[K, V]`, `Optional[X]`.

### ✅ CORRECT

```python
# Modern syntax (Python 3.10+)
from collections.abc import Callable

def process_data(
    items: list[str],
    mapping: dict[str, int],
    callback: Callable[[str], int],
) -> dict[str, int] | None:
    """Process data with callback."""
    if not items:
        return None
    result: dict[str, int] = {}
    for item in items:
        result[item] = callback(item)
    return result

# Union with pipe operator
value: str | int | None = None

# Type alias
UserId = int
UserData = dict[str, str | int]

def get_user(user_id: UserId) -> UserData | None:
    ...
```

### ❌ INCORRECT

```python
# Old syntax (avoid!)
from typing import List, Dict, Optional, Callable, Union

def process_data(
    items: List[str],
    mapping: Dict[str, int],
    callback: Callable[[str], int],
) -> Optional[Dict[str, int]]:
    ...

# Verbose Optional
value: Optional[str] = None  # Use: str | None

# Verbose Union
result: Union[str, int, None] = None  # Use: str | int | None
```

## Rule 3: Never Use Any Without Explicit Type Ignore

Using `Any` defeats type checking. Use specific types or `object` with type ignore + comment.

### ✅ CORRECT

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from external_module import ExternalType  # type: ignore

# Use Protocol for duck typing
from typing import Protocol

class Renderable(Protocol):
    def render(self) -> str: ...

def render_all(items: list[Renderable]) -> str:
    return "\n".join(item.render() for item in items)

# Use TypeVar for generics
from typing import TypeVar

T = TypeVar('T')

def first(items: list[T]) -> T | None:
    return items[0] if items else None
```

### ❌ INCORRECT

```python
# Any - defeats type checking!
def process(data: Any) -> Any:
    return data

# List[Any] - no type safety!
def process_items(items: list[Any]) -> dict[str, Any]:
    ...
```

## Rule 4: Type Hints for Class Attributes

All class attributes must have type hints. Use `ClassVar` for class variables.

### ✅ CORRECT

```python
from typing import ClassVar, Final

class TradingEngine:
    """Trading engine with typed attributes."""

    # Class variables
    MAX_POSITIONS: ClassVar[int] = 100
    DEFAULT_LEVERAGE: ClassVar[float] = 1.0

    # Instance variables with type in __init__
    def __init__(self, initial_balance: float) -> None:
        self.balance: float = initial_balance
        self.positions: dict[str, int] = {}

    # Final constants
    MIN_TRADE_SIZE: Final[float] = 0.01

# With dataclass
from dataclasses import dataclass

@dataclass
class Trade:
    symbol: str
    quantity: int
    price: float
    timestamp: float
```

### ❌ INCORRECT

```python
class TradingEngine:
    # Missing type hints
    MAX_POSITIONS = 100
    DEFAULT_LEVERAGE = 1.0

    def __init__(self, initial_balance: float):
        self.balance = initial_balance  # Missing type
        self.positions = {}  # Missing type
```

## Rule 5: TypedDict for Structured Data

Use `TypedDict` for dictionary structures with specific keys.

### ✅ CORRECT

```python
from typing import TypedDict, Required, NotRequired

class TradeRequest(TypedDict):
    """Type for trade request data."""
    symbol: str
    quantity: int
    price: float
    order_type: Required[str]
    comment: NotRequired[str]

def process_trade(request: TradeRequest) -> None:
    """Process typed trade request."""
    symbol = request["symbol"]
    quantity = request["quantity"]
    ...

# Alternative syntax for simple cases
TradeResult = TypedDict('TradeResult', {
    'order_id': str,
    'status': str,
    'executed_at': float,
})
```

### ❌ INCORRECT

```python
# Untyped dict - error prone!
def process_trade(request: dict) -> None:
    symbol = request["symbol"]  # What type is this?
    quantity = request["quantity"]  # Might not exist!
    ...
```

## Rule 6: Protocol for Duck Typing

Use `Protocol` for structural subtyping instead of ABC for most cases.

### ✅ CORRECT

```python
from typing import Protocol

class DataSource(Protocol):
    """Protocol for data sources."""

    def get_data(self, symbol: str) -> dict[str, float]:
        """Get data for symbol."""
        ...

    def is_available(self) -> bool:
        """Check if available."""
        ...

# Any class with these methods matches the protocol
class APIDataSource:
    def get_data(self, symbol: str) -> dict[str, float]:
        return {"price": 100.0}

    def is_available(self) -> bool:
        return True

def use_source(source: DataSource) -> None:
    """Works with any DataSource implementation."""
    if source.is_available():
        data = source.get_data("AAPL")
```

### ❌ INCORRECT

```python
# ABC requires explicit inheritance
from abc import ABC, abstractmethod

class DataSource(ABC):
    @abstractmethod
    def get_data(self, symbol: str) -> dict:
        pass

# This won't work - no inheritance
class APIDataSource:
    def get_data(self, symbol: str) -> dict:
        return {"price": 100.0}
```

## Rule 7: Generic Classes with TypeVars

Use `TypeVar` for generic classes and functions.

### ✅ CORRECT

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Stack(Generic[T]):
    """Generic stack."""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def peek(self) -> T | None:
        return self._items[-1] if self._items else None

# Constrained TypeVar
class Comparable(Protocol):
    def __lt__(self, other: Any) -> bool: ...

CT = TypeVar('CT', bound=Comparable)

def find_max(items: list[CT]) -> CT:
    """Find maximum in list of comparable items."""
    if not items:
        raise ValueError("Empty list")
    max_item = items[0]
    for item in items[1:]:
        if item > max_item:
            max_item = item
    return max_item
```

## Rule 8: Callable Type Hints

Use proper `Callable` type hints for functions and callbacks.

### ✅ CORRECT

```python
from collections.abc import Callable, Awaitable
from typing import Concatenate, ParamSpec

P = ParamSpec('P')

# Simple callable
def apply(func: Callable[[int, int], int], x: int, y: int) -> int:
    return func(x, y)

# Async callable
async def process_async(
    callback: Callable[[str], Awaitable[dict[str, Any]]],
    data: str,
) -> dict[str, Any]:
    return await callback(data)

# Callable that captures parameters
def decorator(func: Callable[P, int]) -> Callable[P, int]:
    """Decorator preserving signature."""
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> int:
        print("Calling function")
        return func(*args, **kwargs)
    return wrapper
```

### ❌ INCORRECT

```python
# Untyped callback
def apply(func, x: int, y: int) -> int:
    return func(x, y)

# Using Any for callable
def process(callback: Any, data: str) -> Any:
    return callback(data)
```

## Rule 9: Self Types and Class Methods

Use proper type hints for methods returning `self` or class instances.

### ✅ CORRECT

```python
from typing import TypeVar, Self

T = TypeVar('T', bound='Builder')

class Builder:
    """Builder pattern with proper self types."""

    def set_name(self, name: str) -> Self:
        """Return self for chaining."""
        self.name = name  # type: ignore
        return self

    def set_age(self, age: int) -> Self:
        self.age = age  # type: ignore
        return self

    def build(self) -> Self:
        return self

# Generic factory
class Entity:
    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        """Factory method returning correct type."""
        instance = cls()
        for key, value in data.items():
            setattr(instance, key, value)
        return instance

class User(Entity):
    pass

# User.from_dict returns User, not Entity
user: User = User.from_dict({"name": "Alice"})
```

## Rule 10: Narrowing Types with Type Guards

Use type guards and assertions for proper type narrowing.

### ✅ CORRECT

```python
from typing import assert_type

def process(value: int | str | None) -> str:
    """Process value with proper type narrowing."""
    if value is None:
        return "null"
    elif isinstance(value, int):
        return f"int: {value}"
    else:
        # Type narrowed to str
        assert_type(value, str)
        return f"str: {value}"

# Custom type guard
from typing import TypeGuard

def is_dict_str_int(value: object) -> TypeGuard[dict[str, int]]:
    """Type guard for dict[str, int]."""
    return isinstance(value, dict) and all(
        isinstance(k, str) and isinstance(v, int)
        for k, v in value.items()
    )

def process_data(data: object) -> None:
    """Process data with type guard."""
    if is_dict_str_int(data):
        # Type narrowed to dict[str, int]
        for key, value in data.items():
            print(f"{key}: {value}")
```

## Rule 11: Type Ignore Requires Comment

Never use `# type: ignore` without explaining why.

### ✅ CORRECT

```python
# Justified type ignore with comment
import some_external_lib  # type: ignore[import]  # External lib has no stubs

def workaround_known_issue() -> None:
    result = some_external_lib.buggy_method()  # type: ignore[attr-defined]  # Known bug in library, tracked in issue #123
    ...
```

### ❌ INCORRECT

```python
import some_external_lib  # type: ignore  # WHY?

def workaround_known_issue() -> None:
    result = some_external_lib.buggy_method()  # type: ignore  # No explanation!
```

## Quick Command Reference

```bash
# Check types with mypy
mypy --strict .

# Check specific file
mypy --strict app/module.py

# Show error codes
mypy --strict --show-error-codes .

# Generate stub file
stubgen -m module_name -o stubs/
```
