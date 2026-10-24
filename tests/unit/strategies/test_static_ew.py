"""Unit tests de la cartera pasiva equal-weight (conclusión del protocolo).

Comportamiento clave: compra TODO el universo en cuanto lo ve, no hace
timing, re-balancea solo al calendario, y cada posición pesa
target_exposure / n (≤ techo del motor).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.domain.models.market_data import Quote
from app.domain.strategies.static_ew import StaticEqualWeightStrategy

T0 = datetime(2020, 1, 1)


def quote(symbol: str, day: int, close: float) -> Quote:
    return Quote(
        symbol=symbol,
        timestamp=T0 + timedelta(days=day),
        open=D(str(close)),
        high=D(str(close)),
        low=D(str(close)),
        close=D(str(close)),
        last=D(str(close)),
        volume=D(100_000),
        bid=D(str(close)),
        ask=D(str(close)),
    )


def feed(strategy, series_by_symbol: dict[str, list[float]]) -> list[tuple[str, str]]:
    out = []
    maxlen = max(len(v) for v in series_by_symbol.values())
    for day in range(maxlen):
        for symbol, closes in series_by_symbol.items():
            if day < len(closes):
                for sig in strategy.generate_signals(quote(symbol, day, closes[day])):
                    raw = sig.signal_type
                    side = raw.value if hasattr(raw, "value") else str(raw)
                    out.append((sig.symbol, str(side)))
    return out


def make(**overrides) -> StaticEqualWeightStrategy:
    cfg = {
        "name": "static_ew",
        "enabled": True,
        "symbols": ["AAA", "BBB", "CCC"],
        "rebalance_days": 30,
        "min_history": 5,
    }
    cfg.update(overrides)
    return StaticEqualWeightStrategy(cfg)


class TestStaticEqualWeight:
    def test_buys_entire_universe(self) -> None:
        s = make()
        up = [100 * (1.001**i) for i in range(40)]
        trades = feed(s, {"AAA": up, "BBB": up, "CCC": up})
        buys = {sym for sym, side in trades if side == "buy"}
        assert buys == {"AAA", "BBB", "CCC"}, "compra todo el universo, sin selección"

    def test_no_timing_on_crash(self) -> None:
        """Un crash del -50% NO expulsa nada: no hay timing, es pasivo."""
        s = make()
        up = [100 * (1.001**i) for i in range(20)]
        crash = up + [up[-1] * (0.97**i) for i in range(1, 30)]
        trades = feed(s, {"AAA": crash, "BBB": crash, "CCC": crash})
        sells = {sym for sym, side in trades if side == "sell"}
        assert not sells, "la cartera estática no vende por crash"

    def test_late_symbol_enters_at_next_rebalance(self) -> None:
        """Un símbolo que empieza a cotizar tarde entra en el siguiente rebalance."""
        s = make(rebalance_days=10)
        early = [100.0 + i for i in range(50)]
        late = [None] * 15 + [50.0 + i for i in range(35)]  # BBB cotiza desde el día 15
        out = []
        for day in range(50):
            for symbol in ("AAA", "BBB", "CCC"):
                closes = late if symbol == "BBB" else early
                if day < len(closes) and closes[day] is not None:
                    for sig in s.generate_signals(quote(symbol, day, closes[day])):
                        raw = sig.signal_type
                        out.append((sig.symbol, raw.value if hasattr(raw, "value") else str(raw)))
        assert ("BBB", "buy") in out, "el símbolo tardío entra en el siguiente rebalance"

    def test_position_weight_is_equal(self) -> None:
        s = make()
        w = [s._position_weight(sym) for sym in ["AAA", "BBB", "CCC"]]
        assert w[0] == w[1] == w[2], "pesos iguales"
        assert w[0] <= 0.25, "por debajo del techo del motor"

    def test_suggested_max_position_ceil_not_floor(self) -> None:
        """El techo debe quedar POR ENCIMA del peso real (ceil, no round)."""
        s = make()
        s.target_exposure = 0.95
        s.universe = ["A", "B", "C", "D"]
        assert s.suggested_max_position_size >= 0.95 / 4
