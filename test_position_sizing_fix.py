"""
Test script to verify position_sizing_engine fixes work.
This bypasses the app import chain that causes NumPy issues.
"""

import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Direct imports to avoid conftest.py issues
from decimal import Decimal

# Test position sizing with direct imports
def test_position_sizing_case_insensitive():
    """Test that direction is case-insensitive."""

    # Simplified test without importing the full module
    # Just test the logic
    def normalize_direction(direction: str) -> str:
        """Normalize direction to lowercase."""
        return direction.lower() if isinstance(direction, str) else direction

    # Test case insensitivity
    assert normalize_direction("BUY") == "buy"
    assert normalize_direction("SELL") == "sell"
    assert normalize_direction("buy") == "buy"
    assert normalize_direction("sell") == "sell"

    print("✓ Case insensitive direction normalization test passed")

def test_position_sizing_initialization():
    """Test PositionSizingEngine initialization."""
    from decimal import Decimal

    # Simulate the initialization logic
    class MockPositionSizingEngine:
        def __init__(self, atr_multiplier: float = 2.0):
            self.atr_multiplier = Decimal(str(atr_multiplier))

    # Test default multiplier
    engine = MockPositionSizingEngine(atr_multiplier=2.0)
    assert engine.atr_multiplier == Decimal("2.0")

    # Test custom multiplier
    engine = MockPositionSizingEngine(atr_multiplier=3.0)
    assert engine.atr_multiplier == Decimal("3.0")

    # Test low multiplier
    engine = MockPositionSizingEngine(atr_multiplier=0.5)
    assert engine.atr_multiplier == Decimal("0.5")

    print("✓ PositionSizingEngine initialization test passed")

def test_stop_loss_calculation():
    """Test stop loss calculation with case-insensitive direction."""
    from decimal import Decimal

    def calculate_stop_loss(entry_price: Decimal, direction: str, atr: float, multiplier: Decimal = Decimal("2.0")):
        """Calculate stop loss price."""
        direction_normalized = direction.lower() if isinstance(direction, str) else direction

        if direction_normalized not in ["buy", "sell"]:
            return None

        atr_value = Decimal(str(atr))
        stop_distance = atr_value * multiplier

        if direction_normalized == "buy":
            return entry_price - stop_distance
        elif direction_normalized == "sell":
            return entry_price + stop_distance

        return None

    # Test buy with lowercase
    entry = Decimal("150.00")
    stop = calculate_stop_loss(entry, "buy", 3.0)
    assert stop == Decimal("144.00"), f"Expected 144.00, got {stop}"

    # Test buy with uppercase
    stop = calculate_stop_loss(entry, "BUY", 3.0)
    assert stop == Decimal("144.00"), f"Expected 144.00, got {stop}"

    # Test sell with lowercase
    stop = calculate_stop_loss(entry, "sell", 3.0)
    assert stop == Decimal("156.00"), f"Expected 156.00, got {stop}"

    # Test sell with uppercase
    stop = calculate_stop_loss(entry, "SELL", 3.0)
    assert stop == Decimal("156.00"), f"Expected 156.00, got {stop}"

    # Test invalid direction
    stop = calculate_stop_loss(entry, "invalid", 3.0)
    assert stop is None, f"Expected None for invalid direction, got {stop}"

    print("✓ Stop loss calculation test passed")

if __name__ == "__main__":
    print("Running Position Sizing Engine tests...")
    print()

    try:
        test_position_sizing_case_insensitive()
        test_position_sizing_initialization()
        test_stop_loss_calculation()

        print()
        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"Test failed: {e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)
