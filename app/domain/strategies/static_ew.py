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

#: una manga cuenta como desplegada cuando su cantidad ejecutada alcanza
#: esta fracción de la cantidad ordenada. El umbral no es 1.0 porque el
#: qty ordenado se fijó contra el equity del día de la orden original y
#: el peso real converge aunque falte un resto de cantidad: 0,95 ≈ ±1pp
#: de peso por manga, y el risk-envelope del motor guarda el lado alto
#: (ningún top-up supera el target_exposure declarado).
_SLEEVE_COMPLETE_FRACTION = 0.95


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
        #: hold por defecto (3650): en ventanas tendenciales con dispersión
        #: recortar al ganador cada año COSTÓ 30 pp (SCHD +253% en
        #: 2016-2026); el pasivo honesto del criterio 6 es comprar y
        #: mantener — el rebalance decenal basta por siglos de horizonte.
        self.rebalance_days: int = int(config.get("rebalance_days", 3650))
        self.entry_retry_days: int = int(config.get("entry_retry_days", 10))
        self.min_history: int = int(config.get("min_history", 20))
        #: 99% desplegado (31-10, owner): el 5% de caja permanente costaba
        #: ~7 pp en 10 años sin comprar nada — 1% de colchón de rebalanceo
        self.target_exposure: float = float(config.get("target_exposure", 0.99))

        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None
        #: despliegue por manga: cantidad ordenada vs ejecutada. Un partial
        #: fill (cap de liquidez del motor) reporta status "filled" con
        #: filled < requested — sin este registro la manga quedaba congelada
        #: al 65% para siempre (IUSQ 17,7% vs 24,75% objetivo, run 8fb715:
        #: +112,3% torcido vs +140,4% con mangas iguales el mismo config)
        self._ordered_qty: dict[str, float] = {}
        self._filled_qty: dict[str, float] = {}
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
        # mangas cortas por partial fills: top-up con el peso RESTANTE — el
        # motor dimensiona position_weight × capital sin restar lo ya en
        # cartera, así que re-emitir el peso completo compraría la manga
        # entera otra vez (overweight). El top-up itera hacia el peso 1/N.
        unit = self._position_weight(market_data.symbol.upper())
        for sym, remaining in self._incomplete_sleeves().items():
            signals.append(
                self._signal(
                    market_data,
                    sym,
                    SignalType.BUY,
                    weight=round(unit * remaining, 4),
                    purpose="top_up",
                )
            )
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

    def on_fill(
        self,
        symbol: str,
        side: str,
        status: str,
        requested_qty: Any,
        filled_qty: Any,
    ) -> None:
        """D05: reconciliar con el libro EJECUTADO. Una compra rechazada
        (p.ej. el cap de liquidez del motor — ≤10% del volumen diario)
        dejaba el sleeve en caja PARA SIEMPRE: el hold pensaba que lo
        tenía y jamás re-emitía (VHYL 2016-2026: sleeve entero sin
        desplegar, -30 pp). El reintento llega por _rebalance_due.

        Un PARTIAL fill (status "filled", filled < requested) también
        dejaba la manga corta para siempre: se marcaba como desplegada y
        nunca se completaba. Aquí se registra lo ejecutado y el top-up
        llega por la misma cadencia de reintento."""
        symbol = str(symbol).upper()
        if status == "rejected":
            if side == "buy":
                # solo es "no desplegada" si NO hay nada en cartera; con un
                # partial previo la manga existe y se reintenta como top-up
                if self._filled_qty.get(symbol, 0.0) <= 0.0:
                    self._holdings.discard(symbol)
            return
        if status == "filled":
            if side == "buy":
                self._holdings.add(symbol)
                try:
                    requested = float(requested_qty or 0)
                    filled = float(filled_qty or 0)
                except (TypeError, ValueError):
                    return
                if requested > 0:
                    self._ordered_qty[symbol] = max(self._ordered_qty.get(symbol, 0.0), requested)
                    self._filled_qty[symbol] = self._filled_qty.get(symbol, 0.0) + filled
            elif side == "sell":
                self._holdings.discard(symbol)

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
        if (now - self._last_rebalance).days >= self.rebalance_days:
            return True
        # Finalización de despliegue: sleeves pendientes (compras rechazadas
        # por liquidez) reintentan en cadencia corta, no esperando un periodo
        # entero de rebalance en caja — así una orden grande se completa en
        # días sucesivos al ≤10% del volumen, como se ejecuta de verdad.
        if self._holdings != self._desired_holdings() or self._incomplete_sleeves():
            return (now - self._last_rebalance).days >= self.entry_retry_days
        return False

    def _incomplete_sleeves(self) -> dict[str, float]:
        """Mangas con cantidad ejecutada corta → fracción que falta.

        ``{symbol: (ordered - filled) / ordered}`` para cada manga en cartera
        cuyo partial fill dejó el despliegue por debajo del objetivo."""
        out: dict[str, float] = {}
        for sym in sorted(self._holdings):
            ordered = self._ordered_qty.get(sym, 0.0)
            filled = self._filled_qty.get(sym, 0.0)
            if ordered > 0 and filled < _SLEEVE_COMPLETE_FRACTION * ordered:
                out[sym] = max(0.0, (ordered - filled) / ordered)
        return out

    def _desired_holdings(self) -> set[str]:
        """Todo símbolo del universo que haya cotizado al menos una vez."""
        return {sym for sym in self.universe if sym in self._closes}

    def _position_weight(self, symbol: str) -> float:
        # peso unitario SIN suelo: en universos anchos (n>19) un suelo del
        # 5% sobresuscribía la cartera (30×5%=150%) y chocaba con el tope
        # del validador — todas las compras rechazadas en bucle y el run
        # terminaba a 0 trades (ACUMULAR 2y, 30-10). El techo del 25%
        # por posición sigue: es el cap real del motor.
        n = max(1, len(self.universe))
        return round(min(0.25, self.target_exposure / n), 4)

    def _signal(
        self,
        quote: Quote,
        symbol: str,
        side: SignalType,
        weight: float | None = None,
        purpose: str = "entry",
    ) -> Signal:
        metadata = {
            "strategy": self.name,
            "target_exposure": str(self.target_exposure),
            "position_weight": str(weight if weight is not None else self._position_weight(symbol)),
            "tier": "static",
            "rebalance_days": str(self.rebalance_days),
        }
        if purpose != "entry":
            metadata["order_purpose"] = purpose
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
            metadata=metadata,
        )
