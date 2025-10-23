"""
Tests for Logging Middleware
TASK-3: Configuración de logging centralizado
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.middleware.logging_middleware import (
    LoggingMiddleware,
    TradingLoggingMiddleware,
    PortfolioLoggingMiddleware,
    MarketDataLoggingMiddleware,
    log_trading_performance,
    log_portfolio_performance,
    log_market_data_performance,
    log_fastapi_performance
)


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/test-error")
        async def test_error_endpoint():
            raise ValueError("Test error")
        
        app.add_middleware(LoggingMiddleware)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_logging_middleware_success(self, mock_logger, client):
        """Test logging middleware for successful requests."""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Check that logging was called
        assert mock_logger.info.call_count >= 2  # Request and response

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_logging_middleware_error(self, mock_logger, client):
        """Test logging middleware for error requests."""
        with pytest.raises(ValueError):
            client.get("/test-error")
        
        # Check that error logging was called
        assert mock_logger.error.called

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_logging_middleware_metadata(self, mock_logger, client):
        """Test logging middleware metadata."""
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check that info was called with correct metadata
        info_calls = mock_logger.info.call_args_list
        assert len(info_calls) >= 2
        
        # Check request metadata
        request_call = info_calls[0]
        assert "Request started" in request_call[0][1]
        assert "method" in request_call[0][2]["metadata"]
        assert "path" in request_call[0][2]["metadata"]
        assert "client_ip" in request_call[0][2]["metadata"]


class TestTradingLoggingMiddleware:
    """Tests for TradingLoggingMiddleware."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/api/trading/signals")
        async def get_signals():
            return {"signals": []}
        
        @app.post("/api/trading/execute")
        async def execute_trade():
            return {"status": "executed"}
        
        @app.get("/api/other/endpoint")
        async def other_endpoint():
            return {"message": "other"}
        
        app.add_middleware(TradingLoggingMiddleware)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_trading_middleware_trading_endpoints(self, mock_logger, client):
        """Test trading middleware for trading endpoints."""
        response = client.get("/api/trading/signals")
        
        assert response.status_code == 200
        
        # Check that trading logging was called
        assert mock_logger.info.call_count >= 2  # Request and response

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_trading_middleware_non_trading_endpoints(self, mock_logger, client):
        """Test trading middleware for non-trading endpoints."""
        response = client.get("/api/other/endpoint")
        
        assert response.status_code == 200
        
        # Check that no trading logging was called
        assert mock_logger.info.call_count == 0


class TestPortfolioLoggingMiddleware:
    """Tests for PortfolioLoggingMiddleware."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/api/portfolio/positions")
        async def get_positions():
            return {"positions": []}
        
        @app.post("/api/portfolio/update")
        async def update_portfolio():
            return {"status": "updated"}
        
        @app.get("/api/other/endpoint")
        async def other_endpoint():
            return {"message": "other"}
        
        app.add_middleware(PortfolioLoggingMiddleware)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_portfolio_middleware_portfolio_endpoints(self, mock_logger, client):
        """Test portfolio middleware for portfolio endpoints."""
        response = client.get("/api/portfolio/positions")
        
        assert response.status_code == 200
        
        # Check that portfolio logging was called
        assert mock_logger.info.call_count >= 2  # Request and response

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_portfolio_middleware_non_portfolio_endpoints(self, mock_logger, client):
        """Test portfolio middleware for non-portfolio endpoints."""
        response = client.get("/api/other/endpoint")
        
        assert response.status_code == 200
        
        # Check that no portfolio logging was called
        assert mock_logger.info.call_count == 0


class TestMarketDataLoggingMiddleware:
    """Tests for MarketDataLoggingMiddleware."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app for testing."""
        app = FastAPI()
        
        @app.get("/api/market-data/quotes")
        async def get_quotes():
            return {"quotes": []}
        
        @app.post("/api/market-data/subscribe")
        async def subscribe():
            return {"status": "subscribed"}
        
        @app.get("/api/other/endpoint")
        async def other_endpoint():
            return {"message": "other"}
        
        app.add_middleware(MarketDataLoggingMiddleware)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_market_data_middleware_market_data_endpoints(self, mock_logger, client):
        """Test market data middleware for market data endpoints."""
        response = client.get("/api/market-data/quotes")
        
        assert response.status_code == 200
        
        # Check that market data logging was called
        assert mock_logger.info.call_count >= 2  # Request and response

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_market_data_middleware_non_market_data_endpoints(self, mock_logger, client):
        """Test market data middleware for non-market data endpoints."""
        response = client.get("/api/other/endpoint")
        
        assert response.status_code == 200
        
        # Check that no market data logging was called
        assert mock_logger.info.call_count == 0


