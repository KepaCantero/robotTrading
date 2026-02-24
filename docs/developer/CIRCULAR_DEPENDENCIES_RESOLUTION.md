# Circular Dependencies Resolution - Refactoring Guide

## Overview

This document describes the refactoring performed to resolve circular dependencies in the AlgoTrading codebase.

## Problem Statement

Circular dependencies occur when two or more modules depend on each other, directly or indirectly. This causes:
- Import errors at module load time
- Difficulty in testing individual modules
- Tight coupling between components
- Maintenance challenges

## Files Refactored

### 1. `/app/core/protocols/__init__.py` (NEW)

**Purpose**: Define Protocol classes (interfaces) for dependency injection and type hints.

**Technique**: Protocol Pattern (PEP 544)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LoggerProtocol(Protocol):
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, message: str, *args: Any, **kwargs: Any) -> None: ...
```

**Benefits**:
- Enables type checking without runtime imports
- Supports structural subtyping (duck typing)
- No circular import issues

### 2. `/app/shared/exceptions/__init__.py`

**Before**:
```python
from app.exceptions.error_handler import (
    algotrading_exception_handler,
    generic_exception_handler,
    ...
)
from app.infrastructure.middleware.error_middleware import (
    ErrorHandlingMiddleware,
    ...
)
```

**After**:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.middleware.error_middleware import (
        ErrorHandlingMiddleware,
        ...
    )

def _get_error_handlers():
    from app.exceptions.error_handler import (
        algotrading_exception_handler,
        ...
    )
    return (algotrading_exception_handler, ...)
```

**Technique**: Lazy Imports + TYPE_CHECKING

**Benefits**:
- Imports only loaded when actually needed
- TYPE_CHECKING provides type hints without runtime import

### 3. `/app/infrastructure/middleware/error_middleware.py`

**Before**:
```python
from app.exceptions.error_handler import error_handler
from app.services.centralized_logging import LogLevel, LogService, centralized_logger
```

**After**:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.centralized_logging import LogLevel, LogService

def _get_centralized_logger():
    from app.services.centralized_logging import centralized_logger
    return centralized_logger

def _get_error_handler():
    from app.exceptions.error_handler import error_handler
    return error_handler
```

**Technique**: Lazy Imports in Functions

**Benefits**:
- Deferred import breaks circular dependency chain
- Logger and error handler loaded only when needed

### 4. `/app/engines/risk_engine/__init__.py`

**Before**:
```python
try:
    from app.domain.models.portfolio import Portfolio
except ImportError:
    class Portfolio:  # Placeholder
        pass

try:
    from app.domain.services.risk.portfolio import PortfolioRiskManager
except ImportError:
    class PortfolioRiskManager:  # Placeholder
        pass
```

**After**:
```python
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.domain.models.portfolio import Portfolio
    from app.domain.services.risk.portfolio import PortfolioRiskManager

@runtime_checkable
class PortfolioProtocol(Protocol):
    @property
    def portfolio_id(self) -> str: ...
    @property
    def capital(self) -> Any: ...

def _get_portfolio_class():
    from app.domain.models.portfolio import Portfolio
    return Portfolio

def _get_portfolio_risk_manager():
    from app.domain.services.risk.portfolio import PortfolioRiskManager
    return PortfolioRiskManager
```

**Technique**: Protocol + Lazy Loading + Property Pattern

**Benefits**:
- Type-safe interfaces without import coupling
- Lazy loading defers imports until needed
- Property pattern caches loaded instances

### 5. `/app/infrastructure/persistence/database/models/__init__.py`

**Before**:
```python
import sys
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "app.database.models_module", models_file
)
models_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_module)

User = models_module.User
APIKey = models_module.APIKey
```

**After**:
```python
from typing import TYPE_CHECKING, Protocol, runtime_checkable

@runtime_checkable
class UserModelProtocol(Protocol):
    id: int
    email: str
    username: str

_model_cache: dict = {}

