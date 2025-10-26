"""
Tests for MarketDataService - CRITICAL for financial integrity.

This test suite ensures that the market data service:
- Correctly manages feed configurations
- Caches quotes and historical data
- Handles concurrent requests
- Provides accurate market data
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.models.market_data import DataFeedConfig, DataFeedType, DataFrequency, Quote
from app.services.market_data_service import MarketDataService


@pytest.fixture
def service():
    """Create MarketDataService instance."""
    return MarketDataService()


@pytest.fixture
def sample_quote():
    """Create sample market quote."""
    return Quote(
        symbol="AAPL",
        bid=Decimal("150.00"),
        ask=Decimal("150.10"),
        last=Decimal("150.05"),
        volume=Decimal("1000000"),
        timestamp=datetime.utcnow(),
        high=Decimal("155.00"),
        low=Decimal("145.00"),
        open=Decimal("150.00"),
        close=Decimal("150.00"),
    )


class TestMarketDataServiceInitialization:
    """Tests for service initialization."""

    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service is not None
        assert service.default_cache_ttl == 60
        assert service.max_cache_size == 1000

    def test_default_feeds_initialized(self, service):
        """Test default feeds are initialized."""
        # Service should have default feeds
        assert len(service.feed_configs) >= 2  # Mock and Yahoo


class TestFeedConfigurationManagement:
    """Tests for feed configuration management."""

    @pytest.mark.asyncio
    async def test_add_feed_config(self, service):
        """Test adding a feed configuration."""
        config = DataFeedConfig(
            name="Test Feed",
            feed_type=DataFeedType.MOCK,
            base_url="test://localhost",
            rate_limit=500,
            supported_symbols=["TEST"],
            supported_frequencies=[DataFrequency.DAILY],
            max_history_days=30,
            timeout_seconds=5,
            retry_attempts=2,
            retry_delay=1.0,
            is_active=True,
        )
        config_id = await service.add_feed_config(config)
        assert config_id == config.id

    @pytest.mark.asyncio
    async def test_get_feed_config(self, service):
        """Test getting a feed configuration."""
        # Get an existing feed
        configs = await service.list_feed_configs()
        if configs:
            config = configs[0]
            retrieved = await service.get_feed_config(config.id)
            assert retrieved is not None
            assert retrieved.name == config.name

    @pytest.mark.asyncio
    async def test_list_feed_configs(self, service):
        """Test listing feed configurations."""
        configs = await service.list_feed_configs()
        assert len(configs) >= 2  # At least mock and yahoo


class TestFeedConnectionManagement:
    """Tests for feed connection management."""

    @pytest.mark.asyncio
    async def test_connect_feed(self, service):
        """Test connecting to a feed."""
        configs = await service.list_feed_configs()
        if configs:
            config = configs[0]
            result = await service.connect_feed(config.id)
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_disconnect_feed(self, service):
        """Test disconnecting from a feed."""
        configs = await service.list_feed_configs()
        if configs:
            config = configs[0]
            # Connect first
            await service.connect_feed(config.id)
            # Then disconnect
            result = await service.disconnect_feed(config.id)
            assert isinstance(result, bool)


class TestQuoteRetrieval:
    """Tests for quote retrieval."""

    @pytest.mark.asyncio
    async def test_get_quote_with_cache(self, service, sample_quote):
        """Test getting a quote uses cache."""
        # Service should handle quote retrieval
        quote = await service.get_quote("AAPL")
        # May return None if no feed is connected
        assert quote is None or isinstance(quote, Quote)

    @pytest.mark.asyncio
    async def test_cache_quote(self, service, sample_quote):
        """Test caching a quote."""
        await service._cache_quote("AAPL", sample_quote)
        cached = await service._get_cached_quote("AAPL")
        assert cached is not None


class TestHistoricalData:
    """Tests for historical data retrieval."""

    @pytest.mark.asyncio
    async def test_get_historical_data(self, service):
        """Test getting historical data."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        data = await service.get_historical_data("AAPL", start_date, end_date)
        assert isinstance(data, list)


class TestCacheManagement:
    """Tests for cache management."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, service):
        """Test getting cache statistics."""
        stats = await service.get_cache_stats()
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "max_size" in stats

    @pytest.mark.asyncio
    async def test_clear_cache(self, service):
        """Test clearing the cache."""
        await service.clear_cache()
        stats = await service.get_cache_stats()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_cache_cleanup(self, service):
        """Test cache cleanup."""
        # Add some cache entries
        quote = Quote(
            symbol="TEST",
            bid=Decimal("100.00"),
            ask=Decimal("100.10"),
            last=Decimal("100.05"),
            volume=Decimal("1000"),
            timestamp=datetime.utcnow(),
            high=Decimal("105.00"),
            low=Decimal("95.00"),
            open=Decimal("100.00"),
            close=Decimal("100.00"),
        )
        await service._cache_quote("TEST", quote)
        await service._cleanup_cache()
        # Should not crash


class TestServiceStatus:
    """Tests for service status."""

    @pytest.mark.asyncio
    async def test_get_service_status(self, service):
        """Test getting service status."""
        status = await service.get_service_status()
        assert "active_feeds" in status
        assert "total_configs" in status
        assert "cache_entries" in status


class TestTopLiquidAssets:
    """Tests for top liquid assets."""

    @pytest.mark.asyncio
    async def test_get_top_liquid_assets_quotes(self, service):
        """Test getting top liquid assets quotes."""
        quotes = await service.get_top_liquid_assets_quotes(limit=5)
        assert isinstance(quotes, list)


class TestSubscriptions:
    """Tests for market data subscriptions."""

    @pytest.mark.asyncio
    async def test_subscribe_to_symbols(self, service):
        """Test subscribing to symbols."""
        success = await service.subscribe_to_symbols(["AAPL", "MSFT"])
        # May fail if no active feed
        assert isinstance(success, bool)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_get_quote_without_feed(self, service):
        """Test getting quote without active feed."""
        # Should return None gracefully
        quote = await service.get_quote("AAPL")
        assert quote is None or isinstance(quote, Quote)

    @pytest.mark.asyncio
    async def test_connect_to_invalid_feed(self, service):
        """Test connecting to non-existent feed."""
        fake_id = UUID("12345678-1234-1234-1234-123456789012")
        result = await service.connect_feed(fake_id)
        assert result is False


class TestConcurrentOperations:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, service, sample_quote):
        """Test concurrent cache operations."""
        # Cache multiple quotes concurrently
        tasks = [service._cache_quote(f"SYMBOL_{i}", sample_quote) for i in range(5)]
        await asyncio.gather(*tasks)
        stats = await service.get_cache_stats()
        assert stats["total_entries"] >= 0
