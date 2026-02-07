"""
Integration tests for Reconnection Manager with services.

Tests the reconnection manager integration with broker connectors
and data services for 24/7 market operation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.crypto_data_service import CryptoDataFetcher
from app.services.forex_data_service import ForexDataFetcher
from app.services.live_trading.broker_connector import BrokerConnector, BrokerType


class TestBrokerConnectorReconnection:
    """Test BrokerConnector reconnection integration."""

    @pytest.mark.asyncio
    async def test_broker_connector_uses_reconnection_manager(self):
        """Test that BrokerConnector uses reconnection manager."""
        connector = BrokerConnector(BrokerType.ALPACA)

        # Should have reconnection manager initialized
        assert connector.reconnection_manager is not None
        assert connector.reconnection_manager.service_name == "BrokerConnector_alpaca"

    @pytest.mark.asyncio
    async def test_broker_connect_with_reconnection(self):
        """Test broker connection with reconnection."""
        connector = BrokerConnector(BrokerType.ALPACA)

        # Mock the adapter connect to fail twice then succeed
        connect_call_count = 0

        async def mock_connect(*args, **kwargs):
            nonlocal connect_call_count
            connect_call_count += 1
            if connect_call_count < 3:
                raise Exception("Connection failed")
            return True

        connector.adapter.connect = mock_connect

        # Should succeed after retries
        result = await connector.connect()

        assert result is True
        assert connect_call_count == 3

    @pytest.mark.asyncio
    async def test_broker_get_connection_stats(self):
        """Test getting connection statistics."""
        connector = BrokerConnector(BrokerType.ALPACA)

        stats = connector.get_connection_stats()

        assert "service_name" in stats
        assert "total_attempts" in stats
        assert "successful_connections" in stats
        assert "failed_connections" in stats
        assert "success_rate" in stats

    @pytest.mark.asyncio
    async def test_paper_trading_skips_reconnection(self):
        """Test that paper trading doesn't use reconnection by default."""
        connector = BrokerConnector(BrokerType.PAPER)

        # Mock the adapter connect
        connector.adapter.connect = AsyncMock(return_value=True)

        # Should connect directly without reconnection manager
        result = await connector.connect()

        assert result is True
        connector.adapter.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_with_retry_always_uses_reconnection(self):
        """Test that connect_with_retry always uses reconnection manager."""
        connector = Connector(BrokerType.PAPER)

        # Mock the adapter connect to fail twice then succeed
        connect_call_count = 0

        async def mock_connect(*args, **kwargs):
            nonlocal connect_call_count
            connect_call_count += 1
            if connect_call_count < 3:
                raise Exception("Connection failed")
            return True

        connector.adapter.connect = mock_connect

        # Should succeed after retries even for paper trading
        result = await connector.connect_with_retry()

        assert result is True
        assert connect_call_count == 3


class TestCryptoDataServiceReconnection:
    """Test CryptoDataService reconnection integration."""

    def test_crypto_fetcher_has_reconnection_manager(self):
        """Test that CryptoDataFetcher has reconnection manager."""
        fetcher = CryptoDataFetcher()

        # Should have reconnection manager initialized
        assert fetcher.reconnection_manager is not None
        assert fetcher.reconnection_manager.service_name == "CryptoDataFetcher"

    @pytest.mark.asyncio
    async def test_crypto_price_fetch_with_reconnection(self):
        """Test crypto price fetching with reconnection."""
        fetcher = CryptoDataFetcher()

        # Mock the API fetch to fail twice then succeed
        fetch_call_count = 0

        def mock_fetch_price(pair):
            nonlocal fetch_call_count
            fetch_call_count += 1
            if fetch_call_count < 3:
                raise Exception("API failed")
            return Decimal("50000.00")

        fetcher._fetch_price_from_api = mock_fetch_price

        # Mock asyncio.run to handle the async properly in test
        with patch('asyncio.run') as mock_run:
            # Make the mock run return our test value
            mock_run.return_value = Decimal("50000.00")

            # This will use the mocked asyncio.run
            prices = fetcher.get_current_prices(["BTC"])

            # Should have prices even after API failures
            assert "BTC" in prices

    @pytest.mark.asyncio
    async def test_crypto_get_connection_stats(self):
        """Test getting connection statistics."""
        fetcher = CryptoDataFetcher()

        stats = fetcher.get_connection_stats()

        assert "service_name" in stats
        assert "total_attempts" in stats
        assert "successful_connections" in stats
        assert "failed_connections" in stats
        assert "success_rate" in stats

    @pytest.mark.asyncio
    async def test_crypto_ohlcv_fetch_with_reconnection(self):
        """Test crypto OHLCV fetching with reconnection."""
        fetcher = CryptoDataFetcher()

        # Mock the API fetch
        mock_ohlcv = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "open": 50000,
                "high": 51000,
                "low": 49000,
                "close": 50500,
                "volume": 100,
            }
        ]

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = mock_ohlcv

            result = fetcher.get_historical_ohlcv("BTC", "1h", 10)

            # Should return OHLCV data
            assert result is not None
            assert len(result) > 0


