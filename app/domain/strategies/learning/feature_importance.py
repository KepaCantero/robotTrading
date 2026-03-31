"""
FeatureImportance - Sistema completo de análisis de importancia de features.

[TASK-4.2-FEATURE-IMPORTANCE] Enhanced feature importance system for ML models in trading.

Incluye:
1. SHAP values para modelos supervisados (tree-based y neural networks)
2. Attention weights para transformers
3. Feature selection automático basado en importancia
4. Permutation importance (model-agnostic)
5. Built-in model importance extraction
6. Correlation analysis (target and feature-feature)
7. Feature stability tracking over time
8. Comprehensive analysis facade
9. YAML configuration support
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

import numpy as np
from numpy.typing import NDArray
from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

# Type aliases for clarity
ArrayLike: TypeAlias = Union[NDArray[np.floating], NDArray[np.integer]]
FloatArray: TypeAlias = NDArray[np.floating]
IntArray: TypeAlias = NDArray[np.integer]


# ============================================================================
# Protocol types for duck-typed ML objects
# ============================================================================
@runtime_checkable
class Predictor(Protocol):
    """Protocol for models with predict method."""

    def predict(self, X: object, /) -> object: ...


@runtime_checkable
class TreeModel(Protocol):
    """Protocol for tree-based models with feature_importances_."""

    feature_importances_: np.ndarray
    n_estimators: int

    def fit(self, X: object, y: object, /) -> object: ...
    def predict(self, X: object, /) -> object: ...


@runtime_checkable
class ShapExplainer(Protocol):
    """Protocol for SHAP explainers."""

    expected_value: object

    def shap_values(self, X: object, /) -> object: ...


@runtime_checkable
class FeatureImportancesModel(Protocol):
    """Protocol for models that expose feature_importances_."""

    feature_importances_: np.ndarray


@runtime_checkable
class SklearnSelector(Protocol):
    """Protocol for sklearn feature selectors."""

    support_: np.ndarray
    scores_: np.ndarray

    def fit(self, X: object, y: object, /) -> object: ...
    def get_support(self, indices: bool = False, /) -> np.ndarray: ...


@runtime_checkable
class RFESelector(Protocol):
    """Protocol for RFE selectors."""

    ranking_: np.ndarray
    support_: np.ndarray

    def fit(self, X: object, y: object, /) -> object: ...
    def get_support(self, indices: bool = False, /) -> np.ndarray: ...


@runtime_checkable
class NamedModulesModel(Protocol):
    """Protocol for models with named_modules."""

    def named_modules(self) -> Iterable[tuple[str, object]]: ...
    def eval(self) -> object: ...


# Union types for flexible model/explainer/selector parameters
ModelType = Union[Predictor, TreeModel, FeatureImportancesModel, NamedModulesModel, object]
ExplainerType = Union[ShapExplainer, object]
SelectorType = Union[SklearnSelector, RFESelector, object]

# Configuration types - using object for flexible nested config
ConfigValue = Union[str, int, float, bool]
ConfigDict = dict[str, ConfigValue]
NestedConfigDict = dict[str, Union[ConfigValue, ConfigDict]]

# Result types for dictionaries
FeatureImportanceDict = dict[str, float]
FeatureDetailsDict = dict[str, dict[str, float]]
CorrelationMatrixDict = dict[str, dict[str, float]]
StabilityResultDict = dict[str, dict[str, Union[float, bool, str, int]]]

# Generic result dictionary type
ResultDict = dict[str, object]

# ============================================================================
# Optional Dependencies
# ============================================================================


if TYPE_CHECKING:
    from types import ModuleType

shap: ModuleType | None
SHAP_AVAILABLE: bool
_TreeExplainer: type | None
_KernelExplainer: type | None
_LinearExplainer: type | None
_DeepExplainer: type | None
try:
    import shap as _shap

    shap = _shap
    _TreeExplainer = _shap.TreeExplainer
    _KernelExplainer = _shap.KernelExplainer
    _LinearExplainer = _shap.LinearExplainer
    _DeepExplainer = _shap.DeepExplainer
    SHAP_AVAILABLE = True
except (ImportError, OSError):
    shap = None
    _TreeExplainer = None
    _KernelExplainer = None
    _LinearExplainer = None
    _DeepExplainer = None
    SHAP_AVAILABLE = False


def _get_shap_module() -> ModuleType:
    """Get the SHAP module, raising if unavailable."""
    if shap is None:
        raise RuntimeError("SHAP module is not available")
    return shap


SKLEARN_FEATURE_SELECTION_AVAILABLE: bool
SelectKBest: type | None
SelectFromModel: type | None
RFE: type | None
mutual_info_classif: object
mutual_info_regression: object
permutation_importance: object
f_classif: object
f_regression: object
RandomForestClassifier: type | None
RandomForestRegressor: type | None

try:
    from sklearn.ensemble import RandomForestClassifier as _RFClf, RandomForestRegressor as _RFReg
    from sklearn.feature_selection import (
        RFE as _RFE,
        SelectFromModel as SelectFromModelAlias,
        SelectKBest as SelectKBestAlias,
        mutual_info_classif as _mic,
        mutual_info_regression as _mir,
    )
    from sklearn.inspection import permutation_importance as _pi
    from sklearn.metrics import f_classif as _fc, f_regression as _fr

    SelectKBest = SelectKBestAlias
    SelectFromModel = SelectFromModelAlias
    RFE = _RFE
    mutual_info_classif = _mic
    mutual_info_regression = _mir
    permutation_importance = _pi
    f_classif = _fc
    f_regression = _fr
    RandomForestClassifier = _RFClf
    RandomForestRegressor = _RFReg
    SKLEARN_FEATURE_SELECTION_AVAILABLE = True
except (ImportError, OSError):
    SelectKBest = None
    SelectFromModel = None
    RFE = None
    mutual_info_classif = None
    mutual_info_regression = None
    permutation_importance = None
    f_classif = None
    f_regression = None
    RandomForestClassifier = None
    RandomForestRegressor = None
    SKLEARN_FEATURE_SELECTION_AVAILABLE = False


# ============================================================================
# Configuration Loading
# ============================================================================
def load_feature_importance_config(
    config_path: str | None = None,
) -> dict[str, object]:
    """
    Load feature importance configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Try default locations
        possible_paths = [
            Path("config/learning/feature_importance.yaml"),
            Path(__file__).parent.parent.parent.parent.parent / "config/learning/feature_importance.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path and os.path.exists(config_path):
        try:
            import yaml

            with open(config_path) as f:
                config: dict[str, object] = yaml.safe_load(f)
                logger.info(f"Loaded feature importance config from {config_path}")
                return config
        except OSError as e:
            logger.warning(f"Error loading config from {config_path}: {e}")

    return get_default_feature_importance_config()


def get_default_feature_importance_config() -> dict[str, object]:
    """Get default feature importance configuration."""
    return {
        "enabled": True,
        "shap": {
            "enabled": True,
            "sample_size": 100,
            "max_evals": 100,
            "use_background": True,
            "top_n_features": 10,
        },
        "permutation": {
            "enabled": True,
            "n_repeats": 10,
            "n_jobs": -1,
            "random_state": 42,
            "max_samples": 1000,
        },
        "builtin": {"enabled": True, "normalize": True},
        "correlation": {
            "enabled": True,
            "target_correlation_method": "spearman",
            "feature_correlation_method": "pearson",
            "multicollinearity_threshold": 0.9,
            "calculate_mutual_info": True,
        },
        "stability": {
            "enabled": True,
            "window_size": 10,
            "stability_threshold": 0.3,
            "importance_change_threshold": 0.2,
        },
        "selection": {
            "enabled": True,
            "method": "combined",
            "min_importance": 0.01,
            "max_features": "auto",
            "min_features": 5,
        },
        "reporting": {
            "generate_summary": True,
            "generate_recommendations": True,
            "categories": {"critical": 0.1, "important": 0.3, "moderate": 0.6, "low": 1.0},
        },
    }


# ============================================================================
# Data Classes and Enums
# ============================================================================
class ImportanceCategory(Enum):
    """Feature importance category levels."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    MODERATE = "moderate"
    LOW = "low"
    NEGLIGIBLE = "negligible"


@dataclass
class FeatureImportanceResult:
    """Result of feature importance analysis for a single feature."""

    feature_name: str
    importance_score: float
    rank: int
    category: ImportanceCategory
    methods_used: list[str] = field(default_factory=list)
    method_scores: dict[str, float] = field(default_factory=dict)
    stability_score: float | None = None
    correlation_with_target: float | None = None
    recommendation: str | None = None

    def to_dict(
        self,
    ) -> dict[str, str | int | float | list[str] | dict[str, float] | float | None | str | None]:
        """Convert to dictionary."""
        return {
            "feature_name": self.feature_name,
            "importance_score": self.importance_score,
            "rank": self.rank,
            "category": self.category.value,
            "methods_used": self.methods_used,
            "method_scores": self.method_scores,
            "stability_score": self.stability_score,
            "correlation_with_target": self.correlation_with_target,
            "recommendation": self.recommendation,
        }


@dataclass
class ComprehensiveImportanceReport:
    """Comprehensive feature importance report."""

    timestamp: datetime
    n_features: int
    n_samples: int
    feature_results: list[FeatureImportanceResult]
    top_features: list[str]
    low_importance_features: list[str]
    highly_correlated_pairs: list[tuple[str, str, float]]
    recommendations: list[str]
    methods_used: list[str]
    analysis_time_seconds: float

    def to_dict(
        self,
    ) -> dict[str, object]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "n_features": self.n_features,
            "n_samples": self.n_samples,
            "feature_results": [r.to_dict() for r in self.feature_results],
            "top_features": self.top_features,
            "low_importance_features": self.low_importance_features,
            "highly_correlated_pairs": [
                {"feature1": p[0], "feature2": p[1], "correlation": p[2]}
                for p in self.highly_correlated_pairs
            ],
            "recommendations": self.recommendations,
            "methods_used": self.methods_used,
            "analysis_time_seconds": self.analysis_time_seconds,
        }


class SHAPAnalyzer:
    """
    Analizador de importancia de características usando SHAP.

    Importaciones opcionales para SHAP:
        import shap
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

    Soporta:
    - Tree-based models (XGBoost, LightGBM, CatBoost, RandomForest)
    - Neural networks (PyTorch, TensorFlow)
    """

    def __init__(self, config: dict[str, object] | None = None):
        """
        Inicializar analizador SHAP.

        Args:
            config: Configuración
        """
        config = config or {}
        _sample_size = config.get("sample_size", 100)
        self.sample_size = _sample_size if isinstance(_sample_size, int) else 100
        _max_evals = config.get("max_evals", 100)
        self.max_evals = _max_evals if isinstance(_max_evals, int) else 100
        _use_bg = config.get("use_background", True)
        self.use_background = _use_bg if isinstance(_use_bg, bool) else True

        if not SHAP_AVAILABLE:
            logger.warning("SHAP no disponible. Instala con: pip install shap")

    def explain_model(
        self,
        model: ModelType,
        X: FloatArray,
        feature_names: list[str] | None = None,
        model_type: str = "auto",
    ) -> dict[str, str | float | list[str] | dict[str, float] | FloatArray | list[str] | None]:
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
        if not SHAP_AVAILABLE or shap is None:
            return {"error": "SHAP not available", "message": "Install with: pip install shap"}

        try:
            # Determinar tipo de explainer
            explainer = self._create_explainer(model, X, model_type)

            # Calcular SHAP values
            if isinstance(explainer, ShapExplainer):
                shap_values = explainer.shap_values(X[: self.sample_size])
                base_value = (
                    explainer.expected_value if hasattr(explainer, "expected_value") else 0.0
                )
            else:
                return {"error": "Unknown explainer type"}

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
                    name: float(imp) for name, imp in zip(feature_names, feature_importance)
                }
            else:
                importance_dict = {
                    f"feature_{i}": float(imp) for i, imp in enumerate(feature_importance)
                }

            # Estadísticas resumen
            summary_stats = {
                "mean_importance": float(np.mean(feature_importance)),
                "std_importance": float(np.std(feature_importance)),
                "max_importance": float(np.max(feature_importance)),
                "min_importance": float(np.min(feature_importance)),
                "top_features": sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ],
            }

            return {
                "shap_values": shap_values,
                "base_value": float(base_value) if isinstance(base_value, (int, float)) else 0.0,
                "feature_names": feature_names
                or [f"feature_{i}" for i in range(len(feature_importance))],
                "feature_importance": importance_dict,
                "summary_stats": summary_stats,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculando SHAP values: {e}", exc_info=True)
            return {"error": str(e), "error_type": type(e).__name__}

    def _create_explainer(self, model: ModelType, X: FloatArray, model_type: str) -> object:
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
        background = X[: min(50, len(X))] if self.use_background and len(X) > 50 else X

        if model_type == "tree":
            # Tree-based models (XGBoost, LightGBM, CatBoost, RandomForest)
            if _TreeExplainer is None:
                raise RuntimeError("SHAP TreeExplainer not available")
            return _TreeExplainer(model)
        elif model_type == "linear":
            if _LinearExplainer is None:
                raise RuntimeError("SHAP LinearExplainer not available")
            return _LinearExplainer(model, background)
        elif model_type == "neural":
            # Neural networks
            try:
                # Intentar DeepExplainer primero
                if _DeepExplainer is None:
                    raise RuntimeError("SHAP DeepExplainer not available")
                return _DeepExplainer(model, background)
            except (ValueError, TypeError, KeyError, AttributeError):
                # Fallback a KernelExplainer
                if _KernelExplainer is None:
                    raise RuntimeError("SHAP KernelExplainer not available") from None
                predict_fn = model.predict if hasattr(model, "predict") else model
                return _KernelExplainer(predict_fn, background)
        else:
            # Fallback genérico
            if _KernelExplainer is None:
                raise RuntimeError("SHAP KernelExplainer not available")
            predict_fn = model.predict if hasattr(model, "predict") else model
            return _KernelExplainer(predict_fn, background)

    def _detect_model_type(self, model: ModelType) -> str:
        """
        Detectar tipo de modelo automáticamente.

        Returns:
            Tipo de modelo: 'tree', 'linear', 'neural', 'generic'
        """
        model_type = str(type(model)).lower()

        if any(
            x in model_type
            for x in ["xgboost", "lightgbm", "catboost", "randomforest", "gradientboosting"]
        ):
            return "tree"
        elif any(x in model_type for x in ["linear", "logistic", "ridge", "lasso"]):
            return "linear"
        elif any(x in model_type for x in ["neural", "nn", "module", "sequential"]):
            return "neural"
        else:
            return "generic"

    def explain_prediction(
        self,
        model: ModelType,
        X: FloatArray,
        instance_idx: int,
        feature_names: list[str] | None = None,
    ) -> dict[str, str | dict[str, float] | list[tuple[str, float]]]:
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
        if not SHAP_AVAILABLE or shap is None:
            return {"error": "SHAP not available"}

        try:
            explainer = self._create_explainer(model, X, "auto")

            # Calcular SHAP values para esta instancia
            instance = X[instance_idx : instance_idx + 1]

            if isinstance(explainer, ShapExplainer):
                shap_values = explainer.shap_values(instance)
            else:
                return {"error": "Unknown explainer type"}

            # Si es lista (multi-class), usar la clase positiva
            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

            shap_values = shap_values.flatten()

            # Crear explicación
            if feature_names and len(feature_names) == len(shap_values):
                explanation = {
                    name: float(value) for name, value in zip(feature_names, shap_values)
                }
            else:
                explanation = {f"feature_{i}": float(value) for i, value in enumerate(shap_values)}

            # Ordenar por valor absoluto
            sorted_explanation = sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)

            return {
                "explanation": explanation,
                "sorted_explanation": sorted_explanation,
                "top_contributors": sorted_explanation[:5],
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error explicando predicción: {e}", exc_info=True)
            return {"error": str(e)}


class AttentionWeightsAnalyzer:
    """
    Analizador de attention weights para modelos Transformer.

    Extrae y analiza los pesos de atención para entender qué partes
    de la secuencia temporal son más importantes.
    """

    def __init__(self, config: dict[str, str | bool] | None = None):
        """
        Inicializar analizador de attention weights.

        Args:
            config: Configuración
        """
        config = config or {}
        self.aggregation_method = config.get("aggregation_method", "mean")  # mean, max, first
        self.normalize = config.get("normalize", True)

    def extract_attention_weights(
        self, model: ModelType, sequence: FloatArray, layer_idx: int | None = None
    ) -> dict[str, str | FloatArray | None | FloatArray | dict[int, float] | list[int] | int]:
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
                return {"error": "Model is not a PyTorch nn.Module"}

            model.eval()

            # Convertir a tensor
            if isinstance(sequence, np.ndarray):
                sequence_tensor = torch.FloatTensor(sequence)
            else:
                sequence_tensor = sequence

            # Obtener attention weights - returns None or np.ndarray
            # This is a placeholder implementation that will be extended
            attention_weights = self._get_attention_from_model(model, sequence_tensor, layer_idx)

            # Check if attention_weights is None before proceeding
            if attention_weights is None:
                return {
                    "error": "Could not extract attention weights from model",
                    "attention_weights": None,
                }

            # Ensure attention_weights is subscriptable (is an array)
            if not hasattr(attention_weights, "__getitem__"):
                return {
                    "error": "attention_weights is not subscriptable",
                    "attention_weights": attention_weights,
                }

            # We've verified attention_weights has __getitem__ above via hasattr check
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
            attention_by_position = {i: float(aggregated[i]) for i in range(seq_len)}

            # Top posiciones importantes
            sorted_positions = sorted(
                attention_by_position.items(), key=lambda x: x[1], reverse=True
            )
            top_positions = [pos for pos, _ in sorted_positions[:5]]

            return {
                "attention_weights": attention_weights,
                "aggregated_attention": aggregated,
                "attention_by_position": attention_by_position,
                "top_important_positions": top_positions,
                "sequence_length": seq_len,
                "aggregation_method": self.aggregation_method,
            }

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error extrayendo attention weights: {e}", exc_info=True)
            return {"error": str(e)}

    def _get_attention_from_model(
        self, model: ModelType, sequence: FloatArray | object, layer_idx: int | None = None
    ) -> FloatArray | None:
        """
        Extraer attention weights del modelo.

        Args:
            model: Modelo PyTorch
            sequence: Secuencia de entrada
            layer_idx: Índice de capa específica

        Returns:
            Attention weights como numpy array, or None if not available
        """
        try:
            import torch
            import torch.nn as nn

            # Buscar TransformerEncoderLayer en el modelo
            # Hook para capturar attention
            def attention_hook(module, module_input, output):
                # En TransformerEncoderLayer, el output es (output, attention_weights) si return_attn=True
                # O podemos usar register_forward_hook y buscar el atributo
                if hasattr(module, "self_attn"):
                    # Intentar obtener attention weights
                    # Esto requiere que el modelo tenga return_attention=True
                    pass

            # Buscar capas de transformer
            if not isinstance(model, NamedModulesModel):
                return None
            for name, module in model.named_modules():
                if isinstance(module, nn.TransformerEncoderLayer) and (
                    layer_idx is None or name.endswith(f"[{layer_idx}]")
                ):
                    # Registrar hook
                    hook = module.register_forward_hook(attention_hook)
                    # Forward pass
                    with torch.no_grad():
                        module(sequence)
                    hook.remove()

            # Alternativa: usar forward hook global
            # Por ahora, retornar None y usar método alternativo
            # En producción, esto requeriría modificar el modelo para retornar attention

            # Placeholder implementation - requires model-specific implementation
            return None

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
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

    def __init__(self, config: dict[str, object] | None = None):
        """
        Inicializar selector de features.

        Args:
            config: Configuración
        """
        config = config or {}
        _method = config.get("method", "model_based")
        self.method = _method if isinstance(_method, str) else "model_based"
        _nf = config.get("n_features", "auto")
        self.n_features: str | int = _nf if isinstance(_nf, (str, int)) else "auto"
        _it = config.get("importance_threshold", 0.01)
        self.importance_threshold = float(_it) if isinstance(_it, (int, float)) else 0.01
        _cv = config.get("use_cross_validation", True)
        self.use_cross_validation = _cv if isinstance(_cv, bool) else True

        if not SKLEARN_FEATURE_SELECTION_AVAILABLE:
            logger.warning("sklearn feature selection no disponible.")

    def select_features(
        self,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str] | None = None,
        model: ModelType | None = None,
        task_type: str = "classification",  # classification o regression
    ) -> dict[str, str | list[int] | list[str] | dict[str, float] | int | SelectorType]:
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
                "error": "sklearn feature selection not available",
                "selected_features": list(range(X.shape[1])),  # Seleccionar todas
                "selected_feature_names": feature_names
                or [f"feature_{i}" for i in range(X.shape[1])],
            }

        try:
            # Determinar número de features
            if self.n_features == "auto":
                # Seleccionar top 50% o mínimo 10
                n_features = max(10, X.shape[1] // 2)
            else:
                n_features = min(self.n_features, X.shape[1])

            feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]

            if self.method == "univariate":
                selector, scores = self._univariate_selection(X, y, n_features, task_type)
            elif self.method == "rfe":
                selector, scores = self._rfe_selection(X, y, n_features, model, task_type)
            elif self.method == "model_based":
                selector, scores = self._model_based_selection(X, y, model, task_type)
            else:
                # Default: usar todas
                return {
                    "selected_features": list(range(X.shape[1])),
                    "selected_feature_names": feature_names,
                    "feature_scores": {},
                    "n_selected": X.shape[1],
                    "selection_method": "none",
                }

            # Obtener índices seleccionados
            if hasattr(selector, "get_support"):
                selected_indices = selector.get_support(indices=True)
            elif hasattr(selector, "support_"):
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
                "selected_features": (
                    selected_indices.tolist()
                    if isinstance(selected_indices, np.ndarray)
                    else selected_indices
                ),
                "selected_feature_names": selected_feature_names,
                "feature_scores": feature_scores,
                "n_selected": len(selected_indices),
                "selection_method": self.method,
                "selector": selector,  # Para uso futuro
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error seleccionando features: {e}", exc_info=True)
            return {
                "error": str(e),
                "selected_features": list(range(X.shape[1])),
                "selected_feature_names": feature_names
                or [f"feature_{i}" for i in range(X.shape[1])],
            }

    def _univariate_selection(
        self, X: FloatArray, y: FloatArray, n_features: int, task_type: str
    ) -> tuple[SelectorType, FloatArray]:
        """Selección univariante usando SelectKBest."""
        if SelectKBest is None or f_classif is None or f_regression is None:
            raise RuntimeError("sklearn feature selection not available")

        score_func = f_classif if task_type == "classification" else f_regression

        selector = SelectKBest(score_func=score_func, k=n_features)
        selector.fit(X, y)

        scores = selector.scores_
        return selector, scores

    def _rfe_selection(
        self,
        X: FloatArray,
        y: FloatArray,
        n_features: int,
        model: ModelType | None,
        task_type: str,
    ) -> tuple[SelectorType, FloatArray | None]:
        """Recursive Feature Elimination."""
        if RFE is None or RandomForestClassifier is None or RandomForestRegressor is None:
            raise RuntimeError("sklearn not available for RFE selection")

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
        self, X: FloatArray, y: FloatArray, model: ModelType | None, task_type: str
    ) -> tuple[SelectorType, FloatArray | None]:
        """Selección basada en importancia del modelo."""
        if (
            SelectFromModel is None
            or RandomForestClassifier is None
            or RandomForestRegressor is None
        ):
            raise RuntimeError("sklearn not available for model-based selection")

        # Crear modelo base si no se proporciona
        if model is None:
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            if hasattr(model, "fit"):
                model.fit(X, y)

        # Si el modelo ya está entrenado, usar directamente
        if not hasattr(model, "feature_importances_"):
            # Entrenar si no está entrenado
            if not hasattr(model, "n_estimators"):
                if task_type == "classification":
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                else:
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
            if hasattr(model, "fit"):
                model.fit(X, y)

        # Usar SelectFromModel con threshold
        selector = SelectFromModel(estimator=model, threshold=self.importance_threshold)
        selector.fit(X, y)

        # Obtener scores (importancia)
        scores = model.feature_importances_ if hasattr(model, "feature_importances_") else None

        return selector, scores


class FeatureImportanceAnalyzer:
    """
    Analizador unificado de importancia de features.

    Combina SHAP, attention weights y feature selection.
    """

    def __init__(
        self,
        config: dict[str, object] | None = None,
    ):
        """
        Inicializar analizador unificado.

        Args:
            config: Configuración
        """
        config = config or {}
        _shap_cfg = config.get("shap_config", {})
        self.shap_analyzer = SHAPAnalyzer(_shap_cfg if isinstance(_shap_cfg, dict) else None)
        _attn_cfg = config.get("attention_config", {})
        self.attention_analyzer = AttentionWeightsAnalyzer(
            _attn_cfg if isinstance(_attn_cfg, dict) else None
        )
        _fs_cfg = config.get("feature_selector_config", {})
        self.feature_selector = FeatureSelector(_fs_cfg if isinstance(_fs_cfg, dict) else None)

    def analyze(
        self,
        model: ModelType,
        X: FloatArray,
        y: FloatArray | None = None,
        feature_names: list[str] | None = None,
        model_type: str = "auto",
        include_shap: bool = True,
        include_attention: bool = False,
        include_selection: bool = False,
    ) -> dict[str, list[str] | dict[str, object] | None | dict[str, float]]:
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
        results: dict[str, list[str] | dict[str, object] | dict[str, float] | None] = {
            "feature_names": feature_names or [f"feature_{i}" for i in range(X.shape[-1])],
            "shap_analysis": None,
            "attention_analysis": None,
            "feature_selection": None,
            "combined_importance": {},
        }

        # SHAP analysis
        if include_shap:
            try:
                shap_results = self.shap_analyzer.explain_model(model, X, feature_names, model_type)
                results["shap_analysis"] = shap_results
                if "feature_importance" in shap_results:
                    _ci = results["combined_importance"]
                    if isinstance(_ci, dict):
                        _fi = shap_results["feature_importance"]
                        if isinstance(_fi, dict):
                            _ci["shap"] = _fi
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.warning(f"SHAP analysis failed: {e}")

        # Attention analysis (para transformers)
        if include_attention:
            try:
                attention_results = self.attention_analyzer.extract_attention_weights(model, X)
                results["attention_analysis"] = attention_results
            except (RuntimeError, ValueError, TypeError, KeyError) as e:
                logger.warning(f"Attention analysis failed: {e}")

        # Feature selection
        if include_selection and y is not None:
            try:
                selection_results = self.feature_selector.select_features(
                    X.reshape(len(X), -1) if X.ndim > 2 else X, y, feature_names, model
                )
                results["feature_selection"] = selection_results
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Feature selection failed: {e}")

        # Combinar importancias
        _ci_ref = results["combined_importance"]
        if isinstance(_ci_ref, dict) and _ci_ref:
            # Promediar diferentes métodos de importancia
            all_importances: list[dict[str, float]] = []
            for _method, importance_dict in _ci_ref.items():
                if isinstance(importance_dict, dict):
                    all_importances.append(importance_dict)

            # Promediar
            combined: dict[str, list[float]] = {}
            for imp_dict in all_importances:
                for name, value in imp_dict.items():
                    if not isinstance(value, (int, float)):
                        continue
                    if name not in combined:
                        combined[name] = []
                    combined[name].append(float(value))

            # Calcular promedio
            final_combined = {name: float(np.mean(values)) for name, values in combined.items()}
            results["combined_importance"] = final_combined

        return results


# ============================================================================
# Permutation Importance Analyzer [TASK-4.2-FEATURE-IMPORTANCE]
# ============================================================================
class PermutationImportanceAnalyzer:
    """
    Model-agnostic permutation importance analyzer.

    Measures feature importance by shuffling each feature and measuring
    the decrease in model performance. Works with any model.
    """

    def __init__(self, config: dict[str, object] | None = None):
        """
        Initialize permutation importance analyzer.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        _n_repeats = config.get("n_repeats", 10)
        self.n_repeats = _n_repeats if isinstance(_n_repeats, int) else 10
        _n_jobs = config.get("n_jobs", -1)
        self.n_jobs = _n_jobs if isinstance(_n_jobs, int) else -1
        _rs = config.get("random_state", 42)
        self.random_state = _rs if isinstance(_rs, int) else 42
        _ms = config.get("max_samples", 1000)
        self.max_samples = _ms if isinstance(_ms, int) else 1000
        _sc = config.get("scoring", "auto")
        self.scoring = _sc if isinstance(_sc, str) else "auto"

    def calculate_importance(
        self,
        model: ModelType,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str] | None = None,
        scoring: str | None = None,
    ) -> dict[
        str,
        str
        | dict[str, float]
        | dict[str, dict[str, float]]
        | list[tuple[str, float]]
        | list[str]
        | int,
    ]:
        """
        Calculate permutation importance for all features.

        Args:
            model: Trained model with predict method
            X: Feature data (n_samples, n_features)
            y: Target data (n_samples,)
            feature_names: Optional feature names
            scoring: Scoring metric (auto, accuracy, f1, r2, neg_mse)

        Returns:
            Dictionary with importance results
        """
        try:
            # Subsample if dataset is too large (with isolated random state)
            if len(X) > self.max_samples:
                rng = np.random.default_rng(self.random_state)
                indices = rng.choice(len(X), self.max_samples, replace=False)
                X_sample = X[indices]
                y_sample = y[indices]
            else:
                X_sample = X
                y_sample = y

            # Determine scoring
            if scoring is None:
                scoring = self.scoring
            if scoring == "auto":
                # Detect task type
                unique_values = len(np.unique(y_sample))
                scoring = "accuracy" if unique_values <= 10 else "r2"

            # Calculate permutation importance
            if not callable(permutation_importance):
                return self._fallback_permutation_importance(
                    model, X_sample, y_sample, feature_names
                )

            result = permutation_importance(
                model,
                X_sample,
                y_sample,
                n_repeats=self.n_repeats,
                n_jobs=self.n_jobs,
                random_state=self.random_state,
                scoring=scoring,
            )

            # Extract importances
            importances_mean = result.importances_mean
            importances_std = result.importances_std

            # Normalize to sum to 1
            if np.sum(np.abs(importances_mean)) > 0:
                importances_normalized = np.abs(importances_mean) / np.sum(np.abs(importances_mean))
            else:
                importances_normalized = np.zeros_like(importances_mean)

            # Create feature importance dict
            feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]
            importance_dict = {}
            importance_details = {}

            for i, name in enumerate(feature_names):
                importance_dict[name] = float(importances_normalized[i])
                importance_details[name] = {
                    "mean": float(importances_mean[i]),
                    "std": float(importances_std[i]),
                    "normalized": float(importances_normalized[i]),
                }

            # Rank features
            ranked_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

            return {
                "feature_importance": importance_dict,
                "feature_details": importance_details,
                "ranked_features": ranked_features,
                "top_features": [f[0] for f in ranked_features[:10]],
                "scoring": scoring,
                "n_repeats": self.n_repeats,
                "n_samples_used": len(X_sample),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating permutation importance: {e}")
            return {"error": str(e)}

    def _fallback_permutation_importance(
        self,
        model: ModelType,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str] | None = None,
    ) -> dict[str, str | dict[str, float] | list[tuple[str, float]]]:
        """
        Fallback implementation without sklearn.inspection.

        Args:
            model: Trained model
            X: Feature data
            y: Target data
            feature_names: Feature names

        Returns:
            Dictionary with importance results
        """
        try:
            n_features = X.shape[1]
            feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]

            # Require model.predict
            if not isinstance(model, Predictor):
                return {"error": "Model does not have predict method"}

            # Get baseline score
            baseline_pred = model.predict(X)
            if hasattr(y, "dtype") and np.issubdtype(y.dtype, np.floating):
                # Regression
                baseline_score = -np.mean((y - baseline_pred) ** 2)
            else:
                # Classification
                baseline_score = np.mean(baseline_pred == y)

            # Calculate importance for each feature (with isolated random state)
            importances: list[float] = []
            rng = np.random.default_rng(self.random_state)

            for i in range(n_features):
                feat_scores: list[float] = []
                for _ in range(self.n_repeats):
                    X_permuted = X.copy()
                    rng.shuffle(X_permuted[:, i])
                    permuted_pred = model.predict(X_permuted)

                    if hasattr(y, "dtype") and np.issubdtype(y.dtype, np.floating):
                        score = -np.mean((y - permuted_pred) ** 2)
                    else:
                        score = np.mean(permuted_pred == y)
                    feat_scores.append(float(baseline_score - score))

                importances.append(float(np.mean(feat_scores)))

            # Normalize
            importances = np.array(importances)
            if np.sum(np.abs(importances)) > 0:
                importances_normalized = np.abs(importances) / np.sum(np.abs(importances))
            else:
                importances_normalized = np.zeros_like(importances)

            importance_dict = {
                name: float(imp) for name, imp in zip(feature_names, importances_normalized)
            }

            return {
                "feature_importance": importance_dict,
                "ranked_features": sorted(
                    importance_dict.items(), key=lambda x: x[1], reverse=True
                ),
                "method": "fallback",
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error in fallback permutation importance: {e}")
            return {"error": str(e)}


# ============================================================================
# Built-in Model Importance Analyzer [TASK-4.2-FEATURE-IMPORTANCE]
# ============================================================================
class BuiltInImportanceAnalyzer:
    """
    Extract built-in feature importance from tree-based models.

    Works with models that have feature_importances_ attribute:
    - RandomForest
    - GradientBoosting
    - XGBoost
    - LightGBM
    - CatBoost
    """

    def __init__(self, config: dict[str, object] | None = None):
        """
        Initialize built-in importance analyzer.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        _norm = config.get("normalize", True)
        self.normalize = _norm if isinstance(_norm, bool) else True

    def calculate_importance(
        self,
        model: ModelType,
        feature_names: list[str] | None = None,
    ) -> dict[str, str | bool | dict[str, float] | list[tuple[str, float]] | list[str]]:
        """
        Extract feature importance from model.

        Args:
            model: Trained model with feature_importances_ attribute
            feature_names: Optional feature names

        Returns:
            Dictionary with importance results
        """
        try:
            # Check if model has feature_importances_
            if not hasattr(model, "feature_importances_"):
                return {
                    "error": "Model does not have feature_importances_ attribute",
                    "supported": False,
                }

            importances = model.feature_importances_

            # Normalize if requested
            if self.normalize and np.sum(importances) > 0:
                importances = importances / np.sum(importances)

            # Get feature names
            n_features = len(importances)
            if feature_names is None:
                if hasattr(model, "feature_names_in_"):
                    feature_names = list(model.feature_names_in_)
                else:
                    feature_names = [f"feature_{i}" for i in range(n_features)]

            # Create importance dict
            importance_dict = {name: float(imp) for name, imp in zip(feature_names, importances)}

            # Rank features
            ranked_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

            # Get model type
            model_type = type(model).__name__

            return {
                "feature_importance": importance_dict,
                "ranked_features": ranked_features,
                "top_features": [f[0] for f in ranked_features[:10]],
                "model_type": model_type,
                "normalized": self.normalize,
                "supported": True,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error extracting built-in importance: {e}")
            return {"error": str(e), "supported": False}

    def get_importance_type(self, model: ModelType) -> str:
        """
        Determine the type of importance for this model.

        Args:
            model: Model to analyze

        Returns:
            Description of importance type
        """
        model_type = type(model).__name__.lower()

        if "randomforest" in model_type:
            return "Mean Decrease in Impurity (Gini importance)"
        elif "gradientboosting" in model_type:
            return "Mean Decrease in Impurity"
        elif "xgb" in model_type:
            return "Gain (average gain when feature is used)"
        elif "lgb" in model_type or "lightgbm" in model_type:
            return "Split (number of times feature is used)"
        elif "catboost" in model_type:
            return "Prediction Values Change"
        else:
            return "Model-specific importance"


# ============================================================================
# Correlation Analyzer [TASK-4.2-FEATURE-IMPORTANCE]
# ============================================================================
class CorrelationAnalyzer:
    """
    Analyze feature correlations for importance insights.

    Includes:
    - Feature-target correlation
    - Feature-feature correlation (multicollinearity)
    - Mutual information
    """

    def __init__(self, config: dict[str, object] | None = None):
        """
        Initialize correlation analyzer.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        _tm = config.get("target_correlation_method", "spearman")
        self.target_method = _tm if isinstance(_tm, str) else "spearman"
        _fm = config.get("feature_correlation_method", "pearson")
        self.feature_method = _fm if isinstance(_fm, str) else "pearson"
        _mt = config.get("multicollinearity_threshold", 0.9)
        self.multicollinearity_threshold = float(_mt) if isinstance(_mt, (int, float)) else 0.9
        _cmi = config.get("calculate_mutual_info", True)
        self.calculate_mi = _cmi if isinstance(_cmi, bool) else True
        _nn = config.get("n_neighbors", 5)
        self.n_neighbors = _nn if isinstance(_nn, int) else 5

    def analyze(
        self,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str] | None = None,
    ) -> dict[
        str,
        str
        | dict[str, float]
        | list[str]
        | list[tuple[str, str, float]]
        | list[tuple[str, float]]
        | dict[str, dict[str, float]]
        | None,
    ]:
        """
        Perform comprehensive correlation analysis.

        Args:
            X: Feature data (n_samples, n_features)
            y: Target data (n_samples,)
            feature_names: Optional feature names

        Returns:
            Dictionary with correlation analysis results
        """
        n_features = X.shape[1]
        feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]

        results: dict[
            str,
            str
            | dict[str, float]
            | list[str]
            | list[tuple[str, str, float]]
            | list[tuple[str, float]]
            | dict[str, dict[str, float]]
            | None,
        ] = {
            "target_correlations": {},
            "highly_correlated_pairs": [],
            "multicollinearity_warnings": [],
            "mutual_information": {},
            "feature_correlation_matrix": None,
        }

        try:
            # Target correlations
            results["target_correlations"] = self._calculate_target_correlations(
                X, y, feature_names
            )

            # Feature-feature correlations
            corr_matrix, highly_correlated = self._calculate_feature_correlations(X, feature_names)
            results["feature_correlation_matrix"] = corr_matrix
            results["highly_correlated_pairs"] = highly_correlated

            # Multicollinearity warnings
            results["multicollinearity_warnings"] = [
                f"Features {pair[0]} and {pair[1]} are highly correlated ({pair[2]:.3f})"
                for pair in highly_correlated
            ]

            # Mutual information
            if self.calculate_mi:
                results["mutual_information"] = self._calculate_mutual_information(
                    X, y, feature_names
                )

            # Rank features by absolute correlation
            _tc = results["target_correlations"]
            if isinstance(_tc, dict):
                ranked_by_correlation = sorted(
                    _tc.items(),
                    key=lambda x: abs(x[1]),
                    reverse=True,
                )
                results["ranked_by_correlation"] = ranked_by_correlation

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error in correlation analysis: {e}")
            results["error"] = str(e)

        return results

    def _calculate_target_correlations(
        self,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str],
    ) -> dict[str, float]:
        """Calculate correlations between features and target."""
        from scipy import stats

        correlations = {}

        for i, name in enumerate(feature_names):
            try:
                if self.target_method == "spearman":
                    corr, _ = stats.spearmanr(X[:, i], y)
                elif self.target_method == "kendall":
                    corr, _ = stats.kendalltau(X[:, i], y)
                else:  # pearson
                    corr, _ = stats.pearsonr(X[:, i], y)

                correlations[name] = float(corr) if not np.isnan(corr) else 0.0
            except (ValueError, TypeError, KeyError, AttributeError):
                correlations[name] = 0.0

        return correlations

    def _calculate_feature_correlations(
        self,
        X: FloatArray,
        feature_names: list[str],
    ) -> tuple[dict[str, dict[str, float]], list[tuple[str, str, float]]]:
        """Calculate feature-feature correlations and identify highly correlated pairs."""
        X.shape[1]
        corr_matrix: dict[str, dict[str, float]] = {}
        highly_correlated: list[tuple[str, str, float]] = []

        # Calculate correlation matrix
        if self.feature_method == "spearman":
            from scipy import stats

            corr_values, _ = stats.spearmanr(X)
        else:
            corr_values = np.corrcoef(X.T)

        # Handle 1D case
        if corr_values.ndim == 0:
            corr_values = np.array([[1.0]])
        elif corr_values.ndim == 1:
            corr_values = corr_values.reshape(1, -1)

        # Build matrix dict and find highly correlated pairs
        for i, name_i in enumerate(feature_names):
            corr_matrix[name_i] = {}
            for j, name_j in enumerate(feature_names):
                if i < len(corr_values) and j < len(corr_values[0]):
                    corr = float(corr_values[i, j])
                    corr_matrix[name_i][name_j] = corr

                    # Check for high correlation (excluding self-correlation)
                    if i < j and abs(corr) > self.multicollinearity_threshold:
                        highly_correlated.append((name_i, name_j, corr))

        return corr_matrix, highly_correlated

    def _calculate_mutual_information(
        self,
        X: FloatArray,
        y: FloatArray,
        feature_names: list[str],
    ) -> dict[str, float]:
        """Calculate mutual information between features and target."""
        try:
            from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

            # Determine if classification or regression
            unique_values = len(np.unique(y))
            if unique_values <= 10:
                mi_scores = mutual_info_classif(X, y, n_neighbors=self.n_neighbors, random_state=42)
            else:
                mi_scores = mutual_info_regression(
                    X, y, n_neighbors=self.n_neighbors, random_state=42
                )

            return {name: float(score) for name, score in zip(feature_names, mi_scores)}

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"Could not calculate mutual information: {e}")
            return {}


