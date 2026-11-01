"""Conformance scenarios — the engine's honesty, frozen.

Each function returns ``(name, payload)``: a deterministic scenario over
synthetic data whose canonical JSON is byte-compared against a frozen
golden in ``conformance/goldens/``. A scenario regenerating differently
means a fill, a metric or a benchmark definition DRIFTED — the exact
class of silent bug this week produced three times (frozen sleeves run
8fb715, the rf=2% Sharpe convention 0.45-vs-0.71, the optimizer weight
mirror). Idea borrowed from brue's conformance corpus (31-10, owner:
"aplica todo menos lo de ollama").

Rules for scenario data: fixed dates, hand-crafted prices, Decimal
everywhere, no wall clock, no randomness.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.backtesting.engine import BacktestEngine
from app.backtesting.models import BacktestConfig as EngineConfig
from app.domain.models.market_data import Quote
from app.domain.strategies.static_ew import StaticEqualWeightStrategy
from app.domain.strategies.static_weighted import StaticWeightedStrategy

CAPITAL = Decimal("100000")
COMMISSION = Decimal("1.0")
SLIPPAGE = Decimal("0.1")

#: ventana de ejecución: 60 barras tras 25 de warm-up (min_history=20)
WARMUP_START = datetime(2024, 1, 1)
WINDOW_START = datetime(2024, 2, 5)
WINDOW_END = datetime(2024, 5, 3)


def _quote(symbol: str, ts: datetime, close: float, volume: float = 10_000_000.0) -> Quote:
    px = Decimal(str(close))
    vol = Decimal(str(volume))
    return Quote(
        symbol=symbol,
        timestamp=ts,
        open=px,
        high=px,
        low=px,
        close=px,
        volume=vol,
        last=px,
        bid=px,
        ask=px,
    )


def _bars(
    symbol: str, days: list[str], closes: list[float], volumes: list[float] | None = None
) -> list[Quote]:
    vols = volumes or [10_000_000.0] * len(days)
    return [
        _quote(symbol, datetime.fromisoformat(d), c, v)
        for d, c, v in zip(days, closes, vols, strict=True)
    ]


def _trading_days(start: str, n: int) -> list[str]:
    """N business days from `start` (deterministic, weekend-skipping)."""
    from datetime import date, timedelta

    days: list[str] = []
    d = date.fromisoformat(start)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def _r(x: Any, nd: int = 6) -> Any:
    """Canonical rounding: floats → nd decimals (stable bytes everywhere)."""
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: _r(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_r(v, nd) for v in x]
    if isinstance(x, Decimal):
        return round(float(x), nd)
    return x


def _run_engine(strategy: Any, quotes: list[Quote], max_position_size: Decimal) -> dict[str, Any]:
    """The product's engine path: warm-up feeds the strategy, the window
    runs inside the engine loop (same as BacktestOrchestrator — including
    ``signals_valid_from``, without which warm-up consumes the first
    rebalance and the window runs trade-less)."""
    if hasattr(strategy, "signals_valid_from"):
        strategy.signals_valid_from = WINDOW_START
    for q in quotes:
        if q.timestamp < WINDOW_START:
            strategy.generate_signals(q)
    engine = BacktestEngine(
        EngineConfig(
            strategy_name="static_ew",
            initial_capital=CAPITAL,
            max_position_size=max_position_size,
            commission_per_trade=COMMISSION,
            slippage_percentage=SLIPPAGE,
        )
    )
    result = engine.run_backtest(quotes, [], WINDOW_START, WINDOW_END, live_strategy=strategy)
    trades = result.trades if hasattr(result, "trades") else []
    perf = result.performance
    payload: dict[str, Any] = _r(
        {
            "trades": [
                {
                    "symbol": t.symbol,
                    "side": str(t.side),
                    "entry_time": str(t.entry_time)[:19],
                    "entry_price": t.entry_price,
                    "exit_time": str(t.exit_time)[:19] if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "quantity": getattr(t, "quantity", None),
                }
                for t in trades
            ],
            "metrics": {
                "total_return_pct": float(result.total_return or 0),
                "sharpe_ratio": float((getattr(perf, "sharpe_ratio", None) or 0)),
                "max_drawdown": float((getattr(perf, "max_drawdown", None) or 0)),
                "total_trades": int(getattr(perf, "total_trades", len(trades)) or len(trades)),
            },
            "final_positions": {
                s: float(qty) for s, qty in (engine.position_manager.get_all_positions().items())
            },
            "equity_points": len(result.equity_curve or []),
        }
    )
    return payload


# ── escenarios ────────────────────────────────────────────────────────


def scenario_t_plus_1_entry() -> tuple[str, dict[str, Any]]:
    """A signal born on bar N fills at bar N+1's price — never the signal
    bar's. static_ew over two gently-rising symbols; the first BUY must
    land on the first IN-WINDOW bar, one bar after warm-up's last quote."""
    days = _trading_days("2024-01-01", 25 + 60)
    closes_a = [100.0 + i * 0.10 for i in range(len(days))]
    closes_b = [50.0 + i * 0.05 for i in range(len(days))]
    quotes = sorted(
        _bars("AAA", days, closes_a) + _bars("BBB", days, closes_b),
        key=lambda q: (q.timestamp, q.symbol),
    )
    strategy = StaticEqualWeightStrategy({"symbols": ["AAA", "BBB"]})
    payload = _run_engine(strategy, quotes, Decimal("0.50"))
    return "t_plus_1_entry", payload


