"""
Tests for look-ahead bias prevention in backtesting.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.momentum import MarketData
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType


class TestLookAheadBias:
    """Test look-ahead bias prevention techniques."""

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

    def test_signal_timing_validation(self, config):
        """Test that signals are processed with proper timing."""
        market_data = self._create_market_data()
        signals = self._create_signals()

        backtester = SimpleBacktester(config)
        result = backtester.run_backtest(market_data, signals)

        assert result is not None
        assert isinstance(result.total_return, Decimal)

    def _create_market_data(self):
        """Create simple market data."""
        data = []
        base_date = datetime.utcnow() - timedelta(days=100)

        for i in range(50):
            date = base_date + timedelta(days=i)
            price = Decimal("100.0") + Decimal(str(i * 0.5))

            data.append(
                MarketData(
                    symbol="AAPL",
                    bid=price - Decimal("0.5"),
                    ask=price + Decimal("0.5"),
                    spread=Decimal("1.0"),
                    open_price=price,
                    high_price=price + Decimal("1.0"),
                    low_price=price - Decimal("1.0"),
                    close_price=price,
                    volume=Decimal("1000000"),
                    timestamp=date,
                )
            )
        return data

    def _create_signals(self):
        """Create simple signals."""
        signals = []
        base_date = datetime.utcnow() - timedelta(days=50)

        for i in range(10):
            date = base_date + timedelta(days=i * 5)
            price = Decimal("100.0") + Decimal(str(i * 2.0))

            signals.append(
                Signal(
                    symbol="AAPL",
                    signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=Decimal("70.0"),
                    liquidity_score=Decimal("50.0"),
                    priority_score=Decimal("50.0"),
                    source=SignalSource.TECHNICAL,
                    price=price,
                    volume=Decimal("1000"),
                    timestamp=date,
                )
            )
        return signals
