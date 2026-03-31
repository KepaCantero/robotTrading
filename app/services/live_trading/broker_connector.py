"""
T16.1.1: BrokerConnector - Broker API integration

Handles connections to broker APIs (Interactive Brokers, Alpaca, IBKR, etc.)
Abstracts broker-specific APIs into unified interface.

Uses adapter pattern to support multiple brokers:
- AlpacaAdapter: Alpaca broker integration
- PaperAdapter: Paper trading for testing/simulation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Protocol, Union, runtime_checkable

from app.infrastructure.resilience.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
)

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Supported broker types."""

    INTERACTIVE_BROKERS = "ib"
    ALPACA = "alpaca"
    TRADIER = "tradier"
    IBKR = "ibkr"
    PAPER = "paper"  # Paper trading


class OrderStatus(Enum):
    """Order status states."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    EXECUTED = "executed"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Order types."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """Buy or Sell."""

    BUY = "buy"
    SELL = "sell"


@dataclass
class BrokerAccount:
    """Broker account information."""

    account_id: str
    broker_type: BrokerType
    currency: str = "USD"
    cash_available: Decimal = Decimal("0")
    portfolio_value: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    margin_used: Decimal = Decimal("0")
    multiplier: Decimal = Decimal("1")  # Leverage
    connected: bool = False
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class BrokerPosition:
    """Position from broker."""

    symbol: str
    quantity: Decimal
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_pct: Decimal


@dataclass
class BrokerOrder:
    """Order placed with broker."""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    avg_filled_price: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    client_order_id: Optional[str] = None  # SEC-005: Idempotency key


@runtime_checkable
class BrokerAdapter(Protocol):
    """Protocol defining the interface that all broker adapters must implement."""

    account: Optional[BrokerAccount]
    positions: dict[str, BrokerPosition]
    orders: dict[str, BrokerOrder]
    is_connected: bool

    async def connect(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs: object,
    ) -> bool: ...

    async def disconnect(self) -> bool: ...

    async def get_account_info(self) -> Optional[BrokerAccount]: ...

    async def get_positions(self) -> list[BrokerPosition]: ...

    async def get_position(self, symbol: str) -> Optional[BrokerPosition]: ...

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
    ) -> str: ...

    async def cancel_order(self, order_id: str) -> bool: ...

    async def get_order_status(self, order_id: str) -> OrderStatus: ...

    async def update_positions(self) -> dict[str, BrokerPosition]: ...

    async def sync_account_balance(self) -> bool: ...

    async def calculate_portfolio_value(self) -> Optional[Decimal]: ...

    def is_paper_trading(self) -> bool: ...


class BrokerConnector:
    """
    Unified broker API connector.

    Supports multiple brokers with consistent interface.
    Handles authentication, order placement, position tracking, etc.

    Uses adapter pattern - delegates to broker-specific adapters.
    Includes reconnection manager for handling connection failures.
    """

    def __init__(self, broker_type: BrokerType = BrokerType.PAPER):
        """Initialize broker connector with appropriate adapter.

        Args:
            broker_type: Type of broker to use
        """
        self.broker_type = broker_type

        # Create broker-specific adapter
        adapter: BrokerAdapter
        if broker_type == BrokerType.ALPACA:
            from .broker_adapters.alpaca_adapter import AlpacaAdapter

            adapter = AlpacaAdapter()
        else:
            # Default to paper trading for all other types
            from .broker_adapters.paper_adapter import PaperAdapter

            adapter = PaperAdapter()
        self.adapter = adapter

        # Initialize reconnection manager
        self.reconnection_manager = self._create_reconnection_manager()

        logger.info(f"✅ BrokerConnector initialized for {broker_type.value}")

    # Properties for compatibility
    @property
    def account(self) -> Optional[BrokerAccount]:
        """Get account information."""
        return self.adapter.account

    @property
    def positions(self) -> dict[str, BrokerPosition]:
        """Get positions."""
        return self.adapter.positions

    @property
    def orders(self) -> dict[str, BrokerOrder]:
        """Get orders."""
        return self.adapter.orders

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.adapter.is_connected

    def _create_reconnection_manager(self) -> ReconnectionManager:
        """Create reconnection manager with broker-specific configuration."""

        def on_attempt(attempt: int) -> None:
            """Callback when connection attempt is made."""
            logger.info(f"Broker connection attempt {attempt + 1}")

        def on_success(attempt: int) -> None:
            """Callback when connection succeeds."""
            logger.info(f"Broker reconnected after {attempt + 1} attempts")

        def on_failure() -> None:
            """Callback when all connection attempts fail."""
            logger.error("All broker reconnection attempts failed")

        def alert_callback(attempts: int) -> None:
            """Callback when alert threshold is reached."""
            logger.warning(f"Alert: {attempts} failed broker connection attempts")

        config = ReconnectionConfig(
            max_attempts=10,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
            on_attempt=on_attempt,
            on_success=on_success,
            on_failure=on_failure,
            alert_after_attempts=3,
            alert_callback=alert_callback,
        )

        return ReconnectionManager(
            service_name=f"BrokerConnector_{self.broker_type.value}",
            config=config,
        )

    async def connect(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Connect to broker API with exponential backoff retry.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            account_id: Account ID to connect to
            **kwargs: Broker-specific parameters

        Returns:
            True if connection successful
        """

        async def _connect() -> bool:
            """Internal connection function."""
            return await self.adapter.connect(
                api_key=api_key, api_secret=api_secret, account_id=account_id, **kwargs
            )

        # Use reconnection manager for non-paper trading
        if self.broker_type != BrokerType.PAPER:
            result = await self.reconnection_manager.connect_with_backoff(_connect)
            return result is not False

        # Direct connection for paper trading
        return await _connect()

    async def connect_with_retry(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Connect to broker API with forced retry using reconnection manager.

        This method always uses the reconnection manager regardless of broker type.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            account_id: Account ID to connect to
            **kwargs: Broker-specific parameters

        Returns:
            True if connection successful
        """

        async def _connect() -> bool:
            """Internal connection function."""
            return await self.adapter.connect(
                api_key=api_key, api_secret=api_secret, account_id=account_id, **kwargs
            )

        result = await self.reconnection_manager.connect_with_backoff(_connect)
        return result is not False

    def get_connection_stats(self) -> dict[str, Union[str, int, float, bool, None]]:
        return self.reconnection_manager.get_stats()

    async def disconnect(self) -> bool:
        """
        Disconnect from broker.

        Returns:
            True if disconnected successfully
        """
        return await self.adapter.disconnect()

    async def get_account_info(self) -> Optional[BrokerAccount]:
        """
        Get current account information.

        Returns:
            BrokerAccount or None if not connected
        """
        return await self.adapter.get_account_info()

    async def get_positions(self) -> dict[str, BrokerPosition]:
        """
        Get all open positions from broker.

        Returns:
            Dict of symbol → BrokerPosition
        """
        positions_list = await self.adapter.get_positions()
        return {pos.symbol: pos for pos in positions_list}

    async def get_position(self, symbol: str) -> Optional[BrokerPosition]:
        """
        Get single position by symbol.

        Args:
            symbol: Stock symbol

        Returns:
            BrokerPosition or None
        """
        return await self.adapter.get_position(symbol)

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
    ) -> Optional[BrokerOrder]:
        """
        Place order with broker using client_order_id for idempotency.

        SEC-005: The client_order_id is generated by US (not the broker).
        If the system restarts and re-sends the same order with the same client_order_id:
        - Exchange detects duplicate
        - Rejects the order with "Duplicate Order ID"
        - Returns the ORIGINAL order already existing

        This prevents duplications due to "order in limbo" after crash.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: Type of order (market, limit, etc.)
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            client_order_id: Optional client order ID for idempotency

        Returns:
            BrokerOrder object if successful, None otherwise
        """
        import uuid

        # If not provided, generate from UUID
        if client_order_id is None:
            client_order_id = f"trade_{uuid.uuid4().hex}"

        logger.info(
            "Placing order with idempotency key",
            extra={
                "symbol": symbol,
                "side": side.value,
                "quantity": str(quantity),
                "client_order_id": client_order_id,
            },
        )

        try:
            order_id = await self.adapter.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price,
                stop_price=stop_price,
                client_order_id=client_order_id,
            )
            # Return the full order object from adapter's orders dict
            if order_id:
                logger.info(
                    "Order placed successfully",
                    extra={
                        "order_id": order_id,
                        "client_order_id": client_order_id,
                    },
                )
                return self.adapter.orders.get(order_id)
            else:
                logger.error("Order placement failed")
                return None

        except Exception as e:
            # If error is "Duplicate Order ID", NOT a fatal error
            if "duplicate" in str(e).lower():
                logger.warning(
                    "Duplicate order detected - fetching original",
                    extra={"client_order_id": client_order_id},
                )
                # Try to find existing order by client_order_id
                for order in self.adapter.orders.values():
                    if (
                        hasattr(order, "client_order_id")
                        and order.client_order_id == client_order_id
                    ):
                        return order
            logger.error(f"Error placing order: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order by ID.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if canceled successfully
        """
        return await self.adapter.cancel_order(order_id)

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """
        Get status of order.

        Args:
            order_id: Order ID

        Returns:
            OrderStatus
        """
        return await self.adapter.get_order_status(order_id)

    async def update_positions(self) -> dict[str, BrokerPosition]:
        """
        Update positions from broker.

        Returns:
            Dict of symbol → BrokerPosition
        """
        return await self.adapter.update_positions()

    async def sync_account_balance(self) -> bool:
        """
        Sync account balance from broker.

        Returns:
            True if successful
        """
        return await self.adapter.sync_account_balance()

    async def calculate_portfolio_value(self) -> Optional[Decimal]:
        """
        Calculate total portfolio value.

        Returns:
            Total portfolio value (cash + positions) or None if failed
        """
        return await self.adapter.calculate_portfolio_value()

    def get_broker_type(self) -> BrokerType:
        """Get broker type."""
        return self.broker_type

    def is_paper_trading(self) -> bool:
        """Check if using paper trading."""
        return self.adapter.is_paper_trading()


# Singleton
_connector: Optional[BrokerConnector] = None


def get_broker_connector(broker_type: BrokerType = BrokerType.PAPER) -> BrokerConnector:
    """Get or create singleton BrokerConnector."""
    global _connector
    if _connector is None:
        _connector = BrokerConnector()

    return _connector
