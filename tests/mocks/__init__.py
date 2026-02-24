"""
Mock implementations for external trading APIs.

This module provides mock implementations for Interactive Brokers (IBKR) and Binance
APIs to enable testing and development without real API calls.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.domain.models.momentum import MarketData
from app.domain.models.order import Order, OrderSide, OrderStatus, OrderType
from app.domain.models.portfolio import AssetClass, Position


@dataclass
class MockConfig:
    """
    Configuration for mock trading behavior.

    Centralizes all hardcoded values used in mock implementations
    for better auditability and testing.
    """

    # Connection and processing delays (seconds)
    connection_delay: float = 0.1
    processing_delay: float = 0.05

    # Default prices
    default_price: Decimal = Decimal("100.00")
    default_btc_price: Decimal = Decimal("50000.00")
    default_base_price: Decimal = Decimal("150.00")
    default_spread: Decimal = Decimal("0.01")

    # Market data generation multipliers
    high_price_multiplier: Decimal = Decimal("1.02")
    low_price_multiplier: Decimal = Decimal("0.98")

    # Order execution thresholds
    buy_execution_threshold: Decimal = Decimal("0.95")  # 5% below market
    sell_execution_threshold: Decimal = Decimal("1.05")  # 5% above market

    # Limit order rejection thresholds
    limit_buy_rejection_threshold: Decimal = Decimal("0.9")  # 10% below market
    limit_sell_rejection_threshold: Decimal = Decimal("1.1")  # 10% above market

    # Klines generation
    klines_price_variation_percent: float = 0.01  # 1% variation
    klines_variation_range: int = 10  # Range for variation calculation
    klines_variation_offset: int = 5  # Offset for variation calculation

    # Default balances
    default_usd_balance: Decimal = Decimal("100000")
    default_aapl_balance: Decimal = Decimal("1000")
    default_btc_balance: Decimal = Decimal("1.0")
    default_eth_balance: Decimal = Decimal("10.0")
    default_usdt_balance: Decimal = Decimal("10000.0")

    # Default account values
    default_total_cash: Decimal = Decimal("100000.00")
    default_buying_power: Decimal = Decimal("200000.00")
    default_equity: Decimal = Decimal("150000.00")

    # Volume defaults
    default_volume: Decimal = Decimal("1000000")
    default_klines_volume: str = "100.00000000"
    default_quote_asset_volume: str = "5000000.00000000"
    default_number_of_trades: int = 1000
    default_taker_buy_base_volume: str = "50.00000000"
    default_taker_buy_quote_volume: str = "2500000.00000000"

    # Timestamp multiplier for milliseconds
    timestamp_ms_multiplier: int = 1000


# Global mock configuration instance
MOCK_CONFIG = MockConfig()


class MockConnectionStatus(str, Enum):
    """Mock connection status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


