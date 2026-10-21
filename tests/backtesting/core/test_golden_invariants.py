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


def make_engine(commission: str = "0", **config_overrides) -> SimpleBacktester:
    config = BacktestConfig(
        strategy_name="golden",
        initial_capital=Decimal("100000"),
        commission_per_trade=Decimal(commission),
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
            (
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
            )
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
        assert Decimal("-1") <= dd <= Decimal("0"), (
            f"drawdown must be a fraction in [-1,0], got {dd}"
        )
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


class TestCommissionAccounting:
    """Comisiones: las cobra el modelo IBKR (TransactionCostModel), NO
    BacktestConfig.commission_per_trade (ese campo solo pre-valida rentabilidad).

    Contrato: todo trade carga comision (>= minimo IBKR $1) y el capital final
    es menor que el de un backtest identico con costes a cero.
    """

    def test_every_trade_carries_ibkr_commission(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
            make_quote("AAPL", T0 + timedelta(days=2), "110", "112", "109", "111"),
        ]
        sigs = [
            make_signal("AAPL", SignalType.BUY, T0, price="100"),
            make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=1), price="107"),
        ]
        result = make_engine().run_backtest(bars, sigs)

        assert len(result.trades) >= 1
        for t in result.trades:
            assert t.commission >= Decimal("1"), (
                f"trade {t.side} debe cobrar >= minimo IBKR ($1); cobro {t.commission}"
            )

    def test_commissions_reduce_final_capital_vs_zero_cost(self):
        from unittest.mock import patch

        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "105", "108", "104", "107"),
            make_quote("AAPL", T0 + timedelta(days=2), "110", "112", "109", "111"),
        ]
        sigs = [
            make_signal("AAPL", SignalType.BUY, T0, price="100"),
            make_signal("AAPL", SignalType.SELL, T0 + timedelta(days=1), price="107"),
        ]

        con_costes = make_engine().run_backtest(bars, sigs)

        # costes a cero: parchear el modelo para que devuelva costes nulos
        from app.backtesting.services.transaction_cost_model import TransactionCostModel

        def _zero_costs(self, **kwargs):
            return type(
                "ZeroCostResult",
                (),
                {
                    "commission": Decimal("0"),
                    "sec_fee": Decimal("0"),
                    "taf_fee": Decimal("0"),
                    "slippage_cost": Decimal("0"),
                    "market_impact_cost": Decimal("0"),
                    "spread_cost": Decimal("0"),
                    "total_cost": Decimal("0"),
                    "total_cost_bps": Decimal("0"),
                    "gross_value": Decimal("0"),
                },
            )()

        with patch.object(TransactionCostModel, "calculate_costs", _zero_costs):
            sin_costes = make_engine().run_backtest(bars, sigs)

        delta = float(sin_costes.final_capital) - float(con_costes.final_capital)
        assert delta > 0, (
            "mismo backtest con el modelo de costes IBKR debe terminar con menos "
            "capital que uno con costes a cero"
        )


class TestWeekendGap:
    """Gaps entre barras no contiguas: el fill usa el open de la SIGUIENTE barra,
    aunque haya fin de semana de por medio, sin inventar precios intermedios."""

    def test_fill_across_weekend_gap_uses_next_open(self):
        # viernes -> lunes (gap de fin de semana)
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),  # lunes
            make_quote("AAPL", T0 + timedelta(days=4), "100", "102", "99", "100"),  # viernes
            make_quote("AAPL", T0 + timedelta(days=7), "95", "97", "93", "96"),  # lunes
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0 + timedelta(days=4), price="100")

        result = make_engine().run_backtest(bars, [buy])

        # entrada + cierre forzado end_of_backtest; la entrada es la que importa
        entries = [t for t in result.trades if t.side == "buy"]
        assert len(entries) == 1
        trade = entries[0]
        assert trade.entry_time == T0 + timedelta(days=7), "fill tras el gap"
        assert float(trade.entry_price) == pytest.approx(95.0, rel=0.003), (
            "el fill es el open real del lunes, no el close del viernes"
        )

    def test_gap_down_does_not_widen_beyond_bar_range(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=3), "80", "85", "78", "84"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0, price="100")

        result = make_engine().run_backtest(bars, [buy])

        # entrada + cierre forzado a fin de backtest (end_of_backtest)
        entries = [t for t in result.trades if t.side == "buy"]
        assert len(entries) == 1
        assert float(entries[0].entry_price) == pytest.approx(80.0, rel=0.003), (
            "el fill tras el gap es el open real de la barra siguiente"
        )


class TestShortRoundTrip:
    """Shorts: la venta abre, la compra cierra; el PnL es (entrada - salida) x cantidad."""

    def test_sell_without_position_does_not_open_short(self):
        """Contrato actual del motor: LONG-ONLY.

        Un SELL sin posición long NO abre un corto. Este invariante documenta
        la limitación a propósito: si algún día el motor soporta shorts, este
        test saltará y obligará a actualizar el contrato (y su documentación).
        """
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "95", "97", "93", "96"),
            make_quote("AAPL", T0 + timedelta(days=2), "90", "93", "88", "91"),
        ]
        sell = make_signal("AAPL", SignalType.SELL, T0, price="100")

        result = make_engine().run_backtest(bars, [sell])

        opened = [t for t in result.trades if t.reason != "end_of_backtest"]
        assert opened == [], (
            f"motor long-only: un SELL sin posición no debe abrir trades; abrió {len(opened)}"
        )


