# Comprehensive Testing Suite for algoTrading System

This directory contains the comprehensive testing suite for the algoTrading system, including unit tests, integration tests, and load tests.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared pytest fixtures
├── fixtures/                      # Test fixtures and factories
├── integration/                   # Integration tests
│   ├── test_position_monitor_comprehensive.py
│   ├── test_fifo_comprehensive.py
│   ├── test_emergency_close_comprehensive.py
│   └── services/                  # Service-specific integration tests
├── load/                          # Load and stress tests
│   ├── __init__.py
│   └── stress_tests.py
├── unit/                          # Unit tests
│   ├── services/
│   ├── strategies/
│   └── core/
└── README.md                      # This file
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- No external dependencies (database, APIs, etc.)
- Test individual functions and classes
- Run time: < 1 second per test

### Integration Tests (`@pytest.mark.integration`)
- Test interactions between components
- May use database, mock brokers
- Test end-to-end workflows
- Run time: 1-10 seconds per test

### Load Tests (`@pytest.mark.load`)
- Performance and stress tests
- Test with 1000+ positions
- Memory stability tests
- Run time: 10-60 seconds per test

### Critical Tests (`@pytest.mark.critical`)
- Must-pass tests for critical paths
- Position monitoring
- Emergency close
- FIFO tracking
- Run time: 1-5 seconds per test

### Slow Tests (`@pytest.mark.slow`)
- Tests that take > 10 seconds
- 24-hour stability simulations
- Large-scale tests
- Run time: 10-60 seconds per test

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run only load tests
python run_tests.py --load

# Run only critical tests
python run_tests.py --critical
```

### Advanced Usage

```bash
# Run with coverage report
python run_tests.py --coverage

# Run fast tests only (skip slow tests)
python run_tests.py --fast

# Stop on first failure
python run_tests.py --failfast

# Verbose output
python run_tests.py --verbose

# Run tests in parallel (requires pytest-xdist)
python run_tests.py --parallel 4

# Run specific test file
pytest tests/integration/test_position_monitor_comprehensive.py

# Run specific test
pytest tests/integration/test_position_monitor_comprehensive.py::TestPositionMonitorCriticalPaths::test_stop_loss_execution_long_position

# Run with marker
pytest -m "unit"
pytest -m "integration and not slow"
pytest -m "critical or load"
```

### Direct pytest Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Stop on first failure
pytest -x

# Run failed tests only
pytest --lf

# Run last failed tests then new tests
pytest --ff

# Run tests matching pattern
pytest -k "stop_loss"

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

## Test Coverage

Current coverage targets:
- **Overall**: 80% minimum
- **Critical components**: 90% minimum
- **Position monitor**: 95% minimum

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
async def mock_broker():
    """Mock broker for testing."""
    broker = MockBroker()
    yield broker
    # Cleanup

@pytest.fixture
async def db_session():
    """Database session for testing."""
    async with get_db_transaction() as session:
        yield session
        # Rollback transaction
```

## Writing New Tests

### Unit Test Example

```python
import pytest
from app.services.my_service import MyService

@pytest.mark.unit
class TestMyService:
    """Test MyService."""

    def test_calculate_value(self):
        """Test value calculation."""
        service = MyService()
        result = service.calculate(2, 3)
        assert result == 6
```

### Integration Test Example

```python
import pytest
from app.services.position_monitor import PositionMonitor

@pytest.mark.asyncio
@pytest.mark.integration
class TestPositionMonitor:
    """Test position monitor."""

    async def test_stop_loss_execution(self, mock_broker):
        """Test stop-loss execution."""
        monitor = PositionMonitor(mock_broker)
        await monitor.start()

        # Add position
        position = MonitoredPosition(...)
        await monitor.add_position(position)

        # Trigger stop-loss
        # ...

        assert monitor.get_position("test") is None
```

### Load Test Example

```python
import pytest
from app.services.position_monitor import PositionMonitor

@pytest.mark.asyncio
@pytest.mark.load
@pytest.mark.slow
class TestPositionMonitorLoad:
    """Load tests for position monitor."""

    async def test_monitor_1000_positions(self):
        """Test monitoring 1000 positions."""
        # Create 1000 positions
        # Monitor for stability
        # Assert performance metrics
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install -r requirements-dev.txt
      - run: python run_tests.py --coverage
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Tests Fail with Import Errors

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Ensure PYTHONPATH includes project root
export PYTHONPATH=/Users/kepa.cantero/Projects/algoTrading:$PYTHONPATH
```

### Database Tests Fail

```bash
# Ensure test database is configured
export DATABASE_URL=sqlite:///./test.db

# Or use PostgreSQL
export DATABASE_URL=postgresql://user:pass@localhost/test_db
```

### Tests Are Slow

```bash
# Skip slow tests
pytest -m "not slow"

# Run tests in parallel
pytest -n auto

# Run only unit tests
pytest -m "unit"
```

### Coverage Is Low

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View report to see what's not covered
open htmlcov/index.html

# Run coverage on specific module
pytest --cov=app.services.position_monitor
```

## Test Best Practices

1. **Test one thing**: Each test should verify one behavior
2. **Use descriptive names**: `test_stop_loss_triggers_when_price_drops`
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock external dependencies**: Don't depend on real APIs
5. **Clean up**: Use fixtures for setup/teardown
6. **Test edge cases**: Not just happy path
7. **Make tests independent**: Each test should work in isolation
8. **Use markers**: Categorize tests properly
9. **Keep tests fast**: Optimize slow tests
10. **Document complex tests**: Explain what's being tested

## Test Metrics

The test suite aims for:
- **Fast feedback**: Unit tests < 1 second
- **Good coverage**: 80%+ overall
- **Critical coverage**: 95%+ for critical paths
- **Stability**: Tests should be reliable and flake-free

## Support

For issues or questions about tests:
1. Check test logs for error messages
2. Review fixture setup in `conftest.py`
3. Verify environment configuration
4. Check import paths and dependencies
5. Review similar tests for examples

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
