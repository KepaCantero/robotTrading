"""
BaseStrategyEngine - Clase base abstracta para todos los strategy engines.

Extiende BaseStrategy con funcionalidades adicionales para:
- Integración con Learning Engines
- Feature extraction estandarizado
- Callbacks para aprendizaje continuo
- Ajustes dinámicos basados en predicciones
- Soporte para composición de estrategias (ensembles)
- Integración con DataEngine y ContextEngine (Módulos 1 y 2)
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Callable
from collections.abc import Sequence

from app.strategies.base import BaseStrategy
from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalType

logger = logging.getLogger(__name__)

# Importaciones opcionales para DataEngine y ContextEngine
try:
    from app.engines.data_engine import DataEngine
    DATA_ENGINE_AVAILABLE = True
except ImportError:
    DATA_ENGINE_AVAILABLE = False
    logger.debug("DataEngine no disponible")

try:
    from app.engines.context_engine import ContextEngine
    CONTEXT_ENGINE_AVAILABLE = True
except ImportError:
    CONTEXT_ENGINE_AVAILABLE = False
    logger.debug("ContextEngine no disponible")


class BaseStrategyEngine(BaseStrategy, ABC):
    """
    Clase base abstracta para todos los strategy engines.
    
    Un Strategy Engine extiende BaseStrategy con capacidades adicionales:
    1. Integración con Learning Engines (ajustes dinámicos)
    2. Feature extraction estandarizado
    3. Callbacks para aprendizaje continuo
    4. Soporte para composición (ensembles)
    5. Métricas y tracking mejorado
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar strategy engine con configuración.
        
        Args:
            config: Diccionario con parámetros de configuración
        """
        super().__init__(config)
        
        # Learning Engine integration
        self.learning_engine = None  # Se inicializará si está disponible
        self.learning_enabled = config.get("learning_enabled", False)
        self.learning_config = config.get("learning_engine", {})
        
        # DataEngine integration (Módulo 1)
        self.data_engine = None
        self.data_engine_enabled = config.get("data_engine_enabled", False)
        if DATA_ENGINE_AVAILABLE and self.data_engine_enabled:
            data_engine_config = config.get("data_engine_config", {})
            try:
                self.data_engine = DataEngine(data_engine_config)
                logger.info(f"{self.__class__.__name__}: DataEngine habilitado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar DataEngine: {e}")
        
        # ContextEngine integration (Módulo 2)
        self.context_engine = None
        self.context_engine_enabled = config.get("context_engine_enabled", False)
        if CONTEXT_ENGINE_AVAILABLE and self.context_engine_enabled:
            context_engine_config = config.get("context_engine_config", {})
            try:
                self.context_engine = ContextEngine(context_engine_config)
                logger.info(f"{self.__class__.__name__}: ContextEngine habilitado")
            except Exception as e:
                logger.warning(f"No se pudo inicializar ContextEngine: {e}")
        
        # Feature extraction
        self.feature_extractors = []  # Lista de extractores de features
        
        # Callbacks para aprendizaje continuo
        self.on_signal_generated_callbacks: List[Callable] = []
        self.on_trade_executed_callbacks: List[Callable] = []
        self.on_market_data_callbacks: List[Callable] = []
        
        # Métricas y tracking
        self.metrics: Dict[str, Any] = {
            "signals_generated": 0,
            "trades_executed": 0,
            "learning_adjustments_applied": 0,
            "context_analysis_calls": 0,
            "data_engine_calls": 0,
            "last_update": None
        }
        
        # Ensemble support (si este engine es parte de un ensemble)
        self.is_ensemble_component = False
        self.ensemble_weight = Decimal("1.0")  # Peso en ensemble (default: único engine)
        
        logger.info(f"{self.__class__.__name__} initialized: {self.name}")
    
    # ===== Métodos abstractos adicionales =====
    
    @abstractmethod
    def extract_features(self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None) -> Dict[str, Any]:
        """
        Extraer features estandarizados para Learning Engine.
        
        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional de datos de mercado
            
        Returns:
            Diccionario con features estandarizados
        """
        pass
    
    @abstractmethod
    def get_strategy_type(self) -> str:
        """
        Obtener tipo de estrategia (momentum, mean_reversion, pairs_trading, etc.).
        
        Returns:
            String identificando el tipo de estrategia
        """
        pass
    
    # ===== Métodos concretos para Learning Engine integration =====
    
    def set_learning_engine(self, learning_engine: Any) -> None:
        """
        Establecer Learning Engine para este strategy engine.
        
        Args:
            learning_engine: Instancia de un Learning Engine (BaseLearningEngine)
        """
        self.learning_engine = learning_engine
        self.learning_enabled = learning_engine is not None
        logger.info(f"{self.__class__.__name__}: Learning Engine {'habilitado' if self.learning_enabled else 'deshabilitado'}")
    
    def get_learning_prediction(self, market_data: Quote, historical_data: Optional[Sequence[Quote]] = None) -> Optional[Dict[str, Any]]:
        """
        Obtener predicción del Learning Engine (si está disponible).
        
        Args:
            market_data: Datos de mercado actuales
            historical_data: Historial opcional
            
        Returns:
            Diccionario con predicción o None si no hay Learning Engine
        """
        if not self.learning_enabled or self.learning_engine is None:
            return None
        
        try:
            features = self.extract_features(market_data, historical_data)
            prediction = self.learning_engine.predict(features)
            
            # Track learning usage
            self.metrics["learning_adjustments_applied"] += 1
            
            return prediction
        except Exception as e:
            logger.warning(f"{self.__class__.__name__}: Error obteniendo predicción de Learning Engine: {e}")
            return None
    
    def apply_learning_adjustments(self, prediction: Dict[str, Any], signal: Signal) -> Signal:
        """
        Aplicar ajustes sugeridos por Learning Engine a una señal.
        
        Args:
            prediction: Predicción del Learning Engine
            signal: Señal a ajustar
            
        Returns:
            Señal ajustada (puede ser la misma o una nueva)
        """
        if not prediction:
            return signal
        
        # Ajustar confidence basado en predicción
        if "confidence" in prediction:
            signal.confidence = min(100.0, max(0.0, float(prediction["confidence"]) * 100))
        
        # Ajustar strength si está disponible
        if "recommended_action" in prediction:
            # Puede sugerir modificar la señal o su fuerza
            pass
        
        return signal
    
    # ===== Callbacks para aprendizaje continuo =====
    
    def register_signal_callback(self, callback: Callable[[Signal, Quote], None]) -> None:
        """
        Registrar callback para cuando se genera una señal.
        
        Args:
            callback: Función que recibe (signal, market_data)
        """
        self.on_signal_generated_callbacks.append(callback)
    
    def register_trade_callback(self, callback: Callable[[Signal, Any], None]) -> None:
        """
        Registrar callback para cuando se ejecuta un trade.
        
        Args:
            callback: Función que recibe (signal, execution_result)
        """
        self.on_trade_executed_callbacks.append(callback)
    
    def register_market_data_callback(self, callback: Callable[[Quote], None]) -> None:
        """
        Registrar callback para cuando se reciben datos de mercado.
        
        Args:
            callback: Función que recibe (market_data)
        """
        self.on_market_data_callbacks.append(callback)
    
    def _trigger_signal_callbacks(self, signal: Signal, market_data: Quote) -> None:
        """Ejecutar callbacks de señal generada."""
        for callback in self.on_signal_generated_callbacks:
            try:
                callback(signal, market_data)
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}: Error en callback de señal: {e}")
    
    def _trigger_trade_callbacks(self, signal: Signal, execution_result: Any) -> None:
        """Ejecutar callbacks de trade ejecutado."""
        for callback in self.on_trade_executed_callbacks:
            try:
                callback(signal, execution_result)
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}: Error en callback de trade: {e}")
    
    def _trigger_market_data_callbacks(self, market_data: Quote) -> None:
        """Ejecutar callbacks de datos de mercado."""
        for callback in self.on_market_data_callbacks:
            try:
                callback(market_data)
            except Exception as e:
                logger.warning(f"{self.__class__.__name__}: Error en callback de market data: {e}")
    
    # ===== Métodos para composición (ensembles) =====
    
    def set_ensemble_weight(self, weight: Decimal) -> None:
        """
        Establecer peso de este engine en un ensemble.
        
        Args:
            weight: Peso del engine (normalmente entre 0 y 1) - puede ser Decimal o float
        """
        # Convertir a Decimal si es necesario
        if not isinstance(weight, Decimal):
            weight = Decimal(str(weight))
        self.ensemble_weight = weight
        self.is_ensemble_component = weight < Decimal("1.0")
        logger.debug(f"{self.__class__.__name__}: Peso en ensemble = {weight}")
    
    def get_ensemble_weight(self) -> Decimal:
        """Obtener peso actual en ensemble."""
        return self.ensemble_weight
    
    def get_context_analysis(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """
        Obtener análisis de contexto de mercado usando ContextEngine.
        
        Args:
            prices: Lista de precios históricos
        
        Returns:
            Dict con análisis de contexto o None si ContextEngine no está disponible
        """
        if not self.context_engine or not self.context_engine_enabled:
            return None
        
        try:
            self.metrics["context_analysis_calls"] += 1
            return self.context_engine.get_current_regime(prices, method='ensemble')
        except Exception as e:
            logger.error(f"Error obteniendo contexto: {e}")
            return None
    
    def get_volatility_regime(self, prices: List[float]) -> Optional[Dict[str, Any]]:
        """
        Obtener régimen de volatilidad usando ContextEngine.
        
        Args:
            prices: Lista de precios históricos
        
        Returns:
            Dict con régimen de volatilidad o None
        """
        if not self.context_engine or not self.context_engine_enabled:
            return None
        
        try:
            return self.context_engine.get_volatility_regime(prices)
        except Exception as e:
            logger.error(f"Error obteniendo régimen de volatilidad: {e}")
            return None
    
    def get_market_data_from_engine(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        source: Optional[str] = None
    ) -> List[Quote]:
        """
        Obtener datos de mercado usando DataEngine.
        
        Args:
            symbol: Símbolo del instrumento
            start_date: Fecha de inicio
            end_date: Fecha de fin
            source: Fuente específica (opcional)
        
        Returns:
            Lista de Quotes o lista vacía si DataEngine no está disponible
        """
        if not self.data_engine or not self.data_engine_enabled:
            return []
        
        try:
            import asyncio
            
            # Obtener datos OHLCV del DataEngine
            ohlcv_data = asyncio.run(
                self.data_engine.get_ohlcv(symbol, start_date, end_date, source=source)
            )
            
            self.metrics["data_engine_calls"] += 1
            
            # Convertir a Quotes
            quotes = []
            for data in ohlcv_data:
                quote = Quote(
                    symbol=symbol,
                    timestamp=data.get('timestamp', datetime.now()),
                    bid=data.get('close', Decimal('0')),
                    ask=data.get('close', Decimal('0')),
                    last=data.get('close', Decimal('0')),
                    open=data.get('open', Decimal('0')),
                    high=data.get('high', Decimal('0')),
                    low=data.get('low', Decimal('0')),
                    close=data.get('close', Decimal('0')),
                    volume=data.get('volume', Decimal('0'))
                )
                quotes.append(quote)
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de DataEngine: {e}")
            return []
    
    def set_data_engine(self, data_engine: Any) -> None:
        """
        Configurar DataEngine externo.
        
        Args:
            data_engine: Instancia de DataEngine
        """
        self.data_engine = data_engine
        self.data_engine_enabled = True
        logger.info(f"{self.__class__.__name__}: DataEngine configurado externamente")
    
    def set_context_engine(self, context_engine: Any) -> None:
        """
        Configurar ContextEngine externo.
        
        Args:
            context_engine: Instancia de ContextEngine
        """
        self.context_engine = context_engine
        self.context_engine_enabled = True
        logger.info(f"{self.__class__.__name__}: ContextEngine configurado externamente")
    
    # ===== Métodos mejorados de generate_signals =====
    
    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generar señales (método wrapper que añade callbacks y learning).
        
        Este método llama a _generate_signals_impl() (implementación específica)
        y añade funcionalidades de callbacks y learning integration.
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            Lista de señales generadas
        """
        # Trigger market data callbacks
        self._trigger_market_data_callbacks(market_data)
        
        # Generar señales (implementación específica)
        signals = self._generate_signals_impl(market_data)
        
        # Aplicar ajustes de Learning Engine si está disponible
        if self.learning_enabled:
            adjusted_signals = []
            for signal in signals:
                prediction = self.get_learning_prediction(market_data)
                if prediction:
                    signal = self.apply_learning_adjustments(prediction, signal)
                adjusted_signals.append(signal)
            signals = adjusted_signals
        
        # Trigger signal callbacks
        for signal in signals:
            self._trigger_signal_callbacks(signal, market_data)
            self.metrics["signals_generated"] += 1
        
        self.metrics["last_update"] = datetime.utcnow()
        return signals
    
    @abstractmethod
    def _generate_signals_impl(self, market_data: Quote) -> List[Signal]:
        """
        Implementación específica de generación de señales.
        
        Este método debe ser implementado por cada strategy engine.
        
        Args:
            market_data: Datos de mercado actuales
            
        Returns:
            Lista de señales generadas
        """
        pass
    
    # ===== Métricas y estado =====
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtener métricas del engine.
        
        Returns:
            Diccionario con métricas actuales
        """
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Resetear métricas del engine."""
        self.metrics = {
            "signals_generated": 0,
            "trades_executed": 0,
            "learning_adjustments_applied": 0,
            "last_update": None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtener estado completo del engine.
        
        Returns:
            Diccionario con estado del engine
        """
        status = {
            "name": self.name,
            "type": self.get_strategy_type(),
            "version": self.version,
            "is_active": self.is_active,
            "learning_enabled": self.learning_enabled,
            "data_engine_enabled": self.data_engine_enabled,
            "context_engine_enabled": self.context_engine_enabled,
            "is_ensemble_component": self.is_ensemble_component,
            "ensemble_weight": float(self.ensemble_weight),
            "metrics": self.get_metrics()
        }
        
        # Agregar estado de engines si están disponibles
        if self.data_engine:
            try:
                status["data_engine_status"] = self.data_engine.get_status()
            except:
                pass
        
        if self.context_engine:
            try:
                status["context_engine_status"] = "available"
            except:
                pass
        
        return status
    
    def __repr__(self) -> str:
        """Representación detallada del engine."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"type='{self.get_strategy_type()}', "
            f"version='{self.version}', "
            f"active={self.is_active}, "
            f"learning={'enabled' if self.learning_enabled else 'disabled'})"
        )

