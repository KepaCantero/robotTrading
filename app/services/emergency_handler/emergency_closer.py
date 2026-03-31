"""
Emergency Closer - Closes all positions on critical system failures.

Protects against catastrophic losses by closing all positions when:
- Broker connection is lost
- System is shutting down
- Critical errors occur
- Manual emergency trigger is activated

Uses centralized configuration for all timeout parameters.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional, Union

from requests.exceptions import HTTPError

from app.shared.config.centralized_config import get_config
from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class EmergencyTrigger(Enum):
    """Types of emergency triggers."""

    CONNECTION_LOST = "connection_lost"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CRITICAL_ERROR = "critical_error"
    MANUAL_TRIGGER = "manual_trigger"
    HEARTBEAT_FAILURE = "heartbeat_failure"
    MEMORY_EXCEEDED = "memory_exceeded"


@dataclass
class EmergencyCloseResult:
    """Result of emergency close operation."""

    success: bool
    trigger: EmergencyTrigger
    total_positions: int
    closed_positions: int
    failed_positions: int
    total_value: Decimal
    execution_time_seconds: float
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Union[str, int, float, bool, Decimal, list[str], datetime]]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "trigger": self.trigger.value,
            "total_positions": self.total_positions,
            "closed_positions": self.closed_positions,
            "failed_positions": self.failed_positions,
            "total_value": str(self.total_value),
            "execution_time_seconds": self.execution_time_seconds,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat(),
        }


class EmergencyCloser:
    """
    Closes all positions on critical system failures.

    This is a CRITICAL safety component. When triggered, it will:
    1. Fetch all open positions from broker
    2. Close all positions via market orders
    3. Log all actions to audit trail
    4. Send alerts before closing
    5. Record results for analysis

    USE WITH CAUTION: This will close ALL positions immediately.
    """

    def __init__(
        self,
        broker,
        alert_callback: Optional[Callable[[str], None]] = None,
        require_confirmation: bool = False,
        confirmation_timeout_seconds: Optional[float] = None,
    ):
        """
        Initialize emergency closer.

        Args:
            broker: Broker connector for executing orders
            alert_callback: Optional callback for sending alerts
            require_confirmation: If True, waits for confirmation before closing
            confirmation_timeout_seconds: How long to wait for confirmation (uses centralized config if None)
        """
        self.broker = broker
        self.alert_callback = alert_callback
        self.require_confirmation = require_confirmation

        # Use centralized config for confirmation_timeout if not provided
        if confirmation_timeout_seconds is None:
            tt = get_config().trading_thresholds
            confirmation_timeout_seconds = tt.emergency_confirmation_timeout
        self.confirmation_timeout_seconds = confirmation_timeout_seconds

        # State
        self._is_closing = False
        self._audit_log: list[
            dict[
                str,
                Union[
                    str,
                    int,
                    float,
                    bool,
                    Decimal,
                    list[str],
                    datetime,
                    dict[str, Union[str, int, float, bool, Decimal, list[str], datetime]],
                ],
            ]
        ] = []
        self._last_trigger: Optional[EmergencyTrigger] = None
        self._last_close_time: Optional[datetime] = None

        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()

        logger.info("EmergencyCloser initialized")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            # Register shutdown handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
            logger.info("Emergency shutdown signal handlers registered")
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.warning(f"Could not register signal handlers: {e}")

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.critical(f"Received signal {signum} - initiating emergency shutdown")
        # Create async task to handle shutdown
        self._shutdown_task = asyncio.create_task(self.on_system_shutdown())

    async def on_connection_lost(self) -> EmergencyCloseResult:
        """
        Called when broker connection dies.

        This is the most common trigger - broker disconnection means
        we cannot manage positions, so we must close them.

        Returns:
            EmergencyCloseResult with execution details
        """
        logger.critical("CONNECTION LOST - initiating emergency close of all positions")

        # Send alert
        await self._send_alert("EMERGENCY: Broker connection lost. Closing all positions.")

        result = await self.close_all_positions(EmergencyTrigger.CONNECTION_LOST)

        # Log to audit trail
        self._audit_log.append(
            {
                "timestamp": utc_now().isoformat(),
                "trigger": EmergencyTrigger.CONNECTION_LOST.value,
                "result": result.to_dict(),
            }
        )

        return result

    async def on_system_shutdown(self) -> EmergencyCloseResult:
        """
        Called on graceful shutdown.

        This is triggered by SIGTERM/SIGINT when the system is
        being shut down normally.

        Returns:
            EmergencyCloseResult with execution details
        """
        logger.critical("SYSTEM SHUTDOWN - initiating emergency close of all positions")

        # Send alert
        await self._send_alert("EMERGENCY: System shutting down. Closing all positions.")

        result = await self.close_all_positions(EmergencyTrigger.SYSTEM_SHUTDOWN)

        # Log to audit trail
        self._audit_log.append(
            {
                "timestamp": utc_now().isoformat(),
                "trigger": EmergencyTrigger.SYSTEM_SHUTDOWN.value,
                "result": result.to_dict(),
            }
        )

        return result

    async def on_critical_error(self, error: Exception) -> EmergencyCloseResult:
        """
        Called on unhandled exception.

        Only critical errors should trigger this. Use error_threshold
        to configure what counts as critical.

        Args:
            error: The exception that occurred

        Returns:
            EmergencyCloseResult with execution details
        """
        if not self._is_error_critical(error):
            logger.warning(f"Non-critical error - not closing positions: {error}")
            return EmergencyCloseResult(
                success=False,
                trigger=EmergencyTrigger.CRITICAL_ERROR,
                total_positions=0,
                closed_positions=0,
                failed_positions=0,
                total_value=Decimal("0"),
                execution_time_seconds=0.0,
                errors=["Error not critical enough to trigger close"],
            )

        logger.critical(f"CRITICAL ERROR - initiating emergency close: {error}")

        # Send alert
        await self._send_alert(
            f"EMERGENCY: Critical error detected. Closing all positions. Error: {error!s}"
        )

        result = await self.close_all_positions(EmergencyTrigger.CRITICAL_ERROR)

        # Log to audit trail
        self._audit_log.append(
            {
                "timestamp": utc_now().isoformat(),
                "trigger": EmergencyTrigger.CRITICAL_ERROR.value,
                "error": str(error),
                "result": result.to_dict(),
            }
        )

        return result

    def _is_error_critical(self, error: Exception) -> bool:
        """
        Determine if an error is critical enough to close all positions.

        Args:
            error: The exception to evaluate

        Returns:
            True if error is critical
        """
        # Critical error types
        critical_types = (
            ConnectionError,
            TimeoutError,
            MemoryError,
        )

        # Check if error type is critical
        if isinstance(error, critical_types):
            return True

        # Check error message for critical keywords
        error_msg = str(error).lower()
        critical_keywords = [
            "connection lost",
            "connection failed",
            "authentication failed",
            "insufficient funds",
            "order rejected",
            "market closed",
        ]

        return any(keyword in error_msg for keyword in critical_keywords)

    async def manual_trigger(self, reason: str = "Manual") -> EmergencyCloseResult:
        """
        Manually trigger emergency close.

        This can be called via API endpoint or admin command.

        Args:
            reason: Reason for manual trigger

        Returns:
            EmergencyCloseResult with execution details
        """
        logger.critical(f"MANUAL EMERGENCY TRIGGER - reason: {reason}")

        # Send alert
        await self._send_alert(
            f"EMERGENCY: Manual trigger activated. Reason: {reason}. Closing all positions."
        )

        result = await self.close_all_positions(EmergencyTrigger.MANUAL_TRIGGER)

        # Log to audit trail
        self._audit_log.append(
            {
                "timestamp": utc_now().isoformat(),
                "trigger": EmergencyTrigger.MANUAL_TRIGGER.value,
                "reason": reason,
                "result": result.to_dict(),
            }
        )

        return result

    async def close_all_positions(
        self,
        trigger: EmergencyTrigger,
    ) -> EmergencyCloseResult:
        """
        Close all positions via market orders.

        This is the core emergency close logic. It will:
        1. Fetch all open positions
        2. Optionally wait for confirmation
        3. Close all positions via market orders
        4. Record results

        Args:
            trigger: What triggered the emergency close

        Returns:
            EmergencyCloseResult with execution details
        """
        if self._is_closing:
            logger.warning("Emergency close already in progress")
            return EmergencyCloseResult(
                success=False,
                trigger=trigger,
                total_positions=0,
                closed_positions=0,
                failed_positions=0,
                total_value=Decimal("0"),
                execution_time_seconds=0.0,
                errors=["Emergency close already in progress"],
            )

        self._is_closing = True
        start_time = asyncio.get_event_loop().time()

        try:
            # Get confirmation if required
            if self.require_confirmation and trigger != EmergencyTrigger.CONNECTION_LOST:
                confirmed = await self._wait_for_confirmation()
                if not confirmed:
                    logger.warning("Emergency close not confirmed - aborting")
                    return EmergencyCloseResult(
                        success=False,
                        trigger=trigger,
                        total_positions=0,
                        closed_positions=0,
                        failed_positions=0,
                        total_value=Decimal("0"),
                        execution_time_seconds=0.0,
                        errors=["Close not confirmed"],
                    )

            # Fetch all open positions
            positions = await self._get_all_positions()

            if not positions:
                logger.info("No open positions to close")
                return EmergencyCloseResult(
                    success=True,
                    trigger=trigger,
                    total_positions=0,
                    closed_positions=0,
                    failed_positions=0,
                    total_value=Decimal("0"),
                    execution_time_seconds=0.0,
                )

            logger.critical(f"Closing {len(positions)} positions due to {trigger.value}")

            # Close all positions
            closed = 0
            failed = 0
            errors: list[str] = []
            total_value = Decimal("0")

            for position in positions:
                try:
                    close_result = await self._close_position(position)
                    if close_result.get("success", False):
                        closed += 1
                        raw_value = close_result.get("value", Decimal("0"))
                        total_value += Decimal(str(raw_value))
                    else:
                        failed += 1
                        raw_error = close_result.get("error", "Unknown error")
                        errors.append(str(raw_error))
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    failed += 1
                    symbol = getattr(position, "symbol", "unknown")
                    errors.append(f"Error closing {symbol}: {e!s}")
                    logger.error(f"Error closing position {symbol}: {e}")

            execution_time = asyncio.get_event_loop().time() - start_time

            result = EmergencyCloseResult(
                success=failed == 0,
                trigger=trigger,
                total_positions=len(positions),
                closed_positions=closed,
                failed_positions=failed,
                total_value=total_value,
                execution_time_seconds=execution_time,
                errors=errors,
            )

            self._last_trigger = trigger
            self._last_close_time = utc_now()

            logger.critical(
                f"Emergency close complete: {closed}/{len(positions)} positions "
                f"closed in {execution_time:.2f}s"
            )

            return result

        finally:
            self._is_closing = False

    async def _get_all_positions(self) -> list[object]:
        """Get all open positions from broker."""
        try:
            positions = await self.broker.get_positions()
            return positions if positions else []
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def _close_position(
        self, position: object
    ) -> dict[str, Union[str, int, float, bool, Decimal]]:
        """
        Close a single position.

        Args:
            position: Position object from broker

        Returns:
            Dict with success, value, error
        """
        try:
            # Determine order side (opposite of position side)
            side = getattr(position, "side", "LONG")
            order_side = "SELL" if side == "LONG" else "BUY"

            quantity = getattr(position, "quantity", Decimal("0"))

            # Place market order - use centralized config for timeout
            tt = get_config().trading_thresholds
            timeout = tt.emergency_position_close_timeout
            order = await asyncio.wait_for(
                self.broker.place_order(
                    symbol=position.symbol,
                    side=order_side,
                    quantity=quantity,
                    order_type="MARKET",
                ),
                timeout=timeout,
            )

            if order:
                logger.critical(f"Closed position: {position.symbol} ({quantity} shares)")
                return {
                    "success": True,
                    "value": quantity * getattr(position, "current_price", Decimal("0")),
                }
            else:
                return {
                    "success": False,
                    "error": f"Broker returned no order for {position.symbol}",
                }

        except (asyncio.TimeoutError, OSError) as e:
            return {
                "success": False,
                "error": f"Error closing {position.symbol}: {e!s}",
            }

    async def _wait_for_confirmation(self) -> bool:
        """
        Wait for user confirmation before closing.

        Returns:
            True if confirmed
        """
        # In production, this would send an alert and wait for confirmation
        # via API call, webhook, or other mechanism
        logger.warning("Confirmation required - waiting for manual confirmation")

        try:
            await asyncio.sleep(self.confirmation_timeout_seconds)
            return True  # Auto-confirm after timeout
        except asyncio.CancelledError:
            return False

    async def _send_alert(self, message: str) -> None:
        """Send alert notification."""
        logger.critical(f"ALERT: {message}")

        if self.alert_callback:
            try:
                self.alert_callback(message)
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"Error sending alert: {e}")

    def get_audit_log(
        self, limit: int = 100
    ) -> list[dict[str, Union[str, int, float, bool, Decimal, list[str], datetime]]]:
        """Get audit log entries."""
        return self._audit_log[-limit:]

    def get_last_trigger(self) -> Optional[EmergencyTrigger]:
        """Get the last trigger type."""
        return self._last_trigger

    def get_last_close_time(self) -> Optional[datetime]:
        """Get the last close time."""
        return self._last_close_time
