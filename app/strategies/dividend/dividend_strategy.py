"""
Dividend Strategy - Estrategia Principal de Inversión en Dividendos

Estrategia completa de inversión en dividendos que hereda de BaseStrategy
e implementa la lógica de generación de señales basada en análisis de dividendos.

Objetivo: MAXIMIZAR_DIVIDENDOS
- Alto yield sostenible
- Crecimiento de dividendos
- Payout ratio saludable
- Diversificación sectorial

SOLID Principles:
- Single Responsibility: Solo coordinar componentes
- Open/Closed: Extensible sin modificar
- Liskov Substitution: Compatible con BaseStrategy
- Interface Segregation: Interfaces mínimas
- Dependency Inversion: Depende de abstracciones
"""

import logging
from collections import deque
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.strategies.base import BaseStrategy

from .dividend_analyzer import DividendAnalyzer
from .dividend_portfolio_constructor import DividendPortfolio, DividendPortfolioConstructor
from .dividend_screener import DividendScreener
from .models import DividendProfile, DividendStock, DividendStrategyConfig, ExDividendDate

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DividendStrategy(BaseStrategy):
    """
    Estrategia de inversión en dividendos.

    Implementa una estrategia completa de inversión en acciones de dividendos
    con foco en maximizar el ingreso por dividendos de forma sostenible.

    Características:
    - Screening basado en yield, payout ratio y crecimiento
    - Análisis de calidad y sostenibilidad
    - Construcción de portafolio diversificado
    - Captura de fechas ex-dividend (opcional)
    - Seguimiento de Yield on Cost

    Attributes:
        config: Configuración de la estrategia
        screener: Screener de acciones de dividendos
        analyzer: Analizador de calidad
        constructor: Constructor de portafolios
        dividend_calendar: Calendario de fechas ex-dividend
        yield_on_cost_history: Histórico de yield on cost
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de dividendos.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Parsear configuración y trackear si es válida
        self._config_valid = False
        self.strategy_config = self._parse_config(config)

        # Inicializar componentes
        self.screener = DividendScreener(self.strategy_config)
        self.analyzer = DividendAnalyzer(lookback_years=10)
        self.constructor = DividendPortfolioConstructor(self.strategy_config)

        # Estado interno
        self.dividend_calendar: Dict[str, ExDividendDate] = {}
        self.yield_on_cost_history: Dict[str, deque] = {}
        self.current_portfolio: Optional[DividendPortfolio] = None
        self.last_rebalance_date: Optional[date] = None

        # Universo de acciones (se llena con datos)
        self.universe: List[DividendProfile] = []

        # Métricas de rendimiento
        self.total_dividends_received = Decimal("0")
        self.dividend_payments: List[Dict[str, Any]] = []

        logger.info(
            f"✅ DividendStrategy inicializada: "
            f"objetivo=MAXIMIZAR_DIVIDENDOS, "
            f"yield_min={self.strategy_config.min_dividend_yield}%, "
            f"portfolio_size={self.strategy_config.portfolio_size}"
        )

    def _parse_config(self, config: Dict[str, Any]) -> DividendStrategyConfig:
        """
        Parsear configuración desde dict.

        Args:
            config: Configuración raw

        Returns:
            Configuración validada
        """
        try:
            # Valores por defecto
            defaults = {
                "name": "DividendStrategy",
                "description": "Estrategia de inversión en dividendos",
                "version": "1.0.0",
                "min_dividend_yield": Decimal("3.0"),
                "max_dividend_yield": Decimal("15.0"),
                "max_payout_ratio": Decimal("70.0"),
                "min_years_consecutive": 3,
                "portfolio_size": 25,
                "max_sector_weight": Decimal("0.30"),
                "max_single_position": Decimal("0.05"),
            }

            # Merge con config provisto
            merged = {**defaults, **config}

            # Convertir a Decimals donde necesario
            for key in [
                "min_dividend_yield",
                "max_dividend_yield",
                "max_payout_ratio",
                "min_dividend_growth",
                "min_market_cap",
                "max_pe_ratio",
                "max_pb_ratio",
                "max_beta",
                "max_sector_weight",
                "max_single_position",
                "rebalance_threshold",
                "yield_weight",
                "growth_weight",
                "sustainability_weight",
                "value_weight",
                "min_quality_score",
                "min_sustainability_score",
            ]:
                if key in merged and merged[key] is not None:
                    if not isinstance(merged[key], Decimal):
                        merged[key] = Decimal(str(merged[key]))

            parsed_config = DividendStrategyConfig(**merged)
            self._config_valid = True
            return parsed_config

        except Exception as e:
            logger.error(f"Error parseando config: {e}")
            self._config_valid = False
            # Retornar config por defecto
            return DividendStrategyConfig()

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en dividendos.

        Esta estrategia genera señales de compra para acciones de dividendos
        de alta calidad que pasan el screening y análisis.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        if not self.is_active:
            logger.debug("Estrategia inactiva, no se generan señales")
            return []

        symbol = market_data.symbol

        # Si el universo está vacío, no generar señales
        if not self.universe:
            logger.debug("Universo vacío, no se generan señales")
            return []

        # Buscar perfil del símbolo
        profile = None
        for p in self.universe:
            if p.symbol == symbol:
                profile = p
                break

        if profile is None:
            logger.debug(f"No se encontró perfil para {symbol}")
            return []

        # Actualizar precio en el perfil
        profile.current_price = (
            market_data.close if hasattr(market_data, 'close') else market_data.price
        )

        # Evaluar si generar señal
        signals = []

        # 1. Señal de compra si pasa screening y no está en portafolio
        if self._should_buy(profile):
            signal = self._create_buy_signal(profile, market_data)
            signals.append(signal)

        # 2. Señal de venta si hay razones fundamentales
        elif self._should_sell(profile):
            signal = self._create_sell_signal(profile, market_data)
            signals.append(signal)

        # 3. Señal de captura de dividendo (opcional)
        elif self.strategy_config.enable_dividend_capture:
            capture_signal = self._evaluate_dividend_capture(profile, market_data)
            if capture_signal:
                signals.append(capture_signal)

        return signals

    def _should_buy(self, profile: DividendProfile) -> bool:
        """
        Determinar si se debe generar señal de compra.

        Args:
            profile: Perfil de la acción

        Returns:
            True si se debe comprar
        """
        # Verificar si está en el portafolio actual
        if self.current_portfolio:
            for pos in self.current_portfolio.positions:
                if pos.symbol == profile.symbol:
                    return False  # Ya tenemos posición

        # Evaluar calidad
        if profile.quality_score is not None:
            if profile.quality_score < self.strategy_config.min_quality_score:
                return False

        # Evaluar sostenibilidad
        if profile.sustainability_score is not None:
            if profile.sustainability_score < self.strategy_config.min_sustainability_score:
                return False

        # No debe ser un dividend trap
        if profile.is_dividend_trap:
            return False

        # Yield dentro de rango
        yield_pct = profile.dividend_data.dividend_yield
        if (
            yield_pct < self.strategy_config.min_dividend_yield
            or yield_pct > self.strategy_config.max_dividend_yield
        ):
            return False

        return True

    def _should_sell(self, profile: DividendProfile) -> bool:
        """
        Determinar si se debe generar señal de venta.

        Razones para vender:
        - Dividend trap detectado
        - Payout ratio peligroso (>100%)
        - Dividendos cortados
        - Calidad cae por debajo del mínimo

        Args:
            profile: Perfil de la acción

        Returns:
            True si se debe vender
        """
        # Dividend trap
        if profile.is_dividend_trap:
            logger.warning(f"🚨 Dividend trap detectado: {profile.symbol}")
            return True

        # Payout ratio peligroso
        if profile.dividend_data.payout_ratio is not None:
            if profile.dividend_data.payout_ratio > 100:
                logger.warning(f"⚠️ Payout ratio crítico: {profile.symbol}")
                return True

        # Dividend coverage bajo
        if profile.dividend_data.dividend_coverage_ratio is not None:
            if profile.dividend_data.dividend_coverage_ratio < 0.8:
                logger.warning(f"⚠️ Cobertura insuficiente: {profile.symbol}")
                return True

        # Calidad baja
        if profile.quality_score is not None:
            if (
                profile.quality_score < self.strategy_config.min_quality_score * 0.7
            ):  # 70% del mínimo
                logger.warning(f"⚠️ Calidad deteriorada: {profile.symbol}")
                return True

        return False

    def _evaluate_dividend_capture(
        self, profile: DividendProfile, market_data: Quote
    ) -> Optional[Signal]:
        """
        Evaluar oportunidad de captura de dividendo.

        Args:
            profile: Perfil de la acción
            market_data: Datos de mercado

        Returns:
            Señal de captura o None
        """
        ex_div_date = profile.dividend_data.next_ex_dividend_date
        if ex_div_date is None:
            return None

        today = date.today()
        days_until = (ex_div_date - today).days

        # Comprar antes de ex-dividend
        if 0 <= days_until <= self.strategy_config.min_days_before_ex_dividend:
            # Verificar que tenemos liquidez
            if not self._check_liquidity(market_data):
                return None

            return self._create_buy_signal(profile, market_data, reason="dividend_capture")

        return None

    def _create_buy_signal(
        self,
        profile: DividendProfile,
        market_data: Quote,
        reason: str = "dividend_income",
    ) -> Signal:
        """
        Crear señal de compra.

        Args:
            profile: Perfil de la acción
            market_data: Datos de mercado
            reason: Razón de la señal

        Returns:
            Señal de compra
        """
        # Calcular confianza basada en calidad
        confidence = float(profile.quality_score or 70)

        # Calcular fuerza basada en yield y sostenibilidad
        if profile.dividend_data.dividend_yield >= 5:
            strength = SignalStrength.STRONG
        elif profile.dividend_data.dividend_yield >= 4:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Priority score combinado
        priority = min(100, confidence * 0.6 + float(profile.dividend_data.dividend_yield) * 5)

        # Liquidity score (simplificado)
        liquidity_score = 80.0  # TODO: Implementar cálculo real

        signal = Signal(
            symbol=profile.symbol,
            signal_type=SignalType.BUY,
            strength=strength,
            confidence=confidence,
            liquidity_score=liquidity_score,
            priority_score=priority,
            source=SignalSource.FUNDAMENTAL,
            price=market_data.close if hasattr(market_data, 'close') else market_data.price,
            volume=market_data.volume if hasattr(market_data, 'volume') else Decimal("1000000"),
            metadata={
                "reason": reason,
                "dividend_yield": float(profile.dividend_data.dividend_yield),
                "payout_ratio": float(profile.dividend_data.payout_ratio or 0),
                "years_consecutive": profile.dividend_data.years_consecutive_increases,
                "quality_score": float(profile.quality_score or 0),
                "sustainability_score": float(profile.sustainability_score or 0),
                "strategy": "dividend",
            },
        )

        logger.info(
            f"📈 BUY {profile.symbol}: Yield {profile.dividend_data.dividend_yield:.2f}%, "
            f"Confianza {confidence:.1f}%, Razón: {reason}"
        )

        return signal

    def _create_sell_signal(self, profile: DividendProfile, market_data: Quote) -> Signal:
        """
        Crear señal de venta.

        Args:
            profile: Perfil de la acción
            market_data: Datos de mercado

        Returns:
            Señal de venta
        """
        signal = Signal(
            symbol=profile.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=60.0,
            source=SignalSource.FUNDAMENTAL,
            price=market_data.close if hasattr(market_data, 'close') else market_data.price,
            volume=market_data.volume if hasattr(market_data, 'volume') else Decimal("1000000"),
            metadata={
                "reason": "dividend_safety_deteriorated",
                "payout_ratio": float(profile.dividend_data.payout_ratio or 0),
                "is_trap": profile.is_dividend_trap,
                "strategy": "dividend",
            },
        )

        logger.warning(f"📉 SELL {profile.symbol}: Razones fundamentales deterioradas")

        return signal

    def _check_liquidity(self, market_data: Quote) -> bool:
        """
        Verificar si hay suficiente liquidez.

        Args:
            market_data: Datos de mercado

        Returns:
            True si hay suficiente liquidez
        """
        # TODO: Implementar verificación real de liquidez
        # Por ahora, asumir que sí hay
        return True

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar si la señal pasa criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portafolio

        Returns:
            True si la señal pasa el risk check
        """
        # Verificar tamaño de posición
        max_pos = Decimal(str(self.strategy_config.max_single_position))
        current_allocation = Decimal("0")

        for pos in portfolio.positions:
            if pos.symbol == signal.symbol:
                current_allocation = pos.value / portfolio.total_value

        # Si ya tenemos posición, verificar si podemos aumentar
        if current_allocation > 0:
            # No exceder máximo
            if current_allocation >= max_pos:
                logger.debug(
                    f"Posición máxima alcanzada para {signal.symbol}: "
                    f"{current_allocation:.1%} >= {max_pos:.1%}"
                )
                return False

        # Verificar exposición sectorial
        if self.current_portfolio and signal.signal_type == SignalType.BUY:
            sector = self._get_sector_for_symbol(signal.symbol)
            if sector:
                sector_weight = self.current_portfolio.sector_weights.get(sector, Decimal("0"))
                max_sector = self.strategy_config.max_sector_weight

                if sector_weight >= max_sector:
                    logger.debug(
                        f"Peso máximo sectorial alcanzado para {sector}: "
                        f"{sector_weight:.1%} >= {max_sector:.1%}"
                    )
                    return False

        return True

    def _get_sector_for_symbol(self, symbol: str) -> Optional[str]:
        """Obtener sector para un símbolo."""
        for profile in self.universe:
            if profile.symbol == symbol:
                return profile.sector
        return None

    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de nombres de parámetros requeridos
        """
        return [
            "min_dividend_yield",
            "max_dividend_yield",
            "max_payout_ratio",
            "portfolio_size",
        ]

    def validate_config(self) -> bool:
        """
        Validar configuración de la estrategia.

        Returns:
            True si la configuración es válida
        """
        # Retornar el flag que se seteó durante _parse_config
        # Si Pydantic validó exitosamente, el flag es True
        # Si hubo error de validación, el flag es False
        return self._config_valid

    # ============================================================================
    # MÉTODOS DE GESTIÓN DE PORTAFOLIO
    # ============================================================================

    def set_universe(self, profiles: List[DividendProfile]) -> None:
        """
        Establecer universo de acciones de dividendos.

        Args:
            profiles: Lista de perfiles de acciones
        """
        self.universe = profiles
        logger.info(f"Universo establecido: {len(profiles)} acciones")

    def construct_portfolio(
        self, stocks: List[DividendStock], total_capital: Decimal
    ) -> DividendPortfolio:
        """
        Construir portafolio de dividendos.

        Args:
            stocks: Lista de acciones clasificadas
            total_capital: Capital total a invertir

        Returns:
            Portafolio construido
        """
        self.current_portfolio = self.constructor.construct_portfolio(stocks, total_capital)
        self.last_rebalance_date = date.today()

        return self.current_portfolio

    def rebalance_portfolio(
        self, new_stocks: List[DividendStock], total_capital: Decimal
    ) -> DividendPortfolio:
        """
        Rebalancear portafolio existente.

        Args:
            new_stocks: Nueva lista de acciones clasificadas
            total_capital: Capital actual

        Returns:
            Portafolio rebalanceado
        """
        if self.current_portfolio is None:
            return self.construct_portfolio(new_stocks, total_capital)

        self.current_portfolio = self.constructor.rebalance(
            self.current_portfolio, new_stocks, total_capital
        )
        self.last_rebalance_date = date.today()

        return self.current_portfolio

    def analyze_portfolio_drift(self) -> Dict[str, Any]:
        """
        Analizar drift del portafolio actual.

        Returns:
            Dict con análisis de drift
        """
        if self.current_portfolio is None:
            return {"needs_rebalance": False, "reason": "No portfolio"}

        return self.constructor.analyze_drift(self.current_portfolio)

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """
        Obtener métricas del portafolio actual.

        Returns:
            Dict con métricas del portafolio
        """
        if self.current_portfolio is None:
            return {}

        return {
            "total_value": float(self.current_portfolio.total_value),
            "annual_income": float(self.current_portfolio.annual_income),
            "portfolio_yield": float(self.current_portfolio.portfolio_yield),
            "expected_monthly_income": float(self.current_portfolio.expected_monthly_income),
            "num_positions": len(self.current_portfolio.positions),
            "sector_weights": {
                k: float(v) for k, v in self.current_portfolio.sector_weights.items()
            },
            "last_rebalance": (
                self.last_rebalance_date.isoformat() if self.last_rebalance_date else None
            ),
        }

    def update_dividend_calendar(self, ex_dates: List[ExDividendDate]) -> None:
        """
        Actualizar calendario de fechas ex-dividend.

        Args:
            ex_dates: Lista de fechas ex-dividend
        """
        for ex_date in ex_dates:
            self.dividend_calendar[ex_date.symbol] = ex_date

        logger.info(f"Calendario actualizado: {len(ex_dates)} fechas ex-dividend")

    def record_dividend_payment(self, symbol: str, amount: Decimal) -> None:
        """
        Registrar pago de dividendo recibido.

        Args:
            symbol: Símbolo de la acción
            amount: Monto recibido
        """
        self.total_dividends_received += amount

        payment = {
            "symbol": symbol,
            "amount": float(amount),
            "date": date.today().isoformat(),
        }

        self.dividend_payments.append(payment)

        logger.info(f"💰 Dividendo recibido: {symbol} ${amount:.2f}")
