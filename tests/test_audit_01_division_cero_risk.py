"""
TASK-AUDIT-01: Tests for division by zero in RiskCalculator.

This module tests that all division operations in portfolio analytics
are protected against division by zero errors.
"""

from decimal import Decimal

import pytest

from app.services.portfolio_analytics_service import PortfolioAnalyticsService


class TestDivisionByZeroRiskCalculator:
    """Test division by zero protection in risk calculations."""

    @pytest.fixture
    def service(self):
        """Create portfolio analytics service."""
        return PortfolioAnalyticsService()

    def test_calculate_returns_with_zero_previous_value(self, service):
        """Test return calculation when previous value is zero."""
        values = [Decimal("100"), Decimal("0"), Decimal("105")]

        # Should not crash on division by zero
        returns = service._calculate_returns(values)
        assert isinstance(returns, list)

    def test_calculate_cumulative_return_with_zero_start(self, service):
        """Test cumulative return when starting value is zero."""
        values = [Decimal("0"), Decimal("100"), Decimal("105")]

        # Should handle zero start gracefully
        try:
            cumulative = service._calculate_cumulative_return(values)
            assert cumulative is not None or cumulative == Decimal("0")
        except ZeroDivisionError:
            pytest.fail("Should handle zero starting value gracefully")


class TestEdgeCasesRiskCalculator:
    """Test edge cases in risk calculations."""

    @pytest.fixture
    def service(self):
        """Create portfolio analytics service."""
        return PortfolioAnalyticsService()

    def test_calculate_volatility_with_constant_values(self, service):
        """Test volatility calculation with constant values (no variation)."""
        values = [Decimal("100"), Decimal("100"), Decimal("100")]
        returns = service._calculate_returns(values)

        # Should not crash even with zero variance
        try:
            volatility = service._calculate_volatility(returns)
            assert volatility is not None or volatility == Decimal("0")
        except (ZeroDivisionError, ValueError):
            pytest.fail("Should handle constant values gracefully")

    def test_calculate_returns_with_single_value(self, service):
        """Test return calculation with insufficient data."""
        values = [Decimal("100")]

        # Should return empty list or handle gracefully
        returns = service._calculate_returns(values)
        assert isinstance(returns, list)

    def test_calculate_cumulative_return_with_single_value(self, service):
        """Test cumulative return with single value."""
        values = [Decimal("100")]

        # Should handle gracefully
        try:
            cumulative = service._calculate_cumulative_return(values)
            # Should return zero or None for insufficient data
            assert cumulative is not None
        except (ZeroDivisionError, IndexError):
            pytest.fail("Should handle single value gracefully")
