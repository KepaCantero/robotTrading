# Integration Tests

This directory contains integration tests for the algoTrading system.

## Overview

Integration tests verify that multiple components work together correctly. Unlike unit tests that test individual components in isolation, integration tests test the complete flow through the system with real components.

## Test Categories

### 1. ComplianceEngine Integration Tests
**File:** `test_compliance_engine_full_flow.py`

Tests the complete trading workflow through ComplianceEngine:
- Pre-trade analysis with risk validation
- Trade execution via adapters
- Post-trade analysis with compliance checks
- Performance metrics calculation
- Integration with all subsystems

**Key Features:**
- Tests all adapters implement ITradeExecutor protocol
- Tests order management operations (place, cancel, modify)
- Tests error handling and edge cases
- Tests execution statistics and history tracking

### 2. ExecutionEngineAdapter Integration Tests
**File:** `test_execution_engine_integration.py`

Tests the backtesting execution flow through ExecutionEngineAdapter:
- Order placement via adapter
- Integration with PessimisticExecutionEngine
- Trade result handling
- Position tracking
- Commission calculation
- Slippage application

**Key Features:**
- Tests realistic execution with slippage (5 bps default)
- Tests t+1 execution delays
- Tests commission calculation
- Tests both BUY and SELL orders
- Tests order history and statistics

### 3. OrderManagerAdapter Integration Tests
**File:** `test_order_manager_integration.py`

Tests the live trading order management flow through OrderManagerAdapter:
- Order placement with risk validation
- Order status tracking
- Order modification
- Order cancellation
- Integration with OrderManager
- Integration with RiskGates

**Key Features:**
- Tests different order types (MARKET, LIMIT, STOP)
- Tests orders with stop loss and take profit
- Tests signal to order mapping
- Tests order manager integration

### 4. TradingBridgeAdapter Integration Tests
**File:** `test_trading_bridge_integration.py`

Tests the alert-to-trade pipeline through TradingBridgeAdapter:
- Alert signal mapping
- Trade execution from alerts
- Integration with TradingBridgeOrchestrator
- Execution tracking
- Error handling
- Bridge status monitoring

**Key Features:**
- Tests different signal types (LONG, SHORT)
- Tests different alert severity levels
- Tests multi-symbol execution
- Tests orchestrator integration

### 5. SpainTaxEngine Integration Tests
**File:** `test_spain_tax_engine_integration.py`

Tests tax calculation scenarios for Spanish traders:
- Capital gains tax calculation
- Dividend tax from multiple countries
- Modelo 720 threshold checks
- Tax planning scenarios
- Loss harvesting strategies

**Key Features:**
- Tests progressive tax brackets
- Tests EU dividend withholding (0%)
- Tests no wash sale rule advantage
- Tests 4-year loss carryforward

## Running Integration Tests

### Run All Integration Tests
```bash
# Run all integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ -v --cov=app/services/execution --cov=app/core/compliance_engine
```

### Run Specific Test File
```bash
# ComplianceEngine tests
pytest tests/integration/test_compliance_engine_full_flow.py -v

# ExecutionEngineAdapter tests
pytest tests/integration/test_execution_engine_integration.py -v

# OrderManagerAdapter tests
pytest tests/integration/test_order_manager_integration.py -v

# TradingBridgeAdapter tests
pytest tests/integration/test_trading_bridge_integration.py -v

# SpainTaxEngine tests
pytest tests/integration/test_spain_tax_engine_integration.py -v
```

### Run Specific Test
```bash
# Run specific test class
pytest tests/integration/test_compliance_engine_full_flow.py::TestPreTradeAnalysis -v

# Run specific test method
pytest tests/integration/test_compliance_engine_full_flow.py::TestPreTradeAnalysis::test_engine_initialization -v
```

### Run Tests Matching Pattern
```bash
# Run all tests related to compliance
pytest tests/integration/ -v -k "compliance"

# Run all tests related to execution
pytest tests/integration/ -v -k "execution"

# Run all tests related to order management
pytest tests/integration/ -v -k "order"

# Run all tests related to trading bridge
pytest tests/integration/ -v -k "trading_bridge or bridge"
```