# ============================================================================
# Feature Stability Tracker [TASK-4.2-FEATURE-IMPORTANCE]
# ============================================================================
class FeatureStabilityTracker:
    """
    Track feature importance stability over time.

    Monitors:
    - Importance changes between training runs
    - Rank stability
    - Trend detection (increasing/decreasing importance)
    """

    def __init__(self, config: dict[str, object] | None = None):
        """
        Initialize stability tracker.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        _ws = config.get("window_size", 10)
        self.window_size = _ws if isinstance(_ws, int) else 10
        _st = config.get("stability_threshold", 0.3)
        self.stability_threshold = float(_st) if isinstance(_st, (int, float)) else 0.3
        _ict = config.get("importance_change_threshold", 0.2)
        self.importance_change_threshold = float(_ict) if isinstance(_ict, (int, float)) else 0.2

        # History storage
        self._importance_history: list[dict[str, float]] = []
        self._rank_history: list[dict[str, int]] = []
        self._timestamps: list[datetime] = []

    def record_importance(
        self,
        importance_dict: dict[str, float],
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record feature importance snapshot.

        Args:
            importance_dict: Feature importance dictionary
            timestamp: Optional timestamp
        """
        timestamp = timestamp or datetime.now()

        # Calculate ranks
        ranked = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        rank_dict = {name: i + 1 for i, (name, _) in enumerate(ranked)}

        # Add to history
        self._importance_history.append(importance_dict.copy())
        self._rank_history.append(rank_dict)
        self._timestamps.append(timestamp)

        # Maintain window size
        if len(self._importance_history) > self.window_size:
            self._importance_history.pop(0)
            self._rank_history.pop(0)
            self._timestamps.pop(0)

    def analyze_stability(
        self,
    ) -> dict[str, str | int | dict[str, dict[str, float | bool | str | int]] | list[str]]:
        """
        Analyze feature importance stability.

        Returns:
            Dictionary with stability analysis results
        """
        if len(self._importance_history) < 2:
            return {
                "error": "Not enough history for stability analysis",
                "n_snapshots": len(self._importance_history),
            }

        # Get all feature names
        all_features: set[str] = set()
        for imp_dict in self._importance_history:
            all_features.update(imp_dict.keys())

        stability_results: dict[str, dict[str, float | bool | str | int]] = {}

        for feature in all_features:
            # Get importance history for this feature
            importances = [h.get(feature, 0.0) for h in self._importance_history]
            ranks = [h.get(feature, len(all_features)) for h in self._rank_history]

            # Calculate stability metrics
            importance_std = np.std(importances)
            importance_mean = np.mean(importances)
            importance_cv = importance_std / (importance_mean + 1e-8)

            rank_std = np.std(ranks)
            rank_mean = np.mean(ranks)

            # Detect trend
            trend = self._detect_trend(importances)

            # Calculate stability score (lower is more stable)
            stability_score = importance_cv + (rank_std / len(all_features))

            # Determine if feature is stable
            is_stable = stability_score < self.stability_threshold

            stability_results[feature] = {
                "importance_mean": float(importance_mean),
                "importance_std": float(importance_std),
                "importance_cv": float(importance_cv),
                "rank_mean": float(rank_mean),
                "rank_std": float(rank_std),
                "stability_score": float(stability_score),
                "is_stable": is_stable,
                "trend": trend,
                "n_observations": len(importances),
            }

        # Identify unstable features
        unstable_features = [f for f, stats in stability_results.items() if not stats["is_stable"]]

        # Identify trending features
        trending_up = [
            f for f, stats in stability_results.items() if stats["trend"] == "increasing"
        ]
        trending_down = [
            f for f, stats in stability_results.items() if stats["trend"] == "decreasing"
        ]

        return {
            "feature_stability": stability_results,
            "unstable_features": unstable_features,
            "trending_up": trending_up,
            "trending_down": trending_down,
            "n_snapshots": len(self._importance_history),
            "window_size": self.window_size,
        }

    def _detect_trend(self, values: list[float]) -> str:
        """
        Detect trend in importance values.

        Args:
            values: List of importance values

        Returns:
            Trend direction: 'increasing', 'decreasing', or 'stable'
        """
        if len(values) < 3:
            return "insufficient_data"

        try:
            from scipy import stats

            x = np.arange(len(values))
            slope, _, r_value, _, _ = stats.linregress(x, values)

            # Significant trend if R² > 0.5 and slope is meaningful
            if r_value**2 > 0.5:
                if slope > self.importance_change_threshold / len(values):
                    return "increasing"
                elif slope < -self.importance_change_threshold / len(values):
                    return "decreasing"

            return "stable"

        except (RuntimeError, ValueError, TypeError, KeyError):
            return "unknown"

    def get_importance_change(self) -> dict[str, float]:
        """
        Get importance change from first to last snapshot.

        Returns:
            Dictionary with importance changes per feature
        """
        if len(self._importance_history) < 2:
            return {}

        first = self._importance_history[0]
        last = self._importance_history[-1]

        changes = {}
        all_features = set(first.keys()) | set(last.keys())

        for feature in all_features:
            first_imp = first.get(feature, 0.0)
            last_imp = last.get(feature, 0.0)
            changes[feature] = last_imp - first_imp

        return changes

    def reset(self) -> None:
        """Reset history."""
        self._importance_history.clear()
        self._rank_history.clear()
        self._timestamps.clear()


