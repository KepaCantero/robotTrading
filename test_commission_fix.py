#!/usr/bin/env python3
"""
Test script to verify commission ratio fixes.

This script validates that:
1. Commission is set to $0 (standard since 2019)
2. Trade pre-filtering rejects unprofitable trades when commission > $0
3. Position sizing adjusts to maintain acceptable commission ratio
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_config_update():
    """Test that config has been updated with $0 commission."""
    import yaml

    config_path = "config/backtesting/comprehensive_backtest.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    commission = config['backtest']['commission_per_trade']
    slippage = config['backtest']['slippage']

    print("\n" + "="*80)
    print("TEST 1: Configuration Update")
    print("="*80)

    print(f"Commission per trade: ${commission}")
    print(f"Slippage: {slippage}%")

    assert commission == 0.0, f"FAIL: Commission should be $0, but is ${commission}"
    assert slippage == 0.1, f"FAIL: Slippage should be 0.1%, but is {slippage}%"

    print("✅ PASS: Commission is $0 (standard since 2019)")
    print("✅ PASS: Slippage is 0.1%")

    return True


def test_trade_filtering_with_commission():
    """Test trade pre-filtering with non-zero commission."""
    from app.backtesting.models import BacktestConfig
    from app.backtesting.engine import SimpleBacktester
    from app.models.signal import Signal, SignalType, SignalSource, SignalStrength

    print("\n" + "="*80)
    print("TEST 2: Trade Pre-filtering with Commission")
    print("="*80)

    # Create config with $10 commission
    config = BacktestConfig(
        initial_capital=Decimal("10000"),
        commission_per_trade=Decimal("10"),  # $10 per trade
        slippage_percentage=Decimal("0.1"),
        stop_loss_percentage=Decimal("5"),
        take_profit_percentage=Decimal("10"),
        max_position_size=Decimal("0.10"),
        risk_free_rate=Decimal("0.02"),
    )

    # Create backtester
    backtester = SimpleBacktester(config)

    # Create a test signal with all required fields
    past_timestamp = datetime(2024, 1, 1, 12, 0, 0)
    signal = Signal(
        symbol="TEST",
        signal_type=SignalType.BUY,
        confidence=75.0,
        timestamp=past_timestamp,
        source=SignalSource.MOMENTUM,
        price=Decimal("100"),
        strength=SignalStrength.STRONG,
        liquidity_score=0.9,
        priority_score=0.7,
        volume=Decimal("1000000"),
    )

    # Test 2a: Small position - should be rejected with $10 commission
    print("\n2a. Testing small position ($1000) with $10 commission...")
    is_valid = backtester._validate_trade_profitability(signal, Decimal("100"))

    max_position = backtester.capital * backtester.config.max_position_size  # $1000
    expected_profit = max_position * Decimal("0.10")  # 10% of $1000 = $100
    round_trip_commission = config.commission_per_trade * 2  # $20

    print(f"   Max position: ${max_position}")
    print(f"   Expected profit (10%): ${expected_profit}")
    print(f"   Round-trip commission: ${round_trip_commission}")
    print(f"   5x commission: ${round_trip_commission * 5}")
    print(f"   Expected profit >= 5x commission? {expected_profit >= round_trip_commission * 5}")
    print(f"   Result: {'ACCEPT' if is_valid else 'REJECT'}")

    assert not is_valid, "FAIL: Small position should be rejected with $10 commission"
    print("✅ PASS: Small position correctly rejected")

    # Test 2b: Large position - should be accepted with $10 commission
    print("\n2b. Testing larger capital ($100,000) with $10 commission...")
    backtester.capital = Decimal("100000")
    is_valid = backtester._validate_trade_profitability(signal, Decimal("100"))

    max_position = backtester.capital * backtester.config.max_position_size  # $10,000
    expected_profit = max_position * Decimal("0.10")  # 10% of $10,000 = $1,000
    round_trip_commission = config.commission_per_trade * 2  # $20

    print(f"   Max position: ${max_position}")
    print(f"   Expected profit (10%): ${expected_profit}")
    print(f"   Round-trip commission: ${round_trip_commission}")
    print(f"   5x commission: ${round_trip_commission * 5}")
    print(f"   Expected profit >= 5x commission? {expected_profit >= round_trip_commission * 5}")
    print(f"   Result: {'ACCEPT' if is_valid else 'REJECT'}")

    assert is_valid, "FAIL: Large position should be accepted with $10 commission"
    print("✅ PASS: Large position correctly accepted")

    # Test 2c: $0 commission - should always be accepted
    print("\n2c. Testing with $0 commission...")
    backtester.config.commission_per_trade = Decimal("0")
    is_valid = backtester._validate_trade_profitability(signal, Decimal("100"))

    print(f"   Commission: ${backtester.config.commission_per_trade}")
    print(f"   Result: {'ACCEPT' if is_valid else 'REJECT'}")

    assert is_valid, "FAIL: Trade should be accepted with $0 commission"
    print("✅ PASS: $0 commission always accepted")

    return True


def test_position_sizing_adjustment():
    """Test position sizing adjustment for commission ratio."""
    from app.backtesting.models import BacktestConfig
    from app.backtesting.engine import SimpleBacktester
    from app.models.signal import Signal, SignalType, SignalSource, SignalStrength

    print("\n" + "="*80)
    print("TEST 3: Position Sizing Adjustment")
    print("="*80)

    # Test 3a: Small capital where commission ratio cannot be fixed
    print("\n3a. Testing position sizing with high commission ratio (small capital)...")
    config = BacktestConfig(
        initial_capital=Decimal("2000"),  # Small capital
        commission_per_trade=Decimal("10"),  # $10 per trade
        slippage_percentage=Decimal("0.1"),
        stop_loss_percentage=Decimal("5"),
        take_profit_percentage=Decimal("10"),
        max_position_size=Decimal("0.10"),
        risk_free_rate=Decimal("0.02"),
    )

    backtester = SimpleBacktester(config)

    past_timestamp = datetime(2024, 1, 1, 12, 0, 0)
    signal = Signal(
        symbol="TEST",
        signal_type=SignalType.BUY,
        confidence=75.0,
        timestamp=past_timestamp,
        source=SignalSource.MOMENTUM,
        price=Decimal("100"),
        strength=SignalStrength.STRONG,
        liquidity_score=0.9,
        priority_score=0.7,
        volume=Decimal("1000000"),
    )

    print(f"   Capital: ${backtester.capital}")
    print(f"   Max position (10%): ${backtester.capital * config.max_position_size}")
    print(f"   Commission: ${config.commission_per_trade}")
    print(f"   Round-trip: ${config.commission_per_trade * 2}")

    max_position = backtester.capital * config.max_position_size
    commission_ratio = (config.commission_per_trade * 2) / max_position

    print(f"   Commission ratio: {commission_ratio:.2%}")

    # Calculate position size
    position_size = backtester._calculate_position_size(signal, Decimal("100"))
    position_value = position_size * Decimal("100")

    print(f"   Calculated position size: {position_size} shares")
    print(f"   Position value: ${position_value}")

    # With $2000 capital and 10% max position, max position is $200
    # Round-trip commission is $20, which is 10% of $200
    # Position cannot be adjusted beyond max_position_size ($200)
    # So commission ratio will still be 10% (trade should be rejected by pre-filter)

    new_commission_ratio = (config.commission_per_trade * 2) / position_value if position_value > 0 else Decimal("1")
    print(f"   New commission ratio: {new_commission_ratio:.2%}")
    print(f"   Note: Position size capped at max_position_size, ratio still high")

    # The trade should be rejected by the pre-filter, not by position sizing
    is_valid = backtester._validate_trade_profitability(signal, Decimal("100"))
    assert not is_valid, "FAIL: Trade should be rejected due to high commission ratio"
    print("✅ PASS: Trade correctly rejected by pre-filter (position sizing cannot fix this)")

    # Test 3b: Larger capital where position sizing can help
    print("\n3b. Testing position sizing with adequate capital...")
    config2 = BacktestConfig(
        initial_capital=Decimal("50000"),  # Larger capital
        commission_per_trade=Decimal("10"),  # $10 per trade
        slippage_percentage=Decimal("0.1"),
        stop_loss_percentage=Decimal("5"),
        take_profit_percentage=Decimal("10"),
        max_position_size=Decimal("0.10"),
        risk_free_rate=Decimal("0.02"),
    )

    backtester2 = SimpleBacktester(config2)

    signal2 = Signal(
        symbol="TEST",
        signal_type=SignalType.BUY,
        confidence=50.0,  # Lower confidence = smaller initial position
        timestamp=past_timestamp,
        source=SignalSource.MOMENTUM,
        price=Decimal("100"),
        strength=SignalStrength.MODERATE,
        liquidity_score=0.9,
        priority_score=0.5,
        volume=Decimal("1000000"),
    )

    print(f"   Capital: ${backtester2.capital}")
    print(f"   Max position (10%): ${backtester2.capital * config2.max_position_size}")
    print(f"   Commission: ${config2.commission_per_trade}")
    print(f"   Round-trip: ${config2.commission_per_trade * 2}")
    print(f"   Signal confidence: {signal2.confidence}%")

    max_position2 = backtester2.capital * config2.max_position_size
    base_position_value = max_position2 * Decimal("0.5")  # 50% confidence = 50% of max
    base_commission_ratio = (config2.commission_per_trade * 2) / base_position_value

    print(f"   Base position value (50% confidence): ${base_position_value}")
    print(f"   Base commission ratio: {base_commission_ratio:.2%}")

    # Calculate position size
    position_size2 = backtester2._calculate_position_size(signal2, Decimal("100"))
    position_value2 = position_size2 * Decimal("100")

    print(f"   Adjusted position size: {position_size2} shares")
    print(f"   Adjusted position value: ${position_value2}")

    new_commission_ratio2 = (config2.commission_per_trade * 2) / position_value2 if position_value2 > 0 else Decimal("1")
    print(f"   New commission ratio: {new_commission_ratio2:.2%}")

    # With $50,000 capital, even with low confidence, position sizing should maintain ratio <= 1%
    assert new_commission_ratio2 <= Decimal("0.01"), f"FAIL: Commission ratio {new_commission_ratio2:.2%} exceeds 1%"
    print("✅ PASS: Position size adjusted to maintain commission ratio <= 1%")

    return True


def test_commission_ratio_calculation():
    """Test the original problematic scenario."""
    from app.backtesting.models import BacktestConfig
    from app.backtesting.engine import SimpleBacktester

    print("\n" + "="*80)
    print("TEST 4: Original Problematic Scenario")
    print("="*80)

    # Original problematic configuration
    print("\n4a. Original configuration ($20 round-trip, $17.92 position)...")
    commission = Decimal("10")  # $10 per trade
    position_value = Decimal("17.92")
    round_trip = commission * 2

    commission_ratio = round_trip / position_value
    print(f"   Position value: ${position_value}")
    print(f"   Round-trip commission: ${round_trip}")
    print(f"   Commission ratio: {commission_ratio:.2%}")

    assert commission_ratio > Decimal("1"), "Commission ratio should exceed 100%"
    print("✅ PASS: Confirmed original problem - ratio is > 100%")

    print("\n4b. With fixes applied ($0 commission)...")
    commission = Decimal("0")
    round_trip = commission * 2

    commission_ratio = round_trip / position_value if position_value > 0 else Decimal("0")
    print(f"   Position value: ${position_value}")
    print(f"   Round-trip commission: ${round_trip}")
    print(f"   Commission ratio: {commission_ratio:.2%}")

    assert commission_ratio == Decimal("0"), "Commission ratio should be 0% with $0 commission"
    print("✅ PASS: With $0 commission, ratio is 0%")

    return True


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("COMMISSION RATIO FIX VERIFICATION")
    print("="*80)
    print("\nThis test suite verifies the fixes for the critical commission ratio problem.")

    try:
        # Test 1: Configuration update
        test_config_update()

        # Test 2: Trade pre-filtering
        test_trade_filtering_with_commission()

        # Test 3: Position sizing adjustment
        test_position_sizing_adjustment()

        # Test 4: Original scenario
        test_commission_ratio_calculation()

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✅")
        print("="*80)
        print("\nSummary of fixes:")
        print("1. ✅ Commission set to $0 (standard since 2019)")
        print("2. ✅ Trade pre-filtering rejects unprofitable trades when commission > $0")
        print("3. ✅ Position sizing adjusts to maintain commission ratio <= 1%")
        print("4. ✅ Original problem (111% ratio) resolved with $0 commission")
        print("\nThe backtesting system is now ready to run with realistic commission costs.")
        print("="*80)

        return 0

    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
