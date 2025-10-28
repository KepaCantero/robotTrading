"""
MomentumStrategy - Estrategia de momentum basada en RSI, EMA y volumen.

Implementa una estrategia de momentum que utiliza indicadores técnicos
para identificar oportunidades de trading basadas en tendencias de precio.
"""

import logging
from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.core.centralized_config import get_strategy_config, get_trading_threshold
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.services.signal_scoring_engine import get_signal_scoring_engine

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
        self.rsi_history = deque(maxlen=50)  # TASK-IND-STOCH-2: Histórico para Stochastic RSI

        # Cooldown para evitar señales repetidas
        self.last_signal_bar_index = None
        self.last_signal_type = None
        self.current_bar_index = 0
        self.cooldown_bars = config.get("cooldown_bars", 5)  # Número de barras para cooldown

        # TASK-SC-5: Signal Scoring Engine integration
        self.signal_scoring_engine = get_signal_scoring_engine()

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
            Lista de señales generadas (procesadas por Signal Scoring Engine)
        """
        raw_signals = []

        try:
            # Actualizar histórico
            self.price_history.append(float(market_data.close or market_data.last))
            self.volume_history.append(float(market_data.volume))
            self.current_bar_index += 1

            # Calcular indicadores técnicos reales
            rsi = self._calculate_real_rsi()
            ema = self._calculate_real_ema()
            volume_ratio = self._calculate_volume_ratio(market_data)
            roc = self._calculate_real_roc()  # TASK-IND-ROC-2: Calcular ROC
            obv_trend = self._calculate_obv_trend()  # TASK-IND-OBV-1: Calcular tendencia OBV
            
            # TASK-IND-STOCH-2: Calcular Stochastic RSI para filtrar falsas señales
            stoch_rsi, stoch_rsi_signal = self._calculate_stochastic_rsi()

            # Sólo generar señales si tenemos suficiente histórico
            if rsi is None or ema is None:
                return []

            # Convertir None a valores seguros para logging
            roc_safe = roc if roc is not None else 0.0
            stoch_rsi_safe = stoch_rsi if stoch_rsi is not None else 0.0

            # Guardar para uso en señales
            self.last_rsi = rsi
            self.last_ema = ema
            if rsi is not None:
                self.rsi_history.append(rsi)  # TASK-IND-STOCH-2: Guardar histórico RSI

            # Verificar cooldown
            if not self._is_cooldown_active(market_data):
                # TASK-IND-STOCH-2: Filtrar falsas señales con Stochastic RSI
                if self._should_generate_signal(stoch_rsi, stoch_rsi_signal):
                    # Generar señal de compra con condiciones robustas
                    if self._is_buy_signal(rsi, ema, volume_ratio, roc, obv_trend, market_data):
                        signal = self._create_buy_signal(market_data, rsi, ema, volume_ratio, roc)
                        raw_signals.append(signal)
                        self.last_signal_bar_index = self.current_bar_index
                        self.last_signal_type = "buy"
                        logger.debug(
                            f"Generated BUY signal for {market_data.symbol}: RSI={rsi:.2f}, EMA={ema:.2f}, ROC={roc_safe:.2f}, OBV={obv_trend}, StochRSI={stoch_rsi_safe:.2f}"
                        )

                    # Generar señal de venta con condiciones robustas
                    elif self._is_sell_signal(rsi, ema, volume_ratio, roc, obv_trend, market_data):
                        signal = self._create_sell_signal(market_data, rsi, ema, volume_ratio, roc)
                        raw_signals.append(signal)
                        self.last_signal_bar_index = self.current_bar_index
                        self.last_signal_type = "sell"
                        logger.debug(
                            f"Generated SELL signal for {market_data.symbol}: RSI={rsi:.2f}, EMA={ema:.2f}, ROC={roc_safe:.2f}, OBV={obv_trend}, StochRSI={stoch_rsi_safe:.2f}"
                        )
                else:
                    logger.debug("Signal suppressed by Stochastic RSI filter")
            else:
                logger.debug("Signal suppressed due to cooldown period")

        except Exception as e:
            logger.error(f"Error generating signals for {market_data.symbol}: {e}")

        # TASK-SC-5: Process signals through Signal Scoring Engine
        # For backtesting, disable cooldown to allow all signals through
        if raw_signals:
            processed_signals = self.signal_scoring_engine.process_signals(raw_signals, apply_cooldown=False)
            return processed_signals

        return []

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

    def _calculate_real_roc(self, period: int = 12) -> Optional[float]:
        """
        TASK-IND-ROC-2: Calcular ROC (Rate of Change) real usando histórico.

        Args:
            period: Período para cálculo de ROC (default 12)

        Returns:
            Valor de ROC como porcentaje o None si no hay suficiente histórico
        """
        if len(self.price_history) < period + 1:
            return None

        prices = list(self.price_history)
        current_price = prices[-1]
        price_periods_ago = prices[-period - 1]

        if price_periods_ago == 0:
            return None

        roc = ((current_price - price_periods_ago) / price_periods_ago) * 100

        return round(roc, 2)

    def _calculate_real_obv(self) -> Optional[float]:
        """
        TASK-IND-OBV-1: Calcular OBV (On Balance Volume) real usando histórico.

        OBV acumula volumen basado en cambios de precio:
        - Suma volumen cuando precio sube
        - Resta volumen cuando precio baja
        - Permanece igual cuando precio no cambia

        Returns:
            Valor de OBV o None si no hay suficiente histórico
        """
        if len(self.price_history) < 2 or len(self.volume_history) < 2:
            return None

        obv = 0.0

        # Iterar sobre el histórico para calcular OBV acumulativo
        for i in range(1, len(self.price_history)):
            current_price = self.price_history[i]
            previous_price = self.price_history[i - 1]
            current_volume = self.volume_history[i]

            if current_price > previous_price:
                # Precio subió: sumar volumen
                obv += current_volume
            elif current_price < previous_price:
                # Precio bajó: restar volumen
                obv -= current_volume
            # Si precio no cambió, OBV permanece igual

        return round(obv, 2)

    def _calculate_obv_trend(self, lookback: int = 10) -> Optional[str]:
        """
        TASK-IND-OBV-1: Calcular tendencia de OBV.

        Compara OBV actual vs. OBV de hace N períodos para determinar la tendencia.

        Args:
            lookback: Períodos para comparar (default 10)

        Returns:
            "rising" si OBV está aumentando (buying pressure)
            "falling" si OBV está disminuyendo (selling pressure)
            "neutral" si es estable
            None si no hay suficiente histórico
        """
        if len(self.price_history) < lookback + 2:
            return None

        # Calcular OBV actual
        current_obv = 0.0
        for i in range(1, len(self.price_history)):
            if self.price_history[i] > self.price_history[i - 1]:
                current_obv += self.volume_history[i]
            elif self.price_history[i] < self.price_history[i - 1]:
                current_obv -= self.volume_history[i]

        # Calcular OBV de hace N períodos
        period_start = max(0, len(self.price_history) - lookback - 2)
        past_obv = 0.0
        for i in range(period_start + 1, len(self.price_history) - lookback + 1):
            if i < len(self.price_history) and i - 1 >= 0:
                if self.price_history[i] > self.price_history[i - 1]:
                    past_obv += self.volume_history[i]
                elif self.price_history[i] < self.price_history[i - 1]:
                    past_obv -= self.volume_history[i]

        # Comparar para determinar tendencia
        if current_obv > past_obv * 1.02:  # 2% margen para evitar ruido
            return "rising"
        elif current_obv < past_obv * 0.98:
            return "falling"
        else:
            return "neutral"

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
        roc: Optional[float],
        obv_trend: Optional[str],
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de compra con condiciones robustas.

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC (Rate of Change) - TASK-IND-ROC-2
            obv_trend: Tendenica de OBV - TASK-IND-OBV-1
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
        # 5. TASK-IND-ROC-2: ROC > 0 para confirmar aceleración de precio
        # 6. TASK-IND-OBV-1: OBV "rising" o "neutral" para confirmar buying pressure
        rsi_positive = rsi > 55
        ema_bullish = current_price > Decimal(str(ema))
        has_volume = volume_ratio > Decimal(
            "1.2"
        )  # TASK-IND-5: volume_ratio > 1.2 para liquidez confirmada
        
        # TASK-IND-ROC-2: ROC positivo confirma aceleración alcista
        roc_positive = roc is not None and roc > 0
        
        # TASK-IND-OBV-1: OBV rising o neutral confirma buying pressure
        obv_bullish = obv_trend is None or obv_trend in ["rising", "neutral"]

        return rsi_positive and ema_bullish and has_volume and roc_positive and obv_bullish

    def _is_sell_signal(
        self,
        rsi: float,
        ema: float,
        volume_ratio: Decimal,
        roc: Optional[float],
        obv_trend: Optional[str],
        market_data: Quote,
    ) -> bool:
        """
        Determinar si generar señal de venta con condiciones robustas.

        Args:
            rsi: Valor de RSI (0-100)
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC (Rate of Change) - TASK-IND-ROC-2
            obv_trend: Tendencia de OBV - TASK-IND-OBV-1
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
        # 5. TASK-IND-ROC-2: ROC < 0 para confirmar aceleración bajista
        # 6. TASK-IND-OBV-1: OBV "falling" o "neutral" para confirmar selling pressure
        rsi_negative = rsi < 45
        ema_bearish = current_price < Decimal(str(ema))
        has_volume = volume_ratio > Decimal(
            "1.2"
        )  # TASK-IND-5: volume_ratio > 1.2 para liquidez confirmada
        
        # TASK-IND-ROC-2: ROC negativo confirma aceleración bajista
        roc_negative = roc is not None and roc < 0
        
        # TASK-IND-OBV-1: OBV falling o neutral confirma selling pressure
        obv_bearish = obv_trend is None or obv_trend in ["falling", "neutral"]

        return rsi_negative and ema_bearish and has_volume and roc_negative and obv_bearish

    def _create_buy_signal(
        self, market_data: Quote, rsi: float, ema: float, volume_ratio: Decimal, roc: Optional[float]
    ) -> Signal:
        """
        Crear señal de compra con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC - TASK-IND-ROC-2

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
                "roc": str(roc) if roc is not None else "N/A",
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "momentum_type": "positive_breakout",
                "reason": f"momentum_positive_breakout: rsi={rsi:.2f} ema_trend=above volume={float(volume_ratio):.2f}x roc={roc:.2f}" if roc is not None else f"momentum_positive_breakout: rsi={rsi:.2f} ema_trend=above volume={float(volume_ratio):.2f}x",
            },
        )

    def _create_sell_signal(
        self, market_data: Quote, rsi: float, ema: float, volume_ratio: Decimal, roc: Optional[float]
    ) -> Signal:
        """
        Crear señal de venta con metadata completa.

        Args:
            market_data: Datos de mercado
            rsi: Valor de RSI
            ema: Valor de EMA
            volume_ratio: Ratio de volumen
            roc: Valor de ROC - TASK-IND-ROC-2

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
                "roc": str(roc) if roc is not None else "N/A",
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "momentum_type": "negative_reversal",
                "reason": f"momentum_negative_reversal: rsi={rsi:.2f} ema_trend=below volume={float(volume_ratio):.2f}x roc={roc:.2f}" if roc is not None else f"momentum_negative_reversal: rsi={rsi:.2f} ema_trend=below volume={float(volume_ratio):.2f}x",
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

    def _calculate_stochastic_rsi(self, period: int = 14) -> Tuple[Optional[float], Optional[float]]:
        """
        TASK-IND-STOCH-2: Calcular Stochastic RSI para filtrar falsas señales.

        Stochastic RSI ayuda a identificar condiciones de sobrecompra/sobreventa
        más precisamente que RSI solo, reduciendo falsas señales.

        Args:
            period: Período para cálculo (default 14)

        Returns:
            Tuple de (stoch_rsi, stoch_rsi_signal) o (None, None)
        """
        if len(self.rsi_history) < period:
            return None, None

        rsi_values = list(self.rsi_history)
        recent_rsi = rsi_values[-period:]

        # Calcular %K
        highest_rsi = max(recent_rsi)
        lowest_rsi = min(recent_rsi)
        current_rsi = recent_rsi[-1]

        if highest_rsi == lowest_rsi:
            return None, None

        stoch_rsi_k = ((current_rsi - lowest_rsi) / (highest_rsi - lowest_rsi)) * 100

        # Calcular %D como SMA de 3 períodos
        if len(rsi_values) >= period + 2:
            k_values = []
            for i in range(max(-3, -(len(rsi_values) - 1)), 0):
                if len(rsi_values[i - period : i]) == period:
                    recent = rsi_values[i - period : i]
                    high = max(recent)
                    low = min(recent)
                    if high != low:
                        k = ((recent[-1] - low) / (high - low)) * 100
                        k_values.append(k)
            stoch_rsi_d = sum(k_values) / len(k_values) if k_values else stoch_rsi_k
        else:
            stoch_rsi_d = stoch_rsi_k

        return round(stoch_rsi_k, 2), round(stoch_rsi_d, 2)

    def _should_generate_signal(self, stoch_rsi: Optional[float], stoch_rsi_signal: Optional[float]) -> bool:
        """
        TASK-IND-STOCH-2: Determinar si se debe generar señal basado en Stochastic RSI.

        Filtra falsas señales basándose en condiciones de Stochastic RSI:
        - Buy signals: StochRSI debe estar por encima de 20 (salir de sobreventa)
        - Sell signals: StochRSI debe estar por debajo de 80 (salir de sobrecompra)

        Args:
            stoch_rsi: Valor de Stochastic RSI
            stoch_rsi_signal: Valor de señal de Stochastic RSI

        Returns:
            True si se debe generar señal, False si se debe filtrar
        """
        # Si no hay suficiente data, permitir señales (degradación tolerante)
        if stoch_rsi is None or stoch_rsi_signal is None:
            return True

        # Condiciones de filtrado:
        # - Generar señales cuando no está en extremos (evitar sobrecompra/sobreventa)
        # - Esto reduce falsas señales en zonas extremas
        return 20 <= stoch_rsi <= 80
