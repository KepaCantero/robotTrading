"""
Trading Metrics Monitoring Example for SRE Compliance.

This example demonstrates how to use the TradingMetricsMonitor to track
trading-specific metrics essential for algorithmic trading SRE compliance.

Usage:
    python examples/trading_metrics_example.py

Features demonstrated:
- Order execution latency tracking
- Fill rate monitoring
- Slippage analysis
- Position synchronization health
- Market data freshness monitoring
- Strategy health scoring
- Risk limit compliance tracking
"""

import asyncio
import random
from datetime import datetime, timedelta

from app.sre.monitoring import (
    get_trading_metrics_monitor,
    TradingMetricsConfig,
)


async def simulate_order_flow(monitor, num_orders=50):
    """
    Simulate a realistic order flow with varying outcomes.

    Args:
        monitor: TradingMetricsMonitor instance
        num_orders: Number of orders to simulate
    """
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    sides = ["buy", "sell"]

    print(f"\n{'='*60}")
    print(f"Simulating {num_orders} orders...")
    print(f"{'='*60}\n")

    for i in range(num_orders):
        symbol = random.choice(symbols)
        side = random.choice(sides)
        quantity = random.randint(50, 500)
        expected_price = random.uniform(100.0, 200.0)

        # Record order submission
        submitted_at = datetime.utcnow()
        order_id = monitor.record_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            expected_price=expected_price,
            submitted_at=submitted_at,
        )

        # Simulate order processing time
        processing_delay = random.uniform(50, 500)  # milliseconds
        await asyncio.sleep(processing_delay / 1000.0)

        # Determine order outcome
        outcome_roll = random.random()

        if outcome_roll < 0.85:  # 85% fill rate
            # Order filled
            slippage_bps = random.uniform(-2.0, 8.0)  # Can be positive or negative
            fill_price = expected_price * (1 + (slippage_bps / 10000))

            monitor.update_order_fill(
                order_id=order_id,
                fill_price=fill_price,
                filled_at=datetime.utcnow(),
            )

        elif outcome_roll < 0.92:  # 7% rejection rate
            # Order rejected
            reasons = [
                "Insufficient funds",
                "Risk limit exceeded",
                "Market closed",
                "Invalid quantity",
            ]
            monitor.update_order_rejection(
                order_id=order_id,
                reason=random.choice(reasons),
            )

        else:  # 8% cancellation rate
            # Order cancelled
            monitor.update_order_cancellation(order_id=order_id)

        # Print progress every 10 orders
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{num_orders} orders")

        # Small delay between orders
        await asyncio.sleep(0.01)


async def simulate_position_updates(monitor):
    """Simulate position updates between internal and broker systems."""
    print("\nUpdating positions...")

    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    for symbol in symbols:
        internal_qty = random.randint(-1000, 1000)
        broker_qty = internal_qty + random.randint(-5, 5)  # Small discrepancy

        monitor.update_internal_position(symbol, internal_qty)
        monitor.update_broker_position(symbol, broker_qty)

        print(f"  {symbol}: Internal={internal_qty}, Broker={broker_qty}")


async def simulate_market_data_stream(monitor, duration_seconds=5):
    """Simulate market data updates."""
    print("\nStreaming market data...")

    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)

    while datetime.utcnow() < end_time:
        for symbol in symbols:
            latency_ms = random.uniform(10, 100)
            monitor.update_market_data_timestamp(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                latency_ms=latency_ms,
            )

        await asyncio.sleep(0.5)


async def simulate_strategy_updates(monitor):
    """Simulate strategy health updates."""
    print("\nUpdating strategy health scores...")

    strategies = [
        ("momentum", random.uniform(60, 95)),
        ("mean_reversion", random.uniform(55, 90)),
        ("arbitrage", random.uniform(70, 98)),
        ("ml_prediction", random.uniform(50, 85)),
    ]

    for strategy_name, health_score in strategies:
        monitor.update_strategy_health(strategy_name, health_score)
        print(f"  {strategy_name}: Health={health_score:.1f}/100")


