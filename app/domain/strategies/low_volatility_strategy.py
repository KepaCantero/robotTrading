"""
Low Volatility Strategy - Estrategia Principal de Inversión de Baja Volatilidad

Estrategia completa de inversión de baja volatilidad que hereda de BaseStrategy
e implementa la lógica de generación de señales basada en análisis de volatilidad.

Objetivo: CAPITAL_PRESERVATION
- Minimizar volatilidad del portafolio
- Foco en acciones de baja beta
- Sesgo defensivo por sectores
- Optimización de varianza mínima

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
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.strategies.base import BaseStrategy

from .low_beta_screener import LowBetaScreener
from .models import (
    LowVolatilityProfile,
    LowVolatilityStock,
    LowVolatilityStrategyConfig,
    VolatilityMetrics,
    VolatilityRegime,
)
from .portfolio_constructor import LowVolatilityPortfolio, LowVolatilityPortfolioConstructor
from .volatility_calculator import VolatilityCalculator

logger = logging.getLogger(__name__)


class LowVolatilityStrategy(BaseStrategy):
    """
    Estrategia de inversión de baja volatilidad.

    Implementa una estrategia completa de inversión en acciones de baja volatilidad
    con foco en preservación de capital y minimización de riesgo.

    Características:
    - Screening basado en volatilidad, beta y riesgo downside
    - Análisis de características defensivas
    - Construcción de portafolio con optimización de varianza mínima
    - Rebalanceo basado en drift de volatilidad
    - Monitoreo de régimen de volatilidad

    Attributes:
        config: Configuración de la estrategia
        screener: Screener de acciones de baja volatilidad
        calculator: Calculador de métricas de volatilidad
        constructor: Constructor de portafolios
        current_portfolio: Portafolio actual construido
        last_rebalance_date: Fecha del último rebalanceo
        universe: Universo de acciones
        volatility_history: Histórico de volatilidad del portafolio
    """

    # Sectores defensivos por defecto
    DEFENSIVE_SECTORS = ["Utilities", "Consumer Staples", "Healthcare", "Real Estate"]

    # Sectores a evitar por defecto
    CYCLICAL_SECTORS = ["Technology", "Biotechnology", "Energy", "Materials"]

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de baja volatilidad.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Parsear configuración
        self.strategy_config = self._parse_config(config)

        # Inicializar componentes
        self.screener = LowBetaScreener(self.strategy_config)
        self.calculator = VolatilityCalculator(
            risk_free_rate= getattr(config.trading, 'max_risk_per_trade', 0.02))),
            trading_days_per_year=config.get("trading_days_per_year", 252),
        )
        self.constructor = LowVolatilityPortfolioConstructor(self.strategy_config)

        # Estado interno
        self.current_portfolio: Optional[LowVolatilityPortfolio] = None
        self.last_rebalance_date: Optional[date] = None
        self.universe: List[LowVolatilityProfile] = []

        # Métricas de rendimiento
        self.volatility_history: deque = deque(maxlen=252)  # 1 año de datos diarios
        self.beta_history: deque = deque(maxlen=252)

        logger.info(
            f"✅ LowVolatilityStrategy inicializada: "
            f"objetivo=CAPITAL_PRESERVATION, "
            f"max_vol={self.strategy_config.max_historical_volatility}%, "
            f"max_beta={self.strategy_config.max_beta}, "
            f"portfolio_size={self.strategy_config.portfolio_size}"
        )

    def _parse_config(self, config: Dict[str, Any]) -> LowVolatilityStrategyConfig:
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
                "name": "LowVolatilityStrategy",
                "description": "Estrategia de baja volatilidad",
                "version": "1.0.0",
                "max_historical_volatility": Decimal("25.0"),
                "max_beta": Decimal("0.8"),
                "portfolio_size": 30,
                "max_sector_weight": Decimal("0.35"),
                "max_single_position": Decimal("0.06"),
                "min_low_vol_score": Decimal("60.0"),
                "min_defensive_score": Decimal("50.0"),
                "min_stability_score": Decimal("50.0"),
                "preferred_sectors": self.DEFENSIVE_SECTORS,
                "avoid_sectors": self.CYCLICAL_SECTORS,
                "optimization_method": "min_variance",
            }

            # Merge con config provisto
            merged = {**defaults, **config}

            # Convertir a Decimals donde necesario
            for key in [
                "max_historical_volatility",
                "max_beta",
                "min_beta",
                "max_downside_risk",
                "min_sortino_ratio",
                "max_max_drawdown",
                "min_low_vol_score",
                "min_defensive_score",
                "min_stability_score",
                "max_sector_weight",
                "max_single_position",
                "rebalance_threshold",
                "volatility_weight",
                "defensive_weight",
                "stability_weight",
                "quality_weight",
                "target_volatility",
                "min_market_cap",
            ]:
                if key in merged and merged[key] is not None:
                    if not isinstance(merged[key], Decimal):
                        merged[key] = Decimal(str(merged[key]))

            return LowVolatilityStrategyConfig(**merged)

        except Exception as e:
            logger.error(f"Error parseando config: {e}")
            # Retornar config por defecto
            return LowVolatilityStrategyConfig()

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en baja volatilidad.

        Esta estrategia genera señales de compra para acciones de baja volatilidad
        que pasan el screening y análisis.

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

        # 2. Señal de venta si la volatilidad aumenta significativamente
        elif self._should_sell(profile):
            signal = self._create_sell_signal(profile, market_data)
            signals.append(signal)

        return signals

    def _should_buy(self, profile: LowVolatilityProfile) -> bool:
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

        # Evaluar score de baja volatilidad
        if profile.low_vol_score is not None:
            if profile.low_vol_score < self.strategy_config.min_low_vol_score:
                return False

        # Evaluar score defensivo
        if profile.defensive_score is not None:
            if profile.defensive_score < self.strategy_config.min_defensive_score:
                return False

        # Evaluar score de estabilidad
        if profile.stability_score is not None:
            if profile.stability_score < self.strategy_config.min_stability_score:
                return False

        # Verificar que sea baja volatilidad
        if not profile.is_defensive_stock:
            return False

        # Verificar volatilidad promedio
        avg_vol = profile.volatility_metrics.average_volatility
        if avg_vol is None or avg_vol > self.strategy_config.max_historical_volatility:
            return False

        # Verificar beta
        beta = profile.volatility_metrics.beta
        if beta is None or beta > self.strategy_config.max_beta:
            return False

        return True

    def _should_sell(self, profile: LowVolatilityProfile) -> bool:
        """
        Determinar si se debe generar señal de venta.

        Razones para vender:
        - Volatilidad aumenta significativamente (>50% sobre el máximo)
        - Beta aumenta por encima del umbral
        - Máximo drawdown excesivo

        Args:
            profile: Perfil de la acción

        Returns:
            True si se debe vender
        """
        # Verificar si estamos en régimen de alta volatilidad
        if profile.volatility_metrics.volatility_regime == VolatilityRegime.HIGH:
            logger.warning(f"🌊 Régimen de alta volatilidad detectado: {profile.symbol}")
            return True

        # Volatilidad aumentó significativamente
        current_vol = profile.volatility_metrics.average_volatility
        if current_vol and current_vol > self.strategy_config.max_historical_volatility * 1.5:
            logger.warning(f"📈 Volatilidad excesiva: {profile.symbol} {current_vol:.2f}%")
            return True

        # Beta aumentó
        beta = profile.volatility_metrics.beta
        if beta and beta > self.strategy_config.max_beta * 1.2:
            logger.warning(f"⚠️ Beta excesivo: {profile.symbol} {beta:.2f}")
            return True

        # Máximo drawdown excesivo
        max_dd = profile.volatility_metrics.max_drawdown
        if max_dd and max_dd < -50:  # Caída > 50%
            logger.warning(f"📉 Drawdown severo: {profile.symbol} {max_dd:.2f}%")
            return True

        return False

    def _create_buy_signal(
        self,
        profile: LowVolatilityProfile,
        market_data: Quote,
        reason: str = "low_volatility",
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
        # Calcular confianza basada en scores
        confidence = float(profile.overall_score or profile.low_vol_score or 60)

        # Calcular fuerza basada en volatilidad y beta
        vol = profile.volatility_metrics.average_volatility or 20
        beta = profile.volatility_metrics.beta or 0.7

        if vol < 15 and beta < 0.5:
            strength = SignalStrength.STRONG
        elif vol < 20 and beta < 0.7:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Priority score combinado
        priority = min(100, confidence * 0.6 + (100 - vol) * 0.4)

        # Liquidity score (simplificado)
        liquidity_score = 80.0

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
                "volatility": float(vol),
                "beta": float(beta),
                "low_vol_score": float(profile.low_vol_score or 0),
                "defensive_score": float(profile.defensive_score or 0),
                "stability_score": float(profile.stability_score or 0),
                "sector": profile.sector,
                "strategy": "low_volatility",
            },
        )

        logger.info(
            f"📈 BUY {profile.symbol}: Vol {vol:.2f}%, Beta {beta:.2f}, "
            f"Confianza {confidence:.1f}%, Razón: {reason}"
        )

        return signal

    def _create_sell_signal(self, profile: LowVolatilityProfile, market_data: Quote) -> Signal:
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
                "reason": "volatility_increased",
                "volatility": float(profile.volatility_metrics.average_volatility or 0),
                "beta": float(profile.volatility_metrics.beta or 0),
                "strategy": "low_volatility",
            },
        )

        logger.warning(f"📉 SELL {profile.symbol}: Volatilidad aumentó significativamente")

        return signal

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
            "max_historical_volatility",
            "max_beta",
            "portfolio_size",
        ]

    def validate_config(self) -> bool:
        """
        Validar configuración de la estrategia.

        Returns:
            True si la configuración es válida
        """
        try:
            # Validar volatilidad máxima
            if self.strategy_config.max_historical_volatility < 10:
                logger.error("max_historical_volatility debe ser al menos 10%")
                return False

            # Validar beta máximo
            if self.strategy_config.max_beta < 0.1:
                logger.error("max_beta debe ser al menos 0.1")
                return False

            # Validar tamaño de portafolio
            if not (20 <= self.strategy_config.portfolio_size <= 50):
                logger.error("portfolio_size debe estar entre 20 y 50")
                return False

            # Validar pesos
            if self.strategy_config.max_sector_weight > Decimal("1.0"):
                logger.error("max_sector_weight no puede exceder 1.0")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validando config: {e}")
            return False

    # ============================================================================
    # MÉTODOS DE GESTIÓN DE PORTAFOLIO
    # ============================================================================

    def set_universe(self, profiles: List[LowVolatilityProfile]) -> None:
        """
        Establecer universo de acciones de baja volatilidad.

        Args:
            profiles: Lista de perfiles de acciones
        """
        self.universe = profiles
        logger.info(f"Universo establecido: {len(profiles)} acciones")

    def construct_portfolio(
        self,
        stocks: List[LowVolatilityStock],
        total_capital: Decimal,
        returns_matrix: Optional[Any] = None,
    ) -> LowVolatilityPortfolio:
        """
        Construir portafolio de baja volatilidad.

        Args:
            stocks: Lista de acciones clasificadas
            total_capital: Capital total a invertir
            returns_matrix: Matriz de retornos para optimización

        Returns:
            Portafolio construido
        """
        import numpy as np

        if returns_matrix is not None and not isinstance(returns_matrix, np.ndarray):
            returns_matrix = np.array(returns_matrix)

        self.current_portfolio = self.constructor.construct_portfolio(
            stocks, total_capital, returns_matrix
        )
        self.last_rebalance_date = date.today()

        return self.current_portfolio

    def rebalance_portfolio(
        self,
        new_stocks: List[LowVolatilityStock],
        total_capital: Decimal,
        returns_matrix: Optional[Any] = None,
    ) -> LowVolatilityPortfolio:
        """
        Rebalancear portafolio existente.

        Args:
            new_stocks: Nueva lista de acciones clasificadas
            total_capital: Capital actual
            returns_matrix: Matriz de retornos (opcional)

        Returns:
            Portafolio rebalanceado
        """
        import numpy as np

        if returns_matrix is not None and not isinstance(returns_matrix, np.ndarray):
            returns_matrix = np.array(returns_matrix)

        if self.current_portfolio is None:
            return self.construct_portfolio(new_stocks, total_capital, returns_matrix)

        self.current_portfolio = self.constructor.rebalance(
            self.current_portfolio, new_stocks, total_capital, returns_matrix
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
            "expected_volatility": float(self.current_portfolio.expected_volatility),
            "portfolio_beta": float(self.current_portfolio.portfolio_beta),
            "num_positions": len(self.current_portfolio.positions),
            "sector_weights": {
                k: float(v) for k, v in self.current_portfolio.sector_weights.items()
            },
            "last_rebalance": (
                self.last_rebalance_date.isoformat() if self.last_rebalance_date else None
            ),
        }

    def update_volatility_metrics(
        self,
        symbol: str,
        price_series: List[Tuple[date, Decimal]],
        market_series: List[Tuple[date, Decimal]],
    ) -> VolatilityMetrics:
        """
        Actualizar métricas de volatilidad para un símbolo.

        Args:
            symbol: Símbolo de la acción
            price_series: Serie de precios históricos
            market_series: Serie de precios del mercado

        Returns:
            Métricas de volatilidad actualizadas
        """
        metrics = self.calculator.calculate_all_metrics(price_series, market_series, symbol)

        # Actualizar perfil si existe
        for profile in self.universe:
            if profile.symbol == symbol:
                profile.volatility_metrics = metrics
                break

        return metrics

    def calculate_portfolio_volatility(
        self,
        weights: List[float],
        returns_matrix: List[List[float]],
    ) -> Decimal:
        """
        Calcular volatilidad de portafolio.

        Args:
            weights: Pesos del portafolio
            returns_matrix: Matriz de retornos

        Returns:
            Volatilidad anualizada (%)
        """
        import numpy as np

        returns_array = np.array(returns_matrix)
        return self.calculator.calculate_portfolio_volatility(weights, returns_array)
