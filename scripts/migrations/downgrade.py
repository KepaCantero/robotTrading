#!/usr/bin/env python3
"""
Downgrade database to a previous migration.

WARNING: This will revert database changes and may result in data loss!

Usage:
    # Downgrade one step
    python scripts/migrations/downgrade.py

    # Downgrade to specific revision
    python scripts/migrations/downgrade.py --revision <revision_id>

    # Downgrade N steps
    python scripts/migrations/downgrade.py --steps 2

    # Show SQL only (don't execute)
    python scripts/migrations/downgrade.py --sql

Examples:
    python scripts/migrations/downgrade.py
    python scripts/migrations/downgrade.py --revision 0001
    python scripts/migrations/downgrade.py --steps 2
    python scripts/migrations/downgrade.py --sql
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Downgrade database to previous migration"
    )
    parser.add_argument(
        "--revision",
        "-r",
        help="Target revision ID (default: -1 for one step back)",
    )
    parser.add_argument(
        "--steps",
        "-s",
        type=int,
        help="Number of steps to downgrade (default: 1)",
        default=1,
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Show SQL only, don't execute",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    return parser.parse_args()


def main():
    """Run downgrade migration."""
    args = parse_args()

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    # Determine target revision
    if args.revision:
        target = args.revision
    else:
        # Downgrade N steps
        target = f"-{args.steps}"

    print(f"Downgrading database to: {target}")
    print("-" * 60)
    print("WARNING: This will revert database changes!")
    print("         Ensure you have a backup before proceeding.")
    print("-" * 60)

    # Build alembic downgrade command
    cmd = ["python", "-m", "alembic", "downgrade", target]

    if args.sql:
        cmd.append("--sql")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if args.sql or args.verbose:
            print(result.stdout)
        else:
            # Show only important lines
            for line in result.stdout.split("\n"):
                if any(
                    keyword in line.lower()
                    for keyword in ["running", "downgrade", "dropping", "done"]
                ):
                    print(line)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("-" * 60)
        print("Database downgraded successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error downgrading database: {e}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
