# Requirements: services/live_trading/broker_adapters/ib_adapter.py

## Source File Analysis
- **File Path**: `app/services/live_trading/broker_adapters/ib_adapter.py`
- **Lines of Code**: 827
- **Status**: Analysis Complete - PASSED
- **Audit Date**: 2026-02-07

## Purpose
Provides a complete interface to Interactive Brokers TWS/IB Gateway for live trading:
- Async connection management with auto-reconnect
- Real-time market data streaming
- Order placement (Market, Limit, Stop, Stop-Limit)
- Position tracking
- Account summary
- Error handling and recovery

## Dependencies

### Internal
- `app.core.reconnection_manager.ReconnectionManager, ReconnectionConfig` - Reconnection logic for 24/7 operation
- `app.core.trading_validators.TradingValidator` - CRITICAL: Validates position sizes and stop-loss

### External
- `asyncio` - Async operations
- `logging` - Standard Python logging
- `os` - Environment variable loading
- `datetime, timedelta` - Timestamps and time deltas
- `decimal.Decimal` - Precise financial calculations
- `typing` - Type hints (Any, Callable, Dict, List, Optional)
- `ib_insync` - IB API wrapper (IB, LimitOrder, MarketOrder, StopOrder, util, Contract, Ticker)
- `requests.exceptions` - HTTPError, RequestException for network errors

## Classes/Functions

### Custom Exceptions
1. **BrokerError** - Base exception for broker errors
2. **ConfigurationError** - Exception for configuration errors

### Main Class: IBConnection
1. **__init__()** - Initialize with config from env or dict
2. **connect()** - Establish connection to IB
3. **disconnect()** - Disconnect gracefully
4. **get_market_data()** - Get market data with caching
5. **place_order()** - Place order with validation
6. **cancel_order()** - Cancel an order
7. **get_positions()** - Get current positions
8. **get_account_summary()** - Get account summary
9. **subscribe_market_data()** - Subscribe to real-time updates
10. **unsubscribe_market_data()** - Unsubscribe from updates
11. **get_connection_stats()** - Get reconnection statistics

### Helper Methods
1. **_load_config_from_env()** - Load configuration from environment variables
2. **_on_error()** - Handle errors from TWS/IB Gateway
3. **_reconnect_with_backoff()** - Exponential backoff reconnection
4. **_reconnect()** - Attempt to reconnect
5. **_verify_account_access()** - Verify account access
6. **_get_contract()** - Get or create IB contract
7. **__del__()** - Cleanup on deletion

### High-Level Adapter: IBAdapter
1. **connect()** - Connect to IB
2. **disconnect()** - Disconnect from IB
3. **is_connected()** - Check connection status
4. **get_market_data()** - Get market data for symbol
5. **place_order()** - Place an order
6. **cancel_order()** - Cancel an order
7. **get_positions()** - Get current positions
8. **get_account_summary()** - Get account summary
9. **subscribe_market_data()** - Subscribe to updates
10. **unsubscribe_market_data()** - Unsubscribe from updates

### Singleton
1. **get_ib_adapter()** - Get singleton IB adapter instance

## Business Logic

### CRITICAL: Trading Safety (TradingValidator Integration)
- **Position size validation**: Validates position <= 25% of capital
- **Stop-loss validation**: Validates stop-loss price vs entry price
- **Pre-trade validation**: All validation BEFORE order execution
- **Estimated price from market data**: Uses current market data for position value calculation

### Reconnection Logic (ReconnectionManager)
- Configurable max attempts (default: 10)
- Exponential backoff with jitter
- Callbacks for on_attempt, on_success, on_failure
- Alert threshold (default: 3 attempts)
- Supports 24/7 operation

### Market Data Caching
- 5-second validity period for cached data
- Invalidates cache on subscription
- Efficient for repeated queries

### Order Placement Flow
1. Check connection (auto-connect if needed)
2. Validate parameters (side, quantity)
3. CRITICAL: Get available capital and validate position size
4. CRITICAL: Validate stop-loss if provided (warn if missing)
5. Get market data for price validation
6. Validate stop/limit prices vs current market
7. Get contract for symbol
8. Create order (Market/Limit/Stop)
9. Place order via IB
10. Return result with fill details

## Data Models

### Position Dict
```python
{
    'symbol': str,
    'position': float,
    'avg_cost': float,
    'market_value': float,
    'unrealized_pnl': float,
    'realized_pnl': float,
    'currency': str,
}
```

### Account Summary Dict
```python
{
    'tag': {
        'value': float,
        'currency': str,
    },
    'timestamp': str,
    'account_id': str,
}
```

### Market Data Dict
```python
{
    'symbol': str,
    'bid': float,
    'ask': float,
    'last': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': int,
    'timestamp': datetime,
}
```

### Order Result Dict
```python
{
    'order_id': int,
    'status': str,  # 'SUBMITTED' or 'FILLED'
    'fill_price': float,  # if filled
    'filled_quantity': float,  # if filled
    'side': str,
    'symbol': str,
    'timestamp': str,
}
```

## API Contracts

### connect()
```python
async def connect(self) -> bool
```

### place_order()
```python
async def place_order(
    symbol: str,
    side: str,  # 'BUY' or 'SELL'
    quantity: float,
    order_type: str = 'MKT',
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    **contract_kwargs,
) -> Dict[str, Any]
```

