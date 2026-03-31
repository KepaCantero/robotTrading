"""
Tests for mock integration scenarios.
"""

from decimal import Decimal

import pytest


class TestMockIntegration:
    """Test mock integration functionality."""

    @pytest.fixture
    def portfolio_provider(self):
        """Paper trading portfolio provider fixture."""
        from app.infrastructure.providers.paper_trading import PaperTradingPortfolioProvider

        return PaperTradingPortfolioProvider(initial_cash=Decimal("100000"))

    def test_portfolio_provider(self, portfolio_provider):
        """Test portfolio provider."""
        assert portfolio_provider is not None
        assert portfolio_provider.initial_cash == Decimal("100000")
