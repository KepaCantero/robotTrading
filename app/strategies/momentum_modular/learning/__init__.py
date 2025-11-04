"""
LearningEngine - Sistema modular de aprendizaje híbrido para estrategias de trading.
"""

from .base_learning_engine import BaseLearningEngine

# Drift detection y overfitting (siempre disponibles)
from .drift_detector import (
    ConceptDriftDetector,
    OverfittingDetector,
    AutoRetrainingTrigger
)

# Feature importance (siempre disponibles)
from .feature_importance import (
    SHAPAnalyzer,
    AttentionWeightsAnalyzer,
    FeatureSelector,
    FeatureImportanceAnalyzer
)

# Transfer learning (siempre disponibles)
from .transfer_learning import (
    ModelRegistry,
    FineTuner,
    KnowledgeDistiller,
    TransferLearningManager
)

# Multi-task learning (siempre disponibles)
from .multitask_learning import (
    SharedBackbone,
    TaskHead,
    MultiTaskModel,
    MultiObjectiveOptimizer,
    MultiTaskLearningEngine
)

# Hyperparameter tuning (siempre disponibles)
from .hyperparameter_tuner import (
    EarlyStoppingAdaptive,
    ResourceAwareTuner,
    HyperparameterTuner,
    LearningEngineTuner
)

# TODOS los learning engines se importan LAZY para evitar bloqueos
# Solo BaseLearningEngine se importa aquí porque es necesario para type hints
# Los demás se importarán cuando realmente se necesiten en strategy.py

SupervisedLearningEngine = None
DeepLearningEngine = None
ReinforcementLearningEngine = None
TransformerEngine = None
TRANSFORMER_AVAILABLE = False

# HybridLearningEngine también lazy
HybridLearningEngine = None
HYBRID_AVAILABLE = False

# Construir __all__ dinámicamente
__all__ = [
    "BaseLearningEngine",
    "ConceptDriftDetector",
    "OverfittingDetector",
    "AutoRetrainingTrigger",
    "SHAPAnalyzer",
    "AttentionWeightsAnalyzer",
    "FeatureSelector",
    "FeatureImportanceAnalyzer",
    "ModelRegistry",
    "FineTuner",
    "KnowledgeDistiller",
    "TransferLearningManager",
    "SharedBackbone",
    "TaskHead",
    "MultiTaskModel",
    "MultiObjectiveOptimizer",
    "MultiTaskLearningEngine",
    "EarlyStoppingAdaptive",
    "ResourceAwareTuner",
    "HyperparameterTuner",
    "LearningEngineTuner"
]

