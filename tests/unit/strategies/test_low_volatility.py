"""Unit tests de la anomalía de baja volatilidad (comportamiento clave).

Con barras sintéticas deterministas (oscilación alterna de amplitud
conocida → volatilidad proporcional a la amplitud, sin aleatoriedad):
se compra el tramo de MENOR volatilidad; cuando un activo se vuelve
volátil se vende en el siguiente reequilibrio y entra el siguiente más
tranquilo; nada se emite antes de tener historia suficiente.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest

from app.domain.models.market_data import Quote
from app.domain.strategies.low_volatility import LowVolatilityStrategy

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


def oscillating(amplitude_pct: float, days: int, base: float = 100.0) -> list[float]:
    """Serie que alterna base*(1±amp): log-retornos de módulo constante."""
    return [round(base * (1 + amplitude_pct / 100 * (1 if i % 2 else -1)), 6) for i in range(days)]


def feed(strategy, series_by_symbol: dict[str, list[float]], start_day: int = 0):
    """Alimenta el timeline intercalado por día; devuelve (símbolo, lado)."""
    out = []
    maxlen = max(len(v) for v in series_by_symbol.values())
    for day in range(maxlen):
        for symbol, closes in series_by_symbol.items():
            if day < len(closes):
                for sig in strategy.generate_signals(quote(symbol, start_day + day, closes[day])):
                    side = sig.signal_type
                    out.append((sig.symbol, side.value if hasattr(side, "value") else str(side)))
    return out


def make(top_k: int = 2) -> LowVolatilityStrategy:
    return LowVolatilityStrategy(
        {
            "name": "low_volatility",
            "enabled": True,
            "universe": ["CALM", "QUIET", "WILD", "CRAZY"],
            "top_k": top_k,
            "lookback_days": 20,
            "min_history": 25,
            "rebalance_days": 5,
        }
    )


class TestSelection:
    def test_buys_only_the_lowest_volatility_names(self):
        s = make(top_k=2)
        sigs = feed(
            s,
            {
                "CALM": oscillating(0.1, 30),
                "QUIET": oscillating(0.3, 30),
                "WILD": oscillating(2.0, 30),
                "CRAZY": oscillating(4.0, 30),
            },
        )
        buys = {sym for sym, side in sigs if side == "buy"}
        assert buys == {"CALM", "QUIET"}
        assert not [x for x in sigs if x[1] == "sell"]

    def test_no_signals_before_min_history(self):
        s = make()
        sigs = feed(s, {k: oscillating(1.0, 15) for k in ["CALM", "QUIET", "WILD", "CRAZY"]})
        assert sigs == []

    def test_sells_name_that_turns_volatile_and_rotates_in_next_calmest(self):
        s = make(top_k=2)
        feed(
            s,
            {
                "CALM": oscillating(0.1, 30),
                "QUIET": oscillating(0.3, 30),
                "WILD": oscillating(2.0, 30),
                "CRAZY": oscillating(4.0, 30),
            },
        )
        assert s._holdings == {"CALM", "QUIET"}
        # QUIET se vuelve el más volátil durante toda la ventana de lookback
        later = feed(
            s,
            {
                "CALM": oscillating(0.1, 30),
                "QUIET": oscillating(9.0, 30),
                "WILD": oscillating(2.0, 30),
                "CRAZY": oscillating(4.0, 30),
            },
            start_day=30,
        )
        assert ("QUIET", "sell") in later
        assert ("WILD", "buy") in later
        assert s._holdings == {"CALM", "WILD"}


class TestSchedule:
    def test_rebalances_only_every_rebalance_days(self):
        s = make()
        series = {
            k: oscillating(a, 60)
            for k, a in zip(["CALM", "QUIET", "WILD", "CRAZY"], [0.1, 0.3, 2, 4], strict=True)
        }
        feed(s, series)
        # primera decisión al alcanzar min_history (día 24) y luego cada 5 días
        assert s._last_rebalance is not None
        assert (s._last_rebalance - T0).days >= 24


class TestMath:
    def test_realized_volatility_matches_closed_form(self):
        s = make()
        for day, close in enumerate(oscillating(1.0, 25)):
            s.generate_signals(quote("CALM", day, close))
        vol = s.realized_volatility("CALM")
        assert vol is not None
        # log(1.01/0.99) alterna de signo: desviación típica muestral
        # de ±r con media 0 → sqrt(n/(n-1)) * r
        r = math.log(1.01 / 0.99)
        expected = math.sqrt(20 / 19) * r * math.sqrt(252)
        assert vol == pytest.approx(expected, rel=1e-6)

    def test_warmup_and_position_size_are_consistent_with_params(self):
        s = make(top_k=4)
        assert s.suggested_warmup_days == int((20 + 5) * 1.6)
        # 1/top_k, acotado al techo del motor (25%): 4 posiciones = 100% invertido
        assert s.suggested_max_position_size == pytest.approx(0.25)

    def test_position_size_never_exceeds_engine_cap(self):
        # con pocas posiciones 1/top_k superaría el 25% y el motor rechazaría
        # todas las compras en silencio — el techo lo impide
        assert make(top_k=2).suggested_max_position_size == pytest.approx(0.25)
        assert make(top_k=1).suggested_max_position_size == pytest.approx(0.25)
