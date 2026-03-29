"""
Tests for paper trading functionality.
"""

from decimal import Decimal

import pytest

from app.domain.models.portfolio import Portfolio


class TestPaperTrading:
    """Test paper trading operations."""

    @pytest.fixture
    def portfolio(self):
        """Create a test portfolio."""
        return Portfolio(
            portfolio_id="test_portfolio",
            cash=Decimal("100000"),
            broker="paper",
            positions=[],
        )

    def test_portfolio_initialization(self, portfolio):
        """Test portfolio initialization."""
        assert portfolio.cash == Decimal("100000")
        assert isinstance(portfolio.positions, list)
        assert portfolio.broker == "paper"

    def test_cash_balance(self, portfolio):
        """Test cash balance management."""
        assert portfolio.cash == Decimal("100000")
        portfolio.cash = Decimal("50000")
        assert portfolio.cash == Decimal("50000")
