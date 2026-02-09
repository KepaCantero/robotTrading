#!/usr/bin/env python3
"""
Create a new Alembic migration script.

Usage:
    python scripts/migrations/create_migration.py "description of migration"

Examples:
    python scripts/migrations/create_migration.py "add user preferences table"
    python scripts/migrations/create_migration.py "add index to trades table"
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    """Create a new migration."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrations/create_migration.py <message>")
        print("\nExamples:")
        print('  python scripts/migrations/create_migration.py "add user preferences table"')
        print('  python scripts/migrations/create_migration.py "add index to trades table"')
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    print(f"Creating migration: {message}")
    print("-" * 60)

    # Run alembic revision command with autogenerate
    cmd = ["python", "-m", "alembic", "revision", "--autogenerate", "-m", message]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("-" * 60)
        print("Migration created successfully!")
        print("\nNext steps:")
        print("1. Review the generated migration in app/database/migrations/versions/")
        print("2. Edit the migration if needed")
        print("3. Run: python scripts/migrations/upgrade.py")

    except subprocess.CalledProcessError as e:
        print(f"Error creating migration: {e}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
