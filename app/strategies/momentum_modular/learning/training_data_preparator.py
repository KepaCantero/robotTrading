"""
TrainingDataPreparator - Prepara datos de entrenamiento completos para learning engines.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
try:
    import pandas_ta_classic as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    try:
        import pandas_ta as ta
        PANDAS_TA_AVAILABLE = True
    except ImportError:
        PANDAS_TA_AVAILABLE = False
        logger.warning("pandas-ta-classic o pandas-ta no disponible. Funcionalidad limitada.")

from app.models.market_data import Quote
from app.strategies.momentum_modular.learning.feature_extractor import FeatureExtractor
from app.backtesting.models import Trade, TradeStatus

logger = logging.getLogger(__name__)


class TrainingDataPreparator:
    """
    Prepara datos de entrenamiento completos para todos los tipos de learning engines.
    """
    
    def __init__(self, feature_extractor: Optional[FeatureExtractor] = None):
        """
        Inicializar preparador de datos.
        
        Args:
            feature_extractor: FeatureExtractor instance (crea uno nuevo si None)
        """
        self.feature_extractor = feature_extractor or FeatureExtractor()
    
    def prepare_supervised_training_data(
        self,
        quotes: List[Quote],
        trades: List[Trade],
        min_sequence_length: int = 60
    ) -> Dict[str, Any]:
        """
        Preparar datos de entrenamiento para Supervised Learning.
        
        Args:
            quotes: Lista deม datos históricos de mercado
            trades: Lista de trades históricos para generar labels
            min_sequence_length: Longitud mínima de secuencia para calcular indicadores
        
        Returns:
            {
                'features': pd.DataFrame,  # Features X
                'labels': pd.Series         # Labels y (1=success, 0=failure)
            }
        """
        if len(quotes) < min_sequence_length:
            logger.warning(f"Insufficient data: {len(quotes)} quotes < {min_sequence_length} minimum")
            return {'features': pd.DataFrame(), 'labels': pd.Series([], dtype=int)}
        
        # Convertir quotes a DataFrame para cálculo de indicadores
        df = self._quotes_to_dataframe(quotes)
        
        # Calcular todos los indicadores técnicos
        indicators_df = self._calculate_technical_indicators(df)
        
        # Generar features y labels para cada punto de tiempo
        features_list = []
        labels_list = []
        
        # Crear mapa de trades por timestamp para lookup rápido
        trades_by_timestamp = self._create_trades_timestamp_map(trades, df)
        
        for i in range(min_sequence_length, len(indicators_df)):
            quote = quotes[i]
            timestamp = quote.timestamp if hasattr(quote, 'timestamp') else df.index[i]
            
            # Obtener indicadores actuales
            indicators = self._extract_indicators_from_row(indicators_df.iloc[i])
            
            # Obtener contexto de mercado (simplificado - usar datos históricos hasta este punto)
            market_context = self._estimate_market_context(indicators_df.iloc[:i+1])
            
            # Obtener resultados de filtros (simulados para entrenamiento)
            # En producción, estos vendrían de evaluaciones reales de filtros
            filter_results = self._simulate_filter_results(indicators, market_context)
            
            # Extraer features completas
            features = self.feature_extractor.extract_complete_features(
                indicators=indicators,
                filter_results=filter_results,
                market_context=market_context,
                metadata={
                    'timestamp': timestamp,
                    'symbol': quote.symbol,
                    'recent_trades': self._get_recent_trades_before_timestamp(trades, timestamp),
                    'recent_win_rate': self._calculate_recent_win_rate(trades, timestamp)
                }
            )
            
            features_list.append(features['feature_vector'])
            
            # Generar label: ¿fue este punto un buen momento para comprar?
            # Label = 1 si hay un trade exitoso en los próximos N días después de este punto
            label = self._generate_label_for_timestamp(
                timestamp, trades_by_timestamp, df, i, lookahead_days=10
            )
            labels_list.append(label)
        
        if not features_list:
            logger.warning("No features generated")
            return {'features': pd.DataFrame(), 'labels': pd.Series([], dtype=int)}
        
        # Crear DataFrame de features
        feature_names = features_list[0]['feature_names'] if features_list else []
        X_df = pd.DataFrame([f['feature_vector'] for f in features_list], columns=feature_names)
        y_series = pd.Series(labels_list, dtype=int)
        
        logger.info(f"Prepared training data: {len(X_df)} samples, {len(feature_names)} features, "
                   f"{y_series.sum()} positive labels ({y_series.mean()*100:.1f}%)")
        
        return {
            'features': X_df,
            'labels': y_series
        }
    
    def prepare_deep_learning_training_data(
        self,
        quotes: List[Quote],
        trades: List[Trade],
        sequence_length: int = 60,
        min_sequence_length: int = 120
    ) -> Dict[str, Any]:
        """
        Preparar datos de entrenamiento para Deep Learning (LSTM/GRU/Transformers).
        
        Args:
            quotes: Lista de datos históricos
            trades: Lista de trades históricos
            sequence_length: Longitud de secuencia para LSTM
            min_sequence_length: Longitud mínima total requerida
        
        Returns:
            {
                'sequences': np.array shape (n_samples, sequence_length, n_features),
                'labels': np.array shape (n_samples,)
            }
        """
        if len(quotes) < min_sequence_length:
            logger.warning(f"Insufficient data: {len(quotes)} quotes < {min_sequence_length} minimum")
            return {'sequences': np.array([]), 'labels': np.array([])}
        
        df = self._quotes_to_dataframe(quotes)
        indicators_df = self._calculate_technical_indicators(df)
        trades_by_timestamp = self._create_trades_timestamp_map(trades, df)
        
        sequences = []
        labels = []
        
        # Construir secuencias deslizantes
        for i in range(min_sequence_length, len(indicators_df)):
            # Obtener ventana de datos históricos
            historical_window = indicators_df.iloc[i-sequence_length:i+1]
            
            # Construir secuencia de features históricas
            historical_data = []
            for j in range(i - sequence_length, i + 1):
                if j < 0:
                    continue
                
                quote = quotes[j] if j < len(quotes) else quotes[-1]
                indicators = self._extract_indicators_from_row(indicators_df.iloc[j])
                market_context = self._estimate_market_context(indicators_df.iloc[:j+1])
                filter_results = self._simulate_filter_results(indicators, market_context)
                
                historical_data.append({
                    'indicators': indicators,
                    'filter_results': filter_results,
                    'market_context': market_context,
                    'metadata': {
                        'timestamp': quote.timestamp if hasattr(quote, 'timestamp') else df.index[j],
                        'symbol': quote.symbol
                    }
                })
            
            if len(historical_data) < sequence_length:
                continue
            
            # Extraer secuencia de features
            sequence = self.feature_extractor.extract_sequence_features(
                historical_data,
                sequence_length=sequence_length
            )
            
            sequences.append(sequence)
            
            # Generar label
            timestamp = quotes[i].timestamp if hasattr(quotes[i], 'timestamp') else df.index[i]
            label = self._generate_label_for_timestamp(
                timestamp, trades_by_timestamp, df, i, lookahead_days=10
            )
            labels.append(label)
        
        if not sequences:
            logger.warning("No sequences generated")
            return {'sequences': np.array([]), 'labels': np.array([])}
        
        X_sequences = np.array(sequences, dtype=np.float32)
        y_labels = np.array(labels, dtype=int)
        
        logger.info(f"Prepared DL training data: {len(X_sequences)} sequences, "
                   f"shape {X_sequences.shape}, {y_labels.sum()} positive labels")
        
        return {
            'sequences': X_sequences,
            'labels': y_labels
        }
    
    def prepare_reinforcement_learning_data(
        self,
        quotes: List[Quote],
        initial_capital: Decimal = Decimal("100000")
    ) -> Dict[str, Any]:
        """
        Preparar datos de mercado para Reinforcement Learning.
        
        Args:
            quotes: Lista de datos históricos
            initial_capital: Capital inicial
        
        Returns:
            {
                'market_sequences': List[Dict],  # Secuencias de datos de mercado
                'initial_capital': float
            }
        """
        df = self._quotes_to_dataframe(quotes)
        indicators_df = self._calculate_technical_indicators(df)
        
        market_sequences = []
        
        for i in range(len(indicators_df)):
            quote = quotes[i] if i < len(quotes) else quotes[-1]
            indicators = self._extract_indicators_from_row(indicators_df.iloc[i])
            market_context = self._estimate_market_context(indicators_df.iloc[:i+1])
            
            market_sequences.append({
                'price': float(quote.bid) if hasattr(quote, 'bid') else float(quote.close) if hasattr(quote, 'close') else 0.0,
                'volume': float(getattr(quote, 'volume', 0)),
                'timestamp': quote.timestamp if hasattr(quote, 'timestamp') else df.index[i],
                'indicators': indicators,
                'market_context': market_context
            })
        
        logger.info(f"Prepared RL data: {len(market_sequences)} market data points")
        
        return {
            'market_sequences': market_sequences,
            'initial_capital': float(initial_capital)
        }
    
    def _quotes_to_dataframe(self, quotes: List[Quote]) -> pd.DataFrame:
        """Convertir quotes a DataFrame."""
        data = []
        for quote in quotes:
            timestamp = quote.timestamp if hasattr(quote, 'timestamp') else datetime.now()
            price = float(quote.bid) if hasattr(quote, 'bid') else float(quote.close) if hasattr(quote, 'close') else 0.0
            volume = float(getattr(quote, 'volume', 0))
            
            data.append({
                'timestamp': timestamp,
                'open': price,  # Simplificado: usar mismo precio
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular todos los indicadores técnicos necesarios."""
        indicators_df = df.copy()
        
        if not PANDAS_TA_AVAILABLE:
            logger.warning("pandas_ta no disponible, usando cálculos básicos sin indicadores avanzados")
            # Usar cálculos básicos simples
            indicators_df['rsi'] = 50.0
            indicators_df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
            indicators_df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
            indicators_df['momentum_roc'] = df['close'].pct_change(14) * 100
            indicators_df['atr'] = (df['high'] - df['low']).rolling(14).mean()
            indicators_df['stoch_rsi_k'] = 50.0
            indicators_df['stoch_rsi_d'] = 50.0
        else:
            # RSI
            indicators_df['rsi'] = ta.rsi(df['close'], length=14)
            
            # EMAs
            indicators_df['ema_fast'] = ta.ema(df['close'], length=12)
            indicators_df['ema_slow'] = ta.ema(df['close'], length=26)
            
            # Momentum / ROC
            indicators_df['momentum_roc'] = ta.roc(df['close'], length=14)
            
            # ATR
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            indicators_df['atr'] = atr
            
            # StochRSI
            stoch_rsi = ta.stochrsi(df['close'], length=14)
            if isinstance(stoch_rsi, pd.DataFrame):
                indicators_df['stoch_rsi_k'] = stoch_rsi.iloc[:, 0] if len(stoch_rsi.columns) > 0 else 50.0
                indicators_df['stoch_rsi_d'] = stoch_rsi.iloc[:, 1] if len(stoch_rsi.columns) > 1 else 50.0
            else:
                indicators_df['stoch_rsi_k'] = stoch_rsi if stoch_rsi is not None else 50.0
                indicators_df['stoch_rsi_d'] = 50.0
        
        # Volume ratios (común para ambos casos)
        indicators_df['avg_volume'] = df['volume'].rolling(window=20).mean()
        indicators_df['volume_ratio'] = df['volume'] / indicators_df['avg_volume'].replace(0, 1)
        
        # Relative ATR y percentile (común para ambos casos)
        if PANDAS_TA_AVAILABLE:
            indicators_df['relative_atr'] = (indicators_df['atr'] / df['close'] * 100).fillna(0)
        else:
            indicators_df['relative_atr'] = (indicators_df['atr'] / df['close'] * 100).fillna(0)
        
        indicators_df['atr_percentile'] = indicators_df['atr'].rolling(window=30).apply(
            lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100 if len(x) > 0 else 50, raw=False
        ).fillna(50)
        
        # Precio actual
        indicators_df['price'] = df['close']
        
        return indicators_df.fillna(method='ffill').fillna(0)
    
    def _extract_indicators_from_row(self, row: pd.Series) -> Dict[str, float]:
        """Extraer indicadores de una fila del DataFrame."""
        return {
            'rsi': float(row.get('rsi', 50.0)),
            'ema_fast': float(row.get('ema_fast', 0.0)),
            'ema_slow': float(row.get('ema_slow', 0.0)),
            'momentum_roc': float(row.get('momentum_roc', 0.0)),
            'volume_ratio': float(row.get('volume_ratio', 1.0)),
            'volume': float(row.get('volume', 0.0)),
            'avg_volume': float(row.get('avg_volume', 0.0)),
            'atr': float(row.get('atr', 0.0)),
            'relative_atr': float(row.get('relative_atr', 0.0)),
            'atr_percentile': float(row.get('atr_percentile', 50.0)),
            'stoch_rsi_k': float(row.get('stoch_rsi_k', 50.0)),
            'stoch_rsi_d': float(row.get('stoch_rsi_d', 50.0)),
            'price': float(row.get('price', 0.0))
        }
    
    def _estimate_market_context(self, historical_df: pd.DataFrame) -> Dict[str, Any]:
        """Estimar contexto de mercado desde datos históricos."""
        if len(historical_df) < 26:
            return {
                'type': 'unknown',
                'confidence': 0.0,
                'trend_strength': 0.0,
                'volatility_regime': 'normal',
                'volatility_percentile': 50.0,
                'in_range': False
            }
        
        # Detectar tendencia usando EMAs
        ema_fast = historical_df['ema_fast'].iloc[-1] if 'ema_fast' in historical_df.columns else 0
        ema_slow = historical_df['ema_slow'].iloc[-1] if 'ema_slow' in historical_df.columns else 0
        price = historical_df['close'].iloc[-1]
        
        trend_strength = abs(ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0.0
        
        if ema_fast > ema_slow and price > ema_fast:
            market_type = 'trend_up'
        elif ema_fast < ema_slow and price < ema_fast:
            market_type = 'trend_down'
        else:
            market_type = 'range'
        
        # Volatilidad
        atr_percentile = historical_df['atr_percentile'].iloc[-1] if 'atr_percentile' in historical_df.columns else 50.0
        
        if atr_percentile >= 75:
            vol_regime = 'high'
        elif atr_percentile <= 25:
            vol_regime = 'low'
        else:
            vol_regime = 'normal'
        
        return {
            'type': market_type,
            'confidence': min(1.0, trend_strength * 10),
            'trend_strength': trend_strength,
            'volatility_regime': vol_regime,
            'volatility_percentile': atr_percentile,
            'in_range': market_type == 'range'
        }
    
    def _simulate_filter_results(self, indicators: Dict, market_context: Dict) -> Dict[str, Dict]:
        """Simular resultados de filtros para entrenamiento (simplificado)."""
        # En producción, esto vendría de evaluaciones reales de filtros
        # Por ahora, simulamos resultados basados en indicadores
        
        filter_results = {}
        
        # EMA Filter
        ema_fast = indicators.get('ema_fast', 0)
        ema_slow = indicators.get('ema_slow', 0)
        price = indicators.get('price', 0)
        filter_results['ema_filter'] = {
            'passed': price > ema_fast > ema_slow if price > 0 else False,
            'confidence': abs(ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0.0
        }
        
        # RSI Filter
        rsi = indicators.get('rsi', 50)
        filter_results['rsi_filter'] = {
            'passed': 40 < rsi < 70,  # Zona de momentum
            'confidence': 1.0 - abs(rsi - 55) / 55
        }
        
        # Momentum Filter
        momentum = indicators.get('momentum_roc', 0)
        filter_results['momentum_filter'] = {
            'passed': momentum > 0.01,  # Momentum positivo
            'confidence': min(1.0, momentum * 50) if momentum > 0 else 0.0
        }
        
        # Volume Filter
        volume_ratio = indicators.get('volume_ratio', 1.0)
        filter_results['volume_filter'] = {
            'passed': volume_ratio > 1.1,
            'confidence': min(1.0, (volume_ratio - 1.0) / 1.0)
        }
        
        # ATR Filter
        atr_percentile = indicators.get('atr_percentile', 50)
        filter_results['atr_filter'] = {
            'passed': atr_percentile > 60,  # Alta volatilidad
            'confidence': (atr_percentile - 50) / 50
        }
        
        # StochRSI Filter
        stoch_k = indicators.get('stoch_rsi_k', 50)
        filter_results['stoch_rsi_filter'] = {
            'passed': 15 < stoch_k < 85,
            'confidence': 1.0 - abs(stoch_k - 50) / 50
        }
        
        return filter_results
    
    def _create_trades_timestamp_map(self, trades: List[Trade], df: pd.DataFrame) -> Dict[datetime, List[Trade]]:
        """Crear mapa de trades por timestamp."""
        trades_map = {}
        
        for trade in trades:
            if trade.entry_time:
                timestamp = trade.entry_time
                # Redondear a día más cercano para matching
                day = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                if day not in trades_map:
                    trades_map[day] = []
                trades_map[day].append(trade)
        
        return trades_map
    
    def _generate_label_for_timestamp(
        self,
        timestamp: datetime,
        trades_map: Dict[datetime, List[Trade]],
        df: pd.DataFrame,
        current_idx: int,
        lookahead_days: int = 10
    ) -> int:
        """
        Generar label para un timestamp.
        Label = 1 si hubo un trade exitoso en los próximos N días.
        """
        # Buscar trades en ventana lookahead
        end_timestamp = timestamp + timedelta(days=lookahead_days)
        
        # Buscar trades en esta ventana
        relevant_trades = []
        for trade_date, trades in trades_map.items():
            if timestamp <= trade_date <= end_timestamp:
                relevant_trades.extend(trades)
        
        if not relevant_trades:
            return 0  # No hubo trades
        
        # Verificar si alguno fue exitoso
        for trade in relevant_trades:
            if trade.status == TradeStatus.CLOSED and trade.pnl and trade.pnl > 0:
                # Trade exitoso - label positivo
                return 1
        
        # Hubo trades pero no exitosos
        return 0
    
    def _get_recent_trades_before_timestamp(
        self,
        trades: List[Trade],
        timestamp: datetime,
        max_trades: int = 5
    ) -> List[Dict[str, Any]]:
        """Obtener trades recientes antes de un timestamp."""
        recent_trades = []
        
        for trade in reversed(trades):
            if trade.entry_time and trade.entry_time < timestamp:
                if trade.status == TradeStatus.CLOSED and trade.pnl is not None:
                    recent_trades.append({
                        'pnl': float(trade.pnl),
                        'entry_time': trade.entry_time,
                        'exit_time': trade.exit_time
                    })
                    
                    if len(recent_trades) >= max_trades:
                        break
        
        return list(reversed(recent_trades))  # Orden cronológico
    
    def _calculate_recent_win_rate(
        self,
        trades: List[Trade],
        timestamp: datetime,
        window_days: int = 30
    ) -> float:
        """Calcular win rate reciente antes de un timestamp."""
        start_timestamp = timestamp - timedelta(days=window_days)
        
        relevant_trades = [
            t for t in trades
            if t.entry_time and start_timestamp <= t.entry_time < timestamp
            and t.status == TradeStatus.CLOSED and t.pnl is not None
        ]
        
        if not relevant_trades:
            return 0.5  # Default
        
        winning_trades = [t for t in relevant_trades if t.pnl > 0]
        return len(winning_trades) / len(relevant_trades)

