"""
Basic Backtesting Tests

Tests core backtest engine functionality:
- Model validation (Trade, BacktestConfig, PerformanceMetrics)
- Basic backtest execution with realistic data
- Edge cases (empty data, zero volatility, crash scenario)
- Reproducibility
"""

from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    TradeStatus,
)
from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.shared.utils.decimal_utils import round_price

# Rebuild forward references for Pydantic models with datetime fields
BacktestResult.model_rebuild()
Trade.model_rebuild()

DEFAULT_SYMBOL = "AAPL"


# ============================================================================
# Helper: Realistic Data Generation
# ============================================================================


def generate_realistic_quotes(
    symbol: str,
    days: int = 1000,
    seed: int = 42,
    drift: float = 0.05,
    volatility: float = 0.20,
) -> list[Quote]:
    """Generate realistic OHLCV data using Geometric Brownian Motion."""
    np.random.seed(seed)

    mu = drift / 252
    sigma = volatility / np.sqrt(252)

    dW = np.random.standard_normal(days - 1)
    log_returns = (mu - 0.5 * sigma**2) + sigma * dW
    prices = np.empty(days)
    prices[0] = 100.0
    prices[1:] = prices[0] * np.exp(np.cumsum(log_returns))
    prices = np.maximum(prices, 1.0)

    quotes = []
    base_volume = 50_000_000

    for i, close_price in enumerate(prices):
        timestamp = datetime(2020, 1, 1) + timedelta(days=i)

        daily_range = abs(close_price * np.random.normal(0, 0.02))
        high = close_price + abs(np.random.normal(0, daily_range / 2))
        low = close_price - abs(np.random.normal(0, daily_range / 2))
        open_price = close_price + np.random.normal(0, daily_range * 0.3)

        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)

        volume = int(base_volume * (1 + np.random.normal(0, 0.3)))
        volume = max(volume, 1_000_000)

        quotes.append(
            Quote(
                symbol=symbol,
                timestamp=timestamp,
                bid=round_price(close_price * 0.9995, "equity", symbol),
                ask=round_price(close_price * 1.0005, "equity", symbol),
                last=round_price(close_price, "equity", symbol),
                volume=Decimal(str(volume)),
                open=round_price(open_price, "equity", symbol),
                high=round_price(high, "equity", symbol),
                low=round_price(low, "equity", symbol),
                close=round_price(close_price, "equity", symbol),
            )
        )

    return quotes


def generate_sma_crossover_signals(
    quotes: list[Quote],
    fast: int = 20,
    slow: int = 50,
    strength: float = 75.0,
    confidence: float = 80.0,
) -> list[Signal]:
    """Generate trading signals using SMA crossover strategy."""
    signals = []

    if len(quotes) < slow + 1:
        return signals

    closes = [float(q.close) for q in quotes]
    fast_sma = []
    slow_sma = []

    for i in range(len(closes)):
        if i >= fast - 1:
            fast_sma.append(np.mean(closes[i - fast + 1 : i + 1]))
        else:
            fast_sma.append(None)

        if i >= slow - 1:
            slow_sma.append(np.mean(closes[i - slow + 1 : i + 1]))
        else:
            slow_sma.append(None)

    for i in range(slow, len(quotes)):
        if fast_sma[i] is None or slow_sma[i] is None:
            continue
        if fast_sma[i - 1] is None or slow_sma[i - 1] is None:
            continue

        if fast_sma[i - 1] <= slow_sma[i - 1] and fast_sma[i] > slow_sma[i]:
            signals.append(
                Signal(
                    symbol=quotes[i].symbol,
                    signal_type=SignalType.BUY,
                    source=SignalSource.TECHNICAL,
                    timestamp=quotes[i].timestamp,
                    price=quotes[i].close,
                    strength=SignalStrength.MODERATE if strength < 80 else SignalStrength.STRONG,
                    confidence=confidence,
                    liquidity_score=75.0,
                    priority_score=70.0,
                    volume=Decimal("1000000"),
                )
            )

        elif fast_sma[i - 1] >= slow_sma[i - 1] and fast_sma[i] < slow_sma[i]:
            signals.append(
                Signal(
                    symbol=quotes[i].symbol,
                    signal_type=SignalType.SELL,
                    source=SignalSource.TECHNICAL,
                    timestamp=quotes[i].timestamp,
                    price=quotes[i].close,
                    strength=SignalStrength.MODERATE if strength < 80 else SignalStrength.STRONG,
                    confidence=confidence,
                    liquidity_score=75.0,
                    priority_score=70.0,
                    volume=Decimal("1000000"),
                )
            )

    return signals


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def default_config():
    """Default backtest configuration."""
    return BacktestConfig(
        initial_capital=Decimal("100000"),
        commission_per_trade=Decimal("1.0"),
        slippage_percentage=Decimal("0.1"),
        risk_free_rate=Decimal("0.02"),
        max_position_size=Decimal("0.1"),
    )


