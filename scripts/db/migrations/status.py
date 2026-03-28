#!/usr/bin/env python3
"""
Show current database migration status.

Usage:
    python scripts/migrations/status.py

    # Show verbose output
    python scripts/migrations/status.py --verbose
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Show database migration status")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    return parser.parse_args()


def main():
    """Show migration status."""
    args = parse_args()

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    print("Database Migration Status")
    print("=" * 60)

    # Run alembic current command
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "current"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("\nCurrent revision:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting current revision: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)

    print("\n" + "=" * 60)

    # Run alembic history command
    try:
        verbose_flag = "-v" if args.verbose else ""
        result = subprocess.run(
            ["python", "-m", "alembic", "history", verbose_flag],
            check=True,
            capture_output=True,
            text=True,
        )
        print("\nMigration history:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting history: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)

    print("\n" + "=" * 60)

    # Check for pending migrations
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "heads"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("\nLatest revision (head):")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting head revision: {e}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)


if __name__ == "__main__":
    main()