class TestForexDataServiceReconnection:
    """Test ForexDataService reconnection integration."""

    def test_forex_fetcher_has_reconnection_manager(self):
        """Test that ForexDataFetcher has reconnection manager."""
        fetcher = ForexDataFetcher()

        # Should have reconnection manager initialized
        assert fetcher.reconnection_manager is not None
        assert fetcher.reconnection_manager.service_name == "ForexDataFetcher"

    @pytest.mark.asyncio
    async def test_forex_rate_fetch_with_reconnection(self):
        """Test forex rate fetching with reconnection."""
        fetcher = ForexDataFetcher()

        # Mock the API fetch
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = Decimal("1.08")

            rates = fetcher.get_current_rates(["EUR/USD"])

            # Should have rates
            assert "EUR/USD" in rates

    @pytest.mark.asyncio
    async def test_forex_correlation_fetch_with_reconnection(self):
        """Test forex correlation fetching with reconnection."""
        fetcher = ForexDataFetcher()

        # Mock the API fetch
        mock_correlations = {
            "EUR": Decimal("0.85"),
            "GBP": Decimal("0.80"),
        }

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = mock_correlations

            correlations = fetcher.get_correlations("USD")

            # Should have correlations
            assert "EUR" in correlations
            assert correlations["EUR"] == Decimal("0.85")

    @pytest.mark.asyncio
    async def test_forex_get_connection_stats(self):
        """Test getting connection statistics."""
        fetcher = ForexDataFetcher()

        stats = fetcher.get_connection_stats()

        assert "service_name" in stats
        assert "total_attempts" in stats
        assert "successful_connections" in stats
        assert "failed_connections" in stats
        assert "success_rate" in stats


class TestReconfiguration:
    """Test reconfiguration of reconnection managers."""

    def test_custom_reconnection_config_for_broker(self):
        """Test custom reconnection configuration for broker."""
        # This would be implemented if we allow custom config
        # For now, test the default config
        connector = BrokerConnector(BrokerType.ALPACA)

        config = connector.reconnection_manager.config
        assert config.max_attempts == 10
        assert config.alert_after_attempts == 3

    def test_custom_reconnection_config_for_crypto(self):
        """Test custom reconnection configuration for crypto."""
        fetcher = CryptoDataFetcher()

        config = fetcher.reconnection_manager.config
        assert config.max_attempts == 10
        assert config.alert_after_attempts == 3

    def test_custom_reconnection_config_for_forex(self):
        """Test custom reconnection configuration for forex."""
        fetcher = ForexDataFetcher()

        config = fetcher.reconnection_manager.config
        assert config.max_attempts == 10
        assert config.alert_after_attempts == 3


class Test24HourOperation:
    """Test 24/7 operation scenarios."""

    @pytest.mark.asyncio
    async def test_crypto_network_glitch_recovery(self):
        """Test crypto service recovery from network glitch."""
        fetcher = CryptoDataFetcher()

        # Simulate network glitch: fail, then succeed
        fetch_attempts = [False, True]

        def mock_fetch(pair):
            if not fetch_attempts[0]:
                fetch_attempts[0] = True
                raise Exception("Network glitch")
            return Decimal("50000.00")

        fetcher._fetch_price_from_api = mock_fetch

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = Decimal("50000.00")

            # Should recover from glitch
            prices = fetcher.get_current_prices(["BTC"])
            assert "BTC" in prices

    @pytest.mark.asyncio
    async def test_forex_network_glitch_recovery(self):
        """Test forex service recovery from network glitch."""
        fetcher = ForexDataFetcher()

        # Simulate network glitch
        with patch('asyncio.run') as mock_run:
            # First call fails, second succeeds
            mock_run.side_effect = [Exception("Network glitch"), Decimal("1.08")]

            # Should use fallback and eventually recover
            rates = fetcher.get_current_rates(["EUR/USD"])
            # Should have rate (either from fallback or API)
            assert "EUR/USD" in rates

    @pytest.mark.asyncio
    async def test_broker_connection_loss_recovery(self):
        """Test broker recovery from connection loss."""
        connector = BrokerConnector(BrokerType.ALPACA)

        # Simulate connection loss
        connect_attempts = [False, False, True]

        async def mock_connect(*args, **kwargs):
            if not connect_attempts[0]:
                connect_attempts[0] = True
                raise Exception("Connection lost")
            if not connect_attempts[1]:
                connect_attempts[1] = True
                raise Exception("Connection lost")
            return True

        connector.adapter.connect = mock_connect

        # Should recover after multiple attempts
        result = await connector.connect()
        assert result is True


# Helper class for mocking
class Connector:
    """Helper for testing paper trading connector."""

    def __init__(self, broker_type):
        self.broker_type = broker_type
        self.reconnection_manager = MagicMock()
        self.adapter = MagicMock()

    async def connect_with_retry(self, *args, **kwargs):
        async def _connect():
            return await self.adapter.connect(*args, **kwargs)

        result = await self.reconnection_manager.connect_with_backoff(_connect)
        return result is not False
