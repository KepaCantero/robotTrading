"""
Tests for backtesting engine functionality.

This module tests the SimpleBacktester engine with various scenarios
including trending markets, ranging markets, and edge cases.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import (BacktestConfig, BacktestResult,
                                    PerformanceMetrics, Trade, TradeStatus)
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from tests.fixtures.historical_data import (
    create_contradictory_signals, create_single_day_market_data,
    create_single_day_signals, create_spy_2020_ranging_market_data,
    create_spy_2020_ranging_signals, create_spy_2020_trending_market_data,
    create_spy_2020_trending_signals)


class TestSimpleBacktester:
    """Test the SimpleBacktester engine."""

    @pytest.fixture
    def default_config(self):
        """Default backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
            stop_loss_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("10.0"),
        )

    @pytest.fixture
    def backtester(self, default_config):
        """Create a SimpleBacktester instance."""
        return SimpleBacktester(default_config)

    def test_backtester_initialization(self, default_config):
        """Test backtester initialization."""
        backtester = SimpleBacktester(default_config)

        assert backtester.config == default_config
        assert backtester.capital == default_config.initial_capital
        assert len(backtester.positions) == 0
        assert len(backtester.trades) == 0
        assert len(backtester.equity_curve) == 0
        assert backtester.max_drawdown == Decimal("0")
        assert backtester.peak_equity == default_config.initial_capital

    def test_empty_market_data_raises_error(self, backtester):
        """Test that empty market data raises an error."""
        with pytest.raises(ValueError, match="No market data available"):
            backtester.run_backtest([], [])

    def test_single_day_backtest(self, backtester):
        """Test backtest with single day of data."""
        market_data = create_single_day_market_data()
        signals = create_single_day_signals()

        result = backtester.run_backtest(market_data, signals)

        assert isinstance(result, BacktestResult)
        assert result.start_date == market_data[0].timestamp
        assert result.end_date == market_data[0].timestamp
        assert result.final_capital > 0
        assert len(result.trades) >= 0
        assert result.performance.total_trades >= 0

    def test_trending_market_backtest(self, backtester):
        """Test backtest with trending market data."""
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()

        result = backtester.run_backtest(market_data, signals)

        assert isinstance(result, BacktestResult)
        assert result.start_date == market_data[0].timestamp
        assert result.end_date == market_data[-1].timestamp
        assert result.final_capital > 0
        assert len(result.trades) > 0

        # In a trending market, we should have some trades
        assert result.performance.total_trades > 0

    def test_ranging_market_backtest(self, backtester):
        """Test backtest with ranging market data."""
        market_data = create_spy_2020_ranging_market_data()
        signals = create_spy_2020_ranging_signals()

        result = backtester.run_backtest(market_data, signals)

        assert isinstance(result, BacktestResult)
        assert result.start_date == market_data[0].timestamp
        assert result.end_date == market_data[-1].timestamp
        assert result.final_capital > 0
        assert len(result.trades) > 0

    def test_contradictory_signals_handling(self, backtester):
        """Test handling of contradictory signals."""
        market_data = create_single_day_market_data()
        signals = create_contradictory_signals()

        result = backtester.run_backtest(market_data, signals)

        assert isinstance(result, BacktestResult)
        assert len(result.trades) > 0

        # Should handle contradictory signals gracefully
        assert result.final_capital > 0

    def test_reproducibility(self, default_config):
        """Test that same inputs produce same outputs."""
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()

        # Run backtest twice
        backtester1 = SimpleBacktester(default_config)
        result1 = backtester1.run_backtest(market_data, signals)

        backtester2 = SimpleBacktester(default_config)
        result2 = backtester2.run_backtest(market_data, signals)

        # Results should be identical
        assert result1.final_capital == result2.final_capital
        assert result1.total_return == result2.total_return
        assert len(result1.trades) == len(result2.trades)
        assert result1.performance.total_trades == result2.performance.total_trades

    def test_date_filtering(self, backtester):
        """Test backtest with date filtering."""
        market_data = create_spy_2020_trending_market_data()
        signals = create_spy_2020_trending_signals()

        # Filter to first quarter
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 3, 31)

        result = backtester.run_backtest(market_data, signals, start_date, end_date)

        assert result.start_date >= start_date
        assert result.end_date <= end_date
        assert result.final_capital > 0

    def test_slippage_application(self, default_config):
        """Test that slippage is applied correctly."""
        # Create config with high slippage for testing
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("0"),
            slippage_percentage=Decimal("1.0"),  # 1% slippage
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )
        backtester = SimpleBacktester(config)
        market_data = create_single_day_market_data()
        signals = create_single_day_signals()

        result = backtester.run_backtest(market_data, signals)

        # Check that slippage was applied
        buy_trades = [t for t in result.trades if t.side == "buy"]
        assert len(buy_trades) > 0, "No buy trades found"

        for trade in buy_trades:
            assert trade.slippage > 0, f"Expected slippage > 0, got {trade.slippage}"

    def test_commission_calculation(self, default_config):
        """Test that commission is calculated correctly."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("5.0"),  # $5 per trade
            slippage_percentage=Decimal("0"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )
        backtester = SimpleBacktester(config)
        market_data = create_single_day_market_data()
        signals = create_single_day_signals()

        result = backtester.run_backtest(market_data, signals)

        # Check that commission was applied
        total_commission = sum(trade.commission for trade in result.trades)
        assert total_commission > 0

    def test_position_size_calculation(self, default_config):
        """Test position size calculation based on signal confidence."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("0"),
            slippage_percentage=Decimal("0"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.2"),  # 20% max position
        )
        backtester = SimpleBacktester(config)

        # Test position size calculation
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("100.0"),
            volume=Decimal("100"),
            timestamp=datetime.utcnow() - timedelta(seconds=1),
            metadata={"test": True},
        )
        position_size = backtester._calculate_position_size(signal, Decimal("100.0"))

        # Position should be based on confidence and max position size
        expected_max_position_value = config.initial_capital * config.max_position_size
        expected_position_value = expected_max_position_value * Decimal(
            str(signal.confidence / 100.0)
        )
        expected_position_size = expected_position_value / Decimal("100.0")

        assert position_size > 0
        assert position_size <= expected_position_size


