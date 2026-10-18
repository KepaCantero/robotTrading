"""Estrategia de rotación de ETFs de dividendos.

El objetivo "máximo dividendo" no puede backtestearse con fundamentales
(yields, payout) porque el histórico solo trae OHLCV. La exposición a
dividendos la aporta el propio ETF (VYM, SCHD, DVY...), así que la
estrategia honesta sobre precios es una ROTACIÓN: mantener los N ETFs
del sector dividendo con mejor momentum (retorno 12-1) y rebalancear
trimestralmente. Los ETFs que caen del podio se venden; los que entran
se compran. Sin momentum positivo en ninguno, no se abre posición
(mejor caja que rotar entre perdedores).

Es una estrategia CROSS-SECTIONAL: una única instancia debe ver el
timeline completo de todos los símbolos (el runner del backtest la
alimenta así cuando `is_cross_sectional = True`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType

from .base import BaseStrategy

DEFAULT_CONFIDENCE = 80.0
DEFAULT_LIQUIDITY = 90.0
DEFAULT_PRIORITY = 80.0


class DividendETFRotationStrategy(BaseStrategy):
    """Rotación trimestral de los N ETFs de dividendo con mejor momentum 12-1."""

    #: el runner debe alimentar UNA instancia con todos los símbolos en
    #: orden temporal global (no una instancia por símbolo)
    is_cross_sectional = True

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.lookback_days: int = int(config.get("lookback_days", 252))  # ~12 meses
        self.skip_recent_days: int = int(config.get("skip_recent_days", 21))  # 12-1
        self.top_n: int = int(config.get("top_n", 3))
        self.rebalance_days: int = int(config.get("rebalance_days", 63))  # trimestal
        self.min_symbols: int = int(config.get("min_symbols", 2))

        # estado: serie de cierres por símbolo y rotación vigente
        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._last_rebalance: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        symbol = market_data.symbol
        close = float(market_data.close if market_data.close else market_data.last)
        series = self._closes.setdefault(symbol, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []  # barra duplicada o desordenada
        series.append((market_data.timestamp, close))

        due = self._rebalance_due(market_data.timestamp)
        if not due:
            return []

        ranking = self._momentum_ranking()
        self._last_rebalance = market_data.timestamp
        if not ranking:
            return []

        target = {sym for sym, _score in ranking[: self.top_n]}
        signals: list[Signal] = []

        # vender los que caen del podio (o todo si ningún momentum positivo)
        for sym in sorted(self._holdings - target):
            signals.append(self._signal(market_data, sym, SignalType.SELL))

        # comprar las incorporaciones
        for sym in sorted(target - self._holdings):
            signals.append(self._signal(market_data, sym, SignalType.BUY))

        self._holdings = target
        return signals

    def get_required_parameters(self) -> list[str]:
        """Parámetros tunables (el optimizador los usa como grid)."""
        return ["lookback_days", "skip_recent_days", "top_n", "rebalance_days"]

    def risk_check(self, signal: Signal, portfolio: Any) -> bool:
        """La rotación ya limita exposición (top_n) y solo rota momentum > 0."""
        return True

    # ── internos ────────────────────────────────────────────────────

    def _rebalance_due(self, now: datetime) -> bool:
        if self._last_rebalance is None:
            # primer rebalance solo cuando hay historia suficiente en >=min_symbols
            ready = sum(1 for s in self._closes.values() if len(s) >= self.lookback_days)
            return ready >= self.min_symbols
        return (now - self._last_rebalance).days >= self.rebalance_days

    def _momentum_ranking(self) -> list[tuple[str, float]]:
        """Ranking 12-1 por símbolo; solo momentum positivo entra al podio."""
        ranking: list[tuple[str, float]] = []
        for symbol, series in self._closes.items():
            if len(series) < self.lookback_days + self.skip_recent_days:
                continue
            old = series[-(self.lookback_days + self.skip_recent_days) + 1][1]
            recent = series[-(self.skip_recent_days + 1)][1]
            if old <= 0:
                continue
            momentum = recent / old - 1.0
            if momentum > 0:
                ranking.append((symbol, momentum))
        ranking.sort(key=lambda kv: kv[1], reverse=True)
        return ranking

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
                "rotation_top_n": str(self.top_n),
                "lookback_days": str(self.lookback_days),
                "skip_recent_days": str(self.skip_recent_days),
            },
        )
