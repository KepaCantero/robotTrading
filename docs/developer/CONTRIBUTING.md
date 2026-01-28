# Contributing Guidelines

## How to Contribute

We welcome contributions from the community! This document provides guidelines and instructions for contributing to the AlgoTrading project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Documentation Standards](#documentation-standards)
7. [Pull Request Process](#pull-request-process)
8. [Issue Reporting](#issue-reporting)

---

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as contributors and maintainers pledge to make participation in our project and our community a harassment-free experience for everyone.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes**:
- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, or personal/political attacks
- Public or private harassment
- Publishing others' private information without permission
- Other unethical or unprofessional conduct

### Responsibility

Project maintainers are responsible for clarifying the standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Familiarity with the project

### Initial Setup

1. **Fork the repository**:
   ```bash
   // Click "Fork" on GitHub
   ```

2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/algoTrading.git
   cd algoTrading
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-owner/algoTrading.git
   ```

4. **Set up development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **Run tests to verify setup**:
   ```bash
   pytest
   ```

---

## Development Workflow

### 1. Create a Branch

Always create a branch for your work:

```bash
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
# or
git checkout -b docs/your-documentation-update
```

**Branch naming conventions**:
- `feature/` - New features
- `fix/` - Bug fixes
- `hotfix/` - Urgent production fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

### 2. Make Changes

**Write clean, well-documented code** (see [Coding Standards](#coding-standards))

**Commit frequently** with meaningful messages:

```bash
git add file_name.py
git commit -m "Add momentum strategy implementation"
```

**Commit message format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Example**:
```
feat(momentum): add dynamic parameter adjustment

- Implement adaptive lookback period based on volatility
- Add parameter validation
- Update unit tests

Closes #123
```

### 3. Sync with Upstream

Keep your branch up to date:

```bash
git fetch upstream
git rebase upstream/main
```

### 4. Write Tests

Ensure your changes are well-tested (see [Testing Guidelines](#testing-guidelines))

```bash
# Run specific tests
pytest tests/test_your_feature.py

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### 5. Update Documentation

Update relevant documentation (see [Documentation Standards](#documentation-standards))

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Create Pull Request

See [Pull Request Process](#pull-request-process)

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

#### Indentation and Formatting

```python
# Use 4 spaces for indentation
def my_function(param1, param2):
    """Function docstring."""
    if param1 > param2:
        return param1
    return param2

# Maximum line length: 100 characters
# (but prefer 88 for better readability with black)
```

#### Imports

```python
# 1. Standard library imports
import os
import sys
from typing import List, Dict

# 2. Third-party imports
import pandas as pd
from fastapi import FastAPI

# 3. Local imports
from app.models.portfolio import Portfolio
from app.services.trading import TradingService
```

#### Naming Conventions

```python
# Variables and functions: snake_case
my_variable = 1
def calculate_metrics():
    pass

# Classes: PascalCase
class BacktestEngine:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_POSITION_SIZE = 0.05
DEFAULT_LOOKBACK = 20

# Private methods/variables: leading underscore
def _internal_method(self):
    pass
```

### Docstrings

We use **Google-style docstrings**:

```python
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate the Sharpe ratio for a return series.

    The Sharpe ratio measures the excess return per unit of risk.
    Higher values indicate better risk-adjusted performance.

    Args:
        returns: Series of periodic returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
        periods_per_year: Number of periods per year (default: 252 for daily)

    Returns:
        Sharpe ratio as a float

    Raises:
        ValueError: If returns series is empty or contains invalid values

    Examples:
        >>> returns = pd.Series([0.01, 0.02, -0.01, 0.03])
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe ratio: {sharpe:.2f}")
    """
    if returns.empty:
        raise ValueError("Returns series cannot be empty")

    excess_returns = returns - risk_free_rate / periods_per_year
    return excess_returns.mean() / excess_returns.std() * (periods_per_year ** 0.5)
```

### Type Hints

Always use type hints for function signatures:

```python
from typing import List, Dict, Optional

def generate_signals(
    data: pd.DataFrame,
    parameters: Dict[str, float],
    filters: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Generate trading signals from market data.

    Args:
        data: Historical market data
        parameters: Strategy parameters
        filters: Optional list of filters to apply

    Returns:
        List of trading signals
    """
    pass
```

### Error Handling

```python
# Specific exception handling
try:
    result = divide(a, b)
except ZeroDivisionError as e:
    logger.error(f"Division by zero: {e}")
    raise ValueError("Cannot divide by zero") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# Use custom exceptions
class StrategyValidationError(Exception):
    """Raised when strategy validation fails."""
    pass

# Validate inputs early
def calculate_position_size(capital: float, risk_percent: float) -> float:
    if capital < 0:
        raise ValueError("Capital cannot be negative")
    if not 0 <= risk_percent <= 1:
        raise ValueError("Risk percent must be between 0 and 1")
    return capital * risk_percent
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed diagnostic information")
logger.info("General informational message")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue")

# Structured logging with context
logger.info(
    "Trade executed",
    extra={
        "symbol": "AAPL",
        "quantity": 100,
        "price": 150.00,
        "strategy": "momentum"
    }
)
```

### Code Organization

```python
# File structure
"""
Module docstring describing purpose.
"""

# 1. Standard library imports
import os
from typing import List, Dict

# 2. Third-party imports
import pandas as pd
from fastapi import FastAPI

# 3. Local imports
from app.models.portfolio import Portfolio
from app.services.trading import TradingService

# 4. Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# 5. Global variables
logger = logging.getLogger(__name__)

# 6. Classes
class MyClass:
    """Class docstring."""

# 7. Functions
def my_function():
    """Function docstring."""
    pass
```

### Performance Considerations

```python
# Use vectorized operations with pandas/numpy
# Bad:
result = []
for i in range(len(df)):
    result.append(df['close'].iloc[i] * df['volume'].iloc[i])

# Good:
result = df['close'] * df['volume']

# Use list comprehensions instead of loops
# Bad:
squares = []
for i in range(100):
    squares.append(i ** 2)

# Good:
squares = [i ** 2 for i in range(100)]

# Use generators for large datasets
# Bad (loads all into memory):
sum([i * 2 for i in range(1000000)])

# Good (lazy evaluation):
sum(i * 2 for i in range(1000000))
```

---

## Testing Guidelines

### Test Structure

```python
# tests/test_backtesting.py
import pytest
from app.backtesting.engine import BacktestEngine

class TestBacktestEngine:
    """Test suite for BacktestEngine."""

    @pytest.fixture
    def sample_data(self):
        """Fixture providing sample data for testing."""
        return pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100),
            'close': np.random.randn(100).cumsum() + 100
        })

    @pytest.fixture
    def engine(self):
        """Fixture providing a BacktestEngine instance."""
        return BacktestEngine(initial_capital=100000)

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.initial_capital == 100000
        assert engine.current_capital == 100000

    def test_run_backtest(self, engine, sample_data):
        """Test running a backtest."""
        results = engine.run(sample_data)
        assert 'total_return' in results
        assert 'sharpe_ratio' in results

    @pytest.mark.parametrize("capital,expected", [
        (100000, True),
        (0, False),
        (-1000, False),
    ])
    def test_capital_validation(self, capital, expected):
        """Test capital validation."""
        if expected:
            engine = BacktestEngine(initial_capital=capital)
            assert engine.initial_capital == capital
        else:
            with pytest.raises(ValueError):
                BacktestEngine(initial_capital=capital)
```

### Test Coverage

We aim for **80%+ test coverage**. Check your coverage:

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Testing Best Practices

1. **Test behavior, not implementation**
2. **One assertion per test** (when possible)
3. **Use fixtures for setup**
4. **Mock external dependencies**
5. **Test edge cases and error conditions**

---

## Documentation Standards

### Code Documentation

Every function, class, and module must have a docstring:

```python
def calculate_volatility(returns: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate rolling volatility for returns.

    Uses the standard deviation of returns over a specified window.

    Args:
        returns: DataFrame containing return data
        window: Rolling window size (default: 20)

    Returns:
        Series of volatility values

    Raises:
        ValueError: If window is less than 2 or larger than data length

    Examples:
        >>> returns = pd.DataFrame({'return': [0.01, 0.02, -0.01]})
        >>> volatility = calculate_volatility(returns, window=2)
    """
```

### README Documentation

Update README.md when:
- Adding new features
- Changing configuration
- Updating dependencies
- Modifying setup process

### API Documentation

Use OpenAPI/Swagger annotations:

```python
from fastapi import APIRouter, Query
from typing import Optional

@router.get("/signals")
async def get_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum results")
) -> List[Signal]:
    """
    Retrieve trading signals.

    Args:
        symbol: Optional symbol filter
        limit: Maximum number of signals to return (1-1000)

    Returns:
        List of trading signals
    """
    pass
```

---

## Pull Request Process

### Before Submitting

1. **Ensure all tests pass**:
   ```bash
   pytest
   ```

2. **Run code formatting**:
   ```bash
   black app/ tests/
   isort app/ tests/
   ```

3. **Check linting**:
   ```bash
   flake8 app/ tests/
   ```

4. **Update documentation**:
   - Docstrings for new code
   - README for new features
   - API docs for new endpoints

### Creating the Pull Request

1. **Go to GitHub** and click "New Pull Request"
2. **Provide a clear title**:
   ```
   feat(momentum): Add dynamic parameter adjustment
   ```
3. **Fill out the PR template**:
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update

   ## Testing
   - [ ] Tests added/updated
   - [ ] All tests pass

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No new warnings generated
   ```

4. **Link related issues**:
   ```markdown
   Closes #123
   Related to #456
   ```

### After Submitting

- **Respond to review comments** promptly
- **Make requested changes** in separate commits
- **Keep the conversation** professional and constructive

### Merge Process

Maintainers will:
1. Review your PR
2. Request changes if needed
3. Approve when ready
4. Merge your changes
5. Thank you for your contribution! 🎉

---

## Issue Reporting

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check the documentation** for solutions
3. **Try the latest version** to see if the issue is fixed

### Creating a Good Issue

Use the issue template:

```markdown
## Bug Report
**Clear description of the bug**

### Steps to Reproduce
1. Step one
2. Step two
3. See error

### Expected Behavior
What should happen

### Actual Behavior
What actually happens

### Environment
- OS: [e.g. Ubuntu 20.04]
- Python version: [e.g. 3.9]
- AlgoTrading version: [e.g. 1.0.0]

### Logs/Error Messages
```
Paste error messages here
```

## Feature Request
**Clear description of feature**

### Problem Statement
What problem does this solve?

### Proposed Solution
How should it work?

### Alternatives
What other approaches did you consider?

### Additional Context
Any other relevant information
```

### Issue Labels

- `bug`: Bug reports
- `enhancement`: New features
- `documentation`: Documentation issues
- `good first issue`: Good for newcomers
- `help wanted`: Community help needed
- `priority: high`: High priority issues

---

## Community Guidelines

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: General questions, ideas
- **Discord**: Real-time chat (invite link in README)

### Getting Help

1. **Check documentation first**
2. **Search existing issues/discussions**
3. **Ask in GitHub Discussions**
4. **Join Discord** for real-time help

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to AlgoTrading! 🚀