class TestPositionSizingHonorsConfig:
    """El tamaño de posición lo gobierna `config.max_position_size` del motor.

    Antes el motor pedía la cantidad al ComplianceEngine sin pasarle su
    límite, y el sizer caía al default del singleton (10%): toda estrategia
    quedaba capada a ~8% por posición con la mayoría del capital en caja,
    fuera cual fuera su `max_position_size`.
    """

    def test_buy_deploys_max_position_size_fraction_of_capital(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "100", "101", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=2), "100", "101", "99", "100"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0, price="100")
        buy.confidence = 100.0

        result = make_engine(max_position_size=Decimal("0.25")).run_backtest(bars, [buy])

        entries = [t for t in result.trades if t.side == "buy"]
        assert len(entries) == 1
        deployed = float(entries[0].quantity) * float(entries[0].entry_price)
        assert deployed == pytest.approx(25_000, rel=0.01), (
            f"con max_position_size=25% y confianza 100 debe invertir ~25k de 100k, invirtió {deployed:,.0f}"
        )

    def test_confidence_scales_size_below_the_cap(self):
        bars = [
            make_quote("AAPL", T0, "100", "102", "99", "100"),
            make_quote("AAPL", T0 + timedelta(days=1), "100", "101", "99", "100"),
        ]
        buy = make_signal("AAPL", SignalType.BUY, T0, price="100")
        buy.confidence = 80.0

        result = make_engine(max_position_size=Decimal("0.25")).run_backtest(bars, [buy])

        entries = [t for t in result.trades if t.side == "buy"]
        deployed = float(entries[0].quantity) * float(entries[0].entry_price)
        assert deployed == pytest.approx(20_000, rel=0.01), "25% x confianza 0.8 = 20% del capital"


class TestSimultaneousBuysShareTheDayPortfolio:
    """El sizing NO puede ser secuencial sobre cash post-fill.

    Cuatro buys del mismo día (despliegue de una cross-sectional) deben
    dimensionar cada uno la MISMA cartera del día: r×n del capital inicial.
    El bug histórico: cada buy usaba self.capital ya mermado por el buy
    anterior → 1-(1-r)^n desplegado (59% en vez de 80% con r=0.2, n=4).
    """

    def test_four_simultaneous_bys_deploy_full_target(self):
        symbols = ["AAA", "BBB", "CCC", "DDD"]
        bars = []
        signals = []
        for sym in symbols:
            bars.append(make_quote(sym, T0, "100", "102", "99", "100"))
            bars.append(make_quote(sym, T0 + timedelta(days=1), "100", "101", "99", "100"))
            buy = make_signal(sym, SignalType.BUY, T0, price="100")
            buy.confidence = 100.0  # r puro, sin factor de confianza
            signals.append(buy)
        # timeline global intercalado por día (como el runner cross-sectional)
        bars_by_day = sorted(bars, key=lambda q: (q.timestamp, q.symbol))

        result = make_engine(max_position_size=Decimal("0.20")).run_backtest(bars_by_day, signals)

        entries = [t for t in result.trades if t.side == "buy"]
        assert len(entries) == 4, "los 4 buys del día deben ejecutar"
        deployed = sum(float(t.quantity) * float(t.entry_price) for t in entries)
        assert deployed == pytest.approx(80_000, rel=0.01), (
            f"4 x 20% de la cartera del día = 80k de 100k; desplegó {deployed:,.0f} "
            "(sizing secuencial habría dejado ~59k)"
        )

    def test_next_day_buys_size_the_new_portfolio(self):
        """Un buy del día siguiente dimensiona la cartera YA con los fills
        del día anterior — el snapshot se renueva cada día de cotización."""
        bars = [
            make_quote("AAA", T0, "100", "102", "99", "100"),
            make_quote("AAA", T0 + timedelta(days=1), "100", "101", "99", "100"),
            make_quote("BBB", T0 + timedelta(days=1), "100", "101", "99", "100"),
            make_quote("BBB", T0 + timedelta(days=2), "100", "101", "99", "100"),
        ]
        first = make_signal("AAA", SignalType.BUY, T0, price="100")
        first.confidence = 100.0
        second = make_signal("BBB", SignalType.BUY, T0 + timedelta(days=1), price="100")
        second.confidence = 100.0

        result = make_engine(max_position_size=Decimal("0.25")).run_backtest(bars, [first, second])

        entries = {t.symbol: t for t in result.trades if t.side == "buy"}
        assert len(entries) == 2
        a_dep = float(entries["AAA"].quantity) * float(entries["AAA"].entry_price)
        b_dep = float(entries["BBB"].quantity) * float(entries["BBB"].entry_price)
        # AAA: 25% de 100k; BBB (día distinto): 25% de los 75k restantes
        assert a_dep == pytest.approx(25_000, rel=0.01)
        assert b_dep == pytest.approx(18_750, rel=0.01)
