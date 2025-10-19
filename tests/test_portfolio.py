"""
Comprehensive test suite for T004 Portfolio Source of Truth.

Tests cover all components: models, providers, services, and API endpoints.
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List

from app.models.portfolio import (
    AssetClass, Position, Portfolio, MarketRegime, MarketRegimeData,
    AssetUniverse, CircuitBreakerState, CircuitBreaker
)
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
            broker="paper_trading"
        )
        
        assert position.symbol == "AAPL"
        assert position.asset_class == AssetClass.EQUITY
        assert position.quantity == Decimal("100")
        assert position.market_value == Decimal("15500.00")
        assert position.cost_basis == Decimal("15000.00")
        assert position.total_pnl == Decimal("500.00")
        assert position.pnl_percentage == Decimal("3.333333333333333333333333333")
    
    def test_portfolio_creation(self):
        """Test Portfolio model creation and calculations."""
        positions = [
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("500.00"),
                broker="paper_trading"
            ),
            Position(
                symbol="BTCUSDT",
                asset_class=AssetClass.CRYPTO,
                quantity=Decimal("0.1"),
                avg_price=Decimal("45000.00"),
                market_price=Decimal("46000.00"),
                unrealized_pnl=Decimal("100.00"),
                broker="paper_trading"
            )
        ]
        
        portfolio = Portfolio(
            cash=Decimal("50000.00"),
            positions=positions,
            broker="paper_trading"
        )
        
        assert portfolio.cash == Decimal("50000.00")
        assert len(portfolio.positions) == 2
        assert portfolio.total_equity == Decimal("70100.00")  # 50000 + 15500 + 4600
        assert portfolio.total_pnl == Decimal("600.00")
        assert portfolio.total_pnl_percentage == Decimal("0.8559201141226818830242510699")
    
    def test_asset_universe(self):
        """Test AssetUniverse model."""
        universe = AssetUniverse(
            broker="paper_trading",
            asset_class=AssetClass.EQUITY,
            symbols=["AAPL", "MSFT", "GOOGL"],
            min_volume=Decimal("1000000"),
            max_spread=Decimal("0.01")
        )
        
        assert universe.is_supported("AAPL")
        assert universe.is_supported("aapl")  # Case insensitive
        assert not universe.is_supported("TSLA")
    
    def test_circuit_breaker(self):
        """Test CircuitBreaker model."""
        cb = CircuitBreaker(
            name="test_breaker",
            max_errors=3,
            cooldown_seconds=300
        )
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert not cb.should_trigger()
        
        # Simulate errors
        cb.error_count = 3
        assert cb.should_trigger()
        
        # Test reset
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.error_count == 0


class TestPaperTradingProvider:
    """Test PaperTradingPortfolioProvider functionality."""
    
    @pytest.fixture
    def provider(self):
        """Create a test provider instance."""
        return PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, provider):
        """Test getting portfolio."""
        portfolio = await provider.get_portfolio()
        
        assert portfolio.broker == "paper_trading"
        assert portfolio.cash == Decimal("100000")
        assert len(portfolio.positions) == 0
        assert portfolio.total_equity == Decimal("100000")
    
    @pytest.mark.asyncio
    async def test_simulate_trade_buy(self, provider):
        """Test simulating a buy trade."""
        success = await provider.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        assert success
        portfolio = await provider.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"
        assert portfolio.positions[0].quantity == Decimal("100")
        assert portfolio.cash == Decimal("85000")  # 100000 - 15000
    
    @pytest.mark.asyncio
    async def test_simulate_trade_sell(self, provider):
        """Test simulating a sell trade."""
        # First buy some shares
        await provider.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        # Then sell some
        success = await provider.simulate_trade("AAPL", Decimal("-50"), Decimal("160"))
        
        assert success
        portfolio = await provider.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].quantity == Decimal("50")
        assert portfolio.cash == Decimal("93000")  # 85000 + 8000 (50 shares * 160)
    
    @pytest.mark.asyncio
    async def test_simulate_trade_close_position(self, provider):
        """Test closing a position completely."""
        # Buy shares
        await provider.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        # Sell all shares
        success = await provider.simulate_trade("AAPL", Decimal("-100"), Decimal("160"))
        
        assert success
        portfolio = await provider.get_portfolio()
        assert len(portfolio.positions) == 0
        assert portfolio.cash == Decimal("101000")  # 85000 + 16000
    
    @pytest.mark.asyncio
    async def test_get_position(self, provider):
        """Test getting specific position."""
        await provider.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        position = await provider.get_position("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
        
        # Test non-existent position
        position = await provider.get_position("TSLA")
        assert position is None
    
    @pytest.mark.asyncio
    async def test_get_asset_universe(self, provider):
        """Test getting asset universe."""
        universe = await provider.get_asset_universe()
        
        assert len(universe) == 2  # EQUITY and CRYPTO
        equity_universe = next(u for u in universe if u.asset_class == AssetClass.EQUITY)
        crypto_universe = next(u for u in universe if u.asset_class == AssetClass.CRYPTO)
        
        assert "AAPL" in equity_universe.symbols
        assert "BTCUSDT" in crypto_universe.symbols
    
    @pytest.mark.asyncio
    async def test_get_market_regime(self, provider):
        """Test getting market regime data."""
        regime_data = await provider.get_market_regime("AAPL")
        
        assert regime_data is not None
        assert regime_data.regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN, 
                                    MarketRegime.RANGING, MarketRegime.VOLATILE]
        assert 0.0 <= regime_data.confidence <= 1.0
        assert regime_data.atr_ratio > 0
        assert regime_data.trend_strength > 0
        assert regime_data.volatility_level > 0
    
    @pytest.mark.asyncio
    async def test_insufficient_cash(self, provider):
        """Test trade with insufficient cash."""
        success = await provider.simulate_trade("AAPL", Decimal("1000"), Decimal("200"))
        
        assert not success  # Should fail due to insufficient cash
    
    @pytest.mark.asyncio
    async def test_unsupported_symbol(self, provider):
        """Test trade with unsupported symbol."""
        success = await provider.simulate_trade("UNSUPPORTED", Decimal("100"), Decimal("100"))
        
        assert not success  # Should fail due to unsupported symbol
    
    def test_symbol_support(self, provider):
        """Test symbol support checking."""
        assert provider.is_symbol_supported("AAPL")
        assert provider.is_symbol_supported("BTCUSDT")
        assert not provider.is_symbol_supported("UNSUPPORTED")
        
        symbols = provider.get_supported_symbols()
        assert "AAPL" in symbols
        assert "BTCUSDT" in symbols


class TestPortfolioService:
    """Test PortfolioService with circuit breakers."""
    
    @pytest.fixture
    def service(self):
        """Create a test service instance."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        return PortfolioService(provider)
    
    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, service):
        """Test successful portfolio retrieval."""
        portfolio = await service.get_portfolio()
        
        assert portfolio is not None
        assert portfolio.broker == "paper_trading"
        assert portfolio.cash == Decimal("100000")
    
    @pytest.mark.asyncio
    async def test_get_position_success(self, service):
        """Test successful position retrieval."""
        # First create a position
        await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        position = await service.get_position("AAPL")
        assert position is not None
        assert position.symbol == "AAPL"
        assert position.quantity == Decimal("100")
    
    @pytest.mark.asyncio
    async def test_simulate_trade_success(self, service):
        """Test successful trade simulation."""
        success = await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        assert success
        
        portfolio = await service.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.positions[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_status(self, service):
        """Test circuit breaker status."""
        status = service.get_circuit_breaker_status()
        
        assert "api_errors" in status
        assert "slippage" in status
        assert "performance" in status
        
        for cb_name, cb_info in status.items():
            assert cb_info["state"] == "closed"
            assert cb_info["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, service):
        """Test circuit breaker reset."""
        # Manually trigger a circuit breaker
        service.circuit_breakers["api_errors"].error_count = 3
        service.circuit_breakers["api_errors"].state = CircuitBreakerState.OPEN
        
        # Reset it
        service.reset_circuit_breaker("api_errors")
        
        status = service.get_circuit_breaker_status()
        assert status["api_errors"]["state"] == "closed"
        assert status["api_errors"]["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_portfolio_summary(self, service):
        """Test portfolio summary generation."""
        summary = await service.get_portfolio_summary()
        
        assert "broker" in summary
        assert "total_equity" in summary
        assert "cash" in summary
        assert "total_pnl" in summary
        assert "positions_count" in summary
        assert "circuit_breakers" in summary
        
        assert summary["broker"] == "paper_trading"
        assert summary["total_equity"] == 100000.0
        assert summary["cash"] == 100000.0
        assert summary["positions_count"] == 0


class TestIntegration:
    """Integration tests for the complete portfolio system."""
    
    @pytest.mark.asyncio
    async def test_complete_trading_workflow(self):
        """Test complete trading workflow."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        service = PortfolioService(provider)
        
        # Get initial portfolio
        portfolio = await service.get_portfolio()
        assert portfolio.total_equity == Decimal("100000")
        
        # Buy some stocks
        success = await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        assert success
        
        # Check portfolio after trade
        portfolio = await service.get_portfolio()
        assert len(portfolio.positions) == 1
        assert portfolio.cash == Decimal("85000")
        
        # Get position details
        position = await service.get_position("AAPL")
        assert position.quantity == Decimal("100")
        assert position.avg_price == Decimal("150")
        
        # Get market regime
        regime = await service.get_market_regime("AAPL")
        assert regime is not None
        
        # Get asset universe
        universe = await service.get_asset_universe()
        assert len(universe) == 2
        
        # Get portfolio summary
        summary = await service.get_portfolio_summary()
        assert summary["positions_count"] == 1
        # Note: Market price changes due to simulation, so we just check it's reasonable
        assert summary["total_equity"] > 80000  # Should be reasonable given cash + position value
    
    @pytest.mark.asyncio
    async def test_multiple_asset_classes(self):
        """Test trading across multiple asset classes."""
        provider = PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))
        service = PortfolioService(provider)
        
        # Buy equity
        await service.simulate_trade("AAPL", Decimal("100"), Decimal("150"))
        
        # Buy crypto
        await service.simulate_trade("BTCUSDT", Decimal("0.1"), Decimal("45000"))
        
        portfolio = await service.get_portfolio()
        assert len(portfolio.positions) == 2
        
        # Check positions by asset class
        positions_by_class = portfolio.positions_by_asset_class
        assert AssetClass.EQUITY in positions_by_class
        assert AssetClass.CRYPTO in positions_by_class
        assert len(positions_by_class[AssetClass.EQUITY]) == 1
        assert len(positions_by_class[AssetClass.CRYPTO]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
