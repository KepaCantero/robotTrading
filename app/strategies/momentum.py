"""
MomentumStrategy - Estrategia de momentum basada en RSI, EMA y volumen.

Implementa una estrategia de momentum que utiliza indicadores técnicos
para identificar oportunidades de trading basadas en tendencias de precio.
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.core.centralized_config import get_strategy_config, get_trading_threshold
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType

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
            self.momentum_threshold = Decimal(str(params.get("momentum_threshold", 0.02)))
            self.volume_threshold = Decimal(str(params.get("volume_threshold", 1.5)))

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
            self.rsi_threshold = Decimal(str(config.get("rsi_threshold", 40)))
            self.momentum_threshold = Decimal(str(config.get("momentum_threshold", 0.02)))
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )
            self.volume_threshold = Decimal(str(config.get("volume_threshold", 1.5)))

        # Parámetros técnicos
        self.rsi_period = config.get("rsi_period", 14)
        self.ema_period = config.get("ema_period", 20)
        self.lookback_period = config.get("lookback_period", 5)

        # Histórico para calcular indicadores reales
        self.price_history = deque(maxlen=200)  # Mantener 200 velas de histórico
        self.volume_history = deque(maxlen=200)
        self.last_rsi = None
        self.last_ema = None

        # Cooldown para evitar señales repetidas
        self.last_signal_bar_index = None
        self.last_signal_type = None
        self.current_bar_index = 0
        self.cooldown_bars = config.get("cooldown_bars", 5)  # Número de barras para cooldown

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
        Generar señales de trading basadas en momentum con indicadores reales.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """
        signals = []

        try:
            # Actualizar histórico
            self.price_history.append(float(market_data.close or market_data.last))
            self.volume_history.append(float(market_data.volume))
            self.current_bar_index += 1

            # Calcular indicadores técnicos reales
            rsi = self._calculate_real_rsi()
            ema = self._calculate_real_ema()
            volume_ratio = self._calculate_volume_ratio(market_data)

            # Sólo generar señales si tenemos suficiente histórico
            if rsi is None or ema is None:
                return signals

            # Guardar para uso en señales
            self.last_rsi = rsi
            self.last_ema = ema

            # Verificar cooldown
            if not self._is_cooldown_active(market_data):
                # Generar señal de compra con condiciones robustas
                if self._is_buy_signal(rsi, ema, volume_ratio, market_data):
                    signal = self._create_buy_signal(market_data, rsi, ema, volume_ratio)
                    signals.append(signal)
                    self.last_signal_bar_index = self.current_bar_index
                    self.last_signal_type = "buy"
                    logger.debug(
                        f"Generated BUY signal for {market_data.symbol}: RSI={rsi:.2f}, EMA={ema:.2f}"
                    )

                # Generar señal de venta con condiciones robustas
                elif self._is_sell_signal(rsi, ema, volume_ratio, market_data):
                    signal = self._create_sell_signal(market_data, rsi, ema, volume_ratio)
                    signals.append(signal)
                    self.last_signal_bar_index = self.current_bar_index
                    self.last_signal_type = "sell"
                    logger.debug(
                        f"Generated SELL signal for {market_data.symbol}: RSI={rsi:.2f}, EMA={ema:.2f}"
                    )
            else:
                logger.debug("Signal suppressed due to cooldown period")

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

            # Verificar límites de exposición
            total_exposure = self._calculate_total_exposure(portfolio)
            if total_exposure > Decimal("0.8"):  # Máximo 80% de exposición
                logger.debug(f"Total exposure too high: {total_exposure}")
                return False

            return True

        except Exception as e:
            logger.error(f"Risk check error: {e}")
            return False

    def _calculate_real_rsi(self) -> Optional[float]:
        """
        Calcular RSI real usando histórico de precios.

        Returns:
            Valor de RSI o None si no hay suficiente histórico
        """
        if len(self.price_history) < self.rsi_period + 1:
            return None

        prices = list(self.price_history)
        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < self.rsi_period:
            return None

        # Calcular promedio de ganancias y pérdidas
        avg_gain = sum(gains[-self.rsi_period :]) / self.rsi_period
        avg_loss = sum(losses[-self.rsi_period :]) / self.rsi_period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def _calculate_real_ema(self) -> Optional[float]:
        """
        Calcular EMA real usando toda la historia de precios.

        Returns:
            Valor de EMA o None si no hay suficiente histórico
        """
        if len(self.price_history) < self.ema_period:
            return None

        prices = list(self.price_history)

        # Calcular EMA usando todos los datos disponibles (no solo ema_period)
        multiplier = 2 / (self.ema_period + 1)
        ema = prices[0]

        # Iterar sobre toda la historia para un EMA más estable
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return round(ema, 2)

    def _calculate_volume_ratio(self, market_data: Quote) -> Decimal:
        """
        Calcular ratio de volumen dinámicamente usando histórico.

        Args:
            market_data: Datos de mercado

        Returns:
            Ratio de volumen
        """
        if len(self.volume_history) < 20:
            # No hay suficiente histórico, usar valor conservador
            return Decimal("1")

        # Calcular promedio de volumen de las últimas 20 barras
        volume_list = list(self.volume_history)
        avg_volume = sum(volume_list[-20:]) / 20
        if avg_volume > 0:
            return market_data.volume / Decimal(str(avg_volume))
        return Decimal("1")

    def _is_cooldown_active(self, market_data: Quote) -> bool:
        """
        Verificar si el cooldown está activo para evitar señales repetidas.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            True si el cooldown está activo (no debe generar señales)
        """
        if self.last_signal_bar_index is None:
            # No ha habido señales aún, no hay cooldown
            return False

        # Calcular barras transcurridas desde última señal
        bars_since_last_signal = self.current_bar_index - self.last_signal_bar_index

        # Si han pasado menos barras que cooldown_bars, el cooldown está activo
        if bars_since_last_signal < self.cooldown_bars:
            logger.debug(
                f"Cooldown active: {bars_since_last_signal}/{self.cooldown_bars} bars since last signal"
            )
            return True

        return False

    def _is_buy_signal(
        self,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de compra con condiciones robustas.

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de compra
        """
        current_price = market_data.close or market_data.last

        # Condiciones más robustas:
        # 1. RSI > 55 (momentum positivo fuerte)
        # 2. Precio por encima de EMA (tendencia alcista)
        # 3. Volumen razonable
        # 4. TASK-IND-5: Filtro de volumen dinámico >1.2 para confirmar liquidez
        rsi_positive = rsi > 55
        ema_bullish = current_price > Decimal(str(ema))
        has_volume = volume_ratio > Decimal(
            "1.2"
        )  # TASK-IND-5: volume_ratio > 1.2 para liquidez confirmada

        return rsi_positive and ema_bullish and has_volume

    def _is_sell_signal(
        self,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de venta con condiciones robustas.

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            market_data: Datos de mercado

        Returns:
            True si debe generar señal de venta
        """
        current_price = market_data.close or market_data.last

        # Condiciones más robustas:
        # 1. RSI < 45 (momentum negativo fuerte)
        # 2. Precio por debajo de EMA (tendencia bajista)
        # 3. Volumen razonable
        # 4. TASK-IND-5: Filtro de volumen dinámico >1.2 para confirmar liquidez
        rsi_negative = rsi < 45
        ema_bearish = current_price < Decimal(str(ema))
        has_volume = volume_ratio > Decimal(
            "1.2"
        )  # TASK-IND-5: volume_ratio > 1.2 para liquidez confirmada

        return rsi_negative and ema_bearish and has_volume

    def _create_buy_signal(
        self, market_data: Quote, rsi: float, ema: float, volume_ratio: Decimal
    ) -> Signal:
        """
        Crear señal de compra con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen

        Returns:
            Señal de compra
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,  # Más conservador
            confidence=float(rsi),  # Usar RSI como confidence
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi": str(rsi),
                "ema": str(ema),
                "volume_ratio": str(volume_ratio),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "momentum_type": "positive_breakout",
                "reason": f"momentum_positive_breakout: rsi={rsi:.2f} ema_trend=above volume={float(volume_ratio):.2f}x",
            },
        )

    def _create_sell_signal(
        self, market_data: Quote, rsi: float, ema: float, volume_ratio: Decimal
    ) -> Signal:
        """
        Crear señal de venta con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen

        Returns:
            Señal de venta
        """
        return Signal(
            symbol=market_data.symbol,
            signal_type=SignalType.SELL,
            strength=SignalStrength.MODERATE,  # Más conservador
            confidence=abs(50.0 - float(rsi)),  # Usar distancia de RSI desde 50 como confidence
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=market_data.volume,
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "rsi": str(rsi),
                "ema": str(ema),
                "volume_ratio": str(volume_ratio),
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "momentum_type": "negative_reversal",
                "reason": f"momentum_negative_reversal: rsi={rsi:.2f} ema_trend=below volume={float(volume_ratio):.2f}x",
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
