"""
LearningEngine - Sistema modular de aprendizaje híbrido para estrategias de trading.
"""

from .base_learning_engine import BaseLearningEngine
from .supervised_learning_engine import SupervisedLearningEngine
from .deep_learning_engine import DeepLearningEngine
from .reinforcement_learning_engine import ReinforcementLearningEngine

# HybridLearningEngine es opcional (puede no estar implementado aún)
try:
    from .hybrid_learning_engine import HybridLearningEngine
    __all__ = [
        "BaseLearningEngine",
        "SupervisedLearningEngine",
        "DeepLearningEngine",
        "ReinforcementLearningEngine",
        "HybridLearningEngine",
    ]
except ImportError:
    # HybridLearningEngine no está disponible
    __all__ = [
        "BaseLearningEngine",
        "SupervisedLearningEngine",
        "DeepLearningEngine",
        "ReinforcementLearningEngine",
    ]

