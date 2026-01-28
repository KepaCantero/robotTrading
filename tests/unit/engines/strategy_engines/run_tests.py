#!/usr/bin/env python
"""
Test runner script for strategy engine unit tests.

This script runs the tests without importing the main application,
avoiding dependency issues.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

def run_tests():
    """Run the strategy engine tests."""
    import pytest

    # Run tests from the strategy_engines directory
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # pytest arguments
    args = [
        test_dir,
        "-v",
        "--tb=short",
        "-p", "no:cacheprovider",
        "--markers=unit",
        "-x",  # Stop on first failure
    ]

    # Add optional test file argument
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    exit_code = pytest.main(args)
    return exit_code

if __name__ == "__main__":
    sys.exit(run_tests())
