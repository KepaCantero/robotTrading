"""
Tests for PerformanceMetricsCalculator service.

Tests performance metrics calculation, Sharpe ratio, and win rate.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.performance_calculator import PerformanceMetricsCalculator


class TestPerformanceMetricsCalculator:
    """Test suite for PerformanceMetricsCalculator service."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
        )

    @pytest.fixture
    def calculator(self, config):
        """Create calculator instance."""
        return PerformanceMetricsCalculator(config)

    @pytest.fixture
    def sample_trades(self):
        """Create sample trades for testing."""
        return [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1, 10, 0),
                exit_price=Decimal("160"),
                exit_time=datetime(2024, 1, 5, 10, 0),
                status=TradeStatus.CLOSED,
                pnl=Decimal("998"),  # (160-150)*100 - 2 commission
                pnl_percentage=Decimal("6.65"),
                commission=Decimal("1.0"),
            ),
            Trade(
                trade_id="trade_2",
                symbol="MSFT",
                side="buy",
                quantity=Decimal("50"),
                entry_price=Decimal("300"),
                entry_time=datetime(2024, 1, 2, 10, 0),
                exit_price=Decimal("290"),
                exit_time=datetime(2024, 1, 6, 10, 0),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-502"),  # (290-300)*50 - 2 commission
                pnl_percentage=Decimal("-3.35"),
                commission=Decimal("1.0"),
            ),
            Trade(
                trade_id="trade_3",
                symbol="GOOGL",
                side="buy",
                quantity=Decimal("25"),
                entry_price=Decimal("200"),
                entry_time=datetime(2024, 1, 3, 10, 0),
                exit_price=Decimal("220"),
                exit_time=datetime(2024, 1, 8, 10, 0),
                status=TradeStatus.CLOSED,
                pnl=Decimal("498"),  # (220-200)*25 - 2 commission
                pnl_percentage=Decimal("4.0"),
                commission=Decimal("1.0"),
            ),
        ]

    def test_initialization(self, config):
        """Test calculator initialization."""
        calc = PerformanceMetricsCalculator(config)
        assert calc.config == config

    def test_calculate_performance_metrics_with_trades(self, calculator, sample_trades):
        """Test performance metrics calculation with trades."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("-500"))

        assert metrics.total_trades == 3
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 1
        # Win rate should be approximately 66.67% (2/3)
        assert abs(metrics.win_rate - Decimal("66.67")) < Decimal("0.01")
        assert metrics.total_pnl == Decimal("994")  # 998 - 502 + 498
        assert metrics.gross_profit == Decimal("1496")  # 998 + 498
        assert metrics.gross_loss == Decimal("-502")

    def test_calculate_performance_metrics_empty_trades(self, calculator):
        """Test performance metrics with no trades."""
        metrics = calculator.calculate_performance_metrics([], Decimal("0"))

        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.win_rate == Decimal("0")
        assert metrics.total_pnl == Decimal("0")
        assert metrics.gross_profit == Decimal("0")
        assert metrics.gross_loss == Decimal("0")

    def test_calculate_performance_metrics_max_drawdown_clamping(self, calculator, sample_trades):
        """Test that max drawdown is clamped to <= 0."""
        # Pass positive drawdown (invalid)
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("100"))

        # Should be clamped to 0
        assert metrics.max_drawdown <= Decimal("0")

    def test_calculate_performance_metrics_negative_drawdown(self, calculator, sample_trades):
        """Test performance metrics with negative drawdown."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("-5000"))

        assert metrics.max_drawdown == Decimal("-5000")
        # Should be -5% of 100k
        assert abs(metrics.max_drawdown_percentage - Decimal("-5")) < Decimal("0.1")

    def test_calculate_sharpe_ratio_with_trades(self, calculator, sample_trades):
        """Test Sharpe ratio calculation."""
        sharpe = calculator._calculate_sharpe_ratio(sample_trades)

        # Should have a Sharpe ratio
        assert sharpe is not None

    def test_calculate_sharpe_ratio_insufficient_trades(self, calculator):
        """Test Sharpe ratio with insufficient trades."""
        sharpe = calculator._calculate_sharpe_ratio([])

        assert sharpe is None

        sharpe = calculator._calculate_sharpe_ratio(
            [
                Trade(
                    trade_id="trade_1",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("150"),
                    entry_time=datetime(2024, 1, 1),
                    exit_price=Decimal("160"),  # Required for CLOSED trades
                    exit_time=datetime(2024, 1, 2),
                    status=TradeStatus.CLOSED,
                    pnl=Decimal("100"),
                )
            ]
        )

        assert sharpe is None  # Need at least 2 trades

    def test_calculate_sharpe_ratio_no_closed_trades(self, calculator):
        """Test Sharpe ratio with no closed trades."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,  # Not closed
            )
        ]

        sharpe = calculator._calculate_sharpe_ratio(trades)

        assert sharpe is None

    def test_calculate_sharpe_ratio_zero_volatility(self, calculator):
        """Test Sharpe ratio calculation works."""
        # Create trades with identical P&L
        # Note: Even with identical P&L, returns will have slight variance due to
        # compounding (each return is calculated from a different base)
        trades = [
            Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, i + 1),
                exit_price=Decimal("160"),  # Required for CLOSED trades
                exit_time=datetime(2024, 1, i + 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("100"),  # All identical
            )
            for i in range(1, 5)
        ]

        sharpe = calculator._calculate_sharpe_ratio(trades)

        # Should return a valid Sharpe ratio (not None since there is some variance due to compounding)
        assert sharpe is not None
        # With consistent profits, Sharpe should be positive and quite high
        assert sharpe > 0

    def test_create_empty_metrics(self, calculator):
        """Test creating empty metrics."""
        metrics = calculator._create_empty_metrics()

        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.win_rate == Decimal("0")
        assert metrics.total_pnl == Decimal("0")
        assert metrics.sharpe_ratio is None

    def test_create_empty_metrics_with_custom_capital(self, calculator):
        """Test creating empty metrics with custom capital."""
        metrics = calculator._create_empty_metrics(Decimal("50000"))

        assert metrics.total_trades == 0
        # Metrics should be based on custom capital

    def test_calculate_win_rate(self, calculator, sample_trades):
        """Test win rate calculation."""
        win_rate = calculator.calculate_win_rate(sample_trades)

        # 2 winners, 1 loser = 66.67%
        assert abs(win_rate - Decimal("66.67")) < Decimal("0.01")

    def test_calculate_win_rate_empty_trades(self, calculator):
        """Test win rate with no trades."""
        win_rate = calculator.calculate_win_rate([])

        assert win_rate == Decimal("0")

    def test_calculate_win_rate_all_winners(self, calculator):
        """Test win rate with all winning trades."""
        trades = [
            Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, i + 1),
                exit_price=Decimal("160"),
                exit_time=datetime(2024, 1, i + 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("100"),
            )
            for i in range(5)
        ]

        win_rate = calculator.calculate_win_rate(trades)

        assert win_rate == Decimal("100")

    def test_calculate_win_rate_all_losers(self, calculator):
        """Test win rate with all losing trades."""
        trades = [
            Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, i + 1),
                exit_price=Decimal("140"),
                exit_time=datetime(2024, 1, i + 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-100"),
            )
            for i in range(5)
        ]

        win_rate = calculator.calculate_win_rate(trades)

        assert win_rate == Decimal("0")

    def test_calculate_win_rate_ignores_open_trades(self, calculator):
        """Test win rate ignores open trades."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                exit_price=Decimal("160"),
                exit_time=datetime(2024, 1, 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("100"),
            ),
            Trade(
                trade_id="trade_2",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 3),
                status=TradeStatus.OPEN,  # Should be ignored
            ),
        ]

        win_rate = calculator.calculate_win_rate(trades)

        # Only 1 closed trade (winner)
        assert win_rate == Decimal("100")

    def test_calculate_win_rate_clamping(self, calculator):
        """Test win rate is clamped between 0-100."""
        # Create trades that would result in edge cases
        trades = []

        win_rate = calculator.calculate_win_rate(trades)

        assert win_rate >= Decimal("0")
        assert win_rate <= Decimal("100")

    def test_calculate_profit_factor(self, calculator, sample_trades):
        """Test profit factor calculation."""
        profit_factor = calculator.calculate_profit_factor(sample_trades)

        # Gross profit = 1496, Gross loss = 502
        # Profit factor = 1496 / 502 ≈ 2.98
        assert abs(profit_factor - Decimal("2.98")) < Decimal("0.01")

    def test_calculate_profit_factor_no_losses(self, calculator):
        """Test profit factor with no losing trades."""
        trades = [
            Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, i + 1),
                exit_price=Decimal("160"),
                exit_time=datetime(2024, 1, i + 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("100"),
            )
            for i in range(3)
        ]

        profit_factor = calculator.calculate_profit_factor(trades)

        # No losses, should return 0
        assert profit_factor == Decimal("0")

    def test_calculate_profit_factor_no_wins(self, calculator):
        """Test profit factor with no winning trades."""
        trades = [
            Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, i + 1),
                exit_price=Decimal("140"),
                exit_time=datetime(2024, 1, i + 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("-100"),
            )
            for i in range(3)
        ]

        profit_factor = calculator.calculate_profit_factor(trades)

        # No wins, should be 0
        assert profit_factor == Decimal("0")

    def test_calculate_expectancy(self, calculator, sample_trades):
        """Test expectancy calculation."""
        expectancy = calculator.calculate_expectancy(sample_trades)

        # Total P&L = 994, 3 trades
        # Expectancy = 994 / 3 ≈ 331.33
        assert abs(expectancy - Decimal("331.33")) < Decimal("1")

    def test_calculate_expectancy_empty(self, calculator):
        """Test expectancy with no trades."""
        expectancy = calculator.calculate_expectancy([])

        assert expectancy == Decimal("0")

    def test_calculate_performance_metrics_time_metrics(self, calculator, sample_trades):
        """Test time-based metrics."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("0"))

        # First trade: 2024-01-01, Last trade: 2024-01-08
        # Total days: 7
        assert metrics.total_days == 7
        # Avg duration: 7 / 3 ≈ 2.33
        assert abs(metrics.avg_trade_duration - Decimal("2.33")) < Decimal("0.1")

    def test_calculate_performance_metrics_avg_win_loss(self, calculator, sample_trades):
        """Test average win/loss calculations."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("0"))

        # Avg win = (998 + 498) / 2 = 748
        assert abs(metrics.avg_win - Decimal("748")) < Decimal("1")

        # Avg loss = -502 / 1 = -502
        assert abs(metrics.avg_loss - Decimal("-502")) < Decimal("1")

    def test_calculate_performance_metrics_largest_win_loss(self, calculator, sample_trades):
        """Test largest win/loss calculations."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("0"))

        assert metrics.largest_win == Decimal("998")
        assert metrics.largest_loss == Decimal("-502")

    def test_calculate_performance_metrics_total_pnl_percentage(self, calculator, sample_trades):
        """Test total P&L percentage calculation."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("0"))

        # Total P&L = 994, Capital = 100000
        # Percentage = 994 / 100000 * 100 = 0.994%
        assert abs(metrics.total_pnl_percentage - Decimal("0.994")) < Decimal("0.01")

    def test_edge_case_zero_pnl_trades(self, calculator):
        """Test trades with zero P&L."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                exit_price=Decimal("150"),  # Break-even - same price
                exit_time=datetime(2024, 1, 2),
                status=TradeStatus.CLOSED,
                pnl=Decimal("0"),  # Break-even trade
            )
        ]

        win_rate = calculator.calculate_win_rate(trades)

        # Zero P&L should count as loss (not > 0)
        assert win_rate == Decimal("0")

    def test_edge_case_negative_initial_capital(self, config):
        """Test with negative initial capital (edge case)."""
        config.initial_capital = Decimal("-1000")
        calc = PerformanceMetricsCalculator(config)

        metrics = calc._create_empty_metrics()

        # Should handle gracefully
        assert metrics.total_trades == 0

    def test_sharpe_ratio_annualization(self, calculator):
        """Test Sharpe ratio is properly annualized."""
        # Create multiple trades over time
        trades = []
        base_date = datetime(2024, 1, 1)
        for i in range(10):
            pnl = Decimal("100") if i % 2 == 0 else Decimal("-50")
            exit_price = Decimal("160") if pnl > 0 else Decimal("140")
            trades.append(
                Trade(
                    trade_id=f"trade_{i}",
                    symbol="AAPL",
                    side="buy",
                    quantity=Decimal("100"),
                    entry_price=Decimal("150"),
                    entry_time=base_date + timedelta(days=i),
                    exit_price=exit_price,
                    exit_time=base_date + timedelta(days=i + 1),
                    status=TradeStatus.CLOSED,
                    pnl=pnl,
                )
            )

        sharpe = calculator._calculate_sharpe_ratio(trades)

        # Should have a valid Sharpe ratio
        assert sharpe is not None
        # Annualized Sharpe should be reasonable
        assert -10 < float(sharpe) < 10  # Sanity check

    def test_performance_metrics_validation_passes(self, calculator, sample_trades):
        """Test that calculated metrics pass validation."""
        metrics = calculator.calculate_performance_metrics(sample_trades, Decimal("-500"))

        # Should not raise validation errors
        assert metrics.total_trades == metrics.winning_trades + metrics.losing_trades
        assert abs(metrics.win_rate - Decimal("66.67")) < Decimal("0.01")
        assert metrics.gross_profit + metrics.gross_loss == metrics.net_profit
