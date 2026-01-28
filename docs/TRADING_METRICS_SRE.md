# Trading Metrics Monitoring for SRE Compliance

## Overview

The Trading Metrics Monitoring module provides comprehensive monitoring of trading-specific metrics essential for maintaining high availability and performance in algorithmic trading systems. This module extends Google SRE's golden signals with financial metrics critical to trading operations.

## Architecture

### Core Components

#### 1. TradingMetricsMonitor
The main monitoring class that tracks all trading-specific metrics.

**Key Features:**
- Real-time order execution tracking
- Slippage analysis in basis points
- Position synchronization health monitoring
- Market data freshness tracking
- Strategy health scoring
- Risk limit compliance monitoring

#### 2. Metrics Categories

##### Order Execution Metrics
```python
@dataclass(frozen=True)
class OrderExecutionMetrics:
    p50_latency_ms: float      # Median order latency
    p95_latency_ms: float      # 95th percentile latency
    p99_latency_ms: float      # 99th percentile latency
    mean_latency_ms: float     # Average latency
    total_orders: int          # Total orders tracked
    filled_orders: int         # Successfully filled orders
    rejected_orders: int       # Rejected orders
    cancelled_orders: int      # Cancelled orders
    fill_rate_pct: float       # Fill rate percentage
```

##### Slippage Metrics
```python
@dataclass(frozen=True)
class SlippageMetrics:
    avg_slippage_bps: float           # Average slippage in basis points
    p95_slippage_bps: float           # 95th percentile slippage
    max_slippage_bps: float           # Maximum slippage
    total_slippage_usd: float         # Total slippage in USD
    positive_slippage_count: int      # Orders with favorable slippage
    negative_slippage_count: int      # Orders with adverse slippage
    slippage_ratio: float             # Positive / Total ratio
```

##### Position Synchronization Metrics
```python
@dataclass(frozen=True)
class PositionSyncMetrics:
    sync_health_pct: float        # Percentage of positions in sync
    total_positions: int          # Total positions tracked
    synced_positions: int         # Positions matching broker
    mismatched_positions: int     # Positions with discrepancies
    missing_positions: int        # Positions in broker but not internal
    ghost_positions: int          # Positions in internal but not broker
    largest_quantity_delta: float # Largest quantity discrepancy
    avg_quantity_delta: float     # Average quantity discrepancy
```

##### Market Data Metrics
```python
@dataclass(frozen=True)
class MarketDataMetrics:
    avg_latency_ms: float          # Average market data latency
    p95_latency_ms: float          # 95th percentile latency
    p99_latency_ms: float          # 99th percentile latency
    stale_data_count: int          # Number of stale quotes
    total_quotes: int              # Total quotes received
    data_freshness_pct: float      # Percentage of fresh quotes
    gap_count: int                 # Number of data gaps
    last_quote_age_seconds: float  # Age of most recent quote
```

##### Strategy Health Metrics
```python
@dataclass(frozen=True)
class StrategyHealthMetrics:
    overall_health_score: float    # Aggregate health score (0-100)
    active_strategies: int         # Number of active strategies
    healthy_strategies: int        # Strategies with good performance
    degraded_strategies: int       # Strategies with declining performance
    critical_strategies: int       # Strategies needing attention
    avg_sharpe_ratio: float        # Average Sharpe ratio
    avg_win_rate_pct: float        # Average win rate
    avg_profit_factor: float       # Average profit factor
    total_drawdown_pct: float      # Total drawdown percentage
```

##### Risk Limit Metrics
```python
@dataclass(frozen=True)
class RiskLimitMetrics:
    compliance_score: float        # Compliance score (0-100)
    total_limits: int              # Total risk limits
    limits_compliant: int          # Limits within threshold
    limits_violated: int           # Limits exceeded
    limits_warning: int            # Limits near threshold
    critical_violations: int       # Critical limit breaches
    max_breach_pct: float          # Maximum breach percentage
    avg_utilization_pct: float     # Average utilization
```

## Usage

### Basic Setup

```python
from app.sre.monitoring import get_trading_metrics_monitor
from datetime import datetime

# Get monitor instance
monitor = get_trading_metrics_monitor()
await monitor.initialize()

# Start automatic collection
await monitor.start_collection()
```

### Recording Orders

```python
# Record order submission
order_id = monitor.record_order(
    symbol="AAPL",
    side="buy",
    quantity=100.0,
    expected_price=150.0,
    submitted_at=datetime.utcnow()
)

# Update order fill
monitor.update_order_fill(
    order_id=order_id,
    fill_price=150.05,
    filled_at=datetime.utcnow(),
    broker_order_id="BROKER_123"
)

# Update order rejection (if rejected)
monitor.update_order_rejection(
    order_id=order_id,
    reason="Insufficient funds"
)

# Update order cancellation (if cancelled)
monitor.update_order_cancellation(order_id=order_id)
```

### Monitoring Positions

```python
# Update internal positions
monitor.update_internal_position("AAPL", 100.0)
monitor.update_internal_position("MSFT", -50.0)

# Update broker positions
monitor.update_broker_position("AAPL", 100.0)
monitor.update_broker_position("MSFT", -50.0)

# Check position sync health
sync_health = monitor.check_position_sync()
print(f"Position sync health: {sync_health:.1f}%")
```

### Market Data Tracking

```python
# Update market data timestamps
monitor.update_market_data_timestamp(
    symbol="AAPL",
    timestamp=datetime.utcnow(),
    latency_ms=45.0
)
```

