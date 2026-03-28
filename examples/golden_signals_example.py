#!/usr/bin/env python3
"""
Golden Signals Monitoring - Usage Example

This script demonstrates how to use the Golden Signals Monitor
to track the four golden signals for the algorithmic trading system.

Usage:
    python examples/golden_signals_example.py

The script will:
1. Initialize the golden signals monitor
2. Simulate trading system activity
3. Collect and display metrics
4. Show SLO compliance status
5. Demonstrate health status evaluation
"""

import asyncio
import random
import time

from app.sre.monitoring import (
    get_golden_signals_monitor,
    GoldenSignalsConfig,
    HealthStatus,
    SLOTarget,
    SignalType,
    Decimal,
)


async def health_change_callback(old_health: HealthStatus, new_health: HealthStatus):
    """Callback when health status changes."""
    print(f"\n{'!' * 60}")
    print(f"HEALTH STATUS CHANGED: {old_health.value} -> {new_health.value}")
    print(f"{'!' * 60}\n")


async def slo_violation_callback(slo_target: SLOTarget, actual_value: float):
    """Callback when SLO is violated."""
    print(f"\n{'*' * 60}")
    print(f"SLO VIOLATION DETECTED!")
    print(f"  Description: {slo_target.description}")
    print(f"  Target: {slo_target.target_value}")
    print(f"  Actual: {actual_value:.2f}")
    print(f"{'*' * 60}\n")


async def simulate_trading_activity(monitor, duration_seconds: int = 60):
    """Simulate trading system activity."""
    print(f"\nSimulating trading activity for {duration_seconds} seconds...")

    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        # Simulate requests
        num_requests = random.randint(5, 20)
        for _ in range(num_requests):
            # Random latency between 50ms and 800ms
            latency_ms = random.uniform(50, 800)

            # 2% chance of error
            success = random.random() > 0.02
            error_type = (
                None
                if success
                else random.choice(["timeout", "connection_error", "critical_error"])
            )

            # Record metrics
            monitor.record_latency(latency_ms)
            monitor.record_request(success=success, error_type=error_type)

        # Wait a bit
        await asyncio.sleep(1)

    print("Trading activity simulation completed.")


async def main():
    """Main example function."""
    print("=" * 70)
    print("Golden Signals Monitoring - Usage Example")
    print("=" * 70)

    # Create configuration with custom SLO targets
    config = GoldenSignalsConfig(
        service_name="example-trading-engine",
        slo_targets=[
            # Custom latency SLO
            SLOTarget(
                signal_type=SignalType.LATENCY,
                metric_name="p95_ms",
                target_value=Decimal("600"),
                comparison_op="lte",
                window_minutes=5,
                description="95th percentile latency under 600ms",
            ),
            # Error rate SLO
            SLOTarget(
                signal_type=SignalType.ERRORS,
                metric_name="error_rate_pct",
                target_value=Decimal("5.0"),
                comparison_op="lte",
                window_minutes=5,
                description="Error rate under 5%",
            ),
        ],
        # Alert thresholds
        latency_warning_ms=400.0,
        latency_critical_ms=800.0,
        error_rate_warning_pct=2.0,
        error_rate_critical_pct=5.0,
        # Callbacks
        on_health_change=health_change_callback,
        on_slo_violation=slo_violation_callback,
    )

    # Get monitor instance
    monitor = get_golden_signals_monitor(
        service_name="example-trading-engine",
        config=config,
    )

    print("\n1. Initializing monitor...")
    await monitor.initialize()
    print("   Monitor initialized successfully!")

    print("\n2. Starting automatic metrics collection...")
    await monitor.start_collection()
    print("   Collection started!")

    print("\n3. Simulating trading activity...")
    await simulate_trading_activity(monitor, duration_seconds=30)

    print("\n4. Collecting current metrics...")
    metrics = await monitor.collect_metrics()

    print("\n" + "=" * 70)
    print("CURRENT GOLDEN SIGNALS")
    print("=" * 70)

    print("\nLATENCY:")
    print(f"  P50:  {metrics.latency.p50_ms:.2f} ms")
    print(f"  P95:  {metrics.latency.p95_ms:.2f} ms")
    print(f"  P99:  {metrics.latency.p99_ms:.2f} ms")
    print(f"  Mean: {metrics.latency.mean_ms:.2f} ms")

    print("\nTRAFFIC:")
    print(f"  Requests/sec:  {metrics.traffic.requests_per_second:.2f}")
    print(f"  Requests/min:  {metrics.traffic.requests_per_minute:.2f}")
    print(f"  Connections:   {metrics.traffic.current_connections}")

    print("\nERRORS:")
    print(f"  Error rate:    {metrics.errors.error_rate_pct:.2f}%")
    print(f"  Error count:   {metrics.errors.error_count}")
    print(f"  Total requests: {metrics.errors.total_requests}")
    print(f"  By type:       {metrics.errors.errors_by_type}")

    print("\nSATURATION:")
    print(f"  CPU:           {metrics.saturation.cpu_usage_pct:.1f}%")
    print(f"  Memory:        {metrics.saturation.memory_usage_pct:.1f}%")
    print(f"    Used:        {metrics.saturation.memory_used_mb:.0f} MB")
    print(f"    Available:   {metrics.saturation.memory_available_mb:.0f} MB")
    print(f"  Disk:          {metrics.saturation.disk_usage_pct:.1f}%")
    print(f"    Used:        {metrics.saturation.disk_used_gb:.2f} GB")
    print(f"    Free:        {metrics.saturation.disk_free_gb:.2f} GB")
    print(f"  Network:       {metrics.saturation.network_utilization_pct:.1f}%")
    print(
        f"  Load Average:  {metrics.saturation.load_average[0]:.2f}, "
        f"{metrics.saturation.load_average[1]:.2f}, "
        f"{metrics.saturation.load_average[2]:.2f}"
    )

    print("\n" + "=" * 70)
    print(f"OVERALL HEALTH: {metrics.overall_health.value.upper()}")
    print("=" * 70)

    print("\n5. Getting metrics summary...")
    summary = await monitor.get_metrics_summary()
    print("\nSUMMARY:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n6. Checking SLO compliance...")
    compliance = await monitor.check_slo_compliance()
    print("\nSLO COMPLIANCE:")
    for description, is_compliant in compliance.items():
        status = "✓ PASS" if is_compliant else "✗ FAIL"
        print(f"  {status}: {description}")

    print("\n7. Getting metrics history...")
    history = await monitor.get_metrics_history(limit=5)
    print(f"\nRecent history ({len(history)} samples):")
    for i, hist in enumerate(history[-5:], 1):
        print(
            f"  {i}. {hist.collected_at.strftime('%H:%M:%S')} - "
            f"Health: {hist.overall_health.value}, "
            f"Latency P99: {hist.latency.p99_ms:.1f}ms, "
            f"Error Rate: {hist.errors.error_rate_pct:.2f}%"
        )

    print("\n8. Stopping collection...")
    await monitor.stop_collection()
    print("   Collection stopped!")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