# ============================================================================
# Comprehensive Feature Analyzer [TASK-4.2-FEATURE-IMPORTANCE]
# ============================================================================
class ComprehensiveFeatureAnalyzer:
    """
    Comprehensive feature importance analyzer combining all methods.

    Integrates:
    - SHAP analysis
    - Permutation importance
    - Built-in model importance
    - Correlation analysis
    - Feature stability tracking
    - Feature selection recommendations
    """

    def __init__(
        self,
        config: (
            dict[str, str | int | float | bool | dict[str, str | int | float | bool]] | None
        ) = None,
    ):
        """
        Initialize comprehensive analyzer.

        Args:
            config: Configuration dictionary (loaded from YAML if not provided)
        """
        self.config: dict[str, object] = config or load_feature_importance_config()
        self.enabled = self.config.get("enabled", True)

        # Initialize analyzers with safe sub-config extraction
        _shap_cfg = self.config.get("shap", {})
        self.shap_analyzer = SHAPAnalyzer(_shap_cfg if isinstance(_shap_cfg, dict) else None)
        _perm_cfg = self.config.get("permutation", {})
        self.permutation_analyzer = PermutationImportanceAnalyzer(
            _perm_cfg if isinstance(_perm_cfg, dict) else None
        )
        _builtin_cfg = self.config.get("builtin", {})
        self.builtin_analyzer = BuiltInImportanceAnalyzer(
            _builtin_cfg if isinstance(_builtin_cfg, dict) else None
        )
        _corr_cfg = self.config.get("correlation", {})
        self.correlation_analyzer = CorrelationAnalyzer(
            _corr_cfg if isinstance(_corr_cfg, dict) else None
        )
        _stab_cfg = self.config.get("stability", {})
        self.stability_tracker = FeatureStabilityTracker(
            _stab_cfg if isinstance(_stab_cfg, dict) else None
        )
        _sel_cfg = self.config.get("selection", {})
        self.feature_selector = FeatureSelector(_sel_cfg if isinstance(_sel_cfg, dict) else None)

        # Category thresholds
        _reporting = self.config.get("reporting", {})
        _reporting_dict = _reporting if isinstance(_reporting, dict) else {}
        _categories = _reporting_dict.get(
            "categories", {"critical": 0.1, "important": 0.3, "moderate": 0.6, "low": 1.0}
        )
        self.category_thresholds = (
            _categories
            if isinstance(_categories, dict)
            else {"critical": 0.1, "important": 0.3, "moderate": 0.6, "low": 1.0}
        )

    def analyze(
        self,
        model: ModelType,
        X: FloatArray,
        y: FloatArray | None = None,
        feature_names: list[str] | None = None,
        include_shap: bool = True,
        include_permutation: bool = True,
        include_builtin: bool = True,
        include_correlation: bool = True,
        include_selection: bool = False,
    ) -> ComprehensiveImportanceReport:
        """
        Perform comprehensive feature importance analysis.

        Args:
            model: Trained model
            X: Feature data
            y: Target data (required for permutation, correlation, selection)
            feature_names: Optional feature names
            include_shap: Include SHAP analysis
            include_permutation: Include permutation importance
            include_builtin: Include built-in model importance
            include_correlation: Include correlation analysis
            include_selection: Include feature selection

        Returns:
            ComprehensiveImportanceReport with all analysis results
        """
        import time

        start_time = time.time()

        n_features = X.shape[1]
        n_samples = X.shape[0]
        feature_names = feature_names or [f"feature_{i}" for i in range(n_features)]

        # Collect importance from all methods
        all_importances: dict[str, dict[str, float]] = {}
        methods_used: list[str] = []

        # SHAP analysis
        _shap_sub = self.config.get("shap", {})
        _shap_enabled = (
            (isinstance(_shap_sub, dict) and _shap_sub.get("enabled", True))
            if include_shap
            else False
        )
        if _shap_enabled:
            try:
                shap_result = self.shap_analyzer.explain_model(model, X, feature_names)
                if "feature_importance" in shap_result:
                    _fi = shap_result["feature_importance"]
                    if isinstance(_fi, dict):
                        all_importances["shap"] = _fi
                        methods_used.append("shap")
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"SHAP analysis failed: {e}")

        # Permutation importance
        _perm_sub = self.config.get("permutation", {})
        _perm_enabled = (
            (isinstance(_perm_sub, dict) and _perm_sub.get("enabled", True))
            if (include_permutation and y is not None)
            else False
        )
        if _perm_enabled:
            try:
                perm_result = self.permutation_analyzer.calculate_importance(
                    model, X, y, feature_names
                )
                if "feature_importance" in perm_result:
                    _fi = perm_result["feature_importance"]
                    if isinstance(_fi, dict):
                        all_importances["permutation"] = _fi
                        methods_used.append("permutation")
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Permutation importance failed: {e}")

        # Built-in importance
        _builtin_sub = self.config.get("builtin", {})
        _builtin_enabled = (
            (isinstance(_builtin_sub, dict) and _builtin_sub.get("enabled", True))
            if include_builtin
            else False
        )
        if _builtin_enabled:
            try:
                builtin_result = self.builtin_analyzer.calculate_importance(model, feature_names)
                if builtin_result.get("supported", False):
                    _fi = builtin_result.get("feature_importance")
                    if isinstance(_fi, dict):
                        all_importances["builtin"] = _fi
                        methods_used.append("builtin")
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Built-in importance failed: {e}")

        # Correlation analysis
        correlation_result: (
            dict[
                str,
                str
                | dict[str, float]
                | list[str]
                | list[tuple[str, str, float]]
                | dict[str, dict[str, float]]
                | dict[str, dict[str, float]]
                | None,
            ]
            | None
        ) = None
        _corr_sub = self.config.get("correlation", {})
        _corr_enabled = (
            (isinstance(_corr_sub, dict) and _corr_sub.get("enabled", True))
            if (include_correlation and y is not None)
            else False
        )
        if _corr_enabled:
            try:
                correlation_result = self.correlation_analyzer.analyze(X, y, feature_names)
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Correlation analysis failed: {e}")

        # Combine importances (average across methods)
        combined_importance = self._combine_importances(all_importances, feature_names)

        # Update stability tracker
        if combined_importance:
            self.stability_tracker.record_importance(combined_importance)

        # Get stability analysis
        stability_result = self.stability_tracker.analyze_stability()

        # Create feature results
        feature_results = self._create_feature_results(
            combined_importance,
            all_importances,
            correlation_result,
            stability_result,
            feature_names,
        )

        # Identify top and low importance features
        sorted_features = sorted(feature_results, key=lambda x: x.importance_score, reverse=True)
        top_features = [f.feature_name for f in sorted_features[:10]]
        low_importance_features = [
            f.feature_name
            for f in sorted_features
            if f.category in [ImportanceCategory.LOW, ImportanceCategory.NEGLIGIBLE]
        ]

        # Get highly correlated pairs
        highly_correlated: list[tuple[str, str, float]] = []
        if correlation_result is not None and "highly_correlated_pairs" in correlation_result:
            _hcp = correlation_result["highly_correlated_pairs"]
            if isinstance(_hcp, list):
                highly_correlated = _hcp

        # Generate recommendations
        recommendations = self._generate_recommendations(
            feature_results, highly_correlated, stability_result
        )

        analysis_time = time.time() - start_time

        return ComprehensiveImportanceReport(
            timestamp=datetime.now(),
            n_features=n_features,
            n_samples=n_samples,
            feature_results=feature_results,
            top_features=top_features,
            low_importance_features=low_importance_features,
            highly_correlated_pairs=highly_correlated,
            recommendations=recommendations,
            methods_used=methods_used,
            analysis_time_seconds=analysis_time,
        )

    def _combine_importances(
        self,
        all_importances: dict[str, dict[str, float]],
        feature_names: list[str],
    ) -> dict[str, float]:
        """Combine importances from multiple methods."""
        if not all_importances:
            return {name: 1.0 / len(feature_names) for name in feature_names}

        combined = {}
        for feature in feature_names:
            values = []
            for _method, imp_dict in all_importances.items():
                if feature in imp_dict:
                    values.append(imp_dict[feature])
            combined[feature] = float(np.mean(values)) if values else 0.0

        # Normalize
        total = sum(combined.values())
        if total > 0:
            combined = {k: v / total for k, v in combined.items()}

        return combined

    def _create_feature_results(
        self,
        combined_importance: dict[str, float],
        all_importances: dict[str, dict[str, float]],
        correlation_result: (
            dict[
                str,
                str
                | dict[str, float]
                | list[str]
                | list[tuple[str, str, float]]
                | dict[str, dict[str, float]]
                | dict[str, dict[str, float]]
                | None,
            ]
            | None
        ),
        stability_result: dict[
            str, str | int | dict[str, dict[str, float | bool | str | int]] | list[str]
        ],
        feature_names: list[str],
    ) -> list[FeatureImportanceResult]:
        """Create FeatureImportanceResult for each feature."""
        results = []

        # Sort by importance for ranking
        sorted_features = sorted(combined_importance.items(), key=lambda x: x[1], reverse=True)
        feature_ranks = {name: i + 1 for i, (name, _) in enumerate(sorted_features)}

        for feature in feature_names:
            importance = combined_importance.get(feature, 0.0)
            rank = feature_ranks.get(feature, len(feature_names))

            # Determine category
            category = self._get_category(importance, len(feature_names))

            # Get method scores
            method_scores = {}
            methods_used = []
            for method, imp_dict in all_importances.items():
                if feature in imp_dict:
                    method_scores[method] = imp_dict[feature]
                    methods_used.append(method)

            # Get correlation with target
            correlation: float | None = None
            if correlation_result is not None and "target_correlations" in correlation_result:
                _tc = correlation_result["target_correlations"]
                if isinstance(_tc, dict):
                    _val = _tc.get(feature)
                    correlation = _val if isinstance(_val, (int, float)) else None

            # Get stability score
            stability_score: float | None = None
            if "feature_stability" in stability_result:
                _fs = stability_result["feature_stability"]
                if isinstance(_fs, dict):
                    feat_stability = _fs.get(feature, {})
                    if isinstance(feat_stability, dict):
                        _ss = feat_stability.get("stability_score")
                        stability_score = _ss if isinstance(_ss, (int, float)) else None

            # Generate recommendation
            recommendation = self._get_feature_recommendation(
                feature, importance, rank, category, stability_score, correlation
            )

            results.append(
                FeatureImportanceResult(
                    feature_name=feature,
                    importance_score=importance,
                    rank=rank,
                    category=category,
                    methods_used=methods_used,
                    method_scores=method_scores,
                    stability_score=stability_score,
                    correlation_with_target=correlation,
                    recommendation=recommendation,
                )
            )

        return results

    def _get_category(self, importance: float, n_features: int) -> ImportanceCategory:
        """Determine importance category."""
        # Normalize importance relative to uniform distribution
        uniform = 1.0 / n_features
        relative_importance = importance / uniform if uniform > 0 else 0

        if relative_importance >= 3:
            return ImportanceCategory.CRITICAL
        elif relative_importance >= 1.5:
            return ImportanceCategory.IMPORTANT
        elif relative_importance >= 0.5:
            return ImportanceCategory.MODERATE
        elif relative_importance >= 0.1:
            return ImportanceCategory.LOW
        else:
            return ImportanceCategory.NEGLIGIBLE

    def _get_feature_recommendation(
        self,
        feature: str,
        importance: float,
        rank: int,
        category: ImportanceCategory,
        stability_score: float | None,
        correlation: float | None,
    ) -> str:
        """Generate recommendation for a feature."""
        if category == ImportanceCategory.NEGLIGIBLE:
            return "Consider removing - negligible importance"
        elif category == ImportanceCategory.LOW:
            if stability_score and stability_score > 0.5:
                return "Low importance and unstable - candidate for removal"
            return "Monitor - low importance"
        elif category == ImportanceCategory.CRITICAL:
            if stability_score and stability_score > 0.3:
                return "Critical feature but unstable - investigate"
            return "Keep - critical for predictions"
        elif category == ImportanceCategory.IMPORTANT:
            return "Keep - important for predictions"
        else:
            return "Monitor - moderate importance"

    def _generate_recommendations(
        self,
        feature_results: list[FeatureImportanceResult],
        highly_correlated: list[tuple[str, str, float]],
        stability_result: dict[
            str, str | int | dict[str, dict[str, float | bool | str | int]] | list[str]
        ],
    ) -> list[str]:
        """Generate overall recommendations."""
        recommendations = []

        # Low importance features
        low_imp = [
            f.feature_name
            for f in feature_results
            if f.category in [ImportanceCategory.NEGLIGIBLE, ImportanceCategory.LOW]
        ]
        if low_imp:
            recommendations.append(
                f"Consider removing {len(low_imp)} low-importance features: "
                f"{', '.join(low_imp[:5])}{'...' if len(low_imp) > 5 else ''}"
            )

        # Highly correlated pairs
        if highly_correlated:
            recommendations.append(
                f"Found {len(highly_correlated)} highly correlated feature pairs. "
                "Consider removing one from each pair to reduce multicollinearity."
            )

        # Unstable features
        _unstable_val = stability_result.get("unstable_features", [])
        unstable: list[str] = _unstable_val if isinstance(_unstable_val, list) else []
        if unstable:
            recommendations.append(
                f"{len(unstable)} features have unstable importance: "
                f"{', '.join(unstable[:5])}{'...' if len(unstable) > 5 else ''}"
            )

        # Trending features
        _trending_up_val = stability_result.get("trending_up", [])
        trending_up: list[str] = _trending_up_val if isinstance(_trending_up_val, list) else []
        _trending_down_val = stability_result.get("trending_down", [])
        trending_down: list[str] = (
            _trending_down_val if isinstance(_trending_down_val, list) else []
        )
        if trending_up:
            recommendations.append(
                f"Features with increasing importance: {', '.join(trending_up[:3])}"
            )
        if trending_down:
            recommendations.append(
                f"Features with decreasing importance: {', '.join(trending_down[:3])}"
            )

        if not recommendations:
            recommendations.append("Feature set appears well-balanced and stable.")

        return recommendations

    def get_top_features(self, n: int = 10) -> list[str]:
        """Get top N features from last analysis."""
        if not self.stability_tracker._importance_history:
            return []

        last_importance = self.stability_tracker._importance_history[-1]
        sorted_features = sorted(last_importance.items(), key=lambda x: x[1], reverse=True)
        return [f[0] for f in sorted_features[:n]]

    def reset(self) -> None:
        """Reset analyzer state."""
        self.stability_tracker.reset()
