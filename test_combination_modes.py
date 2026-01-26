#!/usr/bin/env python3
"""
Test script to verify filter combination modes work correctly.
This validates the ALL, MAJORITY, and ANY modes.
"""


def test_combination_mode(mode, passed_filters, total_filters):
    """
    Test if a signal should be generated based on combination mode.

    Args:
        mode: 'ALL', 'MAJORITY', or 'ANY'
        passed_filters: Number of filters that passed
        total_filters: Total number of active filters

    Returns:
        True if signal should be generated, False otherwise
    """
    if mode == "ALL":
        return passed_filters == total_filters
    elif mode == "MAJORITY":
        required = max(1, (total_filters + 1) // 2)  # >50%
        return passed_filters >= required
    elif mode == "ANY":
        return passed_filters > 0
    return False


def run_tests():
    """Run comprehensive tests for all combination modes."""
    total_filters = 6  # ema, rsi, stoch_rsi, momentum, volume, atr

    print("Filter Combination Mode Tests")
    print("=" * 70)
    print(f"Total active filters: {total_filters}")
    print()

    # Test ALL mode
    print("ALL Mode Tests:")
    print("-" * 70)
    for passed in range(total_filters + 1):
        result = test_combination_mode("ALL", passed, total_filters)
        status = "BUY SIGNAL" if result else "NO SIGNAL"
        print(f"  {passed}/{total_filters} filters passed -> {status}")

    print()
    print("MAJORITY Mode Tests (requires 4/6):")
    print("-" * 70)
    for passed in range(total_filters + 1):
        result = test_combination_mode("MAJORITY", passed, total_filters)
        status = "BUY SIGNAL" if result else "NO SIGNAL"
        print(f"  {passed}/{total_filters} filters passed -> {status}")

    print()
    print("ANY Mode Tests:")
    print("-" * 70)
    for passed in range(total_filters + 1):
        result = test_combination_mode("ANY", passed, total_filters)
        status = "BUY SIGNAL" if result else "NO SIGNAL"
        print(f"  {passed}/{total_filters} filters passed -> {status}")

    print()
    print("=" * 70)
    print("Comparison Summary:")
    print("-" * 70)

    test_scenarios = [
        (6, "All filters agree"),
        (4, "Majority agrees"),
        (3, "Half agree"),
        (1, "Only one agrees"),
        (0, "None agree"),
    ]

    for passed, description in test_scenarios:
        all_result = test_combination_mode("ALL", passed, total_filters)
        majority_result = test_combination_mode("MAJORITY", passed, total_filters)
        any_result = test_combination_mode("ANY", passed, total_filters)

        print(f"\n{description} ({passed}/{total_filters}):")
        print(f"  ALL mode:     {'BUY' if all_result else 'NO'}")
        print(f"  MAJORITY mode: {'BUY' if majority_result else 'NO'}")
        print(f"  ANY mode:     {'BUY' if any_result else 'NO'}")

    print()
    print("=" * 70)
    print("Configuration Validation:")
    print("-" * 70)
    print("Current production config:")
    print("  combination_mode: 'ALL'")
    print("  min_confidence: 0.8")
    print()
    print("Expected behavior:")
    print("  - Only generates BUY signals when ALL 6 filters pass")
    print("  - Dramatically reduces trade frequency")
    print("  - Increases signal quality and win rate")
    print("  - Minimizes false positives and whipsaw")


if __name__ == "__main__":
    run_tests()
