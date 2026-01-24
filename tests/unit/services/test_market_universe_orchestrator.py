"""
AAA Grade Test Suite for MarketUniverseOrchestrator.

Este módulo contiene tests comprehensivos para el componente orquestador
que centraliza la obtención de datos de mercado y su paso a StrategyStockAllocator.

Author: AlgoTrading System
Created: 2025-01-23
"""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.services.market_universe_loader import MarketUniverseLoader
from app.services.market_universe_orchestrator import (
    MarketUniverseOrchestrator,
    get_market_universe_orchestrator,
)
from app.services.strategy_stock_allocator import (
    AllocationResult,
    StockMetrics,
    StrategyStockAllocator,
)


class TestMarketUniverseOrchestratorUnit:
    """Unit tests para MarketUniverseOrchestrator."""

    @pytest.fixture
    def mock_loader(self):
        """Mock MarketUniverseLoader."""
        loader = MagicMock(spec=MarketUniverseLoader)
        loader.get_combined_universe = AsyncMock(return_value=["AAPL", "MSFT", "GOOGL", "TSLA"])
        loader.download_universe_data = AsyncMock(
            return_value={
                "AAPL": pd.DataFrame(
                    {
                        "open": [150, 151, 152],
                        "high": [152, 153, 154],
                        "low": [149, 150, 151],
                        "close": [151, 152, 153],
                        "volume": [50_000_000, 51_000_000, 52_000_000],
                    }
                ),
                "MSFT": pd.DataFrame(
                    {
                        "open": [300, 301, 302],
                        "high": [302, 303, 304],
                        "low": [299, 300, 301],
                        "close": [301, 302, 303],
                        "volume": [30_000_000, 31_000_000, 32_000_000],
                    }
                ),
                "GOOGL": pd.DataFrame(
                    {
                        "open": [2800, 2810, 2820],
                        "high": [2820, 2830, 2840],
                        "low": [2790, 2800, 2810],
                        "close": [2810, 2820, 2830],
                        "volume": [1_500_000, 1_600_000, 1_700_000],
                    }
                ),
                "TSLA": pd.DataFrame(
                    {
                        "open": [800, 810, 820],
                        "high": [820, 830, 840],
                        "low": [790, 800, 810],
                        "close": [810, 820, 830],
                        "volume": [40_000_000, 41_000_000, 42_000_000],
                    }
                ),
            }
        )
        loader.filter_by_liquidity_volatility = AsyncMock(
            return_value={
                "AAPL": pd.DataFrame(
                    {
                        "open": [150, 151, 152],
                        "high": [152, 153, 154],
                        "low": [149, 150, 151],
                        "close": [151, 152, 153],
                        "volume": [50_000_000, 51_000_000, 52_000_000],
                    }
                ),
                "MSFT": pd.DataFrame(
                    {
                        "open": [300, 301, 302],
                        "high": [302, 303, 304],
                        "low": [299, 300, 301],
                        "close": [301, 302, 303],
                        "volume": [30_000_000, 31_000_000, 32_000_000],
                    }
                ),
            }
        )
        return loader

    @pytest.fixture
    def mock_allocator(self):
        """Mock StrategyStockAllocator."""
        allocator = MagicMock(spec=StrategyStockAllocator)
        allocator.allocate = MagicMock(
            return_value=AllocationResult(
                allocations={
                    "AAPL": StockMetrics(
                        ticker="AAPL",
                        strategy="momentum",
                        weight=0.5,
                        capital=50000.0,
                        sps_score=0.8,
                        decision_log="Test allocation",
                    )
                },
                pairs=[],
                residual_capital=50000.0,
                decision_logs=["Test"],
                validation_passed=True,
                validation_errors=[],
            )
        )
        return allocator

    @pytest.fixture
    def orchestrator(self, mock_loader, mock_allocator):
        """Create orchestrator with mocks."""
        return MarketUniverseOrchestrator(
            market_loader=mock_loader,
            stock_allocator=mock_allocator,
        )

    def test_initialization(self, mock_loader, mock_allocator):
        """Test orchestrator initialization."""
        orchestrator = MarketUniverseOrchestrator(
            market_loader=mock_loader,
            stock_allocator=mock_allocator,
        )

        assert orchestrator.market_loader is mock_loader
        assert orchestrator.stock_allocator is mock_allocator

    def test_initialization_defaults(self):
        """Test initialization with defaults creates instances."""
        orchestrator = MarketUniverseOrchestrator()

        assert orchestrator.market_loader is not None
        assert isinstance(orchestrator.market_loader, MarketUniverseLoader)
        assert orchestrator.stock_allocator is not None
        assert isinstance(orchestrator.stock_allocator, StrategyStockAllocator)

    @pytest.mark.asyncio
    async def test_get_universe_for_allocation(self, orchestrator, mock_loader):
        """Test getting universe for allocation."""
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
        )

        # Verify calls
        mock_loader.get_combined_universe.assert_called_once_with(
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
        )
        mock_loader.download_universe_data.assert_called_once()
        mock_loader.filter_by_liquidity_volatility.assert_called_once()

        # Verify result
        assert isinstance(result, dict)
        assert len(result) == 2  # AAPL and MSFT passed filters
        assert "AAPL" in result
        assert "MSFT" in result

    @pytest.mark.asyncio
    async def test_get_universe_for_allocation_empty_tickers(self, orchestrator, mock_loader):
        """Test handling empty tickers."""
        mock_loader.get_combined_universe = AsyncMock(return_value=[])

        result = await orchestrator.get_universe_for_allocation()

        assert result == {}
        mock_loader.download_universe_data.assert_not_called()
        mock_loader.filter_by_liquidity_volatility.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_universe_for_allocation_no_data_downloaded(self, orchestrator, mock_loader):
        """Test handling no data downloaded."""
        mock_loader.download_universe_data = AsyncMock(return_value={})

        result = await orchestrator.get_universe_for_allocation()

        assert result == {}
        mock_loader.filter_by_liquidity_volatility.assert_not_called()

    @pytest.mark.asyncio
    async def test_allocate_from_market_universe(self, orchestrator, mock_loader, mock_allocator):
        """Test complete allocation flow."""
        result = await orchestrator.allocate_from_market_universe(
            total_capital=100000,
            strategy_allocations={"momentum": 50000, "mean_reversion": 50000},
            include_sp500=True,
        )

        # Verify the flow
        mock_loader.get_combined_universe.assert_called_once()
        mock_loader.download_universe_data.assert_called_once()
        mock_loader.filter_by_liquidity_volatility.assert_called_once()
        mock_allocator.allocate.assert_called_once()

        # Verify allocation call
        alloc_call = mock_allocator.allocate.call_args
        assert alloc_call[1]["total_capital"] == 100000
        assert alloc_call[1]["strategy_allocations"] == {"momentum": 50000, "mean_reversion": 50000}
        assert len(alloc_call[1]["historical_data"]) == 2  # AAPL, MSFT

        # Verify result
        assert result.validation_passed is True
        assert len(result.allocations) == 1
        assert "AAPL" in result.allocations

    @pytest.mark.asyncio
    async def test_allocate_from_market_universe_no_data(
        self, orchestrator, mock_loader, mock_allocator
    ):
        """Test allocation when no data available."""
        mock_loader.get_combined_universe = AsyncMock(return_value=[])

        result = await orchestrator.allocate_from_market_universe(total_capital=100000)

        assert result.validation_passed is False
        assert "No hay datos disponibles" in result.validation_errors
        mock_allocator.allocate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_sp500_for_allocation(self, orchestrator, mock_loader):
        """Test S&P 500 shortcut method."""
        orchestrator.allocate_from_market_universe = AsyncMock(
            return_value=AllocationResult(
                allocations={},
                pairs=[],
                residual_capital=100000,
                validation_passed=True,
                validation_errors=[],
            )
        )

        await orchestrator.get_sp500_for_allocation(
            total_capital=100000,
            top_n=50,
        )

        orchestrator.allocate_from_market_universe.assert_called_once_with(
            total_capital=100000,
            strategy_allocations=None,
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
            top_n_per_universe=50,
        )

    @pytest.mark.asyncio
    async def test_get_ibex35_for_allocation(self, orchestrator, mock_loader):
        """Test IBEX 35 shortcut method."""
        orchestrator.allocate_from_market_universe = AsyncMock(
            return_value=AllocationResult(
                allocations={},
                pairs=[],
                residual_capital=100000,
                validation_passed=True,
                validation_errors=[],
            )
        )

        await orchestrator.get_ibex35_for_allocation(
            total_capital=100000,
            top_n=35,
        )

        orchestrator.allocate_from_market_universe.assert_called_once_with(
            total_capital=100000,
            strategy_allocations=None,
            include_sp500=False,
            include_nasdaq100=False,
            include_ibex35=True,
            include_crypto=False,
            top_n_per_universe=35,
        )

    @pytest.mark.asyncio
    async def test_get_crypto_for_allocation(self, orchestrator, mock_loader):
        """Test Crypto shortcut method."""
        orchestrator.allocate_from_market_universe = AsyncMock(
            return_value=AllocationResult(
                allocations={},
                pairs=[],
                residual_capital=100000,
                validation_passed=True,
                validation_errors=[],
            )
        )

        await orchestrator.get_crypto_for_allocation(
            total_capital=100000,
            top_n=20,
        )

        orchestrator.allocate_from_market_universe.assert_called_once_with(
            total_capital=100000,
            strategy_allocations=None,
            include_sp500=False,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=True,
            top_n_per_universe=20,
        )

    @pytest.mark.asyncio
    async def test_get_mixed_universe_for_allocation(self, orchestrator, mock_loader):
        """Test mixed universe shortcut method."""
        orchestrator.allocate_from_market_universe = AsyncMock(
            return_value=AllocationResult(
                allocations={},
                pairs=[],
                residual_capital=100000,
                validation_passed=True,
                validation_errors=[],
            )
        )

        await orchestrator.get_mixed_universe_for_allocation(
            total_capital=100000,
            sp500_top=50,
            crypto_top=10,
        )

        orchestrator.allocate_from_market_universe.assert_called_once_with(
            total_capital=100000,
            strategy_allocations=None,
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=True,
            top_n_per_universe=50,  # max(50, 10) = 50
        )