async def simulate_risk_limit_updates(monitor):
    """Simulate risk limit utilization updates."""
    print("\nUpdating risk limits...")

    risk_limits = [
        ("max_exposure", random.uniform(50, 95), False),
        ("leverage", random.uniform(40, 88), False),
        ("var_limit", random.uniform(60, 92), False),
        ("concentration", random.uniform(30, 85), False),
        # One critical limit near breach
        ("drawdown", random.uniform(85, 100), True),
    ]

    for limit_name, utilization, is_critical in risk_limits:
        monitor.update_risk_limit(
            limit_name=limit_name,
            utilization_pct=utilization,
            critical=is_critical,
        )
        status = "CRITICAL" if is_critical else "Normal"
        print(f"  {limit_name}: {utilization:.1f}% ({status})")


async def display_metrics_summary(monitor):
    """Display comprehensive metrics summary."""
    print(f"\n{'='*60}")
    print("TRADING METRICS SUMMARY")
    print(f"{'='*60}\n")

    summary = await monitor.get_metrics_summary()

    # Overall health
    print(f"Overall Health: {summary['overall_health'].upper()}")
    print()

    # Order execution metrics
    oe = summary["order_execution"]
    print("Order Execution:")
    print(f"  P95 Latency: {oe['p95_latency_ms']:.2f} ms")
    print(f"  Fill Rate: {oe['fill_rate_pct']:.1f}%")
    print(f"  Total Orders: {oe['total_orders']}")
    print(f"  Status: {oe['status'].upper()}")
    print()

    # Slippage metrics
    slippage = summary["slippage"]
    print("Slippage:")
    print(f"  Average: {slippage['avg_bps']:.2f} bps")
    print(f"  Ratio (positive/total): {slippage['ratio']:.2f}")
    print(f"  Status: {slippage['status'].upper()}")
    print()

    # Position sync metrics
    sync = summary["position_sync"]
    print("Position Sync:")
    print(f"  Health: {sync['health_pct']:.1f}%")
    print(f"  Mismatched: {sync['mismatched']}")
    print(f"  Status: {sync['status'].upper()}")
    print()

    # Market data metrics
    md = summary["market_data"]
    print("Market Data:")
    print(f"  Freshness: {md['freshness_pct']:.1f}%")
    print(f"  P95 Latency: {md['p95_latency_ms']:.2f} ms")
    print(f"  Status: {md['status'].upper()}")
    print()

    # Strategy health
    sh = summary["strategy_health"]
    print("Strategy Health:")
    print(f"  Overall Score: {sh['overall_score']:.1f}/100")
    print(f"  Active Strategies: {sh['active_strategies']}")
    print(f"  Status: {sh['status'].upper()}")
    print()

    # Risk limits
    rl = summary["risk_limits"]
    print("Risk Limits:")
    print(f"  Compliance Score: {rl['compliance_score']:.1f}%")
    print(f"  Violations: {rl['violations']}")
    print(f"  Status: {rl['status'].upper()}")
    print()


async def main():
    """Main demonstration function."""
    print("\n" + "="*60)
    print("TRADING METRICS MONITORING DEMONSTRATION")
    print("="*60)

    # Configure monitor with custom thresholds
    config = TradingMetricsConfig(
        fill_rate_warning_pct=95.0,
        fill_rate_critical_pct=90.0,
        slippage_warning_bps=5.0,
        slippage_critical_bps=10.0,
        order_latency_warning_ms=500.0,
        order_latency_critical_ms=1000.0,
        position_sync_warning_pct=95.0,
        position_sync_critical_pct=90.0,
        strategy_health_warning_score=70.0,
        strategy_health_critical_score=50.0,
        collection_interval_seconds=5,
    )

    # Get monitor instance
    monitor = get_trading_metrics_monitor(config=config)
    await monitor.initialize()

    print("\nTrading Metrics Monitor initialized.")
    print("Starting simulation...")

    # Simulate trading activity
    await simulate_order_flow(monitor, num_orders=50)
    await simulate_position_updates(monitor)
    await simulate_market_data_stream(monitor, duration_seconds=2)
    await simulate_strategy_updates(monitor)
    await simulate_risk_limit_updates(monitor)

    # Collect and display metrics
    print("\nCollecting metrics...")
    metrics = await monitor.collect_metrics()

    await display_metrics_summary(monitor)

    # Calculate specific metrics
    print("\nDirect metric calculations:")
    print(f"  Fill Rate: {monitor.calculate_fill_rate():.1f}%")
    print(f"  Average Slippage: {monitor.calculate_slippage():.2f} bps")
    print(f"  Position Sync Health: {monitor.check_position_sync():.1f}%")
    print(f"  Trading Health: {monitor.evaluate_trading_health()}")

    print(f"\n{'='*60}")
    print("Demonstration complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
