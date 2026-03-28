"""
Time Sync Monitor - Monitor system clock synchronization.

Clock drift can cause:
- Order rejections from broker
- Incorrect timestamps in FIFO database
- Tax calculation errors

This service monitors and validates system time.

Phase 2.7: Time Sync Monitor Implementation
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Dict, Optional, Union

from app.shared.utils.timezone_utils import utc_now
import contextlib

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import ntplib


# NTP Servers for time synchronization
# Using multiple servers for redundancy
NTP_SERVERS = [
    "pool.ntp.org",
    "time.google.com",
    "time.cloudflare.com",
    "time.nist.gov",
]


@dataclass
class TimeSyncConfig:
    """Configuration for time sync monitoring."""

    check_interval_seconds: float = 60.0  # Check every minute
    drift_threshold_seconds: float = 1.0  # Alert if drift > 1 second
    critical_threshold_seconds: float = 5.0  # Critical if drift > 5 seconds
    max_retries: int = 3
    timeout_seconds: float = 5.0

    # Callbacks
    on_drift_detected: Optional[Callable[[float], None]] = None
    on_critical_drift: Optional[Callable[[float], None]] = None
    on_sync_error: Optional[Callable[[Exception], None]] = None


@dataclass
class TimeSyncStatus:
    """Current time sync status."""

    is_synced: bool
    drift_seconds: float
    local_time: datetime
    ntp_time: Optional[datetime]
    ntp_server: Optional[str]
    last_check: datetime
    checks_total: int = 0
    checks_failed: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_synced": self.is_synced,
            "drift_seconds": self.drift_seconds,
            "local_time": self.local_time.isoformat(),
            "ntp_time": self.ntp_time.isoformat() if self.ntp_time else None,
            "ntp_server": self.ntp_server,
            "last_check": self.last_check.isoformat(),
            "checks_total": self.checks_total,
            "checks_failed": self.checks_failed,
        }


class TimeSyncMonitor:
    """
    Monitor system clock synchronization.

    Monitors clock drift every minute and validates orders
    before submission to prevent timestamp errors.

    Features:
    - Monitors clock drift against NTP servers
    - Alerts when drift exceeds thresholds
    - Rejects orders if clock is not synced
    - Provides status and metrics
    """

    def __init__(self, config: Optional[TimeSyncConfig] = None):
        """
        Initialize time sync monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config or TimeSyncConfig()

        # Lazy load ntplib to avoid import errors if not available
        self._ntp_client: Optional[ntplib.NTPClient] = None
        self._ntp_available = False

        # State
        self._is_monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._status = TimeSyncStatus(
            is_synced=True,
            drift_seconds=0.0,
            local_time=utc_now(),
            ntp_time=None,
            ntp_server=None,
            last_check=utc_now(),
        )

        # Check NTP availability
        self._check_ntp_availability()

        logger.info("TimeSyncMonitor initialized")

    def _check_ntp_availability(self) -> None:
        """Check if ntplib is available."""
        try:
            import ntplib

            self._ntp_client = ntplib.NTPClient()
            self._ntp_available = True
            logger.info("NTP synchronization available")
        except ImportError:
            self._ntp_available = False
            logger.warning("ntplib not available - time sync checks disabled")

    async def start(self) -> bool:
        """
        Start monitoring time sync.

        Returns:
            True if started successfully
        """
        if self._is_monitoring:
            logger.warning("TimeSyncMonitor already running")
            return False

        self._is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("TimeSyncMonitor started")
        return True

    async def stop(self) -> bool:
        """
        Stop monitoring time sync.

        Returns:
            True if stopped successfully
        """
        if not self._is_monitoring:
            logger.warning("TimeSyncMonitor not running")
            return False

        self._is_monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None

        logger.info("TimeSyncMonitor stopped")
        return True

    async def _monitor_loop(self) -> None:
        """Monitor clock drift every minute."""
        while self._is_monitoring:
            try:
                drift = await self.check_time_drift()

                if abs(drift) > self.config.critical_threshold_seconds:
                    logger.critical(
                        f"CRITICAL clock drift: {drift:.3f}s "
                        f"(threshold: {self.config.critical_threshold_seconds}s)"
                    )

                    if self.config.on_critical_drift:
                        try:
                            self.config.on_critical_drift(drift)
                        except (asyncio.TimeoutError, OSError) as e:
                            logger.error(f"Error in critical drift callback: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error in time sync monitor loop: {e}", exc_info=True)
                await asyncio.sleep(self.config.check_interval_seconds)

    async def check_time_drift(self) -> float:
        """
        Check clock drift against NTP servers.

        Returns:
            Drift in seconds (positive = local ahead, negative = local behind)
        """
        self._status.checks_total += 1

        # If NTP is not available, return zero drift
        if not self._ntp_available:
            logger.debug("NTP not available, assuming system time is correct")
            self._status.is_synced = True
            self._status.drift_seconds = 0.0
            self._status.local_time = utc_now()
            self._status.last_check = utc_now()
            return 0.0

        for server in NTP_SERVERS:
            try:
                # Get NTP time
                if self._ntp_client is None:
                    continue
                response = await asyncio.to_thread(
                    self._ntp_client.request,
                    server,
                    version=3,
                    timeout=self.config.timeout_seconds,
                )

                # Calculate NTP time
                ntp_timestamp = response.tx_time
                ntp_time = datetime.fromtimestamp(ntp_timestamp, timezone.utc)

                # Get local time
                local_time = utc_now()

                # Calculate drift
                drift = (local_time - ntp_time).total_seconds()

                self._status.local_time = local_time
                self._status.ntp_time = ntp_time
                self._status.ntp_server = server
                self._status.drift_seconds = drift
                self._status.last_check = local_time
                self._status.is_synced = abs(drift) <= self.config.drift_threshold_seconds

                # Check thresholds
                if abs(drift) > self.config.drift_threshold_seconds:
                    logger.warning(
                        f"Clock drift detected: {drift:.3f}s "
                        f"(threshold: {self.config.drift_threshold_seconds}s)"
                    )

                    if self.config.on_drift_detected:
                        try:
                            self.config.on_drift_detected(drift)
                        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                            logger.error(f"Error in drift detected callback: {e}")

                return drift

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"NTP error for {server}: {e}")
                continue

        # All servers failed
        self._status.checks_failed += 1
        self._status.is_synced = False

        error = Exception("All NTP servers failed")
        logger.error("All NTP servers failed")

        if self.config.on_sync_error:
            try:
                self.config.on_sync_error(error)
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.error(f"Error in sync error callback: {e}")

        return 0.0

    async def validate_order_timestamp(self, order: object) -> bool:
        """
        Reject order if clock drift is too high.

        Args:
            order: Order to validate

        Returns:
            True if order can be submitted
        """
        # Check current drift
        drift = self._status.drift_seconds

        if abs(drift) > self.config.drift_threshold_seconds:
            logger.error(
                f"Rejecting order due to clock drift: {drift:.3f}s > "
                f"{self.config.drift_threshold_seconds}s threshold"
            )
            return False

        return True

    def get_status(self) -> TimeSyncStatus:
        """Get current time sync status."""
        return self._status

    def get_drift_seconds(self) -> float:
        """Get current clock drift in seconds."""
        return self._status.drift_seconds

    def is_synced(self) -> bool:
        """Check if clock is synced within threshold."""
        return self._status.is_synced

    def get_ntp_availability(self) -> bool:
        """Check if NTP synchronization is available."""
        return self._ntp_available

    async def sync_clock(self) -> bool:
        """
        Attempt to sync system clock.

        Note: This requires root privileges and may not work in all environments.

        Returns:
            True if sync was successful
        """
        if not self._ntp_available:
            logger.warning("Cannot sync clock - NTP not available")
            return False

        try:
            drift = await self.check_time_drift()

            if abs(drift) < 0.1:  # Already synced
                logger.info("System clock already synced (drift < 0.1s)")
                return True

            # Try to sync using system command
            # This requires root/sudo privileges
            import subprocess

            server = self._status.ntp_server or "pool.ntp.org"
            logger.info(f"Attempting to sync clock with {server}")

            result = subprocess.run(
                ["sudo", "ntpdate", "-u", server],
                capture_output=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                logger.info("System clock synced successfully")
                # Re-check drift after sync
                await asyncio.sleep(1)
                new_drift = await self.check_time_drift()
                logger.info(f"New drift after sync: {new_drift:.3f}s")
                return True
            else:
                logger.warning(f"Clock sync failed: {result.stderr.decode()}")
                return False

        except FileNotFoundError:
            logger.warning("ntpdate command not found - cannot auto-sync clock")
            return False
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error syncing clock: {e}")
            return False

    async def force_check(self) -> Dict[str, Union[str, int, float, bool, None]]:
        """
        Force an immediate time sync check.

        Returns:
            Dictionary with check results
        """
        drift = await self.check_time_drift()

        return {
            "drift_seconds": drift,
            "is_synced": self._status.is_synced,
            "threshold": self.config.drift_threshold_seconds,
            "ntp_server": self._status.ntp_server,
            "local_time": self._status.local_time.isoformat(),
            "ntp_time": self._status.ntp_time.isoformat() if self._status.ntp_time else None,
            "ntp_available": self._ntp_available,
        }


# Singleton instance
_monitor: Optional[TimeSyncMonitor] = None


def get_time_sync_monitor(config: Optional[TimeSyncConfig] = None) -> TimeSyncMonitor:
    """
    Get or create singleton TimeSyncMonitor.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        TimeSyncMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = TimeSyncMonitor(config)
        logger.info("TimeSyncMonitor singleton created")
    return _monitor


def reset_time_sync_monitor() -> None:
    """Reset the singleton TimeSyncMonitor (mainly for testing)."""
    global _monitor
    if _monitor is not None and _monitor._is_monitoring:
        # Stop monitoring if running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_monitor.stop())
            else:
                loop.run_until_complete(_monitor.stop())
        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Error stopping monitor during reset: {e}")
    _monitor = None
    logger.info("TimeSyncMonitor singleton reset")
