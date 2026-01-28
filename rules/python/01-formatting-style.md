# Python Formatting & Style Rules

Code formatting and style standards using Black, Isort, Autoflake, Flake8, and Ruff.

## Tool Configuration

### Black (Formatter)

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
```

### Isort (Import Organizer)

```toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### Ruff (Ultra-fast Linter)

```toml
[tool.ruff]
line-length = 100
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "C",   # flake8-comprehensions
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
]
ignore = []
```

### Flake8 (Classic Linter)

```ini
# .flake8
[flake8]
max-line-length = 100
max-complexity = 10
extend-ignore = E203, W503
exclude = .git,__pycache__,docs/source/conf.py,old,build,dist
```

## Rule 1: Line Length - Maximum 100 Characters

Black enforces 100 character line length. Break long lines appropriately.

### ✅ CORRECT

```python
# Long string using parentheses
long_message = (
    "This is a very long message that needs to be broken "
    "into multiple lines for readability"
)

# Long function call with keyword arguments
result = some_function(
    param1="value1",
    param2="value2",
    param3="value3",
)

# Long function definition with type hints
def process_large_dataset(
    data: list[dict[str, Any]],
    batch_size: int = 1000,
    shuffle: bool = True,
) -> dict[str, float]:
    ...
```

### ❌ INCORRECT

```python
# Line too long (> 100 chars)
long_message = "This is a very long message that should be broken into multiple lines for readability according to Black standards"

result = some_function(param1="value1", param2="value2", param3="value3", param4="value4", param5="value5")
```

## Rule 2: Import Organization - Standard Library, Third Party, Local

Imports must be grouped: 1) standard library, 2) third party, 3) local imports.

### ✅ CORRECT

```python
# Standard library
import os
from pathlib import Path
from typing import Optional

# Third party
import numpy as np
import pandas as pd
from pydantic import BaseModel

# Local
from app.core.models import InputProfile
from app.services import TradingService
```

### ❌ INCORRECT

```python
# Mixed imports (wrong order)
from app.core.models import InputProfile
import os
import pandas as pd
from pathlib import Path
from app.services import TradingService
```

## Rule 3: No Unused Imports

Remove all unused imports. Use Autoflake or Ruff to detect.

### ✅ CORRECT

```python
import pandas as pd  # Used

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna()
```

### ❌ INCORRECT

```python
import numpy as np  # Unused - remove it!
import pandas as pd

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna()
```

## Rule 4: Use F-strings for String Formatting

Use f-strings instead of `.format()` or `%` formatting.

### ✅ CORRECT

```python
name = "Alice"
age = 30

# Simple f-string
message = f"Hello, {name}!"

# With expression
message = f"{name} is {age} years old"

# With format spec
price = 1234.5678
formatted = f"Price: ${price:,.2f}"
```

### ❌ INCORRECT

```python
# Old style formatting
message = "Hello, %s!" % name
message = "Hello, {}!".format(name)
```

## Rule 5: Use Spaces Not Tabs for Indentation

Black enforces 4 spaces for indentation. No tabs.

### ✅ CORRECT

```python
def example():
    if condition:
        do_something()
        if another:
            do_more()
```

### ❌ INCORRECT

```python
def example():
	if condition:		# Tabs - wrong!
		do_something()
```

## Rule 6: Trailing Commas in Multi-line Collections

Use trailing commas in multi-line lists, tuples, dicts, and function calls.

### ✅ CORRECT

```python
# List with trailing comma
items = [
    "first",
    "second",
    "third",
]

# Dict with trailing comma
config = {
    "host": "localhost",
    "port": 8080,
    "debug": True,
}

# Function call with trailing comma
result = calculate(
    x=10,
    y=20,
    z=30,
)
```

### ❌ INCORRECT

```python
# Missing trailing commas
items = [
    "first",
    "second",
    "third"
]

config = {
    "host": "localhost",
    "port": 8080,
    "debug": True
}
```

## Rule 7: Blank Lines Between Top-level Definitions

Use 2 blank lines before top-level functions/classes. 1 blank line before methods.

