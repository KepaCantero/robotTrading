"""Cartera pasiva equal-weight con rebalance periódico.

La conclusión ejecutable del protocolo cuantitativo (criterio 6): en
2016-2026, con costes reales, NINGUNA capa de gestión de dividendos batió
al equiponderado estático de su propio universo (momentum satélite: -20pp
de retorno por +6pp de DD; guardia SMA200: -40/-60pp; refugio a bono:
vendió en el suelo de 2022). Cuando el pasivo gana, la recomendación
honesta ES el pasivo — esta estrategia lo convierte en artefacto
backtesteable y desplegable del pipeline en vez de una nota al pie.

Universo: el del run (``symbols``) — no selecciona nada, no filtra nada,
no hace timing. Solo mantiene todo el universo a partes iguales y
re-balancea al calendario (anual por defecto, ≤4 veces/año).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

DEFAULT_CONFIDENCE = 100.0
DEFAULT_LIQUIDITY = 90.0
DEFAULT_PRIORITY = 80.0

DEFAULT_UNIVERSE = ["SCHD", "VYM", "VYMI", "VIG"]


class StaticEqualWeightStrategy(BaseStrategy):
    """Equal-weight buy&hold del universo del run, rebalance al calendario."""

    is_cross_sectional = True

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        run_symbols = config.get("symbols")
        self.universe: list[str] = (
            [str(s).upper() for s in run_symbols]
            if run_symbols
            else list(config.get("universe") or DEFAULT_UNIVERSE)
        )
        self.rebalance_days: int = int(config.get("rebalance_days", 365))
        self.min_history: int = int(config.get("min_history", 20))
        self.target_exposure: float = float(config.get("target_exposure", 0.95))

        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None
        #: el runner fija la fecha desde la que las señales son ejecutables
        #: (warm-up acumula historia; comprometer holdings pre-ventana crea
        #: posiciones fantasma cuando el motor descarta esas señales)
        self.signals_valid_from: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        close = float(market_data.close if market_data.close else market_data.last)
        symbol = market_data.symbol.upper()
        series = self._closes.setdefault(symbol, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []
        series.append((market_data.timestamp, close))

        if self.signals_valid_from is not None and market_data.timestamp < self.signals_valid_from:
            return []
        if not self._rebalance_due(market_data.timestamp):
            return []
        self._last_rebalance = market_data.timestamp

        desired = self._desired_holdings()
        signals: list[Signal] = []
        for held in sorted(self._holdings - desired):
            signals.append(self._signal(market_data, held, SignalType.SELL))
        for wanted in sorted(desired - self._holdings):
            signals.append(self._signal(market_data, wanted, SignalType.BUY))
        self._holdings = desired
        return signals

    #: poca historia necesita: no calcula indicadores, solo cotiza el universo
    @property
    def suggested_warmup_days(self) -> int:
        return int(self.min_history * 2.5)

    #: techo del validador del motor (≤25%): ceil para no quedar por debajo
    #: del peso real (round hacia abajo rechazaba todas las compras)
    @property
    def suggested_max_position_size(self) -> float:
        unit = self.target_exposure / max(1, len(self.universe))
        return math.ceil(min(0.25, unit) * 100) / 100

    def get_position_size(self, signal: Signal, portfolio: Any) -> Any:
        """Fracción de cartera por símbolo (el motor la usa para el sizing)."""
        return signal.metadata.get("position_weight", 1.0 / max(1, len(self.universe)))

    def get_required_parameters(self) -> list[str]:
        return ["rebalance_days"]

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """Sin apalancamiento ni concentración: el riesgo es el del universo."""
        return True

    # ── internos ────────────────────────────────────────────────────

    def _rebalance_due(self, now: datetime) -> bool:
        if self._last_rebalance is None:
            ready = sum(1 for s in self._closes.values() if len(s) >= 1)
            return ready >= min(2, len(self.universe))
        return (now - self._last_rebalance).days >= self.rebalance_days

    def _desired_holdings(self) -> set[str]:
        """Todo símbolo del universo que haya cotizado al menos una vez."""
        return {sym for sym in self.universe if sym in self._closes}

    def _position_weight(self, symbol: str) -> float:
        n = max(1, len(self.universe))
        return round(min(0.25, max(0.05, self.target_exposure / n)), 4)

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
                "target_exposure": str(self.target_exposure),
                "position_weight": str(self._position_weight(symbol)),
                "tier": "static",
                "rebalance_days": str(self.rebalance_days),
            },
        )
