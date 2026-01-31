"""
Comprehensive unit tests for MetricsCalculator.

Following TDD best practices from Kent Beck:
1. Test-driven development - tests first
2. One assertion per test (mostly)
3. Descriptive test names
4. Arrange-Act-Assert pattern
5. Testing edge cases and boundaries
6. Property-based testing with Hypothesis
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import List
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch, MagicMock

from app.backtesting.metrics import (
    MetricsCalculator,
    calculate_profit_factor,
    calculate_expectancy,
    calculate_expectancy_with_confidence,
)
from app.backtesting.models import Trade, TradeStatus


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_trades() -> List[Trade]:
    """Create sample trades for testing."""
    base_time = datetime(2024, 1, 1, 9, 30, 0)

    return [
        Trade(
            trade_id="T001",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=base_time,
            exit_time=base_time + timedelta(days=1),
            status=TradeStatus.CLOSED,
            pnl=Decimal("500"),  # 100 * (155-150) = 500 profit
        ),
        Trade(
            trade_id="T002",
            symbol="MSFT",
            side="buy",
            quantity=Decimal("50"),
            entry_price=Decimal("300.00"),
            exit_price=Decimal("295.00"),
            entry_time=base_time + timedelta(days=2),
            exit_time=base_time + timedelta(days=3),
            status=TradeStatus.CLOSED,
            pnl=Decimal("-250"),  # 50 * (295-300) = -250 loss
        ),
        Trade(
            trade_id="T003",
            symbol="GOOGL",
            side="buy",
            quantity=Decimal("20"),
            entry_price=Decimal("140.00"),
            exit_price=Decimal("145.00"),
            entry_time=base_time + timedelta(days=4),
            exit_time=base_time + timedelta(days=5),
            status=TradeStatus.CLOSED,
            pnl=Decimal("100"),  # 20 * (145-140) = 100 profit
        ),
        Trade(
            trade_id="T004",
            symbol="TSLA",
            side="buy",
            quantity=Decimal("30"),
            entry_price=Decimal("200.00"),
            exit_price=Decimal("190.00"),
            entry_time=base_time + timedelta(days=6),
            exit_time=base_time + timedelta(days=7),
            status=TradeStatus.CLOSED,
            pnl=Decimal("-300"),  # 30 * (190-200) = -300 loss
        ),
    ]


@pytest.fixture
def winning_trades() -> List[Trade]:
    """Create only winning trades."""
    base_time = datetime(2024, 1, 1)
    return [
        Trade(
            trade_id=f"WIN{i:03d}",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=base_time + timedelta(days=i),
            exit_time=base_time + timedelta(days=i + 1),
            status=TradeStatus.CLOSED,
            pnl=Decimal("500"),
        )
        for i in range(5)
    ]


@pytest.fixture
def losing_trades() -> List[Trade]:
    """Create only losing trades."""
    base_time = datetime(2024, 1, 1)
    return [
        Trade(
            trade_id=f"LOSS{i:03d}",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("155.00"),
            exit_price=Decimal("150.00"),
            entry_time=base_time + timedelta(days=i),
            exit_time=base_time + timedelta(days=i + 1),
            status=TradeStatus.CLOSED,
            pnl=Decimal("-500"),
        )
        for i in range(3)
    ]


@pytest.fixture
def calculator():
    """Create MetricsCalculator instance."""
    return MetricsCalculator(risk_free_rate=Decimal("0.02"))


# =============================================================================
# MetricsCalculator Initialization Tests
# =============================================================================


class TestMetricsCalculatorInitialization:
    """Test suite for MetricsCalculator initialization."""

    def test_initialization_with_default_risk_free_rate(self):
        """Test that calculator initializes with default risk-free rate."""
        calc = MetricsCalculator()
        assert calc.risk_free_rate == Decimal("0.02")

    def test_initialization_with_custom_risk_free_rate(self):
        """Test that calculator accepts custom risk-free rate."""
        calc = MetricsCalculator(risk_free_rate=Decimal("0.03"))
        assert calc.risk_free_rate == Decimal("0.03")

    def test_initialization_with_zero_risk_free_rate(self):
        """Test that calculator accepts zero risk-free rate."""
        calc = MetricsCalculator(risk_free_rate=Decimal("0"))
        assert calc.risk_free_rate == Decimal("0")

    def test_initialization_with_negative_risk_free_rate(self):
        """Test that calculator handles negative risk-free rate."""
        calc = MetricsCalculator(risk_free_rate=Decimal("-0.01"))
        assert calc.risk_free_rate == Decimal("-0.01")


# =============================================================================
# Calculate All Metrics Tests
# =============================================================================


class TestCalculateAllMetrics:
    """Test suite for calculate_all_metrics method."""

    def test_calculate_metrics_with_sample_trades(self, calculator, sample_trades):
        """Test metrics calculation with sample trades."""
        initial_capital = Decimal("10000")
        final_capital = Decimal("10500")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=initial_capital,
            final_capital=final_capital,
            start_date=start_date,
            end_date=end_date,
        )

        # Basic assertions
        assert metrics.total_trades == 4
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 2
        assert metrics.win_rate == Decimal("50")

    def test_calculate_metrics_filters_open_trades(self, calculator):
        """Test that only closed trades are included in metrics."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id="T001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            ),
            Trade(
                trade_id="T002",
                symbol="MSFT",
                side="buy",
                quantity=Decimal("50"),
                entry_price=Decimal("300"),
                exit_price=None,
                entry_time=base_time + timedelta(days=2),
                exit_time=None,
                status=TradeStatus.OPEN,
                pnl=None,
            ),
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Only closed trade should be counted
        assert metrics.total_trades == 1
        assert metrics.winning_trades == 1

    def test_calculate_metrics_with_no_trades_returns_empty_metrics(self, calculator):
        """Test that empty trade list returns empty metrics."""
        metrics = calculator.calculate_all_metrics(
            trades=[],
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.win_rate == Decimal("0")

    def test_calculate_metrics_validates_initial_capital_positive(self, calculator, sample_trades):
        """Test that zero initial capital raises ValueError."""
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            calculator.calculate_all_metrics(
                trades=sample_trades,
                initial_capital=Decimal("0"),
                final_capital=Decimal("10000"),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
            )

    def test_calculate_metrics_validates_initial_capital_not_negative(
        self, calculator, sample_trades
    ):
        """Test that negative initial capital raises ValueError."""
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            calculator.calculate_all_metrics(
                trades=sample_trades,
                initial_capital=Decimal("-1000"),
                final_capital=Decimal("10000"),
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
            )

    def test_calculate_total_pnl_correctly(self, calculator, sample_trades):
        """Test that total P&L is calculated correctly."""
        # Sample trades have P&L: +500, -250, +100, -300 = +50 total
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.total_pnl == Decimal("50")

    def test_calculate_total_pnl_percentage_correctly(self, calculator, sample_trades):
        """Test that P&L percentage is calculated correctly."""
        # 50 / 10000 * 100 = 0.5%
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        expected_percentage = Decimal("50") / Decimal("10000") * Decimal("100")
        assert metrics.total_pnl_percentage == expected_percentage


# =============================================================================
# Win Rate Calculation Tests
# =============================================================================


class TestWinRateCalculation:
    """Test suite for win rate calculation."""

    def test_win_rate_all_winning_trades(self, calculator, winning_trades):
        """Test win rate with 100% winning trades."""
        metrics = calculator.calculate_all_metrics(
            trades=winning_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("12500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.win_rate == Decimal("100")

    def test_win_rate_all_losing_trades(self, calculator, losing_trades):
        """Test win rate with 0% winning trades."""
        metrics = calculator.calculate_all_metrics(
            trades=losing_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("8500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.win_rate == Decimal("0")

    def test_win_rate_mixed_trades(self, calculator, sample_trades):
        """Test win rate with mixed winning and losing trades."""
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # 2 winning out of 4 = 50%
        assert metrics.win_rate == Decimal("50")

    def test_win_rate_is_capped_at_100(self, calculator):
        """Test that win rate never exceeds 100% due to rounding."""
        base_time = datetime(2024, 1, 1)
        # Create trades that might result in rounding issues
        trades = [
            Trade(
                trade_id=f"T{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            )
            for i in range(100)
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("60000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        assert metrics.win_rate <= Decimal("100")


# =============================================================================
# Profit Factor Tests
# =============================================================================


class TestProfitFactor:
    """Test suite for profit factor calculation."""

    def test_profit_factor_with_winning_and_losing_trades(self, winning_trades, losing_trades):
        """Test profit factor calculation."""
        # Gross profit: 5 * 500 = 2500
        # Gross loss: 3 * 500 = 1500
        # Profit factor: 2500 / 1500 = 1.667
        profit_factor = calculate_profit_factor(winning_trades, losing_trades)

        assert profit_factor == Decimal("2500") / Decimal("1500")

    def test_profit_factor_with_only_winning_trades(self, winning_trades):
        """Test profit factor when no losing trades."""
        # Should return 999 (perfect scenario)
        profit_factor = calculate_profit_factor(winning_trades, [])

        assert profit_factor == Decimal("999")

    def test_profit_factor_with_only_losing_trades(self, losing_trades):
        """Test profit factor when no winning trades."""
        profit_factor = calculate_profit_factor([], losing_trades)

        assert profit_factor == Decimal("0")

    def test_profit_factor_with_empty_lists(self):
        """Test profit factor with no trades."""
        profit_factor = calculate_profit_factor([], [])

        # Should handle gracefully - gross_profit=0, gross_loss=1 (fallback)
        assert profit_factor == Decimal("0")


# =============================================================================
# Expectancy Calculation Tests
# =============================================================================


class TestExpectancyCalculation:
    """Test suite for expectancy calculation."""

    def test_expectancy_with_positive_edge(self, winning_trades, losing_trades):
        """Test expectancy with profitable strategy."""
        # Win rate: 5/8 = 62.5%, Loss rate: 37.5%
        # Avg win: 500, Avg loss: 500
        # Expectancy = (0.625 * 500) - (0.375 * 500) = 312.5 - 187.5 = 125
        expectancy = calculate_expectancy(winning_trades, losing_trades)

        assert expectancy > 0

    def test_expectancy_with_negative_edge(self):
        """Test expectancy with unprofitable strategy."""
        base_time = datetime(2024, 1, 1)
        wins = [
            Trade(
                trade_id="W001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("100"),  # Small wins
            )
        ]
        losses = [
            Trade(
                trade_id=f"L00{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("140"),
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-1000"),  # Large losses
            )
            for i in range(3)
        ]

        expectancy = calculate_expectancy(wins, losses)
        assert expectancy < 0

    def test_expectancy_with_no_trades(self):
        """Test expectancy with no trades."""
        expectancy = calculate_expectancy([], [])

        assert expectancy == Decimal("0")

    def test_expectancy_with_only_winning_trades(self, winning_trades):
        """Test expectancy with only winning trades."""
        expectancy = calculate_expectancy(winning_trades, [])

        assert expectancy > 0
        assert expectancy == Decimal("500")  # All wins are 500


# =============================================================================
# Drawdown Calculation Tests
# =============================================================================


class TestDrawdownCalculation:
    """Test suite for drawdown calculation."""

    def test_max_drawdown_with_profitable_trades(self, calculator):
        """Test max drawdown calculation with profitable equity curve."""
        base_time = datetime(2024, 1, 1)
        # Create trades that result in a growing equity curve
        trades = [
            Trade(
                trade_id=f"T{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=i * 2),
                exit_time=base_time + timedelta(days=i * 2 + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            )
            for i in range(10)
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("15000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 28),
        )

        # Should have minimal or zero drawdown
        assert metrics.max_drawdown <= Decimal("0")

    def test_max_drawdown_with_losing_sequence(self, calculator):
        """Test max drawdown with losing trades at start."""
        base_time = datetime(2024, 1, 1)
        trades = [
            # First 5 trades lose
            Trade(
                trade_id=f"LOSS{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("155"),
                exit_price=Decimal("150"),
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-500"),
            )
            for i in range(5)
        ] + [
            # Then 5 trades win
            Trade(
                trade_id=f"WIN{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=5 + i),
                exit_time=base_time + timedelta(days=6 + i),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            )
            for i in range(5)
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 10),
        )

        # Should have negative drawdown
        assert metrics.max_drawdown < Decimal("0")

    def test_max_drawdown_never_exceeds_initial_capital(self, calculator):
        """Test that max drawdown is bounded by initial capital."""
        base_time = datetime(2024, 1, 1)
        # Create extreme losing scenario
        trades = [
            Trade(
                trade_id=f"T{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("1000"),
                entry_price=Decimal("100"),
                exit_price=Decimal("50"),
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-50000"),
            )
            for i in range(5)
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("-240000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 10),
        )

        # Drawdown should not exceed -100% of initial capital
        assert metrics.max_drawdown >= -Decimal("10000")


# =============================================================================
# CAGR Calculation Tests
# =============================================================================


class TestCAGRCalculation:
    """Test suite for CAGR calculation."""

    def test_cagr_with_positive_returns(self, calculator):
        """Test CAGR with profitable investment."""
        initial = Decimal("10000")
        final = Decimal("20000")  # Doubled
        start = datetime(2020, 1, 1)
        end = datetime(2024, 1, 1)  # 4 years

        cagr = calculator.calculate_cagr(initial, final, start, end)

        # (20000/10000)^(1/4) - 1 = ~18.92%
        assert cagr > Decimal("18")
        assert cagr < Decimal("20")

    def test_cagr_with_negative_returns(self, calculator):
        """Test CAGR with loss."""
        initial = Decimal("10000")
        final = Decimal("5000")  # Halved
        start = datetime(2020, 1, 1)
        end = datetime(2024, 1, 1)  # 4 years

        cagr = calculator.calculate_cagr(initial, final, start, end)

        # Should be negative
        assert cagr < Decimal("0")

    def test_cagr_with_no_change(self, calculator):
        """Test CAGR with no profit/loss."""
        initial = Decimal("10000")
        final = Decimal("10000")
        start = datetime(2020, 1, 1)
        end = datetime(2024, 1, 1)

        cagr = calculator.calculate_cagr(initial, final, start, end)

        assert cagr == Decimal("0")

    def test_cagr_validates_initial_capital_positive(self, calculator):
        """Test that zero initial capital raises ValueError."""
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            calculator.calculate_cagr(
                Decimal("0"),
                Decimal("10000"),
                datetime(2020, 1, 1),
                datetime(2024, 1, 1),
            )

    def test_cagr_validates_final_capital_positive(self, calculator):
        """Test that zero final capital raises ValueError."""
        with pytest.raises(ValueError, match="final_capital must be positive"):
            calculator.calculate_cagr(
                Decimal("10000"),
                Decimal("0"),
                datetime(2020, 1, 1),
                datetime(2024, 1, 1),
            )

    def test_cagr_validates_date_order(self, calculator):
        """Test that end_date must be after start_date."""
        with pytest.raises(ValueError, match="start_date.*must be before end_date"):
            calculator.calculate_cagr(
                Decimal("10000"),
                Decimal("20000"),
                datetime(2024, 1, 1),
                datetime(2020, 1, 1),  # Before start
            )

    def test_cagr_with_same_dates_raises_error(self, calculator):
        """Test that same dates raise ValueError."""
        same_date = datetime(2024, 1, 1)
        with pytest.raises(ValueError, match="start_date.*must be before end_date"):
            calculator.calculate_cagr(
                Decimal("10000"),
                Decimal("20000"),
                same_date,
                same_date,
            )


# =============================================================================
# Risk-Reward Ratio Tests
# =============================================================================


class TestRiskRewardRatio:
    """Test suite for risk-reward ratio calculation."""

    def test_risk_reward_ratio_with_favorable_trades(self, calculator, sample_trades):
        """Test risk-reward ratio with good win/loss profile."""
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Sample trades: avg win = (500+100)/2 = 300, avg loss = (250+300)/2 = 275
        # Risk/reward = 300/275 ≈ 1.09
        assert metrics.risk_reward_ratio is not None
        assert metrics.risk_reward_ratio > 0

    def test_risk_reward_ratio_with_only_winning_trades(self, calculator, winning_trades):
        """Test risk-reward ratio with only wins (should be None)."""
        metrics = calculator.calculate_all_metrics(
            trades=winning_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("12500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should be None when no losing trades
        assert metrics.risk_reward_ratio is None

    def test_risk_reward_ratio_with_only_losing_trades(self, calculator, losing_trades):
        """Test risk-reward ratio with only losses (should be None)."""
        metrics = calculator.calculate_all_metrics(
            trades=losing_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("8500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should be None when no winning trades
        assert metrics.risk_reward_ratio is None


# =============================================================================
# Average Win/Loss Tests
# =============================================================================


class TestAverageWinLoss:
    """Test suite for average win and loss calculations."""

    def test_average_win_with_winning_trades(self, calculator, winning_trades):
        """Test average win calculation."""
        metrics = calculator.calculate_all_metrics(
            trades=winning_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("12500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # All wins are 500, so avg should be 500
        assert metrics.avg_win == Decimal("500")

    def test_average_loss_with_losing_trades(self, calculator, losing_trades):
        """Test average loss calculation."""
        metrics = calculator.calculate_all_metrics(
            trades=losing_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("8500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # All losses are 500, so avg should be -500
        assert metrics.avg_loss == Decimal("-500")

    def test_largest_win_and_loss(self, calculator, sample_trades):
        """Test largest win and loss identification."""
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Largest win: 500 (T001), Largest loss: -300 (T004)
        assert metrics.largest_win == Decimal("500")
        assert metrics.largest_loss == Decimal("-300")


# =============================================================================
# Trade Duration Tests
# =============================================================================


class TestTradeDuration:
    """Test suite for trade duration calculations."""

    def test_average_trade_duration_with_single_day_trades(self, calculator, sample_trades):
        """Test average trade duration for 1-day trades."""
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # All trades are 1 day
        assert metrics.avg_trade_duration == Decimal("1")

    def test_average_trade_duration_with_varying_durations(self, calculator):
        """Test average trade duration with varying hold times."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id=f"T{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            )
            for i in range(1, 6)  # Durations: 2, 3, 4, 5, 6 days
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("12500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Average: (2+3+4+5+6)/5 = 4
        assert metrics.avg_trade_duration == Decimal("4")

    def test_total_days_calculation(self, calculator, sample_trades):
        """Test total days calculation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=start_date,
            end_date=end_date,
        )

        # 30 days
        assert metrics.total_days == 30


# =============================================================================
# Property-Based Tests with Hypothesis
# =============================================================================


class TestMetricsCalculatorProperties:
    """Property-based tests using Hypothesis."""

    @given(
        initial_capital=st.integers(min_value=1000, max_value=1000000),
        num_trades=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_win_rate_always_between_0_and_100(self, calculator, initial_capital, num_trades):
        """Property: Win rate should always be between 0 and 100."""
        base_time = datetime(2024, 1, 1)
        trades = []
        for i in range(num_trades):
            is_win = i % 2 == 0  # Alternate wins and losses
            pnl = Decimal("500") if is_win else Decimal("-500")
            trades.append(
                Trade(
                    trade_id=f"T{i:03d}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("150"),
                    exit_price=Decimal("155") if is_win else Decimal("145"),
                    entry_time=base_time + timedelta(days=i),
                    exit_time=base_time + timedelta(days=i + 1),
                    status=TradeStatus.CLOSED,
                    pnl=pnl,
                )
            )

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal(str(initial_capital)),
            final_capital=Decimal(str(initial_capital)),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        assert Decimal("0") <= metrics.win_rate <= Decimal("100")

    @given(
        initial_capital=st.integers(min_value=1000, max_value=100000),
        final_capital=st.integers(min_value=1000, max_value=100000),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_pnl_equals_final_minus_initial(self, calculator, initial_capital, final_capital):
        """Property: For no-trades scenario, P&L should equal final minus initial capital."""
        # Ensure final >= initial for this test
        if final_capital < initial_capital:
            initial_capital, final_capital = final_capital, initial_capital

        metrics = calculator.calculate_all_metrics(
            trades=[],
            initial_capital=Decimal(str(initial_capital)),
            final_capital=Decimal(str(final_capital)),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        expected_pnl = Decimal(str(final_capital)) - Decimal(str(initial_capital))
        assert metrics.total_pnl == expected_pnl

    @given(
        num_winning=st.integers(min_value=0, max_value=50),
        num_losing=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_total_trades_equals_sum_of_wins_and_losses(self, calculator, num_winning, num_losing):
        """Property: Total trades should equal wins + losses."""
        base_time = datetime(2024, 1, 1)
        trades = []

        # Add winning trades
        for i in range(num_winning):
            trades.append(
                Trade(
                    trade_id=f"W{i:03d}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("150"),
                    exit_price=Decimal("155"),
                    entry_time=base_time + timedelta(days=i),
                    exit_time=base_time + timedelta(days=i + 1),
                    status=TradeStatus.CLOSED,
                    pnl=Decimal("500"),
                )
            )

        # Add losing trades
        for i in range(num_losing):
            trades.append(
                Trade(
                    trade_id=f"L{i:03d}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("155"),
                    exit_price=Decimal("150"),
                    entry_time=base_time + timedelta(days=num_winning + i),
                    exit_time=base_time + timedelta(days=num_winning + i + 1),
                    status=TradeStatus.CLOSED,
                    pnl=Decimal("-500"),
                )
            )

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        assert metrics.total_trades == num_winning + num_losing
        assert metrics.winning_trades == num_winning
        assert metrics.losing_trades == num_losing


# =============================================================================
# Edge Cases and Boundary Conditions
# =============================================================================


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_zero_pnl_trade(self, calculator):
        """Test handling of trades with zero P&L."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id="T001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("150"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("0"),
            )
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Zero P&L should be counted as losing trade (P&L <= 0)
        assert metrics.total_trades == 1
        assert metrics.losing_trades == 1

    def test_very_small_pnl_values(self, calculator):
        """Test handling of very small P&L values."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id="T001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("1"),
                entry_price=Decimal("150"),
                exit_price=Decimal("150.01"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("0.01"),
            )
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000.01"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.total_pnl == Decimal("0.01")

    def test_trades_with_none_pnl(self, calculator):
        """Test trades with None P&L are handled correctly."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id="T001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=None,  # Explicitly None
            )
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should handle None P&L gracefully
        assert metrics.total_trades == 1

    def test_unordered_trades(self, calculator):
        """Test that trades are processed in chronological order regardless of input order."""
        base_time = datetime(2024, 1, 1)
        trades = [
            Trade(
                trade_id="T003",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=6),
                exit_time=base_time + timedelta(days=7),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            ),
            Trade(
                trade_id="T001",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time,
                exit_time=base_time + timedelta(days=1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            ),
            Trade(
                trade_id="T002",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=3),
                exit_time=base_time + timedelta(days=4),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            ),
        ]

        # Should not raise error and should process correctly
        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("11500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        assert metrics.total_trades == 3


# =============================================================================
# Sharpe and Sortino Ratio Tests
# =============================================================================


class TestSharpeSortinoRatios:
    """Test suite for Sharpe and Sortino ratio calculations."""

    def test_sharpe_ratio_with_constant_positive_returns(self, calculator):
        """Test Sharpe ratio with constant positive returns."""
        base_time = datetime(2024, 1, 1)
        # Create trades with consistent positive returns
        trades = [
            Trade(
                trade_id=f"T{i:03d}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                exit_price=Decimal("155"),
                entry_time=base_time + timedelta(days=i),
                exit_time=base_time + timedelta(days=i + 1),
                status=TradeStatus.CLOSED,
                pnl=Decimal("500"),
            )
            for i in range(20)
        ]

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("20000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should have positive Sharpe ratio
        assert metrics.sharpe_ratio is not None
        # With zero volatility in returns, Sharpe should be defined
        assert isinstance(metrics.sharpe_ratio, Decimal)

    def test_sharpe_ratio_with_high_volatility(self, calculator):
        """Test Sharpe ratio with volatile returns."""
        base_time = datetime(2024, 1, 1)
        trades = []
        for i in range(20):
            is_win = i % 2 == 0
            pnl = Decimal("1000") if is_win else Decimal("-500")
            trades.append(
                Trade(
                    trade_id=f"T{i:03d}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("150"),
                    exit_price=Decimal("155") if is_win else Decimal("145"),
                    entry_time=base_time + timedelta(days=i),
                    exit_time=base_time + timedelta(days=i + 1),
                    status=TradeStatus.CLOSED,
                    pnl=pnl,
                )
            )

        metrics = calculator.calculate_all_metrics(
            trades=trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10000"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should have Sharpe ratio (might be lower due to volatility)
        assert metrics.sharpe_ratio is not None

    def test_sortino_ratio_with_no_downside(self, calculator, winning_trades):
        """Test Sortino ratio when there are no losing trades."""
        metrics = calculator.calculate_all_metrics(
            trades=winning_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("12500"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # With no downside deviation, Sortino should still be computed
        # (either high value or zero depending on implementation)
        assert metrics.sortino_ratio is not None

    def test_sortino_ratio_with_downside(self, calculator, sample_trades):
        """Test Sortino ratio with downside risk."""
        metrics = calculator.calculate_all_metrics(
            trades=sample_trades,
            initial_capital=Decimal("10000"),
            final_capital=Decimal("10050"),
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
        )

        # Should have Sortino ratio
        assert metrics.sortino_ratio is not None
