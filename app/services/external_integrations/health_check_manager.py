"""
Health check management for external integrations.

Monitors the health of external services (QuestDB, Dagster, MLFlow, Zipline)
and provides status information.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status of external service."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Health information for a service."""

    service_name: str
    status: HealthStatus
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0


class HealthCheckConfig:
    """Configuration for health checks."""

    def __init__(
        self,
        check_interval_sec: int = 60,
        failure_threshold: int = 3,
        recovery_timeout_sec: int = 300,
    ):
        """
        Initialize health check configuration.

        Args:
            check_interval_sec: Interval between health checks
            failure_threshold: Number of failures before marking unhealthy
            recovery_timeout_sec: Time to wait before retrying unhealthy service
        """
        self.check_interval_sec = check_interval_sec
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec


class HealthCheckManager:
    """Manages health checks for external integrations."""

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        """
        Initialize health check manager.

        Args:
            config: Health check configuration
        """
        self.config = config or HealthCheckConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.service_health: Dict[str, ServiceHealth] = {}
        self.check_tasks: Dict[str, asyncio.Task] = {}

    def register_service(self, service_name: str) -> None:
        """
        Register a service for health checking.

        Args:
            service_name: Name of service to monitor
        """
        self.service_health[service_name] = ServiceHealth(
            service_name=service_name,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.utcnow(),
        )
        self.logger.info(f"✅ Registered service for health checks: {service_name}")

    async def check_service_health(
        self,
        service_name: str,
        health_check_func,
    ) -> ServiceHealth:
        """
        Check health of a service.

        Args:
            service_name: Name of service
            health_check_func: Async function that returns True if healthy

        Returns:
            Updated ServiceHealth object
        """
        if service_name not in self.service_health:
            self.register_service(service_name)

        try:
            start_time = datetime.utcnow()
            is_healthy = await health_check_func()
            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            if is_healthy:
                # Service is healthy
                health = self.service_health[service_name]
                health.status = HealthStatus.HEALTHY
                health.response_time_ms = response_time_ms
                health.consecutive_failures = 0
                health.last_check = datetime.utcnow()
                health.error_message = None

                self.logger.debug(
                    f"✅ {service_name} health check passed "
                    f"(response_time={response_time_ms:.0f}ms)"
                )
            else:
                # Service returned false/unhealthy
                self._record_failure(service_name, "Health check returned False")

        except Exception as e:
            # Exception during health check
            self._record_failure(service_name, str(e))

        return self.service_health[service_name]

    def _record_failure(self, service_name: str, error_message: str) -> None:
        """
        Record a health check failure.

        Args:
            service_name: Name of service
            error_message: Error message
        """
        health = self.service_health[service_name]
        health.consecutive_failures += 1
        health.error_message = error_message
        health.last_check = datetime.utcnow()

        if health.consecutive_failures >= self.config.failure_threshold:
            health.status = HealthStatus.UNHEALTHY
            self.logger.warning(
                f"⚠️ {service_name} marked as UNHEALTHY "
                f"({health.consecutive_failures} consecutive failures): {error_message}"
            )
        else:
            health.status = HealthStatus.DEGRADED
            self.logger.warning(
                f"⚠️ {service_name} health check failed "
                f"({health.consecutive_failures}/{self.config.failure_threshold}): {error_message}"
            )

    def get_service_health(self, service_name: str) -> Optional[ServiceHealth]:
        """
        Get health status of a service.

        Args:
            service_name: Name of service

        Returns:
            ServiceHealth object or None if not registered
        """
        return self.service_health.get(service_name)

    def get_all_health_status(self) -> Dict[str, ServiceHealth]:
        """
        Get health status of all services.

        Returns:
            Dictionary of service_name -> ServiceHealth
        """
        return dict(self.service_health)

    def is_service_healthy(self, service_name: str) -> bool:
        """
        Check if a service is healthy.

        Args:
            service_name: Name of service

        Returns:
            True if service is healthy
        """
        health = self.service_health.get(service_name)
        if not health:
            return False
        return health.status == HealthStatus.HEALTHY

    def get_unhealthy_services(self) -> List[str]:
        """
        Get list of unhealthy services.

        Returns:
            List of service names that are unhealthy
        """
        return [
            name
            for name, health in self.service_health.items()
            if health.status == HealthStatus.UNHEALTHY
        ]

    def get_degraded_services(self) -> List[str]:
        """
        Get list of degraded services.

        Returns:
            List of service names that are degraded
        """
        return [
            name
            for name, health in self.service_health.items()
            if health.status == HealthStatus.DEGRADED
        ]

    def reset_service_failures(self, service_name: str) -> None:
        """
        Reset failure counter for a service (on manual recovery).

        Args:
            service_name: Name of service
        """
        if service_name in self.service_health:
            health = self.service_health[service_name]
            health.consecutive_failures = 0
            health.status = HealthStatus.HEALTHY
            health.error_message = None
            self.logger.info(f"✅ Manually reset failures for {service_name}")


# Default instance
_health_check_manager: Optional[HealthCheckManager] = None


def get_health_check_manager() -> HealthCheckManager:
    """Get or create the health check manager singleton."""
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
        logger.info("✅ HealthCheckManager singleton initialized")
    return _health_check_manager
