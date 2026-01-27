#!/usr/bin/env python
"""
Validation script for Profile Batch Backtester refactoring.

This script validates that the refactored modules work correctly
and maintain backward compatibility with the original implementation.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all components can be imported."""
    print("=" * 60)
    print("Testing Imports...")
    print("=" * 60)

    try:
        from app.backtesting.profile_batch import (
            ProfileBatchBacktester,
            ProfileGenerator,
            BaselineBacktestExecutor,
            OptimizationPipeline,
            ResultAggregator,
            ReportGenerator,
        )
        print("✓ All components imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_instantiation():
    """Test that components can be instantiated."""
    print("\n" + "=" * 60)
    print("Testing Instantiation...")
    print("=" * 60)

    try:
        from app.backtesting.profile_batch import ProfileBatchBacktester

        backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
        print("✓ ProfileBatchBacktester instantiated")
        return True
    except Exception as e:
        print(f"✗ Instantiation failed: {e}")
        return False


def test_profile_generation():
    """Test profile generation."""
    print("\n" + "=" * 60)
    print("Testing Profile Generation...")
    print("=" * 60)

    try:
        from app.backtesting.profile_batch import ProfileBatchBacktester

        backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
        profiles = backtester.generate_all_profiles()

        expected_count = 180  # 5 objectives × 3 risks × 3 tiers × 4 horizons
        assert len(profiles) == expected_count, f"Expected {expected_count} profiles, got {len(profiles)}"

        print(f"✓ Generated {len(profiles)} profiles (expected {expected_count})")
        return True
    except Exception as e:
        print(f"✗ Profile generation failed: {e}")
        return False


def test_backward_compatibility():
    """Test backward compatibility with original import."""
    print("\n" + "=" * 60)
    print("Testing Backward Compatibility...")
    print("=" * 60)

    try:
        # This should still work
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester as OldBacktester

        old_backtester = OldBacktester("config/profile_batch_backtest.yaml")
        old_profiles = old_backtester.generate_all_profiles()

        print("✓ Original import still works")
        print(f"✓ Original implementation generates {len(old_profiles)} profiles")
        return True
    except Exception as e:
        print(f"✗ Backward compatibility check failed: {e}")
        return False


def test_api_compatibility():
    """Test that the API is compatible."""
    print("\n" + "=" * 60)
    print("Testing API Compatibility...")
    print("=" * 60)

    try:
        from app.backtesting.profile_batch import ProfileBatchBacktester

        backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

        # Check that all expected methods exist
        expected_methods = [
            "generate_all_profiles",
            "run_single_profile",
            "run_all_profiles",
            "get_best_strategy",
            "export_results",
            "generate_comparison_report",
            "get_fallback_metrics",
        ]

        for method in expected_methods:
            assert hasattr(backtester, method), f"Missing method: {method}"
            print(f"✓ Method exists: {method}")

        print("✓ All expected methods present")
        return True
    except Exception as e:
        print(f"✗ API compatibility check failed: {e}")
        return False


def test_component_independence():
    """Test that components can be used independently."""
    print("\n" + "=" * 60)
    print("Testing Component Independence...")
    print("=" * 60)

    try:
        from app.backtesting.profile_batch import (
            ProfileGenerator,
            BaselineBacktestExecutor,
            ResultAggregator,
        )

        # Test ProfileGenerator independently
        generator = ProfileGenerator("config/profile_batch_backtest.yaml")
        profiles = generator.generate_all_profiles()
        print(f"✓ ProfileGenerator works independently ({len(profiles)} profiles)")

        # Test BaselineBacktestExecutor independently
        from pathlib import Path
        executor = BaselineBacktestExecutor(Path("/tmp/test_output"))
        print("✓ BaselineBacktestExecutor works independently")

        # Test ResultAggregator independently
        aggregator = ResultAggregator("sqlite:///test.db", lambda p: "medio")
        print("✓ ResultAggregator works independently")

        return True
    except Exception as e:
        print(f"✗ Component independence test failed: {e}")
        return False


def test_line_counts():
    """Test that files meet line count constraints."""
    print("\n" + "=" * 60)
    print("Testing Line Counts...")
    print("=" * 60)

    from pathlib import Path

    max_lines = 600
    profile_batch_dir = Path("/Users/kepa.cantero/Projects/algoTrading/app/backtesting/profile_batch")

    all_within_limit = True
    for py_file in profile_batch_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        line_count = len(py_file.read_text().splitlines())
        status = "✓" if line_count <= max_lines else "✗"
        print(f"{status} {py_file.name}: {line_count} lines (max {max_lines})")

        if line_count > max_lines:
            all_within_limit = False

    if all_within_limit:
        print(f"✓ All files within {max_lines} line limit")
        return True
    else:
        print(f"✗ Some files exceed {max_lines} line limit")
        return False


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("PROFILE BATCH BACKTESTER REFACTORING VALIDATION")
    print("=" * 60 + "\n")

    tests = [
        ("Imports", test_imports),
        ("Instantiation", test_instantiation),
        ("Profile Generation", test_profile_generation),
        ("Backward Compatibility", test_backward_compatibility),
        ("API Compatibility", test_api_compatibility),
        ("Component Independence", test_component_independence),
        ("Line Counts", test_line_counts),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60 + "\n")

    if passed == total:
        print("✅ ALL VALIDATION TESTS PASSED!")
        print("\nThe refactoring is successful and ready for production use.")
        return 0
    else:
        print("❌ SOME VALIDATION TESTS FAILED")
        print("\nPlease review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