### Strategy Health Monitoring

```python
# Update strategy health scores
monitor.update_strategy_health("momentum", 85.0)
monitor.update_strategy_health("mean_reversion", 72.0)
monitor.update_strategy_health("arbitrage", 91.0)
```

### Risk Limit Tracking

```python
# Update risk limit utilization
monitor.update_risk_limit(
    limit_name="max_exposure",
    utilization_pct=75.0,
    critical=False
)

monitor.update_risk_limit(
    limit_name="drawdown_limit",
    utilization_pct=95.0,
    critical=True
)
```

### Getting Metrics

```python
# Collect current metrics
metrics = await monitor.collect_metrics()

# Get metrics summary
summary = await monitor.get_metrics_summary()

# Get most recent metrics
current = await monitor.get_current_metrics()

# Calculate specific metrics
fill_rate = monitor.calculate_fill_rate()
avg_slippage = monitor.calculate_slippage()
sync_health = monitor.check_position_sync()
trading_health = monitor.evaluate_trading_health()
```

## Configuration

### Default Thresholds

```python
config = TradingMetricsConfig(
    # Fill rate thresholds
    fill_rate_warning_pct=95.0,
    fill_rate_critical_pct=90.0,

    # Slippage thresholds
    slippage_warning_bps=5.0,
    slippage_critical_bps=10.0,

    # Order latency thresholds
    order_latency_warning_ms=500.0,
    order_latency_critical_ms=1000.0,

    # Position sync thresholds
    position_sync_warning_pct=95.0,
    position_sync_critical_pct=90.0,

    # Market data thresholds
    market_data_stale_threshold_seconds=5.0,

    # Strategy health thresholds
    strategy_health_warning_score=70.0,
    strategy_health_critical_score=50.0,

    # Collection settings
    collection_interval_seconds=60,
    history_size=1440,  # 24 hours at 1-minute intervals
)
```

### Custom Configuration

```python
from app.sre.monitoring import TradingMetricsConfig, get_trading_metrics_monitor

config = TradingMetricsConfig(
    fill_rate_warning_pct=98.0,
    slippage_warning_bps=2.0,
    order_latency_critical_ms=500.0,
    collection_interval_seconds=30,
)

monitor = get_trading_metrics_monitor(config=config)
```

## Health Status Levels

The trading system health is evaluated using five levels:

1. **OPTIMAL**: All metrics within excellent ranges
2. **HEALTHY**: Metrics within acceptable ranges
3. **DEGRADED**: Some metrics showing concerning trends
4. **CRITICAL**: Multiple metrics breaching critical thresholds
5. **SUSPENDED**: Trading suspended due to critical issues

## SLO Integration

The trading metrics monitor integrates with SLO tracking:

```python
# Define SLO targets
slo_targets = [
    # Fill rate SLO
    {
        "metric": "fill_rate_pct",
        "target": 95.0,
        "comparison": "gte",
        "window_minutes": 5,
    },
    # Latency SLO
    {
        "metric": "p95_latency_ms",
        "target": 500.0,
        "comparison": "lte",
        "window_minutes": 5,
    },
    # Slippage SLO
    {
        "metric": "avg_slippage_bps",
        "target": 5.0,
        "comparison": "lte",
        "window_minutes": 5,
    },
]
```

## Database Persistence

Metrics are automatically persisted to SQLite database:

```python
# Database schema
# - trading_metrics_history: Historical metrics
# - order_records: Individual order records

# Path: data/trading_metrics.db
```

## Callbacks

### Health Change Callback

```python
def on_health_change(old_health, new_health):
    print(f"Health changed: {old_health} -> {new_health}")
    # Send alert, notify team, etc.

config = TradingMetricsConfig(
    on_health_change=on_health_change,
)
```

### Critical Event Callback

```python
def on_critical_event(event_type, event_data):
    print(f"Critical event: {event_type}")
    print(f"Data: {event_data}")
    # Trigger incident response

config = TradingMetricsConfig(
    on_critical_event=on_critical_event,
)
```

## Best Practices

1. **Start Collection Early**: Initialize monitor at application startup
2. **Record All Orders**: Track every order for accurate metrics
3. **Sync Positions Regularly**: Update positions frequently for accurate sync health
4. **Monitor Market Data**: Track market data freshness and latency
5. **Set Appropriate Thresholds**: Configure thresholds based on your trading requirements
6. **Use Callbacks**: Implement health change callbacks for proactive alerting
7. **Review Metrics Regularly**: Analyze metrics trends for optimization opportunities

## Performance Considerations

- **Memory Usage**: Monitored with configurable history size
- **Database I/O**: Async operations minimize blocking
- **Collection Interval**: Balance between granularity and overhead
- **Sample Sizes**: Configurable for different metric types

## Troubleshooting

### Low Fill Rate
- Check order rejection reasons
- Review risk limit utilization
- Verify broker connectivity

### High Slippage
- Analyze order timing vs market volatility
- Review order types and execution strategies
- Check market data latency

### Position Sync Issues
- Reconcile positions with broker
- Check for timing discrepancies
- Verify position update logic

### Stale Market Data
- Check data feed connectivity
- Verify data source timestamps
- Review latency metrics

## References

- Google SRE Book: https://sre.google/sre-book/
- Financial SRE patterns for algorithmic trading
- Tomasini's "Trading Systems" methodology
- FIX protocol performance metrics
