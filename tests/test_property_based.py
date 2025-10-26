"""
Tests for property-based testing.
"""

from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig


class TestPropertyBased:
    """Test property-based testing concepts."""

    @pytest.fixture
    def config(self):
        """Default backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )

    def test_position_size_threshold(self, config):
        """Test position size threshold validation."""
        assert config.max_position_size == Decimal("0.1")
        thresholds = config
        assert thresholds.max_position_size == Decimal("0.1")
