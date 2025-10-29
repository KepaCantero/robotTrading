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
        Calcular Z-score del precio.

        Args:
            market_data: Datos de mercado

        Returns:
            Z-score calculado
        """
        # Implementación simplificada - en producción usar datos históricos
        # Simula Z-score basado en variación diaria del precio
        
        # Calculate price change vs open
        price_change = (market_data.last - market_data.open) / market_data.open
        
        # Simulate Z-score based on price movement
        # More variation = higher z-score magnitude
        std_dev = Decimal("0.02")  # 2% standard deviation
        
        if std_dev == 0:
            return Decimal("0")
        
        # Use price change as proxy for Z-score
        z_score = price_change / std_dev
        
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
        # Check if z-score indicates undervaluation
        is_undervalued = z_score < -self.z_score_threshold
        
        # Require confirmation: price closed significantly below open (relaxed from 0.5% to 0.3%)
        price_drop = (market_data.open - market_data.close) / market_data.open > Decimal("0.003")  # > 0.3% drop
        
        # Only allow moderate volatility (relaxed check)
        acceptable_volatility = volatility < self.volatility_threshold * 2  # More permissive
        
        return is_undervalued and price_drop and acceptable_volatility

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
        # Check if z-score indicates overvaluation
        is_overvalued = z_score > self.z_score_threshold
        
        # Require confirmation: price closed significantly above open (relaxed from 0.005 to 0.003)
        price_rise = (market_data.close - market_data.open) / market_data.open > Decimal("0.003")  # > 0.3% rise
        
        # Only allow moderate volatility (relaxed check)
        acceptable_volatility = volatility < self.volatility_threshold * 2  # More permissive
        
        return is_overvalued and price_rise and acceptable_volatility

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
