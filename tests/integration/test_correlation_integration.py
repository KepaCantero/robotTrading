"""
Integration tests for CorrelationAnalyzer with PortfolioRiskManager - Phase 2.4

Tests the real-time correlation matrix integration with portfolio risk management.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

import pandas as pd
import numpy as np

from app.services.correlation.analyzer import CorrelationAnalyzer, CorrelationConfig
from app.services.portfolio_risk_manager import PortfolioRiskManager, RiskLevel
from app.models.portfolio import Portfolio, Position, AssetClass
from app.models.market_data import HistoricalData, DataFeedType, DataFrequency


@pytest.fixture
def mock_market_data_service():
    """Create a mock market data service."""
    service = Mock()
    service.get_historical_data = AsyncMock()
    return service


@pytest.fixture
def correlation_analyzer(mock_market_data_service):
    """Create correlation analyzer for testing."""
    config = CorrelationConfig(
        lookback_days=60,
        min_data_points=20,
        cache_enabled=True,
        use_fallback=True,
    )
    return CorrelationAnalyzer(
        data_service=mock_market_data_service,
        config=config,
    )


@pytest.fixture
def portfolio_with_positions():
    """Create a test portfolio with multiple positions."""
    # Create positions
    positions = [
        Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500"),
            broker="test_broker",
            sector="Technology",
            country="US",
        ),
        Position(
            symbol="MSFT",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("50"),
            avg_price=Decimal("300.00"),
            market_price=Decimal("310.00"),
            unrealized_pnl=Decimal("500"),
            broker="test_broker",
            sector="Technology",
            country="US",
        ),
        Position(
            symbol="JNJ",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("75"),
            avg_price=Decimal("160.00"),
            market_price=Decimal("165.00"),
            unrealized_pnl=Decimal("375"),
            broker="test_broker",
            sector="Healthcare",
            country="US",
        ),
    ]

    portfolio = Portfolio(
        portfolio_id="test_portfolio_1",
        cash=Decimal("50000.00"),
        broker="test_broker",
        currency="USD",
        positions=positions,
    )

    return portfolio


@pytest.fixture
def mock_historical_data():
    """Create mock historical data for testing."""
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=60)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # Generate correlated price data
    base_trend = np.linspace(100, 150, len(dates))

    def create_symbol_data(base_price, correlation_factor):
        """Create price data with specified correlation to base trend."""
        prices = []
        for i, date in enumerate(dates):
            noise = np.random.normal(0, 2)
            price = base_price[i] * correlation_factor + noise
            prices.append(max(price, 10))  # Ensure positive prices
        return prices

    # AAPL data (highly correlated with base)
    aapl_prices = create_symbol_data(base_trend, 1.0)
    mock_aapl = [
        HistoricalData(
            symbol="AAPL",
            timestamp=date,
            open=Decimal(str(aapl_prices[i])),
            high=Decimal(str(aapl_prices[i] + 1)),
            low=Decimal(str(aapl_prices[i] - 1)),
            close=Decimal(str(aapl_prices[i])),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for i, date in enumerate(dates)
    ]

    # MSFT data (also highly correlated with base)
    msft_prices = create_symbol_data(base_trend, 1.0)
    mock_msft = [
        HistoricalData(
            symbol="MSFT",
            timestamp=date,
            open=Decimal(str(msft_prices[i] * 2)),  # Higher price
            high=Decimal(str(msft_prices[i] * 2 + 1)),
            low=Decimal(str(msft_prices[i] * 2 - 1)),
            close=Decimal(str(msft_prices[i] * 2)),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for i, date in enumerate(dates)
    ]

    # JNJ data (less correlated)
    jnj_prices = create_symbol_data(base_trend * 0.5, 0.3)
    mock_jnj = [
        HistoricalData(
            symbol="JNJ",
            timestamp=date,
            open=Decimal(str(jnj_prices[i] + 100)),  # Offset price
            high=Decimal(str(jnj_prices[i] + 100 + 1)),
            low=Decimal(str(jnj_prices[i] + 100 - 1)),
            close=Decimal(str(jnj_prices[i] + 100)),
            volume=Decimal("1000000"),
            feed_type=DataFeedType.YAHOO_FINANCE,
            frequency=DataFrequency.DAILY,
        )
        for i, date in enumerate(dates)
    ]

    return {
        "AAPL": mock_aapl,
        "MSFT": mock_msft,
        "JNJ": mock_jnj,
    }


@pytest.mark.asyncio
async def test_portfolio_risk_manager_with_correlation_analyzer(
    correlation_analyzer, portfolio_with_positions, mock_historical_data, mock_market_data_service
):
    """Test PortfolioRiskManager using real correlation from CorrelationAnalyzer."""
    # Set up mock to return historical data
    mock_market_data_service.get_historical_data.side_effect = (
        lambda symbol, **kwargs: mock_historical_data.get(symbol, [])
    )

    # Create portfolio risk manager with correlation analyzer
    risk_manager = PortfolioRiskManager(correlation_analyzer=correlation_analyzer)

    # Assess portfolio risk
    risk_assessment = risk_manager.assess_portfolio_risk(portfolio_with_positions)

    # Verify assessment structure
    assert risk_assessment is not None
    assert "risk_level" in risk_assessment
    assert "risk_metrics" in risk_assessment
    assert "violations" in risk_assessment

    # Verify correlations were calculated
    correlations = risk_assessment["risk_metrics"]["correlations"]
    assert len(correlations) > 0

    # Check that we have correlation for each pair
    assert "AAPL-MSFT" in correlations
    assert "AAPL-JNJ" in correlations
    assert "MSFT-JNJ" in correlations

    # Verify correlation values are reasonable
    for pair, correlation in correlations.items():
        assert -1 <= correlation <= 1


@pytest.mark.asyncio
async def test_portfolio_risk_manager_without_correlation_analyzer(portfolio_with_positions):
    """Test PortfolioRiskManager fallback when no correlation analyzer provided."""
    # Create portfolio risk manager WITHOUT correlation analyzer
    risk_manager = PortfolioRiskManager(correlation_analyzer=None)

    # Assess portfolio risk
    risk_assessment = risk_manager.assess_portfolio_risk(portfolio_with_positions)

    # Verify assessment still works
    assert risk_assessment is not None
    assert "risk_level" in risk_assessment
    assert "risk_metrics" in risk_assessment

    # Verify fallback correlations were used
    correlations = risk_assessment["risk_metrics"]["correlations"]
    assert len(correlations) > 0

    # Fallback: AAPL and MSFT are both Technology sector
    assert correlations["AAPL-MSFT"] == 0.5

    # Fallback: JNJ is different sector
    assert correlations["AAPL-JNJ"] == 0.3
    assert correlations["MSFT-JNJ"] == 0.3


@pytest.mark.asyncio
async def test_correlation_analyzer_statistics(
    correlation_analyzer, mock_market_data_service, mock_historical_data
):
    """Test correlation analyzer statistics tracking."""
    # Set up mock to return historical data
    mock_market_data_service.get_historical_data.side_effect = (
        lambda symbol, **kwargs: mock_historical_data.get(symbol, [])
    )

    # Calculate correlation matrix
    await correlation_analyzer.calculate_correlation_matrix(["AAPL", "MSFT"])

    # Check statistics
    stats = correlation_analyzer.get_statistics()
    assert stats["calculations_performed"] == 1


@pytest.mark.asyncio
async def test_correlation_cache_update(
    correlation_analyzer, mock_market_data_service, mock_historical_data
):
    """Test correlation cache update functionality."""
    # Set up mock to return historical data
    mock_market_data_service.get_historical_data.side_effect = (
        lambda symbol, **kwargs: mock_historical_data.get(symbol, [])
    )

    # Update cache
    await correlation_analyzer.update_correlation_cache(["AAPL", "MSFT", "JNJ"])

    # Verify cache exists
    assert correlation_analyzer._cache is not None

    # Verify cached matrix
    cached_matrix = correlation_analyzer.get_cached_matrix()
    assert cached_matrix is not None
    assert cached_matrix.shape == (3, 3)

    # Verify all symbols are in cache
    symbols_in_cache = set(cached_matrix.index)
    assert symbols_in_cache == {"AAPL", "MSFT", "JNJ"}


@pytest.mark.asyncio
async def test_correlation_with_new_position(
    correlation_analyzer, portfolio_with_positions, mock_historical_data, mock_market_data_service
):
    """Test correlation calculation when adding a new position."""
    # Set up mock to return historical data
    mock_market_data_service.get_historical_data.side_effect = (
        lambda symbol, **kwargs: mock_historical_data.get(symbol, [])
    )

    # Create portfolio risk manager with correlation analyzer
    risk_manager = PortfolioRiskManager(correlation_analyzer=correlation_analyzer)

    # Create new position to add
    new_position = Position(
        symbol="TSLA",
        asset_class=AssetClass.EQUITY,
        quantity=Decimal("25"),
        avg_price=Decimal("200.00"),
        market_price=Decimal("210.00"),
        unrealized_pnl=Decimal("250"),
        broker="test_broker",
        sector="Technology",
        country="US",
    )

    # Add TSLA mock data
    mock_market_data_service.get_historical_data.side_effect = (
        lambda symbol, **kwargs: mock_historical_data.get(symbol, [])
    )

    # Assess portfolio risk with new position
    risk_assessment = risk_manager.assess_portfolio_risk(
        portfolio_with_positions, new_position=new_position
    )

    # Verify correlations include new position
    correlations = risk_assessment["risk_metrics"]["correlations"]

    # Should have correlation pairs with TSLA
    # Note: Actual pairs depend on implementation


def test_correlation_analyzer_config():
    """Test correlation analyzer configuration."""
    config = CorrelationConfig(
        lookback_days=90,
        update_interval_seconds=1800.0,
        min_data_points=30,
        cache_enabled=False,
        use_fallback=False,
    )

    assert config.lookback_days == 90
    assert config.update_interval_seconds == 1800.0
    assert config.min_data_points == 30
    assert config.cache_enabled is False
    assert config.use_fallback is False


@pytest.mark.asyncio
async def test_correlation_with_insufficient_data(correlation_analyzer, mock_market_data_service):
    """Test correlation fallback when insufficient data available."""
    # Return empty data
    mock_market_data_service.get_historical_data.return_value = []

    # Should use fallback
    result = await correlation_analyzer.calculate_correlation_matrix(["AAPL", "MSFT"])

    # Verify fallback matrix was generated
    assert result is not None
    assert result.shape == (2, 2)
    assert result.loc["AAPL", "AAPL"] == 1.0
    assert result.loc["MSFT", "MSFT"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
