"""Estrategia de dividendos core-satellite con filtro anti-crash.

Diseñada según la evidencia, no según la moda:

1. NÚCLEO (core) de compra-y-mantener en ETFs de crecimiento de dividendo
   / aristócratas (VIG, DGRO, DGRW, SCHD): la evidencia de largo plazo
   (1985-2024) les da ~12.4% anualizado con Sharpe 0.88 frente a 11.7%/0.69
   del mercado amplio. La rotación constante NO genera alfa en este sector
   (VectorBT, 37 ETFs: rotación mensual top-5 84.6% vs equal-weight 152.4%,
   IC medio 0.006 ≈ 0).

2. Filtro anti-crash por momentum 12-1 sobre CADA tenencia del núcleo:
   la rotación/momentum en ETFs de dividendo vale para REDUCIR DRAWDOWN
   (37.4% vs 51.9% en la misma evidencia), no para batir al hold. Cuando
   el momentum ajustado de un ETF es negativo, se vende y su peso se
   refugia en el activo defensivo; vuelve a comprarse cuando recupera
   momentum positivo.

3. Satélite (peso menor) en high-yield (VYM, DVY): solo el top-k por
   momentum positivo, porque el high-yield es el tramo más frágil.

Los precios del repo son ajustados por dividendos → el momentum 12-1
incluye las distribuciones, que es exactamente el canal de
"dividend momentum" de Antolín-Díaz, Petrella & Rubio-Ramírez (RFS 2026):
la persistencia del crecimiento del dividendo predice retornos.

Estrategia CROSS-SECTIONAL: una instancia, timeline global (el runner la
alimenta así por `is_cross_sectional`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

DEFAULT_CONFIDENCE = 80.0
DEFAULT_LIQUIDITY = 90.0
DEFAULT_PRIORITY = 80.0

#: capas por defecto (núcleo crecimiento/aristócratas, satélite high-yield,
#: refugio renta fija) — configurables vía config
DEFAULT_CORE = ["VIG", "DGRO", "DGRW", "SCHD"]
DEFAULT_SATELLITE = ["VYM", "DVY"]
DEFAULT_DEFENSIVE = "BND"

#: clasificación por rol cuando la estrategia recibe el universo del run:
#: high-yield conocido → satélite; renta fija conocida → refugio (primera
#: que aparezca); el resto → núcleo. Universos sin satélites ni refugio
#: (p.ej. el automático del dashboard) degradan a núcleo puro con filtro
#: de momentum — mejor que fallar con cero señales.
_HIGH_YIELD = {"VYM", "DVY", "PEY", "HDV", "SPHD"}
_DEFENSIVE_CANDIDATES = ("BND", "BIV", "AGG", "IEF", "SCHZ")


def _classify_universe(symbols: list[str]) -> tuple[list[str], list[str], str]:
    """Split a run universe into (core, satellite, defensive)."""
    unique = list(dict.fromkeys(str(s).upper() for s in symbols))
    satellite = [s for s in unique if s in _HIGH_YIELD]
    defensive = next((s for s in unique if s in _DEFENSIVE_CANDIDATES), "")
    skip = set(satellite) | {defensive}
    core = [s for s in unique if s not in skip]
    return core or unique, satellite, defensive


class DividendCoreSatelliteStrategy(BaseStrategy):
    """Núcleo buy&hold de crecimiento de dividendo + filtro momentum + satélite."""

    is_cross_sectional = True

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        run_symbols = config.get("symbols")
        if run_symbols:
            # el orquestador fija el universo del run: clasificar capas
            core, satellite, defensive = _classify_universe(list(run_symbols))
            self.core_symbols: list[str] = core
            self.satellite_symbols: list[str] = satellite
            self.defensive_symbol: str = defensive
        else:
            self.core_symbols: list[str] = list(config.get("core_symbols") or DEFAULT_CORE)
            self.satellite_symbols: list[str] = list(
                config.get("satellite_symbols") or DEFAULT_SATELLITE
            )
            self.defensive_symbol: str = str(config.get("defensive_symbol") or DEFAULT_DEFENSIVE)
        self.lookback_days: int = int(config.get("lookback_days", 252))
        self.skip_recent_days: int = int(config.get("skip_recent_days", 21))
        self.satellite_top_k: int = int(config.get("satellite_top_k", 1))
        self.rebalance_days: int = int(config.get("rebalance_days", 63))
        self.min_history: int = int(config.get("min_history", 200))

        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None
        #: el runner fija la fecha desde la que las señales son ejecutables;
        #: antes (warm-up) solo se acumula historia para los indicadores —
        #: comprometer holdings pre-ventana desincronizaría la estrategia
        #: del motor (senales descartadas = posiciones fantasma)
        self.signals_valid_from: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        close = float(market_data.close if market_data.close else market_data.last)
        series = self._closes.setdefault(market_data.symbol, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []
        series.append((market_data.timestamp, close))

        if self.signals_valid_from is not None and market_data.timestamp < self.signals_valid_from:
            return []
        if not self._rebalance_due(market_data.timestamp):
            return []
        self._last_rebalance = market_data.timestamp

        target = self._target_holdings()
        signals: list[Signal] = []
        for sym in sorted(self._holdings - target):
            signals.append(self._signal(market_data, sym, SignalType.SELL))
        for sym in sorted(target - self._holdings):
            signals.append(self._signal(market_data, sym, SignalType.BUY))
        self._holdings = target
        return signals

    #: días de historia que necesita antes de la primera señal (calendario)
    @property
    def suggested_warmup_days(self) -> int:
        return int((self.lookback_days + self.skip_recent_days + self.rebalance_days) * 1.6)

    #: tamaño de posición que permite desplegar el núcleo completo, sin
    #: superar el techo del validador del motor (trade_executor: ≤25%; por
    #: encima rechaza TODAS las compras en silencio)
    @property
    def suggested_max_position_size(self) -> float:
        expected = len(self.core_symbols) + self.satellite_top_k + 1
        return round(min(0.25, 1.5 / expected), 2)

    def get_required_parameters(self) -> list[str]:
        return ["lookback_days", "skip_recent_days", "satellite_top_k", "rebalance_days"]

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """El filtro de momentum y el techo de posiciones ya limitan el riesgo."""
        return True

    # ── internos ────────────────────────────────────────────────────

    def _rebalance_due(self, now: datetime) -> bool:
        if self._last_rebalance is None:
            ready = sum(1 for s in self._closes.values() if len(s) >= self.min_history)
            return ready >= max(2, len(self.core_symbols) // 2)
        return (now - self._last_rebalance).days >= self.rebalance_days

    def _momentum(self, symbol: str) -> float | None:
        """Momentum 12-1 sobre precios AJUSTADOS (incluye dividendos)."""
        series = self._closes.get(symbol)
        if not series or len(series) < self.lookback_days + self.skip_recent_days:
            return None
        old = series[-(self.lookback_days + self.skip_recent_days) + 1][1]
        recent = series[-(self.skip_recent_days + 1)][1]
        if old <= 0:
            return None
        return recent / old - 1.0

    def _target_holdings(self) -> set[str]:
        """Núcleo con momentum>0 + refugio si el núcleo se apaga + top-k satélite.

        (Se probó también el filtro SMA-10m de Faber: en este universo
        2016-2026 rindió peor —12% vs 26%—; gana el momentum empíricamente.)
        """
        target: set[str] = set()

        core_momentum = {s: self._momentum(s) for s in self.core_symbols}
        surviving = {s for s, m in core_momentum.items() if m is not None and m > 0}
        target |= surviving

        # núcleo mayormente apagado (crash del sector) → refugio defensivo
        if len(surviving) <= len(self.core_symbols) // 2:
            if self._momentum(self.defensive_symbol) is not None:
                target.add(self.defensive_symbol)

        # satélite: solo top-k con momentum positivo
        sat_ranked = sorted(
            (
                (s, m)
                for s, m in ((x, self._momentum(x)) for x in self.satellite_symbols)
                if m and m > 0
            ),
            key=lambda kv: kv[1],
            reverse=True,
        )
        target |= {s for s, _m in sat_ranked[: self.satellite_top_k]}

        return target

    def _signal(self, quote: Quote, symbol: str, side: SignalType) -> Signal:
        return Signal(
            symbol=symbol,
            signal_type=side,
            strength=SignalStrength.MODERATE,
            confidence=DEFAULT_CONFIDENCE,
            liquidity_score=DEFAULT_LIQUIDITY,
            priority_score=DEFAULT_PRIORITY,
            source=SignalSource.MOMENTUM,
            price=quote.close if quote.close else quote.last,
            volume=quote.volume,
            timestamp=quote.timestamp,
            metadata={
                "strategy": self.name,
                "tier": (
                    "defensive"
                    if symbol == self.defensive_symbol
                    else "core"
                    if symbol in self.core_symbols
                    else "satellite"
                ),
                "lookback_days": str(self.lookback_days),
                "skip_recent_days": str(self.skip_recent_days),
            },
        )