## Test Requirements

Integration tests require:
- Python 3.9+
- pytest
- pytest-asyncio (for async tests)
- All project dependencies installed

### Installation
```bash
# Install dependencies
pip install pytest pytest-asyncio

# Or install from requirements.txt
pip install -r requirements.txt
```

## Test Fixtures

### Common Fixtures

#### `execution_adapter()`
Creates an ExecutionEngineAdapter instance for backtesting tests.

#### `order_adapter()`
Creates an OrderManagerAdapter instance for live trading tests.

#### `bridge_adapter()`
Creates a TradingBridgeAdapter instance for alert-to-trade tests.

#### `sample_signal()`
Creates a sample TradeSignal for testing.

#### `sample_alert()`
Creates a sample AlertEvent for testing.

## Test Patterns

### Async Tests
Most integration tests are async and use the `@pytest.mark.asyncio` decorator:

```python
@pytest.mark.asyncio
async def test_execute_order(adapter, signal):
    result = await adapter.execute_order(signal)
    assert result.success is True
```

### Fixture Injection
Fixtures are automatically injected into test functions:

```python
def test_adapter_initialization(execution_adapter):
    assert execution_adapter is not None
```

### Test Classes
Related tests are grouped into classes:

```python
class TestOrderExecution:
    @pytest.mark.asyncio
    async def test_buy_order(self, adapter, signal):
        ...

    @pytest.mark.asyncio
    async def test_sell_order(self, adapter, signal):
        ...
```

## Test Coverage

Current integration test coverage:

| Component | Test File | Coverage |
|-----------|-----------|----------|
| ComplianceEngine | test_compliance_engine_full_flow.py | Pre-trade analysis, adapter integration, protocol compliance |
| ExecutionEngineAdapter | test_execution_engine_integration.py | Order execution, slippage, commission, history |
| OrderManagerAdapter | test_order_manager_integration.py | Order placement, status tracking, different order types |
| TradingBridgeAdapter | test_trading_bridge_integration.py | Signal execution, alert mapping, orchestrator integration |
| SpainTaxEngine | test_spain_tax_engine_integration.py | Tax calculation, dividends, Modelo 720 |

## Notes

- Integration tests may take longer to run than unit tests
- Some tests may require external dependencies (mocked for testing)
- Use appropriate fixtures to set up test data
- Tests are designed to be independent and can run in any order
- Each test cleans up after itself to avoid side effects

## Adding New Integration Tests

When adding new integration tests:

1. Create a new test file in `tests/integration/`
2. Name it `test_<component>_integration.py`
3. Import necessary dependencies
4. Create fixtures for test setup
5. Write test classes and methods
6. Use `@pytest.mark.asyncio` for async tests
7. Update this README with the new test description

### Template

```python
"""
Integration test for <Component>.

Tests the <feature> flow through <Component>:
1. <Feature 1>
2. <Feature 2>
3. <Feature 3>
"""

import pytest
from decimal import Decimal

from app.services.<module> import <Component>


@pytest.fixture
def component():
    """Create <Component> instance."""
    return <Component>()


class Test<Component>:
    """Test <Component> integration."""

    @pytest.mark.asyncio
    async def test_feature(self, component):
        """Test <feature>."""
        result = await component.method()
        assert result.success is True
```

## Troubleshooting

### Tests Fail with Import Errors
- Ensure all dependencies are installed
- Check that the project root is in the Python path
- Run tests from the project root directory

### Tests Fail with Async Errors
- Ensure pytest-asyncio is installed
- Check that async tests have the `@pytest.mark.asyncio` decorator
- Verify async methods are properly awaited

### Tests Timeout
- Integration tests may take longer to run
- Increase timeout if needed: `pytest --timeout=300 tests/integration/`

## Contributing

When contributing integration tests:
1. Follow existing test patterns and conventions
2. Use descriptive test names
3. Group related tests in classes
4. Add docstrings explaining what is being tested
5. Update this README with new test descriptions
6. Ensure all tests pass before submitting