### get_market_data()
```python
async def get_market_data(
    symbol: str,
    **contract_kwargs,
) -> Dict[str, Any]
```

## Error Handling

### Exception Handling
- **asyncio.TimeoutError**: Caught in connect, account_summary
- **ConnectionError, OSError**: Caught in connect, disconnect
- **ValueError, TypeError, KeyError, AttributeError, IndexError**: Caught in data operations

### Error Recovery
1. **Reconnection**: Exponential backoff with ReconnectionManager
2. **Graceful degradation**: Returns empty dict on market data failure
3. **Auto-connect**: Attempts to connect if not connected

### Input Validation
- Side must be 'BUY' or 'SELL'
- Quantity must be positive
- Price required for LMT orders
- Stop price required for STP orders
- Position size validation via TradingValidator
- Stop-loss validation via TradingValidator
- Price validation vs current market (prevents invalid orders)

## Performance Considerations

### Async Operations
- All I/O operations are async
- Non-blocking connection and order placement

### Caching
- 5-second cache for market data
- Subscription-based real-time updates
- Efficient contract caching

### Scalability
- Singleton pattern for resource efficiency
- Connection pooling via ib_insync
- Efficient market data subscriptions

## Testing Strategy

### Unit Tests Needed
1. **Connection management**: Test connect/disconnect/reconnect
2. **Configuration**: Test env loading and default config
3. **Order placement**: Test all order types and validation
4. **Market data**: Test caching and subscriptions
5. **TradingValidator integration**: Test position size and stop-loss validation

### Integration Tests Needed
1. **IB Gateway integration**: Test against paper trading
2. **Market data streaming**: Test real-time subscriptions
3. **Reconnection logic**: Test connection failures and recovery
4. **Order execution**: Test order placement and fills

## BASE_RULES Compliance

### Security (P0 - CRITICAL)
- ✅ SEC-001: No hardcoded secrets (uses env vars)
- ✅ SEC-002: Environment validation (via _load_config_from_env)
- ✅ SEC-007: Input validation via TradingValidator
- ✅ TradingValidator validates position sizes BEFORE execution
- ✅ TradingValidator validates stop-loss prices
- ⚠️ Warning logged for orders without stop-loss

### Async Patterns
- ✅ ASYNC-001: All async functions properly marked
- ✅ ASYNC-002: Uses asyncio.sleep for delays
- ✅ Proper error handling in async contexts

### Architecture
- ✅ ARCH-001: Two-layer design (IBConnection + IBAdapter)
- ✅ SOL-001: Single Responsibility - IB integration only
- ✅ SOL-005: Dependency injection (config parameter)
- ✅ ARCH-005: Early returns for error conditions

### Reconnection Pattern
- ✅ ReconnectionManager for 24/7 operation
- ✅ Exponential backoff with jitter
- ✅ Callback registration for events
- ✅ Alert thresholds

### Logging & Observability
- ✅ LOG-003: Appropriate levels (debug, info, warning, error)
- ✅ LOG-004: Exception logging with context
- ✅ LOG-002: Context in logs (symbol, side, quantity, status)
- ✅ LOG-005: No sensitive data logged

### Resource Management
- ✅ __del__ cleanup for IB connection
- ✅ Graceful disconnect
- ✅ Subscription cleanup

### Documentation
- ✅ Comprehensive docstrings
- ✅ Usage examples provided
- ✅ Error handling documented

## Audit Status: PASSED

### Summary
This is a well-structured IB adapter with strong safety features and proper reconnection logic for 24/7 operation. The integration with TradingValidator and ReconnectionManager shows attention to production readiness.

### Strengths
1. **CRITICAL: TradingValidator Integration**: Validates position sizes and stop-loss BEFORE execution
2. **Reconnection Logic**: ReconnectionManager with exponential backoff and callbacks
3. **Market Data Caching**: 5-second cache with real-time subscription option
4. **Contract Management**: Smart contract caching and creation
5. **Comprehensive Error Handling**: All exceptions caught appropriately
6. **Price Validation**: Validates stop/limit prices vs current market
7. **Resource Cleanup**: Proper __del__ implementation

### Safety Features
1. Position size validation (max 25% of capital by default)
2. Stop-loss validation (ensures stop-loss is valid for direction)
3. Warning for orders without stop-loss (risk management)
4. Price validation vs current market (prevents invalid orders)
5. Auto-connect on operations
6. Graceful degradation on errors

### Reconnection Features
1. Exponential backoff (base 1.0s, max 60s)
2. Jitter for thundering herd prevention
3. Configurable max attempts (default: 10)
4. Alert threshold (default: 3 attempts)
5. Callbacks for on_attempt, on_success, on_failure
6. Connection statistics tracking

### No Critical Issues Found
- No security vulnerabilities (no hardcoded secrets)
- No anti-patterns
- Trading safety properly implemented
- Code is production-ready for paper trading

### Notes
- Requires TWS or IB Gateway running
- Environment variables for configuration (IB_HOST, IB_PORT, IB_CLIENT_ID, IB_ACCOUNT)
- Supports both paper (7497) and live (7496) ports
- Singleton pattern via get_ib_adapter()
- ib_insync requires util.patchAsyncio() for async compatibility

---
*Audited on 2026-02-07*