class TestBacktestModels:
    """Test backtesting models."""

    def test_trade_model_validation(self):
        """Test Trade model validation."""
        # Valid trade
        trade = Trade(
            trade_id="test-1",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.0"),
            entry_time=datetime.utcnow(),
            status=TradeStatus.OPEN,
        )
        assert trade.trade_id == "test-1"
        assert trade.symbol == "AAPL"
        assert trade.side == "buy"
        assert trade.status == TradeStatus.OPEN

    def test_trade_invalid_side(self):
        """Test Trade model with invalid side."""
        with pytest.raises(ValueError, match="Trade side must be 'buy' or 'sell'"):
            Trade(
                trade_id="test-1",
                symbol="AAPL",
                side="invalid",
                quantity=Decimal("100"),
                entry_price=Decimal("150.0"),
                entry_time=datetime.utcnow(),
            )

    def test_trade_closed_without_exit_price(self):
        """Test Trade model validation for closed trades."""
        with pytest.raises(ValueError, match="Closed trade must have exit price"):
            Trade(
                trade_id="test-1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150.0"),
                entry_time=datetime.utcnow(),
                status=TradeStatus.CLOSED,
            )

    def test_performance_metrics_validation(self):
        """Test PerformanceMetrics model validation."""
        # Valid metrics
        metrics = PerformanceMetrics(
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=Decimal("60.0"),
            total_pnl=Decimal("1000"),
            total_pnl_percentage=Decimal("1.0"),
            gross_profit=Decimal("1500"),
            gross_loss=Decimal("-500"),
            net_profit=Decimal("1000"),
            max_drawdown=Decimal("-5.0"),
            max_drawdown_percentage=Decimal("-5.0"),
            sharpe_ratio=Decimal("1.5"),
            avg_win=Decimal("250"),
            avg_loss=Decimal("-125"),
            largest_win=Decimal("500"),
            largest_loss=Decimal("-200"),
            total_days=252,
            avg_trade_duration=Decimal("25.2"),
        )
        assert metrics.total_trades == 10
        assert metrics.winning_trades == 6
        assert metrics.losing_trades == 4
        assert metrics.win_rate == Decimal("60.0")

    def test_performance_metrics_inconsistent_trades(self):
        """Test PerformanceMetrics with inconsistent trade counts."""
        with pytest.raises(
            ValueError, match="Total trades must equal winning \\+ losing trades"
        ):
            PerformanceMetrics(
                total_trades=10,
                winning_trades=6,
                losing_trades=3,  # Should be 4
                win_rate=Decimal("60.0"),
                total_pnl=Decimal("1000"),
                total_pnl_percentage=Decimal("1.0"),
                gross_profit=Decimal("1500"),
                gross_loss=Decimal("-500"),
                net_profit=Decimal("1000"),
                max_drawdown=Decimal("-5.0"),
                max_drawdown_percentage=Decimal("-5.0"),
                sharpe_ratio=Decimal("1.5"),
                avg_win=Decimal("250"),
                avg_loss=Decimal("-125"),
                largest_win=Decimal("500"),
                largest_loss=Decimal("-200"),
                total_days=252,
                avg_trade_duration=Decimal("25.2"),
            )

    def test_backtest_config_validation(self):
        """Test BacktestConfig model validation."""
        # Valid config
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )
        assert config.initial_capital == Decimal("100000")
        assert config.commission_per_trade == Decimal("1.0")
        assert config.slippage_percentage == Decimal("0.1")

    def test_backtest_config_high_slippage(self):
        """Test BacktestConfig with high slippage."""
        with pytest.raises(ValueError, match="Slippage percentage too high"):
            BacktestConfig(
                initial_capital=Decimal("100000"),
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("10.0"),  # Too high
                risk_free_rate=Decimal("0.02"),
                max_position_size=Decimal("0.1"),
            )

    def test_backtest_config_stop_loss_greater_than_take_profit(self):
        """Test BacktestConfig with stop loss greater than take profit."""
        with pytest.raises(
            ValueError,
            match="Stop loss percentage must be less than take profit percentage",
        ):
            BacktestConfig(
                initial_capital=Decimal("100000"),
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.1"),
                risk_free_rate=Decimal("0.02"),
                max_position_size=Decimal("0.1"),
                stop_loss_percentage=Decimal("10.0"),
                take_profit_percentage=Decimal("5.0"),  # Less than stop loss
            )


