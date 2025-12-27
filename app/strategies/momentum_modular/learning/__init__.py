"""
LearningEngine - Sistema modular de aprendizaje híbrido para estrategias de trading.
"""

from .base_learning_engine import BaseLearningEngine

# Drift detection y overfitting (siempre disponibles) [TASK-4.2-DRIFT]
from .drift_detector import (
    AdvancedOverfittingDetector,
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
    OverfittingMetrics,
    OverfittingReport,
    OverfittingResult,
    OverfittingSeverity,
    PSIDetector,
    get_default_drift_config,
    get_default_overfitting_config,
    load_drift_config,
    load_overfitting_config,
)

# Feature importance (siempre disponibles) [TASK-4.2-FEATURE-IMPORTANCE]
from .feature_importance import (
    AttentionWeightsAnalyzer,
    BuiltInImportanceAnalyzer,
    ComprehensiveFeatureAnalyzer,
    ComprehensiveImportanceReport,
    CorrelationAnalyzer,
    FeatureImportanceAnalyzer,
    FeatureImportanceResult,
    FeatureSelector,
    FeatureStabilityTracker,
    ImportanceCategory,
    PermutationImportanceAnalyzer,
    SHAPAnalyzer,
    get_default_feature_importance_config,
    load_feature_importance_config,
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

    # Base
    "BaseLearningEngine",
    # Drift detection [TASK-4.2-DRIFT]
    "PSIDetector",
    "ADWINDetector",
    "ConceptDriftDetector",
    "FeatureDriftMonitor",
    "OverfittingDetector",
    "AdvancedOverfittingDetector",
    "ComprehensiveDriftDetector",
    "AutoRetrainingTrigger",
    "DriftResult",
    "DriftSeverity",
    "FeatureDriftReport",
    "ComprehensiveDriftReport",
    "OverfittingSeverity",
    "OverfittingMetrics",
    "OverfittingResult",
    "OverfittingReport",
    "load_drift_config",
    "get_default_drift_config",
    "load_overfitting_config",
    "get_default_overfitting_config",
    # Feature importance [TASK-4.2-FEATURE-IMPORTANCE]
    "SHAPAnalyzer",
    "AttentionWeightsAnalyzer",
    "FeatureSelector",
    "FeatureImportanceAnalyzer",
    "PermutationImportanceAnalyzer",
    "BuiltInImportanceAnalyzer",
    "CorrelationAnalyzer",
    "FeatureStabilityTracker",
    "ComprehensiveFeatureAnalyzer",
    "ImportanceCategory",
    "FeatureImportanceResult",
    "ComprehensiveImportanceReport",
    "load_feature_importance_config",
    "get_default_feature_importance_config",
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
