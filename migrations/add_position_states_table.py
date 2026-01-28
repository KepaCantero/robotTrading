"""
Database Migration: Add position_states table

This migration creates the position_states table for persisting
position monitoring state to enable recovery after system restart.

Run: python -m migrations.add_position_states_table
"""

import logging
from sqlalchemy import text

from app.database import Base, db_manager
from app.database.models import PositionState

logger = logging.getLogger(__name__)


def upgrade():
    """
    Create the position_states table and indexes.
    """
    try:
        logger.info("Starting migration: Add position_states table")

        # Initialize database engine
        db_manager.initialize_sync_engine()

        # Create the table
        PositionState.__table__.create(db_manager.sync_engine, checkfirst=True)

        logger.info("✓ position_states table created successfully")

        # Verify table creation
        with db_manager.get_sync_session() as session:
            result = session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'position_states'"
            ))
            count = result.scalar()
            if count > 0:
                logger.info("✓ Migration verification successful")
            else:
                raise Exception("Table creation verification failed")

        logger.info("Migration completed successfully")
        return True

    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def downgrade():
    """
    Drop the position_states table.
    """
    try:
        logger.info("Starting rollback: Drop position_states table")

        # Initialize database engine
        db_manager.initialize_sync_engine()

        # Drop the table
        PositionState.__table__.drop(db_manager.sync_engine, checkfirst=True)

        logger.info("✓ position_states table dropped successfully")
        logger.info("Rollback completed successfully")
        return True

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        success = downgrade()
    else:
        success = upgrade()

    sys.exit(0 if success else 1)
