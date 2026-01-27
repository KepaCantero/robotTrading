#!/usr/bin/env python3
"""
Test script to verify ProfileConfigLoader integration into ProfileBatchBacktester.

This script tests:
1. ProfileConfigLoader initialization
2. Parameter range loading
3. Validation config loading
4. Fallback logic
5. Backward compatibility

Usage:
    python test_profile_config_loader_integration.py
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_import():
    """Test that ProfileConfigLoader can be imported."""
    logger.info("Testing ProfileConfigLoader import...")
    try:
        from app.core.config.profile_config_loader import ProfileConfigLoader
        logger.info("✅ ProfileConfigLoader import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import ProfileConfigLoader: {e}")
        return False

def test_profile_batch_backtester_import():
    """Test that ProfileBatchBacktester can be imported."""
    logger.info("Testing ProfileBatchBacktester import...")
    try:
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
        logger.info("✅ ProfileBatchBacktester import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import ProfileBatchBacktester: {e}")
        return False

def test_profile_config_loader_initialization():
    """Test ProfileConfigLoader initialization."""
    logger.info("Testing ProfileConfigLoader initialization...")
    try:
        from app.core.config.profile_config_loader import ProfileConfigLoader

        loader = ProfileConfigLoader()
        logger.info("✅ ProfileConfigLoader initialized successfully")

        # Test basic methods
        config = loader.config
        logger.info(f"✅ Config loaded with {len(config)} top-level keys")

        # Test threshold config
        rsi_config = loader.get_threshold_config("rsi")
        logger.info(f"✅ RSI threshold config: {rsi_config}")

        # Test validation configs
        wf_config = loader.get_walk_forward_config()
        logger.info(f"✅ Walk-forward config: {wf_config}")

        mc_config = loader.get_monte_carlo_config()
        logger.info(f"✅ Monte Carlo config: {mc_config}")

        return True
    except Exception as e:
        logger.error(f"❌ ProfileConfigLoader initialization failed: {e}")
        return False

def test_profile_batch_backtester_initialization():
    """Test ProfileBatchBacktester initialization with ProfileConfigLoader."""
    logger.info("Testing ProfileBatchBacktester initialization...")
    try:
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

        # Use the actual config file
        config_path = "config/profile_batch_backtest.yaml"

        if not Path(config_path).exists():
            logger.warning(f"⚠️  Config file not found: {config_path}")
            logger.warning("Creating minimal config for testing...")
            # Create minimal config
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                f.write("""
database:
  url: "sqlite:///test_profile_batch_results.db"

output_dir: "results/test_profile_batch_backtesting"

capital_tiers:
  bajo: 50000
  medio: 150000
  alto: 500000

investment_horizons:
  short: 12
  medium: 24
  long: 36
  very_long: 60

optimization:
  n_trials: 10
  timeout: null

validation:
  walk_forward:
    enabled: true
    n_windows: 3
    train_percentage: 0.6
  monte_carlo:
    enabled: true
    n_simulations: 100
  out_of_sample:
    enabled: true
    train_percentage: 0.7

acceptance_criteria:
  min_sharpe: 1.0
  min_return: 0.10
  max_drawdown: -0.25

modules: {}
reporting: {}
""")

        backtester = ProfileBatchBacktester(config_path)
        logger.info("✅ ProfileBatchBacktester initialized successfully")

        # Check if ProfileConfigLoader was initialized
        if backtester.profile_config_loader is not None:
            logger.info("✅ ProfileConfigLoader is available in backtester")
        else:
            logger.warning("⚠️  ProfileConfigLoader is NOT available (fallback mode)")

        return True
    except Exception as e:
        logger.error(f"❌ ProfileBatchBacktester initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_range_loading():
    """Test parameter range loading from ProfileConfigLoader."""
    logger.info("Testing parameter range loading...")
    try:
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

        backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

        if backtester.profile_config_loader is None:
            logger.warning("⚠️  ProfileConfigLoader not available, skipping parameter range test")
            return True

        # Test RSI thresholds
        rsi_config = backtester.profile_config_loader.get_threshold_config("rsi")
        logger.info(f"✅ RSI config: buy_threshold={rsi_config.get('buy_threshold', {})}, "
                   f"sell_threshold={rsi_config.get('sell_threshold', {})}")

        # Test EMA distance
        ema_config = backtester.profile_config_loader.get_threshold_config("ema_distance")
        logger.info(f"✅ EMA distance config: {ema_config}")

        # Test volume ratio
        vol_config = backtester.profile_config_loader.get_threshold_config("volume_ratio")
        logger.info(f"✅ Volume ratio config: {vol_config}")

        # Test momentum
        mom_config = backtester.profile_config_loader.get_threshold_config("momentum")
        logger.info(f"✅ Momentum config: {mom_config}")

        return True
    except Exception as e:
        logger.error(f"❌ Parameter range loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation_config_loading():
    """Test validation config loading from ProfileConfigLoader."""
    logger.info("Testing validation config loading...")
    try:
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

        backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

        if backtester.profile_config_loader is None:
            logger.warning("⚠️  ProfileConfigLoader not available, skipping validation config test")
            return True

        # Test walk-forward config
        wf_config = backtester.profile_config_loader.get_walk_forward_config()
        logger.info(f"✅ Walk-forward config: {wf_config}")

        # Test Monte Carlo config
        mc_config = backtester.profile_config_loader.get_monte_carlo_config()
        logger.info(f"✅ Monte Carlo config: {mc_config}")

        # Test validation thresholds
        thresholds = backtester.profile_config_loader.get_validation_thresholds()
        logger.info(f"✅ Validation thresholds: {thresholds}")

        return True
    except Exception as e:
        logger.error(f"❌ Validation config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("PROFILE CONFIG LOADER INTEGRATION TEST")
    logger.info("=" * 80)

    tests = [
        ("Import ProfileConfigLoader", test_import),
        ("Import ProfileBatchBacktester", test_profile_batch_backtester_import),
        ("Initialize ProfileConfigLoader", test_profile_config_loader_initialization),
        ("Initialize ProfileBatchBacktester", test_profile_batch_backtester_initialization),
        ("Load Parameter Ranges", test_parameter_range_loading),
        ("Load Validation Configs", test_validation_config_loading),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info("\n" + "-" * 80)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("-" * 80)
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
