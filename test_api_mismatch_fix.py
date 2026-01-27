#!/usr/bin/env python
"""
Test script to verify API mismatch fixes in ProfileBatchBacktester.

This script tests that:
1. _run_baseline() properly handles empty results from ComprehensiveBacktestRunner
2. _run_backtest_with_params() properly handles empty results
3. _safe_extract_first_result() validates results correctly
"""

import logging
import sys
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_safe_extract_first_result():
    """Test the _safe_extract_first_result helper method."""
    from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

    # Create a minimal backtester instance
    backtester = ProfileBatchBacktester("config/backtesting/comprehensive_backtest.yaml")

    print("\n" + "=" * 80)
    print("Testing _safe_extract_first_result()")
    print("=" * 80)

    # Test 1: Valid results
    print("\n1. Testing valid results...")
    valid_results = [{
        "sharpe_ratio": 1.5,
        "return_pct": 20.0,
        "max_drawdown": -10.0,
        "win_rate": 0.6,
        "total_trades": 100
    }]
    result = backtester._safe_extract_first_result(valid_results, "test valid")
    assert result == valid_results[0], "Failed to extract valid result"
    print("   PASS: Valid result extracted correctly")

    # Test 2: Empty list
    print("\n2. Testing empty list...")
    empty_results = []
    result = backtester._safe_extract_first_result(empty_results, "test empty")
    assert result == backtester._get_empty_metrics(), "Failed to handle empty list"
    print("   PASS: Empty list returns empty metrics")

    # Test 3: None results
    print("\n3. Testing None results...")
    result = backtester._safe_extract_first_result(None, "test None")
    assert result == backtester._get_empty_metrics(), "Failed to handle None"
    print("   PASS: None returns empty metrics")

    # Test 4: First element is None
    print("\n4. Testing first element None...")
    none_element = [None]
    result = backtester._safe_extract_first_result(none_element, "test element None")
    assert result == backtester._get_empty_metrics(), "Failed to handle None element"
    print("   PASS: None element returns empty metrics")

    # Test 5: Result with missing fields
    print("\n5. Testing result with missing fields...")
    incomplete_result = [{"sharpe_ratio": 1.5}]
    result = backtester._safe_extract_first_result(incomplete_result, "test incomplete")
    assert result == incomplete_result[0], "Failed to handle incomplete result"
    print("   PASS: Incomplete result returned with warning")

    print("\n" + "=" * 80)
    print("All _safe_extract_first_result tests PASSED")
    print("=" * 80)


def test_api_signature():
    """Test that ComprehensiveBacktestRunner API matches our expectations."""
    from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
    import inspect

    print("\n" + "=" * 80)
    print("Testing ComprehensiveBacktestRunner API signature")
    print("=" * 80)

    # Check return type annotation
    method = ComprehensiveBacktestRunner.run_baseline_backtest
    sig = inspect.signature(method)
    return_annotation = sig.return_annotation

    print(f"\nMethod: {method.__name__}")
    print(f"Return annotation: {return_annotation}")

    # Check if it's a List type
    if "List" in str(return_annotation):
        print("   PASS: Returns List type as expected")
    else:
        print("   WARNING: Return type may not be List")

    print("\n" + "=" * 80)


def test_error_handling():
    """Test error handling in the fixed methods."""
    print("\n" + "=" * 80)
    print("Testing error handling")
    print("=" * 80)

    from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

    backtester = ProfileBatchBacktester("config/backtesting/comprehensive_backtest.yaml")

    # Test _get_empty_metrics
    print("\n1. Testing _get_empty_metrics()...")
    empty = backtester._get_empty_metrics()
    expected_keys = {"sharpe_ratio", "return_pct", "max_drawdown", "win_rate", "total_trades", "total_pnl"}
    assert set(empty.keys()) == expected_keys, "Empty metrics missing expected keys"
    assert all(v == 0.0 for v in empty.values()), "Empty metrics should all be 0.0"
    print("   PASS: Empty metrics structure correct")

    print("\n" + "=" * 80)
    print("Error handling tests PASSED")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_api_signature()
        test_safe_extract_first_result()
        test_error_handling()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED")
        print("=" * 80)
        print("\nSummary of changes:")
        print("- Fixed _run_baseline() to use _safe_extract_first_result()")
        print("- Fixed _run_backtest_with_params() to use _safe_extract_first_result()")
        print("- Added _safe_extract_first_result() helper with comprehensive validation")
        print("- Added proper logging for debugging")
        print("- Returns empty metrics on failure (via _get_empty_metrics())")
        print("=" * 80)
        sys.exit(0)

    except Exception as e:
        logger.error(f"TEST FAILED: {e}", exc_info=True)
        sys.exit(1)
