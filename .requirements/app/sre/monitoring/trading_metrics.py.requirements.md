# Requirements: sre/monitoring/trading_metrics.py

## Source File Analysis
- **File Path**: `app/sre/monitoring/trading_metrics.py`
- **Lines of Code**: 1272
- **Status**: PASSED
- **Audit Date**: 2026-02-07

## Purpose
Implements trading-specific metrics monitoring for algorithmic trading SRE. Extends Google SRE's golden signals with financial metrics critical to trading operations. Key objectives:
- Monitor order execution latency (time from signal to fill)
- Track fill rate and slippage in basis points
- Monitor position synchronization health (broker vs internal)
- Track market data freshness and latency
- Monitor strategy health scores
- Track risk limit compliance

## Dependencies
- Internal: None (standalone SRE module)
- External:
  - `aiosqlite`: Async SQLite database for persistence
  - `asyncio`: Async/await patterns
  - `dataclasses`: Data structures
  - `pathlib`: Path operations

## Classes/Functions

### Enums
- `TradingHealthStatus(str, Enum)`: OPTIMAL, HEALTHY, DEGRADED, CRITICAL, SUSPENDED
- `OrderExecutionPhase(str, Enum)`: SIGNAL_GENERATED, ORDER_VALIDATED, ORDER_SUBMITTED, BROKER_ACKNOWLEDGED, PARTIALLY_FILLED, FULLY_FILLED, REJECTED, CANCELLED

### Data Classes (Frozen - Immutable)
- `OrderExecutionMetrics`: Order execution performance metrics
- `SlippageMetrics`: Slippage analysis metrics (in basis points)
- `PositionSyncMetrics`: Position synchronization health metrics
- `MarketDataMetrics`: Market data quality and latency metrics
- `StrategyHealthMetrics`: Strategy performance and health metrics
- `RiskLimitMetrics`: Risk limit compliance metrics
- `TradingMetrics`: Container for all trading metrics

### Mutable Data Classes
- `OrderRecord`: Record of an order for tracking
  - `get_latency_ms()`: Get order execution latency in milliseconds
  - `get_slippage_bps()`: Get slippage in basis points

### Configuration
- `TradingMetricsConfig`: Configuration for trading metrics monitor
  - Thresholds: fill_rate, slippage, order_latency, position_sync, strategy_health
  - Collection settings: interval, history size, sample sizes
  - Database path and callbacks

### Main Class
- `TradingMetricsMonitor`: Monitor trading-specific metrics for SRE compliance
  - `initialize()`: Initialize the monitor
  - `start_collection()`: Start automatic metrics collection
  - `stop_collection()`: Stop automatic metrics collection
  - `collect_metrics()`: Collect all trading metrics
  - `record_order()`: Record an order submission
  - `update_order_fill()`: Update order with fill information
  - `update_order_rejection()`: Update order as rejected
  - `update_order_cancellation()`: Update order as cancelled
  - `update_internal_position()`: Update internal position for a symbol
  - `update_broker_position()`: Update broker position for a symbol
  - `update_market_data_timestamp()`: Update market data timestamp for a symbol
  - `update_strategy_health()`: Update strategy health score
  - `update_risk_limit()`: Update risk limit utilization
  - `calculate_fill_rate()`: Calculate order fill rate
  - `calculate_slippage()`: Calculate average slippage in basis points
  - `check_position_sync()`: Check broker vs internal position sync health
  - `evaluate_trading_health()`: Evaluate overall trading system health
  - `get_current_metrics()`: Get most recent metrics
  - `get_metrics_summary()`: Get comprehensive metrics summary

### Private Methods
- `_init_database()`: Initialize SQLite schema
- `_collection_loop()`: Main collection loop for automatic collection
- `_collect_order_execution_metrics()`: Collect order execution metrics
- `_collect_slippage_metrics()`: Collect slippage metrics
- `_collect_position_sync_metrics()`: Collect position synchronization metrics
- `_collect_market_data_metrics()`: Collect market data quality metrics
- `_collect_strategy_health_metrics()`: Collect strategy health metrics
- `_collect_risk_limit_metrics()`: Collect risk limit compliance metrics
- `_evaluate_overall_health()`: Evaluate overall trading system health
- `_check_health_change()`: Check if health status has changed
- `_persist_metrics()`: Persist metrics to database

## Business Logic

### Trading SRE Metrics (Financial SRE Patterns)
1. **Order Execution Latency**: Time from signal to fill (p50, p95, p99)
2. **Fill Rate**: Percentage of orders successfully filled
3. **Slippage**: Execution price vs expected price in basis points
4. **Position Sync Health**: Broker vs internal position reconciliation
5. **Market Data Freshness**: Quote freshness and delay
6. **Strategy Health Score**: Aggregate strategy performance indicator (0-100)
7. **Risk Limit Compliance**: Risk limit utilization and violations

