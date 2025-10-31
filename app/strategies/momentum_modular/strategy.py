"""
ModularMomentumStrategy - Estrategia de momentum completamente modular con learning engines integrado.
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from app.strategies.base import BaseStrategy
from app.models.market_data import Quote
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import Portfolio
from app.services.momentum_analysis import TechnicalIndicatorCalculator

from .modules.market_analyzer import MarketAnalyzer
from .modules.filters import (
    EMAFilter, RSIFilter, StochRSIFilter,
    MomentumFilter, VolumeFilter, ATRFilter
)
from .learning.base_learning_engine import BaseLearningEngine
from .learning.feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class ModularMomentumStrategy(BaseStrategy):
    """
    Estrategia de momentum completamente modular con learning engines integrado.
    
    Características:
    - Arquitectura modular: filtros activables/desactivables
    - Learning engines: Supervised, Deep, Reinforcement Learning
    - Análisis de contexto de mercado
    - Ajuste dinámico de thresholds basado en predicciones
    - Reentrenamiento automático
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar estrategia modular.
        
        Args:
            config: Configuración desde YAML (momentum_modular.yaml)
        """
        super().__init__(config)
        
        # Configuración
        self.preset = config.get("preset", "balanced")
        self.presets_config = config.get("presets", {})
        self.current_preset = self.presets_config.get(self.preset, {})
        
        # Módulos de análisis
        self.market_analyzer = MarketAnalyzer(config.get("market_analyzer", {}))
        
        # Filtros modulares
        modules_config = config.get("modules", {})
        self.filters = []
        filter_classes = {
            "ema_filter": EMAFilter,
            "rsi_filter": RSIFilter,
            "stoch_rsi_filter": StochRSIFilter,
            "momentum_filter": MomentumFilter,
            "volume_filter": VolumeFilter,
            "atr_filter": ATRFilter,
        }
        
        for filter_name, filter_class in filter_classes.items():
            if filter_name in modules_config:
                filter_config = modules_config[filter_name]
                if filter_config.get("enabled", True):
                    filter_instance = filter_class(filter_config, preset=self.preset)
                    self.filters.append(filter_instance)
                    logger.info(f"✅ Filtro activado: {filter_name}")
        
        # Learning engine (opcional)
        learning_config = config.get("adaptive_learning", {})
        self.learning_engine: Optional[BaseLearningEngine] = None
        if learning_config.get("enabled", False):
            engine_type = learning_config.get("engine_type", "supervised")
            try:
                if engine_type == "supervised":
                    from .learning.supervised_learning_engine import SupervisedLearningEngine
                    self.learning_engine = SupervisedLearningEngine(learning_config)
                elif engine_type == "deep":
                    from .learning.deep_learning_engine import DeepLearningEngine
                    self.learning_engine = DeepLearningEngine(learning_config)
                elif engine_type == "reinforcement":
                    from .learning.reinforcement_learning_engine import ReinforcementLearningEngine
                    self.learning_engine = ReinforcementLearningEngine(learning_config)
                
                if self.learning_engine:
                    logger.info(f"✅ Learning engine activado: {engine_type}")
            except (ImportError, RuntimeError) as e:
                logger.error(f"❌ Error al inicializar learning engine {engine_type}: {e}")
                logger.error("⚠️ Asegúrate de instalar todas las dependencias: pip install -r requirements.txt")
                raise  # Re-lanzar el error para que el usuario sepa que falta algo
        
        # Feature extractor para learning engines
        self.feature_extractor = FeatureExtractor()
        
        # Thresholds configurables
        self.min_success_probability = self.current_preset.get("min_confidence", 0.6)
        combination_mode = self.current_preset.get("combination_mode", "MAJORITY")
        self.combination_mode = combination_mode  # "ALL", "MAJORITY", "ANY"
        
        # Históricos para indicadores
        self.indicator_calculator = TechnicalIndicatorCalculator()
        self.price_history = deque(maxlen=200)
        self.high_history = deque(maxlen=200)
        self.low_history = deque(maxlen=200)
        self.volume_history = deque(maxlen=200)
        self.atr_history = deque(maxlen=100)
        
        # Histórico de trades para metadata
        self.recent_trades: deque = deque(maxlen=10)
        
        logger.info(f"✅ ModularMomentumStrategy inicializada (preset: {self.preset}, "
                   f"{len(self.filters)} filtros activos, "
                   f"learning: {'✅' if self.learning_engine else '❌'})")
    
    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Genera señales usando módulos y learning engines.
        
        Args:
            market_data: Datos de mercado actuales
        
        Returns:
            Lista de señales generadas
        """
        signals = []
        
        try:
            # 1. Actualizar históricos
            current_price = float(market_data.close or market_data.bid or market_data.last or 0)
            if current_price <= 0:
                return []
            
            self.price_history.append(current_price)
            self.high_history.append(float(market_data.high or current_price))
            self.low_history.append(float(market_data.low or current_price))
            self.volume_history.append(float(market_data.volume or 0))
            
            # Necesitamos suficiente histórico para calcular indicadores
            min_history = 60  # Suficiente para EMA slow (26) + RSI (14) + buffer
            if len(self.price_history) < min_history:
                return []
            
            # 2. Calcular indicadores técnicos
            indicators = self._calculate_indicators()
            if not indicators:
                return []
            
            # 3. Analizar contexto de mercado
            price_list = list(self.price_history)
            atr_list = list(self.atr_history) if self.atr_history else []
            market_context = self.market_analyzer.analyze(market_data, price_list, atr_list)
            
            # 4. Evaluar todos los filtros
            filter_results = self._evaluate_filters(indicators, market_context)
            
            # 5. Generar señal candidata basada en filtros
            signal_type = self._determine_signal_type(filter_results, market_context)
            
            if signal_type is None:
                return []
            
            # 6. SI learning engine está activo, obtener predicción
            learning_prediction = None
            if self.learning_engine and self.learning_engine.is_ready():
                features = {
                    'indicators': indicators,
                    'filter_results': filter_results,
                    'market_context': market_context,
                    'metadata': {
                        'timestamp': market_data.timestamp if hasattr(market_data, 'timestamp') else datetime.now(),
                        'symbol': market_data.symbol,
                        'recent_trades': list(self.recent_trades),
                        'recent_win_rate': self._calculate_recent_win_rate()
                    }
                }
                
                learning_prediction = self.learning_engine.predict(features)
                
                # Filtrar señal si probabilidad es baja
                if self.learning_engine.__class__.__name__ in ['SupervisedLearningEngine', 'DeepLearningEngine']:
                    success_prob = learning_prediction.get('success_probability', learning_prediction.get('confidence', 0.5))
                    if success_prob < self.min_success_probability:
                        logger.debug(f"🚫 Señal rechazada por learning engine: prob={success_prob:.2f} < {self.min_success_probability:.2f}")
                        return []
                
                # Aplicar ajustes sugeridos por learning engine
                self._apply_learning_adjustments(learning_prediction)
            
            # 7. Crear señal
            confidence = self._calculate_signal_confidence(filter_results, learning_prediction)
            
            # Calcular strength basado en confidence
            # IMPORTANTE: Debe coincidir con validación en Signal model
            # - STRONG/VERY_STRONG requieren confidence >= 70.0
            # - WEAK requiere confidence <= 80.0
            if confidence >= 80.0:
                strength = SignalStrength.VERY_STRONG
            elif confidence >= 70.0:  # Cambiado de 65.0 a 70.0 para cumplir validación Pydantic
                strength = SignalStrength.STRONG
            elif confidence >= 50.0:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
            
            # Validación de seguridad: asegurar consistencia entre strength y confidence
            # Esto previene errores de validación Pydantic
            if strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG] and confidence < 70.0:
                # Ajustar strength a MODERATE si confidence es demasiado bajo
                logger.warning(f"⚠️ Confidence {confidence:.2f} es demasiado bajo para {strength}, ajustando a MODERATE")
                strength = SignalStrength.MODERATE
            elif strength == SignalStrength.WEAK and confidence > 80.0:
                # Ajustar strength si confidence es demasiado alto para WEAK
                logger.warning(f"⚠️ Confidence {confidence:.2f} es demasiado alto para {strength}, ajustando a MODERATE")
                strength = SignalStrength.MODERATE
            
            # Calcular liquidity_score (usar volume_ratio del indicador o default)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            liquidity_score = min(100.0, max(0.0, (volume_ratio - 0.5) * 50.0))  # Normalizar 0.5-2.0 -> 0-100
            
            # Calcular priority_score (combinación de confidence y liquidity)
            priority_score = (confidence * 0.7) + (liquidity_score * 0.3)
            
            # Obtener volume del market_data o usar un default
            volume = Decimal(str(getattr(market_data, 'volume', 0)))
            if volume == 0:
                volume = Decimal("0.01")  # Default mínimo
            
            # Usar SignalSource enum - momentum_modular es una variante de momentum
            signal_source = SignalSource.MOMENTUM
            
            signal = Signal(
                symbol=market_data.symbol,
                signal_type=signal_type,
                strength=strength,
                price=Decimal(str(current_price)),
                timestamp=market_data.timestamp if hasattr(market_data, 'timestamp') else datetime.now(),
                confidence=confidence,
                liquidity_score=liquidity_score,
                priority_score=priority_score,
                source=signal_source,
                volume=volume,
                metadata={
                    'strategy': self.name,
                    'indicators': indicators,
                    'market_context': market_context,
                    'filter_results': {name: {'passed': res.get('passed'), 'confidence': res.get('confidence')} 
                                     for name, res in filter_results.items()},
                    'learning_prediction': learning_prediction,
                    'preset': self.preset
                }
            )
            
            signals.append(signal)
            
        except Exception as e:
            logger.error(f"Error generando señal: {e}", exc_info=True)
        
        return signals
    
    def _calculate_indicators(self) -> Dict[str, Any]:
        """Calcular todos los indicadores técnicos necesarios."""
        if len(self.price_history) < 26:
            return {}
        
        prices = list(self.price_history)
        highs = list(self.high_history)
        lows = list(self.low_history)
        volumes = list(self.volume_history)
        
        indicators = {}
        
        # RSI
        rsi = self.indicator_calculator.calculate_rsi(prices, period=14)
        indicators['rsi'] = rsi if rsi is not None else 50.0
        
        # EMAs
        ema_fast = self.indicator_calculator.calculate_ema(prices, period=12)
        ema_slow = self.indicator_calculator.calculate_ema(prices, period=26)
        indicators['ema_fast'] = ema_fast if ema_fast is not None else 0.0
        indicators['ema_slow'] = ema_slow if ema_slow is not None else 0.0
        
        # Momentum / ROC
        momentum = self.indicator_calculator.calculate_roc(prices, period=14)
        indicators['momentum_roc'] = momentum if momentum is not None else 0.0
        
        # Volume
        if len(volumes) >= 20:
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1] if volumes else 0
            indicators['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
            indicators['volume'] = current_volume
            indicators['avg_volume'] = avg_volume
        else:
            indicators['volume_ratio'] = 1.0
            indicators['volume'] = volumes[-1] if volumes else 0
            indicators['avg_volume'] = 0
        
        # ATR
        atr = self.indicator_calculator.calculate_atr(highs, lows, prices, period=14)
        if atr is not None:
            self.atr_history.append(atr)
            indicators['atr'] = atr
            current_price = prices[-1]
            indicators['relative_atr'] = (atr / current_price * 100) if current_price > 0 else 0
            
            # ATR percentile
            if len(self.atr_history) >= 30:
                # Convert deque to list for slicing (deque doesn't support slice notation in older Python)
                recent_atr = list(self.atr_history)[-30:] if len(self.atr_history) > 0 else []
                sorted_atr = sorted(recent_atr)
                percentile = (sorted_atr.index(atr) / len(sorted_atr)) * 100 if atr in sorted_atr else 50
                indicators['atr_percentile'] = percentile
            else:
                indicators['atr_percentile'] = 50
        else:
            indicators['atr'] = 0.0
            indicators['relative_atr'] = 0.0
            indicators['atr_percentile'] = 50.0
        
        # StochRSI (simplificado)
        indicators['stoch_rsi_k'] = 50.0  # TODO: Implementar cálculo real
        indicators['stoch_rsi_d'] = 50.0
        
        # Precio actual
        indicators['price'] = prices[-1]
        
        return indicators
    
    def _evaluate_filters(
        self,
        indicators: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluar todos los filtros activos."""
        filter_results = {}
        
        for filter_instance in self.filters:
            try:
                # Evaluar para compra (BUY)
                result_buy = filter_instance.evaluate(indicators, market_context, 'BUY')
                filter_results[f"{filter_instance.name}_buy"] = result_buy
                
                # Evaluar para venta (SELL)
                result_sell = filter_instance.evaluate(indicators, market_context, 'SELL')
                filter_results[f"{filter_instance.name}_sell"] = result_sell
                
                # Resultado general (usar BUY para simplificar)
                filter_results[filter_instance.name] = result_buy
                
            except Exception as e:
                logger.error(f"Error evaluando filtro {filter_instance.name}: {e}")
                filter_results[filter_instance.name] = {
                    'passed': False,
                    'confidence': 0.0,
                    'reason': f"Error: {str(e)}"
                }
        
        return filter_results
    
    def _determine_signal_type(
        self,
        filter_results: Dict[str, Dict[str, Any]],
        market_context: Dict[str, Any]
    ) -> Optional[SignalType]:
        """Determinar tipo de señal basado en resultados de filtros."""
        
        if len(self.filters) == 0:
            logger.warning("⚠️ No hay filtros activos - no se pueden generar señales")
            return None
        
        # Contar solo los resultados principales de cada filtro (sin _buy/_sell)
        # Cada filtro tiene una entrada principal con su nombre
        filter_names = [f.name for f in self.filters]
        passed_filters = [
            filter_name for filter_name in filter_names
            if filter_name in filter_results and filter_results[filter_name].get('passed', False)
        ]
        
        total_filters = len(self.filters)
        
        logger.debug(f"🔍 Determinando señal: {len(passed_filters)}/{total_filters} filtros pasaron, modo={self.combination_mode}")
        logger.debug(f"   Filtros que pasaron: {passed_filters}")
        logger.debug(f"   Todos los filtros: {filter_names}")
        
        # Decidir según modo de combinación
        if self.combination_mode == "ALL":
            if len(passed_filters) == total_filters:
                logger.debug(f"✅ Todos los filtros pasaron - generando señal BUY")
                return SignalType.BUY
        elif self.combination_mode == "MAJORITY":
            required = max(1, (total_filters + 1) // 2)  # Mayoría = >50%
            if len(passed_filters) >= required:
                logger.debug(f"✅ Mayoría de filtros pasaron ({len(passed_filters)}/{total_filters}) - generando señal BUY")
                return SignalType.BUY
        elif self.combination_mode == "ANY":
            if len(passed_filters) > 0:
                logger.debug(f"✅ Al menos un filtro pasó ({len(passed_filters)}) - generando señal BUY")
                return SignalType.BUY
        
        logger.debug(f"❌ No se cumple el modo de combinación ({self.combination_mode}) - no se genera señal")
        
        # Revisar condiciones de venta (oversold/sobrecomprado)
        # Por ahora solo generamos señales BUY
        # TODO: Implementar lógica de SELL cuando hay posición abierta
        market_type = market_context.get('type', 'unknown')
        if market_type == 'trend_down':
            # Considerar venta si hay posición
            return None  # Por ahora solo compras
        
        return None
    
    def _calculate_signal_confidence(
        self,
        filter_results: Dict[str, Dict[str, Any]],
        learning_prediction: Optional[Dict[str, Any]]
    ) -> float:
        """Calcular confianza de la señal."""
        # Confianza base desde filtros
        confidences = [res.get('confidence', 0.0) for res in filter_results.values()]
        base_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Ajustar con predicción de learning engine
        if learning_prediction:
            learning_confidence = learning_prediction.get('confidence', learning_prediction.get('success_probability', 0.5))
            # Combinar: 60% filtros, 40% learning
            combined = base_confidence * 0.6 + learning_confidence * 0.4
            return min(100.0, max(0.0, combined * 100))
        
        return min(100.0, max(0.0, base_confidence * 100))
    
    def _apply_learning_adjustments(self, prediction: Dict[str, Any]) -> None:
        """Aplicar ajustes sugeridos por learning engine."""
        if not prediction:
            return
        
        # Ajustar thresholds de filtros
        filter_adjustments = prediction.get('filter_adjustments', {})
        if filter_adjustments:
            for filter_instance in self.filters:
                if filter_instance.name in filter_adjustments:
                    adjustment = filter_adjustments[filter_instance.name]
                    # Aplicar ajuste a thresholds (simplificado)
                    logger.debug(f"🔧 Ajustando {filter_instance.name}: {adjustment}")
        
        # Ajustar confianza mínima requerida
        if 'confidence' in prediction:
            predicted_confidence = prediction['confidence']
            if predicted_confidence < 0.5:
                self.min_success_probability = 0.7  # Ser más estricto
            else:
                self.min_success_probability = 0.6  # Normal
    
    def _calculate_recent_win_rate(self) -> float:
        """Calcular win rate de trades recientes."""
        if not self.recent_trades:
            return 0.5
        
        winning = sum(1 for t in self.recent_trades if t.get('pnl', 0) > 0)
        return winning / len(self.recent_trades)
    
    def add_trade_result(self, trade: Dict[str, Any]) -> None:
        """Agregar resultado de trade para aprendizaje futuro."""
        self.recent_trades.append(trade)
    
    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """Verificar criterios de riesgo (implementación básica)."""
        # Verificaciones básicas
        if signal.signal_type == SignalType.BUY:
            # Verificar capital disponible
            required_cash = signal.price * self.get_position_size(signal, portfolio)
            if required_cash > portfolio.cash:
                return False
        
        return True
    
    def get_required_parameters(self) -> List[str]:
        """Parámetros requeridos."""
        return ["name", "preset"]
    
    def get_position_size(self, signal: Signal, portfolio: Portfolio) -> Decimal:
        """Calcular tamaño de posición."""
        max_position_size = Decimal(str(self.config.get("max_position_size", 0.1)))
        available_cash = portfolio.cash
        
        if signal.signal_type == SignalType.BUY:
            max_position_value = available_cash * max_position_size
            position_size = max_position_value / signal.price
            return max(position_size, Decimal("1"))
        else:
            # SELL: usar posición existente
            for pos in portfolio.positions:
                if pos.symbol == signal.symbol:
                    return pos.quantity
            return Decimal("0")

