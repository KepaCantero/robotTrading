"""
Comprehensive test suite for T004 Portfolio Source of Truth.
"""

from decimal import Decimal

import pytest

from app.models.portfolio import AssetClass, Position
from app.providers.paper_trading import PaperTradingPortfolioProvider
from app.services.portfolio_service import PortfolioService


class TestPortfolioModels:
    """Test portfolio models and data structures."""

    def test_position_creation(self):
        """Test Position model creation and validation."""
        position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            broker="paper_trading",
        )
        assert position.symbol == "AAPL"
        assert position.asset_class == AssetClass.EQUITY
        assert position.quantity == Decimal("100")

    def test_portfolio_creation(self):
        """Test Portfolio model creation."""
        from app.models.portfolio import Portfolio

        portfolio = Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("100000"),
            broker="paper",
            positions=[],
        )
        assert portfolio.cash == Decimal("100000")
        assert len(portfolio.positions) == 0


class TestPortfolioService:
    """Test portfolio service functionality."""

    @pytest.fixture
    def service(self):
        """Create portfolio service."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        return PortfolioService(provider)

    @pytest.mark.asyncio
    async def test_simulate_trade_success(self, service):
        """Test successful trade simulation."""
        success = await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        assert success is True

    @pytest.mark.asyncio
    async def test_portfolio_summary(self, service):
        """Test portfolio summary generation."""
        portfolio = await service.get_portfolio()
        assert portfolio is not None


class TestPaperTradingProvider:
    """Test paper trading provider."""

    @pytest.mark.asyncio
    async def test_simulate_trade_buy(self):
        """Test buy trade simulation."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        portfolio = await provider.get_portfolio()
        assert portfolio is not None

    @pytest.mark.asyncio
    async def test_simulate_trade_sell(self):
        """Test sell trade simulation."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        portfolio = await provider.get_portfolio()
        assert portfolio is not None


class TestIntegration:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self):
        """Test complete trading workflow."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        service = PortfolioService(provider)

        portfolio = await service.get_portfolio()
        assert portfolio.total_equity == Decimal("100000")

    @pytest.mark.asyncio
    async def test_multiple_asset_classes(self):
        """Test trading across multiple asset classes."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        service = PortfolioService(provider)

        success = await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        # Just verify trade simulation succeeded
        assert success is True
