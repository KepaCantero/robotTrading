#!/usr/bin/env python3
"""
Test migrations on a fresh database.

This script creates a test database and runs all migrations to verify they work correctly.
"""
import os
import sys
import subprocess
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def run_command(cmd, check=True):
    """Run a command and return result."""
    print(f"{YELLOW}Running: {cmd}{RESET}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"{RED}Error: {result.stderr}{RESET}")
        sys.exit(1)
    return result


def main():
    """Test migrations on a fresh database."""
    print("=" * 60)
    print("Testing Alembic Migrations")
    print("=" * 60)

    # Get project root
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    # Test database path
    test_db_dir = root_dir / "test_migrations"
    test_db_path = test_db_dir / "test_migration.db"

    # Create test directory if needed
    test_db_dir.mkdir(exist_ok=True)

    # Remove existing test database
    if test_db_path.exists():
        print(f"{YELLOW}Removing existing test database...{RESET}")
        test_db_path.unlink()

    # Set environment variable for test database
    os.environ["ALEMBIC_DB_URL"] = f"sqlite:///{test_db_path}"

    print(f"{GREEN}Test database: {test_db_path}{RESET}")
    print("-" * 60)

    # Step 1: Check migration status before
    print(f"\n{YELLOW}1. Checking migration status (before)...{RESET}")
    result = run_command("python -m alembic current", check=False)
    print(result.stdout)

    # Step 2: Run migrations
    print(f"\n{YELLOW}2. Running migrations...{RESET}")
    result = run_command("python -m alembic upgrade head")
    print(result.stdout)

    # Step 3: Check migration status after
    print(f"\n{YELLOW}3. Checking migration status (after)...{RESET}")
    result = run_command("python -m alembic current")
    print(result.stdout)

    # Step 4: Verify database schema
    print(f"\n{YELLOW}4. Verifying database schema...{RESET}")
    import sqlite3

    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = cursor.fetchall()

    print(f"\n{GREEN}Created {len(tables)} tables:{RESET}")
    for table in tables:
        print(f"  - {table[0]}")

    # Verify alembic_version table
    cursor.execute("SELECT version_num FROM alembic_version")
    version = cursor.fetchone()
    print(f"\n{GREEN}Current migration version: {version[0] if version else 'None'}{RESET}")

    # Check some tables have data structure
    expected_tables = [
        "users",
        "portfolios",
        "trades",
        "market_data",
        "backtests",
        "alembic_version",
    ]

    print(f"\n{YELLOW}5. Verifying expected tables exist...{RESET}")
    missing_tables = []
    for expected in expected_tables:
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{expected}'"
        )
        if cursor.fetchone():
            print(f"  {GREEN}✓{RESET} {expected}")
        else:
            print(f"  {RED}✗{RESET} {expected} (MISSING)")
            missing_tables.append(expected)

    conn.close()

    # Step 5: Test rollback
    print(f"\n{YELLOW}6. Testing rollback...{RESET}")
    result = run_command("python -m alembic downgrade -1")
    print(result.stdout)

    print(f"\n{YELLOW}7. Re-applying migrations...{RESET}")
    result = run_command("python -m alembic upgrade head")
    print(result.stdout)

    # Summary
    print("\n" + "=" * 60)
    if missing_tables:
        print(f"{RED}TEST FAILED: Missing tables: {', '.join(missing_tables)}{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}ALL TESTS PASSED!{RESET}")
        print(f"\nTest database: {test_db_path}")
        print("You can inspect it with:")
        print(f"  sqlite3 {test_db_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
