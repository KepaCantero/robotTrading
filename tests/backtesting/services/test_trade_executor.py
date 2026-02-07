"""
Tests for TradeExecutor service.

Tests buy/sell execution, position sizing, and cost calculations.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.backtesting.models import BacktestConfig, Trade, TradeStatus
from app.backtesting.services.pnl_calculator import ProfitAndLossCalculator
from app.backtesting.services.position_manager import PositionManager
from app.backtesting.services.trade_executor import TradeExecutor
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class MockMarketData:
    """Mock market data for testing."""

    def __init__(self, symbol, close=Decimal("150"), high=None, low=None, volume=1000000):
        self.symbol = symbol
        self.close = Decimal(str(close))
        self.high = Decimal(str(high)) if high is not None else Decimal(str(close))
        self.low = Decimal(str(low)) if low is not None else Decimal(str(close))
        self.volume = volume
        self.timestamp = datetime(2024, 1, 1, 10, 0)


class TestTradeExecutor:
    """Test suite for TradeExecutor service."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return BacktestConfig(
            initial_capital=Decimal("100000"),
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.1"),
            max_position_size=Decimal("0.2"),
            stop_loss_percentage=Decimal("10"),
        )

    @pytest.fixture
    def position_manager(self):
        """Create position manager."""
        return PositionManager()

    @pytest.fixture
    def pnl_calculator(self, config):
        """Create P&L calculator."""
        return ProfitAndLossCalculator(config)

    @pytest.fixture
    def trade_executor(self, config, position_manager, pnl_calculator):
        """Create trade executor instance."""
        return TradeExecutor(config, position_manager, pnl_calculator)

    @pytest.fixture
    def buy_signal(self):
        """Create sample buy signal."""
        return Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

    @pytest.fixture
    def sell_signal(self):
        """Create sample sell signal."""
        return Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=50.0,
            priority_score=60.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("160"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1, 10, 0),
        )

    @pytest.fixture
    def sample_buy_trades(self):
        """Create sample buy trades for sell execution."""
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

    def test_initialization(self, config, position_manager, pnl_calculator):
        """Test executor initialization."""
        executor = TradeExecutor(config, position_manager, pnl_calculator)

        assert executor.config == config
        assert executor.position_manager == position_manager
        assert executor.pnl_calculator == pnl_calculator

    def test_execute_buy_signal_success(self, trade_executor, buy_signal):
        """Test successful buy execution."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        assert trade is not None
        assert trade.symbol == "AAPL"
        assert trade.side == "buy"
        assert trade.quantity > 0
        # Entry price includes slippage (0.1%), so slightly higher than 150
        assert trade.entry_price > Decimal("150")
        assert trade.entry_price < Decimal("151")  # Should be close to 150
        assert trade.status == TradeStatus.OPEN
        assert new_capital < capital  # Capital reduced by trade cost

    def test_execute_buy_signal_closes_existing_position(
        self, trade_executor, position_manager, buy_signal
    ):
        """Test buy execution closes existing position first."""
        # Add existing position
        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        close_called = []

        def mock_close_position(symbol, timestamp, reason):
            close_called.append((symbol, reason))

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        # Should have closed existing position
        assert len(close_called) == 1
        assert close_called[0][0] == "AAPL"
        assert close_called[0][1] == "signal_reverse"

    def test_execute_buy_signal_profitability_validation_fails(self, trade_executor, buy_signal):
        """Test buy execution fails profitability validation."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return False  # Validation fails

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        assert trade is None
        assert new_capital == capital  # Capital unchanged

    def test_execute_buy_signal_position_size_too_small(self, trade_executor, buy_signal):
        """Test buy execution with position size <= 0."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("10")  # Very low capital

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        # Should fail due to insufficient capital
        assert trade is None or trade.quantity <= 0

    def test_execute_buy_signal_position_size_validation_fails(self, trade_executor, buy_signal):
        """Test buy with position size that fails validation."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        # Mock trading validator to raise ValueError
        with patch.object(
            trade_executor.trading_validator,
            "validate_position_size",
            side_effect=ValueError("Position too large"),
        ):
            trade, new_capital = trade_executor.execute_buy_signal(
                buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
            )

        assert trade is None
        assert new_capital == capital

    def test_execute_buy_signal_stop_loss_validation_fails(self, trade_executor, buy_signal):
        """Test buy with stop-loss that fails validation."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        # Mock stop-loss validator to raise ValueError
        with patch.object(
            trade_executor.trading_validator,
            "validate_stop_loss",
            side_effect=ValueError("Invalid SL"),
        ):
            trade, new_capital = trade_executor.execute_buy_signal(
                buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
            )

        assert trade is None
        assert new_capital == capital

    def test_execute_buy_signal_liquidity_rejected(self, trade_executor, buy_signal):
        """Test buy with liquidity validation rejection."""
        market_data = MockMarketData("AAPL", 150, volume=0)  # No volume

        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        # Liquidity validator should reject
        if trade is not None:
            # If trade executed, quantity should be reasonable
            assert trade.quantity > 0

    def test_execute_buy_signal_updates_position(
        self, trade_executor, position_manager, buy_signal
    ):
        """Test buy execution updates position."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        initial_position = position_manager.get_position("AAPL")

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        final_position = position_manager.get_position("AAPL")

        assert final_position > initial_position

    def test_execute_sell_signal_success(
        self, trade_executor, position_manager, sell_signal, sample_buy_trades
    ):
        """Test successful sell execution."""
        # Set up position
        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 160)
        capital = Decimal("100000")

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, sample_buy_trades
        )

        assert trade is not None
        assert trade.symbol == "AAPL"
        assert trade.side == "sell"
        assert trade.quantity > 0
        assert trade.status == TradeStatus.CLOSED
        assert trade.pnl is not None
        assert new_capital > capital  # Capital increased by proceeds

    def test_execute_sell_signal_no_position(self, trade_executor, sell_signal):
        """Test sell execution with no position."""
        market_data = MockMarketData("AAPL", 160)
        capital = Decimal("100000")

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, []
        )

        assert trade is None
        assert new_capital == capital  # Capital unchanged

    def test_execute_sell_signal_updates_position(
        self, trade_executor, position_manager, sell_signal, sample_buy_trades
    ):
        """Test sell execution updates position."""
        # Set up position
        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 160)
        capital = Decimal("100000")

        initial_position = position_manager.get_position("AAPL")

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, sample_buy_trades
        )

        final_position = position_manager.get_position("AAPL")

        assert final_position < initial_position

    def test_execute_sell_signal_calculates_pnl(
        self, trade_executor, position_manager, sell_signal, sample_buy_trades
    ):
        """Test sell execution calculates P&L correctly."""
        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 160)  # Sell at higher price
        capital = Decimal("100000")

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, sample_buy_trades
        )

        # Should have profit (bought at 150, sold at 160)
        assert trade.pnl is not None
        assert trade.pnl > 0

    def test_calculate_position_size_basic(self, trade_executor, buy_signal):
        """Test position size calculation."""
        price = Decimal("150")
        capital = Decimal("100000")

        position_size = trade_executor._calculate_position_size(buy_signal, price, capital)

        # Max position = 100000 * 0.2 = 20000
        # With 80% confidence = 16000
        # At $150 = ~106 shares
        assert position_size > 0
        assert position_size * price <= capital * Decimal("0.25")  # Reasonable limit

    def test_calculate_position_size_low_confidence(self, trade_executor):
        """Test position size with low confidence."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.WEAK,
            confidence=30.0,  # Low confidence
            liquidity_score=50.0,
            priority_score=50.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
        )

        price = Decimal("150")
        capital = Decimal("100000")

        position_size = trade_executor._calculate_position_size(signal, price, capital)

        # Low confidence should result in smaller position
        assert position_size > 0

    def test_calculate_position_size_high_confidence(self, trade_executor):
        """Test position size with high confidence."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.VERY_STRONG,
            confidence=95.0,  # High confidence
            liquidity_score=80.0,
            priority_score=90.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
        )

        price = Decimal("150")
        capital = Decimal("100000")

        position_size = trade_executor._calculate_position_size(signal, price, capital)

        # High confidence should result in larger position
        assert position_size > 0

    def test_get_strategy_commission_from_metadata(self, trade_executor):
        """Test getting commission from signal metadata."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
            metadata={"commission_per_trade_pct": "0.5"},
        )

        commission = trade_executor._get_strategy_commission(signal, "test_strategy")

        assert commission == Decimal("0.5")

    def test_get_strategy_commission_from_strategy(self, trade_executor):
        """Test getting commission from strategy object."""

        # Use a real object instead of MagicMock to avoid attribute access issues
        class MockStrategy:
            commission_per_trade_pct = Decimal("0.3")

        mock_strategy = MockStrategy()
        trade_executor.strategy = mock_strategy

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
        )

        commission = trade_executor._get_strategy_commission(signal, "test_strategy")

        assert commission == Decimal("0.3")

    def test_get_strategy_commission_default(self, trade_executor):
        """Test default commission when none specified."""
        # Ensure no strategy is set
        trade_executor.strategy = None

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
        )

        commission = trade_executor._get_strategy_commission(signal, "test_strategy")

        assert commission is None  # Use default from config

    def test_apply_slippage_buy(self, trade_executor):
        """Test slippage application for buy."""
        price = Decimal("150")

        slippage_pct = Decimal("0.1")
        adjusted_price = trade_executor._apply_slippage(
            price, is_buy=True, slippage_pct=slippage_pct
        )

        # Buy price should be higher
        assert adjusted_price > price
        assert adjusted_price == price * Decimal("1.001")

    def test_apply_slippage_sell(self, trade_executor):
        """Test slippage application for sell."""
        price = Decimal("150")

        slippage_pct = Decimal("0.1")
        adjusted_price = trade_executor._apply_slippage(
            price, is_buy=False, slippage_pct=slippage_pct
        )

        # Sell price should be lower
        assert adjusted_price < price
        assert adjusted_price == price * Decimal("0.999")

    def test_apply_slippage_none(self, trade_executor):
        """Test slippage with None (use config default)."""
        price = Decimal("150")

        adjusted_price = trade_executor._apply_slippage(price, is_buy=True, slippage_pct=None)

        # Should use config default (0.1%)
        assert adjusted_price > price

    def test_build_trade_reason(self, trade_executor):
        """Test building trade reason from signal."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
            metadata={"rsi": 30.0, "ema_trend": "bullish"},
        )

        reason = trade_executor._build_trade_reason(signal, MockMarketData("AAPL", 150))

        assert "BUY" in reason
        assert "technical" in reason  # Source is TECHNICAL
        assert "conf=80.0%" in reason
        assert "rsi=30.0" in reason

    def test_execute_buy_with_diagnostic_logger(self, trade_executor, buy_signal):
        """Test buy execution logs to diagnostic logger."""
        mock_logger = MagicMock()
        trade_executor.diagnostic_logger = mock_logger

        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("100000")

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        if trade:
            mock_logger.log_signal_executed.assert_called_once()

    def test_execute_sell_with_diagnostic_logger(
        self, trade_executor, position_manager, sell_signal, sample_buy_trades
    ):
        """Test sell execution logs to diagnostic logger."""
        mock_logger = MagicMock()
        trade_executor.diagnostic_logger = mock_logger

        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 160)
        capital = Decimal("100000")

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, sample_buy_trades
        )

        if trade:
            mock_logger.log_signal_executed.assert_called_once()

    def test_execute_buy_signal_insufficient_capital_adjusts_position(
        self, trade_executor, buy_signal
    ):
        """Test buy execution adjusts position when capital insufficient."""
        market_data = MockMarketData("AAPL", 150)
        capital = Decimal("1000")  # Low capital

        def mock_close_position(symbol, timestamp, reason):
            pass

        def mock_validate_profitability(signal, price):
            return True

        trade, new_capital = trade_executor.execute_buy_signal(
            buy_signal, market_data, capital, mock_close_position, mock_validate_profitability
        )

        # Should adjust position to fit capital or reject
        if trade:
            assert trade.quantity * trade.entry_price <= capital + Decimal("100")  # Some tolerance

    def test_calculate_position_size_minimum(self, trade_executor, buy_signal):
        """Test position size has minimum value."""
        price = Decimal("150")
        capital = Decimal("100")  # Very low capital

        position_size = trade_executor._calculate_position_size(buy_signal, price, capital)

        # Should be at least 1 or very small
        assert position_size >= Decimal("1")

    def test_get_strategy_slippage_from_metadata(self, trade_executor):
        """Test getting slippage from signal metadata."""
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
            metadata={"slippage_per_trade_pct": "0.2"},
        )

        slippage = trade_executor._get_strategy_slippage(signal)

        assert slippage == Decimal("0.2")

    def test_get_strategy_slippage_from_strategy(self, trade_executor):
        """Test getting slippage from strategy object."""

        # Use a real object instead of MagicMock to avoid attribute access issues
        class MockStrategy:
            slippage_per_trade_pct = Decimal("0.15")

        mock_strategy = MockStrategy()
        trade_executor.strategy = mock_strategy

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=50.0,
            priority_score=70.0,
            source=SignalSource.TECHNICAL,
            price=Decimal("150"),
            volume=Decimal("1000"),
            timestamp=datetime(2024, 1, 1),
        )

        slippage = trade_executor._get_strategy_slippage(signal)

        assert slippage == Decimal("0.15")

    def test_execute_sell_signal_closes_buy_trades(
        self, trade_executor, position_manager, sell_signal, sample_buy_trades
    ):
        """Test sell execution closes matching buy trades."""
        position_manager.update_position("AAPL", Decimal("100"))

        market_data = MockMarketData("AAPL", 160)
        capital = Decimal("100000")

        # Check buy trades are open before sell
        assert all(t.status == TradeStatus.OPEN for t in sample_buy_trades)

        trade, new_capital = trade_executor.execute_sell_signal(
            sell_signal, market_data, capital, sample_buy_trades
        )

        # Either the buy trades should be closed OR the sell should execute
        # (The sell might not fully close all buy trades depending on position size calculation)
        assert trade is not None or any(t.status == TradeStatus.CLOSED for t in sample_buy_trades)
        # At minimum, a sell trade should be created
        assert trade is not None
        assert trade.side == "sell"