def scenario_partial_fill_topup() -> tuple[str, dict[str, Any]]:
    """A liquidity-capped buy (≤10% of daily volume) must PARTIALLY fill
    and be topped up on later bars — never frozen short (run 8fb715:
    sleeves stuck at 65% forever). AAA trades tiny volume early, then
    normal; final position must reach the full sleeve."""
    days = _trading_days("2024-01-01", 25 + 60)
    closes_a = [100.0] * len(days)
    closes_b = [50.0] * len(days)
    vols_a = [400.0] * 30 + [10_000_000.0] * (len(days) - 30)  # 400 vol/day early
    quotes = sorted(
        _bars("AAA", days, closes_a, vols_a) + _bars("BBB", days, closes_b),
        key=lambda q: (q.timestamp, q.symbol),
    )
    strategy = StaticEqualWeightStrategy({"symbols": ["AAA", "BBB"]})
    payload = _run_engine(strategy, quotes, Decimal("0.50"))
    return "partial_fill_topup", payload


def scenario_sharpe_convention() -> tuple[str, dict[str, Any]]:
    """The executed Sharpe: marked-to-market equity curve, rf=0, annualized
    ×√252 — the SAME convention as the passive twin (the 0.45-vs-0.71 bug
    was rf=2% on one side only). A smooth 50/50 of a rising and a flat
    sleeve must produce a positive, moderate Sharpe on both conventions."""
    days = _trading_days("2024-01-01", 25 + 120)
    closes_a = []
    px = 100.0
    for i in range(len(days)):
        px *= 1.0 + (0.0009 if i % 3 else -0.0002)  # suave, positivo
        closes_a.append(round(px, 4))
    closes_b = [50.0 + ((i % 7) - 3) * 0.01 for i in range(len(days))]  # plano/ruidoso
    quotes = sorted(
        _bars("AAA", days, closes_a) + _bars("BBB", days, closes_b),
        key=lambda q: (q.timestamp, q.symbol),
    )
    strategy = StaticEqualWeightStrategy({"symbols": ["AAA", "BBB"]})
    payload = _run_engine(strategy, quotes, Decimal("0.50"))

    # referencia independiente: Sharpe rf=0 del universo EW buy&hold
    def _sharpe(rets: list[float]) -> float:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        return mean / math.sqrt(var) * math.sqrt(252) if var > 0 else 0.0

    sleeve_a = {d: c for d, c in zip(days, closes_a, strict=True)}
    sleeve_b = {d: c for d, c in zip(days, closes_b, strict=True)}
    last = {"AAA": 1.0, "BBB": 1.0}
    rets: list[float] = []
    prev = None
    for d in days:
        last["AAA"] = sleeve_a[d] / closes_a[0]
        last["BBB"] = sleeve_b[d] / closes_b[0]
        v = sum(last.values()) / 2
        if prev is not None:
            rets.append(v / prev - 1)
        prev = v
    payload["twin_sharpe_rf0"] = _r(_sharpe(rets))
    return "sharpe_convention", payload


