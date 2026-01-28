#!/usr/bin/env python
"""
Verification script for database security fixes.

This script verifies that all security fixes have been properly implemented.

Usage:
    python verify_database_security_fixes.py
"""

import sys
import re
from pathlib import Path


def check_file_contains(filepath, pattern, description):
    """Check if a file contains a specific pattern."""
    try:
        content = Path(filepath).read_text()
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"✓ {description}")
            return True
        else:
            print(f"✗ {description} - NOT FOUND")
            return False
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        print(f"✗ {description} - ERROR: {e}")
        return False


def check_file_not_contains(filepath, pattern, description):
    """Check if a file does NOT contain a specific pattern."""
    try:
        content = Path(filepath).read_text()
        if not re.search(pattern, content, re.MULTILINE | re.DOTALL):
            print(f"✓ {description}")
            return True
        else:
            print(f"✗ {description} - FOUND (should not be present)")
            return False
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        print(f"✗ {description} - ERROR: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Database Security Fixes Verification")
    print("=" * 70)
    print()

    all_passed = True

    # Task 1: Connection String Logging Fix
    print("Task 1: Connection String Logging Fix")
    print("-" * 70)

    # Check database.py has sanitized logging
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/core/database.py",
        r'logger\.info\(f"Database engine created \(host=',
        "Sanitized logging with host parameter"
    )

    # Check database.py doesn't log full URL
    all_passed &= check_file_not_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/core/database.py",
        r'logger\.info\(f"Database URL: \{url_part\}"\)',
        "No unsafe logging of Database URL"
    )

    print()

    # Task 2: Database Persistence Implementation
    print("Task 2: Database Persistence Implementation")
    print("-" * 70)

    # Check position_monitor.py has json import
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/services/position_monitor/position_monitor.py",
        r'import json',
        "JSON import added for serialization"
    )

    # Check position_monitor.py has monitor_id
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/services/position_monitor/position_monitor.py",
        r'self\.monitor_id = f"monitor_',
        "monitor_id attribute added"
    )

    # Check _load_state_from_db is implemented
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/services/position_monitor/position_monitor.py",
        r'async def _load_state_from_db\(self\).*?from app\.database import get_sync_db.*?state_record = session\.query\(PositionState\)',
        "_load_state_from_db() implemented with database queries"
    )

    # Check _sync_state is implemented
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/services/position_monitor/position_monitor.py",
        r'async def _sync_state\(self\).*?positions_list = \[pos\.to_dict\(\) for pos in self\._positions\.values\(\)\]',
        "_sync_state() implemented with position serialization"
    )

    print()

    # Task 3: PositionState Model
    print("Task 3: PositionState Database Model")
    print("-" * 70)

    # Check models.py has PositionState
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/database/models.py",
        r'class PositionState\(Base\):.*?__tablename__ = ["\']position_states["\']',
        "PositionState model defined in models.py"
    )

    # Check PositionState has required columns
    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/database/models.py",
        r'monitor_id.*?Column\(String\(255\)',
        "PositionState has monitor_id column"
    )

    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/database/models.py",
        r'positions_json.*?Column\(Text',
        "PositionState has positions_json column"
    )

    all_passed &= check_file_contains(
        "/Users/kepa.cantero/Projects/algoTrading/app/database/models.py",
        r'version.*?Column\(Integer',
        "PositionState has version column"
    )

    print()

    # Additional checks
    print("Additional Verification")
    print("-" * 70)

    # Try importing the modules
    try:
        sys.path.insert(0, '/Users/kepa.cantero/Projects/algoTrading')
        from app.database.models import PositionState
        print(f"✓ PositionState model imports successfully")
        print(f"  - Table name: {PositionState.__tablename__}")
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        print(f"✗ Failed to import PositionState: {e}")
        all_passed = False

    try:
        from app.services.position_monitor.position_monitor import PositionMonitor
        print(f"✓ PositionMonitor imports successfully")
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        print(f"✗ Failed to import PositionMonitor: {e}")
        all_passed = False

    try:
        from app.core.database import get_database_engine
        print(f"✓ Database module imports successfully")
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        print(f"✗ Failed to import database module: {e}")
        all_passed = False

    print()
    print("=" * 70)

    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("=" * 70)
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
