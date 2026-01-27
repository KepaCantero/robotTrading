"""
Alembic Environment Configuration for AlgoTrading Platform

This module is run by Alembic to configure the migration environment.
It provides the database connection and metadata for migration generation.
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import Base and metadata from app.database
from app.database import Base, metadata
from app.core.config import get_settings

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
    url = config.get_main_option("sqlalchemy.url")
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


def do_run_migrations(connection):
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Support both SQLite and PostgreSQL
        render_as_batch=True,  # Required for SQLite support
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    # For async migrations, we need to convert the URL to sync format temporarily
    # because Alembic's migration operations are synchronous
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    # Check if using async driver
    db_url = config.get_main_option("sqlalchemy.url")
    is_async = "asyncpg" in db_url or "aiosqlite" in db_url

    if is_async:
        # Run async migrations
        asyncio.run(run_async_migrations())
    else:
        # Run sync migrations
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
