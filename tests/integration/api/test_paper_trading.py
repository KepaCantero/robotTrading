"""
Paper Trading API Endpoints Test Suite

Tests for paper trading API endpoints.

Reference: API-004 - Test coverage for API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.paper_trading import router
from app.models.paper_trading import (
    OrderSide,
    OrderType,
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    PaperTradingConfig,
    PaperTradingSession,
    TradeStatus,
)


class TestPaperTradingAPIEndpoints:
    """Test paper trading API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_portfolio_id(self):
        """Create mock portfolio ID."""
        return uuid4()

    @pytest.fixture
    def mock_session_id(self):
        """Create mock session ID."""
        return uuid4()

    @pytest.fixture
    def mock_portfolio(self, mock_portfolio_id):
        """Create mock portfolio."""
        return PaperPortfolio(
            id=mock_portfolio_id,
            name="Test Portfolio",
            cash_balance=Decimal("100000.00"),
            total_equity=Decimal("100000.00"),
            total_pnl=Decimal("0.00"),
            total_return=Decimal("0.00"),
            daily_pnl=Decimal("0.00"),
            daily_return=Decimal("0.00"),
            positions=[],
            currency="USD",
            created_at=datetime.utcnow(),
        )

    @pytest.fixture
    def mock_session(self, mock_session_id, mock_portfolio_id):
        """Create mock session."""
        return PaperTradingSession(
            id=mock_session_id,
            portfolio_id=mock_portfolio_id,
            name="Test Session",
            description="Test session description",
            is_active=True,
            start_time=datetime.utcnow(),
            end_time=None,
            initial_cash=Decimal("100000.00"),
            current_cash=Decimal("100000.00"),
            total_pnl=Decimal("0.00"),
            trades_count=0,
            currency="USD",
        )

    @pytest.fixture
    def mock_trade(self):
        """Create mock trade."""
        return PaperTrade(
            id=uuid4(),
            portfolio_id=uuid4(),
            session_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            status=TradeStatus.FILLED,
            filled_quantity=Decimal("100"),
            filled_price=Decimal("150.00"),
            commission=Decimal("1.00"),
            created_at=datetime.utcnow(),
            filled_at=datetime.utcnow(),
        )

    @pytest.mark.asyncio
    async def test_create_portfolio_success(self, client):
        """Test create_portfolio creates a new portfolio."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_portfolio.return_value = MagicMock(
                id=uuid4(),
                name="Test Portfolio",
                cash_balance=Decimal("100000.00"),
            )
            mock_get_service.return_value = mock_service

            response = client.post(
                "/paper-trading/portfolios",
                json={"name": "Test Portfolio", "initial_cash": "100000.00"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["portfolio"]["name"] == "Test Portfolio"

    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, client, mock_portfolio):
        """Test get_portfolio returns portfolio data."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_portfolio.return_value = mock_portfolio
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{mock_portfolio.id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["portfolio"]["name"] == "Test Portfolio"

    @pytest.mark.asyncio
    async def test_get_portfolio_not_found(self, client):
        """Test get_portfolio returns 404 for non-existent portfolio."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_portfolio.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_portfolios_success(self, client, mock_portfolio):
        """Test list_portfolios returns all portfolios."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.portfolios = {mock_portfolio.id: mock_portfolio}
            mock_get_service.return_value = mock_service

            response = client.get("/paper-trading/portfolios")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_create_session_success(self, client, mock_session, mock_portfolio_id):
        """Test create_session creates a new session."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_session.return_value = mock_session
            mock_get_service.return_value = mock_service

            response = client.post(
                "/paper-trading/sessions",
                json={
                    "portfolio_id": str(mock_portfolio_id),
                    "name": "Test Session",
                    "description": "Test session description",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["session"]["name"] == "Test Session"

    @pytest.mark.asyncio
    async def test_get_session_success(self, client, mock_session):
        """Test get_session returns session data."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = mock_session
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/sessions/{mock_session.id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["session"]["name"] == "Test Session"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client):
        """Test get_session returns 404 for non-existent session."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_session.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/sessions/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_close_session_success(self, client, mock_session):
        """Test close_session closes a session."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.close_session.return_value = mock_session
            mock_get_service.return_value = mock_service

            response = client.post(f"/paper-trading/sessions/{mock_session.id}/close")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_sessions_success(self, client, mock_session, mock_portfolio_id):
        """Test list_sessions returns sessions with filters."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.sessions = {mock_session.id: mock_session}
            mock_get_service.return_value = mock_service

            response = client.get(
                f"/paper-trading/sessions?portfolio_id={mock_portfolio_id}&is_active=true"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_execute_trade_success(self, client, mock_trade, mock_portfolio_id):
        """Test execute_trade executes a trade successfully."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.execute_trade.return_value = mock_trade
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/paper-trading/portfolios/{mock_portfolio_id}/trades",
                json={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "100",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["trade"]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_execute_trade_with_limit_order(self, client, mock_trade, mock_portfolio_id):
        """Test execute_trade executes a limit order."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.execute_trade.return_value = mock_trade
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/paper-trading/portfolios/{mock_portfolio_id}/trades",
                json={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "LIMIT",
                    "quantity": "100",
                    "price": "149.50",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_trades_success(self, client, mock_trade, mock_portfolio_id):
        """Test get_trades returns trades for a portfolio."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_trades.return_value = [mock_trade]
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{mock_portfolio_id}/trades")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_get_trades_with_filters(self, client, mock_trade, mock_portfolio_id):
        """Test get_trades filters by symbol and status."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_trades.return_value = [mock_trade]
            mock_get_service.return_value = mock_service

            response = client.get(
                f"/paper-trading/portfolios/{mock_portfolio_id}/trades?symbol=AAPL&status=FILLED&limit=50"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_trade_success(self, client, mock_trade):
        """Test get_trade returns trade by ID."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.trades = {mock_trade.id: mock_trade}
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/trades/{mock_trade.id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["trade"]["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_trade_not_found(self, client):
        """Test get_trade returns 404 for non-existent trade."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.trades = {}
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/trades/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_positions_success(self, client, mock_portfolio_id):
        """Test get_positions returns all positions for a portfolio."""
        mock_position = PaperPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            realized_pnl=Decimal("0.00"),
            currency="USD",
        )

        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_positions.return_value = [mock_position]
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{mock_portfolio_id}/positions")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_get_position_by_symbol(self, client, mock_portfolio_id):
        """Test get_position returns position for specific symbol."""
        mock_position = PaperPosition(
            symbol="AAPL",
            quantity=Decimal("100"),
            avg_price=Decimal("150.00"),
            market_price=Decimal("155.00"),
            unrealized_pnl=Decimal("500.00"),
            realized_pnl=Decimal("0.00"),
            currency="USD",
        )

        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_positions.return_value = [mock_position]
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{mock_portfolio_id}/positions/AAPL")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_update_market_prices_success(self, client):
        """Test update_market_prices updates prices for symbols."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_market_prices.return_value = None
            mock_get_service.return_value = mock_service

            response = client.post(
                "/paper-trading/market/update",
                json={
                    "quotes": {
                        "AAPL": {
                            "symbol": "AAPL",
                            "price": "150.25",
                            "bid": "150.20",
                            "ask": "150.30",
                            "volume": 1000000,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    }
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_list_configs_success(self, client):
        """Test list_configs returns all configurations."""
        mock_config = PaperTradingConfig(
            id=uuid4(),
            name="Default Config",
            commission_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.0001"),
            initial_cash=Decimal("100000.00"),
            currency="USD",
        )

        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.configs = {mock_config.id: mock_config}
            mock_get_service.return_value = mock_service

            response = client.get("/paper-trading/configs")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_config_success(self, client):
        """Test get_config returns configuration by ID."""
        mock_config = PaperTradingConfig(
            id=uuid4(),
            name="Default Config",
            commission_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.0001"),
            initial_cash=Decimal("100000.00"),
            currency="USD",
        )

        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.configs = {mock_config.id: mock_config}
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/configs/{mock_config.id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == "Default Config"

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, client):
        """Test get_config returns 404 for non-existent config."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.configs = {}
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/configs/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_portfolio_stats_success(self, client, mock_portfolio):
        """Test get_portfolio_stats returns portfolio statistics."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_portfolio.return_value = mock_portfolio
            mock_service.get_trades.return_value = []
            mock_service.get_positions.return_value = []
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{mock_portfolio.id}/stats")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "portfolio" in data
            assert "trades" in data
            assert "positions" in data

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health_check returns healthy status."""
        response = client.get("/paper-trading/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "paper-trading"


class TestErrorHandling:
    """Test error handling in paper trading API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_execute_trade_timeout(self, client):
        """Test execute_trade handles timeout errors."""
        import asyncio

        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.execute_trade.side_effect = asyncio.TimeoutError()
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/paper-trading/portfolios/{uuid4()}/trades",
                json={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "100",
                },
            )
            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    @pytest.mark.asyncio
    async def test_execute_trade_validation_error(self, client):
        """Test execute_trade handles validation errors."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.execute_trade.side_effect = ValueError("Invalid quantity")
            mock_get_service.return_value = mock_service

            response = client.post(
                f"/paper-trading/portfolios/{uuid4()}/trades",
                json={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": "0",  # Invalid: quantity must be > 0
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_get_portfolio_stats_not_found(self, client):
        """Test get_portfolio_stats returns 404 for non-existent portfolio."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_portfolio.return_value = None
            mock_get_service.return_value = mock_service

            response = client.get(f"/paper-trading/portfolios/{uuid4()}/stats")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_portfolio_validation_error(self, client):
        """Test create_portfolio handles validation errors."""
        with patch("app.api.paper_trading.get_paper_trading_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_portfolio.side_effect = ValueError("Invalid initial cash")
            mock_get_service.return_value = mock_service

            response = client.post(
                "/paper-trading/portfolios",
                json={"name": "Test Portfolio", "initial_cash": "-1000.00"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
