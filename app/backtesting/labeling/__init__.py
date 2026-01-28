"""
Financial ML Labeling module for AlgoTrading system.

This module provides advanced labeling techniques for machine learning in finance,
following the methodologies from Marcos López de Prado's "Advances in Financial Machine Learning".

Key components:
- Triple Barrier Method: Dynamic labeling based on price barriers
- Sample weights by uniqueness: Weight samples by their uniqueness (López de Prado Chapter 4)
- Meta-labeling: Secondary labeling for position sizing
- Bet Sizing with ML: Position sizing based on meta-model probabilities
- F1/MCC metrics: Metrics for imbalanced data classification
- Volatility-adjusted barriers: Dynamic barrier adjustment based on market conditions
"""

from .bet_sizing import (
    BetSizing,
    BetSizingConfig,
    BetSizingResult,
    calculate_bet_sizes,
    calculate_bet_sizes_expected_value,
    calculate_bet_sizes_ml,
    calculate_bet_sizes_with_discrete_allocation,
    calculate_bet_sizes_with_meta_model,
    calculate_bet_sizes_with_risk_target,
)
from .bet_sizing_meta import (
    MetaBetSizingConfig,
    MetaBetSizingResult,
    MetaLabelingBetSizing,
    calculate_bet_sizes_with_meta_labeling,
    calculate_expected_value_with_meta_probabilities,
    calculate_kelly_with_meta_probabilities,
)
from .concurrent_training import (
    ConcurrentModelTrainer,
    ConcurrentTrainingConfig,
    EnsembleResult,
    ModelResult,
    SequentialModelTrainer,
    train_models_concurrent,
)
from .meta_labeling import (
    MetaLabeling,
    MetaLabelingConfig,
    MetaLabelingResult,
    apply_meta_labeling,
    calculate_meta_labels,
    snv_to_signal,
)

# New López de Prado 95% compliance modules
from .meta_labeling_cv import (
    CVConfig,
    CVResult,
    MetaLabelingCV,
    PurgedKFold,
    SequentialBootstrap,
    calculate_purge_embargo_sizes,
    cv_score_meta_labeling,
)
from .triple_barrier import (
    TripleBarrierConfig,
    TripleBarrierLabeler,
    calculate_dynamic_barriers,
    calculate_sample_weights,
    calculate_sample_weights_td,
    calculate_sample_weights_uniqueness,
    get_vertical_barriers,
    meta_labeling,
    plot_triple_barrier,
    purged_cv_split,
    triple_barrier_method,
)

__all__ = [
    # Triple Barrier
    "TripleBarrierLabeler",
    "TripleBarrierConfig",
    "calculate_dynamic_barriers",
    "get_vertical_barriers",
    "plot_triple_barrier",
    "triple_barrier_method",
    "meta_labeling",
    # Sample Weights (López de Prado Chapter 4)
    "calculate_sample_weights",
    "calculate_sample_weights_uniqueness",
    "calculate_sample_weights_td",
    "purged_cv_split",
    # Meta-labeling
    "MetaLabeling",
    "MetaLabelingConfig",
    "MetaLabelingResult",
    "apply_meta_labeling",
    "calculate_meta_labels",
    "snv_to_signal",
    # Bet Sizing with ML (López de Prado Chapter 10)
    "BetSizing",
    "BetSizingConfig",
    "BetSizingResult",
    "calculate_bet_sizes",
    "calculate_bet_sizes_ml",
    "calculate_bet_sizes_with_discrete_allocation",
    "calculate_bet_sizes_with_risk_target",
    "calculate_bet_sizes_expected_value",
    "calculate_bet_sizes_with_meta_model",
    # NEW: Meta-Labeling Cross-Validation (95% compliance)
    "PurgedKFold",
    "MetaLabelingCV",
    "SequentialBootstrap",
    "cv_score_meta_labeling",
    "calculate_purge_embargo_sizes",
    "CVConfig",
    "CVResult",
    # NEW: Bet Sizing with Meta-Labeling Integration (95% compliance)
    "MetaLabelingBetSizing",
    "MetaBetSizingConfig",
    "MetaBetSizingResult",
    "calculate_bet_sizes_with_meta_labeling",
    "calculate_expected_value_with_meta_probabilities",
    "calculate_kelly_with_meta_probabilities",
    # NEW: Concurrent Model Training (95% compliance)
    "ConcurrentModelTrainer",
    "SequentialModelTrainer",
    "train_models_concurrent",
    "ConcurrentTrainingConfig",
    "ModelResult",
    "EnsembleResult",
]
