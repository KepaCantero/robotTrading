#!/usr/bin/env python3
"""
Stamp database with a specific revision without running migrations.

Use this when you need to mark a database as being at a specific
revision without actually running the migrations (e.g., when
the database was created manually or from a backup).

Usage:
    # Stamp database as being at latest revision
    python scripts/migrations/stamp.py --revision head

    # Stamp database as being at specific revision
    python scripts/migrations/stamp.py --revision 0002

Examples:
    python scripts/migrations/stamp.py --revision head
    python scripts/migrations/stamp.py --revision 0001
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Stamp database with specific revision")
    parser.add_argument(
        "--revision",
        "-r",
        required=True,
        help="Target revision ID (or 'head')",
    )
    return parser.parse_args()


def main():
    """Stamp database with revision."""
    args = parse_args()

    # Get project root directory
    root_dir = Path(__file__).parent.parent.parent
    os.chdir(root_dir)

    print(f"Stamping database with revision: {args.revision}")
    print("-" * 60)
    print("WARNING: This marks the database as being at the specified")
    print("         revision without actually running migrations!")
    print("-" * 60)

    # Build alembic stamp command
    cmd = ["python", "-m", "alembic", "stamp", args.revision]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("-" * 60)
        print("Database stamped successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error stamping database: {e}", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
