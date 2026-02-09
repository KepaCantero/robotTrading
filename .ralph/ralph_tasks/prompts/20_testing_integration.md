# Task 20: Testing Integration - Implementation Guide

## Overview

Create comprehensive integration tests for the core system components that were built in previous tasks. This ensures that all the integration adapters work correctly together and that the system functions as a cohesive whole.

## Context

You are working on an algorithmic trading system built in Python. The system has these core components that need integration testing:

1. **ComplianceEngine** - The central coordinator that validates and executes trades
2. **ExecutionEngineAdapter** - Adapter for backtesting execution
3. **OrderManagerAdapter** - Adapter for live trading order management
4. **TradingBridgeAdapter** - Adapter for alert-to-trade pipeline
5. **SpainTaxEngine** - Tax calculations for Spanish traders

## Dependencies

All dependencies are SATISFIED:
- Task 09 (ComplianceEngine): COMPLETED
- Task 10 (ExecutionEngineAdapter): COMPLETED
- Task 11 (OrderManagerAdapter): COMPLETED
- Task 12 (TradingBridgeAdapter): COMPLETED
- Task 02 (SpainTaxEngine): COMPLETED

## Your Task

Create integration tests following this workflow:

### Step 1: Review Existing Test Patterns

First, look at existing integration tests in `tests/integration/` to understand the testing patterns used in this project.

```bash
ls -la tests/integration/
cat tests/integration/test_spain_tax_engine_integration.py
```

### Step 2: Create the Integration Test Files

Create the following integration test files:

1. `tests/integration/test_compliance_engine_full_flow.py`
   - Test pre-trade analysis with risk validation
   - Test trade execution flow
   - Test post-trade analysis
   - Test compliance checks (PDT, wash sales, pattern day trader)
   - Test risk gate integration
   - Test performance metrics

2. `tests/integration/test_execution_engine_integration.py`
   - Test order placement via adapter
   - Test integration with PessimisticExecutionEngine
   - Test trade result handling
   - Test order cancellation
   - Test open orders retrieval
   - Test commission calculation

3. `tests/integration/test_order_manager_integration.py`
   - Test order placement with risk validation
   - Test order status tracking
   - Test order modification
   - Test order cancellation
   - Test stop loss and take profit

4. `tests/integration/test_trading_bridge_integration.py`
   - Test alert-to-signal mapping
   - Test order execution from alerts
   - Test bridge status tracking
   - Test execution history

5. Review and ensure `test_spain_tax_engine_integration.py` is comprehensive

### Step 3: Follow the Implementation Guide

The YAML file contains detailed implementation guidance for each test file. Follow those specifications carefully.

### Step 4: Test Requirements

- Use pytest fixtures for setup
- Use async/await for async methods
- Include proper error handling tests
- Mock external dependencies (broker connections)
- Use proper assertions and validation

### Step 5: Run and Validate

After creating each test file:
1. Validate syntax: `python -m py_compile <test_file>`
2. Run the tests: `pytest <test_file> -v`
3. Fix any issues that arise

## Key Points

1. **Integration tests verify that components work together correctly**
2. **They are different from unit tests which test individual components in isolation**
3. **Focus on the interactions between components, not internal logic**
4. **Use real components (not mocks) unless testing external dependencies**
5. **Test both happy paths and error scenarios**

## Success Criteria

- All integration test files are created
- Tests compile successfully
- Tests pass or are properly marked with expected failures
- Coverage includes:
  - Pre-trade analysis
  - Order execution
  - Order management
  - Alert-to-trade pipeline
  - Tax calculations
- README documentation is created

## Completion

When all tests are created and passing:
1. Update the checkpoint file
2. Update the scratchpad
3. Mark the task as complete
