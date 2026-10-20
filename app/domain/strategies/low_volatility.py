"""Estrategia de anomalía de baja volatilidad (low-volatility anomaly).

Evidencia, no moda:

- Los activos de MENOR volatilidad realizada obtienen retornos iguales o
  superiores a los de mayor volatilidad con mucho menos riesgo (Blitz &
  van Vliet 2007; Baker, Bradley & Wurgler 2011; Frazzini & Pedersen
  "Betting Against Beta" 2014). Es una de las anomalías más robustas
  entre mercados y décadas, y su explicación (apalancamiento limitado,
  preferencia por loterías, benchmarking de gestores) la hace persistente.
- Se implementa como la literatura la testea: cartera equiponderada del
  tramo de menor volatilidad del universo, reequilibrada con poca
  frecuencia (los costes se comen el alfa de la rotación — lección ya
  aprendida con los ETFs de dividendo).
- Universo por defecto: los 11 ETFs sectoriales Vanguard — el efecto
  low-vol es nítido a nivel sectorial (utilities, consumo básico y salud
  frente a tecnología, energía y consumo discrecional).

Volatilidad realizada = desviación típica de log-retornos diarios sobre
`lookback_days`, anualizada. Precios ajustados → incluye distribuciones.

Estrategia CROSS-SECTIONAL: una instancia, timeline global (el runner la
alimenta así por `is_cross_sectional`).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

DEFAULT_CONFIDENCE = 80.0
DEFAULT_LIQUIDITY = 90.0
DEFAULT_PRIORITY = 80.0

#: ETFs sectoriales Vanguard (universo por defecto; configurable)
DEFAULT_UNIVERSE = ["VDC", "VCR", "VDE", "VFH", "VHT", "VIS", "VGT", "VAW", "VNQ", "VPU", "VOX"]
TRADING_DAYS_PER_YEAR = 252
#: techo del validador de tamaño del motor (trade_executor: 5%..25%); por
#: encima, el motor rechaza TODAS las compras en silencio
ENGINE_MAX_POSITION_SIZE = 0.25


class LowVolatilityStrategy(BaseStrategy):
    """Cartera equiponderada del tramo de menor volatilidad realizada."""

    is_cross_sectional = True

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.universe: list[str] = list(config.get("universe") or DEFAULT_UNIVERSE)
        self.top_k: int = int(config.get("top_k", 4))
        self.lookback_days: int = int(config.get("lookback_days", 252))
        self.rebalance_days: int = int(config.get("rebalance_days", 63))
        self.min_history: int = int(config.get("min_history", 200))

        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        close = float(market_data.close if market_data.close else market_data.last)
        series = self._closes.setdefault(market_data.symbol, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []
        series.append((market_data.timestamp, close))

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

    #: días de historia (calendario) antes de la primera señal
    @property
    def suggested_warmup_days(self) -> int:
        return int((self.lookback_days + self.rebalance_days) * 1.6)

    #: tamaño de posición que despliega la cartera completa sin superar el
    #: techo del motor (top_k=4 → 25% cada una = 100% invertido)
    @property
    def suggested_max_position_size(self) -> float:
        return round(min(ENGINE_MAX_POSITION_SIZE, 1.0 / max(1, self.top_k)), 2)

    def get_required_parameters(self) -> list[str]:
        return ["top_k", "lookback_days", "rebalance_days"]

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """La selección por baja volatilidad y el techo de posiciones ya acotan el riesgo."""
        return True

    # ── internos ────────────────────────────────────────────────────

    def _rebalance_due(self, now: datetime) -> bool:
        if self._last_rebalance is None:
            ready = sum(
                1 for s in self.universe if len(self._closes.get(s, ())) >= self.min_history
            )
            return ready >= max(self.top_k, len(self.universe) // 2)
        return (now - self._last_rebalance).days >= self.rebalance_days

    def realized_volatility(self, symbol: str) -> float | None:
        """Volatilidad anualizada de log-retornos diarios sobre `lookback_days`."""
        series = self._closes.get(symbol)
        if not series or len(series) < self.lookback_days + 1:
            return None
        closes = [c for _t, c in series[-(self.lookback_days + 1) :]]
        if any(c <= 0 for c in closes):
            return None
        rets = [math.log(b / a) for a, b in zip(closes[:-1], closes[1:], strict=True)]
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        return math.sqrt(var) * math.sqrt(TRADING_DAYS_PER_YEAR)

    def _target_holdings(self) -> set[str]:
        """Los `top_k` símbolos del universo con menor volatilidad realizada."""
        ranked = sorted(
            (
                (s, v)
                for s, v in ((x, self.realized_volatility(x)) for x in self.universe)
                if v is not None
            ),
            key=lambda kv: kv[1],
        )
        return {s for s, _v in ranked[: self.top_k]}

    def _signal(self, quote: Quote, symbol: str, side: SignalType) -> Signal:
        return Signal(
            symbol=symbol,
            signal_type=side,
            strength=SignalStrength.MODERATE,
            confidence=DEFAULT_CONFIDENCE,
            liquidity_score=DEFAULT_LIQUIDITY,
            priority_score=DEFAULT_PRIORITY,
            source=SignalSource.TECHNICAL,
            price=quote.close if quote.close else quote.last,
            volume=quote.volume,
            timestamp=quote.timestamp,
            metadata={
                "strategy": self.name,
                "realized_volatility": str(self.realized_volatility(symbol)),
                "lookback_days": str(self.lookback_days),
                "top_k": str(self.top_k),
            },
        )
