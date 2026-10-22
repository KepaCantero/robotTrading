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

import math
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.models.market_data import Quote
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

DEFAULT_CONFIDENCE = 100.0
DEFAULT_LIQUIDITY = 90.0
DEFAULT_PRIORITY = 80.0

#: capas por defecto — núcleo GLOBAL (VT, total world) + satélite pequeño de
#: dividendo (SCHD/VIG crecimiento US, VYMI internacional) + refugio renta fija.
#: La evidencia y la práctica fiscal española favorecen un núcleo global
#: diversificado con un satélite de dividendo reducido, no 5 ETFs de dividendo
#: US solapados (91.7% misma exposición). Los precios son AJUSTADOS: el retorno
#: ya incluye distribuciones; la distinción acumulativo/reparto es fiscal y
#: vive en la documentación de usuario, no en el motor.
DEFAULT_CORE = ["SCHD"]
DEFAULT_SATELLITE = ["VYMI", "VYM", "DVY", "VIG"]
DEFAULT_DEFENSIVE = "BND"

#: yield anual estimado (%) para sesgar la selección hacia renta cuando
#: el objetivo es "maximizar dividendos" — el satélite se rankea por
#: yield × momentum, no solo momentum (que favorece growth de yield bajo)
DIVIDEND_YIELDS: dict[str, float] = {
    "VYMI": 4.2,
    "SPYD": 4.5,
    "DVY": 3.8,
    "HDV": 3.7,
    "PEY": 4.3,
    "SCHD": 3.4,
    "VYM": 3.0,
    "SDY": 2.8,
    "NOBL": 2.4,
    "DLN": 2.0,
    "VIG": 1.8,
    "DGRO": 2.0,
    "DGRW": 1.4,
    "VT": 2.0,
    "SPY": 1.3,
    "BND": 3.2,
    "IDV": 4.0,
    "DWX": 3.5,
    "FGD": 3.6,
    "PID": 4.8,
}

