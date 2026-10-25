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
from datetime import datetime, timedelta
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
    "VHYL": 3.6,
    "IDVY": 4.2,
}

#: clasificación por rol cuando la estrategia recibe el universo del run:
#: high-yield conocido → satélite; renta fija conocida → refugio (primera
#: que aparezca); el resto → núcleo. Universos sin satélites ni refugio
#: (p.ej. el automático del dashboard) degradan a núcleo puro con filtro
#: de momentum — mejor que fallar con cero señales.
_HIGH_YIELD = {
    "VYM",
    "DVY",
    "VYMI",
    "PEY",
    "HDV",
    "SPHD",
    "SPYD",
    "IDV",
    "DWX",
    "FGD",
    "PID",
    "VHYL",
    "IDVY",
}
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
        # D03: tope de peso por posición guiado por el perfil (T3.1
        # max_position_size en %) — por defecto el techo del validador.
        self.weight_cap: float = min(0.25, max(0.05, float(config.get("weight_cap", 0.25))))
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
        # D07: refugio por defecto = EFECTIVO (plan §Fase 4: «refugio
        # predeterminado en efectivo»); el activo defensivo es opt-in.
        self.use_defensive_refuge: bool = bool(config.get("use_defensive_refuge", False))
        # D08: último volumen PROPIO de cada símbolo (la barra disparadora
        # ya no presta su volumen/precio al resto).
        self._last_volume: dict[str, Any] = {}
        # D09: cadencia de rebalance en SESIONES (fechas únicas vistas),
        # no días naturales — "semiannual 126" vuelve a ser medio año real.
        self._sessions_seen: set[str] = set()
        self._sessions_since_rebalance = 0
        # D06: pesos objetivo normalizados de la última cartera + residuo
        # (exposición no asignada que queda explicada en caja).
        self._target_weights: dict[str, float] = {}
        self._weight_residual = 0.0
        # D04: eventos de distribución reales (carga perezosa del corpus).
        self._distributions_cache: dict[str, list[tuple[Any, Any]]] | None = None
        #: el runner fija la fecha desde la que las señales son ejecutables;
        #: antes (warm-up) solo se acumula historia para los indicadores —
        #: comprometer holdings pre-ventana desincronizaría la estrategia
        #: del motor (senales descartadas = posiciones fantasma)
        self.signals_valid_from: datetime | None = None

    # ── BaseStrategy ────────────────────────────────────────────────

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        close = float(market_data.close if market_data.close else market_data.last)
        sym = market_data.symbol
        series = self._closes.setdefault(sym, [])
        if series and series[-1][0] >= market_data.timestamp:
            return []
        series.append((market_data.timestamp, close))
        self._last_volume[sym] = market_data.volume

        # D09: contador de SESIONES (fechas únicas de mercado)
        day = market_data.timestamp.date().isoformat()
        if day not in self._sessions_seen:
            self._sessions_seen.add(day)
            self._sessions_since_rebalance += 1

        if self.signals_valid_from is not None and market_data.timestamp < self.signals_valid_from:
            return []

        signals: list[Signal] = []

        # Guardia SMA del NÚCLEO por barra (con buffer): único interruptor
        # capaz de ver un crash en V a tiempo. Solo aplica al núcleo.
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
        self._sessions_since_rebalance = 0

        desired = self._desired_holdings(market_data.timestamp)
        # D10: las señales de protección (SMA) emitidas esta barra SE
        # CONSERVAN — reiniciar la lista borraba la venta exactamente el
        # día de rebalance y el motor se quedaba la posición.
        for held in sorted(self._holdings - desired):
            signals.append(self._signal(market_data, held, SignalType.SELL))
        for wanted in sorted(desired - self._holdings):
            signals.append(self._signal(market_data, wanted, SignalType.BUY))
        self._holdings = desired
        # D06/D04: pesos objetivo de ESTA cartera (normalizados al
        # exposure, yields point-in-time, clamps con redistribución).
        self._target_weights = self._compute_weights(desired, market_data.timestamp)

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
        return math.ceil(min(self.weight_cap, max_unit) * 100) / 100

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
            # Mayoría del core DECLARADO con historia, suelo 1: el mínimo 2
            # absoluto dejaba mudas para siempre a las carteras mono-core
            # (un universo auto de un solo símbolo nunca cruzaba el gate).
            return ready >= max(1, len(self.core_symbols) // 2)
        # D09: cadencia en SESIONES de mercado (fechas únicas), no días
        # naturales — 126 sesiones ≈ 6 meses reales; 126 días naturales
        # eran ~4 meses y la etiqueta "semiannual" mentía.
        return self._sessions_since_rebalance >= self.rebalance_days

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

    def _desired_holdings(self, now: datetime) -> set[str]:
        """Cartera objetivo con HISTÉRESIS de estado, evaluada solo en rebalance.

        NÚCLEO: buy&hold (la evidencia 1985-2024 le da ~12.4%/yr Sharpe 0.88;
        los filtros de momentum suaves sobre el núcleo REDUJERON el retorno
        aquí: 21% y 12% vs 82% del hold). Única guardia: oso PROFUNDO
        (momentum < core_exit_momentum: COVID sí; 2018-Q4/2022 no) y
        re-entrada solo con recuperación clara (> core_reentry_momentum).

        SATÉLITES: rankeados por YIELD REAL × momentum (D04: yield trailing
        12m de los eventos de distribución CONOCIDOS en `now` — nunca el
        diccionario constante). Mantenido mientras momentum > exit (banda
        de histéresis) y rotación RELATIVA al top-k en cada rebalance.

        REFUGIO (D07): por defecto el peso no usado queda en EFECTIVO (plan
        §Fase 4); con use_defensive_refuge=True el activo defensivo entra
        en el objetivo cuando el núcleo libera sitio.
        """
        target: set[str] = set()

        for sym in self.core_symbols:
            # D10: la expulsión por SMA manda SOBRE cualquier otra rama —
            # el catch-all "momentum None → buy&hold" re-compraba en el
            # mismo rebalance al símbolo que la SMA acababa de vender.
            if sym in self._sma_exits:
                continue  # re-entra solo por barra, cuando recupere la SMA
            momentum = self._momentum(sym)
            if momentum is None:
                target.add(sym)  # sin historia suficiente: semántica buy&hold
            elif sym in self._holdings:
                if momentum > self.core_exit_momentum:
                    target.add(sym)
                else:
                    self._guard_exits.add(sym)  # expulsado por oso profundo
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
                # D04: yield REAL conocido en `now` — sin historial de
                # distribuciones el score degrada a solo-momentum (0.0),
                # nunca un 2.5% inventado.
                yield_t12m = self._t12m_yield(sym, now)
                candidates.append((sym, max(yield_t12m, 0.0) * momentum))
        candidates.sort(key=lambda kv: kv[1], reverse=True)
        target |= {sym for sym, _score in candidates[: self.satellite_top_k]}

        # D07: refugio defensivo OPT-IN — por defecto el peso liberado
        # vive en efectivo (la caja ES el refugio del diseño).
        if (
            self.use_defensive_refuge
            and self.defensive_symbol
            and len(target - set(self.satellite_symbols)) < len(self.core_symbols)
        ):
            target.add(self.defensive_symbol)

        return target

    def _position_weight(self, symbol: str) -> float:
        """Peso de la posición: los pesos NORMALIZADOS del último rebalance
        (D06); antes del primer rebalance, la fórmula sobre el libro
        candidato completo (el probe del orquestador la consulta al
        construir el engine).
        """
        if symbol in self._target_weights:
            return self._target_weights[symbol]
        full = set(self.core_symbols) | set(self.satellite_symbols)
        return self._compute_weights(full, self._last_rebalance or datetime.utcnow()).get(
            symbol, 0.05
        )

    def _compute_weights(self, held: set[str], now: datetime) -> dict[str, float]:
        """Pesos objetivo normalizados (D06+D04).

        Las mangas son fracciones DE LA EXPOSICIÓN (no multiplicadores en
        cascada: 0.95×(0.50+0.45) dejaba 90% declarado y 10% sin explicar).
        El núcleo reparte su manga ponderado por yield REAL trailing-12m
        (D04); los satélites equiponderan su manga; clamps 5–25% con
        REDISTRIBUCIÓN del exceso — lo no asignable queda en `_weight_
        residual` (caja explicada, nunca peso evaporado).
        """
        core = [s for s in self.core_symbols if s in held and s != self.defensive_symbol]
        sats = [s for s in self.satellite_symbols if s in held]
        defensive = (
            self.defensive_symbol
            if self.use_defensive_refuge and self.defensive_symbol in held
            else None
        )

        sleeve_total = self.core_share + self.satellite_share + (0.05 if defensive else 0.0)
        raw: dict[str, float] = {}
        if core:
            yields = {s: self._t12m_yield(s, now) for s in core}
            y_sum = sum(yields.values())
            if y_sum > 0:
                for s in core:
                    raw[s] = self.target_exposure * self.core_share * yields[s] / y_sum
            else:
                # sin datos de distribución: equiponderar (nunca yields
                # constantes inventados)
                for s in core:
                    raw[s] = self.target_exposure * self.core_share / len(core)
        if sats:
            unit = self.target_exposure * self.satellite_share / len(sats)
            for s in sats:
                raw[s] = unit
        if defensive:
            raw[defensive] = self.target_exposure * 0.05
        del sleeve_total

        # clamps 5–25% con redistribución en cascada (máx 4 pasadas)
        weights = dict(raw)
        for _ in range(4):
            cap = self.weight_cap
            clamped_high = {s: w for s, w in weights.items() if w > cap}
            clamped_low = {s: w for s, w in weights.items() if w < 0.05}
            if not clamped_high and not clamped_low:
                break
            free = {}
            for s, w in clamped_high.items():
                weights[s] = cap
                free[s] = w - cap
            for s, w in clamped_low.items():
                weights[s] = 0.05
                free[s] = 0.05 - w
            movable = [s for s in weights if s not in clamped_high and s not in clamped_low]
            movable_space = sum(max(0.0, cap - weights[s]) for s in movable)
            total_free = sum(free.values())
            if total_free <= 0 or not movable or movable_space <= 0:
                break
            grant = min(total_free, movable_space)
            for s in movable:
                weights[s] += grant * (max(0.0, cap - weights[s]) / movable_space)

        self._weight_residual = round(max(0.0, self.target_exposure - sum(weights.values())), 4)
        return {s: round(w, 4) for s, w in weights.items()}

    def _distributions(self, symbol: str) -> list[tuple[Any, Any]]:
        """Eventos de distribución del corpus real (carga perezosa, D04)."""
        if self._distributions_cache is None:
            from app.backtesting.dividends import load_distributions

            self._distributions_cache = {}
            for sym in set(self.core_symbols) | set(self.satellite_symbols):
                events = load_distributions(sym)
                self._distributions_cache[sym] = [(e.ex_date, e.amount_per_share) for e in events]
        return self._distributions_cache.get(symbol, [])

    def _t12m_yield(self, symbol: str, now: datetime) -> float:
        """Yield trailing-12m CONOCIDO en `now` (D04): suma de las
        distribuciones con ex-date en los últimos 365 días dividida por el
        último cierre. Sin historial → 0.0 (dato ausente, no yield ficticio)."""
        events = self._distributions(symbol)
        if not events:
            return 0.0
        cutoff = now - timedelta(days=365)
        total = sum(
            float(amount)
            for ex_date, amount in events
            if cutoff <= datetime.combine(ex_date, datetime.min.time()) <= now
        )
        series = self._closes.get(symbol)
        if not series or total <= 0 or series[-1][1] <= 0:
            return 0.0
        return total / series[-1][1]

    def _signal(self, quote: Quote, symbol: str, side: SignalType) -> Signal:
        # D08: cada señal lleva el precio/volumen/timestamp PROPIO del
        # símbolo (último cierre conocido) — la barra disparadora del
        # rebalance ya no presta su precio al resto de la cartera.
        series = self._closes.get(symbol)
        if series:
            ts, own_close = series[-1]
            price_value: Any = Decimal(str(own_close))
            timestamp_value: Any = ts
        else:
            price_value = quote.close if quote.close else quote.last
            timestamp_value = quote.timestamp
        own_volume = self._last_volume.get(symbol)
        return Signal(
            symbol=symbol,
            signal_type=side,
            strength=SignalStrength.MODERATE,
            confidence=DEFAULT_CONFIDENCE,
            liquidity_score=DEFAULT_LIQUIDITY,
            priority_score=DEFAULT_PRIORITY,
            source=SignalSource.MOMENTUM,
            price=price_value,
            volume=own_volume if own_volume is not None else quote.volume,
            timestamp=timestamp_value,
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
