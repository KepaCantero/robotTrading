"""
MeanReversionStrategy - Estrategia de reversión a la media basada en Z-score.

REFACTORED: Usa pandas-ta-classic para cálculos de z-score y volatilidad (NO cálculos manuales).

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
from app.services.momentum_analysis import TechnicalIndicatorCalculator

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
            self.z_score_threshold = Decimal(str(params.get("z_score_threshold")))
            self.lookback_period = params.get("lookback_period")
            self.volatility_threshold = Decimal(str(params.get("volatility_threshold")))
            self.mean_reversion_speed = Decimal(str(params.get("mean_reversion_speed")))
            # FIX: Load atr_floor and price_range_multiplier from config
            self.atr_floor = Decimal(str(params.get("atr_floor")))
            self.price_range_multiplier = Decimal(str(params.get("price_range_multiplier")))

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
            self.z_score_threshold = Decimal(str(config.get("z_score_threshold")))
            self.lookback_period = config.get("lookback_period")
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )
            self.volatility_threshold = Decimal(str(config.get("volatility_threshold")))
            self.mean_reversion_speed = Decimal(str(config.get("mean_reversion_speed")))
            # FIX: Load atr_floor and price_range_multiplier from config (fallback)
            self.atr_floor = Decimal(str(config.get("atr_floor")))
            self.price_range_multiplier = Decimal(str(config.get("price_range_multiplier")))

        # Parámetros adicionales
        min_z_score_value = config.get("min_z_score")
        if min_z_score_value is None and strategy_config:
            min_z_score_value = strategy_config.parameters.get("min_z_score", 1.5)
        elif min_z_score_value is None:
            min_z_score_value = 1.5  # Valor por defecto
        self.min_z_score = Decimal(str(min_z_score_value))

        # Initialize price history for logging purposes (similar to MomentumStrategy)
        from collections import deque
        self.price_history = deque(maxlen=200)  # Maintain up to 200 bars of history
        
        # ✅ USE LIBRARY: Initialize TechnicalIndicatorCalculator (uses pandas-ta-classic)
        self.indicator_calculator = TechnicalIndicatorCalculator()

        logger.info(f"MeanReversionStrategy initialized: {self.name}")
        config_value = strategy_config.parameters.get('z_score_threshold') if strategy_config else 'NO_CONFIG'
        logger.info(f"⚠️ CRITICAL: z_score_threshold={self.z_score_threshold} (target: 1.0, config loaded: {config_value})")

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
            # Calcular Z-score y volatilidad
            z_score = self._calculate_z_score(market_data)
            volatility = self._calculate_volatility(market_data)
            
            # Logging de diagnóstico (INFO level cada cierto número de llamadas)
            current_price = market_data.close or market_data.last
            price_change_pct = ((market_data.close - market_data.open) / market_data.open * 100) if market_data.open > 0 else Decimal("0")
            
            # Logging periódico para diagnóstico
            if not hasattr(self, '_call_count'):
                self._call_count = 0
            self._call_count += 1
            
            # Update price history for tracking
            if not hasattr(self, 'price_history'):
                from collections import deque
                self.price_history = deque(maxlen=200)
            self.price_history.append(float(current_price))
            
            # Log ALL candidates (every call) at DEBUG level
            logger.debug(
                f"🔍 MEAN_REVERSION CANDIDATE {market_data.symbol}: "
                f"price={current_price:.2f}, price_change={price_change_pct:.2f}%, "
                f"z_score={z_score:.4f}, volatility={volatility:.4f}, "
                f"threshold={self.z_score_threshold}, history_len={len(self.price_history)}"
            )
            
            # More frequent logging (every 10 calls) for INFO level
            if self._call_count % 10 == 0:
                logger.info(
                    f"🔍 MEAN_REVERSION {market_data.symbol}: "
                    f"price={current_price:.2f}, z_score={z_score:.4f}, "
                    f"volatility={volatility:.4f}, threshold={self.z_score_threshold}"
                )
            
            # Evaluar condiciones BUY y SELL
            buy_condition = self._is_buy_signal(z_score, volatility, market_data)
            sell_condition = self._is_sell_signal(z_score, volatility, market_data)
            
            # Log ALL candidates when conditions are checked
            logger.debug(
                f"🔍 MEAN_REVERSION CONDITIONS {market_data.symbol}: "
                f"buy_condition={buy_condition}, sell_condition={sell_condition}, "
                f"z_score={z_score:.4f}, price={current_price:.2f}"
            )
            
            # Logging cuando condiciones son True (INFO level)
            if buy_condition or sell_condition:
                logger.info(
                    f"✅ MEAN_REVERSION CONDITIONS MET {market_data.symbol}: z_score={z_score:.4f}, "
                    f"volatility={volatility:.4f}, BUY={buy_condition}, SELL={sell_condition}"
                )

            # Generar señal de compra (precio bajo, esperamos subida)
            if buy_condition:
                signal = self._create_buy_signal(market_data, z_score)
                signals.append(signal)
                logger.info(
                    f"✅ MEAN_REVERSION Generated BUY signal for {market_data.symbol}: "
                    f"Z-score={z_score:.4f}, price={current_price:.2f}, volatility={volatility:.4f}"
                )

            # Generar señal de venta (precio alto, esperamos bajada)
            if sell_condition:  # Changed from elif to if to allow both signals
                signal = self._create_sell_signal(market_data, z_score)
                signals.append(signal)
                logger.info(
                    f"✅ MEAN_REVERSION Generated SELL signal for {market_data.symbol}: "
                    f"Z-score={z_score:.4f}, price={current_price:.2f}, volatility={volatility:.4f}"
                )

        except Exception as e:
            logger.error(f"MEAN_REVERSION Error generating signals for {market_data.symbol}: {e}", exc_info=True)

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
            # FIX: Order matters - check SELL position existence BEFORE calculating position_size
            # For SELL, if no position exists, get_position_size() returns 0, which fails the min check
            if signal.signal_type == SignalType.SELL:
                # First check if position exists
                existing_position = self._get_existing_position(portfolio, signal.symbol)
                if not existing_position:
                    logger.info(
                        f"⚠️ MEAN_REVERSION risk_check REJECTED SELL {signal.symbol}: "
                        f"No position exists to sell"
                    )
                    return False
                # Now calculate sell quantity and verify we have enough
                sell_quantity = self.get_position_size(signal, portfolio)
                if sell_quantity <= 0:
                    logger.info(
                        f"⚠️ MEAN_REVERSION risk_check REJECTED SELL {signal.symbol}: "
                        f"Position size too small ({sell_quantity:.6f})"
                    )
                    return False
                if existing_position.quantity < sell_quantity:
                    logger.info(
                        f"⚠️ MEAN_REVERSION risk_check REJECTED SELL {signal.symbol}: "
                        f"Insufficient position (need={sell_quantity:.6f}, have={existing_position.quantity:.6f})"
                    )
                    return False
                # For SELL, position_size is the sell_quantity
                position_size = sell_quantity
            elif signal.signal_type == SignalType.BUY:
                # For BUY, calculate position size and verify cash
                position_size = self.get_position_size(signal, portfolio)
                if position_size <= 0:
                    logger.info(
                        f"⚠️ MEAN_REVERSION risk_check REJECTED BUY {signal.symbol}: "
                        f"Position size too small ({position_size:.6f})"
                    )
                    return False
                required_cash = signal.price * position_size
                if required_cash > portfolio.cash:
                    logger.info(
                        f"⚠️ MEAN_REVERSION risk_check REJECTED BUY {signal.symbol}: "
                        f"Insufficient cash (required=${required_cash:.2f} > available=${portfolio.cash:.2f}, "
                        f"position_size={position_size:.6f})"
                    )
                    return False
            else:
                # HOLD or other signal types - not supported
                return False

            # Verificar límites de exposición (más conservador que momentum)
            total_exposure = self._calculate_total_exposure(portfolio)
            max_exposure = Decimal("0.6")  # Máximo 60% de exposición
            if total_exposure > max_exposure:
                logger.info(
                    f"⚠️ MEAN_REVERSION risk_check REJECTED {signal.signal_type} {signal.symbol}: "
                    f"Total exposure too high ({total_exposure:.2%} > {max_exposure:.2%})"
                )
                return False

            # Verificar volatilidad del activo
            volatility = self._calculate_volatility_from_signal(signal)
            max_volatility = self.volatility_threshold * 2  # Evitar activos muy volátiles
            if volatility > max_volatility:
                logger.info(
                    f"⚠️ MEAN_REVERSION risk_check REJECTED {signal.signal_type} {signal.symbol}: "
                    f"Asset too volatile ({volatility:.4f} > {max_volatility:.4f} threshold)"
                )
                return False

            logger.debug(
                f"✅ MEAN_REVERSION risk_check PASSED {signal.signal_type} {signal.symbol}: "
                f"position_size={position_size:.6f}, cash=${portfolio.cash:.2f}, "
                f"exposure={total_exposure:.2%}, volatility={volatility:.4f}"
            )
            return True

        except Exception as e:
            logger.error(
                f"❌ MEAN_REVERSION risk_check ERROR for {signal.symbol}: {e}",
                exc_info=True
            )
            return False

    def _calculate_z_score(self, market_data: Quote) -> Decimal:
        """
        Calcular Z-score del precio usando pandas-ta-classic.zscore() library.
        
        ✅ REFACTORED: Uses pandas_ta_classic.zscore() - NO manual calculations

        Args:
            market_data: Datos de mercado

        Returns:
            Z-score calculado
        """
        if len(self.price_history) < self.lookback_period:
            # Not enough history - use simplified calculation
            price_change = (market_data.last - market_data.open) / market_data.open if market_data.open > 0 else Decimal("0")
            std_dev = Decimal("0.02")
            return price_change / std_dev if std_dev > 0 else Decimal("0")
        
        # ✅ USE LIBRARY: Use TechnicalIndicatorCalculator.calculate_zscore() (pandas-ta-classic)
        prices_list = [float(p) for p in list(self.price_history)]
        current_price = float(market_data.last)
        
        # Add current price for calculation
        prices_with_current = prices_list + [current_price]
        
        # Calculate z-score using pandas-ta-classic (rolling z-score with lookback_period)
        z_score_raw = self.indicator_calculator.calculate_zscore(
            prices_with_current, 
            period=self.lookback_period, 
            std=1.0
        )
        
        if z_score_raw is None:
            logger.debug(f"MEAN_REVERSION {market_data.symbol}: Z-score calculation returned None")
            return Decimal("0")
        
        z_score = Decimal(str(z_score_raw))
        
        logger.debug(
            f"MEAN_REVERSION {market_data.symbol}: Z-score calculated via pandas-ta-classic: {z_score:.4f} "
            f"(price={current_price:.2f}, lookback={self.lookback_period})"
        )
        
        return z_score

    def _calculate_volatility(self, market_data: Quote) -> Decimal:
        """
        Calcular volatilidad del activo usando pandas-ta-classic.volatility() library.
        
        ✅ REFACTORED: Uses pandas_ta_classic.volatility() - NO manual calculations

        Args:
            market_data: Datos de mercado

        Returns:
            Volatilidad calculada
        """
        if len(self.price_history) < 2:
            # Fallback to simple calculation
            price_range = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0")
            return price_range
        
        # ✅ USE LIBRARY: Use TechnicalIndicatorCalculator.calculate_volatility() (pandas-ta-classic)
        prices_list = [float(p) for p in list(self.price_history)]
        current_price = float(market_data.last)
        prices_with_current = prices_list + [current_price]
        
        # Calculate volatility using pandas-ta-classic (daily volatility)
        volatility_raw = self.indicator_calculator.calculate_volatility(
            prices_with_current,
            tf='days',
            returns=False,
            log=False
        )
        
        if volatility_raw is None:
            # Fallback to simple calculation if library returns None
            price_range = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0")
            logger.debug(f"MEAN_REVERSION {market_data.symbol}: Volatility calculation returned None, using fallback")
            return price_range
        
        volatility = Decimal(str(volatility_raw))
        
        logger.debug(
            f"MEAN_REVERSION {market_data.symbol}: Volatility calculated via pandas-ta-classic: {volatility:.6f} "
            f"from {len(prices_with_current)} prices"
        )
        
        return volatility

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
        # OPTIMIZED: More permissive BUY conditions for 50-100 trades target
        # Check if z-score indicates undervaluation (reduced threshold to 70%)
        z_score_buy = -self.z_score_threshold * Decimal("0.7")  # 70% of threshold (was 0.8)
        is_undervalued = z_score < z_score_buy
        
        # Make price drop optional - if z-score is very negative, don't require price drop
        price_drop_min = Decimal("0.001")  # Reduced from 0.002 to 0.1% drop (more permissive)
        price_drop = (market_data.open - market_data.close) / market_data.open > price_drop_min
        very_oversold = z_score < -self.z_score_threshold * Decimal("1.2")  # Reduced from 1.5 to 1.2
        
        # Price range multiplier for relative price moves
        price_range = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0")
        acceptable_price_range = price_range >= self.atr_floor * self.price_range_multiplier
        
        # Only allow moderate volatility (more relaxed)
        acceptable_volatility = volatility < self.volatility_threshold * 4  # More permissive (4x)
        
        # OPTIMIZED: BUY if: (undervalued + acceptable_range) OR (very oversold + acceptable_range)
        # Removed price_drop requirement for more opportunities
        return (is_undervalued and acceptable_price_range and acceptable_volatility) or (very_oversold and acceptable_price_range and acceptable_volatility)

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
        # OPTIMIZED: More permissive SELL conditions for 50-100 trades target
        # Check if z-score indicates overvaluation (reduced threshold to 70%)
        z_score_sell = self.z_score_threshold * Decimal("0.7")  # 70% of threshold (was 0.8)
        is_overvalued = z_score > z_score_sell
        
        # Make price rise optional - if z-score is very positive, don't require price rise
        price_rise_min = Decimal("0.001")  # Reduced from 0.002 to 0.1% rise (more permissive)
        price_rise = (market_data.close - market_data.open) / market_data.open > price_rise_min
        very_overbought = z_score > self.z_score_threshold * Decimal("1.2")  # Reduced from 1.5 to 1.2
        
        # Price range multiplier for relative price moves
        price_range = (market_data.high - market_data.low) / market_data.last if market_data.last > 0 else Decimal("0")
        acceptable_price_range = price_range >= self.atr_floor * self.price_range_multiplier
        
        # Only allow moderate volatility (more relaxed)
        acceptable_volatility = volatility < self.volatility_threshold * 4  # More permissive (4x)
        
        # OPTIMIZED: SELL if: (overvalued + acceptable_range) OR (very overbought + acceptable_range)
        # Removed price_rise requirement for more opportunities
        return (is_overvalued and acceptable_price_range and acceptable_volatility) or (very_overbought and acceptable_price_range and acceptable_volatility)

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
            volume=Decimal("1"),  # FIX: Placeholder - get_position_size() calculates actual size based on capital
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
            volume=Decimal("1"),  # FIX: Placeholder - get_position_size() calculates actual size based on capital
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
