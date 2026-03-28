"""
Alembic Environment Configuration for AlgoTrading Platform

This module is run by Alembic to configure the migration environment.
It provides the database connection and metadata for migration generation.
"""

import asyncio
import logging
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import Base and metadata from app.infrastructure.persistence.database
from app.infrastructure.persistence import Base

from app.shared.config.config import get_settings

# Configure logger for migration operations
logger = logging.getLogger(__name__)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings
# Override sqlalchemy.url if ALEMBIC_DB_URL environment variable is set
alembic_db_url = os.environ.get("ALEMBIC_DB_URL")
if alembic_db_url:
    config.set_main_option("sqlalchemy.url", alembic_db_url)
else:
    # Use the sync URL from settings (Alembic doesn't support async URLs directly)
    settings = get_settings()
    sync_url = settings.get_database_url_sync()
    config.set_main_option("sqlalchemy.url", sync_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    try:
        logger.info("Starting offline migration")
        url = config.get_main_option("sqlalchemy.url")

        if not url:
            logger.error("Database URL not configured for offline migration")
            raise ValueError("sqlalchemy.url is not configured in Alembic config")

        logger.info(f"Offline migration URL: {url[:20]}...")  # Log only partial URL for security
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            # Support both SQLite and PostgreSQL
            render_as_batch=True,  # Required for SQLite support
        )

        with context.begin_transaction():
            context.run_migrations()

        logger.info("Offline migration completed successfully")

    except Exception as e:
        logger.error(
            "Offline migration failed",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


def do_run_migrations(connection):
    """Run migrations with the given connection."""
    try:
        logger.info("Configuring migration context")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Support both SQLite and PostgreSQL
            render_as_batch=True,  # Required for SQLite support
        )

        logger.info("Running database migrations")
        with context.begin_transaction():
            context.run_migrations()

        logger.info("Database migrations completed successfully")

    except SQLAlchemyError as e:
        logger.error(
            "Database migration failed with SQLAlchemy error",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during migration execution",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


async def run_async_migrations():
    """Run migrations in async mode."""
    connectable = None
    connection = None
    try:
        logger.info("Starting async migrations")
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

        logger.info("Creating async database engine for migrations")
        # For async migrations, we need to convert the URL to sync format temporarily
        # because Alembic's migration operations are synchronous
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        logger.info("Establishing async connection")
        connection = await connectable.connect()
        logger.info("Running migrations in async mode")
        await connection.run_sync(do_run_migrations)

        logger.info("Async migrations completed successfully")

    except SQLAlchemyError as e:
        logger.error(
            "Async migration failed with database error",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise
    except asyncio.TimeoutError as e:
        logger.error("Async migration timed out", exc_info=True, extra={"error_message": str(e)})
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during async migration",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise
    finally:
        if connection is not None:
            try:
                logger.info("Closing async connection")
                await connection.close()
            except Exception as e:
                logger.error(
                    "Error closing async connection", exc_info=True, extra={"error_message": str(e)}
                )
        if connectable is not None:
            try:
                logger.info("Disposing async engine")
                await connectable.dispose()
            except Exception as e:
                logger.error(
                    "Error disposing async engine", exc_info=True, extra={"error_message": str(e)}
                )


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    try:
        logger.info("Starting online migration")
        # Check if using async driver
        db_url = config.get_main_option("sqlalchemy.url")

        if db_url is None:
            logger.error("Database URL not configured for online migration")
            raise ValueError("sqlalchemy.url is not configured in Alembic config")

        is_async = "asyncpg" in db_url or "aiosqlite" in db_url

        if is_async:
            logger.info("Detected async driver, running async migrations")
            # Run async migrations
            asyncio.run(run_async_migrations())
        else:
            logger.info("Detected sync driver, running sync migrations")
            # Run sync migrations
            connectable = engine_from_config(
                config.get_section(config.config_ini_section),
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )

            logger.info("Establishing sync database connection")
            with connectable.connect() as connection:
                do_run_migrations(connection)

            logger.info("Disposing sync engine")
            connectable.dispose()

        logger.info("Online migration completed successfully")

    except SQLAlchemyError as e:
        logger.error(
            "Online migration failed with database error",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during online migration",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
