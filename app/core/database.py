"""
Database configuration and session management for AlgoTrading MVP.

This module provides async PostgreSQL database connection using SQLAlchemy 2.0
with asyncpg driver, including session management and connection pooling.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from .config import get_settings

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
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


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
            # Create async engine with connection pooling
            _engine = create_async_engine(
                settings.get_database_url_async(),
                echo=settings.database_echo,
                poolclass=QueuePool if settings.is_production() else NullPool,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,  # Recycle connections every hour
                future=True,  # Use SQLAlchemy 2.0 style
            )

            url_part = (
                settings.database_url.split("@")[1] if "@" in settings.database_url else "localhost"
            )
            logger.info(f"Database engine created successfully. URL: {url_part}")

        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise RuntimeError(f"Database engine creation failed: {e}")

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

            _session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Prevent lazy loading issues
                autoflush=True,  # Auto-flush changes
                autocommit=False,  # Use explicit transactions
            )

            logger.info("Session factory created successfully")

        except Exception as e:
            logger.error(f"Failed to create session factory: {e}")
            raise RuntimeError(f"Session factory creation failed: {e}")

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
        except Exception as e:
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
        except Exception as e:
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

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise RuntimeError(f"Database initialization failed: {e}")


async def close_database() -> None:
    """
    Close database connections.

    This function should be called during application shutdown
    to properly close all database connections.
    """
    global _engine, _session_factory

    try:
        if _engine:
            await _engine.dispose()
            _engine = None

        _session_factory = None

        logger.info("Database connections closed successfully")

    except Exception as e:
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

    except Exception as e:
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

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


# Convenience functions for common database operations
async def execute_query(query: str, params: Optional[dict] = None) -> list:
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
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise


async def execute_scalar(query: str, params: Optional[dict] = None) -> any:
    """
    Execute a scalar query (returns single value).

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        any: Scalar result
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            result = await session.execute(query, params or {})
            return result.scalar()
        except Exception as e:
            logger.error(f"Scalar query execution failed: {e}")
            raise


# Export commonly used items
__all__ = [
    "Base",
    "metadata",
    "get_database_engine",
    "get_session_factory",
    "get_db_session",
    "get_db_transaction",
    "init_database",
    "close_database",
    "check_database_connection",
    "get_database_info",
    "execute_query",
    "execute_scalar",
]
