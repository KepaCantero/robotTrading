"""
Tests for expectancy calculation functionality.
"""

from datetime import datetime
from decimal import Decimal


from app.backtesting.metrics import calculate_expectancy, calculate_expectancy_with_confidence
from app.backtesting.models import Trade, TradeStatus


class TestCalculateExpectancy:
    """Test expectancy calculation."""

    def create_trade(
        self,
        trade_id: str,
        pnl: float,
        symbol: str = "TEST",
    ) -> Trade:
        """Helper to create a trade for testing."""
        return Trade(
            trade_id=trade_id,
            symbol=symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            status=TradeStatus.CLOSED,
            pnl=Decimal(str(pnl)),
            pnl_percentage=Decimal("10"),
        )

    def test_positive_expectancy(self):
        """Test calculation of positive expectancy."""
        # 60% win rate, $500 avg win, $300 avg loss
        # Expectancy = (0.6 * 500) - (0.4 * 300) = 300 - 120 = 180
        winning_trades = [
            self.create_trade("W1", 500),
            self.create_trade("W2", 500),
            self.create_trade("W3", 500),
        ]

        losing_trades = [
            self.create_trade("L1", -300),
            self.create_trade("L2", -300),
        ]

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        assert expectancy == Decimal("180")

    def test_negative_expectancy(self):
        """Test calculation of negative expectancy."""
        # 40% win rate, $200 avg win, $400 avg loss
        # Expectancy = (0.4 * 200) - (0.6 * 400) = 80 - 240 = -160
        winning_trades = [
            self.create_trade("W1", 200),
            self.create_trade("W2", 200),
        ]

        losing_trades = [
            self.create_trade("L1", -400),
            self.create_trade("L2", -400),
            self.create_trade("L3", -400),
        ]

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        assert expectancy == Decimal("-160")

    def test_zero_expectancy(self):
        """Test calculation of zero expectancy (breakeven)."""
        # 50% win rate, $300 avg win, $300 avg loss
        # Expectancy = (0.5 * 300) - (0.5 * 300) = 150 - 150 = 0
        winning_trades = [
            self.create_trade("W1", 300),
            self.create_trade("W2", 300),
        ]

        losing_trades = [
            self.create_trade("L1", -300),
            self.create_trade("L2", -300),
        ]

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        assert expectancy == Decimal("0")

    def test_all_winning_trades(self):
        """Test expectancy with only winning trades."""
        winning_trades = [
            self.create_trade("W1", 500),
            self.create_trade("W2", 600),
            self.create_trade("W3", 400),
        ]

        expectancy = calculate_expectancy(winning_trades, [])

        # All wins: expectancy should equal avg win
        # (500 + 600 + 400) / 3 = 500
        assert expectancy == Decimal("500")

    def test_all_losing_trades(self):
        """Test expectancy with only losing trades."""
        losing_trades = [
            self.create_trade("L1", -500),
            self.create_trade("L2", -600),
            self.create_trade("L3", -400),
        ]

        expectancy = calculate_expectancy([], losing_trades)

        # All losses: expectancy should equal avg loss (negative)
        # -(500 + 600 + 400) / 3 = -500
        assert expectancy == Decimal("-500")

    def test_empty_trades(self):
        """Test expectancy with no trades."""
        expectancy = calculate_expectancy([], [])

        assert expectancy == Decimal("0")

    def test_realistic_trading_scenario(self):
        """Test expectancy with realistic trading scenario."""
        # Typical strategy: 40% win rate, 2:1 reward:risk
        # Avg win: $600, Avg loss: $300
        # Expectancy = (0.4 * 600) - (0.6 * 300) = 240 - 180 = 60

        winning_trades = [
            self.create_trade("W1", 600),
            self.create_trade("W2", 600),
        ]

        losing_trades = [
            self.create_trade("L1", -300),
            self.create_trade("L2", -300),
            self.create_trade("L3", -300),
        ]

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        assert expectancy == Decimal("60")

    def test_expectancy_with_varying_amounts(self):
        """Test expectancy with varying trade amounts."""
        winning_trades = [
            self.create_trade("W1", 1000),
            self.create_trade("W2", 200),
            self.create_trade("W3", 500),
        ]

        losing_trades = [
            self.create_trade("L1", -150),
            self.create_trade("L2", -350),
        ]

        expectancy = calculate_expectancy(winning_trades, losing_trades)

        # Win rate: 3/5 = 60%
        # Avg win: (1000 + 200 + 500) / 3 = 566.67
        # Avg loss: (150 + 350) / 2 = 250
        # Expectancy = (0.6 * 566.67) - (0.4 * 250) = 340 - 100 = 240

        # Use approximate comparison for floating point
        assert abs(float(expectancy) - 240.0) < 1.0


