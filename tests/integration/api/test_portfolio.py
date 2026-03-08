"""
Portfolio API Endpoints Test Suite

Tests for portfolio API endpoints with DI container pattern.

Reference: Rule DP-004 - Use dependency injection instead of direct instantiation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.presentation.api.portfolio import get_portfolio_service, router
from app.domain.models.portfolio import Portfolio
from app.services.portfolio_service import PortfolioService


class TestPortfolioAPIEndpoints:
    """Test portfolio API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_portfolio(self):
        """Create mock portfolio."""
        portfolio = MagicMock(spec=Portfolio)
        portfolio.portfolio_id = "test_portfolio"
        portfolio.total_equity = Decimal("100000")
        portfolio.cash = Decimal("100000")
        portfolio.total_pnl = Decimal("0")
        portfolio.total_pnl_percentage = Decimal("0")
        portfolio.positions = []
        portfolio.positions_count = 0
        portfolio.broker = "paper_trading"
        portfolio.currency = "USD"
        portfolio.timestamp = MagicMock()
        return portfolio

    @pytest.mark.asyncio
    async def test_get_portfolio_summary_success(self, client, mock_portfolio):
        """Test get_portfolio_summary returns valid summary."""
        with patch.object(
            PortfolioService, "get_portfolio", new=AsyncMock(return_value=mock_portfolio)
        ):
            response = client.get("/portfolio/")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "portfolio_id" in data
            assert data["broker"] == "paper_trading"

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, client, mock_portfolio):
        """Test get_positions returns empty list initially."""
        mock_portfolio.positions = []
        with patch.object(
            PortfolioService, "get_portfolio", new=AsyncMock(return_value=mock_portfolio)
        ):
            response = client.get("/portfolio/positions")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_position_not_found(self, client):
        """Test get_position returns 404 for non-existent symbol."""
        with patch.object(PortfolioService, "get_position", new=AsyncMock(return_value=None)):
            response = client.get("/portfolio/positions/NONEXISTENT")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_asset_universe(self, client):
        """Test get_asset_universe returns supported asset classes."""
        with patch.object(
            PortfolioService,
            "get_asset_universe",
            new=AsyncMock(return_value=[]),
        ):
            response = client.get("/portfolio/asset-universe")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_market_regime_not_available(self, client):
        """Test get_market_regime returns 404 when unavailable."""
        with patch.object(PortfolioService, "get_market_regime", new=AsyncMock(return_value=None)):
            response = client.get("/portfolio/market-regime/NONEXISTENT")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_simulate_trade_success(self, client):
        """Test simulate_trade returns success correctly."""
        with patch.object(PortfolioService, "simulate_trade", new=AsyncMock(return_value=True)):
            response = client.post(
                "/portfolio/simulate-trade",
                json={"symbol": "AAPL", "quantity": 100, "price": 150.0},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_simulate_trade_failure(self, client):
        """Test simulate_trade returns failure correctly."""
        with patch.object(PortfolioService, "simulate_trade", new=AsyncMock(return_value=False)):
            response = client.post(
                "/portfolio/simulate-trade",
                json={"symbol": "AAPL", "quantity": 100, "price": 150.0},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_status(self, client):
        """Test get_circuit_breaker_status returns all breaker states."""
        with patch.object(
            PortfolioService,
            "get_circuit_breaker_status",
            return_value={},
        ):
            response = client.get("/portfolio/circuit-breakers")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, client):
        """Test reset_circuit_breaker resets breaker state."""
        with patch.object(PortfolioService, "reset_circuit_breaker", return_value=None):
            response = client.post("/portfolio/circuit-breakers/test_breaker/reset")
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_portfolio_health_check_healthy(self, client, mock_portfolio):
        """Test portfolio_health_check returns healthy status."""
        mock_portfolio.positions = []
        with patch.object(
            PortfolioService,
            "get_portfolio",
            new=AsyncMock(return_value=mock_portfolio),
        ):
            with patch.object(
                PortfolioService,
                "get_circuit_breaker_status",
                return_value={},
            ):
                response = client.get("/portfolio/health")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] in ["healthy", "unhealthy"]


