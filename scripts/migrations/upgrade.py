#!/usr/bin/env python3
"""
Upgrade database to the latest migration.

Usage:
    # Upgrade to latest
    python scripts/migrations/upgrade.py

    # Upgrade to specific revision
    python scripts/migrations/upgrade.py --revision <revision_id>

    # Show SQL only (don't execute)
    python scripts/migrations/upgrade.py --sql

Examples:
    python scripts/migrations/upgrade.py
    python scripts/migrations/upgrade.py --revision 0002
    python scripts/migrations/upgrade.py --sql
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Upgrade database to latest or specific migration"
    )
    parser.add_argument(
        "--revision",
        "-r",
        help="Target revision ID (default: head)",
        default="head",
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
    """Run upgrade migration."""
    args = parse_args()

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    print(f"Upgrading database to: {args.revision}")
    print("-" * 60)

    # Build alembic upgrade command
    cmd = ["python", "-m", "alembic", "upgrade", args.revision]

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
                    for keyword in ["running", "upgrade", "creating", "done"]
                ):
                    print(line)

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("-" * 60)
        print("Database upgraded successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error upgrading database: {e}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