### Alert Thresholds (Defaults)
| Metric | Warning | Critical |
|--------|---------|----------|
| Fill Rate | 95% | 90% |
| Slippage | 5 bps | 10 bps |
| Order Latency (p95) | 500ms | 1000ms |
| Position Sync Health | 95% | 90% |
| Market Data Freshness | 90% | 80% |
| Strategy Health Score | 70 | 50 |

### Health Status Determination
```python
# Count critical and warning violations
critical_count = count of metrics above critical thresholds
warning_count = count of metrics above warning thresholds

# Determine overall health
if critical_count >= 2 or risk_limits.critical_violations > 0: CRITICAL
elif critical_count >= 1 or warning_count >= 3: DEGRADED
elif critical_count >= 1 or warning_count >= 1: HEALTHY
else: OPTIMAL
```

### Slippage Calculation (Basis Points)
```python
# 1 basis point = 0.01%
# Slippage = ((fill_price - expected_price) / expected_price) * 10000
def get_slippage_bps(self) -> Optional[float]:
    if self.fill_price and self.expected_price:
        price_diff = self.fill_price - self.expected_price
        return (price_diff / self.expected_price) * 10000
    return None
```

### Position Sync Health Calculation
```python
# Tolerance: 0.01 units
synced = count of positions where |internal_qty - broker_qty| < 0.01
sync_health_pct = (synced / total_positions) * 100
```

## Data Models

### Database Schema
```sql
-- Trading metrics history table
CREATE TABLE trading_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    order_latency_p50 REAL,
    order_latency_p95 REAL,
    order_latency_p99 REAL,
    fill_rate_pct REAL,
    avg_slippage_bps REAL,
    position_sync_health_pct REAL,
    market_data_freshness_pct REAL,
    strategy_health_score REAL,
    risk_compliance_score REAL,
    overall_health TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- Order records table
CREATE TABLE order_records (
    order_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    expected_price REAL NOT NULL,
    submitted_at TEXT NOT NULL,
    filled_at TEXT,
    fill_price REAL,
    status TEXT NOT NULL,
    rejection_reason TEXT,
    broker_order_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('utc'))
)

-- Indexes
CREATE INDEX idx_trading_metrics_timestamp
ON trading_metrics_history(timestamp)
CREATE INDEX idx_order_records_symbol
ON order_records(symbol, submitted_at)
```

## API Contracts

### Initialization
```python
monitor = TradingMetricsMonitor(
    config=TradingMetricsConfig()
)
await monitor.initialize()
```

### Recording Orders
```python
# Submit order
order_id = monitor.record_order(
    symbol="AAPL",
    side="buy",
    quantity=100,
    expected_price=150.25,
    submitted_at=datetime.utcnow()
)

# Update with fill
monitor.update_order_fill(
    order_id=order_id,
    fill_price=150.30,
    filled_at=datetime.utcnow(),
    broker_order_id="BRK12345"
)

# Update rejection
monitor.update_order_rejection(
    order_id=order_id,
    reason="Insufficient margin"
)

# Update cancellation
monitor.update_order_cancellation(order_id=order_id)
```

### Updating Positions
```python
# Update internal position
monitor.update_internal_position(symbol="AAPL", quantity=500)

# Update broker position
monitor.update_broker_position(symbol="AAPL", quantity=498)

# Check sync health
sync_health = monitor.check_position_sync()  # Returns 0-100
```

### Updating Market Data
```python
# Update market data timestamp
monitor.update_market_data_timestamp(
    symbol="AAPL",
    timestamp=datetime.utcnow(),
    latency_ms=15
)
```

### Updating Strategy Health
```python
# Update strategy health score (0-100)
monitor.update_strategy_health(
    strategy_name="momentum_v1",
    health_score=85.5
)
```

### Updating Risk Limits
```python
# Update risk limit utilization
monitor.update_risk_limit(
    limit_name="max_position_size",
    utilization_pct=75.0,
    critical=False
)
```

### Getting Metrics Summary
```python
summary = await monitor.get_metrics_summary()
print(json.dumps(summary, indent=2))
```

## Error Handling
- Database errors: Logged with context
- Timeout errors: Caught with context-rich logging
- Invalid order IDs: Logged but don't block processing
- Missing positions: Treated as zero (graceful degradation)

### Exception Handling Pattern
```python
try:
    # Database operation
except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
    self.logger.error(f"Context: {e}")
    # Handle gracefully, don't crash
```

