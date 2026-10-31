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
        # el techo por manga es lo DECLARADO (target_exposure/N) hasta 95%:
        # universos anchos siguen bajo el 25% clásico; el par dos-fondos de
        # ACUMULAR necesita 49,5% (31-10) y el viejo 25% dejaba media
        # cartera en caja para siempre
        assert w[0] <= 0.95, "por debajo del techo declarado"
        assert w[0] == round(0.99 / 3, 4)

    def test_two_fund_universe_gets_full_sleeve_weights(self) -> None:
        """FIX 2/31-10: el par ACUMULAR (N=2) despliega 49,5% por manga."""
        s = make()
        s.universe = ["VWCE", "AGGH.AS"]
        assert s._position_weight("VWCE") == 0.495
        assert s.suggested_max_position_size == 0.50

    def test_suggested_max_position_ceil_not_floor(self) -> None:
        """El techo debe quedar POR ENCIMA del peso real (ceil, no round)."""
        s = make()
        s.target_exposure = 0.95
        s.universe = ["A", "B", "C", "D"]
        assert s.suggested_max_position_size >= 0.95 / 4

    def test_rejected_buy_is_retried_not_lost_forever(self) -> None:
        """D05 para el pasivo: una compra rechazada por el cap de liquidez
        del motor debe reconciliarse y re-emitirse en cadencia corta — no
        dejar el sleeve en caja para siempre (VHYL 2016-2026: -30 pp)."""
        s = make(rebalance_days=3650, entry_retry_days=10)
        # día 0: entran los símbolos que cotizan (los 3 en el mismo día)
        out = feed(s, {"AAA": [10.0] * 2, "BBB": [10.0] * 2, "CCC": [10.0] * 2})
        buys = {sym for sym, side in out if side == "buy"}
        assert {"AAA", "BBB"} <= buys  # los primeros en cotizar
        # el motor rechaza la compra de BBB (liquidez)
        s.on_fill("BBB", "buy", "rejected", D("100"), D("0"))
        assert "BBB" not in s._holdings
        # día siguiente: NO re-emite (cadencia corta, no diaria)
        next_out = [s.generate_signals(quote(sym, 2, 10.0)) for sym in ("AAA", "BBB", "CCC")]
        assert not any(sig for sigs in next_out for sig in sigs)
        # tras entry_retry_days: re-emite SOLO lo faltante (BBB y el que aún
        # no hubiera entrado)
        retried = []
        for day in range(3, 20):
            for sym in ("AAA", "BBB", "CCC"):
                for sig in s.generate_signals(quote(sym, day, 10.0)):
                    side = sig.signal_type
                    retried.append((sig.symbol, str(side.value if hasattr(side, "value") else side)))
        assert ("BBB", "buy") in retried, "el sleeve rechazado se reintenta"
        assert "AAA" not in {sym for sym, _ in retried}, "no re-compra lo ya en libro"
        # y el fill la confirma
        s.on_fill("BBB", "buy", "filled", D("100"), D("100"))
        assert "BBB" in s._holdings

    def test_fill_rejection_paths_reconcile_book(self) -> None:
        s = make(rebalance_days=3650)
        feed(s, {"AAA": [10.0], "BBB": [10.0], "CCC": [10.0]})
        s.on_fill("AAA", "buy", "filled", D("1"), D("1"))
        s.on_fill("BBB", "buy", "rejected", D("1"), D("0"))
        assert "AAA" in s._holdings
        assert "BBB" not in s._holdings
        s.on_fill("AAA", "sell", "filled", D("1"), D("1"))
        assert "AAA" not in s._holdings