#: clasificación por rol cuando la estrategia recibe el universo del run:
#: high-yield conocido → satélite; renta fija conocida → refugio (primera
#: que aparezca); el resto → núcleo. Universos sin satélites ni refugio
#: (p.ej. el automático del dashboard) degradan a núcleo puro con filtro
#: de momentum — mejor que fallar con cero señales.
_HIGH_YIELD = {"VYM", "DVY", "VYMI", "PEY", "HDV", "SPHD", "SPYD", "IDV", "DWX", "FGD", "PID"}
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
        self.skip_recent_days: int = int(config.get("skip_recent_days", 42))
        self.satellite_top_k: int = int(config.get("satellite_top_k", 2))
        self.rebalance_days: int = int(config.get("rebalance_days", 126))
        self.min_history: int = int(config.get("min_history", 200))
        # Guardias de tendencia por manga (con histéresis y cooldown):
        # - núcleo buy&hold salvo oso PROFUNDO (12-2 < -15%): COVID sí,
        #   2018-Q4/2022 no (evita el látigo que destruía retorno)
        # - satélites high-yield (el tramo frágil): rotación RELATIVA por
        #   yield×momentum en cada rebalance; el timing ABSOLUTO (salir con
        #   momentum negativo) costó 20pp de retorno por 6pp de DD en el
        #   barrido 2016-2026 (95% vs 115%) — desactivado por defecto
        #   (umbrales ±1 = siempre candidatos), disponible vía config
        self.core_exit_momentum: float = float(config.get("core_exit_momentum", -0.15))
        self.core_reentry_momentum: float = float(config.get("core_reentry_momentum", 0.05))
        self.satellite_exit_momentum: float = float(config.get("satellite_exit_momentum", -1.0))
        self.satellite_entry_momentum: float = float(config.get("satellite_entry_momentum", -1.0))
        # Guardia SMA del núcleo (Faber): el momentum 12-2 mide año-contra-año
        # y NO ve los crashes en V (en el fondo COVID SCHD seguía a solo -5%
        # de su precio de hace un año: la guardia de momentum nunca disparó y
        # el núcleo aguantó el -29% entero). El cruce bajo SMA200 sí captura
        # el oso rápido; se evalúa POR BARRA solo del núcleo y con buffer.
        # EXPERIMENTAL y OFF por defecto: el barrido 2016-2026 mostró que los
        # cruces SMA de estos ETFs churnean 58-90 operaciones y destruyen
        # 40-60pp de retorno (52% vs 95-118% sin ella) — cada V-shape de la
        # década castigó el filtro.
        self.sma_guard_days: int = int(config.get("sma_guard_days", 0))
        self.sma_guard_buffer: float = float(config.get("sma_guard_buffer", 0.02))
        # Exposición objetivo de la estrategia: el risk envelope la respeta
        # hasta este tope (estrategias sin declaración siguen al 80%)
        self.target_exposure: float = float(config.get("target_exposure", 0.95))
        # Reparto del exposure entre mangas: núcleo la mitad, satélites casi
        # la otra mitad (VYMI con peso REAL ~20%, no el 4% de antes)
        self.core_share: float = float(config.get("core_share", 0.50))
        self.satellite_share: float = float(config.get("satellite_share", 0.45))

        self._closes: dict[str, list[tuple[datetime, float]]] = {}
        self._holdings: set[str] = set()
        self._guard_exits: set[str] = set()
        self._sma_exits: set[str] = set()
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

        signals: list[Signal] = []

        # Guardia SMA del NÚCLEO por barra (con buffer): único interruptor
        # capaz de ver un crash en V a tiempo. Solo aplica al núcleo.
        sym = market_data.symbol
        if self.sma_guard_days > 0 and sym in self.core_symbols:
            sma = self._sma(sym)
            if sma is not None:
                if sym in self._holdings and close < sma * (1 - self.sma_guard_buffer):
                    signals.append(self._signal(market_data, sym, SignalType.SELL))
                    self._holdings.discard(sym)
                    self._sma_exits.add(sym)
                elif sym in self._sma_exits and close > sma * (1 + self.sma_guard_buffer):
                    signals.append(self._signal(market_data, sym, SignalType.BUY))
                    self._holdings.add(sym)
                    self._sma_exits.discard(sym)

        # La cartera se decide en el rebalance (semiannual por defecto): la
        # rotación por-barra triplicaba las operaciones (30 vs 10) picando
        # en cada cruce de cero del momentum y DESTRUYÓ retorno (35% vs
        # 127% del mismo universo) — la evidencia y la fiscalidad española
        # penalizan cada ida y vuelta.
        if not self._rebalance_due(market_data.timestamp):
            return signals
        self._last_rebalance = market_data.timestamp

        desired = self._desired_holdings()
        signals: list[Signal] = []
        for held in sorted(self._holdings - desired):
            signals.append(self._signal(market_data, held, SignalType.SELL))
        for wanted in sorted(desired - self._holdings):
            signals.append(self._signal(market_data, wanted, SignalType.BUY))
        self._holdings = desired

        return signals

    #: días de historia que necesita antes de la primera señal (calendario)
    @property
    def suggested_warmup_days(self) -> int:
        return int((self.lookback_days + self.skip_recent_days + self.rebalance_days) * 1.6)

    #: tamaño de posición máximo (la unidad de manga mayor, ≤ techo del
    #: validador del motor 25%; por encima rechaza TODAS las compras).
    #: CEIL: el techo debe quedar por encima del peso mayor usado — con
    #: round() hacia abajo, un satélite al 21.38% contra techo 21.0%
    #: rechazaba TODAS las compras satélite del run.
    @property
    def suggested_max_position_size(self) -> float:
        max_unit = max(self._position_weight(s) for s in self.core_symbols + self.satellite_symbols)
        return math.ceil(min(0.25, max_unit) * 100) / 100

    def get_position_size(self, signal: Signal, portfolio: Any) -> Decimal:
        """Fracción de cartera por manga (el motor la usa para el sizing)."""
        return Decimal(str(self._position_weight(signal.symbol)))

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

    def _sma(self, symbol: str) -> float | None:
        """Media móvil simple de cierres de los últimos `sma_guard_days` días."""
        series = self._closes.get(symbol)
        if not series or len(series) < self.sma_guard_days:
            return None
        window = series[-self.sma_guard_days :]
        return sum(price for _ts, price in window) / len(window)

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

    def _desired_holdings(self) -> set[str]:
        """Cartera objetivo con HISTÉRESIS de estado, evaluada solo en rebalance.

        NÚCLEO: buy&hold (la evidencia 1985-2024 le da ~12.4%/yr Sharpe 0.88;
        los filtros de momentum suaves sobre el núcleo REDUJERON el retorno
        aquí: 21% y 12% vs 82% del hold). Única guardia: oso PROFUNDO
        (momentum < core_exit_momentum: COVID sí; 2018-Q4/2022 no) y
        re-entrada solo con recuperación clara (> core_reentry_momentum).

        SATÉLITES: rankeados por YIELD × momentum (momentum solo favorece al
        growth de yield bajo —VIG 1.8% desplaza a VYMI 4.2%— y yield solo
        ignora los crashes). Mantenido mientras momentum > exit (banda de
        histéresis: entró con > +2%, aguanta hasta < -2%) y rotación
        RELATIVA al top-k en cada rebalance.
        """
        target: set[str] = set()

        for sym in self.core_symbols:
            momentum = self._momentum(sym)
            if momentum is None:
                target.add(sym)  # sin historia suficiente: semántica buy&hold
            elif sym in self._holdings:
                if momentum > self.core_exit_momentum:
                    target.add(sym)
                else:
                    self._guard_exits.add(sym)  # expulsado por oso profundo
            elif sym in self._sma_exits:
                continue  # re-entra solo cuando el precio recupere la SMA (por barra)
            elif sym in self._guard_exits:
                if momentum > self.core_reentry_momentum:
                    target.add(sym)
                    self._guard_exits.discard(sym)
            else:
                # despliegue INICIAL: buy&hold — el umbral de re-entrada solo
                # aplica tras una expulsión por oso (si no, un núcleo con
                # momentum +2% en el arranque nunca se compraba y la cartera
                # vivía medio vacía para siempre)
                target.add(sym)

        candidates: list[tuple[str, float]] = []
        for sym in self.satellite_symbols:
            momentum = self._momentum(sym)
            if momentum is None:
                continue
            threshold = (
                self.satellite_exit_momentum
                if sym in self._holdings
                else self.satellite_entry_momentum
            )
            if momentum > threshold:
                candidates.append((sym, DIVIDEND_YIELDS.get(sym, 2.5) / 100.0 * momentum))
        candidates.sort(key=lambda kv: kv[1], reverse=True)
        target |= {sym for sym, _score in candidates[: self.satellite_top_k]}

        return target

    def _position_weight(self, symbol: str) -> float:
        """Peso de la posición como fracción del capital de sizing (5-25%).

        El núcleo reparte `core_share` del target PONDERADO POR YIELD (un
        objetivo de renta pondera por aportación de renta: SCHD 3.4% pesa
        más que VIG 1.8% — y de paso alinea la cartera con sus mejores
        factores); los satélites reparten `satellite_share` entre el top-k
        (el internacional high-yield —VYMI— lleva peso REAL ~20%, no el 4%
        de la cartera uniforme anterior).
        """
        if symbol in self.core_symbols:
            yields = {s: DIVIDEND_YIELDS.get(s, 2.5) for s in self.core_symbols}
            share = yields.get(symbol, 2.5) / max(0.1, sum(yields.values()))
            unit = self.target_exposure * self.core_share * share
        elif symbol == self.defensive_symbol and self.defensive_symbol:
            unit = self.target_exposure * 0.9
        else:
            unit = self.target_exposure * self.satellite_share / max(1, self.satellite_top_k)
        return round(min(0.25, max(0.05, unit)), 4)

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
