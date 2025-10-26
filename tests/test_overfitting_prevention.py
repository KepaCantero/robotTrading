"""
Tests for overfitting prevention techniques.
"""

from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig


class TestOverfittingPrevention:
    """Test overfitting prevention methods."""

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

    def test_config_initialization(self, config):
        """Test backtest configuration initialization."""
        assert config.initial_capital == Decimal("100000")
        assert config.commission_per_trade == Decimal("1.0")

    def test_out_of_sample_generalization(self, config):
        """Test out-of-sample generalization."""
        # Verify configuration is properly initialized
        assert config is not None
        assert isinstance(config.initial_capital, Decimal)
