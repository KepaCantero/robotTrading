#!/usr/bin/env python3
"""
Demo script for TimeSyncMonitor.

Phase 2.7: Time Sync Monitor Demo

This script demonstrates the TimeSyncMonitor functionality including:
- Starting/stopping monitoring
- Checking time drift
- Validating orders
- Getting status
"""

import asyncio
import logging

from app.services.monitoring.time_sync_monitor import (
    TimeSyncConfig,
    TimeSyncMonitor,
    get_time_sync_monitor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def demo_basic_monitoring():
    """Demonstrate basic monitoring functionality."""
    logger.debug("\n" + "=" * 60)
    logger.debug("DEMO: Basic Time Sync Monitoring")
    logger.debug("=" * 60 + "\n")

    # Get monitor instance
    monitor = get_time_sync_monitor()

    # Check NTP availability
    logger.debug(f"NTP Available: {monitor.get_ntp_availability()}")

    # Perform a force check
    logger.debug("\nPerforming force check...")
    result = await monitor.force_check()

    logger.debug(f"Drift: {result['drift_seconds']:.3f} seconds")
    logger.debug(f"Is Synced: {result['is_synced']}")
    logger.debug(f"Threshold: {result['threshold']} seconds")
    logger.debug(f"NTP Server: {result['ntp_server']}")
    logger.debug(f"Local Time: {result['local_time']}")
    logger.debug(f"NTP Time: {result['ntp_time']}")

    # Get status
    status = monitor.get_status()
    logger.debug(f"\nTotal Checks: {status.checks_total}")
    logger.debug(f"Failed Checks: {status.checks_failed}")


async def demo_monitoring_with_callbacks():
    """Demonstrate monitoring with callbacks."""
    logger.debug("\n" + "=" * 60)
    logger.debug("DEMO: Monitoring with Callbacks")
    logger.debug("=" * 60 + "\n")

    # Create callbacks
    drift_detected_count = [0]
    critical_drift_count = [0]

    def on_drift(drift: float):
        drift_detected_count[0] += 1
        logger.warning(f"Drift detected: {drift:.3f}s")

    def on_critical(drift: float):
        critical_drift_count[0] += 1
        logger.critical(f"CRITICAL drift: {drift:.3f}s")

    # Create config with callbacks
    config = TimeSyncConfig(
        check_interval_seconds=2.0,
        drift_threshold_seconds=1.0,
        critical_threshold_seconds=5.0,
        on_drift_detected=on_drift,
        on_critical_drift=on_critical,
    )

    monitor = TimeSyncMonitor(config)

    # Start monitoring
    logger.debug("Starting monitoring for 6 seconds...")
    await monitor.start()

    # Let it run for a few cycles
    await asyncio.sleep(6)

    # Stop monitoring
    await monitor.stop()

    logger.debug(f"\nDrift detected callbacks: {drift_detected_count[0]}")
    logger.debug(f"Critical drift callbacks: {critical_drift_count[0]}")


async def demo_order_validation():
    """Demonstrate order validation."""
    logger.debug("\n" + "=" * 60)
    logger.debug("DEMO: Order Validation")
    logger.debug("=" * 60 + "\n")

    monitor = get_time_sync_monitor()

    # Sample orders
    orders = [
        {"symbol": "AAPL", "quantity": 100, "side": "buy", "price": 150.0},
        {"symbol": "GOOGL", "quantity": 50, "side": "buy", "price": 2800.0},
        {"symbol": "MSFT", "quantity": 75, "side": "sell", "price": 300.0},
    ]

    logger.debug(f"Clock is synced: {monitor.is_synced()}")
    logger.debug(f"Current drift: {monitor.get_drift_seconds():.3f}s")

    logger.debug("\nValidating orders:")
    for order in orders:
        is_valid = await monitor.validate_order_timestamp(order)
        status = "✓ VALID" if is_valid else "✗ REJECTED"
        logger.debug(f"  {order['symbol']}: {status}")

    # Get final status
    status = monitor.get_status()
    logger.debug(f"\nStatus: {status.to_dict()}")


async def demo_metrics_collection():
    """Demonstrate metrics collection."""
    logger.debug("\n" + "=" * 60)
    logger.debug("DEMO: Metrics Collection")
    logger.debug("=" * 60 + "\n")

    monitor = get_time_sync_monitor()

    # Perform multiple checks
    logger.debug("Performing 5 time sync checks...")
    for i in range(5):
        await monitor.check_time_drift()
        await asyncio.sleep(0.5)

    # Get status
    status = monitor.get_status()

    logger.debug("\nMetrics:")
    logger.debug(f"  Total Checks: {status.checks_total}")
    logger.debug(f"  Failed Checks: {status.checks_failed}")
    logger.debug(f"  Current Drift: {status.drift_seconds:.3f}s")
    logger.debug(f"  Is Synced: {status.is_synced}")
    logger.debug(f"  Last Check: {status.last_check}")
    logger.debug(f"  NTP Server: {status.ntp_server}")


async def demo_clock_sync():
    """Demonstrate clock synchronization (if available)."""
    logger.debug("\n" + "=" * 60)
    logger.debug("DEMO: Clock Synchronization")
    logger.debug("=" * 60 + "\n")

    monitor = get_time_sync_monitor()

    if not monitor.get_ntp_availability():
        logger.debug("NTP not available - skipping clock sync demo")
        return

    logger.debug("Attempting to sync system clock...")
    logger.debug("Note: This requires root privileges and may not work in all environments\n")

    result = await monitor.sync_clock()

    if result:
        logger.debug("✓ Clock sync successful")
    else:
        logger.debug("✗ Clock sync failed (may require root privileges)")

    # Check drift after sync attempt
    drift = await monitor.check_time_drift()
    logger.debug(f"\nCurrent drift: {drift:.3f}s")


async def main():
    """Run all demos."""
    logger.debug("\n" + "=" * 60)
    logger.debug("Time Sync Monitor Demo - Phase 2.7")
    logger.debug("=" * 60)

    try:
        # Run demos
        await demo_basic_monitoring()
        await demo_metrics_collection()
        await demo_order_validation()
        await demo_monitoring_with_callbacks()
        await demo_clock_sync()

        logger.debug("\n" + "=" * 60)
        logger.debug("Demo completed successfully!")
        logger.debug("=" * 60 + "\n")

    except KeyboardInterrupt:
        logger.debug("\nDemo interrupted by user")
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Demo error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
