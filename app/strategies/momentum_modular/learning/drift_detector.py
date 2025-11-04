"""
DriftDetector - Sistema de detección de concept drift y sobreajuste.

Detecta:
1. Concept drift: Cambios en la distribución de datos (KS test, MMD)
2. Overfitting: Gap entre train/val, learning curves
3. Auto-retraining triggers: Decide cuándo reentrenar modelos
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from collections import deque
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Importaciones opcionales para tests estadísticos
try:
    from scipy import stats
    from scipy.stats import ks_2samp
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy no disponible. KS test no funcionará.")

try:
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    SKLEARN_METRICS_AVAILABLE = True
except ImportError:
    SKLEARN_METRICS_AVAILABLE = False
    logger.warning("sklearn no disponible. Métricas de overfitting limitadas.")


class ConceptDriftDetector:
    """
    Detecta concept drift usando tests estadísticos.
    
    Tests soportados:
    - Kolmogorov-Smirnov (KS) test: Compara distribuciones
    - Maximum Mean Discrepancy (MMD): Compara distribuciones en RKHS
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar detector de concept drift.
        
        Args:
            config: Configuración del detector
        """
        config = config or {}
        self.window_size = config.get("window_size", 100)  # Tamaño de ventana de referencia
        self.drift_threshold_ks = config.get("drift_threshold_ks", 0.05)  # p-value threshold para KS
        self.drift_threshold_mmd = config.get("drift_threshold_mmd", 0.1)  # Threshold para MMD
        self.use_ks_test = config.get("use_ks_test", True)
        self.use_mmd = config.get("use_mmd", False)
        
        # Histórico de datos de referencia
        self.reference_data: deque = deque(maxlen=self.window_size)
        self.reference_timestamp: Optional[datetime] = None
        
        # Histórico de detecciones
        self.drift_history: List[Dict[str, Any]] = []
    
    def update_reference(self, data: np.ndarray, timestamp: Optional[datetime] = None) -> None:
        """
        Actualizar datos de referencia.
        
        Args:
            data: Array de features o predicciones
            timestamp: Timestamp opcional
        """
        if data.ndim == 1:
            # Si es 1D, añadir como una muestra
            self.reference_data.append(data)
        else:
            # Si es 2D, añadir todas las muestras
            for sample in data:
                self.reference_data.append(sample)
        
        if timestamp:
            self.reference_timestamp = timestamp
    
    def detect_drift(self, current_data: np.ndarray, timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Detectar concept drift en datos actuales vs referencia.
        
        Args:
            current_data: Datos actuales a comparar
            timestamp: Timestamp opcional
        
        Returns:
            Dict con resultados de detección:
            {
                'drift_detected': bool,
                'ks_statistic': float,
                'ks_pvalue': float,
                'mmd_statistic': float,
                'drift_score': float,  # 0-1, mayor = más drift
                'recommendation': str  # 'retrain', 'monitor', 'ok'
            }
        """
        if len(self.reference_data) < 10:
            return {
                'drift_detected': False,
                'reason': 'insufficient_reference_data',
                'recommendation': 'collect_more_data'
            }
        
        if len(current_data) < 10:
            return {
                'drift_detected': False,
                'reason': 'insufficient_current_data',
                'recommendation': 'collect_more_data'
            }
        
        # Convertir referencia a numpy
        reference_array = np.array(list(self.reference_data))
        
        # Aplanar si es necesario para comparación
        if reference_array.ndim > 1:
            reference_flat = reference_array.flatten()
        else:
            reference_flat = reference_array
        
        if current_data.ndim > 1:
            current_flat = current_data.flatten()
        else:
            current_flat = current_data
        
        results = {
            'drift_detected': False,
            'ks_statistic': None,
            'ks_pvalue': None,
            'mmd_statistic': None,
            'drift_score': 0.0,
            'recommendation': 'ok'
        }
        
        # KS Test
        if self.use_ks_test and SCIPY_AVAILABLE:
            try:
                ks_stat, ks_pvalue = ks_2samp(reference_flat, current_flat)
                results['ks_statistic'] = float(ks_stat)
                results['ks_pvalue'] = float(ks_pvalue)
                
                # Drift detectado si p-value < threshold
                if ks_pvalue < self.drift_threshold_ks:
                    results['drift_detected'] = True
                    results['drift_score'] = 1.0 - ks_pvalue  # Invertir: p-value bajo = más drift
            except Exception as e:
                logger.warning(f"Error ejecutando KS test: {e}")
        
        # MMD (Maximum Mean Discrepancy)
        if self.use_mmd:
            try:
                mmd_stat = self._compute_mmd(reference_array, current_data)
                results['mmd_statistic'] = float(mmd_stat)
                
                if mmd_stat > self.drift_threshold_mmd:
                    results['drift_detected'] = True
                    # Normalizar MMD a 0-1
                    results['drift_score'] = min(1.0, mmd_stat / (self.drift_threshold_mmd * 2))
            except Exception as e:
                logger.warning(f"Error ejecutando MMD: {e}")
        
        # Generar recomendación
        if results['drift_detected']:
            if results['drift_score'] > 0.7:
                results['recommendation'] = 'retrain'
            else:
                results['recommendation'] = 'monitor'
        else:
            results['recommendation'] = 'ok'
        
        # Guardar en historial
        if timestamp:
            results['timestamp'] = timestamp.isoformat()
        self.drift_history.append(results)
        
        return results
    
    def _compute_mmd(self, X: np.ndarray, Y: np.ndarray, gamma: float = 1.0) -> float:
        """
        Calcular Maximum Mean Discrepancy (MMD) usando RBF kernel.
        
        Args:
            X: Referencia (n_samples_x, n_features)
            Y: Actual (n_samples_y, n_features)
            gamma: Parámetro del kernel RBF
        
        Returns:
            MMD statistic
        """
        # Simplificación: usar distancia media entre muestras
        # MMD completo requeriría implementación más compleja
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if Y.ndim == 1:
            Y = Y.reshape(-1, 1)
        
        # Calcular distancia promedio entre muestras
        # Aproximación simple usando distancia euclidiana
        X_mean = np.mean(X, axis=0)
        Y_mean = np.mean(Y, axis=0)
        
        mmd = np.linalg.norm(X_mean - Y_mean)
        return float(mmd)
    
    def get_drift_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtener historial de detecciones de drift."""
        return list(self.drift_history[-limit:])


class OverfittingDetector:
    """
    Detecta overfitting usando métricas de train/val gap y learning curves.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar detector de overfitting.
        
        Args:
            config: Configuración del detector
        """
        config = config or {}
        self.overfitting_threshold = config.get("overfitting_threshold", 0.1)  # Gap relativo
        self.min_epochs = config.get("min_epochs", 10)  # Mínimo de epochs para análisis
        
        # Histórico de métricas
        self.train_metrics_history: List[float] = []
        self.val_metrics_history: List[float] = []
        self.epoch_history: List[int] = []
    
    def update_metrics(self, epoch: int, train_metric: float, val_metric: Optional[float] = None) -> None:
        """
        Actualizar métricas de entrenamiento.
        
        Args:
            epoch: Número de epoch
            train_metric: Métrica de entrenamiento (loss, error, etc.)
            val_metric: Métrica de validación (opcional)
        """
        self.epoch_history.append(epoch)
        self.train_metrics_history.append(train_metric)
        if val_metric is not None:
            self.val_metrics_history.append(val_metric)
        else:
            self.val_metrics_history.append(None)
    
    def detect_overfitting(self) -> Dict[str, Any]:
        """
        Detectar overfitting basado en historial de métricas.
        
        Returns:
            Dict con resultados:
            {
                'overfitting_detected': bool,
                'train_val_gap': float,
                'gap_ratio': float,
                'recommendation': str,  # 'stop_training', 'reduce_complexity', 'ok'
                'learning_curve_trend': str  # 'improving', 'plateau', 'diverging'
            }
        """
        if len(self.train_metrics_history) < self.min_epochs:
            return {
                'overfitting_detected': False,
                'reason': 'insufficient_data',
                'recommendation': 'continue_training'
            }
        
        # Filtrar métricas de validación disponibles
        valid_indices = [i for i, v in enumerate(self.val_metrics_history) if v is not None]
        
        if len(valid_indices) < 5:
            return {
                'overfitting_detected': False,
                'reason': 'insufficient_validation_data',
                'recommendation': 'continue_training'
            }
        
        # Usar últimos N epochs
        recent_train = [self.train_metrics_history[i] for i in valid_indices[-10:]]
        recent_val = [self.val_metrics_history[i] for i in valid_indices[-10:]]
        
        # Calcular gap promedio
        train_mean = np.mean(recent_train)
        val_mean = np.mean(recent_val)
        gap = val_mean - train_mean
        
        # Gap relativo
        if train_mean > 0:
            gap_ratio = gap / train_mean
        else:
            gap_ratio = abs(gap)
        
        results = {
            'overfitting_detected': False,
            'train_val_gap': float(gap),
            'gap_ratio': float(gap_ratio),
            'train_metric_mean': float(train_mean),
            'val_metric_mean': float(val_mean),
            'recommendation': 'ok'
        }
        
        # Detectar overfitting
        if gap_ratio > self.overfitting_threshold:
            results['overfitting_detected'] = True
            if gap_ratio > 0.3:
                results['recommendation'] = 'stop_training'
            elif gap_ratio > 0.2:
                results['recommendation'] = 'reduce_complexity'
            else:
                results['recommendation'] = 'monitor'
        
        # Analizar tendencia de learning curve
        if len(recent_train) >= 5:
            train_trend = self._calculate_trend(recent_train)
            val_trend = self._calculate_trend(recent_val)
            
            if train_trend < 0 and val_trend > 0:
                results['learning_curve_trend'] = 'diverging'
                results['overfitting_detected'] = True
            elif train_trend < 0 and val_trend < 0:
                results['learning_curve_trend'] = 'improving'
            else:
                results['learning_curve_trend'] = 'plateau'
        else:
            results['learning_curve_trend'] = 'unknown'
        
        return results
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calcular tendencia usando regresión lineal simple.
        
        Returns:
            Pendiente (negativa = mejorando, positiva = empeorando)
        """
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Pendiente simple
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)
    
    def get_learning_curves(self) -> Dict[str, List[float]]:
        """Obtener learning curves completas."""
        return {
            'epochs': self.epoch_history.copy(),
            'train_metrics': self.train_metrics_history.copy(),
            'val_metrics': self.val_metrics_history.copy()
        }