def scenario_weight_override_applies() -> tuple[str, dict[str, Any]]:
    """The optimizer applies params with setattr AFTER __init__ — the
    split must follow the LIVE attribute (the mirror bug: every trial ran
    the default while the twin read the override)."""
    strategy = StaticWeightedStrategy({"symbols": ["VWCE", "AGGH.AS"]})
    payload = {
        "default": {
            "VWCE": strategy._position_weight("VWCE"),
            "AGGH.AS": strategy._position_weight("AGGH.AS"),
            "max_position": strategy.suggested_max_position_size,
        }
    }
    strategy.equity_weight = 0.90
    payload["after_setattr_090"] = {
        "VWCE": strategy._position_weight("VWCE"),
        "AGGH.AS": strategy._position_weight("AGGH.AS"),
        "max_position": strategy.suggested_max_position_size,
    }
    strategy.equity_weight = 0.30
    payload["after_setattr_030"] = {
        "VWCE": strategy._position_weight("VWCE"),
        "AGGH.AS": strategy._position_weight("AGGH.AS"),
        "max_position": strategy.suggested_max_position_size,
    }
    # y el 0.90 EJECUTADO de verdad por el motor (4 trades, manga 89.1%)
    days = _trading_days("2024-01-01", 25 + 20)
    quotes = sorted(
        _bars("VWCE", days, [100.0 + i * 0.05 for i in range(len(days))])
        + _bars("AGGH.AS", days, [50.0 + i * 0.01 for i in range(len(days))]),
        key=lambda q: (q.timestamp, q.symbol),
    )
    executed = StaticWeightedStrategy({"symbols": ["VWCE", "AGGH.AS"]})
    executed.equity_weight = 0.90
    payload["executed_090"] = _run_engine(
        executed, quotes, Decimal(str(executed.suggested_max_position_size))
    )
    return "weight_override_applies", _r(payload)


def scenario_passive_twin() -> tuple[str, dict[str, Any]]:
    """The orchestrator's passive twin: buy&hold of the universe, sleeves
    normalized at their first close, carry-forward across gaps — and for
    a weighted run, THE RUN'S WEIGHTS (a 75/25 execution was once judged
    against a 50/50 twin)."""
    from app.services.backtest_orchestration.backtest_orchestrator import BacktestOrchestrator

    class _StubLoader:
        """sirve las mismas series sintéticas que el twin consumiría"""

        def __init__(self, series: dict[str, list[tuple[datetime, float]]]) -> None:
            self._series = series

        def load_market_data(self, symbol, start, end, timeframe="1d", source="csv"):
            from app.domain.models.market_data import Quote as Q

            out = []
            for ts, px in self._series[symbol]:
                if start <= ts <= end:
                    p = Decimal(str(px))
                    out.append(
                        Q(
                            symbol=symbol,
                            timestamp=ts,
                            open=p,
                            high=p,
                            low=p,
                            close=p,
                            volume=Decimal(1000000),
                            last=p,
                            bid=p,
                            ask=p,
                        )
                    )
            return out

    days = _trading_days("2024-01-01", 300)
    # equity sube +60%, bono cae −5%: el 75/25 debe separarse del 50/50
    closes_eq = [100.0 * (1.0 + 0.6 * i / (len(days) - 1)) for i in range(len(days))]
    closes_bd = [100.0 * (1.0 - 0.05 * i / (len(days) - 1)) for i in range(len(days))]
    series = {
        "EQ": [(datetime.fromisoformat(d), c) for d, c in zip(days, closes_eq, strict=True)],
        "BD": [(datetime.fromisoformat(d), c) for d, c in zip(days, closes_bd, strict=True)],
    }
    loader = _StubLoader(series)

    class _Cfg:
        symbols = ["EQ", "BD"]

    t0 = datetime.fromisoformat(days[0])
    t1 = datetime.fromisoformat(days[-1])
    orch = BacktestOrchestrator()
    ew = orch._load_dividend_benchmark(_Cfg(), loader, t0, t1)  # noqa: SLF001
    wt = orch._load_dividend_benchmark(  # noqa: SLF001
        _Cfg(), loader, t0, t1, weights={"EQ": 0.75, "BD": 0.25}
    )
    if ew is None or wt is None:
        raise RuntimeError("twin scenario failed to build its benchmark series")
    payload = _r(
        {
            "equal_weight": {
                "return_pct": ew["return_pct"],
                "sharpe": ew["sharpe"],
                "buy_hold_return_pct": ew["buy_hold_return_pct"],
                "buy_hold_sharpe": ew["buy_hold_sharpe"],
                "buy_hold_max_dd_pct": ew["buy_hold_max_dd_pct"],
            },
            "weighted_75_25": {
                "return_pct": wt["return_pct"],
                "sharpe": wt["sharpe"],
                "buy_hold_return_pct": wt["buy_hold_return_pct"],
                "buy_hold_sharpe": wt["buy_hold_sharpe"],
                "buy_hold_max_dd_pct": wt["buy_hold_max_dd_pct"],
            },
        }
    )
    return "passive_twin", payload


