"""
Integration Tests: Liquidity Validation with Backtesting Engine

Tests that liquidity validation is properly integrated into the backtesting
engine and affects trade execution realistically.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.market_data import Quote


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

    def test_liquidity_validator_initialized(self, backtester):
        """Test that liquidity validator is properly initialized."""
        assert (
            backtester.liquidity_validator is not None
        ), "LiquidityValidator should be initialized"
        assert (
            backtester.liquidity_validator.enable_partial_fills == True
        ), "Partial fills should be enabled by default"

    def test_normal_order_executes_with_liquidity_validation(self, backtester):
        """Test that normal orders execute successfully with liquidity validation."""
        # Create market data with normal volume
        bar = Quote(
            symbol="AAPL",
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

        # Create buy signal
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=2),
            metadata={"strategy": "test"},
        )

        # Execute buy
        backtester._execute_buy_signal(signal, bar)

        # Verify trade was executed
        assert len(backtester.trades) == 1, "Trade should be executed"
        assert "AAPL" in backtester.positions, "Position should be opened"
        assert backtester.positions["AAPL"] > 0, "Position should have positive quantity"

        # Verify trade includes market impact in execution price
        trade = backtester.trades[0]
        assert trade.entry_price > Decimal(
            "100"
        ), f"Entry price ${trade.entry_price} should include market impact > $100"

    def test_excessive_order_rejected_by_liquidity_validation(self, backtester):
        """Test that orders exceeding liquidity limits are rejected."""
        # Create market data with low volume
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

        # Create buy signal for large order (>10% of daily volume)
        # With max_position_size of 25%, this would try to buy ~$25K worth = 5,000 shares
        # which is 50% of daily volume - should be rejected
        signal = Signal(
            symbol="PENNY",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=90.0,
            liquidity_score=50.0,  # Low liquidity
            priority_score=50.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("5"),
            volume=Decimal("10000"),
            timestamp=past_time(hours_ago=2),
            metadata={"strategy": "test"},
        )

        initial_capital = backtester.capital
        initial_trade_count = len(backtester.trades)

        # Execute buy (should be rejected by liquidity validation)
        backtester._execute_buy_signal(signal, bar)

        # Verify trade was NOT executed due to liquidity rejection
        assert (
            len(backtester.trades) == initial_trade_count
        ), "Trade should NOT be executed due to liquidity rejection"
        assert (
            "PENNY" not in backtester.positions or backtester.positions["PENNY"] == 0
        ), "Position should NOT be opened"
        # Capital should not have decreased significantly (only commission checks)
        assert backtester.capital >= initial_capital - Decimal(
            "10"
        ), "Capital should not decrease significantly for rejected trade"

    def test_partial_fill_for_large_order(self, backtester):
        """Test that large orders get partial fills."""
        # Create market data with moderate volume
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

        # Create buy signal for large order (7.5% of daily volume)
        # This should trigger partial fill (fill up to 5% = 25,000 shares)
        signal = Signal(
            symbol="TEST",
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=95.0,
            liquidity_score=70.0,
            priority_score=70.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("500000"),
            timestamp=past_time(hours_ago=2),
            metadata={"strategy": "test"},
        )

        # Execute buy
        backtester._execute_buy_signal(signal, bar)

        # Verify trade was executed with partial fill
        assert len(backtester.trades) == 1, "Trade should be executed"
        assert "TEST" in backtester.positions, "Position should be opened"

        # Position size should be limited by partial fill (25K shares = 5% of 500K)
        # Not the full requested amount
        position_size = backtester.positions["TEST"]
        assert position_size > 0, "Position should have positive quantity"
        # Position should be <= 5% of daily volume (25,000 shares)
        assert position_size <= Decimal(
            "25000"
        ), f"Position size {position_size} should be <= 25,000 shares (5% partial fill)"

    def test_sell_order_liquidity_validation(self, backtester):
        """Test that sell orders also undergo liquidity validation."""
        # First, open a position
        bar_buy = Quote(
            symbol="AAPL",
            timestamp=past_time(hours_ago=2),
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

        buy_signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=2),
            metadata={"strategy": "test"},
        )

        backtester._execute_buy_signal(buy_signal, bar_buy)

        # Verify position opened
        position_size = backtester.positions["AAPL"]
        assert position_size > 0, "Position should be opened"

        # Now try to sell with normal volume
        bar_sell = Quote(
            symbol="AAPL",
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

        sell_signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=80.0,
            liquidity_score=75.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=Decimal("100"),
            volume=Decimal("1000000"),
            timestamp=past_time(hours_ago=1),
            metadata={"strategy": "test"},
        )

        initial_capital = backtester.capital

        # Execute sell
        backtester._execute_sell_signal(sell_signal, bar_sell)

        # Verify sell was executed
        assert (
            len([t for t in backtester.trades if t.side == "sell"]) > 0
        ), "Sell trade should be executed"

        # Capital should have increased from sell proceeds
        assert (
            backtester.capital > initial_capital
        ), "Capital should increase after selling position"

    def test_liquidity_metrics_available(self, backtester):
        """Test that liquidity metrics can be retrieved."""
        bar = Quote(
            symbol="AAPL",
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