class TestMarketUniverseOrchestratorSingleton:
    """Test singleton pattern for MarketUniverseOrchestrator."""

    def test_singleton(self):
        """Test singleton pattern works correctly."""
        orchestrator1 = get_market_universe_orchestrator()
        orchestrator2 = get_market_universe_orchestrator()

        assert orchestrator1 is orchestrator2

    def test_singleton_returns_orchestrator(self):
        """Test singleton returns MarketUniverseOrchestrator instance."""
        orchestrator = get_market_universe_orchestrator()

        assert isinstance(orchestrator, MarketUniverseOrchestrator)
        assert orchestrator.market_loader is not None
        assert orchestrator.stock_allocator is not None


class TestMarketUniverseOrchestratorIntegration:
    """Integration tests con componentes reales."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with real components."""
        return MarketUniverseOrchestrator()

    def test_initialization_with_real_components(self, orchestrator):
        """Test initialization with real components."""
        assert orchestrator.market_loader is not None
        assert isinstance(orchestrator.market_loader, MarketUniverseLoader)
        assert orchestrator.stock_allocator is not None
        assert isinstance(orchestrator.stock_allocator, StrategyStockAllocator)

    @pytest.mark.asyncio
    async def test_get_universe_for_allocation_with_fallback(self, orchestrator):
        """Test getting universe uses fallback when yfinance unavailable."""
        # Should use fallback lists and return data
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
            top_n_per_universe=5,
        )

        # Should return something even without yfinance
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_full_flow_with_fallback_data(self, orchestrator):
        """Test full allocation flow with fallback data."""
        result = await orchestrator.allocate_from_market_universe(
            total_capital=100000,
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
            top_n_per_universe=5,
            min_avg_volume=1,  # Very low to ensure some pass
            min_price=1.0,
            max_volatility=1.0,  # Very high to ensure some pass
        )

        # Should complete without errors
        assert result is not None
        assert isinstance(result, AllocationResult)


class TestMarketUniverseOrchestratorEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for edge case tests."""
        return MarketUniverseOrchestrator()

    @pytest.mark.asyncio
    async def test_all_markets_disabled(self, orchestrator):
        """Test with all markets disabled."""
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=False,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_top_n_zero(self, orchestrator):
        """Test with top_n=0."""
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            top_n_per_universe=0,
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_allocation_with_zero_capital(self, orchestrator):
        """Test allocation with zero capital."""
        result = await orchestrator.allocate_from_market_universe(
            total_capital=0,
            include_sp500=True,
        )

        # Should still work (though allocation may be empty)
        assert result is not None
        assert isinstance(result, AllocationResult)

    @pytest.mark.asyncio
    async def test_allocation_with_negative_capital(self, orchestrator):
        """Test allocation with negative capital."""
        result = await orchestrator.allocate_from_market_universe(
            total_capital=-1000,
            include_sp500=True,
        )

        # Should handle gracefully
        assert result is not None
        assert isinstance(result, AllocationResult)

    @pytest.mark.asyncio
    async def test_very_strict_filters(self, orchestrator):
        """Test with very strict filters that reject all."""
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            min_avg_volume=999_999_999_999,  # Impossible
            min_price=999999,  # Impossible
            max_volatility=0.0001,  # Almost impossible
        )

        # Should return empty dict
        assert result == {}

    @pytest.mark.asyncio
    async def test_very_permissive_filters(self, orchestrator):
        """Test with very permissive filters."""
        result = await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            min_avg_volume=1,  # Almost anything
            min_price=0.01,  # Almost anything
            max_volatility=2.0,  # Almost anything
        )

        # Should return at least some data
        assert isinstance(result, dict)


class TestMarketUniverseOrchestratorDataFlow:
    """Test data flow through the orchestrator."""

    @pytest.fixture
    def mock_loader(self):
        """Mock loader with test data."""
        loader = MagicMock(spec=MarketUniverseLoader)
        loader.get_combined_universe = AsyncMock(return_value=["TEST1", "TEST2"])
        loader.download_universe_data = AsyncMock(
            return_value={
                "TEST1": pd.DataFrame(
                    {
                        "open": [100] * 25,
                        "high": [101] * 25,
                        "low": [99] * 25,
                        "close": [100] * 25,
                        "volume": [10_000_000] * 25,
                    }
                ),
                "TEST2": pd.DataFrame(
                    {
                        "open": [200] * 25,
                        "high": [201] * 25,
                        "low": [199] * 25,
                        "close": [200] * 25,
                        "volume": [5_000_000] * 25,
                    }
                ),
            }
        )
        loader.filter_by_liquidity_volatility = AsyncMock(
            return_value={
                "TEST1": pd.DataFrame(
                    {
                        "open": [100] * 25,
                        "high": [101] * 25,
                        "low": [99] * 25,
                        "close": [100] * 25,
                        "volume": [10_000_000] * 25,
                    }
                ),
            }
        )
        return loader

    @pytest.fixture
    def orchestrator(self, mock_loader):
        """Create orchestrator with mock loader."""
        return MarketUniverseOrchestrator(market_loader=mock_loader)

    @pytest.mark.asyncio
    async def test_data_flow_download_to_filter(self, orchestrator, mock_loader):
        """Test data flows from download to filter correctly."""
        result = await orchestrator.get_universe_for_allocation(include_sp500=True)

        # Verify download was called
        assert mock_loader.download_universe_data.called

        # Get the data that was downloaded
        download_call = mock_loader.download_universe_data.call_args
        downloaded_data = download_call[1]["tickers"]

        # Verify filter was called with downloaded data
        assert mock_loader.filter_by_liquidity_volatility.called
        filter_call = mock_loader.filter_by_liquidity_volatility.call_args
        filter_call[1]["data"]

        # Verify the flow
        assert len(downloaded_data) == 2  # TEST1, TEST2
        assert len(result) == 1  # Only TEST1 passed filters

    @pytest.mark.asyncio
    async def test_parameters_passed_correctly(self, orchestrator, mock_loader):
        """Test parameters are passed correctly through the flow."""
        await orchestrator.get_universe_for_allocation(
            include_sp500=True,
            include_crypto=True,
            top_n_per_universe=50,
            download_period="12mo",
            download_interval="1h",
            min_avg_volume=5_000_000,
            min_price=10.0,
            max_volatility=0.2,
        )

        # Verify parameters passed to download
        download_call = mock_loader.download_universe_data.call_args
        assert download_call[1]["period"] == "12mo"
        assert download_call[1]["interval"] == "1h"

        # Verify parameters passed to filter
        filter_call = mock_loader.filter_by_liquidity_volatility.call_args
        assert filter_call[1]["min_avg_volume"] == 5_000_000
        assert filter_call[1]["min_price"] == 10.0
        assert filter_call[1]["max_volatility"] == 0.2