@pytest.fixture
def default_symbol():
    """Default symbol for testing."""
    return DEFAULT_SYMBOL


# ============================================================================
# Test: Basic Backtest Execution
# ============================================================================


class TestBasicBacktest:
    """Test basic backtest execution with realistic data."""

    def test_empty_market_data_raises_error(self, default_config):
        """Backtest should raise ValueError when no market data is provided."""
        backtester = SimpleBacktester(default_config)

        with pytest.raises(ValueError, match="No market data available"):
            backtester.run_backtest([], [])

    def test_backtest_with_realistic_data(self, default_config, default_symbol):
        """Run backtest with realistic GBM-generated data and SMA signals."""
        quotes = generate_realistic_quotes(symbol=default_symbol, days=200, seed=42)
        signals = generate_sma_crossover_signals(quotes)

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, signals)

        assert isinstance(result, BacktestResult)
        assert result.final_capital > 0
        assert result.start_date == quotes[0].timestamp
        assert result.end_date == quotes[-1].timestamp
        assert result.performance is not None

    def test_backtest_with_no_signals(self, default_config, default_symbol):
        """Backtest should handle no signals gracefully."""
        quotes = generate_realistic_quotes(symbol=default_symbol, days=100, seed=42)

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, [])

        assert isinstance(result, BacktestResult)
        assert result.final_capital > 0
        # No trades should be executed
        assert result.performance is not None

    def test_reproducibility(self, default_config, default_symbol):
        """Same seed should produce identical results."""
        quotes1 = generate_realistic_quotes(symbol=default_symbol, days=200, seed=42)
        quotes2 = generate_realistic_quotes(symbol=default_symbol, days=200, seed=42)
        signals1 = generate_sma_crossover_signals(quotes1)
        signals2 = generate_sma_crossover_signals(quotes2)

        backtester1 = SimpleBacktester(default_config)
        result1 = backtester1.run_backtest(quotes1, signals1)

        backtester2 = SimpleBacktester(default_config)
        result2 = backtester2.run_backtest(quotes2, signals2)

        assert result1.final_capital == result2.final_capital
        assert result1.total_return == result2.total_return

    def test_trades_have_valid_structure(self, default_config, default_symbol):
        """All generated trades should have valid structure."""
        quotes = generate_realistic_quotes(symbol=default_symbol, days=200, seed=42)
        signals = generate_sma_crossover_signals(quotes)

        if not signals:
            pytest.skip("No signals generated for this data")

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, signals)

        for trade in result.trades:
            assert trade.quantity > 0
            assert trade.entry_price > 0
            assert trade.symbol == default_symbol

    def test_all_buy_signals_no_sells(self, default_config, default_symbol):
        """Backtest should handle all buy signals (no sell signals) gracefully."""
        quotes = generate_realistic_quotes(symbol=default_symbol, days=100, seed=42)

        signals = []
        for i in range(10, min(50, len(quotes)), 10):
            signals.append(
                Signal(
                    symbol=default_symbol,
                    signal_type=SignalType.BUY,
                    source=SignalSource.TECHNICAL,
                    timestamp=quotes[i].timestamp,
                    price=quotes[i].close,
                    strength=SignalStrength.MODERATE,
                    confidence=75.0,
                    liquidity_score=75.0,
                    priority_score=70.0,
                    volume=Decimal("1000000"),
                )
            )

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, signals)

        assert result is not None
        assert result.final_capital > 0


