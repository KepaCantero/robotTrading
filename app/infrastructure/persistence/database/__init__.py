"""
Database Configuration and Setup
TASK-6: Configuración de base de datos
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from sqlalchemy import MetaData, create_engine, event, text
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.shared.config.base.environment_config import get_config
from app.shared.exceptions.exceptions import raise_database_error

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()

# Global database engines
_sync_engine: object | None = None
_async_engine: object | None = None
_session_factory: sessionmaker | None = None
_async_session_factory: async_sessionmaker | None = None


class DatabaseManager:
    """Database manager for handling connections and sessions."""

    def __init__(self):
        self.config = get_config()
        self.sync_engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None

    def initialize_sync_engine(self) -> None:
        """Initialize synchronous database engine."""
        try:
            conn_string = self.config.database.connection_string
            is_sqlite = "sqlite" in conn_string.lower()

            if is_sqlite:
                # SQLite: No pooling parameters supported
                self.sync_engine = create_engine(
                    conn_string,
                    echo=self.config.debug,
                    connect_args={"check_same_thread": False},
                )
                logger.info("Synchronous database engine initialized (SQLite, no pooling)")
            else:
                # PostgreSQL: Use connection pooling
                self.sync_engine = create_engine(
                    conn_string,
                    poolclass=QueuePool,
                    pool_size=self.config.database.db_pool_size,
                    max_overflow=self.config.database.db_max_overflow,
                    pool_timeout=self.config.database.db_pool_timeout,
                    pool_pre_ping=True,  # Verify connections before use
                    echo=self.config.debug,  # Log SQL queries in debug mode
                    echo_pool=self.config.debug,  # Log pool events in debug mode
                )
                logger.info(
                    f"Synchronous database engine initialized (PostgreSQL, pool_size={self.config.database.db_pool_size})"
                )

            # Create session factory
            self.session_factory = sessionmaker(
                bind=self.sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

            # Add connection event listeners
            self._add_connection_listeners()

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            raise_database_error(
                f"Failed to initialize sync database engine: {e!s}",
                "engine_initialization",
            )

    def initialize_async_engine(self) -> None:
        """Initialize asynchronous database engine."""
        try:
            # Convert sync connection string to async
            async_connection_string = self._convert_to_async_url(
                self.config.database.connection_string
            )
            is_sqlite = "sqlite" in async_connection_string.lower()

            if is_sqlite:
                # SQLite: No pooling parameters supported
                self.async_engine = create_async_engine(
                    async_connection_string,
                    echo=self.config.debug,
                )
                logger.info("Asynchronous database engine initialized (SQLite, no pooling)")
            else:
                # PostgreSQL: Use connection pooling
                self.async_engine = create_async_engine(
                    async_connection_string,
                    poolclass=QueuePool,
                    pool_size=self.config.database.db_pool_size,
                    max_overflow=self.config.database.db_max_overflow,
                    pool_timeout=self.config.database.db_pool_timeout,
                    pool_pre_ping=True,
                    echo=self.config.debug,
                    echo_pool=self.config.debug,
                )
                logger.info(
                    f"Asynchronous database engine initialized (PostgreSQL, pool_size={self.config.database.db_pool_size})"
                )

            # Create async session factory
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            raise_database_error(
                f"Failed to initialize async database engine: {e!s}",
                "async_engine_initialization",
            )

    def _convert_to_async_url(self, sync_url: str) -> str:
        """Convert synchronous database URL to asynchronous."""
        if sync_url.startswith("postgresql://"):
            return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if sync_url.startswith("postgresql+psycopg2://"):
            return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        return sync_url

    def _add_connection_listeners(self) -> None:
        """Add database connection event listeners."""

        @event.listens_for(self.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set database connection parameters."""
            if "postgresql" in str(self.sync_engine.url):
                # PostgreSQL specific settings
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("SET timezone TO 'UTC'")
                    cursor.execute("SET statement_timeout TO '30s'")
                    cursor.execute("SET lock_timeout TO '10s'")

        @event.listens_for(self.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout."""
            logger.debug("Database connection checked out")

        @event.listens_for(self.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin."""
            logger.debug("Database connection checked in")

    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            if not self.sync_engine:
                self.initialize_sync_engine()

            Base.metadata.create_all(bind=self.sync_engine)
            logger.info("Database tables created successfully")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            raise_database_error(f"Failed to create database tables: {e!s}", "create_tables")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        try:
            if not self.sync_engine:
                self.initialize_sync_engine()

            Base.metadata.drop_all(bind=self.sync_engine)
            logger.info("Database tables dropped successfully")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            raise_database_error(f"Failed to drop database tables: {e!s}", "drop_tables")

    def get_sync_session(self) -> Session:
        """Get synchronous database session."""
        if not self.session_factory:
            self.initialize_sync_engine()

        return self.session_factory()

    def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session."""
        if not self.async_session_factory:
            self.initialize_async_engine()

        return self.async_session_factory()

    def close_connections(self) -> None:
        """Close all database connections."""
        try:
            if self.sync_engine:
                self.sync_engine.dispose()
                logger.info("Synchronous database connections closed")

            if self.async_engine:
                self.async_engine.sync_engine.dispose()
                logger.info("Asynchronous database connections closed")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Error closing database connections: {e}")

    async def close_connections_async(self) -> None:
        """Close all database connections (async-safe)."""
        try:
            if self.sync_engine:
                self.sync_engine.dispose()
                logger.info("Synchronous database connections closed")

            if self.async_engine:
                await self.async_engine.dispose()
                logger.info("Asynchronous database connections closed")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance (lazy initialization)
_db_manager: DatabaseManager | None = None


def _get_db_manager() -> DatabaseManager:
    """Lazily create and cache the DatabaseManager singleton.

    Deferring instantiation avoids triggering config loading (which requires
    environment variables like SECRET_KEY) at import time, preventing import
    failures in tests and other modules that only need symbols from this module.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Dependency functions for FastAPI
@contextlib.contextmanager
def get_sync_db() -> Session:
    """Get synchronous database session for FastAPI dependency injection."""
    session = _get_db_manager().get_sync_session()
    try:
        yield session
    finally:
        session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session for FastAPI dependency injection."""
    session = _get_db_manager().get_async_session()
    try:
        yield session
    finally:
        await session.close()


# Database initialization functions
def initialize_database() -> None:
    """Initialize database with all engines and create tables."""
    try:
        logger.info("Initializing database...")

        # Initialize engines
        mgr = _get_db_manager()
        mgr.initialize_sync_engine()
        mgr.initialize_async_engine()

        # Create tables
        mgr.create_tables()

        logger.info("Database initialization completed successfully")

    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def initialize_database_async() -> None:
    """Initialize database for async operations."""
    try:
        logger.info("Initializing async database...")

        # Initialize async engine
        _get_db_manager().initialize_async_engine()

        logger.info("Async database initialization completed successfully")

    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"Async database initialization failed: {e}")
        raise


# Database health check functions
def check_database_health() -> bool:
    """Check database health."""
    try:
        session = _get_db_manager().get_sync_session()
        try:
            # Simple query to check connection
            session.execute(text("SELECT 1"))
            return True
        finally:
            session.close()
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def check_database_health_async() -> bool:
    """Check database health asynchronously."""
    try:
        session = _get_db_manager().get_async_session()
        try:
            # Simple query to check connection
            await session.execute(text("SELECT 1"))
            return True
        finally:
            await session.close()
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"Async database health check failed: {e}")
        return False


# Database utility functions
def get_database_url() -> str:
    """Get database connection URL."""
    return get_config().database.connection_string


def get_database_config() -> dict:
    """Get database configuration as dictionary."""
    config = get_config().database
    return {
        "host": config.db_host,
        "port": config.db_port,
        "name": config.db_name,
        "user": config.db_user,
        "pool_size": config.db_pool_size,
        "max_overflow": config.db_max_overflow,
        "pool_timeout": config.db_pool_timeout,
        "ssl_mode": config.db_ssl_mode,
    }


# Context managers for database sessions
class DatabaseSession:
    """Context manager for database sessions."""

    def __init__(self, async_mode: bool = False):
        self.async_mode = async_mode
        self.session = None

    def __enter__(self):
        if self.async_mode:
            raise RuntimeError("Use async context manager for async sessions")
        self.session = _get_db_manager().get_sync_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()

    async def __aenter__(self):
        if not self.async_mode:
            raise RuntimeError("Use sync context manager for sync sessions")
        self.session = _get_db_manager().get_async_session()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
            await self.session.close()


# Database transaction decorators
def database_transaction(func):
    """Decorator for database transactions."""

    def wrapper(*args, **kwargs):
        with DatabaseSession() as session:
            return func(session, *args, **kwargs)

    return wrapper


def async_database_transaction(func):
    """Decorator for async database transactions."""

    async def wrapper(*args, **kwargs):
        async with DatabaseSession(async_mode=True) as session:
            return await func(session, *args, **kwargs)

    return wrapper


# Backward compatibility functions for tests
def get_session_factory():
    """Get the session factory for backward compatibility."""
    mgr = _get_db_manager()
    if not mgr.session_factory:
        mgr.initialize_sync_engine()
    return mgr.session_factory


def close_database():
    """Close database connections for backward compatibility."""
    _get_db_manager().close_connections()


async def init_database():
    """Initialize database connections for application startup."""
    mgr = _get_db_manager()
    mgr.initialize_sync_engine()
    try:
        mgr.initialize_async_engine()
    except Exception as e:
        logger.warning(f"Async engine init skipped: {e}")


def get_db_transaction():
    """Get database transaction context for backward compatibility."""
    return DatabaseSession()
