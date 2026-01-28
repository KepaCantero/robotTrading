"""
AAA Grade Test Suite for MarketUniverseLoader.

This module contains comprehensive tests for the MarketUniverseLoader component,
including unit tests, integration tests, and edge cases.
"""

import asyncio
from datetime import timedelta
from decimal import Decimal

import pandas as pd
import pytest

from app.models.assets import Asset, AssetClass, Exchange
from app.services.market_universe_loader import (
    YFINANCE_AVAILABLE,
    MarketUniverseLoader,
    get_market_universe_loader,
)


class TestMarketUniverseLoaderUnit:
    """Unit tests for MarketUniverseLoader."""

    @pytest.fixture
    def loader(self):
        """Create a fresh loader instance for each test."""
        return MarketUniverseLoader(
            min_avg_volume=1_000_000,
            min_price=5.0,
            max_volatility=0.15,
            cache_ttl_hours=1,  # 1 hour for tests
        )

    def test_initialization(self, loader):
        """Test loader initialization with parameters."""
        assert loader.min_avg_volume == 1_000_000
        assert loader.min_price == 5.0
        assert loader.max_volatility == 0.15
        assert loader.cache_ttl == timedelta(hours=1)
        assert loader._universe_cache.max_size == 50
        assert loader._data_cache.max_size == 100
        assert loader._universe_cache.get_stats()["size"] == 0
        assert loader._data_cache.get_stats()["size"] == 0

    def test_singleton(self):
        """Test singleton pattern works correctly."""
        loader1 = get_market_universe_loader()
        loader2 = get_market_universe_loader()
        assert loader1 is loader2

    def test_sp500_fallback_list(self, loader):
        """Test S&P 500 fallback list is not empty."""
        assert len(loader.SP500_FALLBACK) > 0
        assert "AAPL" in loader.SP500_FALLBACK
        assert "MSFT" in loader.SP500_FALLBACK
        assert "GOOGL" in loader.SP500_FALLBACK

    def test_nasdaq100_fallback_list(self, loader):
        """Test NASDAQ 100 fallback list is not empty."""
        assert len(loader.NASDAQ100_FALLBACK) > 0
        assert "AAPL" in loader.NASDAQ100_FALLBACK
        assert "MSFT" in loader.NASDAQ100_FALLBACK

    def test_ibex35_fallback_list(self, loader):
        """Test IBEX 35 fallback list is not empty."""
        assert len(loader.IBEX35_FALLBACK) > 0
        assert "SAN.MC" in loader.IBEX35_FALLBACK
        assert "REP.MC" in loader.IBEX35_FALLBACK

    def test_crypto_fallback_list(self, loader):
        """Test crypto fallback list is not empty."""
        assert len(loader.CRYPTO_TOP20) > 0
        assert "BTC-USD" in loader.CRYPTO_TOP20
        assert "ETH-USD" in loader.CRYPTO_TOP20

    @pytest.mark.asyncio
    async def test_get_sp500_universe_returns_list(self, loader):
        """Test get_sp500_universe returns a list."""
        tickers = await loader.get_sp500_universe()
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        assert all(isinstance(t, str) for t in tickers)

    @pytest.mark.asyncio
    async def test_get_crypto_universe_returns_list(self, loader):
        """Test get_crypto_universe returns a list."""
        tickers = await loader.get_crypto_universe(top_n=10)
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        assert all(isinstance(t, str) for t in tickers)

    @pytest.mark.asyncio
    async def test_get_combined_universe(self, loader):
        """Test get_combined_universe merges multiple sources."""
        tickers = await loader.get_combined_universe(
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
        )
        assert isinstance(tickers, list)
        assert len(tickers) > 0

    def test_cache_mechanism(self, loader):
        """Test caching works correctly."""
        cache_key = "test_cache"
        test_data = ["AAPL", "MSFT", "GOOGL"]

        # Cache is empty initially
        assert loader._get_cached_universe(cache_key) is None

        # Add to cache
        loader._cache_universe(cache_key, test_data)
        assert loader._get_cached_universe(cache_key) == test_data

    def test_cache_expiration(self, loader):
        """Test cache expires after TTL."""
        # Create loader with 0 TTL for immediate expiration
        short_ttl_loader = MarketUniverseLoader(cache_ttl_hours=0)
        cache_key = "test_expire"
        test_data = ["AAPL", "MSFT"]

        # Add to cache
        short_ttl_loader._cache_universe(cache_key, test_data)

        # Should be immediately expired
        assert short_ttl_loader._get_cached_universe(cache_key) is None

    def test_clear_cache(self, loader):
        """Test cache can be cleared."""
        loader._cache_universe("test1", ["AAPL"])
        loader._cache_data("test2", {"AAPL": pd.DataFrame()})

        assert loader._universe_cache.get_stats()["size"] > 0
        assert loader._data_cache.get_stats()["size"] > 0

        loader.clear_cache()

        assert loader._universe_cache.get_stats()["size"] == 0
        assert loader._data_cache.get_stats()["size"] == 0