class TestBacktestEdgeCases:
    """Test edge cases for backtesting."""

    @pytest.fixture
    def default_config(self):
        """Default backtest configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
            stop_loss_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("10.0"),
        )

    def test_zero_initial_capital(self):
        """Test backtest with zero initial capital."""
        config = BacktestConfig(
            initial_capital=Decimal("0.01"),  # Very small capital
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )
        backtester = SimpleBacktester(config)
        market_data = create_single_day_market_data()
        signals = create_single_day_signals()

        result = backtester.run_backtest(market_data, signals)

        # Should handle small capital gracefully
        assert result.final_capital >= 0
        assert len(result.trades) >= 0

    def test_very_high_commission(self):
        """Test backtest with very high commission."""
        config = BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1000.0"),  # Very high commission
            slippage_percentage=Decimal("0.1"),
            risk_free_rate=Decimal("0.02"),
            max_position_size=Decimal("0.1"),
        )
        backtester = SimpleBacktester(config)
        market_data = create_single_day_market_data()
        signals = create_single_day_signals()

        result = backtester.run_backtest(market_data, signals)

        # Should handle high commission gracefully
        assert result.final_capital >= 0
        assert len(result.trades) >= 0

    def test_no_signals(self, default_config):
        """Test backtest with no signals."""
        backtester = SimpleBacktester(default_config)
        market_data = create_spy_2020_trending_market_data()
        signals = []  # No signals

        result = backtester.run_backtest(market_data, signals)

        # Should complete without errors
        assert result.final_capital == default_config.initial_capital
        assert len(result.trades) == 0
        assert result.performance.total_trades == 0

    def test_signals_without_matching_market_data(self, default_config):
        """Test backtest with signals for symbols not in market data."""
        backtester = SimpleBacktester(default_config)
        market_data = create_single_day_market_data()  # SPY data

        # Signal for different symbol
        signal = Signal(
            symbol="TEST_SYMBOL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("100.0"),
            volume=Decimal("100"),
            timestamp=datetime.utcnow() - timedelta(seconds=1),
            metadata={"test": True},
        )
        result = backtester.run_backtest(market_data, [signal])

        # Should handle mismatched symbols gracefully
        assert result.final_capital == default_config.initial_capital
        assert len(result.trades) == 0
