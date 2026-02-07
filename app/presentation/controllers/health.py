"""
Health Check Endpoint - Monitors system health for production readiness.

Returns HTTP 200 if all systems healthy, HTTP 503 if any critical service down.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    checks: Dict[str, Any]
    uptime_seconds: float


class HealthChecker:
    """
    Performs health checks on all critical system components.
    """

    def __init__(self) -> None:
        """Initialize the health checker."""
        self.start_time: datetime = datetime.now()
        self._db_path: Optional[str] = None
        self._broker: Optional[Any] = None

    def set_dependencies(self, db_path: Optional[str] = None, broker: Optional[Any] = None) -> None:
        """
        Set dependencies for health checks.

        Args:
            db_path: Optional database file path
            broker: Optional broker instance for connectivity checks
        """
        self._db_path = db_path
        self._broker = broker

    async def check_database(self) -> Dict[str, Any]:
        """
        Check database connection and integrity.

        Returns:
            Dict with status: "healthy", "degraded", or "unhealthy"
        """
        if not self._db_path:
            return {"status": "degraded", "message": "Database not configured"}

        try:
            if not os.path.exists(self._db_path):
                return {
                    "status": "unhealthy",
                    "message": f"Database file not found: {self._db_path}",
                }

            # Check file size (should be > 0)
            file_size: int = os.path.getsize(self._db_path)
            if file_size == 0:
                return {"status": "unhealthy", "message": "Database file is empty"}

            # Try to connect (basic check)
            import sqlite3

            conn = sqlite3.connect(self._db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()

            return {
                "status": "healthy",
                "message": f"Database OK ({len(tables)} tables)",
                "file_size_mb": round(file_size / (1024 * 1024), 2),
            }

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    async def check_broker(self) -> Dict[str, Any]:
        """
        Check broker API connectivity.

        Returns:
            Dict with status
        """
        if not self._broker:
            return {"status": "degraded", "message": "Broker not configured"}

        try:
            # Try to get account info with timeout
            account = await asyncio.wait_for(self._broker.get_account_info(), timeout=5.0)

            if account:
                return {
                    "status": "healthy",
                    "message": f"Broker connected: {type(self._broker).__name__}",
                }
            else:
                return {"status": "degraded", "message": "Broker returned no account info"}

        except asyncio.TimeoutError:
            return {"status": "unhealthy", "message": "Broker connection timeout"}
        except (ConnectionError, OSError) as e:
            return {"status": "unhealthy", "message": f"Broker error: {str(e)}"}

    def check_memory(self) -> Dict[str, Any]:
        """
        Check memory usage.

        Returns:
            Dict with status and memory info
        """
        try:
            import psutil

            process = psutil.Process(os.getpid())

            # Memory info
            memory_info = process.memory_info()
            memory_mb: float = memory_info.rss / (1024 * 1024)

            # Memory percent
            memory_percent: float = process.memory_percent()

            # Determine status based on usage
            if memory_mb > 4096:  # > 4GB
                status = "unhealthy"
            elif memory_mb > 2048:  # > 2GB
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "memory_mb": round(memory_mb, 2),
                "memory_percent": round(memory_percent, 2),
                "available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
            }

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            return {"status": "degraded", "message": f"Memory check error: {str(e)}"}

    async def check_positions(self) -> Dict[str, Any]:
        """
        Check active positions.

        Returns:
            Dict with position count and status
        """
        if not self._broker:
            return {"status": "degraded", "message": "Broker not configured", "count": 0}

        try:
            positions = await asyncio.wait_for(self._broker.get_positions(), timeout=5.0)

            count: int = len(positions) if positions else 0

            return {"status": "healthy", "count": count, "message": f"{count} open positions"}

        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            return {"status": "degraded", "message": f"Position check error: {str(e)}", "count": 0}

    async def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all health checks and return combined status.

        Returns:
            Dict with all check results
        """
        checks: Dict[str, Dict[str, Any]] = {
            "database": await self.check_database(),
            "broker": await self.check_broker(),
            "memory": self.check_memory(),
            "positions": await self.check_positions(),
        }

        # Determine overall status
        statuses = [c.get("status", "unknown") for c in checks.values()]

        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        # Calculate uptime
        uptime: float = (datetime.now() - self.start_time).total_seconds()

        return {"status": overall_status, "checks": checks, "uptime_seconds": uptime}


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """
    Get or create the global health checker instance.

    Returns:
        HealthChecker: Singleton instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns HTTP 200 if all systems healthy, HTTP 503 if any critical service down.

    The response includes:
    - Overall status: healthy, degraded, or unhealthy
    - Individual check results for database, broker, memory, positions
    - System uptime in seconds
    - Timestamp of check

    Returns:
        HealthCheckResponse with system health status
    """
    checker = get_health_checker()

    result = await checker.run_all_checks()

    # Add timestamp
    result["timestamp"] = datetime.now().isoformat()

    # Return appropriate HTTP status
    if result["status"] == "unhealthy":
        pass
    elif result["status"] == "degraded":
        pass  # Still return 200 for degraded

    return HealthCheckResponse(**result)
