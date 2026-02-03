"""
Tests for app/presentation/dto/requests.py
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.presentation.dto.requests import (
    CreatePortfolioRequest,
    ExecuteStrategyRequest,
)


class TestCreatePortfolioRequest:
    """Test CreatePortfolioRequest DTO."""

    def test_valid_request(self):
        """Test creating a valid portfolio request."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("10000.00"),
            "currency": "USD",
        }
        request = CreatePortfolioRequest(**data)
        
        assert request.portfolio_id == "test_portfolio"
        assert request.initial_capital == Decimal("10000.00")
        assert request.currency == "USD"

    def test_default_currency(self):
        """Test default currency is USD."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("5000.00"),
        }
        request = CreatePortfolioRequest(**data)
        
        assert request.currency == "USD"

    def test_zero_capital_fails(self):
        """Test that zero capital fails validation."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("0"),
        }
        
        with pytest.raises(ValidationError):
            CreatePortfolioRequest(**data)

    def test_negative_capital_fails(self):
        """Test that negative capital fails validation."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("-1000.00"),
        }
        
        with pytest.raises(ValidationError):
            CreatePortfolioRequest(**data)

    def test_missing_portfolio_id_fails(self):
        """Test that missing portfolio_id fails validation."""
        data = {
            "initial_capital": Decimal("10000.00"),
        }
        
        with pytest.raises(ValidationError):
            CreatePortfolioRequest(**data)

    def test_missing_initial_capital_fails(self):
        """Test that missing initial_capital fails validation."""
        data = {
            "portfolio_id": "test_portfolio",
        }
        
        with pytest.raises(ValidationError):
            CreatePortfolioRequest(**data)

    def test_very_large_capital(self):
        """Test with very large capital amount."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("999999999999.99"),
        }
        request = CreatePortfolioRequest(**data)
        
        assert request.initial_capital == Decimal("999999999999.99")

    def test_small_capital(self):
        """Test with small capital amount."""
        data = {
            "portfolio_id": "test_portfolio",
            "initial_capital": Decimal("0.01"),
        }
        request = CreatePortfolioRequest(**data)
        
        assert request.initial_capital == Decimal("0.01")


class TestExecuteStrategyRequest:
    """Test ExecuteStrategyRequest DTO."""

    def test_valid_request(self):
        """Test creating a valid strategy request."""
        data = {
            "strategy_type": "momentum",
            "symbol": "AAPL",
            "parameters": {"period": 20, "threshold": 0.5},
        }
        request = ExecuteStrategyRequest(**data)
        
        assert request.strategy_type == "momentum"
        assert request.symbol == "AAPL"
        assert request.parameters == {"period": 20, "threshold": 0.5}

    def test_default_parameters(self):
        """Test default parameters is empty dict."""
        data = {
            "strategy_type": "mean_reversion",
            "symbol": "BTC-USD",
        }
        request = ExecuteStrategyRequest(**data)
        
        assert request.parameters == {}

    def test_missing_strategy_type_fails(self):
        """Test that missing strategy_type fails validation."""
        data = {
            "symbol": "AAPL",
        }
        
        with pytest.raises(ValidationError):
            ExecuteStrategyRequest(**data)

    def test_missing_symbol_fails(self):
        """Test that missing symbol fails validation."""
        data = {
            "strategy_type": "momentum",
        }
        
        with pytest.raises(ValidationError):
            ExecuteStrategyRequest(**data)

    def test_empty_parameters(self):
        """Test with empty parameters dict."""
        data = {
            "strategy_type": "pairs_trading",
            "symbol": "EUR/USD",
            "parameters": {},
        }
        request = ExecuteStrategyRequest(**data)
        
        assert request.parameters == {}
