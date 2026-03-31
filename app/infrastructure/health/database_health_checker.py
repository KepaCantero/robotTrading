from __future__ import annotations

"""Database health checker for infrastructure layer."""


import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class DatabaseHealthCheckerProtocol(Protocol):
    """Protocol for database health checking."""

    def check_health(
        self, db_path: str | None = None, timeout: float | None = None
    ) -> dict[str, Any]:
        """Check database connectivity and integrity."""
        ...


@dataclass
class DatabaseHealthConfig:
    """Configuration for database health checker."""

    db_path: str
    timeout: float = 5.0


class SQLiteDatabaseHealthChecker:
    """SQLite implementation of database health checker."""

    def __init__(self, config: DatabaseHealthConfig) -> None:
        """Initialize with configuration."""
        self.config = config
        logger.debug(
            "SQLiteDatabaseHealthChecker initialized",
            extra={"db_path": config.db_path, "timeout": config.timeout},
        )

    def check_health(
        self, db_path: str | None = None, timeout: float | None = None
    ) -> dict[str, Any]:
        """Check database connectivity and integrity."""
        path = db_path or self.config.db_path
        conn_timeout = timeout or self.config.timeout

        logger.debug(
            "Starting database health check", extra={"db_path": path, "timeout": conn_timeout}
        )

        try:
            # Check file exists
            if not Path(path).exists():
                logger.warning(
                    "Database file not found", extra={"db_path": path, "health_status": "unhealthy"}
                )
                return {
                    "status": "unhealthy",
                    "message": f"Database file not found: {path}",
                }

            # Check file size
            file_size = Path(path).stat().st_size
            if file_size == 0:
                logger.warning(
                    "Database file is empty", extra={"db_path": path, "health_status": "unhealthy"}
                )
                return {"status": "unhealthy", "message": "Database file is empty"}

            # Connect and check tables
            with self._get_connection(path, conn_timeout) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                logger.info(
                    "Database health check passed",
                    extra={
                        "db_path": path,
                        "health_status": "healthy",
                        "table_count": len(tables),
                        "file_size_mb": round(file_size / (1024 * 1024), 5),
                    },
                )

                return {
                    "status": "healthy",
                    "message": f"Database OK ({len(tables)} tables)",
                    "file_size_mb": round(file_size / (1024 * 1024), 5),
                }

        except sqlite3.Error as e:
            logger.error(
                "Database error during health check",
                extra={"db_path": path, "error": str(e), "health_status": "unhealthy"},
            )
            return {"status": "unhealthy", "message": f"Database error: {e!s}"}
        except Exception as e:
            logger.error(
                "Unexpected error during health check",
                extra={"db_path": path, "error": str(e), "health_status": "unhealthy"},
            )
            return {"status": "unhealthy", "message": f"Unexpected error: {e!s}"}

    def _get_connection(self, db_path: str, timeout: float) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(db_path, timeout=timeout)


# Factory
class DatabaseHealthCheckerFactory:
    """Factory for creating database health checkers."""

    @staticmethod
    def create_sqlite_checker(db_path: str, timeout: float = 5.0) -> SQLiteDatabaseHealthChecker:
        """Create SQLite health checker."""
        logger.debug(
            "Creating SQLite health checker", extra={"db_path": db_path, "timeout": timeout}
        )
        config = DatabaseHealthConfig(db_path=db_path, timeout=timeout)
        return SQLiteDatabaseHealthChecker(config)