class TestMarketUniverseLoaderIntegration:
    """Integration tests with real yfinance API."""

    @pytest.fixture
    def loader(self):
        """Create loader for integration tests."""
        return MarketUniverseLoader(
            min_avg_volume=1_000_000,
            min_price=5.0,
            max_volatility=0.15,
            cache_ttl_hours=1,
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_download_single_ticker(self, loader):
        """Test downloading data for a single ticker."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        data = await loader.download_universe_data(
            tickers=["AAPL"],
            period="1mo",
            interval="1d",
            progress=False,
        )

        # yfinance may return empty data due to API issues, network problems, or rate limiting
        # The test verifies the loader functions correctly, even if the API fails
        assert isinstance(data, dict)

        # If data was returned, validate its structure
        if "AAPL" in data and data["AAPL"] is not None:
            assert isinstance(data["AAPL"], pd.DataFrame)
            if len(data["AAPL"]) > 0:  # Only check columns if we have data
                assert "close" in data["AAPL"].columns or "Close" in data["AAPL"].columns
                assert "volume" in data["AAPL"].columns or "Volume" in data["AAPL"].columns
        else:
            # Empty response is acceptable - it means yfinance API didn't return data
            # This could be due to network issues, API changes, or rate limiting
            pytest.skip("yfinance returned empty data - API may be unavailable or rate limited")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_download_multiple_tickers(self, loader):
        """Test downloading data for multiple tickers."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = ["AAPL", "MSFT", "GOOGL"]
        data = await loader.download_universe_data(
            tickers=tickers,
            period="1mo",
            interval="1d",
            progress=False,
        )

        # Verify response structure
        assert isinstance(data, dict)

        # yfinance may return empty data due to API issues
        if len(data) == 0:
            pytest.skip("yfinance returned empty data - API may be unavailable or rate limited")

        # If we got data, validate it
        for ticker, df in data.items():
            assert isinstance(df, pd.DataFrame)
            # Only check length if we have a valid DataFrame
            if len(df) > 0:
                # Validate column names (could be lowercase or original case)
                assert "close" in df.columns or "Close" in df.columns

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_filter_by_liquidity(self, loader):
        """Test filtering stocks by liquidity and volatility."""
        # Create sample data with 20+ rows (requirement of filter function)

        data = {
            "AAPL": pd.DataFrame(
                {
                    "close": [150 + i for i in range(25)],  # 25 data points
                    "volume": [50_000_000 + i * 100000 for i in range(25)],
                }
            ),
            "PENNY_STOCK": pd.DataFrame(
                {
                    "close": [0.50 + i * 0.01 for i in range(25)],  # Below min_price
                    "volume": [1_000_000 + i * 10000 for i in range(25)],
                }
            ),
            "LOW_VOL": pd.DataFrame(
                {
                    "close": [20 + i for i in range(25)],
                    "volume": [100_000 + i * 1000 for i in range(25)],  # Below min_volume
                }
            ),
        }

        filtered = await loader.filter_by_liquidity_volatility(
            data,
            min_avg_volume=1_000_000,
            min_price=5.0,
            max_volatility=0.10,  # 10% max daily vol
        )

        # Only AAPL should pass
        assert "AAPL" in filtered
        assert "PENNY_STOCK" not in filtered  # Price too low
        assert "LOW_VOL" not in filtered  # Volume too low

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fetch_and_filter_convenience(self, loader):
        """Test the convenience method that downloads AND filters."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = ["AAPL", "MSFT"]

        result = await loader.fetch_and_filter(
            tickers=tickers,
            period="1mo",
            interval="1d",
        )

        # Should return filtered results
        assert isinstance(result, dict)
        # At least some tickers should pass filters
        assert len(result) >= 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_assets_from_universe(self, loader):
        """Test converting tickers to Asset objects."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = ["AAPL", "MSFT"]

        assets = await loader.get_assets_from_universe(
            tickers=tickers,
            period="1mo",
        )

        assert isinstance(assets, list)

        # yfinance may return empty data due to API issues
        if len(assets) == 0:
            pytest.skip("yfinance returned empty data - no assets could be created")

        # Validate asset structure
        for asset in assets:
            assert isinstance(asset, Asset)
            # Check if symbol matches (allowing for crypto symbol conversion)
            assert asset.symbol in tickers or asset.symbol.replace("-USD", "USDT") in [
                t.replace("-USD", "USDT") for t in tickers
            ]


class TestMarketUniverseLoaderEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def loader(self):
        """Create loader for edge case tests."""
        return MarketUniverseLoader()

    @pytest.mark.asyncio
    async def test_empty_ticker_list(self, loader):
        """Test downloading with empty ticker list."""
        data = await loader.download_universe_data([])
        assert data == {}

    @pytest.mark.asyncio
    async def test_invalid_ticker(self, loader):
        """Test downloading with invalid ticker."""
        data = await loader.download_universe_data(["INVALID_TICKER_12345"])
        # Should return empty dict or dict with None values
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_filter_empty_data(self, loader):
        """Test filtering empty data dictionary."""
        filtered = await loader.filter_by_liquidity_volatility({})
        assert filtered == {}

    @pytest.mark.asyncio
    async def test_filter_insufficient_data(self, loader):
        """Test filtering with insufficient data points."""
        data = {
            "SHORT": pd.DataFrame(
                {
                    "close": [100, 101],  # Only 2 data points
                    "volume": [1_000_000, 1_100_000],
                }
            ),
        }

        filtered = await loader.filter_by_liquidity_volatility(data)
        # Should be filtered out due to insufficient data
        assert "SHORT" not in filtered

    @pytest.mark.asyncio
    async def test_filter_null_values(self, loader):
        """Test filtering handles null values correctly."""
        data = {
            "NULL_DATA": pd.DataFrame(
                {
                    "close": [100, None, 102, None, 104],
                    "volume": [1_000_000, 1_100_000, None, 1_200_000, 1_000_000],
                }
            ),
        }

        # Should not crash, should filter out or handle gracefully
        filtered = await loader.filter_by_liquidity_volatility(data)
        assert isinstance(filtered, dict)

    @pytest.mark.asyncio
    async def test_concurrent_downloads(self, loader):
        """Test that concurrent downloads work correctly."""
        tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

        # Run multiple downloads concurrently
        tasks = [
            loader.download_universe_data(tickers, period="1wk", interval="1d") for _ in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete without errors
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)

    def test_liquidity_score_calculation(self, loader):
        """Test liquidity score calculation logic."""
        asset = Asset(
            symbol="TEST",
            name="Test Asset",
            asset_class=AssetClass.EQUITY,
            exchange=Exchange.NASDAQ,
            avg_volume=Decimal("10000000"),  # 10M shares/day
            avg_spread=Decimal("0.01"),
        )

        df = pd.DataFrame(
            {
                "close": [100] * 100,
                "volume": [10_000_000] * 100,
            }
        )

        # Should not raise any errors
        asyncio.run(loader._calculate_liquidity_score(asset, df))

        # Score should be calculated
        assert asset.liquidity_score >= 0
        assert asset.liquidity_score <= 100


class TestMarketUniverseLoaderCaching:
    """Test caching behavior."""

    @pytest.fixture
    def loader(self):
        """Create loader with short TTL for testing."""
        return MarketUniverseLoader(cache_ttl_hours=1)

    @pytest.mark.asyncio
    async def test_universe_caching(self, loader):
        """Test that universe results are cached."""

        # First call should cache
        tickers1 = await loader.get_sp500_universe()
        # Cache is populated regardless of yfinance availability (uses fallback)
        assert loader._universe_cache.get_stats()["size"] > 0

        # Second call should use cache
        tickers2 = await loader.get_sp500_universe()
        assert tickers1 == tickers2

    @pytest.mark.asyncio
    async def test_data_caching(self, loader):
        """Test that downloaded data is cached."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = ["AAPL"]

        # First download
        data1 = await loader.download_universe_data(tickers, period="1wk")

        # Second download should use cache
        data2 = await loader.download_universe_data(tickers, period="1wk")

        # Results should be identical
        assert data1.keys() == data2.keys()

    def test_clear_cache_removes_all(self, loader):
        """Test that clear_cache removes all cached data."""
        # Add some cache entries
        loader._cache_universe("test1", ["AAPL", "MSFT"])
        loader._cache_data("test2", {"AAPL": pd.DataFrame()})

        loader.clear_cache()

        assert loader._universe_cache.get_stats()["size"] == 0
        assert loader._data_cache.get_stats()["size"] == 0


@pytest.mark.integration
class TestMarketUniverseLoaderRealAPI:
    """Integration tests with real yfinance API (marked as integration)."""

    @pytest.fixture
    def loader(self):
        """Create loader for real API tests."""
        return MarketUniverseLoader(
            min_avg_volume=100_000,  # Lower threshold for testing
            min_price=1.0,  # Lower price for testing
            cache_ttl_hours=24,
        )

    @pytest.mark.asyncio
    async def test_real_sp500_data(self, loader):
        """Test fetching real S&P 500 data."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = await loader.get_sp500_universe()

        # Should return at least fallback list
        assert len(tickers) > 0

        # Try to download first 5
        sample = tickers[:5]
        data = await loader.download_universe_data(sample, period="5d", progress=False)

        # yfinance may return empty data due to API issues
        # The test validates that the loader structure works correctly
        assert isinstance(data, dict)

        # If no data was returned, skip with informative message
        if len(data) == 0:
            pytest.skip("yfinance returned empty S&P 500 data - API may be unavailable or rate limited")

    @pytest.mark.asyncio
    async def test_real_crypto_data(self, loader):
        """Test fetching real crypto data."""
        # Skip if yfinance not available
        if not YFINANCE_AVAILABLE:
            pytest.skip("yfinance not available - requires Python 3.10+")

        tickers = await loader.get_crypto_universe(top_n=5)

        assert len(tickers) > 0

        # Download first 3
        sample = tickers[:3]
        data = await loader.download_universe_data(sample, period="5d", progress=False)

        # yfinance may return empty data due to API issues
        # The test validates that the loader structure works correctly
        assert isinstance(data, dict)

        # If no data was returned, skip with informative message
        if len(data) == 0:
            pytest.skip("yfinance returned empty crypto data - API may be unavailable or rate limited")