class MockIBKRClient:
    """
    Mock Interactive Brokers client for testing and development.

    Simulates IBKR TWS API behavior without requiring actual connection.
    """

    def __init__(self, account_id: str = "DU123456", config: MockConfig = MOCK_CONFIG):
        self.account_id = account_id
        self.config = config
        self.connection_status = MockConnectionStatus.DISCONNECTED
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        # Store references to original orders
        self.original_orders: Dict[str, Order] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.balances: Dict[str, Decimal] = {
            "USD": self.config.default_usd_balance,
            "AAPL": self.config.default_aapl_balance,
        }  # Default balance
        self._order_counter = 1

    async def connect(self) -> bool:
        """Simulate connection to IBKR."""
        await asyncio.sleep(self.config.connection_delay)
        self.connection_status = MockConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> bool:
        """Simulate disconnection from IBKR."""
        self.connection_status = MockConnectionStatus.DISCONNECTED
        return True

    async def get_account_summary(self) -> Dict[str, Any]:
        """Get mock account summary."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        return {
            "account_id": self.account_id,
            "total_cash": self.config.default_total_cash,
            "buying_power": self.config.default_buying_power,
            "equity": self.config.default_equity,
            "net_liquidation": self.config.default_equity,
            "currency": "USD",
            "timestamp": datetime.utcnow(),
        }

    async def get_positions(self) -> List[Position]:
        """Get mock positions."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        return list(self.positions.values())

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get mock position for specific symbol."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        return self.positions.get(symbol)

    async def place_order(self, order: Order) -> str:
        """Place mock order."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        order_id = f"IBKR_{self._order_counter:06d}"
        self._order_counter += 1

        # Create a copy of the order with updated fields
        order_data = order.model_dump()
        order_data.update(
            {
                "id": order_id,
                "status": OrderStatus.PENDING,
                "created_at": datetime.utcnow(),
            }
        )

        # Create new order instance
        updated_order = Order(**order_data)
        updated_order.order_id = order_id  # Set the broker order ID
        self.orders[order_id] = updated_order

        # Store reference to original order for updates
        self.original_orders[order_id] = order

        # Update the original order object with the new fields
        order.order_id = order_id
        order.id = order_id
        order.status = OrderStatus.PENDING

        # Simulate order execution
        await asyncio.sleep(self.config.processing_delay)

        if self._should_execute_order(updated_order):
            await self._execute_order(updated_order)
            # Update original order with execution results
            order.status = updated_order.status
            order.filled_at = updated_order.filled_at
            order.filled_price = updated_order.filled_price
            order.filled_quantity = updated_order.filled_quantity
        else:
            # Reject orders that cannot be executed
            if updated_order.order_type == OrderType.LIMIT:
                # For LIMIT orders, check if price is too far from market first
                market_data = self.market_data.get(updated_order.symbol)
                if market_data:
                    current_price = market_data.close_price
                    if updated_order.side == OrderSide.BUY:
                        if updated_order.price < current_price * self.config.limit_buy_rejection_threshold:
                            updated_order.status = OrderStatus.REJECTED
                            updated_order.rejected_reason = "Insufficient funds"
                            order.status = OrderStatus.REJECTED
                            order.rejected_reason = "Insufficient funds"
                        else:
                            updated_order.status = OrderStatus.PENDING
                            order.status = OrderStatus.PENDING
                    else:
                        if updated_order.price > current_price * self.config.limit_sell_rejection_threshold:
                            updated_order.status = OrderStatus.REJECTED
                            updated_order.rejected_reason = "Insufficient funds"
                            order.status = OrderStatus.REJECTED
                            order.rejected_reason = "Insufficient funds"
                        else:
                            updated_order.status = OrderStatus.PENDING
                            order.status = OrderStatus.PENDING
                else:
                    updated_order.status = OrderStatus.PENDING
                    order.status = OrderStatus.PENDING
            elif not self._check_balance_for_order(updated_order):
                updated_order.status = OrderStatus.REJECTED
                updated_order.rejected_reason = "Insufficient balance"
                order.status = OrderStatus.REJECTED
                order.rejected_reason = "Insufficient balance"
            else:
                updated_order.status = OrderStatus.PENDING
                order.status = OrderStatus.PENDING

        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel mock order."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.REJECTED,
            ]:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.utcnow()

                # Update original order if it exists
                if order_id in self.original_orders:
                    original_order = self.original_orders[order_id]
                    original_order.status = OrderStatus.CANCELLED
                    original_order.cancelled_at = datetime.utcnow()

                return True

        return False

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get mock market data."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        return self.market_data.get(symbol)

    async def subscribe_market_data(self, symbol: str) -> bool:
        """Subscribe to mock market data."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to IBKR")

        # Generate mock market data
        base_price = Decimal("150.00")
        spread = Decimal("0.01")

        self.market_data[symbol] = MarketData(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            open_price=base_price,
            high_price=base_price * self.config.high_price_multiplier,
            low_price=base_price * self.config.low_price_multiplier,
            close_price=base_price,
            volume=self.config.default_volume,
            bid=base_price - spread / Decimal("2"),
            ask=base_price + spread / Decimal("2"),
            spread=spread,
        )

        return True

    def _should_execute_order(self, order: Order) -> bool:
        """Determine if order should be executed."""
        # Check balance first
        if not self._check_balance_for_order(order):
            return False

        # Simple mock logic: execute if price is reasonable
        if order.order_type == OrderType.MARKET:
            return True

        if order.order_type == OrderType.LIMIT:
            market_data = self.market_data.get(order.symbol)
            if market_data:
                current_price = market_data.close_price
            else:
                current_price = self.config.default_price

            if order.side == OrderSide.BUY:
                return order.price >= current_price * self.config.buy_execution_threshold
            return order.price <= current_price * self.config.sell_execution_threshold

        return False

    def _check_balance_for_order(self, order: Order) -> bool:
        """Check if there's sufficient balance for the order."""
        try:
            if order.side == OrderSide.BUY:
                required_balance = order.quantity * order.price
                available_balance = self.balances.get("USD", self.config.default_usd_balance)
                return available_balance >= required_balance
            # For sell orders, check if we have the asset
            available_quantity = self.balances.get(order.symbol, Decimal("0"))
            return available_quantity >= order.quantity
        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            return False

    async def _execute_order(self, order: Order):
        """Execute mock order."""
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.filled_price = (
            order.price
            if order.order_type == OrderType.LIMIT
            else self._get_market_price(order.symbol)
        )
        order.filled_quantity = order.quantity

        # Update position
        if order.symbol in self.positions:
            position = self.positions[order.symbol]
            if order.side == OrderSide.BUY:
                position.quantity += order.filled_quantity
                position.avg_price = (
                    position.avg_price * (position.quantity - order.filled_quantity)
                    + order.filled_price * order.filled_quantity
                ) / position.quantity
            else:
                position.quantity -= order.filled_quantity
        else:
            if order.side == OrderSide.BUY:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.filled_quantity,
                    avg_price=order.filled_price,
                    market_price=order.filled_price,
                    asset_class=AssetClass.EQUITY,
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    broker="IBKR",
                )

    def _get_market_price(self, symbol: str) -> Decimal:
        """Get mock market price."""
        market_data = self.market_data.get(symbol)
        if market_data:
            return market_data.close_price
        return self.config.default_price


