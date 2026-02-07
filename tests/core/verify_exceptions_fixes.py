#!/usr/bin/env python3
"""
Quick verification script for P0 fixes in app/core/exceptions.py

This script verifies the critical changes made:
1. DatabaseError renamed to AlgoTradingDatabaseError
2. Input validation added to all helper functions
"""

import importlib.util
import sys

# Load exceptions module directly
spec = importlib.util.spec_from_file_location(
    "app.core.exceptions", "/Users/kepa.cantero/Projects/algoTrading/app/core/exceptions.py"
)
exceptions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exceptions)

print("=" * 70)
print("VERIFYING P0 FIXES FOR app/core/exceptions.py")
print("=" * 70)

# Test 1: Verify DatabaseError was renamed to AlgoTradingDatabaseError
print("\n[P0] Test 1: DatabaseError → AlgoTradingDatabaseError")
print("-" * 70)
assert hasattr(exceptions, 'AlgoTradingDatabaseError'), "❌ AlgoTradingDatabaseError not found"
assert not hasattr(exceptions, 'DatabaseError') or 'DatabaseError' not in dir(
    exceptions
), "❌ Old DatabaseError still exists"
error = exceptions.AlgoTradingDatabaseError("test")
assert error.__class__.__name__ == "AlgoTradingDatabaseError", "❌ Class name is incorrect"
print("✅ AlgoTradingDatabaseError exists and is properly named")
print(f"✅ Class name: {error.__class__.__name__}")

# Test 2: Verify input validation for all helper functions
print("\n[P0] Test 2: Input validation for all helper functions")
print("-" * 70)

helper_functions = [
    'raise_configuration_error',
    'raise_validation_error',
    'raise_business_logic_error',
    'raise_market_data_error',
    'raise_trading_error',
    'raise_database_error',
    'raise_authentication_error',
]

validation_tests = [
    ("empty string", ""),
    ("whitespace", "   "),
    ("newline", "\n"),
    ("tab", "\t"),
]

all_passed = True
for func_name in helper_functions:
    func = getattr(exceptions, func_name)
    print(f"\nTesting {func_name}:")
    for test_name, invalid_input in validation_tests:
        try:
            func(invalid_input)
            print(f"  ❌ {func_name} did not validate {test_name}: '{repr(invalid_input)}'")
            all_passed = False
        except ValueError as e:
            if "message must be a non-empty string" in str(e):
                print(f"  ✅ {func_name} rejects {test_name}: '{repr(invalid_input)}'")
            else:
                print(f"  ⚠️  {func_name} validation message: {e}")
        except Exception as e:
            print(f"  ❌ {func_name} raised unexpected error: {type(e).__name__}: {e}")
            all_passed = False

# Test 3: Verify all exception classes exist
print("\n[P0] Test 3: All exception classes exist")
print("-" * 70)

expected_classes = [
    'AlgoTradingError',
    'ConfigurationError',
    'ValidationError',
    'BusinessLogicError',
    'MarketDataError',
    'TradingError',
    'PortfolioError',
    'SignalError',
    'BacktestError',
    'AlgoTradingDatabaseError',
    'APIError',
    'AuthenticationError',
]

for cls_name in expected_classes:
    if hasattr(exceptions, cls_name):
        print(f"✅ {cls_name}")
    else:
        print(f"❌ {cls_name} NOT FOUND")
        all_passed = False

# Final result
print("\n" + "=" * 70)
if all_passed:
    print("✅ ALL P0 FIXES VERIFIED SUCCESSFULLY")
    print("=" * 70)
    sys.exit(0)
else:
    print("❌ SOME VERIFICATIONS FAILED")
    print("=" * 70)
    sys.exit(1)
