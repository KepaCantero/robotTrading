"""
Alpaca API Client - Low-level Alpaca broker API wrapper.

Handles:
- Authentication with Alpaca API
- REST API calls (orders, positions, account)
- WebSocket streaming for real-time quotes
- Error handling and retry logic
- Rate limit compliance
- Configurable timeouts for all operations
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

import websockets
from requests.exceptions import HTTPError

from app.shared.config.timeout_config import get_timeouts

logger = logging.getLogger(__name__)


class AlpacaClientError(Exception):
    """Base exception for Alpaca client errors."""

    def __init__(self, message: str, timeout: bool = False):
        """
        Initialize Alpaca client error.

        Args:
            message: Error message
            timeout: Whether this error was caused by a timeout
        """
        super().__init__(message)
        self.timeout = timeout


class AlpacaClient:
    """
    Low-level Alpaca API wrapper with configurable timeouts.

    All API operations are wrapped with asyncio.wait_for() to prevent
    indefinite hangs. Timeout values are loaded from the centralized
    timeout configuration.

    Attributes:
        api: Alpaca REST API client instance
        stream: WebSocket stream connection
        base_url: API base URL
        is_authenticated: Authentication status
        timeouts: Timeout configuration instance
    """

    def __init__(self):
        """Initialize Alpaca client (not connected yet)."""
        self.api = None  # Will be alpaca_trade_api.REST instance
        self.stream = None  # Will be WebSocket stream
        self.base_url: Optional[str] = None
        self.is_authenticated = False
        self.last_request_time: Optional[datetime] = None
        self.rate_limit_reset: Optional[datetime] = None

        # Load timeout configuration
        self._timeouts = get_timeouts()

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
        """
        Authenticate with Alpaca API.

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            base_url: API base URL (paper or live)
            paper_trading: Whether to use paper trading (True) or live (False)

        Returns:
            bool: True if authentication successful

        Raises:
            AlpacaClientError: If authentication fails or times out
        """
        try:
            # Import here to avoid hard dependency
            from alpaca_trade_api import REST
        except ImportError:
            logger.error("alpaca-trade-api not installed. Run: pip install alpaca-trade-api")
            raise AlpacaClientError("alpaca-trade-api library not available")

        try:
            self.base_url = base_url

            # Create API client in thread pool with timeout
            def create_client():
                return REST(
                    api_key=api_key,
                    secret_key=api_secret,
                    base_url=base_url,
                    api_version="v2",
                )

            loop = asyncio.get_event_loop()
            self.api = await asyncio.wait_for(
                loop.run_in_executor(None, create_client), timeout=self._timeouts.alpaca_connect
            )

            # Test connectivity by getting account with timeout
            account = await asyncio.wait_for(
                loop.run_in_executor(None, self.api.get_account), timeout=self._timeouts.alpaca_read
            )

            if not account:
                raise AlpacaClientError("Failed to get account info")

            self.is_authenticated = True
            logger.info(f"Authenticated with Alpaca (Account: {account.account_number})")

            return True

        except asyncio.TimeoutError:
            logger.error("Alpaca authentication timed out")
            raise AlpacaClientError("Authentication timed out", timeout=True)
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Alpaca authentication failed: {str(e)}")
            raise AlpacaClientError(f"Authentication failed: {str(e)}")

    async def get_account(self) -> Dict[str, Any]:
        """
        Fetch account information from Alpaca with timeout.

        Returns:
            dict: Account data including:
                - account_number: Account ID
                - cash: Available cash
                - portfolio_value: Total portfolio value
                - buying_power: Available buying power
                - equity: Account equity
                - multiplier: Leverage multiplier

        Raises:
            AlpacaClientError: If request fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()
            account = await asyncio.wait_for(
                loop.run_in_executor(None, self.api.get_account), timeout=self._timeouts.alpaca_read
            )

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

        except asyncio.TimeoutError:
            logger.error("Get account request timed out")
            raise AlpacaClientError("get_account timed out", timeout=True)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get account: {str(e)}")
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
        client_order_id: Optional[str] = None,
    ) -> str:
        """
        Submit an order to Alpaca with timeout.

        SEC-005: Supports client_order_id for idempotency.

        Args:
            symbol: Stock symbol
            qty: Order quantity
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', 'stop', 'stop_limit')
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: Order time in force ('day', 'gtc', 'ioc')
            trail_percent: Trailing stop percentage
            client_order_id: Client order ID for idempotency

        Returns:
            str: Order ID from Alpaca

        Raises:
            AlpacaClientError: If order submission fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()

            def submit():
                kwargs = {
                    "symbol": symbol,
                    "qty": float(qty),
                    "side": side,
                    "type": order_type,
                    "time_in_force": time_in_force,
                }
                if limit_price is not None:
                    kwargs["limit_price"] = float(limit_price)
                if stop_price is not None:
                    kwargs["stop_price"] = float(stop_price)
                if trail_percent is not None:
                    kwargs["trail_percent"] = trail_percent
                if client_order_id is not None:
                    kwargs["client_order_id"] = client_order_id

                return self.api.submit_order(**kwargs)

            order = await asyncio.wait_for(
                loop.run_in_executor(None, submit), timeout=self._timeouts.alpaca_write
            )

            logger.info(f"Order submitted: {order.id} ({symbol} {side} {qty})")
            return order.id

        except asyncio.TimeoutError:
            logger.error(f"Order submission timed out: {symbol} {side} {qty}")
            raise AlpacaClientError("submit_order timed out", timeout=True)
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Order submission failed: {str(e)}")
            raise AlpacaClientError(f"submit_order failed: {str(e)}")

    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order with timeout.

        Args:
            order_id: Order ID to cancel

        Returns:
            bool: True if cancellation successful

        Raises:
            AlpacaClientError: If cancellation fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, self.api.cancel_order, order_id),
                timeout=self._timeouts.alpaca_write,
            )
            logger.info(f"Order cancelled: {order_id}")
            return True

        except asyncio.TimeoutError:
            logger.error(f"Order cancellation timed out: {order_id}")
            raise AlpacaClientError("cancel_order timed out", timeout=True)
        except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
            logger.error(f"Order cancellation failed: {str(e)}")
            raise AlpacaClientError(f"cancel_order failed: {str(e)}")

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details with timeout.

        Args:
            order_id: Order ID to query

        Returns:
            dict: Order details

        Raises:
            AlpacaClientError: If request fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()
            order = await asyncio.wait_for(
                loop.run_in_executor(None, self.api.get_order, order_id),
                timeout=self._timeouts.alpaca_read,
            )

            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price)
                if order.filled_avg_price
                else None,
                "type": order.order_type,
                "side": order.side,
                "status": order.status,
                "created_at": str(order.created_at),
                "updated_at": str(order.updated_at) if order.updated_at else None,
            }

        except asyncio.TimeoutError:
            logger.error(f"Get order timed out: {order_id}")
            raise AlpacaClientError("get_order timed out", timeout=True)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get order: {str(e)}")
            raise AlpacaClientError(f"get_order failed: {str(e)}")

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions with timeout.

        Returns:
            list: List of position dicts, each with:
                - symbol: Stock symbol
                - qty: Quantity held
                - avg_fill_price: Average purchase price
                - current_price: Current market price
                - market_value: Position market value
                - unrealized_pl: Unrealized profit/loss
                - unrealized_plpc: Unrealized P/L percentage
                - side: Position side ('long' or 'short')

        Raises:
            AlpacaClientError: If request fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()
            positions = await asyncio.wait_for(
                loop.run_in_executor(None, self.api.get_positions),
                timeout=self._timeouts.alpaca_read,
            )

            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "avg_fill_price": float(pos.avg_entry_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                    "side": pos.side,
                }
                for pos in positions
            ]

        except asyncio.TimeoutError:
            logger.error("Get positions timed out")
            raise AlpacaClientError("get_positions timed out", timeout=True)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get positions: {str(e)}")
            raise AlpacaClientError(f"get_positions failed: {str(e)}")

    async def get_orders(self, status: str = "open", limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get orders from Alpaca with timeout.

        Args:
            status: Order status ('open', 'closed', 'all')
            limit: Maximum number of orders to return

        Returns:
            list: List of order dicts

        Raises:
            AlpacaClientError: If request fails or times out
        """
        if not self.api:
            raise AlpacaClientError("Not authenticated")

        try:
            loop = asyncio.get_event_loop()
            orders = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self.api.get_orders(status=status, limit=limit)),
                timeout=self._timeouts.alpaca_read,
            )

            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "qty": float(order.qty),
                    "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                    "type": order.order_type,
                    "side": order.side,
                    "status": order.status,
                    "created_at": str(order.created_at),
                }
                for order in orders
            ]

        except asyncio.TimeoutError:
            logger.error("Get orders timed out")
            raise AlpacaClientError("get_orders timed out", timeout=True)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to get orders: {str(e)}")
            raise AlpacaClientError(f"get_orders failed: {str(e)}")

    # ==================== WebSocket Methods ====================

    async def start_stream(self, symbols: Optional[List[str]] = None) -> None:
        """
        Start WebSocket stream for real-time data.

        Args:
            symbols: List of symbols to subscribe to (None = all)

        Raises:
            AlpacaClientError: If stream fails to start
        """
        if self.is_streaming:
            logger.warning("Stream already running")
            return

        self.subscribed_symbols = symbols or ["*"]
        self.is_streaming = True

        # Start stream in background task
        self.stream_task = asyncio.create_task(self._run_stream())
        logger.info(f"Started stream for symbols: {self.subscribed_symbols}")

    async def _run_stream(self) -> None:
        """
        Internal method to run WebSocket stream with reconnection logic.

        Handles WebSocket connection lifecycle and message processing.
        """
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        base_reconnect_delay = 1.0

        while self.is_streaming:
            try:
                await self._connect_and_stream()
                reconnect_attempts = 0  # Reset on successful connection

            except asyncio.TimeoutError as e:
                if not self.is_streaming:
                    break
                logger.warning(f"Stream connection timed out: {e}")

            except OSError as e:
                if not self.is_streaming:
                    break

                reconnect_attempts += 1
                if reconnect_attempts > max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts ({max_reconnect_attempts}) reached")
                    self.is_streaming = False
                    if self.on_connection_error:
                        self.on_connection_error(e)
                    break

                delay = min(base_reconnect_delay * (2 ** (reconnect_attempts - 1)), 30)
                logger.warning(
                    f"Stream disconnected, reconnecting in {delay}s "
                    f"(attempt {reconnect_attempts}/{max_reconnect_attempts})"
                )
                await asyncio.sleep(delay)

    async def _connect_and_stream(self) -> None:
        """
        Connect to WebSocket and process messages.

        Raises:
            asyncio.TimeoutError: If connection times out
            ConnectionError: If connection fails
        """
        ws_url = self._get_stream_url()

        try:
            async with websockets.connect(
                ws_url,
                ping_interval=self._timeouts.websocket_ping_interval,
                ping_timeout=self._timeouts.websocket_ping_timeout,
                close_timeout=self._timeouts.websocket_close_timeout,
            ) as websocket:
                self.stream_socket = websocket
                logger.info(f"WebSocket connected to {ws_url}")

                # Authenticate
                auth_msg = {
                    "action": "auth",
                    "key": self.api._api_key if self.api else "",
                    "secret": self.api._secret_key if self.api else "",
                }
                await websocket.send(json.dumps(auth_msg))

                # Wait for auth response with timeout
                try:
                    auth_response = await asyncio.wait_for(
                        websocket.recv(), timeout=self._timeouts.alpaca_connect
                    )
                    auth_data = json.loads(auth_response)

                    if (
                        auth_data.get("status") != "auth_success"
                        and auth_data.get("T") != "success"
                    ):
                        raise ConnectionError(f"WebSocket auth failed: {auth_data}")

                    logger.info("WebSocket authenticated")
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError("WebSocket auth timed out")

                # Subscribe to symbols
                await self._subscribe_to_symbols(websocket)

                # Process messages
                while self.is_streaming:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(), timeout=self._timeouts.websocket_idle_timeout
                        )
                        await self._process_stream_message(message)
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.ping()
                        logger.debug("WebSocket ping sent")

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            raise ConnectionError(f"WebSocket closed: {e}")
        finally:
            self.stream_socket = None

    def _get_stream_url(self) -> str:
        """
        Get WebSocket URL based on authentication.

        Returns:
            str: WebSocket URL for Alpaca
        """
        if self.base_url == "https://paper-api.alpaca.markets":
            return "wss://data.sandbox.alpaca.markets/stream"
        else:
            return "wss://data.alpaca.markets/stream"

    async def _subscribe_to_symbols(self, websocket: websockets.WebSocketClientProtocol) -> None:
        """
        Subscribe to quote and trade updates for symbols.

        Args:
            websocket: WebSocket connection
        """
        if "*" in self.subscribed_symbols:
            subscribe_msg = {
                "action": "subscribe",
                "quotes": ["*"],
                "trades": ["*"],
            }
        else:
            subscribe_msg = {
                "action": "subscribe",
                "quotes": self.subscribed_symbols,
                "trades": self.subscribed_symbols,
            }

        await websocket.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to streams: {self.subscribed_symbols}")

    async def _process_stream_message(self, message: str) -> None:
        """
        Process incoming WebSocket message.

        Args:
            message: JSON message from WebSocket
        """
        try:
            data = json.loads(message)
            msg_type = data.get("T")

            if msg_type == "q":
                if self.on_quote:
                    self.on_quote(data)
            elif msg_type == "t":
                if self.on_trade:
                    self.on_trade(data)
            elif msg_type == "o":
                if self.on_order_update:
                    self.on_order_update(data)
            elif msg_type == "error":
                logger.error(f"Stream error: {data.get('msg')}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message: {message}")
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error processing stream message: {str(e)}")

    # ==================== Handler Registration ====================

    def register_quote_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for quote updates."""
        self.on_quote = callback
        logger.info("Quote handler registered")

    def register_trade_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for trade updates."""
        self.on_trade = callback
        logger.info("Trade handler registered")

    def register_order_handler(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register callback for order updates."""
        self.on_order_update = callback
        logger.info("Order handler registered")

    def register_error_handler(self, callback: Callable[[Exception], None]) -> None:
        """Register callback for connection errors."""
        self.on_connection_error = callback
        logger.info("Error handler registered")

    async def stop_stream(self) -> None:
        """Stop WebSocket stream gracefully."""
        if not self.is_streaming:
            return

        try:
            self.is_streaming = False

            if self.stream_socket:
                try:
                    await asyncio.wait_for(
                        self.stream_socket.close(), timeout=self._timeouts.websocket_close_timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning("Socket close timed out")
                except OSError as e:
                    logger.warning(f"Error closing socket: {e}")
                self.stream_socket = None

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
            logger.info("Stream stopped successfully")

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error stopping stream: {str(e)}")

    def __repr__(self) -> str:
        """String representation."""
        auth_status = "Authenticated" if self.is_authenticated else "Not authenticated"
        return f"AlpacaClient({auth_status}, url={self.base_url})"