class MockBinanceClient:
    """
    Mock Binance client for testing and development.

    Simulates Binance API behavior without requiring actual connection.
    """

    def __init__(
        self,
        api_key: str = "mock_api_key",
        api_secret: str = "mock_api_secret",
        config: MockConfig = MOCK_CONFIG,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.config = config
        self.connection_status = MockConnectionStatus.DISCONNECTED
        self.balances: Dict[str, Decimal] = {}
        self.orders: Dict[str, Order] = {}
        # Store references to original orders
        self.original_orders: Dict[str, Order] = {}
        self.market_data: Dict[str, MarketData] = {}
        self._order_counter = 1

    async def connect(self) -> bool:
        """Simulate connection to Binance."""
        await asyncio.sleep(self.config.connection_delay)
        self.connection_status = MockConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> bool:
        """Simulate disconnection from Binance."""
        self.connection_status = MockConnectionStatus.DISCONNECTED
        return True

    async def get_account_info(self) -> Dict[str, Any]:
        """Get mock account info."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        return {
            "account_type": "SPOT",
            "can_trade": True,
            "can_withdraw": True,
            "can_deposit": True,
            "balances": [
                {
                    "asset": "BTC",
                    "free": str(self.config.default_btc_balance),
                    "locked": "0.00000000",
                },
                {
                    "asset": "ETH",
                    "free": str(self.config.default_eth_balance),
                    "locked": "0.00000000",
                },
                {
                    "asset": "USDT",
                    "free": str(self.config.default_usdt_balance),
                    "locked": "0.00000000",
                },
            ],
            "timestamp": datetime.utcnow(),
        }

    async def get_balance(self, asset: str) -> Decimal:
        """Get mock balance for asset."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        return self.balances.get(asset, Decimal("0"))

    async def place_order(self, order: Order) -> str:
        """Place mock order."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        order_id = f"BINANCE_{self._order_counter:06d}"
        self._order_counter += 1

        # Create a copy of the order with updated fields
        order_data = order.model_dump()
        order_data.update(
            {
                "id": order_id,
                "status": OrderStatus.PENDING,
                "created_at": datetime.utcnow(),
            }
        )

        # Create new order instance
        updated_order = Order(**order_data)
        updated_order.order_id = order_id  # Set the broker order ID
        self.orders[order_id] = updated_order

        # Store reference to original order for updates
        self.original_orders[order_id] = order

        # Update the original order object with the new fields
        order.order_id = order_id
        order.id = order_id
        order.status = OrderStatus.PENDING

        # Simulate order execution
        await asyncio.sleep(self.config.processing_delay)

        if self._should_execute_order(updated_order):
            await self._execute_order(updated_order)
            # Update original order with execution results
            order.status = updated_order.status
            order.filled_at = updated_order.filled_at
            order.filled_price = updated_order.filled_price
            order.filled_quantity = updated_order.filled_quantity
        else:
            # Reject orders that cannot be executed
            if updated_order.order_type == OrderType.LIMIT:
                # For LIMIT orders, check if price is too far from market first
                market_data = self.market_data.get(updated_order.symbol)
                if market_data:
                    current_price = market_data.close_price
                    if updated_order.side == OrderSide.BUY:
                        if updated_order.price < current_price * self.config.limit_buy_rejection_threshold:
                            updated_order.status = OrderStatus.REJECTED
                            updated_order.rejected_reason = "Insufficient funds"
                            order.status = OrderStatus.REJECTED
                            order.rejected_reason = "Insufficient funds"
                        else:
                            updated_order.status = OrderStatus.PENDING
                            order.status = OrderStatus.PENDING
                    else:
                        if updated_order.price > current_price * self.config.limit_sell_rejection_threshold:
                            updated_order.status = OrderStatus.REJECTED
                            updated_order.rejected_reason = "Insufficient funds"
                            order.status = OrderStatus.REJECTED
                            order.rejected_reason = "Insufficient funds"
                        else:
                            updated_order.status = OrderStatus.PENDING
                            order.status = OrderStatus.PENDING
                else:
                    updated_order.status = OrderStatus.PENDING
                    order.status = OrderStatus.PENDING
            elif not self._check_balance_for_order(updated_order):
                updated_order.status = OrderStatus.REJECTED
                updated_order.rejected_reason = "Insufficient balance"
                order.status = OrderStatus.REJECTED
                order.rejected_reason = "Insufficient balance"
            else:
                updated_order.status = OrderStatus.PENDING
                order.status = OrderStatus.PENDING

        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel mock order."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [
                OrderStatus.PENDING,
                OrderStatus.SUBMITTED,
                OrderStatus.REJECTED,
            ]:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.utcnow()

                # Update original order if it exists
                if order_id in self.original_orders:
                    original_order = self.original_orders[order_id]
                    original_order.status = OrderStatus.CANCELLED
                    original_order.cancelled_at = datetime.utcnow()

                return True

        return False

    async def get_ticker_price(self, symbol: str) -> Optional[Decimal]:
        """Get mock ticker price."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        market_data = self.market_data.get(symbol)
        if market_data:
            return market_data.close_price
        return None

    async def get_klines(
        self, symbol: str, interval: str = "1d", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get mock klines data."""
        if self.connection_status != MockConnectionStatus.CONNECTED:
            raise ConnectionError("Not connected to Binance")

        # Generate mock klines data
        base_price = self.config.default_btc_price
        klines = []

        for i in range(limit):
            price_change = Decimal(
                str(
                    self.config.klines_price_variation_percent
                    * (i % self.config.klines_variation_range - self.config.klines_variation_offset)
                )
            )
            price = base_price * (Decimal("1") + price_change)

            klines.append(
                {
                    "open_time": int(
                        (datetime.utcnow() - timedelta(days=limit - i)).timestamp()
                        * self.config.timestamp_ms_multiplier
                    ),
                    "open": str(price),
                    "high": str(price * self.config.high_price_multiplier),
                    "low": str(price * self.config.low_price_multiplier),
                    "close": str(price),
                    "volume": self.config.default_klines_volume,
                    "close_time": int(
                        (datetime.utcnow() - timedelta(days=limit - i - 1)).timestamp()
                        * self.config.timestamp_ms_multiplier
                    ),
                    "quote_asset_volume": self.config.default_quote_asset_volume,
                    "number_of_trades": self.config.default_number_of_trades,
                    "taker_buy_base_asset_volume": self.config.default_taker_buy_base_volume,
                    "taker_buy_quote_asset_volume": self.config.default_taker_buy_quote_volume,
                }
            )

        return klines

    def _should_execute_order(self, order: Order) -> bool:
        """Determine if order should be executed."""
        # Simple mock logic: execute if balance is sufficient
        if order.side == OrderSide.BUY:
            required_balance = order.quantity * order.price
            # For BUY orders, we need quote currency (USDT)
            quote_asset = "USDT" if "USDT" in order.symbol else "USD"
            available_balance = self.balances.get(quote_asset, Decimal("0"))
            return available_balance >= required_balance
        # For SELL orders, we need base currency (e.g., BTC from BTCUSDT)
        base_asset = (
            order.symbol.split("USDT")[0]
            if "USDT" in order.symbol
            else order.symbol.split("USD")[0]
        )
        available_balance = self.balances.get(base_asset, Decimal("0"))
        return available_balance >= order.quantity

    def _check_balance_for_order(self, order: Order) -> bool:
        """Check if there's sufficient balance for the order."""
        try:
            if order.side == OrderSide.BUY:
                required_balance = order.quantity * order.price
                # For BUY orders, we need quote currency (USDT)
                quote_asset = "USDT" if "USDT" in order.symbol else "USD"
                available_balance = self.balances.get(quote_asset, Decimal("0"))
                return available_balance >= required_balance
            # For SELL orders, we need base currency (e.g., BTC from BTCUSDT)
            base_asset = (
                order.symbol.split("USDT")[0]
                if "USDT" in order.symbol
                else order.symbol.split("USD")[0]
            )
            available_balance = self.balances.get(base_asset, Decimal("0"))
            return available_balance >= order.quantity
        except (ValueError, KeyError, AttributeError, IndexError, TypeError):
            return False

    async def _execute_order(self, order: Order):
        """Execute mock order."""
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.filled_price = (
            order.price
            if order.order_type == OrderType.LIMIT
            else self._get_market_price(order.symbol)
        )
        order.filled_quantity = order.quantity

        # Update balances
        base_asset = order.symbol.split("USDT")[0] if "USDT" in order.symbol else "USDT"
        quote_asset = "USDT" if "USDT" in order.symbol else order.symbol.split("USDT")[0]

        if order.side == OrderSide.BUY:
            # Buy: reduce quote asset, increase base asset
            self.balances[quote_asset] = self.balances.get(quote_asset, Decimal("0")) - (
                order.filled_quantity * order.filled_price
            )
            self.balances[base_asset] = (
                self.balances.get(base_asset, Decimal("0")) + order.filled_quantity
            )
        else:
            # Sell: reduce base asset, increase quote asset
            self.balances[base_asset] = (
                self.balances.get(base_asset, Decimal("0")) - order.filled_quantity
            )
            self.balances[quote_asset] = self.balances.get(quote_asset, Decimal("0")) + (
                order.filled_quantity * order.filled_price
            )

    def _get_market_price(self, symbol: str) -> Decimal:
        """Get mock market price."""
        market_data = self.market_data.get(symbol)
        if market_data:
            return market_data.close_price
        return self.config.default_btc_price


# Factory functions for easy instantiation
def create_mock_ibkr_client(account_id: str = "DU123456") -> MockIBKRClient:
    """Create a mock IBKR client."""
    return MockIBKRClient(account_id)


def create_mock_binance_client(
    api_key: str = "mock_api_key", api_secret: str = "mock_api_secret"
) -> MockBinanceClient:
    """Create a mock Binance client."""
    return MockBinanceClient(api_key, api_secret)
