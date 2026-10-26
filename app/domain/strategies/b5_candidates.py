"""B5 (T5.2) — 5 candidatas satélite del paper "151 Estrategias de Trading"
(Kakushadze & Serur, docs/b5/paper_151_estrategias_kakushadze_serur.pdf).

Cada clase cita la sección exacta del paper y implementa su fórmula
cerrada; desviaciones documentadas en la propia clase. Todas son
rotaciones transversales del universo del run (mecánica core-satélite:
rebalance al calendario, señal BUY/SELL de la diferencia, pesos por
metadata) evaluadas por el MISMO motor con walk-forward/t+1/costes.

El paper define; el motor valida. Veredicto binario en docs/b5 (T5.4).
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

CONFIDENCE = 90.0
LIQUIDITY = 90.0
PRIORITY = 75.0


class _B5RotationBase(BaseStrategy):
    """Mecánica común: series de cierres + rebalance calendario + diff."""

    is_cross_sectional = True

    #: universo ETF líquido multi-activo por defecto (subclases pueden
    #: especializarlo, p.ej. B5SectorMomentum con sector ETFs)
    # EFA sustituye a EEM (sin CSV local); same developed+EM exposure
    DEFAULT_UNIVERSE = ["SPY", "QQQ", "GLD", "TLT", "EFA", "VNQ", "LQD", "VGK"]

    #: subclases: función de score (None = el símbolo no puntúa)
    def _score(self, symbol: str, now: datetime) -> float | None:
        raise NotImplementedError

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        run_symbols = config.get("symbols")
        self.universe: list[str] = (
            [str(s).upper() for s in run_symbols]
            if run_symbols
            else [str(s).upper() for s in (config.get("universe") or self.DEFAULT_UNIVERSE)]
        )
        self.top_k: int = int(config.get("top_k", 3))
        self.rebalance_days: int = int(config.get("rebalance_days", 63))
        self.min_history: int = int(config.get("min_history", 30))
        self.target_exposure: float = float(config.get("target_exposure", 0.95))
        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None
        self.signals_valid_from: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        symbol = market_data.symbol.upper()
        close = float(market_data.close if market_data.close else market_data.last)
        series = self._closes.setdefault(symbol, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []
        series.append((market_data.timestamp, close))

        if self.signals_valid_from is not None and market_data.timestamp < self.signals_valid_from:
            return []
        if not self._rebalance_due(market_data.timestamp):
            return []
        self._last_rebalance = market_data.timestamp

        desired = self._desired_holdings(market_data.timestamp)
        signals = [
            self._signal(market_data, s, SignalType.SELL) for s in sorted(self._holdings - desired)
        ]
        signals += [
            self._signal(market_data, s, SignalType.BUY) for s in sorted(desired - self._holdings)
        ]
        self._holdings = desired
        return signals

    @property
    def suggested_warmup_days(self) -> int:
        return max(60, self.min_history * 2)

    @property
    def suggested_max_position_size(self) -> float:
        unit = self.target_exposure / max(1, self.top_k)
        return math.ceil(min(0.25, unit) * 100) / 100

    def get_position_size(self, signal: Signal, portfolio: Any) -> Any:
        return signal.metadata.get("position_weight", 1.0 / max(1, self.top_k))

    def get_required_parameters(self) -> list[str]:
        return ["lookback_days", "rebalance_days"]

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        return True

    # ── internos ────────────────────────────────────────────────────

    def _rebalance_due(self, now: datetime) -> bool:
        if self._last_rebalance is None:
            ready = sum(1 for s in self._closes.values() if len(s) >= self.min_history)
            if ready < max(2, len(self.universe) // 2):
                return False
            self._ready_at = now
            return True
        return (now - self._last_rebalance).days >= self.rebalance_days

    def _desired_holdings(self, now: datetime) -> set[str]:
        scored: list[tuple[float, str]] = []
        for symbol in self.universe:
            try:
                value = self._score(symbol, now)
            except (KeyError, IndexError, ValueError):
                value = None
            if value is not None and not math.isnan(value):
                scored.append((value, symbol))
        scored.sort(reverse=True)
        return {s for _, s in scored[: self.top_k]}

    def _closes_before(self, symbol: str, now: datetime) -> list[float]:
        return [c for t, c in self._closes.get(symbol, []) if t <= now]

    def _return_over(
        self, symbol: str, now: datetime, lookback: int, skip: int = 0
    ) -> float | None:
        closes = self._closes_before(symbol, now)
        need = lookback + skip + 1
        if len(closes) < need:
            return None
        end = closes[-1 - skip] if skip else closes[-1]
        start = closes[-1 - skip - lookback]
        if start <= 0:
            return None
        return end / start - 1.0

    def _position_weight(self, symbol: str) -> float:
        return round(min(0.25, max(0.05, self.target_exposure / max(1, self.top_k))), 4)

    def _signal(self, quote: Quote, symbol: str, side: SignalType) -> Signal:
        return Signal(
            symbol=symbol,
            signal_type=side,
            strength=SignalStrength.MODERATE,
            confidence=CONFIDENCE,
            liquidity_score=LIQUIDITY,
            priority_score=PRIORITY,
            source=SignalSource.MOMENTUM,
            price=quote.close if quote.close else quote.last,
            volume=quote.volume,
            timestamp=quote.timestamp,
            metadata={
                "strategy": self.name,
                "position_weight": str(self._position_weight(symbol)),
                "tier": "b5-satellite",
                "paper": self.PAPER_REF,
            },
        )


# ══════════════════════════════════════════════════════════════════


class B5PriceMomentum(_B5RotationBase):
    """§3.1 Precio-momentum (p.41): retorno pasado como señal transversal.

    Long top-k por retorno de `lookback_days` saltando `skip_recent_days`
    (el clásico 12-1 con skip — evitar el efecto reversión de último mes).
    """

    PAPER_REF = "151 Estrategias §3.1 (p.41)"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.lookback_days: int = int(config.get("lookback_days", 252))
        self.skip_recent_days: int = int(config.get("skip_recent_days", 21))

    def _score(self, symbol: str, now: datetime) -> float | None:
        return self._return_over(symbol, now, self.lookback_days, self.skip_recent_days)


class B5MeanReversion(_B5RotationBase):
    """§3.9 Reversión a la media – grupo único (p.48).

    Long BOTTOM-k por retorno corto (se invierte el score): los más caídos
    del ventana corta revierten. Es la dirección contraria a §3.1 y por
    eso diversifica como satélite.
    """

    PAPER_REF = "151 Estrategias §3.9 (p.48)"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.lookback_days: int = int(config.get("lookback_days", 20))

    def _score(self, symbol: str, now: datetime) -> float | None:
        r = self._return_over(symbol, now, self.lookback_days)
        return -r if r is not None else None


class B5MovingAverageFilter(_B5RotationBase):
    """§3.11 Media móvil (p.52): filtro de tendencia precio-vs-MA.

    Mantener los símbolos COTANDO por encima de su media móvil de
    `ma_days` (salir debajo). Top-k entre los que pasan el filtro, por
    distancia a la MA (tendencia más limpia primero).
    """

    PAPER_REF = "151 Estrategias §3.11 (p.52)"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.lookback_days: int = int(config.get("lookback_days", 200))
        self.ma_days: int = int(config.get("ma_days", self.lookback_days))

    def _score(self, symbol: str, now: datetime) -> float | None:
        closes = self._closes_before(symbol, now)
        if len(closes) < self.ma_days:
            return None
        ma = sum(closes[-self.ma_days :]) / self.ma_days
        if ma <= 0:
            return None
        return closes[-1] / ma - 1.0  # solo positivo pasa el filtro


class B5SectorMomentum(B5PriceMomentum):
    """§4.1 Rotación de momentum sectorial (p.66).

    DESVIACIÓN documentada: el paper rota por industrias de acciones vía
    clasificación fundamental; nuestro universo operable son ETFs → los
    SECTOR ETFs son los proxies de sector (XLK/XLE/XLV/…). Misma fórmula
    de momentum §3.1 aplicada a los proxies.
    """

    PAPER_REF = "151 Estrategias §4.1 (p.66) — desviación: sector-ETF proxies"

    # XLY fuera (mismo estilo que XLK en colapso tech); sin XLI/XLP locales
    DEFAULT_UNIVERSE = ["XLK", "XLE", "XLV", "XLF", "XLU", "XLB"]


class B5MomentumCarry(_B5RotationBase):
    """§8.4 Combo de momentum & carry (p.98).

    Long los pares cuyo momentum y carry COINCIDEN en signo, rankeados por
    carry (puntos porcentuales del diferencial base−quote, corpus real de
    B3: data/rates + data/fx). Un par con carry positivo pero momentum
    negativo NO entra — el combo exige acuerdo (la fórmula del paper).
    Universo por defecto: los 7 pares del corpus B3.
    """

    PAPER_REF = "151 Estrategias §8.4 (p.98) — carry real B3"

    DEFAULT_UNIVERSE = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF"]

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.lookback_days: int = int(config.get("lookback_days", 126))
        self.min_history: int = int(config.get("min_history", max(30, self.lookback_days)))

    def _score(self, symbol: str, now: datetime) -> float | None:
        from app.backtesting.fx_history import FxHistory

        momentum = self._return_over(symbol, now, self.lookback_days)
        carry = FxHistory().carry_differential(symbol, now.date())
        if momentum is None or carry is None:
            return None
        if momentum > 0 and carry.rate > 0:
            return float(carry.rate)
        # el caso espejo (momentum<0 Y carry<0) pide CORTAR el par: el
        # motor es long-only y no puede expresarlo → excluido (desviación
        # documentada; el combo exige acuerdo A FAVOR de mantener)
        return None
