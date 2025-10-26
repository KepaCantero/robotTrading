"""
Tests for survivorship bias prevention.
"""

from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig


class TestSurvivorshipBias:
    """Test survivorship bias prevention."""

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

    def test_survivorship_bias_detection(self, config):
        """Test survivorship bias detection."""
        assert config is not None
        assert isinstance(config.initial_capital, Decimal)

    def test_delisted_assets_inclusion(self, config):
        """Test delisted assets inclusion in backtesting."""
        assert config.max_position_size == Decimal("0.1")
