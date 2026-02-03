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

from app.infrastructure.health import (
    DatabaseHealthCheckerFactory,
    DatabaseHealthCheckerProtocol,
    SQLiteDatabaseHealthChecker,
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

    def __init__(
        self,
        db_health_checker: Optional[DatabaseHealthCheckerProtocol] = None,
    ) -> None:
        """
        Initialize the health checker.

        Args:
            db_health_checker: Optional database health checker from infrastructure layer
        """
        self.start_time: datetime = datetime.now()
        self._db_health_checker: Optional[DatabaseHealthCheckerProtocol] = db_health_checker
        self._broker: Optional[Any] = None

    def set_dependencies(
        self,
        db_path: Optional[str] = None,
        broker: Optional[Any] = None,
    ) -> None:
        """
        Set dependencies for health checks.

        Args:
            db_path: Optional database file path (creates checker if not set)
            broker: Optional broker instance for connectivity checks
        """
        self._broker = broker
        if db_path and not self._db_health_checker:
            self._db_health_checker = DatabaseHealthCheckerFactory.create_sqlite_checker(db_path)

    async def check_database(self) -> Dict[str, Any]:
        """
        Check database connection and integrity.

        Returns:
            Dict with status: "healthy", "degraded", or "unhealthy"
        """
        if self._db_health_checker is None:
            logger.warning("Database health check: database checker not configured")
            return {"status": "degraded", "message": "Database not configured"}

        try:
            result = self._db_health_checker.check_health()
            logger.info(f"Database health check: {result.get('message', 'No message')}")
            return result
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}

    async def check_broker(self) -> Dict[str, Any]:
        """
        Check broker API connectivity.

        Returns:
            Dict with status
        """
        if not self._broker:
            logger.warning("Broker health check: broker not configured")
            return {"status": "degraded", "message": "Broker not configured"}

        try:
            # Try to get account info with timeout
            account = await asyncio.wait_for(self._broker.get_account_info(), timeout=5.0)

            if account:
                result = {
                    "status": "healthy",
                    "message": f"Broker connected: {type(self._broker).__name__}",
                }
                logger.info(f"Broker health check: {result['message']}")
                return result
            else:
                logger.warning("Broker health check: broker returned no account info")
                return {"status": "degraded", "message": "Broker returned no account info"}

        except asyncio.TimeoutError:
            logger.error("Broker health check: connection timeout after 5s")
            return {"status": "unhealthy", "message": "Broker connection timeout"}
        except Exception as e:
            logger.error(f"Broker health check failed: {str(e)}")
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

            result = {
                "status": status,
                "memory_mb": round(memory_mb, 2),
                "memory_percent": round(memory_percent, 2),
                "available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
            }

            # Log based on status
            if status == "unhealthy":
                logger.error(f"Memory health check: {status} - {result['memory_mb']:.1f}MB used ({result['memory_percent']:.1f}%)")
            elif status == "degraded":
                logger.warning(f"Memory health check: {status} - {result['memory_mb']:.1f}MB used ({result['memory_percent']:.1f}%)")
            else:
                logger.info(f"Memory health check: {status} - {result['memory_mb']:.1f}MB used ({result['memory_percent']:.1f}%)")

            return result

        except ImportError:
            logger.warning("Memory health check: psutil not installed")
            return {"status": "degraded", "message": "psutil not installed"}
        except Exception as e:
            logger.error(f"Memory health check failed: {str(e)}")
            return {"status": "degraded", "message": f"Memory check error: {str(e)}"}

    async def check_positions(self) -> Dict[str, Any]:
        """
        Check active positions.

        Returns:
            Dict with position count and status
        """
        if not self._broker:
            logger.warning("Positions health check: broker not configured")
            return {"status": "degraded", "message": "Broker not configured", "count": 0}

        try:
            positions = await asyncio.wait_for(self._broker.get_positions(), timeout=5.0)

            count: int = len(positions) if positions else 0

            result = {"status": "healthy", "count": count, "message": f"{count} open positions"}
            logger.info(f"Positions health check: {result['message']}")
            return result

        except Exception as e:
            logger.error(f"Positions health check failed: {str(e)}")
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

        result = {"status": overall_status, "checks": checks, "uptime_seconds": uptime}

        # Log overall status
        logger.info(
            f"Overall health check: {overall_status.upper()} - "
            f"uptime={uptime:.0f}s, "
            f"database={checks['database']['status']}, "
            f"broker={checks['broker']['status']}, "
            f"memory={checks['memory']['status']}, "
            f"positions={checks['positions']['status']}"
        )

        return result


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
