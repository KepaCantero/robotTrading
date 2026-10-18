"""Unit tests del core-satellite de dividendos (comportamiento clave).

Con barras sintéticas deterministas: el núcleo en tendencia alcista se
compra; cuando su momentum 12-1 se vuelve negativo se vende y el refugio
defensivo entra; el satélite solo admite momentum positivo.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal as D

from app.domain.models.market_data import Quote
from app.domain.strategies.dividend_core_satellite import DividendCoreSatelliteStrategy

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
    """Alimenta el timeline intercalado por día; devuelve (símbolo, lado)."""
    out = []
    maxlen = max(len(v) for v in series_by_symbol.values())
    for day in range(maxlen):
        for symbol, closes in series_by_symbol.items():
            if day < len(closes):
                for sig in strategy.generate_signals(quote(symbol, day, closes[day])):
                    raw_type = sig.signal_type
                    side = raw_type.value if hasattr(raw_type, "value") else str(raw_type)
                    out.append((sig.symbol, str(side)))
    return out


def make() -> DividendCoreSatelliteStrategy:
    return DividendCoreSatelliteStrategy(
        {
            "name": "dividend_tracking",
            "enabled": True,
            "core_symbols": ["CORE1", "CORE2"],
            "satellite_symbols": ["SAT1"],
            "defensive_symbol": "DEF",
            "lookback_days": 30,
            "skip_recent_days": 3,
            "min_history": 25,
            "rebalance_days": 5,
        }
    )


class TestDividendCoreSatellite:
    def test_buys_uptrending_core(self) -> None:
        s = make()
        up = [100 * (1.002**i) for i in range(60)]  # +12% en 60 días
        trades = feed(s, {"CORE1": up, "CORE2": up, "SAT1": up, "DEF": [100] * 60})
        buys = {sym for sym, side in trades if side == "buy"}
        assert "CORE1" in buys and "CORE2" in buys
        assert "DEF" not in buys

    def test_crash_exits_core_and_goes_defensive(self) -> None:
        s = make()
        up = [100 * (1.002**i) for i in range(60)]
        crash = up + [up[-1] * (0.98**i) for i in range(1, 40)]  # -55% tras el pico
        flat = [100] * len(crash)
        trades = feed(s, {"CORE1": crash, "CORE2": crash, "SAT1": crash, "DEF": flat})
        sells = {sym for sym, side in trades if side == "sell"}
        defensive_in = ("DEF", "buy") in trades
        assert "CORE1" in sells and "CORE2" in sells, "el crash debe expulsar al núcleo"
        assert defensive_in, "con el núcleo apagado entra el refugio"

    def test_never_buys_negative_momentum(self) -> None:
        s = make()
        down = [100 * (0.998**i) for i in range(70)]  # -13%
        trades = feed(s, {"CORE1": down, "CORE2": down, "SAT1": down, "DEF": [100] * 70})
        buys = {sym for sym, side in trades if side == "buy"}
        assert not (buys & {"CORE1", "CORE2", "SAT1"}), "momentum negativo nunca se compra"
