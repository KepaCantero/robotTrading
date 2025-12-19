"""
LearningEngine - Sistema modular de aprendizaje híbrido para estrategias de trading.
"""

from .base_learning_engine import BaseLearningEngine

# Drift detection y overfitting (siempre disponibles) [TASK-4.2-DRIFT]
from .drift_detector import (
    ADWINDetector,
    AutoRetrainingTrigger,
    ComprehensiveDriftDetector,
    ComprehensiveDriftReport,
    ConceptDriftDetector,
    DriftResult,
    DriftSeverity,
    FeatureDriftMonitor,
    FeatureDriftReport,
    OverfittingDetector,
    PSIDetector,
    get_default_drift_config,
    load_drift_config,
)

# Feature importance (siempre disponibles)
from .feature_importance import (
    AttentionWeightsAnalyzer,
    FeatureImportanceAnalyzer,
    FeatureSelector,
    SHAPAnalyzer,
)

# Hyperparameter tuning (siempre disponibles)
from .hyperparameter_tuner import (
    EarlyStoppingAdaptive,
    HyperparameterTuner,
    LearningEngineTuner,
    ResourceAwareTuner,
)

# Multi-task learning (siempre disponibles)
from .multitask_learning import (
    MultiObjectiveOptimizer,
    MultiTaskLearningEngine,
    MultiTaskModel,
    SharedBackbone,
    TaskHead,
)

# Transfer learning (siempre disponibles)
from .transfer_learning import FineTuner, KnowledgeDistiller, ModelRegistry, TransferLearningManager

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
    # Base
    "BaseLearningEngine",
    # Drift detection [TASK-4.2-DRIFT]
    "PSIDetector",
    "ADWINDetector",
    "ConceptDriftDetector",
    "FeatureDriftMonitor",
    "OverfittingDetector",
    "ComprehensiveDriftDetector",
    "AutoRetrainingTrigger",
    "DriftResult",
    "DriftSeverity",
    "FeatureDriftReport",
    "ComprehensiveDriftReport",
    "load_drift_config",
    "get_default_drift_config",
    # Feature importance
    "SHAPAnalyzer",
    "AttentionWeightsAnalyzer",
    "FeatureSelector",
    "FeatureImportanceAnalyzer",
    # Transfer learning
    "ModelRegistry",
    "FineTuner",
    "KnowledgeDistiller",
    "TransferLearningManager",
    # Multi-task learning
    "SharedBackbone",
    "TaskHead",
    "MultiTaskModel",
    "MultiObjectiveOptimizer",
    "MultiTaskLearningEngine",
    # Hyperparameter tuning
    "EarlyStoppingAdaptive",
    "ResourceAwareTuner",
    "HyperparameterTuner",
    "LearningEngineTuner",
]