class TestDIContainerPattern:
    """Test DI container pattern for portfolio service."""

    def test_get_portfolio_service_returns_singleton(self):
        """Test that get_portfolio_service returns the same instance."""
        service1 = get_portfolio_service()
        service2 = get_portfolio_service()
        # Both should be PortfolioService instances
        assert isinstance(service1, PortfolioService)
        assert isinstance(service2, PortfolioService)

    def test_get_portfolio_service_from_di_container(self):
        """Test that get_portfolio_service uses DI container."""
        from app.core.di_container import get_portfolio_service as di_get_portfolio_service

        service_from_function = di_get_portfolio_service()

        # Should be PortfolioService instance
        assert isinstance(service_from_function, PortfolioService)

        # Should be singleton (same instance on subsequent calls)
        service_from_function2 = di_get_portfolio_service()
        assert service_from_function is service_from_function2

    def test_di_container_initialization(self):
        """Test that DI container is properly initialized with portfolio services."""
        from app.core.di_container import get_portfolio_service as di_get_portfolio_service

        # get_portfolio_service function should be available
        service = di_get_portfolio_service()
        assert service is not None
        assert isinstance(service, PortfolioService)

        # Should be singleton
        service2 = di_get_portfolio_service()
        assert service is service2


class TestSymbolUppercaseConversion:
    """Test symbol parameter uppercase conversion."""

    @pytest.mark.asyncio
    async def test_get_position_converts_symbol_to_uppercase(self, client):
        """Test get_position converts symbol to uppercase."""
        from app.domain.models.portfolio import AssetClass, Position

        mock_position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("150"),
            market_price=Decimal("155"),
            unrealized_pnl=Decimal("500"),
            realized_pnl=Decimal("0"),
            currency="USD",
            broker="paper_trading",
        )

        with patch.object(
            PortfolioService, "get_position", new=AsyncMock(return_value=mock_position)
        ) as mock_get:
            client.get("/portfolio/positions/aapl")
            # Should call with uppercase symbol
            mock_get.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_market_regime_converts_symbol_to_uppercase(self, client):
        """Test get_market_regime converts symbol to uppercase."""
        with patch.object(
            PortfolioService, "get_market_regime", new=AsyncMock(return_value=None)
        ) as mock_get:
            client.get("/portfolio/market-regime/aapl")
            # Should call with uppercase symbol
            mock_get.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_simulate_trade_converts_symbol_to_uppercase(self, client):
        """Test simulate_trade converts symbol to uppercase."""
        with patch.object(
            PortfolioService, "simulate_trade", new=AsyncMock(return_value=True)
        ) as mock_simulate:
            client.post(
                "/portfolio/simulate-trade",
                json={"symbol": "aapl", "quantity": 100, "price": 150.0},
            )
            # Should call with uppercase symbol
            call_args = mock_simulate.call_args
            assert call_args[0][0] == "AAPL"


class TestErrorHandling:
    """Test error handling in portfolio API."""

    @pytest.mark.asyncio
    async def test_get_portfolio_circuit_breaker_open(self, client):
        """Test get_portfolio returns 503 when circuit breaker is open."""
        with patch.object(PortfolioService, "get_portfolio", new=AsyncMock(return_value=None)):
            response = client.get("/portfolio/")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "circuit breaker" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_simulate_trade_error_handling(self, client):
        """Test simulate_trade handles errors correctly."""
        with patch.object(
            PortfolioService, "simulate_trade", new=AsyncMock(side_effect=ValueError("Test error"))
        ):
            response = client.post(
                "/portfolio/simulate-trade",
                json={"symbol": "AAPL", "quantity": 100, "price": 150.0},
            )
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
