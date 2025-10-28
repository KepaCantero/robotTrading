"""
MeanReversionStrategy - Estrategia de reversión a la media basada en Z-score.

Implementa una estrategia de reversión a la media que utiliza Z-score
para identificar cuando un activo se desvía significativamente de su media
y espera que regrese a ella.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List

from app.core.centralized_config import get_strategy_config, get_trading_threshold
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """Estrategia de reversión a la media basada en Z-score."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de reversión a la media.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Load strategy-specific configuration
        strategy_config = get_strategy_config("mean_reversion")
        if strategy_config:
            params = strategy_config.parameters
            self.z_score_threshold = Decimal(str(params.get("z_score_threshold", 2.0)))
            self.lookback_period = params.get("lookback_period", 20)
            self.volatility_threshold = Decimal(str(params.get("volatility_threshold", 0.05)))
            self.mean_reversion_speed = Decimal(str(params.get("mean_reversion_speed", 0.1)))

            # Use strategy-specific risk parameters or fallback to global
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct"))
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or get_trading_threshold("take_profit_pct"))
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or get_trading_threshold("max_position_size"))
            )
        else:
            # Fallback to config or defaults
            self.z_score_threshold = Decimal(str(config.get("z_score_threshold", 2.0)))
            self.lookback_period = config.get("lookback_period", 20)
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )
            self.volatility_threshold = Decimal(str(config.get("volatility_threshold", 0.02)))
            self.mean_reversion_speed = Decimal(str(config.get("mean_reversion_speed", 0.1)))

        # Parámetros adicionales
        self.min_z_score = Decimal(str(config.get("min_z_score", 1.5)))

        logger.info(f"MeanReversionStrategy initialized: {self.name}")

    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de parámetros requeridos
        """
        return [
            "z_score_threshold",
            "lookback_period",
            "stop_loss",
            "take_profit",
            "max_position_size",
        ]

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en reversión a la media.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # Calcular Z-score
            z_score = self._calculate_z_score(market_data)
            volatility = self._calculate_volatility(market_data)

            # Generar señal de compra (precio bajo, esperamos subida)
            if self._is_buy_signal(z_score, volatility, market_data):
                signal = self._create_buy_signal(market_data, z_score)
                signals.append(signal)
                logger.debug(f"Generated BUY signal for {market_data.symbol} (Z-score: {z_score})")

            # Generar señal de venta (precio alto, esperamos bajada)
            elif self._is_sell_signal(z_score, volatility, market_data):
                signal = self._create_sell_signal(market_data, z_score)
                signals.append(signal)
                logger.debug(f"Generated SELL signal for {market_data.symbol} (Z-score: {z_score})")

        except Exception as e:
            logger.error(f"Error generating signals for {market_data.symbol}: {e}")

        return signals

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verificar si la señal cumple criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio

        Returns:
            True si la señal pasa el risk check, False en caso contrario
        """
        try:
            # Verificar tamaño de posición
            position_size = self.get_position_size(signal, portfolio)
            if position_size <= 0:
                logger.debug(f"Position size too small: {position_size}")
                return False

            # Verificar cash disponible para compras
            if signal.signal_type == SignalType.BUY:
                required_cash = signal.price * signal.volume
                if required_cash > portfolio.cash:
                    logger.debug(f"Insufficient cash: {required_cash} > {portfolio.cash}")
                    return False

            # Verificar posición existente para ventas
            elif signal.signal_type == SignalType.SELL:
                existing_position = self._get_existing_position(portfolio, signal.symbol)
                if not existing_position or existing_position.quantity < signal.volume:
                    logger.debug(f"Insufficient position for sell: {signal.volume}")
                    return False

            # Verificar límites de exposición (más conservador que momentum)
            total_exposure = self._calculate_total_exposure(portfolio)
            if total_exposure > Decimal("0.6"):  # Máximo 60% de exposición
                logger.debug(f"Total exposure too high: {total_exposure}")
                return False

            # Verificar volatilidad del activo
            volatility = self._calculate_volatility_from_signal(signal)
            if volatility > self.volatility_threshold * 2:  # Evitar activos muy volátiles
                logger.debug(f"Asset too volatile: {volatility}")
                return False

            return True

        except Exception as e:
            logger.error(f"Risk check error: {e}")
            return False

    def _calculate_z_score(self, market_data: Quote) -> Decimal:
        """
        Calcular Z-score del precio.

        Args:
            market_data: Datos de mercado

        Returns:
            Z-score calculado
        """
        # Implementación simplificada - en producción usar datos históricos
        # Por ahora, simulamos Z-score basado en precio vs media móvil

        # Simular precio promedio y desviación estándar
        # Use wider range to generate more signals for demo
        avg_price = market_data.last * Decimal("0.98")  # Closer to current price
        # Increased std dev to allow for more variation
        std_dev = market_data.last * Decimal("0.03")  # Smaller std for more sensitive detection

        if std_dev == 0:
            return Decimal("0")

        z_score = (market_data.last - avg_price) / std_dev
        return z_score

    def _calculate_volatility(self, market_data: Quote) -> Decimal:
        """
        Calcular volatilidad del activo.

        Args:
            market_data: Datos de mercado

        Returns:
            Volatilidad calculada
        """
        # Implementación simplificada
        price_range = (market_data.high - market_data.low) / market_data.last
        return price_range

    def _is_buy_signal(self, z_score: Decimal, volatility: Decimal, market_data: Quote) -> bool:
        """
        Determinar si generar señal de compra.

        Args:
            z_score: Z-score calculado
            volatility: Volatilidad del activo
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de compra
        """
        # Simplified for demo - just check if price is lower than open
        is_undervalued = z_score < 0  # Price is below average
        has_low_volatility = volatility < self.volatility_threshold

        return is_undervalued and has_low_volatility

    def _is_sell_signal(self, z_score: Decimal, volatility: Decimal, market_data: Quote) -> bool:
        """
        Determinar si generar señal de venta.

        Args:
            z_score: Z-score calculado
            volatility: Volatilidad del activo
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de venta
        """
        # Simplified for demo - just check if price is higher than open
        is_overvalued = z_score > 0  # Price is above average
        has_low_volatility = volatility < self.volatility_threshold

        return is_overvalued and has_low_volatility

    def _create_buy_signal(self, market_data: Quote, z_score: Decimal) -> Signal:
        """
        Crear señal de compra.

        Args:
            market_data: Datos de mercado
            z_score: Z-score calculado

        Returns:
            Señal de compra
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=75.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "z_score": str(z_score),
                "z_score_threshold": str(self.z_score_threshold),
                "lookback_period": str(self.lookback_period),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
            },
        )

    def _create_sell_signal(self, market_data: Quote, z_score: Decimal) -> Signal:
        """
        Crear señal de venta.

        Args:
            market_data: Datos de mercado
            z_score: Z-score calculado

        Returns:
            Señal de venta
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=75.0,
            priority_score=80.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "z_score": str(z_score),
                "z_score_threshold": str(self.z_score_threshold),
                "lookback_period": str(self.lookback_period),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
            },
        )

    def _get_existing_position(self, portfolio: Portfolio, symbol: str):
        """
        Obtener posición existente para un símbolo.

        Args:
            portfolio: Portfolio actual
            symbol: Símbolo a buscar

        Returns:
            Posición existente o None
        """
        for position in portfolio.positions:
            if position.symbol == symbol:
                return position
        return None

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """
        Calcular exposición total del portfolio.

        Args:
            portfolio: Portfolio actual

        Returns:
            Exposición total como porcentaje
        """
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value

        if total_value == 0:
            return Decimal("0")

        invested_value = total_value - portfolio.cash
        return invested_value / total_value

    def _calculate_volatility_from_signal(self, signal: Signal) -> Decimal:
        """
        Calcular volatilidad desde la señal.

        Args:
            signal: Señal de trading

        Returns:
            Volatilidad estimada
        """
        # Implementación simplificada
        return Decimal("0.015")  # Volatilidad promedio simulada
