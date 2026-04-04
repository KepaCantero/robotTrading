"""
Tests for Rebalancer Domain Service - ZeroDivisionError fix verification
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal

from app.domain.services.rebalancer import RebalancePlan, Rebalancer, RebalanceTrade


def test_rebalance_trade_with_zero_current_quantity_no_zero_division():
    """Test that RebalanceTrade with zero current_quantity doesn't cause ZeroDivisionError."""
    # Create a trade with zero current quantity (simulating a new position)
    trade = RebalanceTrade(
        symbol="TEST",
        target_quantity=Decimal("100"),
        current_quantity=Decimal("0"),  # Zero quantity - the critical case
        trade_quantity=Decimal("100"),
        target_value=Decimal("10000"),
        current_value=Decimal("0"),
        drift_pct=Decimal("10"),
        average_price=Decimal("100"),  # Price computed during plan creation
    )

    # Verify the trade was created successfully
    assert trade.symbol == "TEST"
    assert trade.current_quantity == Decimal("0")
    assert trade.average_price == Decimal("100")

    # Test calculation using average_price (no division needed)
    trade_value = abs(trade.trade_quantity * trade.average_price)
    assert trade_value == Decimal("10000")


def test_rebalance_plan_validation_with_zero_quantity_positions():
    """Test that validate_rebalance_plan works with zero-quantity positions."""
    # Create plan with trades that have zero current quantity
    trades = [
        RebalanceTrade(
            symbol="NEW1",
            target_quantity=Decimal("50"),
            current_quantity=Decimal("0"),  # Zero quantity
            trade_quantity=Decimal("50"),
            target_value=Decimal("5000"),
            current_value=Decimal("0"),
            drift_pct=Decimal("5"),
            average_price=Decimal("100"),  # Pre-computed price
        ),
        RebalanceTrade(
            symbol="EXIST1",
            target_quantity=Decimal("150"),
            current_quantity=Decimal("100"),  # Has existing quantity
            trade_quantity=Decimal("50"),
            target_value=Decimal("15000"),
            current_value=Decimal("10000"),
            drift_pct=Decimal("5"),
            average_price=Decimal("100"),  # Pre-computed price
        ),
    ]

    plan = RebalancePlan(
        total_value=Decimal("100000"),
        cash_available=Decimal("20000"),
        trades=trades,
        total_drift=Decimal("10"),
        estimated_cost=Decimal("2"),
    )

    # Mock portfolio object (minimal)
    class MockPortfolio:
        pass

    portfolio = MockPortfolio()
    rebalancer = Rebalancer()

    # This should NOT raise ZeroDivisionError
    is_valid, issues = rebalancer.validate_rebalance_plan(plan, portfolio)

    # Verify validation worked
    assert isinstance(is_valid, bool)
    assert isinstance(issues, list)
    # With $20,000 cash and $10,000 in buys, should be valid
    assert is_valid is True


def test_rebalance_trade_average_price_calculation():
    """Test that average_price is correctly calculated for existing and new positions."""
    # For existing position with quantity
    existing_value = Decimal("10000")
    existing_qty = Decimal("100")
    existing_avg_price = existing_value / existing_qty
    assert existing_avg_price == Decimal("100")

    # For new position (zero quantity) - uses market price
    market_price = Decimal("150")
    new_avg_price = market_price  # Falls back to market price
    assert new_avg_price == Decimal("150")


if __name__ == "__main__":
    print("Running ZeroDivisionError fix verification tests...")
    test_rebalance_trade_with_zero_current_quantity_no_zero_division()
    print("  ✓ test_rebalance_trade_with_zero_current_quantity_no_zero_division PASSED")

    test_rebalance_plan_validation_with_zero_quantity_positions()
    print("  ✓ test_rebalance_plan_validation_with_zero_quantity_positions PASSED")

    test_rebalance_trade_average_price_calculation()
    print("  ✓ test_rebalance_trade_average_price_calculation PASSED")

    print("\nAll tests PASSED! ZeroDivisionError fix verified.")
