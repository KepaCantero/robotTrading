# Live Trading CLI Implementation

This task creates the command-line interface for live trading operations.

## Overview

Create a comprehensive CLI that integrates with:
- **ComplianceEngine**: Main coordinator for all trading operations
- **TradingBridgeOrchestrator**: Alert monitoring and execution
- **OrderManager**: Order lifecycle management
- **RiskGates**: Pre-trade risk validation

## Files to Create

1. **scripts/start_live_trading.py** - Main CLI with commands:
   - `start` - Start live trading
   - `stop` - Stop trading
   - `validate` - Validate config
   - `test-broker` - Test connection
   - `risk-status` - Check risk
   - `positions` - Show positions
   - `order` - Place manual order

2. **scripts/validate_config.py** - Standalone config validation

3. **scripts/validate_broker_connection.py** - Standalone broker test

## Key Requirements

- Use `asyncio` for async operations
- Integrate with ComplianceEngine for all operations
- Check kill switch before starting
- Use RiskGates for all orders
- Provide clear error messages
- Log all operations
- Handle keyboard interrupts gracefully

## Testing

Create unit tests for CLI validation functions.

## Success Criteria

- All scripts compile without errors
- CLI --help shows all commands
- validate_config.py checks all components
- validate_broker_connection.py tests broker
- Tests pass
