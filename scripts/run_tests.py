#!/usr/bin/env python
"""
Comprehensive test runner for algoTrading system.

This script provides convenient ways to run different test suites:
- Unit tests: Fast, isolated tests
- Integration tests: Slower tests with external dependencies
- Load tests: Performance and stress tests
- Critical tests: Must-pass tests for critical paths
- All tests: Complete test suite

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --load             # Run only load tests
    python run_tests.py --critical         # Run only critical tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --failfast         # Stop on first failure
"""

import argparse
import subprocess
import sys
from typing import List


def run_pytest(args: List[str]) -> int:
    """
    Run pytest with given arguments.

    Args:
        args: List of pytest arguments

    Returns:
        Exit code from pytest
    """
    cmd = ["python", "-m", "pytest"] + args
    print(f"\n{'=' * 70}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'=' * 70}\n")

    result = subprocess.run(cmd, sys.stdout)

    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run algoTrading test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run all tests
  %(prog)s --unit             Run only unit tests
  %(prog)s --integration      Run only integration tests
  %(prog)s --load             Run only load tests
  %(prog)s --critical         Run only critical path tests
  %(prog)s --coverage         Run with coverage report
  %(prog)s --fast             Run fast tests only (skip slow tests)
  %(prog)s --failfast         Stop on first failure
  %(prog)s --verbose          Verbose output
        """,
    )

    # Test suite selection
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--load", action="store_true", help="Run only load/stress tests")
    parser.add_argument("--critical", action="store_true", help="Run only critical path tests")

    # Test options
    parser.add_argument("--coverage", "-c", action="store_true", help="Generate coverage report")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--failfast", "-x", action="store_true", help="Stop on first failure")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--parallel",
        "-n",
        type=int,
        metavar="N",
        help="Run tests in parallel with N workers (requires pytest-xdist)",
    )
    parser.add_argument(
        "--kernel",
        action="store_true",
        help="Run tests (deprecated alias for backwards compatibility)",
    )

    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = []

    # Add test paths based on selection
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.load:
        pytest_args.extend(["-m", "load"])
    elif args.critical:
        pytest_args.extend(["-m", "critical"])
    else:
        # Run all tests
        pass

    # Add options
    if args.fast:
        pytest_args.extend(["-m", "not slow"])

    if args.failfast:
        pytest_args.append("-x")

    if args.verbose:
        pytest_args.append("-vv")
    else:
        pytest_args.append("-v")

    if args.parallel:
        pytest_args.extend(["-n", str(args.parallel)])

    if args.coverage:
        # Coverage is enabled by default in pytest.ini
        pass

    # Run tests
    exit_code = run_pytest(pytest_args)

    # Print summary
    print(f"\n{'=' * 70}")
    if exit_code == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print(f"{'=' * 70}\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
