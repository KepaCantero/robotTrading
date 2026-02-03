"""
Unit tests for portfolio_optimizer.py
======================================

Tests for portfolio compliance optimizer.
"""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from app.core.compliance.portfolio_optimizer import PortfolioComplianceOptimizer
from app.core.compliance.results import OptimizeResult


@pytest.fixture
def sample_returns():
    """Create sample returns DataFrame."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    import numpy as np
    np.random.seed(42)
    data = np.random.randn(100, 3) * 0.02  # 2% daily volatility
    
    return pd.DataFrame(data, index=dates, columns=symbols)


@pytest.fixture
def sample_prices():
    """Create sample current prices."""
    return {
        "AAPL": Decimal("180.00"),
        "MSFT": Decimal("400.00"),
        "GOOGL": Decimal("140.00"),
    }


@pytest.fixture
def sample_price_histories():
    """Create sample price histories."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    
    histories = {}
    for symbol, base_price in [("AAPL", 180), ("MSFT", 400), ("GOOGL", 140)]:
        prices = [base_price + i * 0.5 for i in range(100)]
        histories[symbol] = pd.DataFrame({
            "close": prices,
            "volume": [1000000] * 100,
        }, index=dates)
    
    return histories


@pytest.fixture
def optimizer():
    """Create PortfolioComplianceOptimizer instance."""
    return PortfolioComplianceOptimizer()


class TestPortfolioComplianceOptimizer:
    """Tests for PortfolioComplianceOptimizer class."""

    def test_init(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer._registry is not None
        assert isinstance(optimizer._cache, dict)

    def test_optimize_portfolio_basic(self, optimizer, sample_returns, sample_prices):
        """Test basic portfolio optimization."""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        result = optimizer.optimize_portfolio(
            symbols=symbols,
            returns=sample_returns,
            current_prices=sample_prices,
        )
        
        assert isinstance(result, OptimizeResult)
        assert isinstance(result.weights, dict)
        assert len(result.weights) > 0

    def test_optimize_portfolio_with_histories(self, optimizer, sample_returns, sample_prices, sample_price_histories):
        """Test optimization with price histories."""
        result = optimizer.optimize_portfolio(
            symbols=["AAPL", "MSFT", "GOOGL"],
            returns=sample_returns,
            current_prices=sample_prices,
            price_histories=sample_price_histories,
        )
        
        assert isinstance(result, OptimizeResult)
        # Regime should be detected if price histories provided

    def test_optimize_portfolio_with_constraints(self, optimizer, sample_returns, sample_prices):
        """Test optimization with constraints."""
        constraints = {
            "max_weight": 0.5,
            "min_weight": 0.1,
        }
        
        result = optimizer.optimize_portfolio(
            symbols=["AAPL", "MSFT", "GOOGL"],
            returns=sample_returns,
            current_prices=sample_prices,
            constraints=constraints,
        )
        
        # Weights should respect constraints
        for weight in result.weights.values():
            assert weight <= 0.55  # Allow small tolerance

    def test_optimize_portfolio_equal_weights_fallback(self, optimizer):
        """Test equal weights when optimization unavailable."""
        import numpy as np
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        returns = pd.DataFrame(np.random.randn(10, 2), columns=["A", "B"])
        
        result = optimizer.optimize_portfolio(
            symbols=["A", "B"],
            returns=returns,
            current_prices={"A": Decimal("100"), "B": Decimal("100")},
        )
        
        # Should have equal weights
        assert result.weights["A"] == result.weights["B"]

    def test_get_available_optimizers(self, optimizer):
        """Test getting available optimization methods."""
        methods = optimizer.get_available_optimizers()
        
        assert isinstance(methods, list)

    def test_calculate_portfolio_metrics(self, optimizer, sample_returns):
        """Test portfolio metrics calculation."""
        weights = {"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2}
        
        metrics = optimizer.calculate_portfolio_metrics(weights, sample_returns)
        
        assert "expected_return" in metrics
        assert "risk" in metrics
        assert "sharpe_ratio" in metrics
        assert metrics["expected_return"] > 0


class TestPortfolioOptimizerEdgeCases:
    """Edge case tests."""

    def test_empty_symbols_list(self, optimizer):
        """Test handling of empty symbols list."""
        result = optimizer.optimize_portfolio(
            symbols=[],
            returns=pd.DataFrame(),
            current_prices={},
        )
        assert isinstance(result, OptimizeResult)

    def test_single_symbol(self, optimizer):
        """Test optimization with single symbol."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        returns = pd.DataFrame({"A": [0.01] * 10}, index=dates)
        
        result = optimizer.optimize_portfolio(
            symbols=["A"],
            returns=returns,
            current_prices={"A": Decimal("100")},
        )
        
        assert "A" in result.weights

    def test_zero_volatility_returns(self, optimizer):
        """Test with zero volatility returns."""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        returns = pd.DataFrame({"A": [0.0] * 10}, index=dates)
        
        result = optimizer.optimize_portfolio(
            symbols=["A"],
            returns=returns,
            current_prices={"A": Decimal("100")},
        )
        
        assert isinstance(result, OptimizeResult)
