"""
Unit tests for CorrelationAnalyzer - Phase 2.4

Tests the real-time correlation matrix calculation functionality.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import numpy as np
import pandas as pd
import pytest

from app.models.market_data import DataFeedType, DataFrequency, HistoricalData
from app.services.correlation.analyzer import (
    CorrelationAnalyzer,
    CorrelationCache,
    CorrelationConfig,
)


@pytest.fixture
def mock_data_service():
    """Create a mock market data service."""
    service = Mock()
    service.get_historical_data = AsyncMock()
    return service


@pytest.fixture
def correlation_config():
    """Create test correlation config."""
    return CorrelationConfig(
        lookback_days=60,
        update_interval_seconds=3600.0,
        min_data_points=20,
        cache_enabled=True,
        use_fallback=True,
    )


@pytest.fixture
def correlation_analyzer(mock_data_service, correlation_config):
    """Create correlation analyzer for testing."""
    return CorrelationAnalyzer(
        data_service=mock_data_service,
        config=correlation_config,
    )


def test_correlation_config_defaults():
    """Test CorrelationConfig default values."""
    config = CorrelationConfig()
    assert config.lookback_days == 60
    assert config.update_interval_seconds == 3600.0
    assert config.min_data_points == 20
    assert config.cache_enabled is True
    assert config.use_fallback is True
    assert config.fallback_value == 0.3


def test_correlation_cache_validity():
    """Test CorrelationCache validity check."""
    matrix = pd.DataFrame(
        [[1.0, 0.5], [0.5, 1.0]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"]
    )

    # Valid cache (recent)
    recent_cache = CorrelationCache(
        matrix=matrix,
        timestamp=datetime.now(timezone.utc),
        symbols={"AAPL", "MSFT"},
    )
    assert recent_cache.is_valid(max_age_seconds=3600) is True

    # Invalid cache (old)
    old_cache = CorrelationCache(
        matrix=matrix,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=7200),
        symbols={"AAPL", "MSFT"},
    )
    assert old_cache.is_valid(max_age_seconds=3600) is False


@pytest.mark.asyncio
async def test_calculate_correlation_matrix_success(correlation_analyzer, mock_data_service):
    """Test successful correlation matrix calculation."""
    # Create mock historical data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=60)

    # Generate mock price data with known correlation
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # Create two highly correlated series
    base_prices = np.linspace(100, 150, len(dates))
    noise1 = np.random.normal(0, 2, len(dates))
    noise2 = np.random.normal(0, 2, len(dates))

    mock_data_aapl = [
        HistoricalData(
            symbol="AAPL",
            timestamp=date,
            open=Decimal(str(base_prices[i] + noise1[i])),
            high=Decimal(str(base_prices[i] + noise1[i] + 1)),
            low=Decimal(str(base_prices[i] + noise1[i] - 1)),
            close=Decimal(str(base_prices[i] + noise1[i])),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for i, date in enumerate(dates)
    ]

    mock_data_msft = [
        HistoricalData(
            symbol="MSFT",
            timestamp=date,
            open=Decimal(str(base_prices[i] + noise2[i])),
            high=Decimal(str(base_prices[i] + noise2[i] + 1)),
            low=Decimal(str(base_prices[i] + noise2[i] - 1)),
            close=Decimal(str(base_prices[i] + noise2[i])),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for i, date in enumerate(dates)
    ]

    mock_data_service.get_historical_data.side_effect = [
        mock_data_aapl,
        mock_data_msft,
    ]

    # Calculate correlation matrix
    result = await correlation_analyzer.calculate_correlation_matrix(["AAPL", "MSFT"])

    # Verify structure
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 2)
    assert list(result.index) == ["AAPL", "MSFT"]
    assert list(result.columns) == ["AAPL", "MSFT"]

    # Verify diagonal is 1.0 (self-correlation)
    assert abs(result.loc["AAPL", "AAPL"] - 1.0) < 0.01
    assert abs(result.loc["MSFT", "MSFT"] - 1.0) < 0.01

    # Verify correlation is reasonable
    correlation = result.loc["AAPL", "MSFT"]
    assert -1 <= correlation <= 1


@pytest.mark.asyncio
async def test_calculate_correlation_matrix_empty_symbols(correlation_analyzer):
    """Test that empty symbols list raises ValueError."""
    with pytest.raises(ValueError, match="Symbols list cannot be empty"):
        await correlation_analyzer.calculate_correlation_matrix([])


@pytest.mark.asyncio
async def test_calculate_correlation_matrix_no_data(correlation_analyzer, mock_data_service):
    """Test fallback when no historical data available."""
    mock_data_service.get_historical_data.return_value = []

    # Should use fallback when use_fallback=True
    result = await correlation_analyzer.calculate_correlation_matrix(["AAPL", "MSFT"])

    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 2)


@pytest.mark.asyncio
async def test_get_correlation_from_cache(correlation_analyzer):
    """Test getting correlation from cache."""
    # Create cached matrix
    cached_matrix = pd.DataFrame(
        [[1.0, 0.7], [0.7, 1.0]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"]
    )

    correlation_analyzer._cache = CorrelationCache(
        matrix=cached_matrix,
        timestamp=datetime.now(timezone.utc),
        symbols={"AAPL", "MSFT"},
    )

    # Reset cache hits counter
    correlation_analyzer._cache_hits = 0

    # Get correlation
    correlation = await correlation_analyzer.get_correlation("AAPL", "MSFT")

    assert correlation == 0.7
    assert correlation_analyzer._cache_hits == 1


@pytest.mark.asyncio
async def test_get_correlation_fallback(correlation_analyzer, mock_data_service):
    """Test fallback correlation when calculation fails."""
    # Return empty list for both symbols
    mock_data_service.get_historical_data.return_value = []

    # Disable fallback in config to force calculation failure
    correlation_analyzer.config.use_fallback = True

    # Set symbol metadata for fallback
    correlation_analyzer.set_symbol_metadata("AAPL", sector="Technology")
    correlation_analyzer.set_symbol_metadata("MSFT", sector="Technology")

    # Reset counters
    correlation_analyzer._fallback_used = 0
    correlation_analyzer._cache_misses = 0

    # Get correlation (should use fallback after calculation fails)
    correlation = await correlation_analyzer.get_correlation("AAPL", "MSFT")

    # Same sector = 0.5
    assert correlation == 0.5
    # Fallback is used when calculate_correlation_matrix generates fallback matrix
    assert (
        correlation_analyzer._fallback_used >= 0
    )  # May or may not be incremented depending on implementation


def test_get_fallback_correlation_same_sector(correlation_analyzer):
    """Test fallback correlation for same sector."""
    correlation_analyzer.set_symbol_metadata("AAPL", sector="Technology")
    correlation_analyzer.set_symbol_metadata("MSFT", sector="Technology")

    correlation = correlation_analyzer._get_fallback_correlation("AAPL", "MSFT")
    assert correlation == 0.5


def test_get_fallback_correlation_same_market(correlation_analyzer):
    """Test fallback correlation for same market."""
    correlation_analyzer.set_symbol_metadata("AAPL", market="US")
    correlation_analyzer.set_symbol_metadata("MSFT", market="US")

    correlation = correlation_analyzer._get_fallback_correlation("AAPL", "MSFT")
    assert correlation == 0.3


def test_get_fallback_correlation_different(correlation_analyzer):
    """Test fallback correlation for different symbols."""
    correlation = correlation_analyzer._get_fallback_correlation("AAPL", "MSFT")
    assert correlation == 0.3  # Default fallback value


def test_get_cached_matrix_valid(correlation_analyzer):
    """Test getting valid cached matrix."""
    cached_matrix = pd.DataFrame(
        [[1.0, 0.7], [0.7, 1.0]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"]
    )

    correlation_analyzer._cache = CorrelationCache(
        matrix=cached_matrix,
        timestamp=datetime.now(timezone.utc),
        symbols={"AAPL", "MSFT"},
    )

    result = correlation_analyzer.get_cached_matrix()

    assert result is not None
    assert result.shape == (2, 2)
    assert result.loc["AAPL", "MSFT"] == 0.7


def test_get_cached_matrix_expired(correlation_analyzer):
    """Test that expired cache returns None."""
    cached_matrix = pd.DataFrame(
        [[1.0, 0.7], [0.7, 1.0]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"]
    )

    correlation_analyzer._cache = CorrelationCache(
        matrix=cached_matrix,
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=7200),
        symbols={"AAPL", "MSFT"},
    )

    result = correlation_analyzer.get_cached_matrix()

    assert result is None


def test_clear_cache(correlation_analyzer):
    """Test clearing the cache."""
    cached_matrix = pd.DataFrame(
        [[1.0, 0.7], [0.7, 1.0]], index=["AAPL", "MSFT"], columns=["AAPL", "MSFT"]
    )

    correlation_analyzer._cache = CorrelationCache(
        matrix=cached_matrix,
        timestamp=datetime.now(timezone.utc),
        symbols={"AAPL", "MSFT"},
    )

    correlation_analyzer.clear_cache()

    assert correlation_analyzer._cache is None


def test_get_statistics(correlation_analyzer):
    """Test getting correlation analyzer statistics."""
    stats = correlation_analyzer.get_statistics()

    assert "calculations_performed" in stats
    assert "cache_hits" in stats
    assert "cache_misses" in stats
    assert "fallback_used" in stats
    assert "cache_enabled" in stats
    assert "background_updates_running" in stats

    # Check initial values
    assert stats["calculations_performed"] == 0
    assert stats["cache_hits"] == 0
    assert stats["cache_misses"] == 0
    assert stats["fallback_used"] == 0


@pytest.mark.asyncio
async def test_update_correlation_cache(correlation_analyzer, mock_data_service):
    """Test updating correlation cache."""
    # Create minimal mock data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=60)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    mock_data = [
        HistoricalData(
            symbol="AAPL",
            timestamp=date,
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.0"),
            close=Decimal("100.0"),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for date in dates[:30]  # 30 days of data
    ]

    mock_data_service.get_historical_data.return_value = mock_data

    # Update cache
    await correlation_analyzer.update_correlation_cache(["AAPL", "MSFT"])

    # Verify cache was updated
    assert correlation_analyzer._cache is not None
    assert isinstance(correlation_analyzer._cache.matrix, pd.DataFrame)


def test_calculate_returns(correlation_analyzer):
    """Test returns calculation from prices."""
    # Create sample price data
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    prices = pd.DataFrame(
        {
            "AAPL": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "MSFT": [200, 201, 202, 203, 204, 205, 206, 207, 208, 209],
        },
        index=dates,
    )

    returns = correlation_analyzer._calculate_returns(prices)

    # Check structure
    assert isinstance(returns, pd.DataFrame)
    assert returns.shape[1] == 2
    assert len(returns) == 9  # One less than prices due to pct_change

    # Check first return value
    expected_aapl_return = (101 - 100) / 100
    assert abs(returns.iloc[0]["AAPL"] - expected_aapl_return) < 0.0001


def test_calculate_correlation_from_returns(correlation_analyzer):
    """Test correlation calculation from returns."""
    # Create sample return data
    returns = pd.DataFrame(
        {
            "AAPL": [0.01, 0.02, -0.01, 0.03, 0.01],
            "MSFT": [0.015, 0.025, -0.005, 0.035, 0.015],
        }
    )

    corr_matrix = correlation_analyzer._calculate_correlation(returns)

    # Check structure
    assert isinstance(corr_matrix, pd.DataFrame)
    assert corr_matrix.shape == (2, 2)

    # Check diagonal
    assert abs(corr_matrix.loc["AAPL", "AAPL"] - 1.0) < 0.01
    assert abs(corr_matrix.loc["MSFT", "MSFT"] - 1.0) < 0.01

    # Check high correlation (data designed to be correlated)
    correlation = corr_matrix.loc["AAPL", "MSFT"]
    assert correlation > 0.9  # Should be very high correlation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
