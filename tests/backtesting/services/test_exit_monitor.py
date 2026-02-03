"""
Tests for ExitConditionMonitor service.

Tests stop-loss, take-profit monitoring, and exit condition checks.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.exit_monitor import ExitConditionMonitor
from app.backtesting.services.position_manager import PositionManager


class MockMarketData:
    """Mock market data for testing."""

    def __init__(self, symbol, close, high=None, low=None, timestamp=None):
        self.symbol = symbol
        self.close = Decimal(str(close))
        self.high = Decimal(str(high)) if high is not None else None
        self.low = Decimal(str(low)) if low is not None else None
        self.timestamp = timestamp or datetime(2024, 1, 1, 10, 0)


class TestExitConditionMonitor:
    """Test suite for ExitConditionMonitor service."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            stop_loss_percentage=Decimal("10"),  # 10% stop loss
            take_profit_percentage=Decimal("20"),  # 20% take profit
            commission_per_trade=Decimal("1.0"),
        )

    @pytest.fixture
    def position_manager(self):
        """Create position manager."""
        pm = PositionManager()
        pm.update_position("AAPL", Decimal("100"))
        return pm

    @pytest.fixture
    def exit_monitor(self, config, position_manager):
        """Create exit monitor instance."""

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        return ExitConditionMonitor(config, position_manager, mock_slippage)

    @pytest.fixture
    def sample_trades(self):
        """Create sample trades."""
        return [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
                commission=Decimal("1.0"),
            )
        ]

    def test_initialization(self, config, position_manager):
        """Test monitor initialization."""

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(config, position_manager, mock_slippage)

        assert monitor.config == config
        assert monitor.position_manager == position_manager

    def test_calculate_stop_loss_price(self, exit_monitor):
        """Test stop loss price calculation."""
        entry_price = Decimal("150")

        stop_loss = exit_monitor.calculate_stop_loss_price(entry_price)

        # 150 * (1 - 0.10) = 135
        assert stop_loss == Decimal("135")

    def test_calculate_stop_loss_price_none(self):
        """Test stop loss price when not configured."""
        config = BacktestConfig(stop_loss_percentage=None)
        pm = PositionManager()

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(config, pm, mock_slippage)

        stop_loss = monitor.calculate_stop_loss_price(Decimal("150"))

        assert stop_loss is None

    def test_calculate_take_profit_price(self, exit_monitor):
        """Test take profit price calculation."""
        entry_price = Decimal("150")

        take_profit = exit_monitor.calculate_take_profit_price(entry_price)

        # 150 * (1 + 0.20) = 180
        assert take_profit == Decimal("180")

    def test_calculate_take_profit_price_none(self):
        """Test take profit price when not configured."""
        config = BacktestConfig(take_profit_percentage=None)
        pm = PositionManager()

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(config, pm, mock_slippage)

        take_profit = monitor.calculate_take_profit_price(Decimal("150"))

        assert take_profit is None

    def test_is_stop_loss_hit_with_low(self, exit_monitor):
        """Test stop loss detection using low price."""
        market_data = MockMarketData("AAPL", close=140, low=134, high=145)
        stop_loss_price = Decimal("135")

        is_hit, execution_price = exit_monitor.is_stop_loss_hit(market_data, stop_loss_price)

        assert is_hit is True
        assert execution_price == Decimal("135")  # Stop loss price

    def test_is_stop_loss_hit_with_close(self, exit_monitor):
        """Test stop loss detection using close price (no low)."""
        market_data = MockMarketData("AAPL", close=134, low=None, high=145)
        stop_loss_price = Decimal("135")

        is_hit, execution_price = exit_monitor.is_stop_loss_hit(market_data, stop_loss_price)

        assert is_hit is True
        assert execution_price == Decimal("134")  # Close price

    def test_is_stop_loss_not_hit(self, exit_monitor):
        """Test stop loss not hit."""
        market_data = MockMarketData("AAPL", close=140, low=138, high=145)
        stop_loss_price = Decimal("135")

        is_hit, execution_price = exit_monitor.is_stop_loss_hit(market_data, stop_loss_price)

        assert is_hit is False
        assert execution_price is None

    def test_is_take_profit_hit_with_high(self, exit_monitor):
        """Test take profit detection using high price."""
        market_data = MockMarketData("AAPL", close=170, low=135, high=181)
        take_profit_price = Decimal("180")

        is_hit, execution_price = exit_monitor.is_take_profit_hit(market_data, take_profit_price)

        assert is_hit is True
        assert execution_price == Decimal("180")  # Take profit price

    def test_is_take_profit_hit_with_close(self, exit_monitor):
        """Test take profit detection using close price (no high)."""
        market_data = MockMarketData("AAPL", close=181, low=None, high=None)
        take_profit_price = Decimal("180")

        is_hit, execution_price = exit_monitor.is_take_profit_hit(market_data, take_profit_price)

        assert is_hit is True
        assert execution_price == Decimal("181")  # Close price

    def test_is_take_profit_not_hit(self, exit_monitor):
        """Test take profit not hit."""
        market_data = MockMarketData("AAPL", close=170, low=135, high=175)
        take_profit_price = Decimal("180")

        is_hit, execution_price = exit_monitor.is_take_profit_hit(market_data, take_profit_price)

        assert is_hit is False
        assert execution_price is None

    def test_check_exit_conditions_stop_loss_triggered(self, exit_monitor, sample_trades):
        """Test stop loss exit condition triggered."""
        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is True
        assert len(close_called) == 1
        assert close_called[0][0] == "AAPL"
        assert close_called[0][1] == "stop_loss"
        assert close_called[0][2] == Decimal("135")  # Stop loss price

    def test_check_exit_conditions_take_profit_triggered(self, exit_monitor, sample_trades):
        """Test take profit exit condition triggered."""
        # High triggers TP (181 >= 180), but low is above SL (140 > 135)
        market_data = MockMarketData("AAPL", close=170, low=140, high=181)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is True
        assert len(close_called) == 1
        assert close_called[0][0] == "AAPL"
        assert close_called[0][1] == "take_profit"
        assert close_called[0][2] == Decimal("180")  # Take profit price

    def test_check_exit_conditions_both_triggered_pessimistic(self, exit_monitor, sample_trades):
        """Test both SL and TP triggered - stop loss takes priority (pessimistic)."""
        # Low triggers SL, high triggers TP
        market_data = MockMarketData("AAPL", close=150, low=130, high=185)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is True
        assert len(close_called) == 1
        # Pessimistic execution: stop loss takes priority
        assert close_called[0][1] == "stop_loss"
        assert close_called[0][2] <= Decimal("135")  # Stop loss price or lower

    def test_check_exit_conditions_no_trigger(self, exit_monitor, sample_trades):
        """Test no exit conditions triggered."""
        market_data = MockMarketData("AAPL", close=150, low=145, high=155)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is False
        assert len(close_called) == 0

    def test_check_exit_conditions_no_position(self, exit_monitor, sample_trades):
        """Test exit check with no position."""
        # Create position manager with no position
        pm = PositionManager()

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(exit_monitor.config, pm, mock_slippage)

        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is False
        assert len(close_called) == 0

    def test_check_exit_conditions_zero_position(self, exit_monitor, sample_trades):
        """Test exit check with zero position."""
        # Set position to zero
        exit_monitor.position_manager.close_position("AAPL")

        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, sample_trades, mock_close)

        assert result is False
        assert len(close_called) == 0

    def test_check_exit_conditions_no_open_trades(self, exit_monitor):
        """Test exit check with no open trades."""
        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, [], mock_close)

        assert result is False
        assert len(close_called) == 0

    def test_check_exit_conditions_uses_most_recent_trade(self, exit_monitor):
        """Test that exit conditions use the most recent trade's entry price."""
        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("100"),  # Old trade
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            ),
            Trade(
                trade_id="trade_2",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),  # Recent trade
                entry_time=datetime(2024, 1, 2),
                status=TradeStatus.OPEN,
            ),
        ]

        # Stop loss should be based on $150 (most recent)
        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_exit_conditions(market_data, trades, mock_close)

        # Should trigger at $135 (10% below $150, not $90)
        assert result is True
        assert close_called[0][2] == Decimal("135")

    def test_check_exit_conditions_no_stop_loss_config(self):
        """Test exit check when stop loss not configured."""
        config = BacktestConfig(
            stop_loss_percentage=None, take_profit_percentage=Decimal("20")
        )
        pm = PositionManager()
        pm.update_position("AAPL", Decimal("100"))

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(config, pm, mock_slippage)

        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            )
        ]

        # Price drops but no SL configured
        market_data = MockMarketData("AAPL", close=140, low=134, high=145)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = monitor.check_exit_conditions(market_data, trades, mock_close)

        # Should not trigger (no SL configured)
        assert result is False

    def test_check_exit_conditions_no_take_profit_config(self):
        """Test exit check when take profit not configured."""
        config = BacktestConfig(
            stop_loss_percentage=Decimal("10"), take_profit_percentage=None
        )
        pm = PositionManager()
        pm.update_position("AAPL", Decimal("100"))

        def mock_slippage(price, is_buy, slippage_pct=None):
            return price

        monitor = ExitConditionMonitor(config, pm, mock_slippage)

        trades = [
            Trade(
                trade_id="trade_1",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150"),
                entry_time=datetime(2024, 1, 1),
                status=TradeStatus.OPEN,
            )
        ]

        # Price rises but no TP configured, and doesn't trigger SL either (low=145 > 135)
        market_data = MockMarketData("AAPL", close=170, low=145, high=181)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = monitor.check_exit_conditions(market_data, trades, mock_close)

        # Should not trigger (no TP configured)
        assert result is False

    def test_check_all_symbols_exit_conditions(self, exit_monitor, sample_trades):
        """Test check_all_symbols_exit_conditions (placeholder)."""
        market_data = MockMarketData("AAPL", close=150, low=145, high=155)

        close_called = []

        def mock_close(symbol, timestamp, reason, price):
            close_called.append((symbol, reason, price))

        result = exit_monitor.check_all_symbols_exit_conditions(
            market_data, sample_trades, mock_close
        )

        # Currently returns 0 (placeholder implementation)
        assert result == 0