### ✅ CORRECT

```python
def function_one():
    pass


def function_two():
    pass


class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass
```

### ❌ INCORRECT

```python
def function_one():
    pass
def function_two():
    pass

class MyClass:
    def method_one(self):
        pass
    def method_two(self):
        pass
```

## Rule 8: Quotes - Prefer Double Quotes

Black prefers double quotes for strings. Single quotes only if string contains double quotes.

### ✅ CORRECT

```python
# Double quotes (default)
message = "Hello, World!"

# Single quotes when string contains double quotes
quote = 'He said "Hello" to me'

# Triple double quotes for docstrings
def function():
    """This is a docstring."""
    pass
```

### ❌ INCORRECT

```python
# Inconsistent quote style
message = 'Hello, World!'
quote = "He said \"Hello\" to me"
```

## Rule 9: Whitespace Around Operators

Use spaces around operators except for keyword arguments with default values.

### ✅ CORRECT

```python
# Binary operators with spaces
x = 5 + 10
result = (a + b) * (c - d)

# Keyword arguments without spaces
def function(default: int = 10, optional: str = "value"):
    pass

# Slice notation without spaces
subset = data[1:10]
step = data[::2]
```

### ❌ INCORRECT

```python
# Missing spaces around operators
x = 5+10
result = (a+b)*(c-d)

# Unnecessary spaces in slices
subset = data[1 : 10]
step = data[ : : 2]

# Extra spaces in defaults (Black will fix)
def function(default: int = 10, optional: str = "value"):  # Black: no spaces
```

## Rule 10: No Mutable Default Arguments

Never use mutable default arguments. Use `None` and initialize inside function.

### ✅ CORRECT

```python
from typing import Optional

def append_to_list(value: int, target: Optional[list[int]] = None) -> list[int]:
    if target is None:
        target = []
    target.append(value)
    return target

# With type hints (Python 3.10+)
def process_data(data: dict[str, int] | None = None) -> dict[str, int]:
    if data is None:
        data = {}
    return data
```

### ❌ INCORRECT

```python
# Mutable default - creates shared state!
def append_to_list(value: int, target: list[int] = []) -> list[int]:
    target.append(value)
    return target

# Mutable default - shared dict!
def process_data(data: dict[str, int] = {}) -> dict[str, int]:
    return data
```

## Rule 11: Naming Conventions

Follow PEP 8 naming conventions.

### ✅ CORRECT

```python
# Modules: lowercase_with_underscores
# my_module.py

# Packages: lowercase
# mypackage/

# Classes: CapWords
class TradingEngine:
    pass

class HTTPClient:
    pass

# Functions/Variables: lowercase_with_underscores
def calculate_profit() -> float:
    pass

user_name = "Alice"
total_count = 100

# Constants: UPPER_CASE_WITH_UNDERSCORES
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private: _leading_underscore
class MyClass:
    def _internal_method(self):
        pass
```

### ❌ INCORRECT

```python
# Wrong: class names should be CapWords
class tradingEngine:
    pass

# Wrong: functions should be lowercase
def CalculateProfit():
    pass

# Wrong: constants should be uppercase
maxRetries = 3
```

## Rule 12: Use Context Managers for Resource Management

Always use context managers for file operations, locks, connections, etc.

### ✅ CORRECT

```python
# File operations
def read_file(path: Path) -> str:
    with path.open("r") as f:
        return f.read()

# Lock management
from threading import Lock

lock = Lock()

def protected_section():
    with lock:
        # Critical section
        pass

# Database connections
from contextlib import contextmanager

@contextmanager
def db_connection():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### ❌ INCORRECT

```python
# Manual file handling - error prone!
def read_file(path: Path) -> str:
    f = path.open("r")
    data = f.read()
    f.close()  # Never reached if exception!
    return data
```

## Quick Command Reference

```bash
# Format code
black .

# Organize imports
isort .

# Remove unused imports
autoflake --remove-all-unused-imports --in-place .

# Check linting
flake8 . --max-complexity=10
ruff check .

# Fix linting issues automatically
ruff check . --fix
```
