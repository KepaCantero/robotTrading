"""
Stop Executor - Executes stop-loss and take-profit orders.

Handles the actual order execution when stops are triggered.

This is a CRITICAL component for production trading. When a stop-loss or
take-profit is triggered, the executor must:
1. Place the order immediately
2. Handle broker errors gracefully
3. Log all execution details
4. Return detailed execution results
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from app.core.decimal_utils import to_decimal

if TYPE_CHECKING:
    from .position_monitor import MonitoredPosition

logger = logging.getLogger(__name__)


class StopType(Enum):
    """Type of stop order."""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class StopExecutionResult:
    """Result of stop order execution."""

    success: bool
    stop_type: StopType
    symbol: str
    quantity: Decimal
    requested_price: Decimal
    executed_price: Optional[Decimal] = None
    order_id: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    broker_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "stop_type": self.stop_type.value,
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "requested_price": str(self.requested_price),
            "executed_price": str(self.executed_price) if self.executed_price else None,
            "order_id": self.order_id,
            "error_message": self.error_message,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_time_ms": self.execution_time_ms,
            "broker_response": self.broker_response,
        }


class StopExecutor:
    """
    Executes stop-loss and take-profit orders.

    This component handles the actual order execution when stops are triggered
    by the PositionMonitor.

    The executor must:
    1. Place orders immediately (market orders for emergency exits)
    2. Handle timeouts and broker errors
    3. Retry on transient failures
    4. Log all execution details for audit trail
    """

    # Default timeouts
    DEFAULT_ORDER_TIMEOUT = 30.0  # seconds
    DEFAULT_RETRY_ATTEMPTS = 2
    DEFAULT_RETRY_DELAY = 1.0  # seconds

    def __init__(self, broker, order_timeout: float = DEFAULT_ORDER_TIMEOUT):
        """
        Initialize stop executor.

        Args:
            broker: Broker connector for executing orders
            order_timeout: Maximum time to wait for order execution (seconds)
        """
        self.broker = broker
        self.order_timeout = order_timeout
        logger.info("StopExecutor initialized")

    async def execute_stop_loss(
        self, position: "MonitoredPosition", retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    ) -> StopExecutionResult:
        """
        Execute stop-loss order for a position.

        This is a CRITICAL operation. When stop-loss is triggered, we must
        exit the position immediately to prevent further losses.

        Args:
            position: MonitoredPosition with triggered stop-loss
            retry_attempts: Number of retry attempts on failure

        Returns:
            StopExecutionResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        logger.critical(
            f"Executing STOP LOSS for {position.symbol} @ {position.current_price} "
            f"(entry: {position.entry_price}, stop: {position.stop_loss_price})"
        )

        # Determine order side (opposite of position side)
        order_side = "SELL" if position.side == "LONG" else "BUY"

        # Try to execute with retries
        for attempt in range(retry_attempts + 1):
            try:
                result = await self._execute_order(
                    symbol=position.symbol,
                    side=order_side,
                    quantity=position.quantity,
                    order_type="MARKET",
                    stop_type=StopType.STOP_LOSS,
                    requested_price=position.stop_loss_price,
                    current_price=position.current_price,
                )

                # Calculate execution time
                executed_at = datetime.now(timezone.utc)
                result.execution_time_ms = int((executed_at - start_time).total_seconds() * 1000)
                result.executed_at = executed_at

                if result.success:
                    logger.critical(
                        f"STOP LOSS EXECUTED: {position.symbol} - "
                        f"Order ID: {result.order_id} - "
                        f"Price: {result.executed_price} - "
                        f"Time: {result.execution_time_ms}ms"
                    )
                else:
                    logger.error(
                        f"STOP LOSS FAILED (attempt {attempt + 1}/{retry_attempts + 1}): "
                        f"{position.symbol} - {result.error_message}"
                    )

                return result

            except Exception as e:
                logger.error(
                    f"STOP LOSS ERROR (attempt {attempt + 1}/{retry_attempts + 1}): "
                    f"{position.symbol} - {str(e)}"
                )

                if attempt < retry_attempts:
                    await asyncio.sleep(self.DEFAULT_RETRY_DELAY)
                    continue

                # Final failure
                return StopExecutionResult(
                    success=False,
                    stop_type=StopType.STOP_LOSS,
                    symbol=position.symbol,
                    quantity=position.quantity,
                    requested_price=position.stop_loss_price,
                    error_message=f"Failed after {retry_attempts + 1} attempts: {str(e)}",
                    executed_at=datetime.now(timezone.utc),
                )

    async def execute_take_profit(
        self, position: "MonitoredPosition", retry_attempts: int = DEFAULT_RETRY_ATTEMPTS
    ) -> StopExecutionResult:
        """
        Execute take-profit order for a position.

        When take-profit is triggered, we exit the position to lock in gains.

        Args:
            position: MonitoredPosition with triggered take-profit
            retry_attempts: Number of retry attempts on failure

        Returns:
            StopExecutionResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            f"Executing TAKE PROFIT for {position.symbol} @ {position.current_price} "
            f"(entry: {position.entry_price}, target: {position.take_profit_price})"
        )

        # Determine order side (opposite of position side)
        order_side = "SELL" if position.side == "LONG" else "BUY"

        # Try to execute with retries
        for attempt in range(retry_attempts + 1):
            try:
                result = await self._execute_order(
                    symbol=position.symbol,
                    side=order_side,
                    quantity=position.quantity,
                    order_type="MARKET",
                    stop_type=StopType.TAKE_PROFIT,
                    requested_price=position.take_profit_price,
                    current_price=position.current_price,
                )

                # Calculate execution time
                executed_at = datetime.now(timezone.utc)
                result.execution_time_ms = int((executed_at - start_time).total_seconds() * 1000)
                result.executed_at = executed_at

                if result.success:
                    logger.info(
                        f"TAKE PROFIT EXECUTED: {position.symbol} - "
                        f"Order ID: {result.order_id} - "
                        f"Price: {result.executed_price} - "
                        f"Time: {result.execution_time_ms}ms"
                    )
                else:
                    logger.error(
                        f"TAKE PROFIT FAILED (attempt {attempt + 1}/{retry_attempts + 1}): "
                        f"{position.symbol} - {result.error_message}"
                    )

                return result

            except Exception as e:
                logger.error(
                    f"TAKE PROFIT ERROR (attempt {attempt + 1}/{retry_attempts + 1}): "
                    f"{position.symbol} - {str(e)}"
                )

                if attempt < retry_attempts:
                    await asyncio.sleep(self.DEFAULT_RETRY_DELAY)
                    continue

                # Final failure
                return StopExecutionResult(
                    success=False,
                    stop_type=StopType.TAKE_PROFIT,
                    symbol=position.symbol,
                    quantity=position.quantity,
                    requested_price=position.take_profit_price,
                    error_message=f"Failed after {retry_attempts + 1} attempts: {str(e)}",
                    executed_at=datetime.now(timezone.utc),
                )

    async def _execute_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str,
        stop_type: StopType,
        requested_price: Optional[Decimal],
        current_price: Decimal,
    ) -> StopExecutionResult:
        """
        Execute order with timeout.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, etc.)
            stop_type: Type of stop being executed
            requested_price: Requested price (for logging)
            current_price: Current market price

        Returns:
            StopExecutionResult with execution details
        """
        try:
            # Place market order with timeout
            order_result = await asyncio.wait_for(
                self.broker.place_order(
                    symbol=symbol,
                    side=side,
                    quantity=float(quantity),
                    order_type=order_type,
                ),
                timeout=self.order_timeout,
            )

            # Check if order was successful
            if order_result and "error" not in order_result:
                # Successful execution
                executed_price = order_result.get("fill_price", current_price)
                order_id = str(order_result.get("order_id", "unknown"))

                return StopExecutionResult(
                    success=True,
                    stop_type=stop_type,
                    symbol=symbol,
                    quantity=quantity,
                    requested_price=requested_price or Decimal("0"),
                    executed_price=to_decimal(executed_price),
                    order_id=order_id,
                    broker_response=order_result,
                )
            else:
                # Broker returned error
                error_msg = order_result.get("error", "Unknown error") if order_result else "No response"
                return StopExecutionResult(
                    success=False,
                    stop_type=stop_type,
                    symbol=symbol,
                    quantity=quantity,
                    requested_price=requested_price or Decimal("0"),
                    error_message=error_msg,
                    broker_response=order_result,
                )

        except asyncio.TimeoutError:
            return StopExecutionResult(
                success=False,
                stop_type=stop_type,
                symbol=symbol,
                quantity=quantity,
                requested_price=requested_price or Decimal("0"),
                error_message=f"Order execution timeout after {self.order_timeout}s",
            )

        except Exception as e:
            return StopExecutionResult(
                success=False,
                stop_type=stop_type,
                symbol=symbol,
                quantity=quantity,
                requested_price=requested_price or Decimal("0"),
                error_message=str(e),
            )

    async def execute_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_type: StopType,
        stop_price: Decimal,
    ) -> StopExecutionResult:
        """
        Execute a stop order directly (without MonitoredPosition).

        This is useful for manual stop orders or external triggers.

        Args:
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            quantity: Order quantity
            stop_type: Type of stop (STOP_LOSS or TAKE_PROFIT)
            stop_price: Stop price

        Returns:
            StopExecutionResult with execution details
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"Executing {stop_type.value} order for {symbol} @ {stop_price}")

        try:
            result = await self._execute_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="MARKET",
                stop_type=stop_type,
                requested_price=stop_price,
                current_price=stop_price,
            )

            # Calculate execution time
            executed_at = datetime.now(timezone.utc)
            result.execution_time_ms = int((executed_at - start_time).total_seconds() * 1000)
            result.executed_at = executed_at

            return result

        except Exception as e:
            return StopExecutionResult(
                success=False,
                stop_type=stop_type,
                symbol=symbol,
                quantity=quantity,
                requested_price=stop_price,
                error_message=str(e),
                executed_at=datetime.now(timezone.utc),
            )
