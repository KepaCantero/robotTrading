"""
Database configuration and session management for AlgoTrading MVP.

This module provides async PostgreSQL database connection using SQLAlchemy 2.0
with asyncpg driver, including session management and connection pooling.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import MetaData
from sqlalchemy.exc import (
    ArgumentError,
    DatabaseError,
    DisconnectionError,
    IntegrityError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.shared.config.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy metadata configuration
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides metadata configuration and common functionality
    for all database models in the AlgoTrading system.
    """

    metadata = metadata


# Global variables for database engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_engine() -> AsyncEngine:
    """
    Get or create the database engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance

    Raises:
        RuntimeError: If engine cannot be created
    """
    global _engine

    if _engine is None:
        settings = get_settings()

        try:
            db_url = settings.get_database_url_async()

            # Check if using SQLite (doesn't support connection pooling)
            is_sqlite = "sqlite" in db_url.lower()

            if is_sqlite:
                # SQLite: No pooling parameters supported
                _engine = create_async_engine(
                    db_url,
                    echo=settings.database_echo,
                    future=True,  # Use SQLAlchemy 2.0 style
                )
                logger.info("Database engine created (SQLite, no pooling)")
            else:
                # PostgreSQL: Use connection pooling
                _engine = create_async_engine(
                    db_url,
                    echo=settings.database_echo,
                    poolclass=QueuePool if settings.is_production() else NullPool,
                    pool_size=settings.database_pool_size,
                    max_overflow=settings.database_max_overflow,
                    pool_pre_ping=True,  # Verify connections before use
                    pool_recycle=3600,  # Recycle connections every hour
                    future=True,  # Use SQLAlchemy 2.0 style
                )
                # Sanitize connection string - only log host, not credentials
                # SECURITY: Password redaction verified - url_part extracts only host portion after '@'
                # If database_url contains "postgresql://user:PASSWORD@host:port/db",
                # splitting on '@' and taking [1] gives us "host:port/db" without credentials
                url_part = (
                    settings.database_url.split("@")[1]
                    if "@" in settings.database_url
                    else "localhost"
                )
                # SECURITY VERIFIED: url_part contains only host:port/db, password is excluded
                logger.info(
                    f"Database engine created (host={url_part}, pool_size={settings.database_pool_size})"
                )

        except (ArgumentError, OperationalError, SQLAlchemyTimeoutError, ValueError) as e:
            logger.error(f"Failed to create database engine: {e}")
            raise RuntimeError(f"Database engine creation failed: {e}") from e

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create the session factory.

    Returns:
        async_sessionmaker[AsyncSession]: SQLAlchemy async session factory

    Raises:
        RuntimeError: If session factory cannot be created
    """
    global _session_factory

    if _session_factory is None:
        try:
            engine = get_database_engine()
            _async_session = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Prevent lazy loading issues
                autoflush=True,  # Auto-flush changes
                autocommit=False,  # Use explicit transactions
            )
            _session_factory = _async_session

            logger.info("Session factory created successfully")

        except (ArgumentError, OperationalError, ValueError) as e:
            logger.error(f"Failed to create session factory: {e}")
            raise RuntimeError(f"Session factory creation failed: {e}") from e

    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    This function provides a dependency injection pattern for FastAPI endpoints.
    It creates a new database session for each request and ensures proper cleanup.

    Yields:
        AsyncSession: SQLAlchemy async session

    Example:
        ```python
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(User))
            return result.scalars().all()
        ```
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except (DatabaseError, OperationalError, SQLAlchemyTimeoutError, DisconnectionError) as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions.

    Provides a transactional context that automatically commits on success
    and rolls back on failure.

    Yields:
        AsyncSession: SQLAlchemy async session within transaction

    Example:
        ```python
        async with get_db_transaction() as db:
            user = User(name="John", email="john@example.com")
            db.add(user)
            # Transaction will be committed automatically
        ```
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
            logger.debug("Database transaction committed successfully")
        except (DatabaseError, OperationalError, IntegrityError, SQLAlchemyTimeoutError) as e:
            logger.error(f"Database transaction error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize the database.

    Creates all tables defined in the Base metadata.
    This function should be called during application startup.

    Raises:
        RuntimeError: If database initialization fails
    """
    try:
        engine = get_database_engine()

        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    except (DatabaseError, OperationalError, SQLAlchemyTimeoutError) as e:
        logger.error(f"Database initialization failed: {e}")
        raise RuntimeError(f"Database initialization failed: {e}") from e


async def close_database() -> None:
    """
    Close database connections.

    This function should be called during application shutdown
    to properly close all database connections.
    """
    # # global _engine  # F824 removed, _session_factory
    # F824 removed
    try:
        if _engine:
            await _engine.dispose()

        logger.info("Database connections closed successfully")

    except (DatabaseError, OperationalError) as e:
        logger.error(f"Error closing database connections: {e}")


async def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection is working, False otherwise
    """
    try:
        engine = get_database_engine()

        async with engine.begin() as conn:
            # Simple query to test connection
            result = await conn.execute("SELECT 1")
            result.fetchone()

        logger.debug("Database connection check successful")
        return True

    except (OperationalError, DatabaseError, SQLAlchemyTimeoutError) as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_database_info() -> dict:
    """
    Get database connection information.

    Returns:
        dict: Database connection information including URL, pool status, etc.
    """
    try:
        settings = get_settings()
        engine = get_database_engine()

        # Get pool information
        pool = engine.pool
        pool_info = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }

        return {
            "url": (
                settings.database_url.split("@")[1] if "@" in settings.database_url else "localhost"
            ),
            "echo": settings.database_echo,
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_status": pool_info,
            "is_production": settings.is_production(),
        }

    except (OperationalError, AttributeError, KeyError) as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


# Convenience functions for common database operations
async def execute_query(query: str, params: dict | None = None) -> list:
    """
    Execute a raw SQL query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        list: Query results
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            result = await session.execute(query, params or {})
            return result.fetchall()
        except (DatabaseError, OperationalError, IntegrityError) as e:
            logger.error(f"Query execution failed: {e}")
            raise


async def execute_scalar(query: str, params: dict | None = None) -> object:
    """
    Execute a scalar query (returns single value).

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Scalar result
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            result = await session.execute(query, params or {})
            return result.scalar()
        except (DatabaseError, OperationalError, IntegrityError) as e:
            logger.error(f"Scalar query execution failed: {e}")
            raise


@contextmanager
def get_sync_db() -> Session:
    """
    Get a synchronous database session.

    Use this for non-async operations like PositionMonitor persistence.

    Yields:
        Session: SQLAlchemy synchronous session

    Example:
        ```python
        with get_sync_db() as session:
            result = session.execute(query)
            session.commit()
        ```
    """
    engine = get_database_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except (DatabaseError, OperationalError, IntegrityError):
        session.rollback()
        raise
    finally:
        session.close()


# Export commonly used items
__all__ = [
    "Base",
    "check_database_connection",
    "close_database",
    "execute_query",
    "execute_scalar",
    "get_database_engine",
    "get_database_info",
    "get_db_session",
    "get_db_transaction",
    "get_session_factory",
    "get_sync_db",
    "init_database",
    "metadata",
]
