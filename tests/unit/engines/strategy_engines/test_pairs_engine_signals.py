"""Tests del comportamiento de señales del engine de pairs (gates arreglados).

La suite histórica test_pairs_engine.py falla en árbol limpio (parchea un
import inexistente y fixtures con modelos inválidos — deuda preexistente de
la zona engines); esta suite cubre lo que el camino productivo necesita:
que las puertas de cointegración ABRAN y las señales existan.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal as D

from app.domain.models.market_data import Quote
from app.engines.strategy_engines.pairs_engine import PairsTradingStrategyEngine

T0 = datetime(2020, 1, 1)


def quote(symbol: str, day: int, close: float) -> Quote:
    return Quote(
        symbol=symbol,
        timestamp=T0 + timedelta(days=day),
        open=D(str(round(close, 4))),
        high=D(str(round(close, 4))),
        low=D(str(round(close, 4))),
        close=D(str(round(close, 4))),
        last=D(str(round(close, 4))),
        volume=D(1_000_000),
        bid=D(str(round(close, 4))),
        ask=D(str(round(close, 4))),
    )


def make(**cfg) -> PairsTradingStrategyEngine:
    base = {"name": "pairs_trading", "enabled": True, "pair_symbols": ["AAA", "BBB"]}
    base.update(cfg)
    return PairsTradingStrategyEngine(base)


def cointegrated_series(days: int, seed: int = 7) -> tuple[list[float], list[float]]:
    """AAA = 2·BBB + ruido estacionario: par cointegrado por construcción."""
    rng = random.Random(seed)
    bbb, noise = 100.0, 0.0
    aaa_series, bbb_series = [], []
    for _ in range(days):
        bbb *= 1 + rng.gauss(0, 0.01)
        noise = 0.6 * noise + rng.gauss(0, 1.5)  # AR(1) estacionario
        aaa_series.append(2.0 * bbb + noise + 5.0)
        bbb_series.append(bbb)
    return aaa_series, bbb_series


def side_of(signal) -> str:
    raw = signal.signal_type
    return raw.value if hasattr(raw, "value") else str(raw)


class TestPairsGatesOpen:
    def test_cointegrated_pair_emits_signals(self) -> None:
        """Un par cointegrado por construcción debe generar señales.

        Antes de arreglar las puertas (estadístico ADF comparado como
        p-value, spread sin cubrir, p-value cuantizado) este test era
        imposible: 10 años de AAPL/MSFT real daban CERO señales.
        """
        s = make()
        aaa, bbb = cointegrated_series(400)
        signals = []
        for day in range(len(aaa)):
            for sig in s.generate_signals(quote("AAA", day, aaa[day])):
                signals.append(("AAA", side_of(sig)))
            for sig in s.generate_signals(quote("BBB", day, bbb[day])):
                signals.append(("BBB", side_of(sig)))
        assert signals, "un par cointegrado con excursiones de z debe emitir señales"
        # las piernas deben ser OPUESTAS cuando ambas cotizan la señal
        sells = {sym for sym, side in signals if side == "sell"}
        buys = {sym for sym, side in signals if side == "buy"}
        assert sells and buys, "el par abre ambas piernas"

    def test_is_cross_sectional(self) -> None:
        """El engine necesita el timeline intercalado de ambos símbolos."""
        assert make().is_cross_sectional is True

    def test_cointegration_refreshes(self) -> None:
        """El p-value no queda congelado: se re-testea cada N barras."""
        s = make()
        aaa, bbb = cointegrated_series(150)
        for day in range(120):
            s.generate_signals(quote("AAA", day, aaa[day]))
            s.generate_signals(quote("BBB", day, bbb[day]))
        first = s.cached_cointegration_score
        assert first is not None, "el test de cointegración debe haber corrido"
        for day in range(120, 120 + s._COINTEGRATION_REFRESH_BARS + 5):
            s.generate_signals(quote("AAA", day, aaa[day % 120]))
            s.generate_signals(quote("BBB", day, bbb[day % 120]))
        # el contador de barras rueda (no se quedó en el valor inicial)
        assert s._bars_since_cointegration < s._COINTEGRATION_REFRESH_BARS


class TestFallbackPValueContinuous:
    def test_strongly_stationary_returns_below_one_percent(self) -> None:
        """El p-value del fallback debe ser CONTINUO por debajo de 0.01.

        La cuantización anterior ({0.01, 0.05, 0.10}) hacía p < 0.01
        matemáticamente imposible incluso para ruido blanco puro.
        """
        import numpy as np

        from app.shared.performance.statsmodels_fallback import adfuller

        rng = np.random.default_rng(3)
        white_noise = rng.normal(0, 1, 500)
        result = adfuller(white_noise)
        assert result[1] < 0.01, f"ruido blanco debería dar p<0.01, dio {result[1]}"
        # y una caminata aleatoria (no estacionaria) debe dar p ALTO
        walk = np.cumsum(rng.normal(0, 1, 500))
        assert adfuller(walk)[1] > 0.05, "una caminata aleatoria no es estacionaria"
