"""
Alpaca Adapter - Implements BrokerConnector interface for Alpaca.

Maps between:
- Low-level AlpacaClient API calls
- Standard BrokerConnector interface (BrokerOrder, BrokerPosition, BrokerAccount)
- Application-level requirements (risk gates, order manager, etc.)
- Error recovery and resilience
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from app.services.live_trading.broker_connector import (
    BrokerAccount,
    BrokerOrder,
    BrokerPosition,
    BrokerType,
    OrderSide,
    OrderStatus,
    OrderType,
)

from .alpaca_client import AlpacaClient, AlpacaClientError
from .alpaca_error_handler import (
    AlpacaErrorClassifier,
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
    RetryConfig,
)

logger = logging.getLogger(__name__)


class AlpacaAdapter:
    """Adapter to implement BrokerConnector interface for Alpaca."""

    def __init__(self):
        """Initialize Alpaca adapter with error recovery."""
        self.client = AlpacaClient()
        self.account: Optional[BrokerAccount] = None
        self.positions: Dict[str, BrokerPosition] = {}
        self.orders: Dict[str, BrokerOrder] = {}
        self.is_connected = False

        # Error recovery and resilience
        self.error_manager = ErrorRecoveryManager()
        self.error_classifier = AlpacaErrorClassifier()
        self.retry_config = RetryConfig(max_attempts=3, base_delay=1.0)

        # Recovery callbacks
        self.on_circuit_break: Optional[Callable[[], None]] = None
        self.on_sync_error: Optional[Callable[[Exception], None]] = None

    async def connect(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        paper_trading: bool = True,
        base_url: str = "https://paper-api.alpaca.markets",
        **kwargs,
    ) -> bool:
        """Connect to Alpaca broker.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            account_id: Account ID (optional, retrieved from Alpaca)
            paper_trading: Use paper trading (True) or live (False)
            base_url: API endpoint URL
            **kwargs: Additional arguments

        Returns:
            bool: True if connection successful
        """
        if not api_key or not api_secret:
            logger.error("❌ Alpaca API key and secret are required")
            return False

        try:
            # Authenticate with Alpaca
            await self.client.authenticate(
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                paper_trading=paper_trading,
            )

            # Get account info
            account_data = await self.client.get_account()
            self.account = self._transform_account(account_data)

            # Get initial positions
            positions_data = await self.client.get_positions()
            self.positions = {
                pos["symbol"]: self._transform_position(pos) for pos in positions_data
            }

            # Register streaming handlers for real-time updates
            self.client.register_quote_handler(self._on_quote_update)
            self.client.register_trade_handler(self._on_trade_update)
            self.client.register_order_handler(self._on_order_update)
            self.client.register_error_handler(self._on_stream_error)

            # Start WebSocket streaming for real-time updates
            await self.client.start_stream()

            self.is_connected = True
            logger.info(f"✅ Connected to Alpaca (Account: {self.account.account_id})")

            return True

        except AlpacaClientError as e:
            logger.error(f"❌ Alpaca connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during connection: {str(e)}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Alpaca broker.

        Returns:
            bool: True if disconnection successful
        """
        try:
            await self.client.stop_stream()
            self.is_connected = False
            logger.info("✅ Disconnected from Alpaca")
            return True
        except Exception as e:
            logger.error(f"❌ Error during disconnect: {str(e)}")
            return False

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
    ) -> str:
        """Place an order on Alpaca.

        Args:
            symbol: Stock symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, STOP, STOP_LIMIT)
            price: Limit price if applicable
            stop_price: Stop price if applicable

        Returns:
            str: Order ID

        Raises:
            Exception: If order placement fails
        """
        if not self.is_connected:
            raise Exception("Not connected to Alpaca")

        try:
            # Map side to Alpaca format
            alpaca_side = "buy" if side == OrderSide.BUY else "sell"

            # Map order type to Alpaca format
            alpaca_order_type = order_type.value.lower()

            # Submit order to Alpaca
            order_data = await self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=alpaca_side,
                order_type=alpaca_order_type,
                limit_price=price,
                stop_price=stop_price,
            )

            # Transform and cache order
            order = self._transform_order(order_data, symbol, side)
            self.orders[order.order_id] = order

            logger.info(f"✅ Order placed: {symbol} {side.value} {quantity}")

            return order.order_id

        except AlpacaClientError as e:
            logger.error(f"❌ Order placement failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error placing order: {str(e)}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Alpaca.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation successful
        """
        if not self.is_connected:
            return False

        try:
            await self.client.cancel_order(order_id)

            # Update local order status
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELED

            logger.info(f"✅ Order {order_id} cancelled")
            return True

        except AlpacaClientError as e:
            logger.error(f"❌ Order cancellation failed: {str(e)}")
            return False

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get order status from Alpaca.

        Args:
            order_id: Order ID to query

        Returns:
            OrderStatus: Current order status
        """
        if not self.is_connected:
            return OrderStatus.PENDING

        try:
            order_data = await self.client.get_order(order_id)
            return self._map_order_status(order_data["status"])

        except AlpacaClientError as e:
            logger.warning(f"⚠️  Failed to get order status: {str(e)}")
            # Return cached status if available
            if order_id in self.orders:
                return self.orders[order_id].status
            return OrderStatus.PENDING

    async def get_account_info(self) -> Optional[BrokerAccount]:
        """Get account information from Alpaca.

        Returns:
            BrokerAccount: Account information or None if failed
        """
        if not self.is_connected:
            return self.account

        try:
            account_data = await self.client.get_account()
            self.account = self._transform_account(account_data)
            return self.account

        except AlpacaClientError as e:
            logger.warning(f"⚠️  Failed to get account info: {str(e)}")
            return self.account

    async def get_positions(self) -> List[BrokerPosition]:
        """Get all open positions from Alpaca.

        Returns:
            list: List of BrokerPosition objects
        """
        if not self.is_connected:
            return list(self.positions.values())

        try:
            positions_data = await self.client.get_positions()

            self.positions = {
                pos["symbol"]: self._transform_position(pos) for pos in positions_data
            }

            return list(self.positions.values())

        except AlpacaClientError as e:
            logger.warning(f"⚠️  Failed to get positions: {str(e)}")
            return list(self.positions.values())

    async def get_position(self, symbol: str) -> Optional[BrokerPosition]:
        """Get a specific position.

        Args:
            symbol: Stock symbol

        Returns:
            BrokerPosition: Position info or None if not found
        """
        positions = await self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    async def update_positions(self) -> Dict[str, BrokerPosition]:
        """Update all positions (alias for get_positions).

        Returns:
            dict: Dictionary of symbol -> BrokerPosition
        """
        positions = await self.get_positions()
        return {pos.symbol: pos for pos in positions}

    async def sync_account_balance(self) -> bool:
        """Synchronize account balance from Alpaca.

        Returns:
            bool: True if sync successful
        """
        try:
            account_data = await self.client.get_account()
            self.account = self._transform_account(account_data)
            return True
        except AlpacaClientError as e:
            logger.warning(f"⚠️  Failed to sync account balance: {str(e)}")
            return False

    async def calculate_portfolio_value(self) -> Optional[Decimal]:
        """Calculate current portfolio value.

        Returns:
            Decimal: Portfolio value or None if failed
        """
        account = await self.get_account_info()
        return account.portfolio_value if account else None

    # ==================== Data Transformation Methods ====================

    def _transform_account(self, alpaca_account: Dict[str, Any]) -> BrokerAccount:
        """Transform Alpaca account data to BrokerAccount.

        Args:
            alpaca_account: Raw Alpaca account data

        Returns:
            BrokerAccount: Standardized account object
        """
        return BrokerAccount(
            account_id=alpaca_account["account_number"],
            broker_type=BrokerType.ALPACA,
            currency="USD",
            cash_available=Decimal(str(alpaca_account["cash"])),
            portfolio_value=Decimal(str(alpaca_account["portfolio_value"])),
            buying_power=Decimal(str(alpaca_account["buying_power"])),
            equity=Decimal(str(alpaca_account["equity"])),
            margin_used=Decimal(
                str(float(alpaca_account["multiplier"]) - 1.0)
            ),  # margin = multiplier - 1
            multiplier=Decimal(str(alpaca_account["multiplier"])),
        )

    def _transform_position(self, alpaca_pos: Dict[str, Any]) -> BrokerPosition:
        """Transform Alpaca position data to BrokerPosition.

        Args:
            alpaca_pos: Raw Alpaca position data

        Returns:
            BrokerPosition: Standardized position object
        """
        qty = Decimal(str(alpaca_pos["qty"]))
        avg_price = Decimal(str(alpaca_pos["avg_fill_price"]))
        current_price = Decimal(str(alpaca_pos["current_price"]))

        market_value = qty * current_price
        unrealized_pl = (current_price - avg_price) * qty

        # Calculate unrealized P&L percentage
        if market_value != 0:
            unrealized_pl_pct = (unrealized_pl / market_value) * Decimal("100")
        else:
            unrealized_pl_pct = Decimal("0")

        return BrokerPosition(
            symbol=alpaca_pos["symbol"],
            quantity=qty,
            avg_price=avg_price,
            current_price=current_price,
            market_value=market_value,
            unrealized_pl=unrealized_pl,
            unrealized_pl_pct=unrealized_pl_pct,
        )

    def _transform_order(
        self,
        alpaca_order: Dict[str, Any],
        symbol: str,
        side: OrderSide,
    ) -> BrokerOrder:
        """Transform Alpaca order data to BrokerOrder.

        Args:
            alpaca_order: Raw Alpaca order data
            symbol: Stock symbol
            side: Order side

        Returns:
            BrokerOrder: Standardized order object
        """
        qty = Decimal(str(alpaca_order["qty"]))
        filled_qty = Decimal(str(alpaca_order.get("filled_qty", 0)))
        filled_avg_price = (
            Decimal(str(alpaca_order["filled_avg_price"]))
            if alpaca_order.get("filled_avg_price")
            else Decimal("0")
        )

        return BrokerOrder(
            order_id=alpaca_order["id"],
            symbol=symbol,
            side=side,
            order_type=OrderType[alpaca_order["type"].upper()],
            quantity=qty,
            filled_quantity=filled_qty,
            avg_filled_price=filled_avg_price,
            status=self._map_order_status(alpaca_order["status"]),
            created_at=(
                datetime.fromisoformat(alpaca_order["created_at"].replace("Z", "+00:00"))
                if alpaca_order.get("created_at")
                else datetime.utcnow()
            ),
            updated_at=(
                datetime.fromisoformat(alpaca_order["updated_at"].replace("Z", "+00:00"))
                if alpaca_order.get("updated_at")
                else None
            ),
        )

    def _map_order_status(self, alpaca_status: str) -> OrderStatus:
        """Map Alpaca order status to standard OrderStatus.

        Args:
            alpaca_status: Alpaca status string

        Returns:
            OrderStatus: Standard order status
        """
        status_map = {
            "new": OrderStatus.SUBMITTED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "done_for_day": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "expired": OrderStatus.EXPIRED,
            "pending_new": OrderStatus.PENDING,
            "accepted": OrderStatus.ACKNOWLEDGED,
            "pending_cancel": OrderStatus.PENDING,
            "pending_replace": OrderStatus.PENDING,
            "stopped": OrderStatus.PENDING,
            "rejected": OrderStatus.REJECTED,
            "suspended": OrderStatus.PENDING,
            "calculated": OrderStatus.PENDING,
        }

        return status_map.get(alpaca_status.lower(), OrderStatus.PENDING)

    # ==================== WebSocket Event Handlers ====================

    def _on_quote_update(self, quote_data: Dict[str, Any]) -> None:
        """Handle real-time quote update from WebSocket.

        Updates cached position prices and calculates P&L.

        Args:
            quote_data: Quote message from Alpaca WebSocket
        """
        try:
            symbol = quote_data.get("S")
            bid_price = Decimal(str(quote_data.get("bp", 0)))
            ask_price = Decimal(str(quote_data.get("ap", 0)))
            last_price = (bid_price + ask_price) / Decimal("2")  # Midpoint

            # Update position if we have one
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos.current_price = last_price

                # Recalculate P&L
                pos.market_value = pos.quantity * pos.current_price
                pos.unrealized_pl = (pos.current_price - pos.avg_price) * pos.quantity

                if pos.market_value != Decimal("0"):
                    pos.unrealized_pl_pct = (pos.unrealized_pl / pos.market_value) * Decimal("100")

                logger.debug(
                    f"📊 {symbol} updated: ${last_price} (P&L: {pos.unrealized_pl_pct:.2f}%)"
                )

        except Exception as e:
            logger.error(f"❌ Error processing quote update: {str(e)}")

    def _on_trade_update(self, trade_data: Dict[str, Any]) -> None:
        """Handle real-time trade/execution update from WebSocket.

        Updates order status and position on execution.

        Args:
            trade_data: Trade message from Alpaca WebSocket
        """
        try:
            symbol = trade_data.get("S")
            price = Decimal(str(trade_data.get("p", 0)))
            size = Decimal(str(trade_data.get("s", 0)))

            logger.info(f"🔔 Trade executed: {symbol} @ ${price} x {size}")

            # Could trigger order completion or position update here
            # For now, just log the event

        except Exception as e:
            logger.error(f"❌ Error processing trade update: {str(e)}")

    def _on_order_update(self, order_data: Dict[str, Any]) -> None:
        """Handle real-time order status update from WebSocket.

        Updates cached order status immediately.

        Args:
            order_data: Order message from Alpaca WebSocket
        """
        try:
            order_id = order_data.get("id")
            status = order_data.get("status")

            if order_id in self.orders:
                old_status = self.orders[order_id].status
                new_status = self._map_order_status(status)

                self.orders[order_id].status = new_status
                self.orders[order_id].filled_quantity = Decimal(
                    str(order_data.get("filled_qty", 0))
                )
                self.orders[order_id].avg_filled_price = Decimal(
                    str(order_data.get("filled_avg_price", 0))
                )

                logger.info(f"📋 Order {order_id}: {old_status.value} → {new_status.value}")

        except Exception as e:
            logger.error(f"❌ Error processing order update: {str(e)}")

    def _on_stream_error(self, error: Exception) -> None:
        """Handle WebSocket stream connection error.

        Args:
            error: Exception from WebSocket connection
        """
        logger.error(f"❌ WebSocket stream error: {str(error)}")
        # Could emit alerts or trigger reconnection strategy here

    # ==================== Error Recovery & Retry Methods ====================

    async def _retry_with_backoff(
        self,
        operation_name: str,
        async_operation,
        *args,
        **kwargs,
    ) -> Any:
        """Execute operation with retry logic and exponential backoff.

        Args:
            operation_name: Name of operation for logging
            async_operation: Async function to execute
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result from operation

        Raises:
            AlpacaClientError: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.retry_config.max_attempts):
            try:
                # Check circuit breaker
                if not self.error_manager.should_allow_request():
                    logger.error(f"❌ Circuit breaker open, skipping {operation_name}")
                    raise AlpacaClientError("Circuit breaker open - service unavailable")

                # Execute operation
                result = await async_operation(*args, **kwargs)
                self.error_manager.handle_request_success()
                logger.debug(f"✅ {operation_name} succeeded")
                return result

            except Exception as e:
                last_error = e
                strategy = self.error_manager.handle_request_failure(e)

                # Check if retryable
                if strategy != ErrorRecoveryStrategy.RETRY:
                    logger.error(f"❌ {operation_name} failed with non-retryable error: {str(e)}")
                    raise

                # Calculate backoff delay
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self.error_manager.get_retry_delay(attempt)
                    logger.warning(
                        f"⚠️  {operation_name} failed (attempt {attempt + 1}/"
                        f"{self.retry_config.max_attempts}), retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(f"❌ {operation_name} failed after {self.retry_config.max_attempts} attempts")
        raise AlpacaClientError(f"{operation_name} failed: {str(last_error)}")

    async def _sync_positions_with_recovery(self) -> Dict[str, BrokerPosition]:
        """Sync positions with error recovery.

        Uses position sync recovery to handle partial failures gracefully.

        Returns:
            dict: Position dictionary
        """
        try:
            positions_data = await self.client.get_positions()
            self.positions = {
                pos["symbol"]: self._transform_position(pos) for pos in positions_data
            }
            self.error_manager.position_sync_recovery.record_sync_success()
            return self.positions

        except Exception as e:
            self.error_manager.position_sync_recovery.record_sync_failure()

            if not self.error_manager.position_sync_recovery.should_retry():
                logger.error("❌ Position sync failed, max retries exhausted")
                if self.on_sync_error:
                    self.on_sync_error(e)
                raise

            # Return cached positions if available
            logger.warning(f"⚠️  Position sync failed, using cached data: {str(e)}")
            return self.positions

    def register_error_callbacks(
        self,
        on_circuit_break: Optional[Callable[[], None]] = None,
        on_sync_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Register error recovery callbacks.

        Args:
            on_circuit_break: Called when circuit breaker opens
            on_sync_error: Called when position sync fails critically
        """
        self.on_circuit_break = on_circuit_break
        self.on_sync_error = on_sync_error
        self.error_manager.on_circuit_open = on_circuit_break
        self.error_manager.on_sync_needed = self._sync_positions_with_recovery
        logger.info("Error recovery callbacks registered")

    def get_error_recovery_status(self) -> Dict[str, Any]:
        """Get current error recovery status.

        Returns:
            dict: Status information
        """
        return {
            "circuit_breaker": {
                "state": self.error_manager.circuit_breaker.state,
                "failures": self.error_manager.circuit_breaker.failure_count,
            },
            "position_sync": {
                "failures": self.error_manager.position_sync_recovery.sync_failure_count,
                "last_sync": str(self.error_manager.position_sync_recovery.last_successful_sync),
                "is_stale": self.error_manager.position_sync_recovery.is_stale(),
            },
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "base_delay": self.retry_config.base_delay,
            },
        }

    # ==================== Status Methods ====================

    def is_paper_trading(self) -> bool:
        """Check if using paper trading mode.

        Returns:
            bool: True if paper trading
        """
        return self.client.base_url == "https://paper-api.alpaca.markets"

    def get_broker_type(self) -> BrokerType:
        """Get broker type.

        Returns:
            BrokerType: Alpaca broker type
        """
        return BrokerType.ALPACA

    def __repr__(self) -> str:
        """String representation."""
        status = "🟢 Connected" if self.is_connected else "🔴 Disconnected"
        return f"AlpacaAdapter({status})"
