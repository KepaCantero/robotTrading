"""
Alpaca API Client - Low-level Alpaca broker API wrapper.

Handles:
- Authentication with Alpaca API
- REST API calls (orders, positions, account)
- WebSocket streaming for real-time quotes
- Error handling and retry logic
- Rate limit compliance
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)


class AlpacaClientError(Exception):
    """Base exception for Alpaca client errors."""


class AlpacaClient:
    """Low-level Alpaca API wrapper."""

    def __init__(self):
        """Initialize Alpaca client (not connected yet)."""
        self.api = None  # Will be alpaca_trade_api.REST instance
        self.stream = None  # Will be WebSocket stream
        self.base_url: Optional[str] = None
        self.is_authenticated = False
        self.last_request_time: Optional[datetime] = None
        self.rate_limit_reset: Optional[datetime] = None

        # WebSocket streaming
        self.stream_socket: Optional[websockets.WebSocketClientProtocol] = None
        self.stream_task: Optional[asyncio.Task] = None
        self.is_streaming = False
        self.subscribed_symbols: List[str] = []

        # Event callbacks
        self.on_quote: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_trade: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_order_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_connection_error: Optional[Callable[[Exception], None]] = None

    async def authenticate(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://paper-api.alpaca.markets",
        paper_trading: bool = True,
    ) -> bool:
        """Authenticate with Alpaca API.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL (paper or live)
            paper_trading: Whether to use paper trading (True) or live (False)

        Returns:
            bool: True if authentication successful

        Raises:
            AlpacaClientError: If authentication fails
        """
        try:
            # Import here to avoid hard dependency
            from alpaca_trade_api import REST

            self.base_url = base_url
            self.api = REST(
                api_key=api_key,
                secret_key=api_secret,
                base_url=base_url,
                api_version="v2",
            )

            # Test connectivity by getting account
            account = self.api.get_account()
            if not account:
                raise AlpacaClientError("Failed to get account info")

            self.is_authenticated = True
            logger.info(f"✅ Authenticated with Alpaca (Account: {account.account_number})")

            return True

        except ImportError:
            logger.error("alpaca-trade-api not installed. Run: pip install alpaca-trade-api")
            raise AlpacaClientError("alpaca-trade-api library not available")
        except Exception as e:
            logger.error(f"❌ Alpaca authentication failed: {str(e)}")
            raise AlpacaClientError(f"Authentication failed: {str(e)}")

    async def get_account(self) -> Dict[str, Any]:
        """Fetch account information from Alpaca.

        Returns:
            dict: Account data including:
                - account_number: Account ID
                - cash: Available cash
                - portfolio_value: Total portfolio value
                - buying_power: Available buying power
                - equity: Account equity
                - multiplier: Leverage multiplier

        Raises:
            AlpacaClientError: If request fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            account = self.api.get_account()

            return {
                "account_number": account.account_number,
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity),
                "multiplier": float(account.multiplier),
                "status": account.status,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get account: {str(e)}")
            raise AlpacaClientError(f"get_account failed: {str(e)}")

    async def submit_order(
        self,
        symbol: str,
        qty: Decimal,
        side: str,
        order_type: str = "market",
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "day",
        trail_percent: Optional[float] = None,
    ) -> str:
        """Submit an order to Alpaca.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Order quantity
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', 'stop', 'stop_limit', 'trailing_stop')
            limit_price: Price for limit orders
            stop_price: Price for stop orders
            time_in_force: Order duration ('day', 'gtc', 'opg', 'cls')
            trail_percent: Trail percent for trailing stop orders

        Returns:
            str: Order ID

        Raises:
            AlpacaClientError: If order submission fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            # Build order parameters
            order_params = {
                "symbol": symbol,
                "qty": float(qty),
                "side": side.lower(),
                "type": order_type.lower(),
                "time_in_force": time_in_force,
            }

            # Add limit price if applicable
            if limit_price is not None and order_type.lower() in ("limit", "stop_limit"):
                order_params["limit_price"] = float(limit_price)

            # Add stop price if applicable
            if stop_price is not None and order_type.lower() in ("stop", "stop_limit"):
                order_params["stop_price"] = float(stop_price)

            # Add trail_percent for trailing stop orders
            if trail_percent is not None and order_type.lower() == "trailing_stop":
                order_params["trail_percent"] = trail_percent

            # Submit order
            order = self.api.submit_order(**order_params)

            return order.id

        except Exception as e:
            logger.error(f"❌ Order submission failed: {str(e)}")
            raise AlpacaClientError(f"submit_order failed: {str(e)}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation was successful

        Raises:
            AlpacaClientError: If cancellation fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            self.api.cancel_order(order_id)
            logger.info(f"✅ Order {order_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"❌ Order cancellation failed: {str(e)}")
            raise AlpacaClientError(f"cancel_order failed: {str(e)}")

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Alpaca.

        Args:
            order_id: Order ID to query

        Returns:
            dict: Order data

        Raises:
            AlpacaClientError: If request fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            order = self.api.get_order(order_id)

            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "type": order.order_type,
                "status": order.status,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": (
                    float(order.filled_avg_price) if order.filled_avg_price else None
                ),
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            }

        except Exception as e:
            logger.error(f"❌ Failed to get order: {str(e)}")
            raise AlpacaClientError(f"get_order failed: {str(e)}")

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions from Alpaca.

        Returns:
            list: List of position dicts, each with:
                - symbol: Stock symbol
                - qty: Quantity held
                - avg_fill_price: Average purchase price
                - current_price: Current market price
                - market_value: Position market value

        Raises:
            AlpacaClientError: If request fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            positions = self.api.get_positions()

            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_fill_price": float(pos.avg_fill_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "side": pos.side,
                }
                for pos in positions
            ]

        except Exception as e:
            logger.error(f"❌ Failed to get positions: {str(e)}")
            raise AlpacaClientError(f"get_positions failed: {str(e)}")

    async def get_orders(self, status: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """Get orders from Alpaca.

        Args:
            status: Order status ('open', 'closed', 'all')
            limit: Maximum number of orders to return

        Returns:
            list: List of order dicts

        Raises:
            AlpacaClientError: If request fails
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            orders = self.api.get_orders(status=status, limit=limit)

            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "side": order.side,
                    "type": order.order_type,
                    "status": order.status,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                    "filled_avg_price": (
                        float(order.filled_avg_price) if order.filled_avg_price else None
                    ),
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"❌ Failed to get orders: {str(e)}")
            raise AlpacaClientError(f"get_orders failed: {str(e)}")

    async def start_stream(self, symbols: Optional[List[str]] = None) -> None:
        """Start WebSocket stream for real-time quotes and trades.

        Args:
            symbols: List of symbols to stream (e.g., ['AAPL', 'TSLA'])
                    If None, subscribes to all symbols

        Raises:
            AlpacaClientError: If streaming fails
        """
        if not self.is_authenticated:
            raise AlpacaClientError("Must authenticate before starting stream")

        if self.is_streaming:
            logger.warning("Stream already running")
            return

        try:
            self.subscribed_symbols = symbols or ["*"]
            self.is_streaming = True

            # Start WebSocket connection in background task
            self.stream_task = asyncio.create_task(self._run_stream())
            logger.info(f"✅ WebSocket stream started for symbols: {self.subscribed_symbols}")

        except Exception as e:
            logger.error(f"❌ Failed to start stream: {str(e)}")
            self.is_streaming = False
            raise AlpacaClientError(f"Stream startup failed: {str(e)}")

    async def _run_stream(self) -> None:
        """Internal method to run WebSocket stream with reconnection logic.

        Handles WebSocket connection lifecycle and message processing.
        """
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        base_reconnect_delay = 1.0

        while self.is_streaming:
            try:
                await self._connect_and_stream()
                reconnect_attempts = 0  # Reset on successful connection

            except Exception as e:
                if not self.is_streaming:
                    # Stream was intentionally stopped
                    break

                reconnect_attempts += 1
                if reconnect_attempts > max_reconnect_attempts:
                    logger.error(f"❌ Max reconnection attempts ({max_reconnect_attempts}) reached")
                    self.is_streaming = False
                    if self.on_connection_error:
                        self.on_connection_error(e)
                    break

                # Exponential backoff
                delay = min(base_reconnect_delay * (2 ** (reconnect_attempts - 1)), 30)
                logger.warning(
                    f"⚠️  Stream disconnected, reconnecting in {delay}s "
                    f"(attempt {reconnect_attempts}/{max_reconnect_attempts})"
                )
                await asyncio.sleep(delay)

    async def _connect_and_stream(self) -> None:
        """Connect to Alpaca WebSocket and process messages.

        Raises:
            Exception: Connection or processing errors
        """
        ws_url = self._get_stream_url()

        try:
            async with websockets.connect(ws_url) as websocket:
                self.stream_socket = websocket
                logger.info("✅ WebSocket connected to Alpaca")

                # Authenticate
                auth_msg = {
                    "action": "auth",
                    "key": self.api.api_key if self.api else None,
                    "secret": self.api.secret_key if self.api else None,
                }
                await websocket.send(json.dumps(auth_msg))

                # Wait for auth response
                auth_response = await websocket.recv()
                auth_data = json.loads(auth_response)
                if not auth_data.get("data", {}).get("status") == "authorized":
                    raise AlpacaClientError(f"WebSocket auth failed: {auth_data}")

                logger.info("✅ WebSocket authenticated")

                # Subscribe to symbols
                await self._subscribe_to_symbols(websocket)

                # Process incoming messages
                async for message in websocket:
                    if not self.is_streaming:
                        break

                    await self._process_stream_message(message)

        except asyncio.CancelledError:
            logger.info("Stream task cancelled")
        except Exception as e:
            logger.error(f"❌ Stream error: {str(e)}")
            raise
        finally:
            self.stream_socket = None

    def _get_stream_url(self) -> str:
        """Get WebSocket URL based on authentication.

        Returns:
            str: WebSocket URL for Alpaca
        """
        if self.base_url == "https://paper-api.alpaca.markets":
            return "wss://data.sandbox.alpaca.markets/stream"
        else:
            return "wss://data.alpaca.markets/stream"

    async def _subscribe_to_symbols(self, websocket: websockets.WebSocketClientProtocol) -> None:
        """Subscribe to quote and trade updates for symbols.

        Args:
            websocket: WebSocket connection
        """
        if "*" in self.subscribed_symbols:
            # Subscribe to all quotes and trades
            subscribe_msg = {
                "action": "subscribe",
                "quotes": ["*"],
                "trades": ["*"],
            }
        else:
            # Subscribe to specific symbols
            subscribe_msg = {
                "action": "subscribe",
                "quotes": self.subscribed_symbols,
                "trades": self.subscribed_symbols,
            }

        await websocket.send(json.dumps(subscribe_msg))
        logger.info(f"✅ Subscribed to streams: {self.subscribed_symbols}")

    async def _process_stream_message(self, message: str) -> None:
        """Process incoming WebSocket message.

        Args:
            message: JSON message from WebSocket
        """
        try:
            data = json.loads(message)
            msg_type = data.get("T")

            if msg_type == "q":
                # Quote update
                if self.on_quote:
                    self.on_quote(data)

            elif msg_type == "t":
                # Trade update
                if self.on_trade:
                    self.on_trade(data)

            elif msg_type == "o":
                # Order update
                if self.on_order_update:
                    self.on_order_update(data)

            elif msg_type == "error":
                logger.error(f"❌ Stream error: {data.get('msg')}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing stream message: {str(e)}")

    def register_quote_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for quote updates.

        Args:
            callback: Function to call with quote data
        """
        self.on_quote = callback
        logger.info("Quote handler registered")

    def register_trade_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for trade updates.

        Args:
            callback: Function to call with trade data
        """
        self.on_trade = callback
        logger.info("Trade handler registered")

    def register_order_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for order updates.

        Args:
            callback: Function to call with order data
        """
        self.on_order_update = callback
        logger.info("Order handler registered")

    def register_error_handler(self, callback: Callable[[Exception], None]) -> None:
        """Register callback for connection errors.

        Args:
            callback: Function to call with exception
        """
        self.on_connection_error = callback
        logger.info("Error handler registered")

    async def stop_stream(self) -> None:
        """Stop WebSocket stream gracefully."""
        if not self.is_streaming:
            return

        try:
            self.is_streaming = False

            # Close socket
            if self.stream_socket:
                try:
                    await self.stream_socket.close()
                except Exception as e:
                    logger.warning(f"Error closing socket: {e}")
                self.stream_socket = None

            # Cancel stream task
            if self.stream_task:
                try:
                    self.stream_task.cancel()
                    await asyncio.wait_for(self.stream_task, timeout=5.0)
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("Stream task cancellation timed out")
                finally:
                    self.stream_task = None

            self.subscribed_symbols = []
            logger.info("✅ Stream stopped successfully")

        except Exception as e:
            logger.error(f"❌ Error stopping stream: {str(e)}")

    def __repr__(self) -> str:
        """String representation."""
        auth_status = "✅ Authenticated" if self.is_authenticated else "❌ Not authenticated"
        return f"AlpacaClient({auth_status}, url={self.base_url})"
