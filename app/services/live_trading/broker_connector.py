"""
T16.1.1: BrokerConnector - Broker API integration

Handles connections to broker APIs (Interactive Brokers, Alpaca, IBKR, etc.)
Abstracts broker-specific APIs into unified interface.

Uses adapter pattern to support multiple brokers:
- AlpacaAdapter: Alpaca broker integration
- PaperAdapter: Paper trading for testing/simulation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

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


class BrokerConnector:
    """
    Unified broker API connector.

    Supports multiple brokers with consistent interface.
    Handles authentication, order placement, position tracking, etc.

    Uses adapter pattern - delegates to broker-specific adapters.
    """

    def __init__(self, broker_type: BrokerType = BrokerType.PAPER):
        """Initialize broker connector with appropriate adapter.

        Args:
            broker_type: Type of broker to use
        """
        self.broker_type = broker_type

        # Create broker-specific adapter
        if broker_type == BrokerType.ALPACA:
            from .broker_adapters.alpaca_adapter import AlpacaAdapter

            self.adapter: Any = AlpacaAdapter()
        else:
            # Default to paper trading for all other types
            from .broker_adapters.paper_adapter import PaperAdapter

            self.adapter: Any = PaperAdapter()

        logger.info(f"✅ BrokerConnector initialized for {broker_type.value}")

    # Properties for compatibility
    @property
    def account(self) -> Optional[BrokerAccount]:
        """Get account information."""
        return self.adapter.account

    @property
    def positions(self) -> Dict[str, BrokerPosition]:
        """Get positions."""
        return self.adapter.positions

    @property
    def orders(self) -> Dict[str, BrokerOrder]:
        """Get orders."""
        return self.adapter.orders

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.adapter.is_connected

    async def connect(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Connect to broker API.

        Args:
            api_key: API key for authentication
            api_secret: API secret for authentication
            account_id: Account ID to connect to
            **kwargs: Broker-specific parameters

        Returns:
            True if connection successful
        """
        return await self.adapter.connect(
            api_key=api_key, api_secret=api_secret, account_id=account_id, **kwargs
        )

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

    async def get_positions(self) -> List[BrokerPosition]:
        """
        Get all open positions from broker.

        Returns:
            List of BrokerPosition objects
        """
        return await self.adapter.get_positions()

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
    ) -> str:
        """
        Place order with broker.

        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: Type of order (market, limit, etc.)
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)

        Returns:
            Order ID if successful
        """
        return await self.adapter.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
        )

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

    async def update_positions(self) -> Dict[str, BrokerPosition]:
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

    return _connector