## Performance Considerations
- **In-memory history**: Deque with maxlen for O(1) append/pop
- **Async collection**: All I/O is non-blocking
- **Database indexing**: Indexes on timestamp, symbol
- **Collection interval**: Default 60 seconds (configurable)
- **History size**: Default 1440 samples (24 hours at 1-minute intervals)
- **Sample sizes**: 1000 samples for order latency and slippage

### Optimization Notes
- Deque for O(1) history operations
- Order tracking with dictionary lookups (O(1))
- Position sync with tolerance-based comparison
- Metrics persisted asynchronously
- Automatic history trimming

## Testing Strategy

### Unit Tests Needed
1. Order execution latency calculation
2. Fill rate calculation
3. Slippage calculation in basis points
4. Position sync health calculation
5. Market data freshness calculation
6. Strategy health scoring
7. Risk limit compliance checking
8. Overall health status evaluation

### Integration Tests Needed
1. Database persistence and recovery
2. Order lifecycle tracking (submit, fill, reject, cancel)
3. Position reconciliation
4. Automatic collection loop
5. Callback triggering on health changes

### Edge Cases to Test
1. Empty order book (no orders)
2. All orders rejected (0% fill rate)
3. Maximum slippage (extreme price moves)
4. Complete position mismatch (0% sync)
5. Stale market data (old timestamps)
6. Negative strategy health scores
7. Risk limit violations (>100% utilization)

### Example Test Cases
```python
# Test order latency calculation
order = OrderRecord(
    order_id="test_1",
    symbol="AAPL",
    side="buy",
    quantity=100,
    expected_price=150.0,
    submitted_at=datetime(2026, 2, 7, 12, 0, 0)
)
order.filled_at = datetime(2026, 2, 7, 12, 0, 0, 500000)  # +500ms
assert order.get_latency_ms() == 500.0

# Test slippage calculation
order.fill_price = 150.50  # +$0.50
expected_slippage = (0.50 / 150.0) * 10000  # ~33.33 bps
assert abs(order.get_slippage_bps() - expected_slippage) < 0.1

# Test fill rate calculation
monitor.record_order("AAPL", "buy", 100, 150.0, datetime.utcnow())
monitor.record_order("TSLA", "buy", 50, 200.0, datetime.utcnow())
monitor.update_order_fill("order_1", 150.0, datetime.utcnow())
monitor.update_order_rejection("order_2", "rejected")
fill_rate = monitor.calculate_fill_rate()  # Should be 50%
assert fill_rate == 50.0

# Test position sync health
monitor.update_internal_position("AAPL", 100)
monitor.update_broker_position("AAPL", 100)  # Perfect sync
monitor.update_internal_position("TSLA", 50)
monitor.update_broker_position("TSLA", 49)  # 1 unit difference
sync_health = monitor.check_position_sync()  # Should be 50%
assert sync_health == 50.0
```

## Audit Status: PASSED

### Compliance Summary
- **Structure**: Well-organized following Financial SRE patterns
- **Documentation**: Comprehensive docstrings with usage examples
- **Error Handling**: Proper exception handling with context
- **Type Hints**: Complete type annotations using `from __future__ import annotations`
- **Async/Await**: Correct async patterns throughout
- **Data Classes**: Proper use of frozen dataclasses for immutability
- **Database**: Proper schema with indexes for performance
- **Logging**: Context-aware logging at appropriate levels
- **Configuration**: Sensible defaults with override capability
- **Singleton Pattern**: Module-level singleton management

### Strengths
1. Complete implementation of Financial SRE metrics
2. Trading-specific metrics beyond golden signals
3. Order lifecycle tracking with latency measurement
4. Slippage calculation in basis points (industry standard)
5. Position reconciliation with tolerance handling
6. Market data freshness tracking
7. Strategy health scoring system
8. Risk limit compliance monitoring

### No Critical Issues Found
All code follows best practices for:
- Financial SRE patterns
- Algorithmic trading reliability engineering
- Clean Architecture principles
- Async Python programming
- Database operations
- Error handling
- Type safety

### Integration Points
- Extends Golden Signals monitoring with trading-specific metrics
- Integrates with order management systems
- Connects to position management systems
- Feeds into error budget calculations
- Works with alert fatigue prevention system

### Financial SRE Compliance
This module implements Financial SRE patterns for algorithmic trading:
1. **Order Execution**: End-to-end latency tracking (signal to fill)
2. **Slippage Analysis**: Basis point calculation (industry standard)
3. **Position Reconciliation**: Broker vs internal position sync
4. **Market Data Quality**: Freshness and latency tracking
5. **Strategy Health**: Aggregate performance scoring
6. **Risk Management**: Limit compliance monitoring

---
*Audited on 2026-02-07*
