"""
PairsTradingStrategy - Estrategia de trading de pares basada en cointegración.

Implementa una estrategia de pairs trading que identifica pares de activos
cointegrados y comercia cuando el spread entre ellos se desvía significativamente.
"""

from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
import logging

from .base import BaseStrategy
from app.models.market_data import Quote
from app.models.signal import Signal
from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PairsTradingStrategy(BaseStrategy):
    """Estrategia de trading de pares basada en cointegración."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia de pairs trading.
        
        Args:
            config: Configuración de la estrategia
        """
        super().__init__(config)
        
        # Parámetros de la estrategia
        self.cointegration_threshold = Decimal(str(config.get("cointegration_threshold", 0.05)))
        self.spread_threshold = Decimal(str(config.get("spread_threshold", 2.0)))
        self.stop_loss = Decimal(str(config.get("stop_loss", 0.04)))
        self.take_profit = Decimal(str(config.get("take_profit", 0.08)))
        self.max_position_size = Decimal(str(config.get("max_position_size", 0.06)))
        
        # Parámetros de pares
        self.pair_symbols = config.get("pair_symbols", ["AAPL", "MSFT"])
        self.lookback_period = config.get("lookback_period", 30)
        self.min_correlation = Decimal(str(config.get("min_correlation", 0.7)))
        
        # Parámetros adicionales
        self.hedge_ratio = Decimal(str(config.get("hedge_ratio", 1.0)))
        self.max_spread_deviation = Decimal(str(config.get("max_spread_deviation", 3.0)))
        
        logger.info(f"PairsTradingStrategy initialized: {self.name}")
        logger.info(f"Trading pair: {self.pair_symbols}")
    
    def get_required_parameters(self) -> List[str]:
        """
        Obtener parámetros requeridos para la estrategia.
        
        Returns:
            Lista de parámetros requeridos
        """
        return [
            "cointegration_threshold",
            "spread_threshold",
            "stop_loss",
            "take_profit",
            "max_position_size",
            "pair_symbols"
        ]
    
    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales de trading basadas en pairs trading.
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            Lista de señales generadas
        """
        signals = []
        
        try:
            # Verificar si el símbolo es parte del par
            if market_data.symbol not in self.pair_symbols:
                return signals
            
            # Calcular métricas del par
            spread = self._calculate_spread(market_data)
            correlation = self._calculate_correlation(market_data)
            cointegration_score = self._calculate_cointegration_score(market_data)
            
            # Generar señales basadas en el spread
            if self._is_spread_signal(spread, correlation, cointegration_score, market_data):
                pair_signals = self._create_pair_signals(market_data, spread)
                signals.extend(pair_signals)
                logger.debug(f"Generated pair signals for {market_data.symbol} (spread: {spread})")
            
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
            
            # Verificar límites de exposición (muy conservador para pairs trading)
            total_exposure = self._calculate_total_exposure(portfolio)
            if total_exposure > Decimal("0.4"):  # Máximo 40% de exposición
                logger.debug(f"Total exposure too high: {total_exposure}")
                return False
            
            # Verificar balance del par (pairs trading debe ser balanceado)
            pair_exposure = self._calculate_pair_exposure(portfolio)
            if pair_exposure > Decimal("0.2"):  # Máximo 20% de exposición por par
                logger.debug(f"Pair exposure too high: {pair_exposure}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Risk check error: {e}")
            return False
    
    def _calculate_spread(self, market_data: Quote) -> Decimal:
        """
        Calcular spread entre los activos del par.
        
        Args:
            market_data: Datos de mercado
            
        Returns:
            Spread calculado
        """
        # Implementación simplificada - en producción usar datos históricos
        # Por ahora, simulamos spread basado en precio
        
        if market_data.symbol == self.pair_symbols[0]:
            # Simular precio del segundo activo
            other_price = market_data.last * Decimal("1.1")
            spread = market_data.last - other_price * self.hedge_ratio
        else:
            # Simular precio del primer activo
            other_price = market_data.last * Decimal("0.9")
            spread = other_price - market_data.last * self.hedge_ratio
        
        return spread
    
    def _calculate_correlation(self, market_data: Quote) -> Decimal:
        """
        Calcular correlación entre los activos del par.
        
        Args:
            market_data: Datos de mercado
            
        Returns:
            Correlación calculada
        """
        # Implementación simplificada
        return Decimal("0.85")  # Correlación alta simulada
    
    def _calculate_cointegration_score(self, market_data: Quote) -> Decimal:
        """
        Calcular score de cointegración.
        
        Args:
            market_data: Datos de mercado
            
        Returns:
            Score de cointegración
        """
        # Implementación simplificada
        return Decimal("0.95")  # Alta cointegración simulada
    
    def _is_spread_signal(self, spread: Decimal, correlation: Decimal,
                         cointegration_score: Decimal, market_data: Quote) -> bool:
        """
        Determinar si generar señal basada en el spread.
        
        Args:
            spread: Spread calculado
            correlation: Correlación entre activos
            cointegration_score: Score de cointegración
            market_data: Datos de mercado
            
        Returns:
            True si debe generar señal
        """
        return (
            abs(spread) > self.spread_threshold and  # Spread significativo
            correlation > self.min_correlation and  # Correlación suficiente
            cointegration_score > self.cointegration_threshold and  # Cointgración válida
            abs(spread) < self.max_spread_deviation  # Spread no extremo
        )
    
    def _create_pair_signals(self, market_data: Quote, spread: Decimal) -> List[Signal]:
        """
        Crear señales para ambos activos del par.
        
        Args:
            market_data: Datos de mercado
            spread: Spread calculado
            
        Returns:
            Lista de señales para el par
        """
        signals = []
        quantity = Decimal("50")  # Cantidad menor (pairs trading es más conservador)
        
        if market_data.symbol == self.pair_symbols[0]:
            # Primer activo del par
            if spread > 0:
                # Spread positivo: vender activo 1, comprar activo 2
                signal1 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MODERATE,
                    confidence=65.0,
                    liquidity_score=70.0,
                    priority_score=75.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=market_data.volume,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "sell_asset1",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit)
                    }
                )
                signals.append(signal1)
            else:
                # Spread negativo: comprar activo 1, vender activo 2
                signal1 = Signal(
                    symbol=market_data.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MODERATE,
                    confidence=65.0,
                    liquidity_score=70.0,
                    priority_score=75.0,
                    source=SignalSource.MOMENTUM,
                    price=market_data.last,
                    volume=market_data.volume,
                    timestamp=market_data.timestamp,
                    metadata={
                        "strategy": self.name,
                        "pair_type": "buy_asset1",
                        "spread": str(spread),
                        "hedge_ratio": str(self.hedge_ratio),
                        "stop_loss": str(self.stop_loss),
                        "take_profit": str(self.take_profit)
                    }
                )
                signals.append(signal1)
        
        return signals
    
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
    
    def _calculate_pair_exposure(self, portfolio: Portfolio) -> Decimal:
        """
        Calcular exposición específica del par.
        
        Args:
            portfolio: Portfolio actual
            
        Returns:
            Exposición del par como porcentaje
        """
        total_value = portfolio.cash
        for position in portfolio.positions:
            total_value += position.market_value
        
        if total_value == 0:
            return Decimal("0")
        
        pair_value = Decimal("0")
        for position in portfolio.positions:
            if position.symbol in self.pair_symbols:
                pair_value += position.market_value
        
        return pair_value / total_value
