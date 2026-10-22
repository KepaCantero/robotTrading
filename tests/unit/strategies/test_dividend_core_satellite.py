"""Unit tests del core-satellite de dividendos (comportamiento clave).

Con barras sintéticas deterministas: el núcleo en tendencia alcista se
compra; un oso PROFUNDO (momentum < core_exit_momentum) lo expulsa a
efectivo; un bache superficial (2018-Q4/2022) NO lo expulsa; el satélite
solo admite momentum positivo.
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

    def test_deep_crash_exits_core_to_cash(self) -> None:
        """El oso PROFUNDO (-55%) expulsa el núcleo a EFECTIVO — sin bono.

        El refugio-a-BNO a cadencia de rebalance vendió en el suelo de 2022
        y re-entró tras el rebote (77% vs 127% del mismo run sin él); el
        refugio ahora es simplemente no mantener renta variable en oso
        profundo, y no compra ningún defensivo.
        """
        s = make()
        up = [100 * (1.002**i) for i in range(60)]
        crash = up + [up[-1] * (0.98**i) for i in range(1, 40)]  # -55% tras el pico
        flat = [100] * len(crash)
        trades = feed(s, {"CORE1": crash, "CORE2": crash, "SAT1": crash, "DEF": flat})
        sells = {sym for sym, side in trades if side == "sell"}
        buys = {sym for sym, side in trades if side == "buy"}
        assert "CORE1" in sells and "CORE2" in sells, "el oso profundo debe expulsar al núcleo"
        assert "DEF" not in buys, "no hay compra de defensivo: el refugio es efectivo"

    def test_shallow_dip_keeps_core(self) -> None:
        """Un bache superficial (-10%, tipo 2018-Q4/2022) NO expulsa el núcleo."""
        s = make()
        up = [100 * (1.002**i) for i in range(60)]
        dip = up + [up[-1] * (0.994**i) for i in range(1, 20)]  # -11% tras el pico
        flat = [100] * len(dip)
        trades = feed(s, {"CORE1": dip, "CORE2": dip, "SAT1": dip, "DEF": flat})
        sells = {sym for sym, side in trades if side == "sell"}
        assert "CORE1" not in sells and "CORE2" not in sells, "bache superficial: el núcleo aguanta"

    def test_never_buys_negative_momentum_satellite(self) -> None:
        """Con el filtro absoluto ACTIVADO (config), el satélite con momentum
        negativo nunca se compra; el núcleo sí (buy&hold). Por defecto el
        filtro está OFF (la evidencia 2016-2026: -20pp retorno por +6pp DD).
        """
        s = make()
        s.satellite_entry_momentum = 0.02
        s.satellite_exit_momentum = -0.02
        down = [100 * (0.998**i) for i in range(70)]  # -13%
        trades = feed(s, {"CORE1": down, "CORE2": down, "SAT1": down, "DEF": [100] * 70})
        buys = {sym for sym, side in trades if side == "buy"}
        assert "SAT1" not in buys, "momentum negativo nunca se compra en el satélite"
        assert "CORE1" in buys and "CORE2" in buys, "el núcleo es buy&hold, se compra igual"


class TestWarmupDoesNotCommitPhantomHoldings:
    """El warm-up alimenta indicadores, NO posicionamiento.

    Antes: el primer rebalance durante el warm-up comprometía `_holdings`
    con señales que el runner descartaba (fuera de ventana) → cuando el
    target volvía a ser ese set, target−holdings=∅ y el motor se quedaba
    SIN posición durante años (visto en el run de aceptación 2008-2026:
    equity plana 2011-2015). Ahora `signals_valid_from` corta cualquier
    decisión pre-ventana y el primer rebalance YA EN VENTANA despliega.
    """

    def test_no_signals_before_valid_from_and_full_deploy_after(self):
        s = make()
        s.signals_valid_from = T0 + timedelta(days=30)
        # 30 días de warm-up alcista (el core compraría si se le dejara)
        warmup = feed(
            s,
            {
                "CORE1": [100 + i for i in range(30)],  # días 0-29: TODO antes de valid_from
                "CORE2": [100 + i for i in range(30)],
                "SAT1": [50 + i for i in range(30)],
                "DEF": [40 + i for i in range(30)],
            },
        )
        assert warmup == [], "warm-up no puede emitir señales"
        assert s._holdings == set(), "warm-up no puede comprometer holdings"
        # primeras barras EN ventana (día 31+) → despliegue completo del target
        live = []
        for day in range(31, 45):
            for sym, closes in {
                "CORE1": 131 + (day - 31),
                "CORE2": 131 + (day - 31),
                "SAT1": 81 + (day - 31),
                "DEF": 71 + (day - 31),
            }.items():
                for sig in s.generate_signals(quote(sym, day, float(closes))):
                    side = sig.signal_type
                    live.append((sig.symbol, side.value if hasattr(side, "value") else str(side)))
        buys = {sym for sym, side in live if side == "buy"}
        assert "CORE1" in buys and "CORE2" in buys, (
            "el primer rebalance en ventana despliega el core"
        )


class TestRunUniverseClassification:
    """El orquestador pasa el universo del run vía config["symbols"]; sin
    clasificación la estrategia mira sus capas por defecto (VIG/DGRO/…),
    que pueden no existir en los datos → cero señales (bug del dashboard
    con universo automático: IBEX, QQQ, NVDA…)."""

    def test_deep_universe_classifies_all_three_layers(self):
        s = DividendCoreSatelliteStrategy(
            {"name": "d", "enabled": True, "symbols": ["SDY", "DLN", "DVY", "PEY", "BIV"]}
        )
        assert s.core_symbols == ["SDY", "DLN"]
        assert s.satellite_symbols == ["DVY", "PEY"]
        assert s.defensive_symbol == "BIV"

    def test_ten_year_preset_universe_matches_default_layers(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["VIG", "DGRO", "DGRW", "SCHD", "VYM", "DVY", "BND"],
            }
        )
        assert s.core_symbols == ["VIG", "DGRO", "DGRW", "SCHD"]
        assert s.satellite_symbols == ["VYM", "DVY"]
        assert s.defensive_symbol == "BND"

    def test_arbitrary_universe_degrades_to_pure_core(self):
        s = DividendCoreSatelliteStrategy(
            {"name": "d", "enabled": True, "symbols": ["IBEX", "QQQ", "NVDA", "7203.T"]}
        )
        assert s.core_symbols == ["IBEX", "QQQ", "NVDA", "7203.T"]
        assert s.satellite_symbols == []
        assert s.defensive_symbol == ""

    def test_no_symbols_keeps_explicit_layer_config(self):
        s = make()
        assert s.core_symbols == ["CORE1", "CORE2"]
        assert s.satellite_symbols == ["SAT1"]
        assert s.defensive_symbol == "DEF"

    def test_arbitrary_universe_still_generates_signals(self):
        s = DividendCoreSatelliteStrategy(
            {
                "name": "d",
                "enabled": True,
                "symbols": ["AAA", "BBB"],
                "lookback_days": 30,
                "skip_recent_days": 3,
                "min_history": 25,
                "rebalance_days": 5,
            }
        )
        trades = feed(
            s, {"AAA": [100 + i for i in range(40)], "BBB": [50 + 0.5 * i for i in range(40)]}
        )
        buys = {sym for sym, side in trades if side == "buy"}
        assert buys == {"AAA", "BBB"}, "universo sin satélites: núcleo puro se despliega"
