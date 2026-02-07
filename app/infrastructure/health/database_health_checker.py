"""Database health checker for infrastructure layer."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Protocol


class DatabaseHealthCheckerProtocol(Protocol):
    """Protocol for database health checking."""

    def check_health(
        self, db_path: str | None = None, timeout: float | None = None
    ) -> Dict[str, Any]:
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

    def check_health(
        self, db_path: str | None = None, timeout: float | None = None
    ) -> Dict[str, Any]:
        """Check database connectivity and integrity."""
        path = db_path or self.config.db_path
        conn_timeout = timeout or self.config.timeout

        try:
            # Check file exists
            if not Path(path).exists():
                return {
                    "status": "unhealthy",
                    "message": f"Database file not found: {path}",
                }

            # Check file size
            file_size = Path(path).stat().st_size
            if file_size == 0:
                return {"status": "unhealthy", "message": "Database file is empty"}

            # Connect and check tables
            with self._get_connection(path, conn_timeout) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                return {
                    "status": "healthy",
                    "message": f"Database OK ({len(tables)} tables)",
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                }

        except sqlite3.Error as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Unexpected error: {str(e)}"}

    def _get_connection(self, db_path: str, timeout: float) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(db_path, timeout=timeout)


# Factory
class DatabaseHealthCheckerFactory:
    """Factory for creating database health checkers."""

    @staticmethod
    def create_sqlite_checker(db_path: str, timeout: float = 5.0) -> SQLiteDatabaseHealthChecker:
        """Create SQLite health checker."""
        config = DatabaseHealthConfig(db_path=db_path, timeout=timeout)
        return SQLiteDatabaseHealthChecker(config)
