from __future__ import annotations

"""
Interactive Brokers Adapter for AlgoTrading

This module provides a complete interface to Interactive Brokers TWS/IB Gateway
for live trading operations.

Features:
- Async connection management with auto-reconnect
- Real-time market data streaming
- Order placement (Market, Limit, Stop, Stop-Limit)
- Position tracking
- Account summary
- Error handling and recovery

Usage:
    from app.services.live_trading.broker_adapters.ib_adapter import IBAdapter, IBConnection

    # Create connection
    ib = IBConnection()
    await ib.connect()

    # Get market data
    data = await ib.get_market_data()

    # Place order
    result = await ib.place_order(
        side='BUY',
        quantity=1000,
        stop_loss=1.08,
        take_profit=1.12
    )
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from ib_insync import IB, LimitOrder, MarketOrder, StopOrder, util
from ib_insync.contract import Contract as IBContract
from ib_insync.ticker import Ticker

from app.domain.services.trading_validators import TradingValidator
from app.infrastructure.resilience.reconnection_manager import (
    ReconnectionConfig,
    ReconnectionManager,
)

# from app.models.position import Position  # NOTE: Position model not implemented yet
# from app.utils.exceptions import BrokerError, ConfigurationError  # NOTE: Not implemented


# Custom exceptions for IB adapter
class BrokerError(Exception):
    """Base exception for broker errors."""


class ConfigurationError(Exception):
    """Exception for configuration errors."""


logger = logging.getLogger(__name__)

# Patch asyncio for ib_insync compatibility
util.patchAsyncio()


class IBConnection:
    """
    Manages connection to Interactive Brokers TWS/IB Gateway.

    Handles:
    - Connection establishment with retry logic
    - Auto-reconnection on failures
    - Market data subscription and caching
    - Error handling
    """

    # Market data validity period (5 seconds)
    MARKET_DATA_VALIDITY = timedelta(seconds=5)

    # Connection settings
    MAX_CONNECTION_ATTEMPTS = 3
    RECONNECT_DELAY = 5
    CONNECTION_TIMEOUT = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize IB connection.

        Args:
            config: Optional configuration dict with keys:
                - host: IB host (default: 127.0.0.1)
                - port: IB port (default: 7497 for paper, 7496 for live)
                - client_id: Client ID (default: auto-generated)
                - account: IB account ID
                - paper_trading: True for paper, False for live (default: True)
        """
        # Load configuration
        self.config = config or self._load_config_from_env()

        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 7497)
        self.client_id = self.config.get('client_id', int(datetime.now().timestamp() % 1000))
        self.account = self.config.get('account', '')
        self.paper_trading = self.config.get('paper_trading', True)

        # Connection state
        self.connected: bool = False
        self.connection_attempts: int = 0
        self.ib: IB = IB()

        # Setup error handler
        self.ib.errorEvent += self._on_error

        # Market data cache
        self._market_data_cache: Dict[str, Dict[str, Any]] = {}
        self._market_data_time: Dict[str, datetime] = {}
        self._subscribed_contracts: Dict[str, IBContract] = {}

        # Default contracts for common symbols
        self._default_contracts: Dict[str, IBContract] = {}

        # Initialize reconnection manager for 24/7 operation
        self.reconnection_manager = self._create_reconnection_manager()

        # CRITICAL: Initialize trading validator for safety checks
        self.validator = TradingValidator()

        logger.info(
            f"IB Connection initialized: {self.host}:{self.port} (Client ID: {self.client_id})"
        )

    def _create_reconnection_manager(self) -> ReconnectionManager:
        """Create reconnection manager for IB connection."""

        def on_attempt(attempt: int) -> None:
            """Callback when connection attempt is made."""
            logger.info(f"IB connection attempt {attempt + 1}")

        def on_success(attempt: int) -> None:
            """Callback when connection succeeds."""
            logger.info(f"IB reconnected after {attempt + 1} attempts")

        def on_failure() -> None:
            """Callback when all connection attempts fail."""
            logger.error("All IB reconnection attempts failed")

        def alert_callback(attempts: int) -> None:
            """Callback when alert threshold is reached."""
            logger.warning(f"Alert: {attempts} failed IB connection attempts")

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
            service_name="IBAdapter",
            config=config,
        )

    @staticmethod
    def _load_config_from_env() -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            'host': os.getenv('IB_HOST', '127.0.0.1'),
            'port': int(os.getenv('IB_PORT', '7497')),
            'client_id': int(os.getenv('IB_CLIENT_ID', '1')),
            'account': os.getenv('IB_ACCOUNT', ''),
            'paper_trading': os.getenv('IB_PAPER_TRADING', 'True').lower() == 'true',
        }

    def _on_error(
        self, reqId: int, errorCode: int, errorString: str, contract: Optional[IBContract]
    ) -> None:
        """
        Handle errors from TWS/IB Gateway.

        Args:
            reqId: Request ID
            errorCode: Error code
            errorString: Error message
            contract: Related contract (if any)
        """
        # Ignore informational messages
        if errorCode in [2104, 2106, 2158]:
            return

        logger.error(f"IB Error (Code {errorCode}): {errorString}")

        # Handle connection errors
        if errorCode in [502, 504, 1100, 1101, 1102]:
            self.connected = False
            logger.warning("Connection lost with IB. Attempting to reconnect...")
            asyncio.create_task(self._reconnect_with_backoff())

    async def _reconnect_with_backoff(self) -> bool:
        """
        Attempt to reconnect to IB using exponential backoff.

        Returns:
            True if reconnection successful, False otherwise
        """

        async def _connect() -> bool:
            """Internal connection function."""
            return await self.connect()

        result = await self.reconnection_manager.connect_with_backoff(_connect)
        return result is not False

    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect to IB.

        Returns:
            True if reconnection successful, False otherwise
        """
        if self.connection_attempts >= self.MAX_CONNECTION_ATTEMPTS:
            logger.error(f"Max reconnection attempts ({self.MAX_CONNECTION_ATTEMPTS}) reached")
            return False

        self.connection_attempts += 1
        logger.info(
            f"Reconnection attempt {self.connection_attempts}/{self.MAX_CONNECTION_ATTEMPTS}"
        )

        try:
            await asyncio.sleep(self.RECONNECT_DELAY)
            return await self.connect()
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Reconnection error: {e}")
            return False

    async def connect(self) -> bool:
        """
        Establish connection to Interactive Brokers.

        Returns:
            True if connection successful, False otherwise
        """
        if self.connected and self.ib.isConnected():
            logger.debug("Already connected to IB")
            return True

        try:
            logger.info(
                f"Connecting to IB at {self.host}:{self.port} (Client ID: {self.client_id})"
            )

            # Connect with timeout
            await asyncio.wait_for(
                self.ib.connectAsync(self.host, self.port, self.client_id),
                timeout=self.CONNECTION_TIMEOUT,
            )

            if self.ib.isConnected():
                self.connected = True
                self.connection_attempts = 0
                logger.info("✅ Successfully connected to Interactive Brokers")

                # Verify account access
                if self.account:
                    await self._verify_account_access()

                return True
            else:
                logger.error("❌ Failed to connect to IB")
                return False

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"❌ Error connecting to IB: {e}")
            self.connected = False
            return False

    async def _verify_account_access(self) -> None:
        """Verify access to the specified account."""
        try:
            await asyncio.sleep(1)
            accounts = self.ib.managedAccounts()
            if self.account not in accounts:
                logger.warning(f"Account {self.account} not in accessible accounts: {accounts}")
            else:
                logger.info(f"✅ Account {self.account} accessible")
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error verifying account access: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Interactive Brokers gracefully."""
        try:
            if self.connected and self.ib.isConnected():
                # Cancel all market data subscriptions
                for _symbol, contract in self._subscribed_contracts.items():
                    self.ib.cancelMktData(contract)
                self._subscribed_contracts.clear()

                # Disconnect
                await self.ib.disconnectAsync()
                self.connected = False
                logger.info("Disconnected from Interactive Brokers")
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error disconnecting from IB: {e}")

    def _get_contract(self, symbol: str, **kwargs) -> IBContract:
        """
        Get or create IB contract for a symbol.

        Args:
            symbol: Trading symbol
            **kwargs: Additional contract parameters

        Returns:
            IB Contract object
        """
        if symbol in self._default_contracts:
            return self._default_contracts[symbol]

        # Default contract parameters
        contract_params = {
            'symbol': symbol,
            'secType': kwargs.get('secType', 'STK'),
            'exchange': kwargs.get('exchange', 'SMART'),
            'currency': kwargs.get('currency', 'USD'),
        }

        # Add special parameters for different asset classes
        if contract_params['secType'] == 'CASH':
            # Forex
            contract_params['symbol'] = kwargs.get('baseCurrency', symbol[:3])
            contract_params['currency'] = kwargs.get('quoteCurrency', symbol[3:])
            contract_params['exchange'] = 'IDEALPRO'

        contract = IBContract(**contract_params)
        self._default_contracts[symbol] = contract
        return contract

    async def get_market_data(self, symbol: str, **contract_kwargs) -> Dict[str, Any]:
        """
        Get market data for a symbol with caching.

        Args:
            symbol: Trading symbol
            **contract_kwargs: Additional contract parameters

        Returns:
            Market data dict with keys: bid, ask, last, volume, timestamp
        """
        if not self.connected and not await self.connect():
            logger.error("Cannot get market data - not connected to IB")
            return {}

        # Check cache validity
        if symbol in self._market_data_cache:
            cache_time = self._market_data_time.get(symbol, datetime.min)
            if datetime.now() - cache_time < self.MARKET_DATA_VALIDITY:
                return self._market_data_cache[symbol]

        try:
            # Get contract
            contract = self._get_contract(symbol, **contract_kwargs)

            # Request market data
            self.ib.reqMktData(contract, "", False, False)
            await asyncio.sleep(2)

            # Get ticker
            ticker = self.ib.ticker(contract)
            if not ticker or ticker.bid is None:
                logger.warning(f"No valid market data for {symbol}")
                return {}

            # Update cache
            market_data = {
                'symbol': symbol,
                'bid': float(ticker.bid) if ticker.bid else None,
                'ask': float(ticker.ask) if ticker.ask else None,
                'last': float(ticker.last) if ticker.last else None,
                'high': float(ticker.high) if ticker.high else None,
                'low': float(ticker.low) if ticker.low else None,
                'close': float(ticker.close) if ticker.close else None,
                'volume': int(ticker.volume) if ticker.volume else None,
                'timestamp': datetime.now(),
            }

            self._market_data_cache[symbol] = market_data
            self._market_data_time[symbol] = datetime.now()

            logger.debug(
                f"Market data updated for {symbol}: bid={market_data['bid']}, ask={market_data['ask']}"
            )
            return market_data

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'MKT',
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **contract_kwargs,
    ) -> Dict[str, Any]:
        """
        Place an order with IB.

        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            order_type: Order type ('MKT', 'LMT', 'STP', 'STP LMT')
            price: Limit price (for LMT orders)
            stop_price: Stop price (for STP orders)
            **contract_kwargs: Additional contract parameters

        Returns:
            Order result dict with keys: order_id, status, fill_price, etc.
        """
        if not self.connected and not await self.connect():
            return {'error': 'Cannot connect to IB'}

        try:
            # Validate parameters
            side = side.upper()
            if side not in ['BUY', 'SELL']:
                return {'error': f'Invalid side: {side}'}
            if quantity <= 0:
                return {'error': f'Invalid quantity: {quantity}'}

            # CRITICAL: Validate BEFORE executing
            # Get available capital (estimate from account if possible)
            try:
                account_summary = await self.get_account_summary()
                available_capital = Decimal(
                    str(account_summary.get('NetLiquidation', {}).get('value', 100000))
                )
            except (ValueError, TypeError, KeyError, AttributeError):
                # Fallback to default if account summary unavailable
                available_capital = Decimal("100000")
                logger.warning("Could not fetch account capital, using default for validation")

            # Calculate position value
            market_data_for_price = await self.get_market_data(symbol, **contract_kwargs)
            estimated_price = Decimal(
                str(market_data_for_price.get('last', market_data_for_price.get('bid', 100)))
            )
            position_value = Decimal(str(quantity)) * estimated_price

            # Validate position size
            try:
                self.validator.validate_position_size(
                    capital=available_capital,
                    position_size=position_value,
                    max_position_percent=Decimal("0.25"),
                )
            except ValueError as e:
                logger.error(f"Position size validation failed: {e}")
                return {'error': str(e)}

            # Validate stop-loss if provided
            if stop_price:
                try:
                    self.validator.validate_stop_loss(
                        entry_price=estimated_price,
                        stop_loss=Decimal(str(stop_price)),
                        side='long' if side == 'BUY' else 'short',
                    )
                except ValueError as e:
                    logger.error(f"Stop-loss validation failed: {e}")
                    return {'error': str(e)}
            else:
                # Log warning but don't fail (some strategies may not use SL)
                logger.warning(
                    f"Order for {symbol} placed without stop-loss - ensure risk is managed elsewhere"
                )

            # Get market data for validation
            market_data = await self.get_market_data(symbol, **contract_kwargs)
            if not market_data:
                return {'error': 'Cannot get market data for order validation'}

            # Validate stop/limit prices
            if stop_price and ((side == 'BUY' and stop_price >= market_data.get('bid', 0)) or (
                side == 'SELL' and stop_price <= market_data.get('ask', float('inf'))
            )):
                return {'error': 'Invalid stop price for current market'}
            if price and ((side == 'BUY' and price <= market_data.get('ask', float('inf'))) or (
                side == 'SELL' and price >= market_data.get('bid', 0)
            )):
                return {'error': 'Invalid limit price for current market'}

            # Get contract
            contract = self._get_contract(symbol, **contract_kwargs)

            # Create order
            if order_type == 'MKT':
                order = MarketOrder(side, quantity)
            elif order_type == 'LMT':
                if not price:
                    return {'error': 'Limit price required for LMT order'}
                order = LimitOrder(side, quantity, price)
            elif order_type == 'STP':
                if not stop_price:
                    return {'error': 'Stop price required for STP order'}
                order = StopOrder(side, quantity, stop_price)
            else:
                return {'error': f'Unsupported order type: {order_type}'}

            # Place order
            trade = self.ib.placeOrder(contract, order)
            await asyncio.sleep(1)

            if not trade.fills:
                return {
                    'order_id': trade.order.orderId,
                    'status': 'SUBMITTED',
                    'message': 'Order submitted, not yet filled',
                    'timestamp': datetime.now().isoformat(),
                }

            fill_price = trade.fills[0].execution.price

            return {
                'order_id': trade.order.orderId,
                'status': 'FILLED',
                'fill_price': float(fill_price),
                'filled_quantity': float(trade.fills[0].execution.shares),
                'side': side,
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error placing order: {e}")
            return {'error': str(e)}

    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.ib.cancelOrder(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions.

        Returns:
            List of position dicts
        """
        if not self.connected and not await self.connect():
            return []

        try:
            positions = self.ib.positions()
            result = []
            for pos in positions:
                result.append(
                    {
                        'symbol': pos.contract.symbol,
                        'position': float(pos.position),
                        'avg_cost': float(pos.avgCost) if pos.avgCost else 0.0,
                        'market_value': float(pos.marketValue) if pos.marketValue else 0.0,
                        'unrealized_pnl': float(pos.unrealizedPNL) if pos.unrealizedPNL else 0.0,
                        'realized_pnl': float(pos.realizedPNL) if pos.realizedPNL else 0.0,
                        'currency': pos.contract.currency,
                    }
                )
            return result
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary.

        Returns:
            Account summary dict
        """
        if not self.connected and not await self.connect():
            return {}

        try:
            # Request account summary
            self.ib.reqAccountSummary()

            # Wait for data
            await asyncio.sleep(1)

            summary = {}
            for item in self.ib.accountSummary():
                tag = item.tag
                value = item.value
                currency = item.currency

                summary[tag] = {
                    'value': float(value) if value else 0.0,
                    'currency': currency,
                }

            # Add calculated fields
            summary['timestamp'] = datetime.now().isoformat()
            summary['account_id'] = (
                self.account or self.ib.managedAccounts()[0] if self.ib.managedAccounts() else ''
            )

            return summary

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error getting account summary: {e}")
            return {}

    async def subscribe_market_data(
        self, symbol: str, callback: Callable[[Dict[str, Any]], None], **contract_kwargs
    ) -> None:
        """
        Subscribe to real-time market data updates.

        Args:
            symbol: Trading symbol
            callback: Function to call with updates
            **contract_kwargs: Additional contract parameters
        """
        if not self.connected:
            await self.connect()

        try:
            contract = self._get_contract(symbol, **contract_kwargs)
            self._subscribed_contracts[symbol] = contract

            def on_ticker_update(ticker: Ticker):
                if ticker.bid is None or ticker.ask is None:
                    return

                data = {
                    'symbol': symbol,
                    'bid': float(ticker.bid),
                    'ask': float(ticker.ask),
                    'last': float(ticker.last) if ticker.last else None,
                    'volume': int(ticker.volume) if ticker.volume else None,
                    'high': float(ticker.high) if ticker.high else None,
                    'low': float(ticker.low) if ticker.low else None,
                    'timestamp': datetime.now(),
                }
                callback(data)

            self.ib.reqMktData(contract, "", False, False)

            # Subscribe to ticker updates
            self.ib.pendingTickersEvent += on_ticker_update

            logger.info(f"Subscribed to market data for {symbol}")

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error subscribing to market data for {symbol}: {e}")

    async def unsubscribe_market_data(self, symbol: str) -> None:
        """
        Unsubscribe from market data updates.

        Args:
            symbol: Trading symbol
        """
        if symbol in self._subscribed_contracts:
            try:
                self.ib.cancelMktData(self._subscribed_contracts[symbol])
                del self._subscribed_contracts[symbol]
                logger.info(f"Unsubscribed from market data for {symbol}")
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.error(f"Error unsubscribing from market data for {symbol}: {e}")

    def __del__(self):
        """
        Clean up IB connection on deletion.

        This method is called when the object is garbage collected.
        It attempts to disconnect from IB if still connected.
        """
        try:
            if hasattr(self, 'ib') and self.ib.isConnected():
                self.ib.disconnect()
        except OSError as e:
            # Connection errors during cleanup are expected in some cases
            logger.warning(f"Connection error during IB adapter cleanup: {e}")
        except Exception as e:
            # Log any other unexpected errors during cleanup
            logger.error(f"Unexpected error during IB adapter cleanup: {e}", exc_info=True)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get reconnection statistics."""
        return self.reconnection_manager.get_stats()


class IBAdapter:
    """
    High-level adapter for Interactive Brokers trading operations.

    This class provides a simplified interface for common trading operations,
    abstracting away the complexity of the IB API.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize IB adapter.

        Args:
            config: Configuration dict (uses env vars if not provided)
        """
        self.connection = IBConnection(config)
        self._subscribed_callbacks: Dict[str, List[Callable]] = {}

    async def connect(self) -> bool:
        """Connect to IB."""
        return await self.connection.connect()

    async def disconnect(self) -> None:
        """Disconnect from IB."""
        await self.connection.disconnect()

    async def is_connected(self) -> bool:
        """Check if connected to IB."""
        return self.connection.connected and self.connection.ib.isConnected()

    async def get_market_data(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Get market data for a symbol."""
        return await self.connection.get_market_data(symbol, **kwargs)

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'MKT',
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Place an order."""
        return await self.connection.place_order(
            symbol, side, quantity, order_type, price, stop_price, **kwargs
        )

    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an order."""
        return await self.connection.cancel_order(order_id)

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        return await self.connection.get_positions()

    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        return await self.connection.get_account_summary()

    async def subscribe_market_data(
        self, symbol: str, callback: Callable[[Dict[str, Any]], None], **kwargs
    ) -> None:
        """Subscribe to market data updates."""
        if symbol not in self._subscribed_callbacks:
            self._subscribed_callbacks[symbol] = []
        self._subscribed_callbacks[symbol].append(callback)
        await self.connection.subscribe_market_data(symbol, callback, **kwargs)

    async def unsubscribe_market_data(self, symbol: str) -> None:
        """Unsubscribe from market data updates."""
        self._subscribed_callbacks.pop(symbol, None)
        await self.connection.unsubscribe_market_data(symbol)

    @property
    def is_connected_property(self) -> bool:
        """Connection status property."""
        return self.connection.connected


# Singleton instance for easy access
_ib_adapter_instance: Optional[IBAdapter] = None


def get_ib_adapter() -> IBAdapter:
    """
    Get the singleton IB adapter instance.

    Returns:
        IBAdapter instance
    """
    global _ib_adapter_instance
    if _ib_adapter_instance is None:
        _ib_adapter_instance = IBAdapter()
    return _ib_adapter_instance
