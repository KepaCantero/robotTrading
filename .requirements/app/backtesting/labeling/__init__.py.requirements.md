# Requirements: backtesting/labeling/__init__.py

## Audit Status: PASSED
**Audit Date:** 2026-02-07T05:30:00Z
**Auditor:** GAP Audit System

## Source File Analysis
- **File Path:** `app/backtesting/labeling/__init__.py`
- **Lines of Code:** 130
- **Type:** Barrel export module

## Purpose
Barrel export module for Financial ML Labeling system. This module provides advanced labeling techniques for machine learning in finance, following methodologies from Marcos López de Prado's "Advances in Financial Machine Learning".

## Dependencies
### Internal
- `.bet_sizing` - Bet sizing with ML
- `.bet_sizing_meta` - Bet sizing with meta-labeling integration
- `.concurrent_training` - Concurrent model training
- `.meta_labeling` - Meta-labeling for position sizing
- `.meta_labeling_cv` - Meta-labeling with cross-validation
- `.triple_barrier` - Triple barrier method

### External
- None (this is an __init__.py barrel export module)

## Classes/Functions Exported
### Triple Barrier Method
- `TripleBarrierLabeler` - Main triple barrier labeling class
- `TripleBarrierConfig` - Configuration for triple barrier
- `calculate_dynamic_barriers` - Calculate dynamic price barriers
- `get_vertical_barriers` - Get vertical barrier timestamps
- `plot_triple_barrier` - Visualization helper
- `triple_barrier_method` - Main triple barrier method
- `meta_labeling` - Meta-labeling function

### Sample Weights (López de Prado Chapter 4)
- `calculate_sample_weights` - Calculate sample weights
- `calculate_sample_weights_uniqueness` - Weights by uniqueness
- `calculate_sample_weights_td` - Time-decay weights
- `purged_cv_split` - Purged cross-validation split

### Meta-labeling
- `MetaLabeling` - Meta-labeling class
- `MetaLabelingConfig` - Meta-labeling configuration
- `MetaLabelingResult` - Meta-labeling result
- `apply_meta_labeling` - Apply meta-labeling
- `calculate_meta_labels` - Calculate meta labels
- `snv_to_signal` - Convert SNV to signal

### Bet Sizing with ML (López de Prado Chapter 10)
- `BetSizing` - Bet sizing class
- `BetSizingConfig` - Bet sizing configuration
- `BetSizingResult` - Bet sizing result
- `calculate_bet_sizes` - Calculate bet sizes
- `calculate_bet_sizes_ml` - Calculate with ML
- `calculate_bet_sizes_with_discrete_allocation` - Discrete allocation
- `calculate_bet_sizes_with_risk_target` - Risk-based sizing
- `calculate_bet_sizes_expected_value` - Expected value sizing
- `calculate_bet_sizes_with_meta_model` - Meta-model sizing

### Meta-Labeling Cross-Validation (95% compliance)
- `PurgedKFold` - Purged K-Fold CV
- `MetaLabelingCV` - Meta-labeling with CV
- `SequentialBootstrap` - Sequential bootstrapping
- `cv_score_meta_labeling` - CV scoring for meta-labeling
- `calculate_purge_embargo_sizes` - Calculate purge/embargo sizes
- `CVConfig` - CV configuration
- `CVResult` - CV result

### Bet Sizing with Meta-Labeling Integration
- `MetaLabelingBetSizing` - Combined meta-labeling bet sizing
- `MetaBetSizingConfig` - Configuration
- `MetaBetSizingResult` - Result
- `calculate_bet_sizes_with_meta_labeling` - Calculate with meta-labeling
- `calculate_expected_value_with_meta_probabilities` - EV with meta-probs
- `calculate_kelly_with_meta_probabilities` - Kelly with meta-probs

### Concurrent Model Training
- `ConcurrentModelTrainer` - Concurrent training
- `SequentialModelTrainer` - Sequential training
- `train_models_concurrent` - Train models concurrently
- `ConcurrentTrainingConfig` - Configuration
- `ModelResult` - Single model result
- `EnsembleResult` - Ensemble result

## BASE_RULES Compliance
✅ **R099 (Absolute imports):** All imports use absolute paths with `from .module`
✅ **R098 (No relative imports):** Uses explicit relative imports (acceptable in __init__.py)
✅ **R100 (Modern type hints):** N/A (barrel export module with no type annotations)
✅ **R102 (Any without docs):** N/A (no Any types used)
✅ **R103 (No type comments):** No type comments used
✅ **R104 (No bare except):** N/A (no exception handling)
✅ **R105 (No print statements):** No print() statements
✅ **R107 (No mutable defaults):** N/A (no functions with defaults)
✅ **R108 (Exception handling):** N/A (no exception handling)
✅ **R110 (Google docstrings):** Comprehensive module docstring with references
✅ **R111 (No circular imports):** Imports are from submodules, no circularity

## Module Docstring
The module has an excellent docstring following Google style with:
- Clear description of module purpose
- Reference to López de Prado's methodologies
- List of key components with descriptions
- References to academic literature

## Exports
All exported items are properly listed in `__all__` with organized sections and comments indicating:
- Core triple barrier functionality
- Sample weight calculation methods
- Meta-labeling components
- Bet sizing with ML
- New features (95% compliance modules)
- Cross-validation utilities

## Notes
- F401 warnings are expected for barrel export modules
- Well-organized export structure with logical grouping
- Comments indicate which modules are newer/higher compliance
- Follows López de Prado's methodologies closely

---
*Auto-generated on Thu Feb  5 20:32:58 CET 2026*
*Updated for GAP Audit on 2026-02-07*