class AutoRetrainingTrigger:
    """
    Sistema de triggers automáticos para reentrenamiento.
    
    Combina detección de drift y overfitting para decidir cuándo reentrenar.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar sistema de triggers.
        
        Args:
            config: Configuración
        """
        config = config or {}
        
        # Detectors
        self.drift_detector = ConceptDriftDetector(config.get("drift_detector_config", {}))
        self.overfitting_detector = OverfittingDetector(config.get("overfitting_detector_config", {}))
        
        # Triggers
        self.retrain_on_drift = config.get("retrain_on_drift", True)
        self.retrain_on_overfitting = config.get("retrain_on_overfitting", True)
        self.retrain_interval_days = config.get("retrain_interval_days", 30)  # Reentrenar cada X días
        self.retrain_on_performance_degradation = config.get("retrain_on_performance_degradation", True)
        self.performance_degradation_threshold = config.get("performance_degradation_threshold", 0.2)  # 20% peor
        
        # Histórico
        self.last_retrain_timestamp: Optional[datetime] = None
        self.performance_history: List[Dict[str, Any]] = []
        self.retrain_history: List[Dict[str, Any]] = []
    
    def should_retrain(
        self,
        current_data: Optional[np.ndarray] = None,
        current_performance: Optional[Dict[str, float]] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Decidir si se debe reentrenar el modelo.
        
        Args:
            current_data: Datos actuales para detectar drift
            current_performance: Métricas de performance actuales
            timestamp: Timestamp opcional
        
        Returns:
            Dict con decisión:
            {
                'should_retrain': bool,
                'reasons': List[str],
                'drift_detection': Dict,
                'overfitting_detection': Dict,
                'performance_degradation': Dict,
                'time_based': bool
            }
        """
        timestamp = timestamp or datetime.now()
        reasons = []
        should_retrain = False
        
        results = {
            'should_retrain': False,
            'reasons': [],
            'drift_detection': None,
            'overfitting_detection': None,
            'performance_degradation': None,
            'time_based': False
        }
        
        # 1. Check time-based retraining
        if self.last_retrain_timestamp:
            days_since_retrain = (timestamp - self.last_retrain_timestamp).days
            if days_since_retrain >= self.retrain_interval_days:
                should_retrain = True
                reasons.append(f"time_based: {days_since_retrain} days since last retrain")
                results['time_based'] = True
        else:
            # Primera vez, no hay historial
            pass
        
        # 2. Check concept drift
        if self.retrain_on_drift and current_data is not None:
            drift_result = self.drift_detector.detect_drift(current_data, timestamp)
            results['drift_detection'] = drift_result
            
            if drift_result.get('drift_detected', False):
                if drift_result.get('recommendation') == 'retrain':
                    should_retrain = True
                    reasons.append(f"concept_drift: drift_score={drift_result.get('drift_score', 0):.3f}")
        
        # 3. Check overfitting
        if self.retrain_on_overfitting:
            overfitting_result = self.overfitting_detector.detect_overfitting()
            results['overfitting_detection'] = overfitting_result
            
            if overfitting_result.get('overfitting_detected', False):
                if overfitting_result.get('recommendation') in ['stop_training', 'reduce_complexity']:
                    should_retrain = True
                    reasons.append(f"overfitting: gap_ratio={overfitting_result.get('gap_ratio', 0):.3f}")
        
        # 4. Check performance degradation
        if self.retrain_on_performance_degradation and current_performance:
            perf_result = self._check_performance_degradation(current_performance)
            results['performance_degradation'] = perf_result
            
            if perf_result.get('degradation_detected', False):
                should_retrain = True
                reasons.append(f"performance_degradation: {perf_result.get('degradation_score', 0):.3f}")
        
        results['should_retrain'] = should_retrain
        results['reasons'] = reasons
        
        return results
    
    def _check_performance_degradation(self, current_performance: Dict[str, float]) -> Dict[str, Any]:
        """
        Verificar si hay degradación de performance.
        
        Args:
            current_performance: Métricas actuales (ej: {'accuracy': 0.8, 'f1': 0.75})
        
        Returns:
            Dict con resultados de degradación
        """
        if len(self.performance_history) < 3:
            # No hay suficiente historial
            return {
                'degradation_detected': False,
                'reason': 'insufficient_history'
            }
        
        # Comparar con promedio histórico
        historical_avg = {}
        for metric_name in current_performance.keys():
            historical_values = [
                perf.get(metric_name)
                for perf in self.performance_history[-10:]
                if perf.get(metric_name) is not None
            ]
            if historical_values:
                historical_avg[metric_name] = np.mean(historical_values)
        
        degradation_scores = {}
        for metric_name, current_value in current_performance.items():
            if metric_name in historical_avg:
                historical_value = historical_avg[metric_name]
                # Para métricas donde mayor es mejor (accuracy, f1, etc.)
                degradation = (historical_value - current_value) / historical_value if historical_value > 0 else 0
                degradation_scores[metric_name] = degradation
        
        if not degradation_scores:
            return {'degradation_detected': False, 'reason': 'no_comparable_metrics'}
        
        # Score promedio de degradación
        avg_degradation = np.mean(list(degradation_scores.values()))
        
        degradation_detected = avg_degradation > self.performance_degradation_threshold
        
        return {
            'degradation_detected': degradation_detected,
            'degradation_score': float(avg_degradation),
            'metric_degradations': degradation_scores,
            'historical_averages': historical_avg
        }
    
    def record_retrain(self, timestamp: Optional[datetime] = None, metadata: Optional[Dict] = None) -> None:
        """Registrar que se realizó un reentrenamiento."""
        timestamp = timestamp or datetime.now()
        self.last_retrain_timestamp = timestamp
        
        self.retrain_history.append({
            'timestamp': timestamp.isoformat(),
            'metadata': metadata or {}
        })
    
    def record_performance(self, performance: Dict[str, float], timestamp: Optional[datetime] = None) -> None:
        """Registrar performance actual."""
        self.performance_history.append({
            'timestamp': (timestamp or datetime.now()).isoformat(),
            **performance
        })
    
    def get_retrain_history(self) -> List[Dict[str, Any]]:
        """Obtener historial de reentrenamientos."""
        return self.retrain_history.copy()

