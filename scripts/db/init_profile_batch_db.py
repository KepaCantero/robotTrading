#!/usr/bin/env python
"""
Initialize Profile Batch Backtester Database

This script creates and initializes the database for the ProfileBatchBacktester.

Usage:
    python scripts/init_profile_batch_db.py
    python scripts/init_profile_batch_db.py --db-url postgresql://user:pass@localhost/profiles
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backtesting.profile_batch_backtester import Base


def init_database(db_url: str, drop_existing: bool = False):
    """
    Initialize the database.

    Args:
        db_url: Database connection URL
        drop_existing: Whether to drop existing tables first
    """
    print(f"Initializing database: {db_url}")

    # Create engine
    engine = create_engine(db_url, echo=True)

    # Drop existing tables if requested
    if drop_existing:
        print("\nDropping existing tables...")
        Base.metadata.drop_all(engine)

    # Create all tables
    print("\nCreating tables...")
    Base.metadata.create_all(engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Verify tables were created
    tables = engine.table_names()
    print(f"\nCreated tables: {', '.join(tables)}")

    # Check if profile_results table exists
    if "profile_results" in tables:
        print("\n✅ profile_results table created successfully")

        # Get table info
        from sqlalchemy import inspect

        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("profile_results")]
        print(f"\nColumns in profile_results ({len(columns)}):")
        for col in columns:
            print(f"  - {col}")

        # Get indexes
        indexes = inspector.get_indexes("profile_results")
        if indexes:
            print(f"\nIndexes on profile_results ({len(indexes)}):")
            for idx in indexes:
                print(f"  - {idx['name']}: {', '.join(idx['column_names'])}")

    session.close()

    print("\n✅ Database initialization complete!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Profile Batch Backtester Database"
    )

    parser.add_argument(
        "--db-url",
        type=str,
        default="sqlite:///results/profile_batch_results.db",
        help="Database connection URL (default: sqlite:///results/profile_batch_results.db)"
    )

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating new ones"
    )

    parser.add_argument(
        "--postgres",
        action="store_true",
        help="Use PostgreSQL (requires: --db-url postgresql://user:pass@host/db)"
    )

    args = parser.parse_args()

    # Set default PostgreSQL URL if --postgres flag is used
    if args.postgres and not args.db_url.startswith("postgresql"):
        args.db_url = "postgresql://postgres:postgres@localhost:5432/profile_batch_results"

    try:
        init_database(args.db_url, args.drop)

    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
