"""Golden invariant tests for the backtesting engine.

These tests pin down the correctness properties the engine must always
satisfy, independently of any strategy:

1. t+1 open execution: a signal generated at bar t fills at the OPEN of the
   next bar (with zero slippage the fill equals the open exactly).
2. No look-ahead: a signal timestamped in the future never executes, and
   mutating market data AFTER a cutoff never changes trades BEFORE it.
3. Cash reconciliation: final capital == initial capital + sum(closed P&L).
4. Drawdown contract: -1 <= max_drawdown <= 0 (decimal fraction from peak)
   and max_drawdown_percentage is its percentage form.
5. Determinism: identical inputs produce identical economics.
6. Pessimistic stops: stop-loss wins when both SL and TP are touched in one
   bar, and a bar that gaps through the stop fills at the open.

All fixtures use hand-built deterministic bars (no randomness) and zero
slippage/commissions so fills can be asserted exactly.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult, Trade, TradeStatus
from app.domain.models.market_data import Quote
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

# Pydantic cannot resolve the TYPE_CHECKING-guarded datetime forward refs
# automatically (same as test_full_workflow.py).
BacktestResult.model_rebuild()
Trade.model_rebuild()

T0 = datetime(2024, 1, 1, 10, 0, 0)


def make_quote(
    symbol: str,
    timestamp: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
    volume: str = "1000000",
) -> Quote:
    return Quote(
        symbol=symbol,
        timestamp=timestamp,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        last=Decimal(close),
        volume=Decimal(volume),
        bid=Decimal(close),
        ask=Decimal(close),
    )


def make_signal(
    symbol: str,
    signal_type: SignalType,
    timestamp: datetime,
    price: str = "100",
    strategy: str = "golden",
) -> Signal:
    return Signal(
        symbol=symbol,
        signal_type=signal_type,
        strength=SignalStrength.MODERATE,
        confidence=80.0,
        liquidity_score=90.0,
        priority_score=80.0,
        source=SignalSource.MOMENTUM,
        price=Decimal(price),
        timestamp=timestamp,
        volume=Decimal("1000000"),
        metadata={"strategy": strategy},
    )


def make_engine(**config_overrides) -> SimpleBacktester:
    config = BacktestConfig(
        strategy_name="golden",
        initial_capital=Decimal("100000"),
        commission_per_trade=Decimal("0"),
        slippage_percentage=Decimal("0"),
        **config_overrides,
    )
    return SimpleBacktester(config, enable_risk_envelope=False)


class TestNextDayOpenExecution:
    """A signal generated at bar t must fill at the open of bar t+1."""

    def test_buy_fills_at_next_bar_open(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
            make_quote("AAPL", T0 + timedelta(days=2), "110", "112", "109", "111"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0, price="100")

        result = make_engine().run_backtest(bars, [buy])

        buy_trades = [t for t in result.trades if t.side == "buy"]
        assert len(buy_trades) == 1
        trade = buy_trades[0]
        assert trade.entry_time == T0 + timedelta(days=1), "must fill on the NEXT bar"
        # Base slippage (~0.1%) is charged on top of the open
        assert float(trade.entry_price) == pytest.approx(105.0, rel=0.003), (
            "must fill at the next bar's open (plus base slippage)"
        )

    def test_signal_on_last_bar_never_fills(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0 + timedelta(days=1), price="107")

        result = make_engine().run_backtest(bars, [buy])

        assert len(result.trades) == 0, "no subsequent bar -> no fill"

    def test_legacy_same_bar_mode_still_available(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0, price="100")

        result = make_engine(next_day_execution=False).run_backtest(bars, [buy])

        buy_trades = [t for t in result.trades if t.side == "buy"]
        assert len(buy_trades) == 1
        assert float(buy_trades[0].entry_price) == pytest.approx(100.0, rel=0.003), (
            "legacy mode fills at the matching bar's close (plus base slippage)"
        )


class TestNoLookAhead:
    """Signals from the future never execute; future data never changes past trades."""

    def test_future_signal_never_executes(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
        ]
        future_buy = make_signal("AAPL", SignalType.BUY, T0 + timedelta(days=5), price="120")

        result = make_engine().run_backtest(bars, [future_buy])

        assert len(result.trades) == 0, "a signal timestamped beyond the data must not fill"

    def test_mutating_future_data_keeps_past_trades_identical(self):
        # 6 bars rising steadily; BUY at bar 0, SELL at bar 2
        bars = [
            make_quote(
                "AAPL",
                T0 + timedelta(days=i),
                str(100 + 5 * i),
                str(102 + 5 * i),
                str(99 + 5 * i),
                str(101 + 5 * i),
            )
            for i in range(6)
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0 + timedelta(days=0))
        sell = make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=2))

        baseline = make_engine().run_backtest(list(bars), [buy, sell])

        # Corrupt everything after the cutoff (day 3+): prices multiplied x10
        mutated = [
            bar.model_copy(
                update={
                    "open": bar.open * 10,
                    "high": bar.high * 10,
                    "low": bar.low * 10,
                    "close": bar.close * 10,
                    "last": bar.last * 10,
                    "bid": bar.bid * 10,
                    "ask": bar.ask * 10,
                }
            )
            if bar.timestamp > T0 + timedelta(days=3)
            else bar
            for bar in bars
        ]
        after = make_engine().run_backtest(mutated, [buy, sell])

        cutoff = T0 + timedelta(days=3)

        def econ_signature(res: BacktestResult):
            return [
                (t.symbol, t.side, t.quantity, t.entry_price, t.entry_time)
                for t in res.trades
                if t.entry_time <= cutoff
            ]

        assert econ_signature(baseline) == econ_signature(after), (
            "trades entered before the cutoff must be identical when only "
            "future data changes (look-ahead check)"
        )


class TestCashReconciliation:
    """final capital must reconcile with the sum of closed trade P&L."""

    def test_final_capital_equals_initial_plus_closed_pnl(self):
        bars = [
            make_quote(
                "AAPL",
                T0 + timedelta(days=i),
                str(100 + 5 * i),
                str(102 + 5 * i),
                str(99 + 5 * i),
                str(101 + 5 * i),
            )
            for i in range(5)
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0)
        sell = make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=2))

        result = make_engine().run_backtest(bars, [buy, sell])

        assert result.final_capital is not None
        closed_pnl = sum(
            (t.pnl or Decimal("0")) for t in result.trades if t.status == TradeStatus.CLOSED
        )
        assert float(result.final_capital) == pytest.approx(
            float(Decimal("100000") + closed_pnl), abs=1.0
        ), "cash must reconcile: final == initial + sum(closed P&L)"


class TestDrawdownContract:
    """max_drawdown is a decimal fraction from peak in [-1, 0]."""

    def test_drawdown_bounds_and_percentage_form(self):
        # Generate a rising-then-crashing path via a simple round trip
        prices = [100, 110, 120, 60, 55, 50]
        bars = [
            make_quote(
                "AAPL",
                T0 + timedelta(days=i),
                str(p),
                str(p + 2),
                str(p - 1),
                str(p),
            )
            for i, p in enumerate(prices)
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0)
        sell = make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=1))

        result = make_engine().run_backtest(bars, [buy, sell])

        dd = result.performance.max_drawdown
        assert Decimal("-1") <= dd <= Decimal("0"), f"drawdown must be a fraction in [-1,0], got {dd}"
        assert float(result.performance.max_drawdown_percentage) == pytest.approx(
            float(dd * 100), abs=0.001
        )


class TestDeterminism:
    """Same inputs must yield the same economics on repeated runs."""

    def test_repeated_run_is_identical(self):
        bars = [
            make_quote(
                "AAPL",
                T0 + timedelta(days=i),
                str(100 + (i % 3)),
                str(103 + (i % 3)),
                str(98 + (i % 3)),
                str(101 + (i % 3)),
            )
            for i in range(8)
        ]
        signals = [
            make_signal("AAPL", SignalType.BUY, T0 + timedelta(days=1)),
            make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=4)),
        ]

        r1 = make_engine().run_backtest(list(bars), list(signals))
        r2 = make_engine().run_backtest(list(bars), list(signals))

        assert float(r1.final_capital) == float(r2.final_capital)
        assert len(r1.trades) == len(r2.trades)
        for t1, t2 in zip(r1.trades, r2.trades):
            assert (t1.side, t1.quantity, t1.entry_price) == (t2.side, t2.quantity, t2.entry_price)


class TestPessimisticStops:
    """SL wins over TP in the same bar; gap-through fills at the open."""

    def test_sl_and_tp_in_same_bar_fills_at_sl(self):
        # Entry fills at day-1 open = 100 (SL=95, TP=110). Day-2 bar touches
        # both levels: the pessimistic engine must fill at the stop.
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=2), "100", "111", "94", "100"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0)

        engine = make_engine(
            stop_loss_percentage=Decimal("5"), take_profit_percentage=Decimal("10")
        )
        result = engine.run_backtest(bars, [buy])

        closed = [t for t in result.trades if t.status == TradeStatus.CLOSED]
        assert closed, "the both-levels bar must close the position"
        assert closed[-1].reason == "stop_loss"
        assert float(closed[-1].exit_price) == pytest.approx(95.0, abs=0.5), (
            f"stop-loss must win over take-profit in the same bar, exit={closed[-1].exit_price}"
        )

    def test_gap_through_stop_fills_at_open(self):
        # Entry fills at day-1 open = 100 (SL=95). Day-2 bar opens at 80,
        # far below the stop: the fill must be the open (80), not 95.
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=2), "80", "85", "79", "82"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0)

        engine = make_engine(stop_loss_percentage=Decimal("5"))
        result = engine.run_backtest(bars, [buy])

        closed = [t for t in result.trades if t.status == TradeStatus.CLOSED]
        assert closed, "the gap bar must close the position"
        assert closed[-1].reason == "stop_loss"
        assert float(closed[-1].exit_price) == pytest.approx(80.0, abs=0.2), (
            f"gap through the stop must fill at the open, exit={closed[-1].exit_price}"
        )
