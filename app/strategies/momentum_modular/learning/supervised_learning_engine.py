"""
SupervisedLearningEngine - Aprende a predecir probabilidad de éxito de trades.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .base_learning_engine import BaseLearningEngine

logger = logging.getLogger(__name__)

# Importaciones opcionales para diferentes algoritmos
try:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import cross_val_score, train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn no disponible. Funcionalidad limitada.")

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except (ImportError, Exception) as e:
    XGBOOST_AVAILABLE = False
    logger.warning(f"XGBoost no disponible ({type(e).__name__}). Usando sklearn como alternativa.")

try:
    import lightgbm as lgb

    LIGHTGBM_AVAILABLE = True
except (ImportError, Exception) as e:
    LIGHTGBM_AVAILABLE = False
    logger.warning(f"LightGBM no disponible ({type(e).__name__}). No será usado.")

try:
    import catboost as cb

    CATBOOST_AVAILABLE = True
except (ImportError, Exception) as e:
    CATBOOST_AVAILABLE = False
    logger.warning(f"CatBoost no disponible ({type(e).__name__}). No será usado.")

try:
    import torch
    import torch.nn as nn

    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("PyTorch no disponible. Neural networks no disponibles.")


class SupervisedLearningEngine(BaseLearningEngine):
    """
    Motor de aprendizaje supervisado para predecir éxito de trades.

    Algoritmos soportados:
    - RandomForest
    - GradientBoosting
    - XGBoost
    - LightGBM
    - CatBoost
    - Neural Networks (PyTorch)

    Optimiza thresholds de filtros basado en datos históricos etiquetados.
    """

    def __init__(self, config: Dict):
        """Inicializar motor de aprendizaje supervisado."""
        super().__init__("supervised", config)

        self.algorithm = config.get(
            "algorithm", "random_forest"
        )  # random_forest, xgboost, lightgbm, catboost, gradient_boosting, neural_net
        self.feature_cols = config.get("feature_columns", [])
        self.target_col = config.get("target_column", "trade_success")

        # Parámetros específicos por algoritmo
        self.model_params = config.get("model_parameters", {})

        # Threshold optimization
        self.optimize_thresholds = config.get("optimize_thresholds", True)
        self.threshold_params = config.get(
            "threshold_parameters",
            {
                "rsi_buy_min": {"min": 30, "max": 50, "step": 2},
                "rsi_buy_max": {"min": 60, "max": 80, "step": 2},
                "momentum_threshold": {"min": 0.01, "max": 0.03, "step": 0.005},
                "ema_distance": {"min": 0.002, "max": 0.01, "step": 0.001},
            },
        )

    def train(
        self, training_data: Dict[str, Any], validation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Entrenar modelo supervisado.

        Args:
            training_data: {
                'features': pd.DataFrame o np.array,  # Features (indicadores, filtros, etc.)
                'labels': pd.Series o np.array,       # 1 si trade exitoso, 0 si fallido
                'metadata': Dict                      # Info adicional (timestamps, symbols, etc.)
            }
            validation_data: Misma estructura que training_data (opcional)

        Returns:
            Métricas de entrenamiento
        """
        # Verificar disponibilidad dinámicamente para asegurar que sklearn está disponible
        # Esto maneja casos donde SKLEARN_AVAILABLE puede ser incorrecto o sklearn se importó después
        try:
            # Verificar que sklearn está realmente disponible
            import sklearn

            # Verificar que las clases específicas están disponibles
            from sklearn.ensemble import (  # noqa: F401
                GradientBoostingClassifier,
                RandomForestClassifier,
            )
            from sklearn.model_selection import train_test_split  # noqa: F401
        except ImportError as e:
            raise ImportError(
                f"scikit-learn es requerido para SupervisedLearningEngine. "
                f"Instala con: pip install scikit-learn>=1.3.0\n"
                f"Error al verificar: {e}"
            )

        # Preparar datos
        X_train = training_data['features']
        y_train = training_data['labels']

        if isinstance(X_train, pd.DataFrame):
            X_train = X_train.values
        if isinstance(y_train, pd.Series):
            y_train = y_train.values

        # Validar que hay suficientes datos y múltiples clases
        if len(X_train) == 0 or len(y_train) == 0:
            logger.warning("Datos de entrenamiento vacíos")
            return {'error': 'empty_data'}

        unique_labels = len(np.unique(y_train))
        if unique_labels < 2:
            logger.warning(
                f"Solo hay {unique_labels} clase(s) en los labels. Se necesita al menos 2 clases para entrenamiento supervisado."
            )
            logger.warning(
                f"  Total samples: {len(y_train)}, Labels: {np.unique(y_train, return_counts=True)}"
            )
            # No podemos entrenar sin múltiples clases - retornar error
            return {
                'error': 'insufficient_classes',
                'message': f'Solo hay {unique_labels} clase(s) en los labels. Se necesita al menos 2 clases.',
                'unique_labels': int(unique_labels),
                'total_samples': len(y_train),
            }

        # Split de validación si no se proporciona
        if validation_data is None:
            # Solo usar stratify si hay más de una clase (evita error con una sola clase)
            unique_classes = len(np.unique(y_train))
            stratify_param = y_train if unique_classes > 1 else None
            X_train, X_val, y_train, y_val = train_test_split(
                X_train, y_train, test_size=0.2, random_state=42, stratify=stratify_param
            )
        else:
            X_val = validation_data['features']
            y_val = validation_data['labels']
            if isinstance(X_val, pd.DataFrame):
                X_val = X_val.values
            if isinstance(y_val, pd.Series):
                y_val = y_val.values

        # Entrenar modelo según algoritmo seleccionado
        if self.algorithm == "random_forest":
            self.model = self._train_random_forest(X_train, y_train)
        elif self.algorithm == "xgboost" and XGBOOST_AVAILABLE:
            self.model = self._train_xgboost(X_train, y_train)
        elif self.algorithm == "lightgbm" and LIGHTGBM_AVAILABLE:
            self.model = self._train_lightgbm(X_train, y_train, X_val, y_val)
        elif self.algorithm == "catboost" and CATBOOST_AVAILABLE:
            self.model = self._train_catboost(X_train, y_train, X_val, y_val)
        elif self.algorithm == "gradient_boosting":
            self.model = self._train_gradient_boosting(X_train, y_train)
        elif self.algorithm == "neural_net" and PYTORCH_AVAILABLE:
            self.model = self._train_neural_net(X_train, y_train, X_val, y_val)
        else:
            logger.warning(f"Algoritmo {self.algorithm} no disponible, usando RandomForest")
            self.model = self._train_random_forest(X_train, y_train)

        # Evaluar en validación
        metrics = self._evaluate_model(X_val, y_val)

        # Optimizar thresholds si está habilitado
        if self.optimize_thresholds and training_data.get('metadata'):
            optimal_thresholds = self._optimize_thresholds(training_data)
            metrics['optimal_thresholds'] = optimal_thresholds

        self.is_trained = True
        return metrics

    def _train_random_forest(self, X_train, y_train):
        """Entrenar RandomForest."""
        n_estimators = self.model_params.get("n_estimators", 100)
        max_depth = self.model_params.get("max_depth", 10)
        min_samples_split = self.model_params.get("min_samples_split", 5)

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        return model

    def _train_xgboost(self, X_train, y_train):
        """Entrenar XGBoost."""
        params = {
            'n_estimators': self.model_params.get("n_estimators", 100),
            'max_depth': self.model_params.get("max_depth", 6),
            'learning_rate': self.model_params.get("learning_rate", 0.1),
            'subsample': self.model_params.get("subsample", 0.8),
            'random_state': 42,
            **self.model_params.get("xgboost_params", {}),
        }

        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)
        return model

    def _train_lightgbm(self, X_train, y_train, X_val, y_val):
        """Entrenar LightGBM con early stopping."""
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': self.model_params.get("num_leaves", 31),
            'learning_rate': self.model_params.get("learning_rate", 0.05),
            'feature_fraction': self.model_params.get("feature_fraction", 0.9),
            'bagging_fraction': self.model_params.get("bagging_fraction", 0.8),
            'bagging_freq': self.model_params.get("bagging_freq", 5),
            'verbose': -1,  # Suprimir output
            'random_state': 42,
            **self.model_params.get("lightgbm_params", {}),
        }

        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # Entrenar con early stopping
        num_boost_round = self.model_params.get("n_estimators", 100)
        early_stopping_rounds = self.model_params.get("early_stopping_rounds", 10)

        model = lgb.train(
            params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[val_data],
            callbacks=[lgb.early_stopping(early_stopping_rounds), lgb.log_evaluation(period=0)],
        )

        # Wrapper para compatibilidad con predict_proba
        class LightGBMWrapper:
            def __init__(self, model):
                self.model = model

            def predict_proba(self, X):
                pred = self.model.predict(X)
                # Retornar en formato [prob_class_0, prob_class_1]
                return np.column_stack([1 - pred, pred])

            def predict(self, X):
                return (self.model.predict(X) >= 0.5).astype(int)

            @property
            def feature_importances_(self):
                return self.model.feature_importance(importance_type='gain')

        return LightGBMWrapper(model)

    def _train_catboost(self, X_train, y_train, X_val, y_val):
        """Entrenar CatBoost con early stopping."""
        params = {
            'iterations': self.model_params.get("n_estimators", 100),
            'depth': self.model_params.get("max_depth", 6),
            'learning_rate': self.model_params.get("learning_rate", 0.1),
            'loss_function': 'Logloss',
            'eval_metric': 'AUC',
            'verbose': False,
            'random_seed': 42,
            **self.model_params.get("catboost_params", {}),
        }

        # CatBoost acepta early stopping automáticamente
        model = cb.CatBoostClassifier(**params)

        # Entrenar con early stopping
        model.fit(
            X_train,
            y_train,
            eval_set=(X_val, y_val),
            early_stopping_rounds=self.model_params.get("early_stopping_rounds", 10),
            verbose=False,
        )

        return model

    def _train_gradient_boosting(self, X_train, y_train):
        """Entrenar GradientBoosting."""
        params = {
            'n_estimators': self.model_params.get("n_estimators", 100),
            'max_depth': self.model_params.get("max_depth", 5),
            'learning_rate': self.model_params.get("learning_rate", 0.1),
            'random_state': 42,
        }

        model = GradientBoostingClassifier(**params)
        model.fit(X_train, y_train)
        return model

    def _train_neural_net(self, X_train, y_train, X_val, y_val):
        """Entrenar red neuronal con PyTorch."""
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch requerido para neural networks")

        input_size = X_train.shape[1]
        hidden_sizes = self.model_params.get("hidden_sizes", [64, 32])
        learning_rate = self.model_params.get("learning_rate", 0.001)
        epochs = self.model_params.get("epochs", 50)
        batch_size = self.model_params.get("batch_size", 32)

        # Definir modelo
        layers = [nn.Linear(input_size, hidden_sizes[0]), nn.ReLU()]
        for i in range(len(hidden_sizes) - 1):
            layers.extend([nn.Linear(hidden_sizes[i], hidden_sizes[i + 1]), nn.ReLU()])
        layers.append(nn.Linear(hidden_sizes[-1], 1))
        layers.append(nn.Sigmoid())

        model = nn.Sequential(*layers)
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # Convertir a tensores
        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train).unsqueeze(1)
        X_val_t = torch.FloatTensor(X_val)
        y_val_t = torch.FloatTensor(y_val).unsqueeze(1)

        # Entrenar
        for epoch in range(epochs):
            # Forward pass
            outputs = model(X_train_t)
            loss = criterion(outputs, y_train_t)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if (epoch + 1) % 10 == 0:
                with torch.no_grad():
                    val_outputs = model(X_val_t)
                    val_loss = criterion(val_outputs, y_val_t)
                    logger.debug(
                        f"Epoch {epoch+1}/{epochs}, Loss: {loss.item():.4f}, Val Loss: {val_loss.item():.4f}"
                    )

        return model

    def _evaluate_model(self, X, y):
        """Evaluar modelo y retornar métricas."""
        if PYTORCH_AVAILABLE and isinstance(self.model, nn.Module):
            # Evaluación para PyTorch
            with torch.no_grad():
                X_t = torch.FloatTensor(X)
                predictions = self.model(X_t).numpy().flatten()
                y_pred = (predictions >= 0.5).astype(int)
        else:
            # Evaluación para sklearn/xgboost/lightgbm/catboost
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)
                # Verificar si solo hay una clase (proba tiene shape [n_samples, 1])
                # En ese caso, usar la única columna disponible
                if proba.shape[1] > 1:
                    predictions = proba[:, 1]
                else:
                    predictions = proba[:, 0]
            else:
                predictions = self.model.predict(X)

            # Obtener predicciones de clase (para métricas)
            y_pred = self.model.predict(X)

        metrics = {
            'accuracy': float(accuracy_score(y, y_pred)),
            'precision': float(precision_score(y, y_pred, zero_division=0)),
            'recall': float(recall_score(y, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y, y_pred, zero_division=0)),
        }

        # AUC si hay probabilidades y más de una clase
        unique_labels = len(np.unique(y))
        if unique_labels > 1:
            try:
                if predictions.ndim == 1:
                    # Ya es un array 1D
                    metrics['roc_auc'] = float(roc_auc_score(y, predictions))
                elif predictions.shape[1] > 1:
                    # Múltiples clases, usar la clase positiva
                    metrics['roc_auc'] = float(roc_auc_score(y, predictions[:, 1]))
                else:
                    # Solo una columna, usar esa
                    metrics['roc_auc'] = float(roc_auc_score(y, predictions[:, 0]))
            except (ValueError, IndexError) as e:
                # Si falla (por ejemplo, solo una clase en y), simplemente no calcular AUC
                logger.debug(f"No se pudo calcular AUC: {e}")
                pass

        return metrics

    def _optimize_thresholds(self, training_data: Dict) -> Dict[str, float]:
        """
        Optimizar thresholds de filtros usando grid search.

        Retorna thresholds optimizados para maximizar win rate o Sharpe ratio.
        """
        # Placeholder: implementación simplificada
        # En producción, usar grid search o optimización bayesiana
        optimal = {}

        for param_name, param_config in self.threshold_params.items():
            # Buscar threshold óptimo
            best_value = param_config["min"]
            best_score = 0.0

            values = np.arange(
                param_config["min"],
                param_config["max"] + param_config["step"],
                param_config["step"],
            )

            for value in values:
                # Simular score (en producción, evaluar en datos reales)
                score = np.random.random()  # Placeholder
                if score > best_score:
                    best_score = score
                    best_value = value

            optimal[param_name] = float(best_value)

        logger.info(f"Thresholds optimizados: {optimal}")
        return optimal

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predecir probabilidad de éxito de un trade.

        Args:
            features: {
                'indicators': Dict,      # RSI, EMA, Momentum, etc.
                'filter_results': Dict,  # Resultados de filtros
                'market_context': Dict   # Contexto de mercado
            }

        Returns:
            {
                'success_probability': float,  # 0.0-1.0
                'recommended_action': str,     # 'BUY', 'SELL', 'HOLD'
                'confidence': float,
                'feature_importance': Dict     # Importancia de features (si disponible)
            }
        """
        if not self.is_ready():
            return {'success_probability': 0.5, 'recommended_action': 'HOLD', 'confidence': 0.0}

        # Extraer features del dict
        feature_vector = self._extract_features(features)

        if PYTORCH_AVAILABLE and isinstance(self.model, nn.Module):
            # Predicción con PyTorch
            with torch.no_grad():
                X_t = torch.FloatTensor([feature_vector])
                prob = self.model(X_t).item()
        else:
            # Predicción con sklearn/xgboost
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba([feature_vector])[0]
                # Manejar caso donde solo hay una clase
                if len(proba) > 1:
                    prob = proba[1]  # Clase positiva
                else:
                    prob = proba[0]  # Única clase disponible
            else:
                pred = self.model.predict([feature_vector])[0]
                prob = float(pred)

        # Decidir acción
        if prob >= 0.6:
            action = 'BUY'
        elif prob <= 0.4:
            action = 'SELL'
        else:
            action = 'HOLD'

        # Feature importance si disponible
        importance = {}
        # LightGBM wrapper tiene feature_importances_ como property
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            if isinstance(features.get('indicators'), dict):
                feature_names = list(features['indicators'].keys())
                # Puede que tengamos más features que nombres, usar índices genéricos si es necesario
                for i, imp in enumerate(importances):
                    if i < len(feature_names):
                        importance[feature_names[i]] = float(imp)
                    else:
                        importance[f'feature_{i}'] = float(imp)
        # CatBoost también tiene feature_importances_
        elif hasattr(self.model, 'get_feature_importance'):
            try:
                importances = self.model.get_feature_importance()
                if isinstance(features.get('indicators'), dict):
                    feature_names = list(features['indicators'].keys())
                    for i, imp in enumerate(importances):
                        if i < len(feature_names):
                            importance[feature_names[i]] = float(imp)
                        else:
                            importance[f'feature_{i}'] = float(imp)
            except Exception as e:
                logger.debug(f"No se pudo obtener feature importance: {e}")

        return {
            'success_probability': float(prob),
            'recommended_action': action,
            'confidence': abs(prob - 0.5) * 2,  # 0.0 si prob=0.5, 1.0 si prob=0.0 o 1.0
            'feature_importance': importance,
        }

    def _extract_features(self, features: Dict) -> List[float]:
        """Extraer vector de features del dict usando FeatureExtractor."""
        # Usar FeatureExtractor para extracción completa
        from app.strategies.momentum_modular.learning.feature_extractor import FeatureExtractor

        if not hasattr(self, '_feature_extractor'):
            self._feature_extractor = FeatureExtractor()

        extracted = self._feature_extractor.extract_complete_features(
            indicators=features.get('indicators', {}),
            filter_results=features.get('filter_results', {}),
            market_context=features.get('market_context', {}),
            metadata=features.get('metadata', {}),
        )

        return extracted['feature_vector']

    def evaluate(self, test_data: Dict[str, Any]) -> Dict[str, float]:
        """Evaluar modelo en datos de prueba."""
        X_test = test_data['features']
        y_test = test_data['labels']

        if isinstance(X_test, pd.DataFrame):
            X_test = X_test.values
        if isinstance(y_test, pd.Series):
            y_test = y_test.values

        return self._evaluate_model(X_test, y_test)