class TestCalculateExpectancyWithConfidence:
    """Test expectancy calculation with confidence intervals."""

    def create_trade(
        self,
        trade_id: str,
        pnl: float,
        symbol: str = "TEST",
    ) -> Trade:
        """Helper to create a trade for testing."""
        return Trade(
            trade_id=trade_id,
            symbol=symbol,
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("100"),
            exit_price=Decimal("110"),
            entry_time=datetime(2024, 1, 1),
            exit_time=datetime(2024, 1, 2),
            status=TradeStatus.CLOSED,
            pnl=Decimal(str(pnl)),
            pnl_percentage=Decimal("10"),
        )

    def test_confidence_interval_basic(self):
        """Test basic confidence interval calculation."""
        winning_trades = [
            self.create_trade("W1", 500),
            self.create_trade("W2", 500),
        ]

        losing_trades = [
            self.create_trade("L1", -300),
            self.create_trade("L2", -300),
            self.create_trade("L3", -300),
        ]

        result = calculate_expectancy_with_confidence(
            winning_trades,
            losing_trades,
            confidence_level=0.95,
        )

        assert "expectancy" in result
        assert "lower_bound" in result
        assert "upper_bound" in result
        assert "std_error" in result

        # Expectancy should be positive
        assert result["expectancy"] > 0

        # Lower bound should be less than expectancy
        assert result["lower_bound"] < result["expectancy"]

        # Upper bound should be greater than expectancy
        assert result["upper_bound"] > result["expectancy"]

    def test_confidence_interval_empty(self):
        """Test confidence interval with no trades."""
        result = calculate_expectancy_with_confidence([], [], confidence_level=0.95)

        assert result["expectancy"] == Decimal("0")
        assert result["lower_bound"] == Decimal("0")
        assert result["upper_bound"] == Decimal("0")
        assert result["std_error"] == Decimal("0")

    def test_confidence_interval_narrow(self):
        """Test that confidence interval narrows with more data."""
        # Small sample
        small_wins = [self.create_trade(f"W{i}", 500) for i in range(5)]
        small_losses = [self.create_trade(f"L{i}", -300) for i in range(5)]

        small_result = calculate_expectancy_with_confidence(
            small_wins,
            small_losses,
            confidence_level=0.95,
        )

        # Large sample
        large_wins = [self.create_trade(f"W{i}", 500) for i in range(50)]
        large_losses = [self.create_trade(f"L{i}", -300) for i in range(50)]

        large_result = calculate_expectancy_with_confidence(
            large_wins,
            large_losses,
            confidence_level=0.95,
        )

        # Standard error should be smaller with larger sample
        assert large_result["std_error"] < small_result["std_error"]

        # Confidence interval should be narrower with larger sample
        small_range = float(small_result["upper_bound"] - small_result["lower_bound"])
        large_range = float(large_result["upper_bound"] - large_result["lower_bound"])

        assert large_range < small_range

    def test_confidence_interval_different_levels(self):
        """Test confidence intervals at different confidence levels."""
        winning_trades = [
            self.create_trade("W1", 500),
            self.create_trade("W2", 500),
        ]

        losing_trades = [
            self.create_trade("L1", -300),
            self.create_trade("L2", -300),
            self.create_trade("L3", -300),
        ]

        # 90% confidence
        result_90 = calculate_expectancy_with_confidence(
            winning_trades,
            losing_trades,
            confidence_level=0.90,
        )

        # 99% confidence
        result_99 = calculate_expectancy_with_confidence(
            winning_trades,
            losing_trades,
            confidence_level=0.99,
        )

        # 99% interval should be wider than 90% interval
        range_90 = float(result_90["upper_bound"] - result_90["lower_bound"])
        range_99 = float(result_99["upper_bound"] - result_99["lower_bound"])

        assert range_99 > range_90
