"""
MomentumStrategy - Estrategia de momentum basada en RSI, EMA y volumen.

Implementa una estrategia de momentum que utiliza indicadores técnicos
para identificar oportunidades de trading basadas en tendencias de precio.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List

from app.core.centralized_config import (get_strategy_config,
                                         get_trading_threshold)
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """Estrategia de momentum basada en RSI, EMA y volumen."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de momentum.

        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)

        # Load strategy-specific configuration
        strategy_config = get_strategy_config("momentum")
        if strategy_config:
            params = strategy_config.parameters
            self.rsi_threshold = Decimal(str(params.get("rsi_threshold", 40)))
            self.momentum_threshold = Decimal(
                str(params.get("momentum_threshold", 0.02))
            )
            self.volume_threshold = Decimal(str(params.get("volume_threshold", 1.5)))

            # Use strategy-specific risk parameters or fallback to global
            self.stop_loss = Decimal(
                str(
                    strategy_config.stop_loss_pct
                    or get_trading_threshold("stop_loss_pct")
                )
            )
            self.take_profit = Decimal(
                str(
                    strategy_config.take_profit_pct
                    or get_trading_threshold("take_profit_pct")
                )
            )
            self.max_position_size = Decimal(
                str(
                    strategy_config.max_position_size
                    or get_trading_threshold("max_position_size")
                )
            )
        else:
            # Fallback to config or defaults
            self.rsi_threshold = Decimal(str(config.get("rsi_threshold", 40)))
            self.momentum_threshold = Decimal(
                str(config.get("momentum_threshold", 0.02))
            )
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(
                    config.get(
                        "max_position_size", get_trading_threshold("max_position_size")
                    )
                )
            )
            self.volume_threshold = Decimal(str(config.get("volume_threshold", 1.5)))

        # Parámetros técnicos
        self.rsi_period = config.get("rsi_period", 14)
        self.ema_period = config.get("ema_period", 20)
        self.lookback_period = config.get("lookback_period", 5)

        logger.info(f"MomentumStrategy initialized: {self.name}")

    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de parámetros requeridos
        """
        return [
            "rsi_threshold",
            "momentum_threshold",
            "stop_loss",
            "take_profit",
            "max_position_size",
        ]

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en momentum.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # Calcular indicadores técnicos
            rsi = self._calculate_rsi(market_data)
            ema_trend = self._calculate_ema_trend(market_data)
            volume_ratio = self._calculate_volume_ratio(market_data)

            # Generar señal de compra
            if self._is_buy_signal(rsi, ema_trend, volume_ratio, market_data):
                signal = self._create_buy_signal(market_data)
                signals.append(signal)
                logger.debug(f"Generated BUY signal for {market_data.symbol}")

            # Generar señal de venta
            elif self._is_sell_signal(rsi, ema_trend, volume_ratio, market_data):
                signal = self._create_sell_signal(market_data)
                signals.append(signal)
                logger.debug(f"Generated SELL signal for {market_data.symbol}")

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
                    logger.debug(
                        f"Insufficient cash: {required_cash} > {portfolio.cash}"
                    )
                    return False

            # Verificar posición existente para ventas
            elif signal.signal_type == SignalType.SELL:
                existing_position = self._get_existing_position(
                    portfolio, signal.symbol
                )
                if not existing_position or existing_position.quantity < signal.volume:
                    logger.debug(f"Insufficient position for sell: {signal.volume}")
                    return False

            # Verificar límites de exposición
            total_exposure = self._calculate_total_exposure(portfolio)
            if total_exposure > Decimal("0.8"):  # Máximo 80% de exposición
                logger.debug(f"Total exposure too high: {total_exposure}")
                return False

            return True

        except Exception as e:
            logger.error(f"Risk check error: {e}")
            return False

    def _calculate_rsi(self, market_data: Quote) -> Decimal:
        """
        Calcular RSI (simplificado).

        Args:
            market_data: Datos de mercado

        Returns:
            Valor de RSI
        """
        # Implementación simplificada - en producción usar biblioteca técnica
        # Por ahora, simulamos RSI basado en precio
        if market_data.last > market_data.open:
            return Decimal("60")  # Momentum positivo
        else:
            return Decimal("40")  # Momentum negativo

    def _calculate_ema_trend(self, market_data: Quote) -> Decimal:
        """
        Calcular tendencia EMA (simplificado).

        Args:
            market_data: Datos de mercado

        Returns:
            Tendencia EMA
        """
        # Implementación simplificada
        price_change = (market_data.last - market_data.open) / market_data.open
        return Decimal(str(price_change))

    def _calculate_volume_ratio(self, market_data: Quote) -> Decimal:
        """
        Calcular ratio de volumen.

        Args:
            market_data: Datos de mercado

        Returns:
            Ratio de volumen
        """
        # Implementación simplificada
        avg_volume = Decimal("1000000")  # Volumen promedio simulado
        return market_data.volume / avg_volume

    def _is_buy_signal(
        self,
        rsi: Decimal,
        ema_trend: Decimal,
        volume_ratio: Decimal,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de compra.

        Args:
            rsi: Valor de RSI
            ema_trend: Tendencia EMA
            volume_ratio: Ratio de volumen
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de compra
        """
        return (
            rsi < self.rsi_threshold  # RSI oversold
            and ema_trend > self.momentum_threshold  # Tendencia alcista
            and volume_ratio > self.volume_threshold  # Volumen alto
        )

    def _is_sell_signal(
        self,
        rsi: Decimal,
        ema_trend: Decimal,
        volume_ratio: Decimal,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de venta.

        Args:
            rsi: Valor de RSI
            ema_trend: Tendencia EMA
            volume_ratio: Ratio de volumen
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de venta
        """
        return (
            rsi > (100 - self.rsi_threshold)  # RSI overbought
            and ema_trend < -self.momentum_threshold  # Tendencia bajista
            and volume_ratio > self.volume_threshold  # Volumen alto
        )

    def _create_buy_signal(self, market_data: Quote) -> Signal:
        """
        Crear señal de compra.

        Args:
            market_data: Datos de mercado

        Returns:
            Señal de compra
        """
        quantity = Decimal("100")  # Cantidad fija por simplicidad

        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            confidence=75.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi_threshold": str(self.rsi_threshold),
                "momentum_threshold": str(self.momentum_threshold),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
            },
        )

    def _create_sell_signal(self, market_data: Quote) -> Signal:
        """
        Crear señal de venta.

        Args:
            market_data: Datos de mercado

        Returns:
            Señal de venta
        """
        quantity = Decimal("100")  # Cantidad fija por simplicidad

        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.STRONG,
            confidence=75.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi_threshold": str(self.rsi_threshold),
                "momentum_threshold": str(self.momentum_threshold),
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