def scenario_sleeve_book_fsm() -> tuple[str, dict[str, Any]]:
    """The sleeve book as a state machine, driven event by event (idea
    NautilusTrader): rejected stays empty, a partial leaves the sleeve
    incomplete until a top-up crosses 95% of ordered, a sell empties it,
    and an UNMODEDED engine status must NOT corrupt the book (it is
    logged loudly instead — previously it was silently dropped)."""

    strategy = StaticEqualWeightStrategy({"symbols": ["AAA", "BBB"]})

    def _state(sym: str) -> dict[str, Any]:
        return _r(
            {
                "held": sym in strategy._holdings,
                "incomplete": strategy._incomplete_sleeves().get(sym),
                "filled": strategy._filled_qty.get(sym, 0.0),
            }
        )

    steps: dict[str, Any] = {}

    # 1) compra RECHAZADA sin nada en cartera → manga sigue vacía
    strategy._holdings.add("AAA")  # el hold la marca deseada al emitir
    strategy.on_fill("AAA", "buy", "rejected", 1000, 0)
    steps["rejected_from_empty"] = _state("AAA")

    # 2) PARTIAL del 40% → en cartera pero incompleta (falta 60%)
    strategy.on_fill("AAA", "buy", "filled", 1000, 400)
    steps["partial_40pct"] = _state("AAA")

    # 3) top-up de 50% → 90% ejecutado: aún incompleta (<95%)
    strategy.on_fill("AAA", "buy", "filled", 500, 500)
    steps["after_topup_90pct"] = _state("AAA")

    # 4) top-up final → 140% de la orden original ≈ completa
    strategy.on_fill("AAA", "buy", "filled", 100, 100)
    steps["complete"] = _state("AAA")

    # 5) venta → manga vacía de nuevo
    strategy.on_fill("AAA", "sell", "filled", 1000, 1000)
    steps["after_sell"] = _state("AAA")

    # 6) estado NO modelado del motor → el libro no cambia (y loguea)
    strategy.on_fill("AAA", "buy", "expired", 100, 100)
    steps["unknown_status_noop"] = _state("AAA")

    return "sleeve_book_fsm", steps


SCENARIOS = [
    scenario_t_plus_1_entry,
    scenario_partial_fill_topup,
    scenario_sharpe_convention,
    scenario_weight_override_applies,
    scenario_passive_twin,
    scenario_sleeve_book_fsm,
]