def __getattr__(name: str):
    if name in {"User", "APIKey", "Portfolio", ...}:
        return _get_model(name)
    raise AttributeError(f"module has no attribute {name!r}")
```

**Technique**: `__getattr__` Module-Level Hook + Protocol Pattern

**Benefits**:
- Python 3.7+ `__getattr__` for lazy module-level imports
- Protocols provide type hints without importing models
- Caching prevents repeated imports

### 6. `/app/backtesting/core/executor.py` (Already Refactored)

**Technique**: In-Function Imports

```python
def execute(self, quotes, strategy, **kwargs):
    # Import here to avoid circular dependency
    from app.backtesting.engine import SimpleBacktester
    ...
```

## Techniques Summary

### 1. TYPE_CHECKING Pattern

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from module import Class

def func(param: "Class") -> None:  # String annotation or forward reference
    ...
```

**Use When**: You need type hints but no runtime access to the class.

### 2. Lazy/Deferred Imports

```python
def get_dependency():
    from expensive_module import Dependency
    return Dependency()

def use_dependency():
    dep = get_dependency()
    dep.do_something()
```

**Use When**: Two modules mutually depend on each other.

### 3. Protocol Pattern (PEP 544)

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyInterface(Protocol):
    def method(self) -> str: ...

def accepts_interface(obj: MyInterface) -> None:
    # Works with any object that has method()
    result = obj.method()
```

**Use When**: You need duck typing with type safety.

### 4. `__getattr__` Module Hook

```python
def __getattr__(name: str):
    if name == "MyClass":
        from my_module import MyClass
        return MyClass
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

**Use When**: You need lazy module-level attribute access.

### 5. Property Pattern for Lazy Loading

```python
class MyClass:
    def __init__(self):
        self._heavy_dependency = None

    @property
    def heavy_dependency(self):
        if self._heavy_dependency is None:
            from heavy_module import HeavyDependency
            self._heavy_dependency = HeavyDependency()
        return self._heavy_dependency
```

**Use When**: Instance-level lazy loading with caching.

## Best Practices

1. **Prefer TYPE_CHECKING for Type Hints**: Use `if TYPE_CHECKING:` blocks for imports only needed for type annotations.

2. **Use Protocols for Interfaces**: Define Protocol classes in a central location (`/app/core/protocols/`) for shared interfaces.

3. **Lazy Load Heavy Dependencies**: Use function-level imports or properties for expensive imports.

4. **Avoid Placeholder Classes**: Use Protocols instead of placeholder/stub classes.

5. **Document Circular Dependencies**: Add comments explaining why lazy imports are used.

6. **Consider Dependency Injection**: For complex dependencies, use DI containers.

## Verification

To verify that circular dependencies are resolved:

```bash
# Check for import cycles
python -c "import app.main"

# Run import linter
lint-imports

# Check specific module
python -c "from app.engines.risk_engine import RiskEngine"
python -c "from app.infrastructure.middleware.error_middleware import ErrorHandlingMiddleware"
python -c "from app.shared.exceptions import setup_error_handling"
```

## Files Created/Modified

### Created
- `/app/core/protocols/__init__.py` - Protocol definitions

### Modified
- `/app/shared/exceptions/__init__.py` - Lazy imports for error handlers
- `/app/infrastructure/middleware/error_middleware.py` - Lazy imports for logging
- `/app/engines/risk_engine/__init__.py` - Protocol + lazy loading
- `/app/infrastructure/persistence/database/models/__init__.py` - `__getattr__` pattern

## Future Improvements

1. **Centralize Protocols**: Move all Protocol definitions to `/app/core/protocols/`

2. **Add Import Tests**: Create automated tests to detect circular imports

3. **Use Dependency Injection Container**: Consider using a DI framework for complex dependency graphs

4. **Refactor Remaining Files**: Continue applying these patterns to other files with circular dependencies

---

*Document created: 2026-02-22*
*Author: Claude Code Assistant*
