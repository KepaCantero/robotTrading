"""
Tests for app/presentation/dto/responses.py
"""

import pytest
from decimal import Decimal

from app.presentation.dto.responses import (
    PortfolioResponse,
    StrategyResponse,
    HealthResponse,
)


class TestPortfolioResponse:
    """Test PortfolioResponse DTO."""

    def test_valid_response(self):
        """Test creating a valid portfolio response."""
        data = {
            "portfolio_id": "test_portfolio",
            "total_value": Decimal("15000.50"),
            "currency": "USD",
            "positions": [
                {"symbol": "AAPL", "quantity": 10},
                {"symbol": "MSFT", "quantity": 5},
            ],
        }
        response = PortfolioResponse(**data)
        
        assert response.portfolio_id == "test_portfolio"
        assert response.total_value == Decimal("15000.50")
        assert response.currency == "USD"
        assert len(response.positions) == 2

    def test_default_positions(self):
        """Test default positions is empty list."""
        data = {
            "portfolio_id": "test_portfolio",
            "total_value": Decimal("10000.00"),
            "currency": "USD",
        }
        response = PortfolioResponse(**data)
        
        assert response.positions == []

    def test_empty_positions_list(self):
        """Test with explicitly empty positions list."""
        data = {
            "portfolio_id": "test_portfolio",
            "total_value": Decimal("10000.00"),
            "currency": "USD",
            "positions": [],
        }
        response = PortfolioResponse(**data)
        
        assert response.positions == []

    def test_many_positions(self):
        """Test with many positions."""
        positions = [{"symbol": f"STOCK{i}", "quantity": i} for i in range(100)]
        data = {
            "portfolio_id": "test_portfolio",
            "total_value": Decimal("100000.00"),
            "currency": "USD",
            "positions": positions,
        }
        response = PortfolioResponse(**data)
        
        assert len(response.positions) == 100

    def test_json_serialization(self):
        """Test JSON serialization."""
        data = {
            "portfolio_id": "test_portfolio",
            "total_value": Decimal("12345.67"),
            "currency": "USD",
            "positions": [{"symbol": "AAPL", "quantity": 10}],
        }
        response = PortfolioResponse(**data)
        
        json_data = response.model_dump_json()
        assert "test_portfolio" in json_data
        assert "12345.67" in json_data

    def test_missing_portfolio_id_fails(self):
        """Test that missing portfolio_id fails validation."""
        data = {
            "total_value": Decimal("10000.00"),
            "currency": "USD",
        }
        
        with pytest.raises(Exception):
            PortfolioResponse(**data)


class TestStrategyResponse:
    """Test StrategyResponse DTO."""

    def test_valid_response(self):
        """Test creating a valid strategy response."""
        data = {
            "strategy_id": "strategy_123",
            "strategy_type": "momentum",
            "status": "active",
            "signals": [
                {"symbol": "AAPL", "action": "buy"},
                {"symbol": "MSFT", "action": "hold"},
            ],
        }
        response = StrategyResponse(**data)
        
        assert response.strategy_id == "strategy_123"
        assert response.strategy_type == "momentum"
        assert response.status == "active"
        assert len(response.signals) == 2

    def test_default_signals(self):
        """Test default signals is empty list."""
        data = {
            "strategy_id": "strategy_123",
            "strategy_type": "mean_reversion",
            "status": "inactive",
        }
        response = StrategyResponse(**data)
        
        assert response.signals == []

    def test_different_status_values(self):
        """Test with different status values."""
        statuses = ["active", "inactive", "completed", "error"]
        
        for status in statuses:
            data = {
                "strategy_id": "strategy_123",
                "strategy_type": "momentum",
                "status": status,
            }
            response = StrategyResponse(**data)
            assert response.status == status

    def test_json_serialization(self):
        """Test JSON serialization."""
        data = {
            "strategy_id": "strategy_123",
            "strategy_type": "pairs_trading",
            "status": "active",
            "signals": [{"symbol": "EUR/USD", "action": "sell"}],
        }
        response = StrategyResponse(**data)
        
        json_data = response.model_dump_json()
        assert "strategy_123" in json_data
        assert "pairs_trading" in json_data


class TestHealthResponse:
    """Test HealthResponse DTO."""

    def test_valid_response(self):
        """Test creating a valid health response."""
        data = {
            "status": "healthy",
            "version": "1.0.0",
        }
        response = HealthResponse(**data)
        
        assert response.status == "healthy"
        assert response.version == "1.0.0"

    def test_default_version(self):
        """Test default version is 1.0.0."""
        data = {
            "status": "healthy",
        }
        response = HealthResponse(**data)
        
        assert response.version == "1.0.0"

    def test_different_status_values(self):
        """Test with different status values."""
        statuses = ["healthy", "degraded", "unhealthy"]
        
        for status in statuses:
            data = {"status": status}
            response = HealthResponse(**data)
            assert response.status == status

    def test_custom_version(self):
        """Test with custom version."""
        data = {
            "status": "healthy",
            "version": "2.1.3",
        }
        response = HealthResponse(**data)
        
        assert response.version == "2.1.3"

    def test_missing_status_fails(self):
        """Test that missing status fails validation."""
        data = {}
        
        with pytest.raises(Exception):
            HealthResponse(**data)
