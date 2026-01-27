#!/usr/bin/env python3
"""
Verification script for CRITICAL database and validation integration fixes.

This script verifies all fixes from the code review have been properly implemented.

Run this after installing dependencies: pip install -r requirements.txt
"""

import sys
import os

def test_get_sync_db():
    """Test 1: Verify get_sync_db() function exists and works."""
    print("\n=== Test 1: get_sync_db() function ===")
    try:
        from app.core.database import get_sync_db
        print("✅ get_sync_db imported from app.core.database")

        # Check if it's a context manager
        from contextlib import AbstractContextManager
        if hasattr(get_sync_db, '__call__'):
            print("✅ get_sync_db is callable")
        else:
            print("❌ get_sync_db is not callable")
            return False

        # Check database.__init__ exports it
        from app.database import get_sync_db as exported_func
        if get_sync_db is exported_func:
            print("✅ get_sync_db properly exported from app.database.__init__")
        else:
            print("⚠️  get_sync_db exported but may be different instance")

        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_trading_validator():
    """Test 2: Verify TradingValidator integration in broker adapters."""
    print("\n=== Test 2: TradingValidator Integration ===")
    success = True

    # Test TradingValidator itself
    try:
        from app.core.trading_validators import TradingValidator
        from decimal import Decimal

        validator = TradingValidator()

        # Test validate_position_size
        try:
            validator.validate_position_size(
                capital=Decimal("100000"),
                position_size=Decimal("20000"),
                max_position_percent=Decimal("0.25")
            )
            print("✅ TradingValidator.validate_position_size works")
        except Exception as e:
            print(f"❌ validate_position_size failed: {e}")
            success = False

        # Test validate_stop_loss
        try:
            validator.validate_stop_loss(
                entry_price=Decimal("100"),
                stop_loss=Decimal("95"),
                side="long"
            )
            print("✅ TradingValidator.validate_stop_loss works")
        except Exception as e:
            print(f"❌ validate_stop_loss failed: {e}")
            success = False

    except Exception as e:
        print(f"❌ FAILED to import TradingValidator: {e}")
        return False

    # Test IB adapter integration
    try:
        from app.services.live_trading.broker_adapters.ib_adapter import IBConnection

        # Check if adapter has validator attribute
        # We can't instantiate without IB connection, so just check the class
        import inspect
        init_source = inspect.getsource(IBConnection.__init__)

        if 'self.validator = TradingValidator()' in init_source:
            print("✅ IBAdapter has TradingValidator in __init__")
        else:
            print("❌ IBAdapter missing TradingValidator in __init__")
            success = False

        # Check if place_order uses validator
        place_order_source = inspect.getsource(IBConnection.place_order)
        if 'self.validator.validate_position_size' in place_order_source:
            print("✅ IBAdapter.place_order() calls validate_position_size")
        else:
            print("❌ IBAdapter.place_order() missing validate_position_size call")
            success = False

        if 'self.validator.validate_stop_loss' in place_order_source:
            print("✅ IBAdapter.place_order() calls validate_stop_loss")
        else:
            print("❌ IBAdapter.place_order() missing validate_stop_loss call")
            success = False

    except Exception as e:
        print(f"❌ FAILED to check IB adapter: {e}")
        success = False

    # Test Alpaca adapter integration
    try:
        from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter

        import inspect
        init_source = inspect.getsource(AlpacaAdapter.__init__)

        if 'self.validator = TradingValidator()' in init_source:
            print("✅ AlpacaAdapter has TradingValidator in __init__")
        else:
            print("❌ AlpacaAdapter missing TradingValidator in __init__")
            success = False

        # Check if place_order uses validator
        place_order_source = inspect.getsource(AlpacaAdapter.place_order)
        if 'self.validator.validate_position_size' in place_order_source:
            print("✅ AlpacaAdapter.place_order() calls validate_position_size")
        else:
            print("❌ AlpacaAdapter.place_order() missing validate_position_size call")
            success = False

        if 'self.validator.validate_stop_loss' in place_order_source:
            print("✅ AlpacaAdapter.place_order() calls validate_stop_loss")
        else:
            print("❌ AlpacaAdapter.place_order() missing validate_stop_loss call")
            success = False

    except Exception as e:
        print(f"❌ FAILED to check Alpaca adapter: {e}")
        success = False

    return success


def test_stop_executor_exports():
    """Test 3: Verify StopExecutor is properly exported."""
    print("\n=== Test 3: StopExecutor Exports ===")
    try:
        from app.services.position_monitor import (
            StopExecutor,
            StopExecutionResult,
            StopType,
            PositionMonitor
        )

        print("✅ StopExecutor exported from position_monitor.__init__")
        print("✅ StopExecutionResult exported from position_monitor.__init__")
        print("✅ StopType exported from position_monitor.__init__")
        print("✅ PositionMonitor exported from position_monitor.__init__")

        # Check __all__ includes these
        from app.services.position_monitor import __all__ as exports
        required_exports = ['StopExecutor', 'StopExecutionResult', 'StopType', 'PositionMonitor']

        for export in required_exports:
            if export in exports:
                print(f"✅ '{export}' in __all__")
            else:
                print(f"❌ '{export}' NOT in __all__")
                return False

        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_position_state_model():
    """Test 4: Verify PositionState model exists and is correct."""
    print("\n=== Test 4: PositionState Model ===")

    # Check duplicate removed
    if os.path.exists('app/database/models/position_state.py'):
        print("❌ Duplicate PositionState file still exists at app/database/models/position_state.py")
        return False
    else:
        print("✅ Duplicate PositionState file removed")

    # Check model in models.py
    try:
        from app.database.models import PositionState
        print("✅ PositionState imported from app.database.models")

        # Check model attributes
        required_attrs = [
            'id', 'monitor_id', 'positions_json', 'last_sync',
            'is_active', 'version', 'created_at', 'updated_at'
        ]

        for attr in required_attrs:
            if hasattr(PositionState, attr):
                print(f"✅ PositionState.{attr} exists")
            else:
                print(f"❌ PositionState.{attr} missing")
                return False

        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_alembic_migration():
    """Test 5: Verify Alembic migration exists."""
    print("\n=== Test 5: Alembic Migration ===")

    migration_file = 'alembic/versions/001_add_position_states_table.py'

    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"✅ Migration file exists: {migration_file}")

    # Check migration content
    try:
        with open(migration_file, 'r') as f:
            content = f.read()

        checks = [
            ('def upgrade()', 'upgrade() function'),
            ('def downgrade()', 'downgrade() function'),
            ("'position_states'", 'position_states table'),
            ('op.create_table', 'create_table operation'),
            ('op.drop_table', 'drop_table operation'),
        ]

        for check_str, desc in checks:
            if check_str in content:
                print(f"✅ Migration has {desc}")
            else:
                print(f"❌ Migration missing {desc}")
                return False

        return True
    except Exception as e:
        print(f"❌ FAILED to read migration: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("CRITICAL FIXES VERIFICATION SCRIPT")
    print("=" * 70)

    results = {
        "get_sync_db() function": test_get_sync_db(),
        "TradingValidator Integration": test_trading_validator(),
        "StopExecutor Exports": test_stop_executor_exports(),
        "PositionState Model": test_position_state_model(),
        "Alembic Migration": test_alembic_migration(),
    }

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(results.values())

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Critical fixes verified successfully.")
    else:
        failed_count = sum(1 for passed in results.values() if not passed)
        print(f"⚠️  {failed_count} test(s) failed. Please review the output above.")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
