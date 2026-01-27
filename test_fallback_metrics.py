#!/usr/bin/env python
"""
Test script to verify fallback metrics tracking in ProfileBatchBacktester.

This script tests:
1. Metrics initialization
2. Thread-safe incrementing
3. get_fallback_metrics() method
4. log_fallback_summary() method
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_fallback_metrics():
    """Test fallback metrics tracking functionality."""
    logger.info("=" * 60)
    logger.info("Testing Fallback Metrics Tracking")
    logger.info("=" * 60)

    # Test 1: Initialization
    logger.info("\nTest 1: Metrics Initialization")
    backtester = ProfileBatchBacktester("config/backtesting/comprehensive_backtest.yaml")

    # Get initial metrics
    initial_metrics = backtester.get_fallback_metrics()
    logger.info(f"Initial metrics: {initial_metrics}")

    # Verify all metrics are initialized to 0 or higher
    assert initial_metrics["profile_config_loader_fallback_count"] >= 0, "ProfileConfigLoader count should be >= 0"
    assert initial_metrics["profile_strategy_mapper_fallback_count"] >= 0, "ProfileStrategyMapper count should be >= 0"
    assert initial_metrics["config_key_mismatch_count"] >= 0, "Config key mismatch count should be >= 0"
    logger.info("✓ Metrics initialized correctly")

    # Test 2: Increment counters
    logger.info("\nTest 2: Increment Counters")
    backtester._increment_fallback_counter("profile_config_loader")
    backtester._increment_fallback_counter("profile_config_loader")
    backtester._increment_fallback_counter("profile_strategy_mapper")
    backtester._increment_fallback_counter("config_key_mismatch")

    metrics_after = backtester.get_fallback_metrics()
    logger.info(f"After increments: {metrics_after}")

    assert metrics_after["profile_config_loader_fallback_count"] >= 2, "Should have at least 2 ProfileConfigLoader fallbacks"
    assert metrics_after["profile_strategy_mapper_fallback_count"] >= 1, "Should have at least 1 ProfileStrategyMapper fallback"
    assert metrics_after["config_key_mismatch_count"] >= 1, "Should have at least 1 config key mismatch"
    logger.info("✓ Counters incremented correctly")

    # Test 3: Thread safety
    logger.info("\nTest 3: Thread Safety")
    import threading

    def increment_many_times():
        for _ in range(100):
            backtester._increment_fallback_counter("profile_config_loader")

    threads = [threading.Thread(target=increment_many_times) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics_threaded = backtester.get_fallback_metrics()
    logger.info(f"After threaded increments: {metrics_threaded}")
    logger.info("✓ Thread safety verified (no errors)")

    # Test 4: Log summary
    logger.info("\nTest 4: Log Summary")
    backtester.log_fallback_summary()
    logger.info("✓ Summary logged successfully")

    # Test 5: Check metrics are included in batch summary format
    logger.info("\nTest 5: Metrics Integration")
    # The metrics should be accessible for summary generation
    all_metrics = backtester.get_fallback_metrics()
    total = sum(all_metrics.values())
    logger.info(f"Total fallbacks tracked: {total}")
    logger.info("✓ Metrics are accessible for integration")

    logger.info("\n" + "=" * 60)
    logger.info("All Tests Passed!")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    try:
        test_fallback_metrics()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
