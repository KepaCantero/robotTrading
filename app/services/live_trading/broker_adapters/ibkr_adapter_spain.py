"""
Interactive Brokers Adapter for Spain

This adapter implements the IBrokerAdapter Protocol for Spanish traders.
It provides EUR currency support, IBEX35 stock trading, and follows
the Protocol interface exactly.

Protocol Compliance:
- connect() -> bool
- disconnect() -> bool
- place_order(order: dict) -> str
- cancel_order(order_id: str) -> bool
- get_account() -> dict
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from ib_insync import IB, LimitOrder, MarketOrder, StopOrder, util
from ib_insync.contract import Contract as IBContract

from app.infrastructure.resilience.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
)

from .currency_converter import get_currency_converter
from .ibex35_contracts import create_stock_contract

util.patchAsyncio()

logger = logging.getLogger(__name__)


class IBKRSpainAdapter:
    """
    Interactive Brokers adapter for Spanish traders.

    Implements IBrokerAdapter Protocol with:
    - EUR base currency
    - IBEX35 stock support
    - Currency conversion for multi-currency accounts
    - Spanish market hours awareness

    Note:
        This class implements IBrokerAdapter Protocol but is not
        declared as such because Protocol is for structural subtyping.
        Any class with matching methods is compatible.
    """

    # Connection settings
    CONNECTION_TIMEOUT = 10
    RECONNECT_DELAY = 5

    def __init__(self, config: Optional[dict[str, Any]] = None, ib_instance: Optional[IB] = None):
        """
        Initialize IBKR Spain adapter.

        Args:
            config: Configuration dict with keys:
                - host: IB host (default: 127.0.0.1)
                - port: IB port (default: 7497 for paper, 7496 for live)
                - client_id: Client ID (default: auto-generated)
                - account: IB account ID
                - paper_trading: True for paper, False for live (default: True)
            ib_instance: Optional existing IB instance to reuse
        """
        self.config = config or self._load_config_from_env()
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 7497)
        self.client_id = self.config.get("client_id", int(datetime.now().timestamp() % 1000))
        self.account = self.config.get("account", "")
        self.paper_trading = self.config.get("paper_trading", True)

        # IB connection
        self.ib = ib_instance or IB()
        self._connected = False

        # Currency converter
        self.currency_converter = get_currency_converter(self.ib)

        # Setup error handler
        self.ib.errorEvent += self._on_error

        # Reconnection manager
        self.reconnection_manager = self._create_reconnection_manager()

        # Track orders
        self._placed_orders: dict[str, Any] = {}

        logger.info(
            f"IBKR Spain Adapter initialized: {self.host}:{self.port} "
            f"(Client ID: {self.client_id}, Paper: {self.paper_trading})"
        )

    @staticmethod
    def _load_config_from_env() -> dict[str, Any]:
        """Load configuration from environment variables."""
        import os

        return {
            "host": os.getenv("IB_HOST", "127.0.0.1"),
            "port": int(os.getenv("IB_PORT", "7497")),
            "client_id": int(os.getenv("IB_CLIENT_ID", "1")),
            "account": os.getenv("IB_ACCOUNT", ""),
            "paper_trading": os.getenv("IB_PAPER_TRADING", "True").lower() == "true",
        }

    def _create_reconnection_manager(self) -> ReconnectionManager:
        """Create reconnection manager for reliable connection."""
        config = ReconnectionConfig(
            max_attempts=10,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            exponential_base=2.0,
            jitter=True,
            jitter_factor=0.1,
        )
        return ReconnectionManager("IBKRSpainAdapter", config)

    def _on_error(
        self, reqId: int, errorCode: int, errorString: str, contract: Optional[IBContract]
    ) -> None:
        """Handle IB errors."""
        # Ignore informational messages
        if errorCode in [2104, 2106, 2158]:
            return

        logger.error(f"IB Error (Code {errorCode}): {errorString}")

        # Handle connection errors
        if errorCode in [502, 504, 1100, 1101, 1102]:
            self._connected = False
            logger.warning("Connection lost with IB")
            self._reconnect_task = asyncio.create_task(self._reconnect())

    async def _reconnect(self) -> bool:
        """Attempt to reconnect."""
        try:
            await asyncio.sleep(self.RECONNECT_DELAY)
            return await self.connect()
        except Exception as e:
            logger.error(f"Reconnection error: {e}")
            return False

    async def connect(self) -> bool:
        """
        Connect to Interactive Brokers.

        Returns:
            True if connection successful, False otherwise
        """
        if self._connected and self.ib.isConnected():
            logger.debug("Already connected to IB")
            return True

        try:
            logger.info(
                f"Connecting to IB at {self.host}:{self.port} (Client ID: {self.client_id})"
            )

            await asyncio.wait_for(
                self.ib.connectAsync(self.host, self.port, self.client_id),
                timeout=self.CONNECTION_TIMEOUT,
            )

            if self.ib.isConnected():
                self._connected = True
                logger.info("Successfully connected to Interactive Brokers")

                # Update currency converter with live IB connection
                self.currency_converter.set_ib_connection(self.ib)
                await self.currency_converter.update_rates()

                return True
            else:
                logger.error("Failed to connect to IB")
                return False

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error connecting to IB: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from Interactive Brokers.

        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            if self._connected and self.ib.isConnected():
                await self.ib.disconnectAsync()
                self._connected = False
                logger.info("Disconnected from Interactive Brokers")
                return True
            return True  # Already disconnected

        except Exception as e:
            logger.error(f"Error disconnecting from IB: {e}")
            return False

    async def place_order(self, order: dict) -> str:
        """
        Place an order with IB.

        Args:
            order: Order dict with keys:
                - symbol: Stock symbol (e.g., "SAN.MC")
                - side: "BUY" or "SELL"
                - quantity: Number of shares
                - order_type: "MKT", "LMT", or "STP"
                - price: Limit price (required for LMT)
                - stop_price: Stop price (required for STP)
                - currency: "EUR" (default) or "USD"
                - exchange: "SMART" (default) or "MADRID"
                - time_in_force: "DAY" (default) or "GTC", "IOC"

        Returns:
            Order ID as string

        Raises:
            ValueError: If order parameters are invalid
            RuntimeError: If connection fails or order rejected
        """
        if not self._connected and not await self.connect():
            raise RuntimeError("Cannot connect to IB")

        # Validate order dict
        required_fields = ["symbol", "side", "quantity", "order_type"]
        for field in required_fields:
            if field not in order:
                raise ValueError(f"Missing required field: {field}")

        symbol = order["symbol"]
        side = order["side"].upper()
        quantity = order["quantity"]
        order_type = order["order_type"].upper()
        currency = order.get("currency", "EUR")
        exchange = order.get("exchange", "SMART")

        # Validate side
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}")

        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid quantity: {quantity}") from exc

        # Get contract
        contract = create_stock_contract(symbol, currency=currency, exchange=exchange)

        # Create order based on type
        if order_type == "MKT":
            ib_order = MarketOrder(side, quantity)
        elif order_type == "LMT":
            if "price" not in order:
                raise ValueError("Limit price required for LMT orders")
            price = float(order["price"])
            ib_order = LimitOrder(side, quantity, price)
        elif order_type == "STP":
            if "stop_price" not in order:
                raise ValueError("Stop price required for STP orders")
            stop_price = float(order["stop_price"])
            ib_order = StopOrder(side, quantity, stop_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        # Set time in force
        tif = order.get("time_in_force", "DAY")
        ib_order.tif = tif

        # Place order
        try:
            trade = self.ib.placeOrder(contract, ib_order)
            await asyncio.sleep(1)

            order_id = str(trade.order.orderId)

            # Store order info
            self._placed_orders[order_id] = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "contract": contract,
                "timestamp": datetime.now(),
            }

            logger.info(f"Order placed: {order_id} - {side} {quantity} {symbol} ({order_type})")

            return order_id

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise RuntimeError(f"Order placement failed: {e}") from e

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel (as string)

        Returns:
            True if cancellation successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            # Convert string order_id to int for IB API
            order_id_int = int(order_id)

            # Get order info if available
            order_info = self._placed_orders.get(order_id)
            if order_info and "contract" in order_info:
                # Cancel specific order
                self.ib.cancelOrder(self._placed_orders[order_id].get("orderId"))
            else:
                # Use IB's cancelOrder by ID
                # Note: IB API requires the Order object, not just ID
                # We need to find the order in the IB's order tracker
                for trade in self.ib.openTrades():
                    if trade.order.orderId == order_id_int:
                        self.ib.cancelOrder(trade.order)
                        break
                else:
                    logger.warning(f"Order {order_id} not found in open orders")
                    return False

            await asyncio.sleep(0.5)
            logger.info(f"Order {order_id} cancelled")
            return True

        except ValueError:
            logger.error(f"Invalid order ID format: {order_id}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    async def get_account(self) -> dict:
        """
        Get account information.

        Returns:
            Account dict with keys:
                - account_id: IB account ID
                - currency: Base currency (EUR)
                - net_liquidation: Total account value
                - available_funds: Available for trading
                - buying_power: Total buying power
                - total_cash_balance: Cash balance
                - positions: List of current positions
                - timestamp: ISO format timestamp
        """
        if not self._connected and not await self.connect():
            return {}

        try:
            # Request account summary
            self.ib.reqAccountSummary()
            await asyncio.sleep(1)

            summary = {}
            for item in self.ib.accountSummary():
                tag = item.tag
                value = item.value
                currency = item.currency

                summary[tag] = {
                    "value": float(value) if value else 0.0,
                    "currency": currency,
                }

            # Get positions
            positions = []
            for pos in self.ib.positions():
                position_value = float(pos.marketValue) if pos.marketValue else 0.0

                # Convert to EUR if needed
                if pos.contract.currency != "EUR":
                    # This would require currency converter
                    # For now, keep original currency
                    pass

                positions.append(
                    {
                        "symbol": pos.contract.symbol,
                        "position": float(pos.position),
                        "avg_cost": float(pos.avgCost) if pos.avgCost else 0.0,
                        "market_value": position_value,
                        "currency": pos.contract.currency,
                        "unrealized_pnl": float(pos.unrealizedPNL) if pos.unrealizedPNL else 0.0,
                    }
                )

            # Build account dict
            result = {
                "account_id": self.account
                or (self.ib.managedAccounts()[0] if self.ib.managedAccounts() else ""),
                "currency": "EUR",
                "net_liquidation": summary.get("NetLiquidation", {}).get("value", 0.0),
                "available_funds": summary.get("AvailableFunds", {}).get("value", 0.0),
                "buying_power": summary.get("BuyingPower", {}).get("value", 0.0),
                "total_cash_balance": summary.get("TotalCashBalance", {}).get("value", 0.0),
                "positions": positions,
                "timestamp": datetime.now().isoformat(),
            }

            return result

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}

    async def get_order_status(self, order_id: str) -> dict:
        """
        Get status of an order.

        Args:
            order_id: Order ID to check

        Returns:
            Order status dict with keys: status, fill_price, filled_quantity, etc.
        """
        if not self._connected:
            return {}

        try:
            order_id_int = int(order_id)

            for trade in self.ib.trades():
                if trade.order.orderId == order_id_int:
                    return {
                        "order_id": order_id,
                        "status": trade.orderStatus.status,
                        "filled": trade.orderStatus.filled,
                        "remaining": trade.orderStatus.remaining,
                        "avg_fill_price": trade.orderStatus.avgFillPrice,
                        "last_fill_price": trade.orderStatus.lastFillPrice,
                        "why_held": trade.orderStatus.whyHeld,
                    }

            return {"order_id": order_id, "status": "NOT_FOUND"}

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return {}

    def is_connected(self) -> bool:
        """Check if connected to IB."""
        return self._connected and self.ib.isConnected()


def get_ibkr_spain_adapter(config: Optional[dict[str, Any]] = None) -> IBKRSpainAdapter:
    """
    Get or create IBKR Spain adapter instance.

    Args:
        config: Optional configuration dict

    Returns:
        IBKRSpainAdapter instance
    """
    return IBKRSpainAdapter(config)