# ============================================================================
# Test: Model Validation
# ============================================================================


class TestBacktestModels:
    """Test backtesting model validation."""

    def test_trade_model_validation(self):
        """Trade model should validate basic fields."""
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
        assert trade.quantity == Decimal("100")
        assert trade.entry_price == Decimal("150.0")
        assert trade.status == TradeStatus.OPEN

    def test_trade_invalid_side(self):
        """Trade model should reject invalid side values."""
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
        """Closed trade must have exit price."""
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
        """PerformanceMetrics should accept valid data."""
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

    def test_performance_metrics_inconsistent_trades(self):
        """PerformanceMetrics should reject inconsistent trade counts."""
        with pytest.raises(ValueError, match="Total trades must equal winning \\+ losing trades"):
            PerformanceMetrics(
                total_trades=10,
                winning_trades=6,
                losing_trades=3,
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

    def test_backtest_config_defaults(self):
        """BacktestConfig should have sensible defaults."""
        config = BacktestConfig()
        assert config.initial_capital == Decimal("100000")
        assert config.commission_per_trade == Decimal("1.0")
        assert config.slippage_percentage == Decimal("0.1")

    def test_backtest_config_high_slippage(self):
        """BacktestConfig should reject slippage > 5%."""
        with pytest.raises(ValueError, match="Slippage percentage too high"):
            BacktestConfig(
                initial_capital=Decimal("100000"),
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("10.0"),
            )

    def test_backtest_config_stop_loss_greater_than_take_profit(self):
        """Stop loss must be less than take profit."""
        with pytest.raises(
            ValueError,
            match="Stop loss percentage must be less than take profit percentage",
        ):
            BacktestConfig(
                initial_capital=Decimal("100000"),
                stop_loss_percentage=Decimal("10.0"),
                take_profit_percentage=Decimal("5.0"),
            )


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_volatility_no_signals(self, default_config, default_symbol):
        """With constant prices, SMA crossover should not generate signals."""
        quotes = []
        for i in range(100):
            quotes.append(
                Quote(
                    symbol=default_symbol,
                    timestamp=datetime(2023, 1, 1) + timedelta(days=i),
                    bid=Decimal("99.95"),
                    ask=Decimal("100.05"),
                    last=Decimal("100.00"),
                    open=Decimal("100.00"),
                    high=Decimal("100.00"),
                    low=Decimal("100.00"),
                    close=Decimal("100.00"),
                    volume=Decimal("1000000"),
                )
            )

        signals = generate_sma_crossover_signals(quotes)
        assert len(signals) == 0

    def test_market_crash_scenario(self, default_config, default_symbol):
        """Backtest should handle extreme negative drift gracefully."""
        quotes = generate_realistic_quotes(
            symbol=default_symbol,
            days=200,
            seed=42,
            drift=-0.50,
            volatility=0.40,
        )
        signals = generate_sma_crossover_signals(quotes)

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, signals)

        assert result.performance is not None
        # Final capital should be positive but less than initial
        assert result.final_capital > 0

    def test_extreme_volatility_scenario(self, default_config, default_symbol):
        """Backtest should handle extreme volatility."""
        quotes = generate_realistic_quotes(
            symbol=default_symbol,
            days=200,
            seed=42,
            drift=0.0,
            volatility=1.0,
        )
        signals = generate_sma_crossover_signals(quotes)

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, signals)

        assert result is not None
        assert result.performance is not None
        assert result.final_capital > 0

    def test_short_data_window(self, default_config, default_symbol):
        """Backtest should work with minimal data (not enough for SMA signals)."""
        quotes = generate_realistic_quotes(symbol=default_symbol, days=30, seed=42)

        backtester = SimpleBacktester(default_config)
        result = backtester.run_backtest(quotes, [])

        assert isinstance(result, BacktestResult)
        assert result.final_capital > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