class TestLoggingDecorators:
    """Tests for logging decorators."""

    def test_log_trading_performance_decorator(self):
        """Test trading performance decorator."""
        @log_trading_performance("test_trading_operation")
        def test_trading_function():
            return "trading_result"
        
        result = test_trading_function()
        assert result == "trading_result"

    def test_log_portfolio_performance_decorator(self):
        """Test portfolio performance decorator."""
        @log_portfolio_performance("test_portfolio_operation")
        def test_portfolio_function():
            return "portfolio_result"
        
        result = test_portfolio_function()
        assert result == "portfolio_result"

    def test_log_market_data_performance_decorator(self):
        """Test market data performance decorator."""
        @log_market_data_performance("test_market_data_operation")
        def test_market_data_function():
            return "market_data_result"
        
        result = test_market_data_function()
        assert result == "market_data_result"

    def test_log_fastapi_performance_decorator(self):
        """Test FastAPI performance decorator."""
        @log_fastapi_performance("test_fastapi_operation")
        def test_fastapi_function():
            return "fastapi_result"
        
        result = test_fastapi_function()
        assert result == "fastapi_result"


class TestMiddlewareIntegration:
    """Integration tests for logging middleware."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with all middleware."""
        app = FastAPI()
        
        @app.get("/api/trading/signals")
        async def get_trading_signals():
            return {"signals": []}
        
        @app.get("/api/portfolio/positions")
        async def get_portfolio_positions():
            return {"positions": []}
        
        @app.get("/api/market-data/quotes")
        async def get_market_data_quotes():
            return {"quotes": []}
        
        @app.get("/api/other/endpoint")
        async def get_other_endpoint():
            return {"message": "other"}
        
        # Add all middleware
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(TradingLoggingMiddleware)
        app.add_middleware(PortfolioLoggingMiddleware)
        app.add_middleware(MarketDataLoggingMiddleware)
        
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_all_middleware_integration(self, mock_logger, client):
        """Test integration of all middleware."""
        # Test trading endpoint
        response = client.get("/api/trading/signals")
        assert response.status_code == 200
        
        # Test portfolio endpoint
        response = client.get("/api/portfolio/positions")
        assert response.status_code == 200
        
        # Test market data endpoint
        response = client.get("/api/market-data/quotes")
        assert response.status_code == 200
        
        # Test other endpoint
        response = client.get("/api/other/endpoint")
        assert response.status_code == 200
        
        # Check that logging was called for all endpoints
        assert mock_logger.info.call_count >= 8  # At least 2 calls per endpoint

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_middleware_request_id_header(self, mock_logger, client):
        """Test that request ID is added to response headers."""
        response = client.get("/api/trading/signals")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None

    @patch('app.middleware.logging_middleware.centralized_logger')
    def test_middleware_duration_logging(self, mock_logger, client):
        """Test that duration is logged."""
        response = client.get("/api/trading/signals")
        
        assert response.status_code == 200
        
        # Check that duration was logged
        info_calls = mock_logger.info.call_args_list
        duration_logged = any(
            "duration_ms" in call[0][2]["metadata"] 
            for call in info_calls
        )
        assert duration_logged
