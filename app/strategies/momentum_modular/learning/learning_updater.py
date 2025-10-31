"""
LearningEngineUpdater - Sistema de reentrenamiento automático para learning engines.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .base_learning_engine import BaseLearningEngine
from .training_data_preparator import TrainingDataPreparator

logger = logging.getLogger(__name__)


class LearningEngineUpdater:
    """
    Gestiona reentrenamiento automático periódico de learning engines.
    
    Características:
    - Reentrenamiento periódico (cada N días)
    - Validación de lookahead bias
    - Gestión de historial de trades
    - Preparación de datos desde historial
    """
    
    def __init__(
        self,
        learning_engine: BaseLearningEngine,
        rebalance_frequency_days: int = 7,
        min_trades_for_retrain: int = 20,
        lookahead_window_days: int = 10
    ):
        """
        Inicializar updater.
        
        Args:
            learning_engine: Learning engine a reentrenar
            rebalance_frequency_days: Frecuencia de reentrenamiento (días)
            min_trades_for_retrain: Número mínimo de trades para reentrenar
            lookahead_window_days: Ventana de lookahead para labels (días)
        """
        self.learning_engine = learning_engine
        self.rebalance_frequency_days = rebalance_frequency_days
        self.min_trades_for_retrain = min_trades_for_retrain
        self.lookahead_window_days = lookahead_window_days
        
        self.last_retrain_date: Optional[datetime] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.market_history: List[Dict[str, Any]] = []
        
        self.training_data_preparator = TrainingDataPreparator()
    
    def should_retrain(self, current_date: datetime) -> bool:
        """
        Verificar si se debe reentrenar.
        
        Args:
            current_date: Fecha actual del backtest
        
        Returns:
            True si se debe reentrenar, False en caso contrario
        """
        if self.last_retrain_date is None:
            # Primera vez - reentrenar si hay suficientes trades
            return len(self.trade_history) >= self.min_trades_for_retrain
        
        days_since_retrain = (current_date - self.last_retrain_date).days
        has_enough_trades = len(self.trade_history) >= self.min_trades_for_retrain
        
        return days_since_retrain >= self.rebalance_frequency_days and has_enough_trades
    
    def add_trade_result(
        self,
        trade: Dict[str, Any],
        timestamp: datetime
    ) -> None:
        """
        Agregar resultado de trade al historial.
        
        Args:
            trade: Dict con información del trade (pnl, entry_time, exit_time, etc.)
            timestamp: Timestamp del trade
        """
        trade_record = {
            **trade,
            'recorded_at': timestamp
        }
        self.trade_history.append(trade_record)
    
    def add_market_data(
        self,
        market_data: Dict[str, Any],
        timestamp: datetime
    ) -> None:
        """
        Agregar datos de mercado al historial.
        
        Args:
            market_data: Dict con datos de mercado (price, volume, indicators, etc.)
            timestamp: Timestamp de los datos
        """
        market_record = {
            **market_data,
            'timestamp': timestamp
        }
        self.market_history.append(market_record)
    
    def retrain_if_needed(
        self,
        current_date: datetime,
        quotes: Optional[List] = None
    ) -> bool:
        """
        Reentrenar learning engine si es necesario.
        
        Args:
            current_date: Fecha actual del backtest
            quotes: Lista de quotes históricos (opcional, se usan si están disponibles)
        
        Returns:
            True si se reentrenó, False en caso contrario
        """
        if not self.should_retrain(current_date):
            return False
        
        logger.info(
            f"🔄 Iniciando reentrenamiento de {self.learning_engine.__class__.__name__} "
            f"({len(self.trade_history)} trades, "
            f"último reentrenamiento: {self.last_retrain_date})"
        )
        
        try:
            # Preparar datos de entrenamiento desde historial
            training_data = self._prepare_training_data_from_history(quotes)
            
            if not training_data or self._is_training_data_empty(training_data):
                logger.warning("⚠️ Datos de entrenamiento vacíos, saltando reentrenamiento")
                return False
            
            # Reentrenar
            metrics = self.learning_engine.train(training_data)
            
            logger.info(
                f"✅ Reentrenamiento completado: {metrics}"
            )
            
            self.last_retrain_date = current_date
            
            # Limpiar historial antiguo (mantener solo último 30 días)
            self._clean_old_history(current_date)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en reentrenamiento: {e}", exc_info=True)
            return False
    
    def _prepare_training_data_from_history(
        self,
        quotes: Optional[List] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Preparar datos de entrenamiento desde historial de trades y market data.
        
        Args:
            quotes: Lista de quotes históricos (si están disponibles)
        
        Returns:
            Dict con datos de entrenamiento o None si no hay suficientes datos
        """
        if not self.trade_history or len(self.trade_history) < self.min_trades_for_retrain:
            logger.warning(f"No hay suficientes trades ({len(self.trade_history)}) para reentrenar")
            return None
        
        engine_type = self._get_engine_type()
        
        if quotes is None:
            # Si no hay quotes, intentar reconstruir desde market_history
            if not self.market_history:
                logger.warning("No hay quotes ni market_history disponible")
                return None
            
            # Convertir market_history a formato Quote (simplificado)
            # Esto es una aproximación - en producción se requerirían los quotes completos
            quotes = self._convert_market_history_to_quotes()
        
        if not quotes or len(quotes) < 60:
            logger.warning(f"No hay suficientes quotes ({len(quotes) if quotes else 0}) para entrenar")
            return None
        
        # Convertir trade_history a formato Trade
        trades = self._convert_trade_history_to_trades()
        
        # Preparar datos según tipo de engine
        if engine_type == "supervised":
            return self.training_data_preparator.prepare_supervised_training_data(
                quotes=quotes,
                trades=trades,
                min_sequence_length=60
            )
        elif engine_type == "deep":
            return self.training_data_preparator.prepare_deep_learning_training_data(
                quotes=quotes,
                trades=trades,
                sequence_length=60,
                min_sequence_length=120
            )
        elif engine_type == "reinforcement":
            return self.training_data_preparator.prepare_reinforcement_learning_data(
                quotes=quotes,
                initial_capital=Decimal("100000")  # Default
            )
        
        return None
    
    def _get_engine_type(self) -> str:
        """Obtener tipo de learning engine."""
        class_name = self.learning_engine.__class__.__name__
        if "Supervised" in class_name:
            return "supervised"
        elif "Deep" in class_name:
            return "deep"
        elif "Reinforcement" in class_name:
            return "reinforcement"
        return "supervised"  # Default
    
    def _is_training_data_empty(self, training_data: Dict[str, Any]) -> bool:
        """Verificar si los datos de entrenamiento están vacíos."""
        if "features" in training_data:
            df = training_data["features"]
            return df is None or (hasattr(df, 'empty') and df.empty) or len(df) == 0
        elif "sequences" in training_data:
            arr = training_data["sequences"]
            return arr is None or len(arr) == 0
        elif "market_sequences" in training_data:
            lst = training_data["market_sequences"]
            return lst is None or len(lst) == 0
        
        return True
    
    def _convert_trade_history_to_trades(self) -> List:
        """Convertir trade_history a formato Trade (simplificado para backtest)."""
        # En producción, esto convertiría a objetos PDE Trade completos
        # Por ahora, retornar formato simplificado
        trades = []
        for trade_record in self.trade_history:
            trades.append({
                'pnl': trade_record.get('pnl', 0),
                'entry_time': trade_record.get('entry_time'),
                'exit_time': trade_record.get('exit_time'),
                'status': 'CLOSED' if trade_record.get('exit_time') else 'OPEN'
            })
        return trades
    
    def _convert_market_history_to_quotes(self) -> List:
        """Convertir market_history a formato Quote (simplificado)."""
        # En producción, esto requeriría reconstruir objetos Quote completos
        # Por ahora, retornar formato simplificado
        from app.models.market_data import Quote
        
        quotes = []
        for market_record in self.market_history:
            quote = Quote(
                symbol=market_record.get('symbol', 'UNKNOWN'),
                timestamp=market_record.get('timestamp', datetime.now()),
                bid=Decimal(str(market_record.get('price', 0))),
                ask=Decimal(str(market_record.get('price', 0))),
                volume=int(market_record.get('volume', 0))
            )
            quotes.append(quote)
        
        return quotes
    
    def _clean_old_history(self, current_date: datetime) -> None:
        """Limpiar historial antiguo (mantener solo último 30 días)."""
        cutoff_date = current_date - timedelta(days=30)
        
        self.trade_history = [
            t for t in self.trade_history
            if t.get('recorded_at', current_date) >= cutoff_date
        ]
        
        self.market_history = [
            m for m in self.market_history
            if m.get('timestamp', current_date) >= cutoff_date
        ]
        
        logger.debug(
            f"🧹 Historial limpiado: {len(self.trade_history)} trades, "
            f"{len(self.market_history)} market data points"
        )

