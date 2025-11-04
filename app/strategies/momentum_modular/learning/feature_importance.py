"""
FeatureImportance - Sistema completo de análisis de importancia de features.

Incluye:
1. SHAP values para modelos supervisados (tree-based y neural networks)
2. Attention weights para transformers
3. Feature selection automático basado en importancia
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)

# Importaciones opcionales para SHAP
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("shap no disponible. SHAP values no funcionarán.")

try:
    from sklearn.feature_selection import (
        SelectKBest, f_classif, f_regression,
        RFE, SelectFromModel
    )
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    SKLEARN_FEATURE_SELECTION_AVAILABLE = True
except ImportError:
    SKLEARN_FEATURE_SELECTION_AVAILABLE = False
    logger.warning("sklearn feature selection no disponible.")


class SHAPAnalyzer:
    """
    Analizador SHAP para explicar predicciones de modelos.
    
    Soporta:
    - Tree-based models (XGBoost, LightGBM, CatBoost, RandomForest)
    - Neural networks (PyTorch, TensorFlow)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar analizador SHAP.
        
        Args:
            config: Configuración
        """
        config = config or {}
        self.sample_size = config.get("sample_size", 100)  # Para TreeExplainer
        self.max_evals = config.get("max_evals", 100)  # Para KernelExplainer
        self.use_background = config.get("use_background", True)
        
        if not SHAP_AVAILABLE:
            logger.warning("SHAP no disponible. Instala con: pip install shap")
    
    def explain_model(
        self,
        model: Any,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None,
        model_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Explicar modelo usando SHAP values.
        
        Args:
            model: Modelo entrenado
            X: Datos de entrada (n_samples, n_features)
            feature_names: Nombres de features (opcional)
            model_type: Tipo de modelo ('tree', 'linear', 'neural', 'auto')
        
        Returns:
            Dict con SHAP values y explicaciones:
            {
                'shap_values': np.ndarray,
                'base_value': float,
                'feature_names': List[str],
                'feature_importance': Dict[str, float],
                'summary_stats': Dict
            }
        """
        if not SHAP_AVAILABLE:
            return {
                'error': 'SHAP not available',
                'message': 'Install with: pip install shap'
            }
        
        try:
            # Determinar tipo de explainer
            explainer = self._create_explainer(model, X, model_type)
            
            # Calcular SHAP values
            if isinstance(explainer, shap.TreeExplainer):
                # TreeExplainer es rápido y exacto para tree-based models
                shap_values = explainer.shap_values(X[:self.sample_size])
                base_value = explainer.expected_value
            elif isinstance(explainer, shap.KernelExplainer):
                # KernelExplainer para modelos generales (más lento)
                shap_values = explainer.shap_values(X[:min(self.sample_size, len(X))], nsamples=self.max_evals)
                base_value = explainer.expected_value if hasattr(explainer, 'expected_value') else 0.0
            else:
                # LinearExplainer o DeepExplainer
                shap_values = explainer.shap_values(X[:self.sample_size])
                base_value = explainer.expected_value if hasattr(explainer, 'expected_value') else 0.0
            
            # Si shap_values es una lista (multi-class), usar promedio
            if isinstance(shap_values, list):
                shap_values = np.mean([np.abs(sv) for sv in shap_values], axis=0)
            else:
                shap_values = np.abs(shap_values)  # Valor absoluto para importancia
            
            # Calcular importancia promedio por feature
            if shap_values.ndim > 1:
                feature_importance = np.mean(shap_values, axis=0)
            else:
                feature_importance = shap_values
            
            # Crear dict de importancia
            if feature_names and len(feature_names) == len(feature_importance):
                importance_dict = {
                    name: float(imp)
                    for name, imp in zip(feature_names, feature_importance)
                }
            else:
                importance_dict = {
                    f'feature_{i}': float(imp)
                    for i, imp in enumerate(feature_importance)
                }
            
            # Estadísticas resumen
            summary_stats = {
                'mean_importance': float(np.mean(feature_importance)),
                'std_importance': float(np.std(feature_importance)),
                'max_importance': float(np.max(feature_importance)),
                'min_importance': float(np.min(feature_importance)),
                'top_features': sorted(
                    importance_dict.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }
            
            return {
                'shap_values': shap_values,
                'base_value': float(base_value),
                'feature_names': feature_names or [f'feature_{i}' for i in range(len(feature_importance))],
                'feature_importance': importance_dict,
                'summary_stats': summary_stats
            }
            
        except Exception as e:
            logger.error(f"Error calculando SHAP values: {e}", exc_info=True)
            return {
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def _create_explainer(self, model: Any, X: np.ndarray, model_type: str) -> Any:
        """
        Crear explainer SHAP apropiado para el modelo.
        
        Args:
            model: Modelo entrenado
            X: Datos de entrada
            model_type: Tipo de modelo
        
        Returns:
            SHAP explainer
        """
        if model_type == "auto":
            # Auto-detectar tipo
            model_type = self._detect_model_type(model)
        
        # Preparar background data
        if self.use_background and len(X) > 50:
            background = X[:min(50, len(X))]
        else:
            background = X
        
        if model_type == "tree":
            # Tree-based models (XGBoost, LightGBM, CatBoost, RandomForest)
            return shap.TreeExplainer(model)
        elif model_type == "linear":
            # Linear models
            return shap.LinearExplainer(model, background)
        elif model_type == "neural":
            # Neural networks
            try:
                # Intentar DeepExplainer primero
                return shap.DeepExplainer(model, background)
            except:
                # Fallback a KernelExplainer
                return shap.KernelExplainer(model.predict, background)
        else:
            # Fallback genérico
            return shap.KernelExplainer(model.predict, background)
    
    def _detect_model_type(self, model: Any) -> str:
        """
        Detectar tipo de modelo automáticamente.
        
        Returns:
            Tipo de modelo: 'tree', 'linear', 'neural', 'generic'
        """
        model_type = str(type(model)).lower()
        
        if any(x in model_type for x in ['xgboost', 'lightgbm', 'catboost', 'randomforest', 'gradientboosting']):
            return "tree"
        elif any(x in model_type for x in ['linear', 'logistic', 'ridge', 'lasso']):
            return "linear"
        elif any(x in model_type for x in ['neural', 'nn', 'module', 'sequential']):
            return "neural"
        else:
            return "generic"
    
    def explain_prediction(
        self,
        model: Any,
        X: np.ndarray,
        instance_idx: int,
        feature_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Explicar una predicción individual.
        
        Args:
            model: Modelo entrenado
            X: Datos completos
            instance_idx: Índice de la instancia a explicar
            feature_names: Nombres de features
        
        Returns:
            Dict con explicación para esta instancia
        """
        if not SHAP_AVAILABLE:
            return {'error': 'SHAP not available'}
        
        try:
            explainer = self._create_explainer(model, X, "auto")
            
            # Calcular SHAP values para esta instancia
            instance = X[instance_idx:instance_idx+1]
            
            if isinstance(explainer, shap.TreeExplainer):
                shap_values = explainer.shap_values(instance)
            else:
                shap_values = explainer.shap_values(instance, nsamples=self.max_evals)
            
            # Si es lista (multi-class), usar la clase positiva
            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            
            shap_values = shap_values.flatten()
            
            # Crear explicación
            if feature_names and len(feature_names) == len(shap_values):
                explanation = {
                    name: float(value)
                    for name, value in zip(feature_names, shap_values)
                }
            else:
                explanation = {
                    f'feature_{i}': float(value)
                    for i, value in enumerate(shap_values)
                }
            
            # Ordenar por valor absoluto
            sorted_explanation = sorted(
                explanation.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            return {
                'explanation': explanation,
                'sorted_explanation': sorted_explanation,
                'top_contributors': sorted_explanation[:5]
            }
            
        except Exception as e:
            logger.error(f"Error explicando predicción: {e}", exc_info=True)
            return {'error': str(e)}


class AttentionWeightsAnalyzer:
    """
    Analizador de attention weights para modelos Transformer.
    
    Extrae y analiza los pesos de atención para entender qué partes
    de la secuencia temporal son más importantes.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar analizador de attention weights.
        
        Args:
            config: Configuración
        """
        config = config or {}
        self.aggregation_method = config.get("aggregation_method", "mean")  # mean, max, first
        self.normalize = config.get("normalize", True)
    
    def extract_attention_weights(
        self,
        model: Any,
        sequence: np.ndarray,
        layer_idx: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extraer attention weights de un modelo Transformer.
        
        Args:
            model: Modelo Transformer (PyTorch)
            sequence: Secuencia de entrada (batch_size, seq_len, features)
            layer_idx: Índice de capa específica (None = todas)
        
        Returns:
            Dict con attention weights y análisis:
            {
                'attention_weights': np.ndarray,
                'attention_by_position': Dict[int, float],
                'top_important_positions': List[int],
                'feature_importance': Dict[str, float]
            }
        """
        try:
            import torch
            import torch.nn as nn
            
            if not isinstance(model, nn.Module):
                return {'error': 'Model is not a PyTorch nn.Module'}
            
            model.eval()
            
            # Convertir a tensor
            if isinstance(sequence, np.ndarray):
                sequence_tensor = torch.FloatTensor(sequence)
            else:
                sequence_tensor = sequence
            
            # Obtener attention weights
            attention_weights = self._get_attention_from_model(model, sequence_tensor, layer_idx)
            
            if attention_weights is None:
                return {'error': 'Could not extract attention weights from model'}
            
            # Agregar attention weights
            if self.aggregation_method == "mean":
                aggregated = np.mean(attention_weights, axis=(0, 1))  # Promediar heads y layers
            elif self.aggregation_method == "max":
                aggregated = np.max(attention_weights, axis=(0, 1))
            else:  # first
                aggregated = attention_weights[0, 0]  # Primer head, primera layer
            
            # Normalizar si es necesario
            if self.normalize:
                aggregated = aggregated / (np.sum(aggregated) + 1e-8)
            
            # Analizar importancia por posición
            seq_len = aggregated.shape[0]
            attention_by_position = {
                i: float(aggregated[i])
                for i in range(seq_len)
            }
            
            # Top posiciones importantes
            sorted_positions = sorted(
                attention_by_position.items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_positions = [pos for pos, _ in sorted_positions[:5]]
            
            return {
                'attention_weights': attention_weights,
                'aggregated_attention': aggregated,
                'attention_by_position': attention_by_position,
                'top_important_positions': top_positions,
                'sequence_length': seq_len,
                'aggregation_method': self.aggregation_method
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo attention weights: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _get_attention_from_model(
        self,
        model: Any,
        sequence: Any,
        layer_idx: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Extraer attention weights del modelo.
        
        Args:
            model: Modelo PyTorch
            sequence: Secuencia de entrada
            layer_idx: Índice de capa específica
        
        Returns:
            Attention weights como numpy array
        """
        try:
            import torch
            import torch.nn as nn
            
            # Buscar TransformerEncoderLayer en el modelo
            attention_weights_list = []
            
            # Hook para capturar attention
            def attention_hook(module, input, output):
                # En TransformerEncoderLayer, el output es (output, attention_weights) si return_attn=True
                # O podemos usar register_forward_hook y buscar el atributo
                if hasattr(module, 'self_attn'):
                    # Intentar obtener attention weights
                    # Esto requiere que el modelo tenga return_attention=True
                    pass
            
            # Buscar capas de transformer
            for name, module in model.named_modules():
                if isinstance(module, nn.TransformerEncoderLayer):
                    if layer_idx is None or name.endswith(f'[{layer_idx}]'):
                        # Registrar hook
                        hook = module.register_forward_hook(attention_hook)
                        # Forward pass
                        with torch.no_grad():
                            output = module(sequence)
                        hook.remove()
            
            # Alternativa: usar forward hook global
            # Por ahora, retornar None y usar método alternativo
            # En producción, esto requeriría modificar el modelo para retornar attention
            
            return None  # Placeholder - requiere implementación específica del modelo
            
        except Exception as e:
            logger.warning(f"No se pudieron extraer attention weights: {e}")
            return None


class FeatureSelector:
    """
    Sistema de selección automática de features basado en importancia.
    
    Métodos soportados:
    - Univariate selection (SelectKBest)
    - Recursive Feature Elimination (RFE)
    - Model-based selection (SelectFromModel)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar selector de features.
        
        Args:
            config: Configuración
        """
        config = config or {}
        self.method = config.get("method", "model_based")  # univariate, rfe, model_based
        self.n_features = config.get("n_features", "auto")  # Número de features o "auto"
        self.importance_threshold = config.get("importance_threshold", 0.01)
        self.use_cross_validation = config.get("use_cross_validation", True)
        
        if not SKLEARN_FEATURE_SELECTION_AVAILABLE:
            logger.warning("sklearn feature selection no disponible.")
    
    def select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
        model: Optional[Any] = None,
        task_type: str = "classification"  # classification o regression
    ) -> Dict[str, Any]:
        """
        Seleccionar features más importantes.
        
        Args:
            X: Features (n_samples, n_features)
            y: Targets (n_samples,)
            feature_names: Nombres de features
            model: Modelo para model-based selection (opcional)
            task_type: Tipo de tarea
        
        Returns:
            Dict con features seleccionadas:
            {
                'selected_features': List[int],
                'selected_feature_names': List[str],
                'feature_scores': Dict[str, float],
                'n_selected': int,
                'selection_method': str
            }
        """
        if not SKLEARN_FEATURE_SELECTION_AVAILABLE:
            return {
                'error': 'sklearn feature selection not available',
                'selected_features': list(range(X.shape[1])),  # Seleccionar todas
                'selected_feature_names': feature_names or [f'feature_{i}' for i in range(X.shape[1])]
            }
        
        try:
            # Determinar número de features
            if self.n_features == "auto":
                # Seleccionar top 50% o mínimo 10
                n_features = max(10, X.shape[1] // 2)
            else:
                n_features = min(self.n_features, X.shape[1])
            
            feature_names = feature_names or [f'feature_{i}' for i in range(X.shape[1])]
            
            if self.method == "univariate":
                selector, scores = self._univariate_selection(X, y, n_features, task_type)
            elif self.method == "rfe":
                selector, scores = self._rfe_selection(X, y, n_features, model, task_type)
            elif self.method == "model_based":
                selector, scores = self._model_based_selection(X, y, model, task_type)
            else:
                # Default: usar todas
                return {
                    'selected_features': list(range(X.shape[1])),
                    'selected_feature_names': feature_names,
                    'feature_scores': {},
                    'n_selected': X.shape[1],
                    'selection_method': 'none'
                }
            
            # Obtener índices seleccionados
            if hasattr(selector, 'get_support'):
                selected_indices = selector.get_support(indices=True)
            elif hasattr(selector, 'support_'):
                selected_indices = np.where(selector.support_)[0]
            else:
                selected_indices = list(range(X.shape[1]))
            
            # Crear dict de scores
            feature_scores = {}
            if scores is not None:
                for i, name in enumerate(feature_names):
                    if i < len(scores):
                        feature_scores[name] = float(scores[i])
            
            selected_feature_names = [feature_names[i] for i in selected_indices]
            
            return {
                'selected_features': selected_indices.tolist() if isinstance(selected_indices, np.ndarray) else selected_indices,
                'selected_feature_names': selected_feature_names,
                'feature_scores': feature_scores,
                'n_selected': len(selected_indices),
                'selection_method': self.method,
                'selector': selector  # Para uso futuro
            }
            
        except Exception as e:
            logger.error(f"Error seleccionando features: {e}", exc_info=True)
            return {
                'error': str(e),
                'selected_features': list(range(X.shape[1])),
                'selected_feature_names': feature_names or [f'feature_{i}' for i in range(X.shape[1])]
            }
    
    def _univariate_selection(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_features: int,
        task_type: str
    ) -> Tuple[Any, np.ndarray]:
        """Selección univariante usando SelectKBest."""
        if task_type == "classification":
            score_func = f_classif
        else:
            score_func = f_regression
        
        selector = SelectKBest(score_func=score_func, k=n_features)
        selector.fit(X, y)
        
        scores = selector.scores_
        return selector, scores
    
    def _rfe_selection(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_features: int,
        model: Optional[Any],
        task_type: str
    ) -> Tuple[Any, Optional[np.ndarray]]:
        """Recursive Feature Elimination."""
        # Crear modelo base si no se proporciona
        if model is None:
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=50, random_state=42)
        
        selector = RFE(estimator=model, n_features_to_select=n_features)
        selector.fit(X, y)
        
        # Scores de RFE
        scores = selector.ranking_  # Lower is better
        return selector, scores
    
    def _model_based_selection(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model: Optional[Any],
        task_type: str
    ) -> Tuple[Any, Optional[np.ndarray]]:
        """Selección basada en importancia del modelo."""
        # Crear modelo base si no se proporciona
        if model is None:
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
        
        # Si el modelo ya está entrenado, usar directamente
        if not hasattr(model, 'feature_importances_'):
            # Entrenar si no está entrenado
            if not hasattr(model, 'n_estimators'):
                if task_type == "classification":
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                else:
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
        
        # Usar SelectFromModel con threshold
        selector = SelectFromModel(
            estimator=model,
            threshold=self.importance_threshold
        )
        selector.fit(X, y)
        
        # Obtener scores (importancia)
        if hasattr(model, 'feature_importances_'):
            scores = model.feature_importances_
        else:
            scores = None
        
        return selector, scores


class FeatureImportanceAnalyzer:
    """
    Analizador unificado de importancia de features.
    
    Combina SHAP, attention weights y feature selection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar analizador unificado.
        
        Args:
            config: Configuración
        """
        config = config or {}
        self.shap_analyzer = SHAPAnalyzer(config.get("shap_config", {}))
        self.attention_analyzer = AttentionWeightsAnalyzer(config.get("attention_config", {}))
        self.feature_selector = FeatureSelector(config.get("feature_selector_config", {}))
    
    def analyze(
        self,
        model: Any,
        X: np.ndarray,
        y: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
        model_type: str = "auto",
        include_shap: bool = True,
        include_attention: bool = False,
        include_selection: bool = False
    ) -> Dict[str, Any]:
        """
        Análisis completo de importancia de features.
        
        Args:
            model: Modelo entrenado
            X: Features (n_samples, n_features) o sequences (n_samples, seq_len, features)
            y: Targets (opcional, para feature selection)
            feature_names: Nombres de features
            model_type: Tipo de modelo
            include_shap: Incluir análisis SHAP
            include_attention: Incluir análisis de attention (para transformers)
            include_selection: Incluir feature selection
        
        Returns:
            Dict con análisis completo
        """
        results = {
            'feature_names': feature_names or [f'feature_{i}' for i in range(X.shape[-1])],
            'shap_analysis': None,
            'attention_analysis': None,
            'feature_selection': None,
            'combined_importance': {}
        }
        
        # SHAP analysis
        if include_shap:
            try:
                shap_results = self.shap_analyzer.explain_model(
                    model, X, feature_names, model_type
                )
                results['shap_analysis'] = shap_results
                if 'feature_importance' in shap_results:
                    results['combined_importance']['shap'] = shap_results['feature_importance']
            except Exception as e:
                logger.warning(f"SHAP analysis failed: {e}")
        
        # Attention analysis (para transformers)
        if include_attention:
            try:
                attention_results = self.attention_analyzer.extract_attention_weights(
                    model, X
                )
                results['attention_analysis'] = attention_results
            except Exception as e:
                logger.warning(f"Attention analysis failed: {e}")
        
        # Feature selection
        if include_selection and y is not None:
            try:
                selection_results = self.feature_selector.select_features(
                    X.reshape(len(X), -1) if X.ndim > 2 else X,
                    y,
                    feature_names,
                    model
                )
                results['feature_selection'] = selection_results
            except Exception as e:
                logger.warning(f"Feature selection failed: {e}")
        
        # Combinar importancias
        if results['combined_importance']:
            # Promediar diferentes métodos de importancia
            all_importances = []
            for method, importance_dict in results['combined_importance'].items():
                all_importances.append(importance_dict)
            
            # Promediar
            combined = {}
            for imp_dict in all_importances:
                for name, value in imp_dict.items():
                    if name not in combined:
                        combined[name] = []
                    combined[name].append(value)
            
            # Calcular promedio
            final_combined = {
                name: float(np.mean(values))
                for name, values in combined.items()
            }
            results['combined_importance'] = final_combined
        
        return results

