"""
Integration Tests: Liquidity Validation with Backtesting Engine

Tests that liquidity validation is properly integrated into the backtesting
engine and affects trade execution realistically.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.liquidity_validator import LiquidityValidator
from app.backtesting.models import BacktestConfig
from app.domain.models.market_data import Quote


def past_time(hours_ago=1):
    """Create a datetime in the past."""
    return datetime.utcnow() - timedelta(hours=hours_ago)


class TestLiquidityIntegration:
    """Test liquidity validator integration with backtesting engine."""

    @pytest.fixture
    def backtester(self):
        """Create backtester with default configuration."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            stop_loss_percentage=Decimal("5"),
            take_profit_percentage=Decimal("10"),
            max_position_size=Decimal("0.25"),  # 25% max position
        )
        return SimpleBacktester(config)

    @pytest.fixture
    def validator(self):
        """Create a standalone LiquidityValidator for direct testing."""
        return LiquidityValidator(
            enable_partial_fills=True,
            max_order_pct_of_volume=Decimal("0.10"),
            warning_order_pct_of_volume=Decimal("0.05"),
            partial_fill_pct=Decimal("0.05"),
        )

    def test_liquidity_validator_initialized(self, backtester):
        """Test that liquidity validator is properly initialized."""
        assert (
            backtester.liquidity_validator is not None
        ), "LiquidityValidator should be initialized"
        assert (
            backtester.liquidity_validator.enable_partial_fills == True
        ), "Partial fills should be enabled by default"

    def test_normal_order_executes_with_liquidity_validation(self, validator, default_symbol):
        """Test that normal orders execute successfully with liquidity validation."""
        bar = Quote(
            symbol=default_symbol,
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),  # 1M shares daily
            spread=Decimal("1.0"),
        )

        # Order for 5000 shares = 0.5% of daily volume - well within limits
        result = validator.simulate_fill(
            order_quantity=Decimal("5000"),
            current_bar=bar,
            order_side="buy",
            symbol=default_symbol,
        )

        assert result.fill_status == "FILLED", f"Normal order should be filled: {result.rejection_reason}"
        assert result.filled_quantity == Decimal("5000"), "Should fill full quantity"
        assert result.fill_price > Decimal("100"), "Fill price should include market impact"

    def test_excessive_order_rejected_by_liquidity_validation(self, validator):
        """Test that orders exceeding liquidity limits are rejected."""
        bar = Quote(
            symbol="PENNY",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("4.5"),
            ask=Decimal("5.5"),
            last=Decimal("5"),
            open=Decimal("5"),
            high=Decimal("6"),
            low=Decimal("4"),
            close=Decimal("5"),
            volume=Decimal("10000"),  # Only 10K shares daily (illiquid)
            spread=Decimal("1.0"),
        )

        # Order for 5000 shares = 50% of daily volume - should be rejected
        result = validator.simulate_fill(
            order_quantity=Decimal("5000"),
            current_bar=bar,
            order_side="buy",
            symbol="PENNY",
        )

        assert result.fill_status == "REJECTED", (
            f"Excessive order should be rejected, got: {result.fill_status}"
        )
        assert result.filled_quantity == Decimal("0"), "Rejected order should have zero fill"
        assert result.rejection_reason is not None, "Should have a rejection reason"

    def test_partial_fill_for_large_order(self, validator):
        """Test that large orders get partial fills."""
        bar = Quote(
            symbol="TEST",
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("500000"),  # 500K shares daily
            spread=Decimal("1.0"),
        )

        # Order for 50000 shares = 10% of daily volume - exactly at max threshold,
        # but above partial_fill_pct (5% = 25000), so should get partial fill
        result = validator.simulate_fill(
            order_quantity=Decimal("37500"),  # 7.5% of daily volume
            current_bar=bar,
            order_side="buy",
            symbol="TEST",
        )

        assert result.fill_status == "PARTIAL", (
            f"Large order should get partial fill, got: {result.fill_status}"
        )
        assert result.filled_quantity > 0, "Should have some fill"
        # Partial fill should be capped at 5% of daily volume (25,000 shares)
        assert result.filled_quantity <= Decimal("25000"), (
            f"Partial fill {result.filled_quantity} should be <= 25,000 (5% of 500K)"
        )

    def test_sell_order_liquidity_validation(self, validator, default_symbol):
        """Test that sell orders also undergo liquidity validation."""
        bar = Quote(
            symbol=default_symbol,
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        # Normal sell order - 5000 shares = 0.5% of daily volume
        result = validator.simulate_fill(
            order_quantity=Decimal("5000"),
            current_bar=bar,
            order_side="sell",
            symbol=default_symbol,
        )

        assert result.fill_status == "FILLED", f"Sell order should be filled: {result.rejection_reason}"
        assert result.filled_quantity == Decimal("5000"), "Should fill full quantity"
        # Sell price should be less than close due to slippage
        assert result.fill_price < Decimal("100"), (
            "Sell fill price should include slippage (less than close)"
        )

    def test_liquidity_metrics_available(self, backtester, default_symbol):
        """Test that liquidity metrics can be retrieved."""
        bar = Quote(
            symbol=default_symbol,
            timestamp=past_time(hours_ago=1),
            bid=Decimal("99.5"),
            ask=Decimal("100.5"),
            last=Decimal("100"),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1000000"),
            spread=Decimal("1.0"),
        )

        # Get liquidity metrics
        metrics = backtester.liquidity_validator.get_liquidity_metrics(
            current_bar=bar, order_quantity=Decimal("50000")
        )

        # Verify metrics
        assert "daily_volume" in metrics
        assert "max_order_size" in metrics
        assert "warning_threshold" in metrics
        assert "partial_fill_size" in metrics
        assert "order_quantity" in metrics
        assert "order_pct_of_volume" in metrics
        assert "would_reject" in metrics
        assert "would_warn" in metrics

        # Verify values
        assert metrics["daily_volume"] == 1000000.0
        assert metrics["max_order_size"] == 100000.0  # 10% of 1M
        assert metrics["warning_threshold"] == 50000.0  # 5% of 1M
        assert metrics["partial_fill_size"] == 50000.0  # 5% of 1M
