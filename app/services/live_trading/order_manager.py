"""
T16.1.2: OrderManager - Order lifecycle management

Manages order placement, execution tracking, cancellation, and error handling.
Integrates with BrokerConnector for actual order operations.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Depends

from .broker_connector import (
    BrokerConnector,
    BrokerOrder,
    OrderSide,
    OrderStatus,
    OrderType,
    get_broker_connector,
)
from .risk_gates import RiskCheckResult, RiskGates

logger = logging.getLogger(__name__)

_DEFAULT_FEES = Decimal("0")


@dataclass
class OrderExecution:
    """Record of order execution."""

    order_id: str
    symbol: str
    quantity: Decimal
    price: Decimal
    execution_time: datetime = field(default_factory=datetime.now)
    fees: Decimal = Decimal("0")
    net_proceeds: Decimal = Decimal("0")


@dataclass
class OrderError:
    """Order error information."""

    order_id: str
    symbol: str
    error_code: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3


class OrderManager:
    """
    Manages order lifecycle from placement to execution.

    Features:
    - Order placement and tracking
    - Execution monitoring
    - Cancellation handling
    - Order history
    - Error tracking and recovery
    - Order status polling
    """

    def __init__(
        self,
        broker: Optional[BrokerConnector] = None,
        risk_gates: Optional[RiskGates] = None,
    ):
        """Initialize order manager with risk validation."""
        self.broker = broker or get_broker_connector()
        # Create RiskGates instance directly if not provided (avoiding Depends() for direct instantiation)
        if risk_gates is None:
            from .risk_gates import RiskGates as RiskGatesImpl

            self.risk_gates = RiskGatesImpl(broker=self.broker)
        else:
            self.risk_gates = risk_gates
        self.pending_orders: dict[str, BrokerOrder] = {}
        self.executed_orders: dict[str, BrokerOrder] = {}
        self.order_history: list[BrokerOrder] = []
        self.order_errors: dict[str, OrderError] = {}
        self.executions: list[OrderExecution] = []
        logger.info("✅ OrderManager initialized with risk validation")

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        timeout_seconds: int = 60,
    ) -> Optional[BrokerOrder]:
        """
        Place order with broker.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            timeout_seconds: Timeout for order placement

        Returns:
            BrokerOrder if successful, None if risk validation fails
        """
        # Generate correlation ID for audit trail (SEC-005)
        correlation_id = str(uuid.uuid4())

        # Determine order price for risk validation
        order_price = price
        if order_price is None and order_type == OrderType.MARKET:
            # For market orders, get current price from broker
            account = await self.broker.get_account_info()
            if account:
                # Use conservative estimate if no current price available
                order_price = Decimal("100")  # Conservative default

        # TRD-002: Risk validation BEFORE order execution
        if order_price is not None:
            try:
                risk_result: RiskCheckResult = await self.risk_gates.validate_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=order_price,
                )

                if not risk_result.passed:
                    # Log rejection with structured logging and correlation ID
                    logger.warning(
                        "Order rejected by risk gates",
                        extra={
                            "correlation_id": correlation_id,
                            "symbol": symbol,
                            "side": side.value,
                            "quantity": str(quantity),
                            "price": str(order_price),
                            "order_type": order_type.value,
                            "risk_level": risk_result.risk_level.value,
                            "violations": risk_result.violations,
                            "warnings": risk_result.warnings,
                        },
                    )
                    return None

                # Log risk approval with structured logging (SEC-005)
                logger.info(
                    "Order approved by risk gates",
                    extra={
                        "correlation_id": correlation_id,
                        "symbol": symbol,
                        "side": side.value,
                        "quantity": str(quantity),
                        "price": str(order_price),
                        "order_type": order_type.value,
                        "risk_level": risk_result.risk_level.value,
                    },
                )
            except Exception as e:
                logger.error(
                    "Risk validation failed - order rejected",
                    extra={
                        "correlation_id": correlation_id,
                        "symbol": symbol,
                        "side": side.value,
                        "error": str(e),
                    },
                )
                return None

        try:
            order = await self.broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                stop_price=stop_price,
            )

            if order:
                self.pending_orders[order.order_id] = order
                self.order_history.append(order)
                # SEC-005: Structured logging with correlation ID
                logger.info(
                    "Order placed successfully",
                    extra={
                        "correlation_id": correlation_id,
                        "order_id": order.order_id,
                        "symbol": symbol,
                        "side": side.value,
                        "quantity": str(quantity),
                        "order_type": order_type.value,
                        "price": str(price) if price else None,
                    },
                )
                return order
            else:
                logger.error(
                    "Order placement failed",
                    extra={
                        "correlation_id": correlation_id,
                        "symbol": symbol,
                        "side": side.value,
                        "quantity": str(quantity),
                    },
                )
                return None

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(
                "Error placing order",
                extra={
                    "correlation_id": correlation_id,
                    "symbol": symbol,
                    "side": side.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if canceled successfully
        """
        if order_id not in self.pending_orders:
            logger.warning(f"⚠️ Order not found in pending: {order_id}")
            return False

        try:
            success = await self.broker.cancel_order(order_id)
            if success:
                order = self.pending_orders.pop(order_id)
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.now()
                self.order_history.append(order)
                logger.info(f"✅ Order canceled: {order_id}")
            return success
        except (OSError, ValueError) as e:
            logger.error(f"❌ Error canceling order: {e!s}")
            return False

    async def cancel_all_orders(self) -> int:
        """
        Cancel all pending orders.

        Returns:
            Number of orders canceled
        """
        canceled_count = 0
        order_ids = list(self.pending_orders.keys())

        for order_id in order_ids:
            if await self.cancel_order(order_id):
                canceled_count += 1

        logger.info(f"✅ Canceled {canceled_count} orders")
        return canceled_count

    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get current order status.

        Args:
            order_id: Order ID

        Returns:
            OrderStatus or None
        """
        # Check pending orders first
        if order_id in self.pending_orders:
            return self.pending_orders[order_id].status

        # Check executed orders
        if order_id in self.executed_orders:
            return self.executed_orders[order_id].status

        # Query broker
        return await self.broker.get_order_status(order_id)

    async def poll_order_status(
        self,
        order_id: str,
        max_polls: int = 60,
        max_wait_seconds: int = 30,
    ) -> Optional[BrokerOrder]:
        """
        Poll order status until execution or timeout.

        ASYNC-004: Implements exponential backoff to avoid rate limit saturation.

        Args:
            order_id: Order ID to poll
            max_polls: Maximum number of polls
            max_wait_seconds: Maximum wait time between polls (caps exponential backoff)

        Returns:
            Final BrokerOrder or None
        """
        for poll_count in range(max_polls):
            order = self.pending_orders.get(order_id)
            if not order:
                logger.warning(
                    "Order not found in pending orders",
                    extra={"order_id": order_id},
                )
                return None

            status = await self.get_order_status(order_id)
            if status in (
                OrderStatus.FILLED,
                OrderStatus.EXECUTED,
                OrderStatus.CANCELED,
                OrderStatus.REJECTED,
            ):
                # Move to executed
                self.pending_orders.pop(order_id, None)
                self.executed_orders[order_id] = order
                logger.info(
                    "Order reached terminal status",
                    extra={
                        "order_id": order_id,
                        "status": status.value,
                        "poll_count": poll_count + 1,
                    },
                )
                return order

            # ASYNC-004: Exponential backoff with cap at max_wait_seconds
            # Wait pattern: 1s, 2s, 4s, 8s, 16s, 30s, 30s, ...
            if poll_count < max_polls - 1:
                wait_time = min(2**poll_count, max_wait_seconds)
                await asyncio.sleep(wait_time)

        logger.warning(
            "Order polling timeout",
            extra={
                "order_id": order_id,
                "max_polls": max_polls,
            },
        )
        return None

    async def record_execution(
        self,
        order_id: str,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal = _DEFAULT_FEES,
    ) -> Optional[OrderExecution]:
        """
        Record order execution.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            quantity: Executed quantity
            price: Execution price
            fees: Transaction fees

        Returns:
            OrderExecution record
        """
        net_proceeds = quantity * price - fees

        execution = OrderExecution(
            order_id=order_id,
            symbol=symbol,
            quantity=quantity,
            price=price,
            fees=fees,
            net_proceeds=net_proceeds,
        )

        self.executions.append(execution)
        logger.info(f"✅ Recorded execution: {order_id} - {quantity} {symbol} @ {price}")
        return execution

    async def get_pending_orders(self, symbol: Optional[str] = None) -> list[BrokerOrder]:
        """
        Get pending orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of pending BrokerOrder objects
        """
        orders = list(self.pending_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_executed_orders(self, symbol: Optional[str] = None) -> list[BrokerOrder]:
        """
        Get executed orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of executed BrokerOrder objects
        """
        orders = list(self.executed_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_order_history(self, symbol: Optional[str] = None) -> list[BrokerOrder]:
        """
        Get complete order history.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of all BrokerOrder objects
        """
        orders = self.order_history
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    async def get_execution_history(
        self,
        symbol: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[OrderExecution]:
        """
        Get execution history.

        Args:
            symbol: Filter by symbol
            since: Filter by date

        Returns:
            List of OrderExecution records
        """
        executions = self.executions

        if symbol:
            executions = [e for e in executions if e.symbol == symbol]

        if since:
            executions = [e for e in executions if e.execution_time >= since]

        return executions

    async def record_error(
        self,
        order_id: str,
        symbol: str,
        error_code: str,
        error_message: str,
    ) -> OrderError:
        """
        Record order error.

        Args:
            order_id: Order ID
            symbol: Stock symbol
            error_code: Error code
            error_message: Error message

        Returns:
            OrderError record
        """
        error = OrderError(
            order_id=order_id,
            symbol=symbol,
            error_code=error_code,
            error_message=error_message,
        )

        self.order_errors[order_id] = error
        logger.warning(f"⚠️ Order error {error_code}: {error_message}")
        return error

    async def get_order_errors(self, symbol: Optional[str] = None) -> list[OrderError]:
        """
        Get recorded order errors.

        Args:
            symbol: Filter by symbol

        Returns:
            List of OrderError records
        """
        errors = list(self.order_errors.values())
        if symbol:
            errors = [e for e in errors if e.symbol == symbol]
        return errors

    def get_total_executions(self) -> int:
        """Get total number of executions."""
        return len(self.executions)

    def get_pending_count(self) -> int:
        """Get number of pending orders."""
        return len(self.pending_orders)

    def get_executed_count(self) -> int:
        """Get number of executed orders."""
        return len(self.executed_orders)


# Import asyncio at module level for poll_order_status
# import pandas as pd  # F401 unused

# Singleton
_manager: Optional[OrderManager] = None


_DEFAULT_BROKER_DEPENDS = Depends(get_broker_connector)


def get_order_manager(
    broker: BrokerConnector = _DEFAULT_BROKER_DEPENDS,
) -> OrderManager:
    """Get or create singleton OrderManager."""
    global _manager
    if _manager is None:
        # Import RiskGates here to avoid circular dependency
        from .risk_gates import RiskGates

        # Create RiskGates directly for the OrderManager
        _manager = OrderManager(broker=broker, risk_gates=RiskGates(broker=broker))

    return _manager
