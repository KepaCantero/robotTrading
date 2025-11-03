"""
LearningEngine - Sistema modular de aprendizaje híbrido para estrategias de trading.
"""

from .base_learning_engine import BaseLearningEngine

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

# Construir __all__ dinámicamente - solo BaseLearningEngine por ahora
# Los demás se importan lazy cuando se necesitan
__all__ = ["BaseLearningEngine"]

