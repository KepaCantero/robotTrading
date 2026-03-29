"""
Covered Call Strategy - Estrategia Principal

Estrategia completa de covered calls que hereda de BaseStrategy
e implementa la lógica de generación de señales basada en análisis de opciones.

Objetivo: INCOME_GENERATION
- Generar ingreso adicional vendiendo opciones call
- Mantener posición larga en activos de calidad
- Gestión activa de rolling y assignment

SOLID Principles:
- Single Responsibility: Coordinar componentes, no implementar lógica específica
- Open/Closed: Extensible sin modificar
- Liskov Substitution: Compatible con BaseStrategy
- Interface Segregation: Interfaces mínimas
- Dependency Inversion: Depende de abstracciones
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Union

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy
from app.shared.config.centralized_config import get_config

from .greeks_calculator import GreeksCalculator
from .models import (
    AssignmentProbability,
    CallOption,
    CoveredCallConfig,
    CoveredCallPosition,
    RollDecision,
)
from .option_screener import OptionScreener, OptionScreeningCriteria
from .position_manager import PositionManager
from .roll_analyzer import RollAnalyzer

if TYPE_CHECKING:
    from datetime import date

logger = logging.getLogger(__name__)


class CoveredCallStrategy(BaseStrategy):
    """
    Estrategia de covered calls.

    Implementa una estrategia completa de generación de ingresos
    a través de la venta de opciones de compra cubiertas.

    Características:
    - Screening de opciones óptimas
    - Gestión de posiciones covered call
    - Análisis de rolling
    - Cálculo de Greeks y probabilidades

    Attributes:
        config: Configuración de la estrategia
        strategy_config: Configuración parseada (CoveredCallConfig)
        screener: Screener de opciones
        position_manager: Gestor de posiciones
        roll_analyzer: Analizador de rolling
        greeks_calculator: Calculador de Greeks
    """

    def __init__(self, config: dict[str, Union[str, int, float, Decimal, bool]]):
        """
        Inicializar estrategia de covered calls.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Parsear configuración
        self.strategy_config = self._parse_config(config)

        # Inicializar componentes
        self.greeks_calculator = GreeksCalculator()

        # Usar configuración centralizada para multiplicadores de moneyness
        centralized_config = get_config()
        min_moneyness_multiplier = Decimal(
            str(getattr(centralized_config.trading, "covered_call_min_moneyness_multiplier", 0.5))
        )
        max_moneyness_multiplier = Decimal(
            str(getattr(centralized_config.trading, "covered_call_max_moneyness_multiplier", 2.0))
        )

        screening_criteria = OptionScreeningCriteria(
            min_days_to_expiry=max(7, self.strategy_config.target_dte - 15),
            max_days_to_expiry=min(90, self.strategy_config.target_dte + 30),
            min_moneyness=self.strategy_config.target_otm_pct * min_moneyness_multiplier,
            max_moneyness=self.strategy_config.target_otm_pct * max_moneyness_multiplier,
            min_premium=self.strategy_config.min_premium_pct,
        )

        self.screener = OptionScreener(
            criteria=screening_criteria,
            greeks_calculator=self.greeks_calculator,
        )

        self.position_manager = PositionManager(
            config=self.strategy_config,
            greeks_calculator=self.greeks_calculator,
        )

        self.roll_analyzer = RollAnalyzer(
            greeks_calculator=self.greeks_calculator,
        )

        # Estado interno
        self.available_options: dict[str, list[CallOption]] = {}
        self.last_scan_date: Optional[date] = None

        # Métricas de rendimiento
        self.total_premium_collected = Decimal("0")
        self.positions_opened = 0
        self.positions_closed = 0

        logger.info(
            f"✅ CoveredCallStrategy inicializada: "
            f"objetivo=INCOME_GENERATION, "
            f"target_DTE={self.strategy_config.target_dte}, "
            f"target_OTM={self.strategy_config.target_otm_pct:.1%}, "
            f"min_premium={self.strategy_config.min_premium_pct:.1%}"
        )

    def _parse_config(
        self, raw_config: dict[str, Union[str, int, float, Decimal, bool]]
    ) -> CoveredCallConfig:
        """
        Parsear configuración desde dict.

        Args:
            raw_config: Configuración raw

        Returns:
            Configuración validada
        """
        try:
            # Valores por defecto - usar configuración centralizada
            centralized_config = get_config()

            defaults = {
                "name": "CoveredCallStrategy",
                "description": "Estrategia de covered calls",
                "version": "1.0.0",
                "max_position_size": Decimal(
                    str(getattr(centralized_config.trading, "covered_call_max_position_size", 0.10))
                ),
                "max_contracts_per_position": 10,
                "min_shares_required": 100,
                "target_dte": 30,
                "target_otm_pct": Decimal(
                    str(getattr(centralized_config.trading, "covered_call_target_otm_pct", 0.03))
                ),
                "min_premium_pct": Decimal(
                    str(getattr(centralized_config.trading, "covered_call_min_premium_pct", 0.01))
                ),
                "roll_threshold_days": 7,
                "roll_threshold_itm": Decimal(
                    str(
                        getattr(centralized_config.trading, "covered_call_roll_threshold_itm", 0.02)
                    )
                ),
                "roll_threshold_otm": Decimal(
                    str(
                        getattr(centralized_config.trading, "covered_call_roll_threshold_otm", 0.05)
                    )
                ),
                "assignment_probability_threshold": AssignmentProbability.HIGH,
                "auto_roll": False,
                "avoid_earnings": True,
            }

            # Merge con config provisto
            merged = {**defaults, **raw_config}

            # Convertir a Decimals donde necesario
            for key in [
                "max_position_size",
                "target_otm_pct",
                "min_premium_pct",
                "roll_threshold_itm",
                "roll_threshold_otm",
            ]:
                if (
                    key in merged
                    and merged[key] is not None
                    and not isinstance(merged[key], Decimal)
                ):
                    merged[key] = Decimal(str(merged[key]))

            return CoveredCallConfig(**merged)

        except Exception as e:
            logger.error(f"Error parseando config: {e}")
            return CoveredCallConfig()

    def generate_signals(self, market_data: Quote) -> list[Signal]:
        """
        Generar señales de trading basadas en covered calls.

        Esta estrategia genera señales cuando:
        - Hay oportunidad de abrir nueva posición covered call
        - Se debe hacer roll de una posición existente
        - Se debe cerrar una posición (assignment o manual)

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        if not self.is_active:
            logger.debug("Estrategia inactiva, no se generan señales")
            return []

        symbol = market_data.symbol

        # Obtener precio
        current_price = market_data.close if hasattr(market_data, "close") else market_data.price

        signals = []

        # 1. Verificar si debemos abrir nueva posición
        open_signal = self._evaluate_open_position(market_data)
        if open_signal:
            signals.append(open_signal)

        # 2. Verificar posiciones existentes para rolling/cierre
        positions = self.position_manager.get_positions_by_symbol(symbol)

        for position in positions:
            # Actualizar posición con precio actual
            self.position_manager.update_position(
                symbol=symbol,
                expiry_date=position.call_option.expiry_date,
                strike=position.call_option.strike,
                current_price=current_price,
            )

            # Evaluar roll
            roll_decision = self.position_manager.should_roll_position(
                symbol=symbol,
                expiry_date=position.call_option.expiry_date,
                strike=position.call_option.strike,
                current_price=current_price,
            )

            if roll_decision.should_roll:
                # Crear señal de roll
                roll_signal = self._create_roll_signal(position, roll_decision, market_data)
                signals.append(roll_signal)

            # Evaluar cierre por alta probabilidad de assignment
            elif position.assignment_probability == AssignmentProbability.VERY_HIGH:
                close_signal = self._create_close_signal(
                    position, "high_assignment_probability", market_data
                )
                signals.append(close_signal)

        return signals

    def _evaluate_open_position(self, market_data: Quote) -> Optional[Signal]:
        """
        Evaluar si abrir nueva posición covered call.

        Args:
            market_data: Datos de mercado

        Returns:
            Señal de apertura o None
        """
        symbol = market_data.symbol

        # Verificar si ya tenemos posición en este símbolo
        existing = self.position_manager.get_positions_by_symbol(symbol)
        if existing:
            return None  # Ya tenemos posición

        # Obtener opciones disponibles
        options = self.available_options.get(symbol, [])
        if not options:
            return None  # No hay opciones disponibles

        # Screening de opciones
        current_price = market_data.close if hasattr(market_data, "close") else market_data.price

        best_options = self.screener.get_best_option(
            options=options,
            underlying_price=current_price,
            top_n=1,
        )

        if not best_options:
            return None  # No pasaron el screening

        best_option = best_options[0]

        # Crear señal de apertura (BUY to open covered call)
        # La señal principal es BUY del subyacente
        signal = Signal(
            symbol=symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=65.0,
            source=SignalSource.FUNDAMENTAL,
            price=current_price,
            volume=market_data.volume if hasattr(market_data, "volume") else Decimal("1000000"),
            metadata={
                "reason": "covered_call_opportunity",
                "strategy": "covered_calls",
                "target_strike": str(best_option.strike),
                "expiry_date": best_option.expiry_date.isoformat(),
                "days_to_expiry": best_option.days_to_expiry,
                "option_bid": str(best_option.bid) if best_option.bid else None,
                "premium_pct": (
                    str(float(best_option.mid_price or 0) / float(current_price) * 100)
                    if best_option.mid_price
                    else None
                ),
                "delta": (
                    best_option.metadata.get("delta") if hasattr(best_option, "metadata") else None
                ),
                "theta": (
                    best_option.metadata.get("theta") if hasattr(best_option, "metadata") else None
                ),
            },
        )

        logger.info(
            f"📊 Oportunidad covered call: {symbol} "
            f"strike=${best_option.strike}, DTE={best_option.days_to_expiry}"
        )

        return signal

    def _create_roll_signal(
        self,
        position: CoveredCallPosition,
        roll_decision: RollDecision,
        market_data: Quote,
    ) -> Signal:
        """
        Crear señal de rolling.

        Args:
            position: Posición actual
            roll_decision: Decisión de roll
            market_data: Datos de mercado

        Returns:
            Señal de rolling
        """
        current_price = market_data.close if hasattr(market_data, "close") else market_data.price

        # El rolling se implementa como:
        # 1. BUY to close (cerrar opción corta)
        # 2. SELL to open (abrir nueva opción)
        # Para simplificar, generamos una señal HOLD con metadata de roll

        signal = Signal(
            symbol=position.symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.MODERATE,
            confidence=float(roll_decision.confidence),
            liquidity_score=75.0,
            priority_score=float(roll_decision.confidence) * 0.8,
            source=SignalSource.FUNDAMENTAL,
            price=current_price,
            volume=market_data.volume if hasattr(market_data, "volume") else Decimal("1000000"),
            metadata={
                "reason": "roll_covered_call",
                "strategy": "covered_calls",
                "roll_type": roll_decision.roll_type.value if roll_decision.roll_type else None,
                "current_strike": str(position.call_option.strike),
                "current_expiry": position.call_option.expiry_date.isoformat(),
                "new_strike": str(roll_decision.new_strike) if roll_decision.new_strike else None,
                "new_expiry": (
                    roll_decision.new_expiry.isoformat() if roll_decision.new_expiry else None
                ),
                "roll_reason": roll_decision.reason,
                "confidence": str(roll_decision.confidence),
            },
        )

        logger.info(
            f"🔄 Roll recomendado: {position.symbol} "
            f"{roll_decision.roll_type.value if roll_decision.roll_type else 'unknown'}"
        )

        return signal

    def _create_close_signal(
        self,
        position: CoveredCallPosition,
        reason: str,
        market_data: Quote,
    ) -> Signal:
        """
        Crear señal de cierre.

        Args:
            position: Posición a cerrar
            reason: Razón del cierre
            market_data: Datos de mercado

        Returns:
            Señal de cierre
        """
        current_price = market_data.close if hasattr(market_data, "close") else market_data.price

        signal = Signal(
            symbol=position.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.STRONG,
            confidence=85.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.FUNDAMENTAL,
            price=current_price,
            volume=market_data.volume if hasattr(market_data, "volume") else Decimal("1000000"),
            metadata={
                "reason": reason,
                "strategy": "covered_calls",
                "strike": str(position.call_option.strike),
                "expiry": position.call_option.expiry_date.isoformat(),
                "assignment_probability": position.assignment_probability.value,
            },
        )

        logger.warning(f"⚠️ Cierre recomendado: {position.symbol} razón={reason}")

        return signal

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar si la señal pasa criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio

        Returns:
            True si la señal pasa el risk check
        """
        # Verificar exposición total - usar configuración centralizada
        centralized_config = get_config()
        max_total_exposure = Decimal(
            str(getattr(centralized_config.trading, "covered_call_max_total_exposure", 0.30))
        )

        # Calcular exposición actual
        current_exposure = Decimal("0")
        for pos in portfolio.positions:
            if pos.symbol in [p.symbol for p in self.position_manager.get_all_positions()]:
                current_exposure += pos.value / portfolio.total_value

        # Verificar si nueva señal excedería
        if signal.signal_type == SignalType.BUY:
            potential_exposure = current_exposure + self.strategy_config.max_position_size

            if potential_exposure > max_total_exposure:
                logger.debug(
                    f"Exposición máxima alcanzada: {potential_exposure:.1%} > {max_total_exposure:.1%}"
                )
                return False

        return True

    def get_required_parameters(self) -> list[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de nombres de parámetros requeridos
        """
        return [
            "target_dte",
            "target_otm_pct",
            "min_premium_pct",
            "max_position_size",
        ]

    def validate_config(self) -> bool:
        """
        Validar configuración de la estrategia.

        Returns:
            True si la configuración es válida
        """
        try:
            # Validar DTE
            if not (7 <= self.strategy_config.target_dte <= 90):
                logger.error("target_dte debe estar entre 7 y 90")
                return False

            # Usar configuración centralizada para rangos de validación
            centralized_config = get_config()

            # Validar OTM
            min_otm = Decimal(
                str(getattr(centralized_config.trading, "covered_call_min_otm_pct", 0.01))
            )
            max_otm = Decimal(
                str(getattr(centralized_config.trading, "covered_call_max_otm_pct", 0.20))
            )
            if not (min_otm <= self.strategy_config.target_otm_pct <= max_otm):
                logger.error(f"target_otm_pct debe estar entre {min_otm:.1%} y {max_otm:.1%}")
                return False

            # Validar prima mínima
            min_premium = Decimal(
                str(getattr(centralized_config.trading, "covered_call_min_premium_lower", 0.005))
            )
            max_premium = Decimal(
                str(getattr(centralized_config.trading, "covered_call_min_premium_upper", 0.10))
            )
            if not (min_premium <= self.strategy_config.min_premium_pct <= max_premium):
                logger.error(
                    f"min_premium_pct debe estar entre {min_premium:.1%} y {max_premium:.1%}"
                )
                return False

            # Validar tamaño de posición
            min_pos = Decimal(
                str(getattr(centralized_config.trading, "covered_call_min_position_size", 0.01))
            )
            max_pos = Decimal(
                str(getattr(centralized_config.trading, "covered_call_max_position_upper", 0.50))
            )
            if not (min_pos <= self.strategy_config.max_position_size <= max_pos):
                logger.error(f"max_position_size debe estar entre {min_pos:.1%} y {max_pos:.1%}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validando config: {e}")
            return False

    # ========================================================================
    # MÉTODOS DE GESTIÓN DE OPCIONES Y POSICIONES
    # ========================================================================

    def set_available_options(self, options: list[CallOption]) -> None:
        """
        Establecer opciones disponibles para un símbolo.

        Args:
            options: Lista de opciones disponibles
        """
        if not options:
            return

        symbol = options[0].symbol
        self.available_options[symbol] = options

        logger.debug(f"Opciones actualizadas: {symbol} - {len(options)} opciones")

    def create_covered_call_position(
        self,
        symbol: str,
        shares_owned: int,
        average_cost: Decimal,
        current_price: Decimal,
        strike: Optional[Decimal] = None,
        dte: Optional[int] = None,
    ) -> Optional[CoveredCallPosition]:
        """
        Crear una posición covered call.

        Args:
            symbol: Símbolo del activo
            shares_owned: Acciones poseídas
            average_cost: Costo promedio
            current_price: Precio actual
            strike: Strike objetivo (None = auto)
            dte: DTE objetivo (None = usa config)

        Returns:
            Posición creada o None
        """
        # Obtener opciones disponibles
        options = self.available_options.get(symbol, [])
        if not options:
            logger.warning(f"No hay opciones disponibles para {symbol}")
            return None

        # Filtrar por DTE si se especifica
        target_dte = dte if dte is not None else self.strategy_config.target_dte

        # Filtrar opciones
        filtered_options = [opt for opt in options if abs(opt.days_to_expiry - target_dte) <= 15]

        # Seleccionar strike
        if strike is not None:
            filtered_options = [opt for opt in filtered_options if opt.strike == strike]
        else:
            # Usar target OTM
            target_strike = current_price * (1 + self.strategy_config.target_otm_pct)
            # Usar configuración centralizada para tolerancia de strike
            centralized_config = get_config()
            strike_tolerance = Decimal(
                str(getattr(centralized_config.trading, "covered_call_strike_tolerance", 0.02))
            )
            filtered_options = [
                opt
                for opt in filtered_options
                if abs(opt.strike - target_strike) <= current_price * strike_tolerance
            ]

        if not filtered_options:
            logger.warning(f"No hay opciones que coincidan con criterios para {symbol}")
            return None

        # Seleccionar la mejor
        best = self.screener.get_best_option(
            options=filtered_options,
            underlying_price=current_price,
            top_n=1,
        )

        if not best:
            return None

        best_option = best[0]

        # Calcular contratos a vender
        contracts_to_sell = min(
            shares_owned // 100,
            self.strategy_config.max_contracts_per_position,
        )

        if contracts_to_sell == 0:
            logger.warning(f"Acciones insuficientes para covered call: {symbol}")
            return None

        # Calcular prima
        premium = best_option.mid_price or Decimal("0")

        # Crear posición
        try:
            position = self.position_manager.open_position(
                symbol=symbol,
                shares_owned=shares_owned,
                average_cost=average_cost,
                current_price=current_price,
                call_option=best_option,
                contracts_to_sell=contracts_to_sell,
                premium_received=premium,
            )

            self.positions_opened += 1
            self.total_premium_collected += position.total_premium

            return position

        except ValueError as e:
            logger.error(f"Error creando posición: {e}")
            return None

    def get_position_summary(self) -> dict[str, Union[int, float, list[str], dict[str, float]]]:
        """
        Obtener resumen de posiciones.

        Returns:
            Dict con métricas agregadas
        """
        metrics = self.position_manager.get_position_metrics()

        return {
            **metrics,
            "total_premium_collected": float(self.total_premium_collected),
            "positions_opened": self.positions_opened,
            "positions_closed": self.positions_closed,
            "active_symbols": list(
                {pos.symbol for pos in self.position_manager.get_all_positions()}
            ),
        }

    def analyze_roll_opportunities(
        self,
        symbol: str,
        current_price: Decimal,
    ) -> list[
        dict[str, Union[str, int, bool, list[dict[str, Union[str, float, int, None]]], None]]
    ]:
        """
        Analizar oportunidades de rolling para un símbolo.

        Args:
            symbol: Símbolo a analizar
            current_price: Precio actual

        Returns:
            Lista de oportunidades con métricas
        """
        positions = self.position_manager.get_positions_by_symbol(symbol)
        opportunities = []

        for position in positions:
            options = self.available_options.get(symbol, [])

            rolls = self.roll_analyzer.analyze_roll_opportunities(
                position=position,
                current_price=current_price,
                available_options=options,
            )

            should_roll, best_roll = self.roll_analyzer.should_roll(
                position=position,
                current_price=current_price,
                opportunities=rolls,
            )

            if rolls:
                metrics = [self.roll_analyzer.calculate_roll_metrics(position, r) for r in rolls]

                opportunities.append(
                    {
                        "position_symbol": position.symbol,
                        "current_strike": str(position.call_option.strike),
                        "current_expiry": position.call_option.expiry_date.isoformat(),
                        "should_roll": should_roll,
                        "opportunities_count": len(rolls),
                        "best_roll": (
                            {
                                "roll_type": best_roll.roll_type.value if best_roll else None,
                                "new_strike": (
                                    str(best_roll.new_option.strike) if best_roll else None
                                ),
                                "new_expiry": (
                                    best_roll.new_option.expiry_date.isoformat()
                                    if best_roll
                                    else None
                                ),
                                "additional_premium": (
                                    str(best_roll.additional_premium) if best_roll else None
                                ),
                            }
                            if best_roll
                            else None
                        ),
                        "metrics": metrics,
                    }
                )

        return opportunities
