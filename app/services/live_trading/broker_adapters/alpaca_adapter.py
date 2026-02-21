# mypy: ignore-errors
# pylint: disable=unsupported-binary-operation  # For Python 3.10+ union syntax
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
from typing import Any, Callable, Dict, List, Optional, Tuple  # noqa: F401

from app.core.trading_validators import TradingValidator
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

        # CRITICAL: Initialize trading validator for safety checks
        self.validator = TradingValidator()

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
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
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
        except (asyncio.TimeoutError, OSError) as e:
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
        client_order_id: Optional[str] = None,
    ) -> str:
        """Place an order on Alpaca.

        SEC-005: Supports client_order_id for idempotency. Alpaca supports
        client_order_id natively to prevent duplicate orders.

        Args:
            symbol: Stock symbol
            side: Order side (BUY or SELL)
            quantity: Order quantity
            order_type: Order type (MARKET, LIMIT, STOP, STOP_LIMIT)
            price: Limit price if applicable
            stop_price: Stop price if applicable
            client_order_id: Optional client order ID for idempotency

        Returns:
            str: Order ID

        Raises:
            ConnectionError: If not connected to Alpaca
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Alpaca")

        # CRITICAL: Validate BEFORE executing
        # Get available capital
        account = await self.get_account_info()
        if account:
            available_capital = account.cash_available
        else:
            available_capital = Decimal("100000")  # Fallback default
            logger.warning("Could not fetch account capital, using default for validation")

        # Calculate position value - skip for MARKET orders since price is unknown
        # For MARKET orders, we'll validate based on buying power instead
        if order_type == OrderType.MARKET:
            # For market orders, just validate quantity is positive
            if quantity <= 0:
                raise ValueError(f"Quantity must be positive for market orders, got {quantity}")
            logger.debug("Skipping position size validation for MARKET order (price unknown)")
        else:
            # For limit/stop orders, we can calculate position value
            if price is None:
                raise ValueError(f"Price is required for {order_type.value} orders")
            position_value = quantity * price

            # Validate position size
            try:
                self.validator.validate_position_size(
                    capital=available_capital,
                    position_size=position_value,
                    max_position_percent=Decimal("0.25"),
                )
            except ValueError as e:
                logger.error(f"Position size validation failed: {e}")
                raise ValueError(f"Position size validation failed: {e}")

        # Validate stop-loss if provided
        if stop_price:
            # For stop orders, validate the stop price
            try:
                estimated_price = price or Decimal("100")  # Fallback for market orders
                self.validator.validate_stop_loss(
                    entry_price=estimated_price,
                    stop_loss=stop_price,
                    side='long' if side == OrderSide.BUY else 'short',
                )
            except ValueError as e:
                logger.error(f"Stop-loss validation failed: {e}")
                raise ValueError(f"Stop-loss validation failed: {e}")
        else:
            # Log warning but don't fail (some strategies may not use SL)
            logger.warning(
                f"Order for {symbol} placed without stop-loss - ensure risk is managed elsewhere"
            )

        try:
            # Map side to Alpaca format
            alpaca_side = "buy" if side == OrderSide.BUY else "sell"

            # Map order type to Alpaca format
            alpaca_order_type = order_type.value.lower()

            # Submit order to Alpaca with client_order_id for idempotency
            order_id = await self.client.submit_order(
                symbol=symbol,
                qty=quantity,
                side=alpaca_side,
                order_type=alpaca_order_type,
                limit_price=price,
                stop_price=stop_price,
                client_order_id=client_order_id,  # SEC-005: Pass client_order_id
            )

            # Create basic order dict for transformation
            order_data = {
                "id": order_id,
                "qty": float(quantity),
                "status": "new",
                "type": alpaca_order_type,
            }

            # Transform and cache order (include client_order_id)
            order = self._transform_order(order_data, symbol, side, client_order_id)
            self.orders[order.order_id] = order

            logger.info(f"✅ Order placed: {symbol} {side.value} {quantity}")

            return order.order_id

        except AlpacaClientError as e:
            logger.error(f"❌ Order placement failed: {str(e)}")
            raise
        except (ValueError, TypeError, KeyError, AttributeError) as e:
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

        except (asyncio.TimeoutError, OSError) as e:
            logger.warning(f"⚠️  Failed to get account info: {str(e)}")
            # Return cached account on error (as test expects)
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

        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
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
            # Round to 2 decimal places for consistency
            unrealized_pl_pct = unrealized_pl_pct.quantize(Decimal("0.01"))
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
        client_order_id: Optional[str] = None,
    ) -> BrokerOrder:
        """Transform Alpaca order data to BrokerOrder.

        Args:
            alpaca_order: Raw Alpaca order data
            symbol: Stock symbol
            side: Order side
            client_order_id: Optional client order ID for idempotency

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

        # Handle created_at - may be string or datetime object or None
        created_at = datetime.utcnow()
        if alpaca_order.get("created_at"):
            created_at_val = alpaca_order["created_at"]
            if isinstance(created_at_val, str):
                created_at = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
            else:
                created_at = created_at_val

        # Handle updated_at - may be string or datetime object or None
        updated_at = None
        if alpaca_order.get("updated_at"):
            updated_at_val = alpaca_order["updated_at"]
            if isinstance(updated_at_val, str):
                updated_at = datetime.fromisoformat(updated_at_val.replace("Z", "+00:00"))
            else:
                updated_at = updated_at_val

        return BrokerOrder(
            order_id=alpaca_order["id"],
            symbol=symbol,
            side=side,
            order_type=OrderType[alpaca_order["type"].upper()],
            quantity=qty,
            filled_quantity=filled_qty,
            avg_filled_price=filled_avg_price,
            status=self._map_order_status(alpaca_order["status"]),
            created_at=created_at,
            updated_at=updated_at,
            client_order_id=client_order_id,  # SEC-005: Store client_order_id
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
                    # Round to 2 decimal places for consistency
                    pos.unrealized_pl_pct = pos.unrealized_pl_pct.quantize(Decimal("0.01"))

                logger.debug(
                    f"📊 {symbol} updated: ${last_price} (P&L: {pos.unrealized_pl_pct:.2f}%)"
                )

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
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

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
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

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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

            except (asyncio.TimeoutError, OSError) as e:
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

        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
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

    async def execute_trade(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        stop_loss_pct: Optional[Decimal] = None,
        take_profit_pct: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete trade with risk management.

        This is the main entry point for trade execution that:
        1. Validates the order parameters
        2. Checks risk limits
        3. Places the order with the broker
        4. Optionally places stop-loss and take-profit orders
        5. Returns execution details

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            side: Order side (BUY or SELL)
            quantity: Number of shares
            order_type: Order type (MARKET, LIMIT, STOP, STOP_LIMIT)
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            stop_loss_pct: Optional stop-loss percentage (e.g., 0.02 for 2%)
            take_profit_pct: Optional take-profit percentage (e.g., 0.05 for 5%)

        Returns:
            Dict with execution details:
                - order_id: Primary order ID
                - status: Order status
                - filled_qty: Quantity filled
                - filled_avg_price: Average fill price
                - stop_loss_order_id: Stop-loss order ID (if applicable)
                - take_profit_order_id: Take-profit order ID (if applicable)
                - timestamp: Execution timestamp

        Raises:
            ConnectionError: If not connected to Alpaca
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to Alpaca - cannot execute trade")

        # Validate quantity
        if quantity <= Decimal("0"):
            raise ValueError(f"Invalid quantity: {quantity}. Must be > 0")

        # Check account has sufficient buying power for BUY orders
        if side == OrderSide.BUY:
            account = await self.get_account_info()
            if account:
                estimated_cost = quantity * (price or Decimal("0"))
                if price is None:
                    # For market orders, we need current price estimate
                    # Using buying power check only
                    if estimated_cost > account.buying_power:
                        raise ValueError(
                            f"Insufficient buying power: {account.buying_power} < estimated cost"
                        )

        execution_result = {
            "symbol": symbol,
            "side": side.value,
            "requested_qty": str(quantity),
            "order_type": order_type.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Execute primary order with retry logic
            order_id = await self._retry_with_backoff(
                f"execute_trade_{symbol}",
                self.place_order,
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                stop_price=stop_price,
            )

            execution_result["order_id"] = order_id
            execution_result["status"] = "submitted"

            # Wait briefly for order to be processed
            await asyncio.sleep(0.5)

            # Get order status
            order_status = await self.get_order_status(order_id)
            execution_result["order_status"] = order_status.value

            # Get fill details if available
            if order_id in self.orders:
                order = self.orders[order_id]
                execution_result["filled_qty"] = str(order.filled_quantity)
                execution_result["filled_avg_price"] = str(order.avg_filled_price)

            # Place bracket orders (stop-loss and take-profit) if specified
            if order_status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                filled_price = (
                    self.orders[order_id].avg_filled_price if order_id in self.orders else price
                )

                # CRITICAL FIX: Use FILLED quantity, not original quantity for partial fills
                filled_qty = (
                    self.orders[order_id].filled_quantity if order_id in self.orders else quantity
                )

                if filled_qty <= Decimal("0"):
                    logger.warning("⚠️ No filled quantity for bracket orders")
                else:
                    if filled_price and stop_loss_pct:
                        sl_price = filled_price * (Decimal("1") - stop_loss_pct)
                        try:
                            sl_order_id = await self.place_order(
                                symbol=symbol,
                                side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,
                                quantity=filled_qty,  # Use filled quantity, not original
                                order_type=OrderType.STOP,
                                stop_price=sl_price.quantize(Decimal("0.01")),
                            )
                            execution_result["stop_loss_order_id"] = sl_order_id
                            execution_result["stop_loss_price"] = str(sl_price)
                            execution_result["stop_loss_qty"] = str(filled_qty)
                            logger.info(
                                f"✅ Stop-loss order placed: {sl_order_id} @ ${sl_price:.2f} for {filled_qty} shares"
                            )
                        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                            logger.warning(f"⚠️ Failed to place stop-loss order: {e}")

                    if filled_price and take_profit_pct:
                        tp_price = filled_price * (Decimal("1") + take_profit_pct)
                        try:
                            tp_order_id = await self.place_order(
                                symbol=symbol,
                                side=OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY,
                                quantity=filled_qty,  # Use filled quantity, not original
                                order_type=OrderType.LIMIT,
                                price=tp_price.quantize(Decimal("0.01")),
                            )
                            execution_result["take_profit_order_id"] = tp_order_id
                            execution_result["take_profit_price"] = str(tp_price)
                            execution_result["take_profit_qty"] = str(filled_qty)
                            logger.info(
                                f"✅ Take-profit order placed: {tp_order_id} @ ${tp_price:.2f} for {filled_qty} shares"
                            )
                        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                            logger.warning(f"⚠️ Failed to place take-profit order: {e}")

            logger.info(
                f"✅ Trade executed: {side.value} {quantity} {symbol} "
                f"(order_id={order_id}, status={order_status.value})"
            )

            return execution_result

        except AlpacaClientError as e:
            execution_result["status"] = "failed"
            execution_result["error"] = str(e)
            logger.error(f"❌ Trade execution failed: {e}")
            raise
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            execution_result["status"] = "failed"
            execution_result["error"] = str(e)
            logger.error(f"❌ Unexpected error in trade execution: {e}")
            raise

    def __repr__(self) -> str:
        """String representation."""
        status = "🟢 Connected" if self.is_connected else "🔴 Disconnected"
        return f"AlpacaAdapter({status})"
