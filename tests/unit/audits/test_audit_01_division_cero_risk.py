"""
TASK-AUDIT-01: Tests for division by zero in portfolio calculations.

This module tests that all division operations in portfolio analytics
are protected against division by zero errors.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.services.portfolio_analytics._portfolio_calculations import PortfolioCalculations


def _make_portfolio(total_value: Decimal, positions=None):
    """Create a mock portfolio with the given total value."""
    portfolio = MagicMock()
    portfolio.total_value = total_value
    portfolio.positions = positions or []
    return portfolio


class TestDivisionByZeroPortfolioCalculations:
    """Test division by zero protection in portfolio calculations."""

    @pytest.fixture
    def service(self):
        """Create portfolio calculations instance."""
        return PortfolioCalculations()

    def test_herfindahl_with_zero_total_value(self, service):
        """Test Herfindahl index when total portfolio value is zero."""
        portfolio = _make_portfolio(Decimal("0"))

        result = service.calculate_herfindahl_index(portfolio)
        assert result == Decimal("0")

    def test_herfindahl_with_empty_portfolio(self, service):
        """Test Herfindahl index with no positions."""
        portfolio = _make_portfolio(Decimal("1000"), positions=[])

        result = service.calculate_herfindahl_index(portfolio)
        assert result == Decimal("0")

    def test_effective_positions_with_zero_herfindahl(self, service):
        """Test effective positions when herfindahl is zero (empty portfolio)."""
        portfolio = _make_portfolio(Decimal("0"))

        result = service.calculate_effective_positions(portfolio)
        assert result == Decimal("0")

    def test_largest_position_weight_zero_total(self, service):
        """Test largest position weight when total value is zero."""
        portfolio = _make_portfolio(Decimal("0"))

        result = service.calculate_largest_position_weight(portfolio)
        assert result == Decimal("0")

    def test_largest_position_weight_empty(self, service):
        """Test largest position weight with no positions."""
        portfolio = _make_portfolio(Decimal("1000"), positions=[])

        result = service.calculate_largest_position_weight(portfolio)
        assert result == Decimal("0")
