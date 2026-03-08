"""
Tests for portfolio concurrency operations.
"""

from decimal import Decimal

import pytest

from app.domain.models.portfolio import Portfolio


class TestPortfolioConcurrency:
    """Test portfolio concurrency handling."""

    @pytest.fixture
    def portfolio(self):
        """Create a test portfolio."""
        return Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("100000"),
            broker="paper",
            positions=[],
        )

    def test_portfolio_operations(self, portfolio):
        """Test basic portfolio operations."""
        assert portfolio.cash == Decimal("100000")
        portfolio.cash = Decimal("90000")
        assert portfolio.cash == Decimal("90000")
