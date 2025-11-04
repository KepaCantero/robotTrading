"""
Tests for system concurrency operations.
"""

from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig


class TestSystemConcurrency:
    """Test system concurrency handling."""

    @pytest.fixture
    def backtest_config(self):
        """Create backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )

    def test_backtester_initialization(self, backtest_config):
        """Test backtester initialization."""
        backtester = SimpleBacktester(backtest_config)
        assert backtester is not None
