"""
Validation module for financial backtesting (FASE 5.3).

This module implements advanced validation techniques specifically designed for
financial time series to prevent look-ahead bias, detect overfitting, and ensure
robust strategy performance.

Key Components:
- WalkForwardValidator: Rolling window walk-forward validation
- OverfittingDetector: IS vs OS comparison with degradation analysis
- RegimeDetector: Market regime detection (bull/bear/volatility/trend)
- ParameterStabilityAnalyzer: Parameter drift and stability analysis
- PurgedKFold: K-Fold CV with purging and embargo (López de Prado Chapter 4)
- PurgedTimeSeriesSplit: Time series split with purging and embargo
- CrossValidation: Event-based purged CV with t1 (exit times) support
- BonferroniCorrection: Multiple testing correction (Ernest Chan)
- CrossSectionalConsistency: Ilmanen's cross-sectional validation
- BiasVarianceAnalysis: Hastie's bias-variance decomposition
- FeatureExplosionValidator: Feature explosion detection
- Utility functions for purged cross-validation

References:
    - AUDIT_PLAN_COMPLETO.md - FASE 5.3: Validation
    - "Advances in Financial Machine Learning" by Marcos López de Prado (Chapter 4)
    - "Quantitative Trading" by Ernest P. Chan (Chapter 2)
    - "Expected Returns" by Antti Ilmanen
    - "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    - "A Reality Check for Data Snooping" by Halbert White
"""

# Existing validation components
from .bias_variance_analysis import (
    BiasVarianceAnalyzer,
    BiasVarianceResult,
    LearningCurveResult,
    ModelComplexityLevel,
    StabilityTestResult,
    analyze_bias_variance,
)
from .bonferroni_correction import (
    BonferroniCorrector,
    HypothesisTest,
    MultipleTestResult,
    ParameterTestResult,
    correct_for_multiple_testing,
    is_strategy_significant,
)
from .cross_sectional_consistency import (
    ConsistencyLevel,
    CrossSectionalConsistencyChecker,
    CrossSectionalResult,
    DecileAnalysisResult,
    validate_cross_sectional_consistency,
)
from .cross_validation import (
    PurgedCVConfig,
    PurgedKFold as PurgedKFoldCV,
    PurgedSplitResult,
    PurgedTimeSeriesSplit as PurgedTimeSeriesSplitCV,
    cv_score,
)
from .cross_validation_methods import (
    CrossValidation,
    CVMethod,
    CVResult,
    KFoldCV,
    LeaveOneOutCV,
    NestedCrossValidation,
    NestedCVResult,
    StratifiedKFoldCV,
    TimeSeriesSplitCV,
    cross_validate,
    nested_cross_validate,
)
from .drawdown_validator import DrawdownValidationError, DrawdownValidator
from .feature_explosion_validator import (
    FeatureExplosionLevel,
    FeatureExplosionResult,
    FeatureExplosionValidator,
    MulticollinearityResult,
    analyze_multicollinearity,
    validate_feature_explosion,
)

# FASE 5.3: Validation Module (New)
from .models import (
    MarketRegime,
    OverfittingLevel,
    OverfittingMetrics,
    ParameterStabilityResult,
    PeriodResult,
    RegimeConfig,
    RegimeTransitionMatrix,
    RegimeType,
    StabilityLevel,
    TrendRegime,
    VolatilityRegime,
    WalkForwardConfig,
    WalkForwardResult,
)
from .overfitting_detector import (
    OverfittingDetector,
    analyze_parameter_stability,
    calculate_overfitting_metrics,
    calculate_stability_score,
    classify_stability,
    detect_parameter_drift,
    generate_stability_recommendation,
)
from .parameter_stability import (
    ParameterStabilityAnalyzer,
    calculate_parameter_stability,
    detect_parameter_drift_simple,
    filter_stable_parameters,
    rank_parameters_by_stability,
)

# Task 17: Backtest Fixes - P&L and Drawdown Validators
from .pnl_validator import PnLValidationError, PnLValidator
from .purged_kfold import (
    PurgedKFold,
    PurgedKFoldConfig,
    PurgedSplit,
    PurgedTimeSeriesSplit,
    apply_embargo,
    cross_validate_with_purging,
    get_embargo_indices,
    get_purge_indices,
    purged_kfold_splits,
)
from .regime_detector import RegimeDetector, classify_market_state, detect_regime_from_data
from .walk_forward import (
    RollingWindowOptimizer,
    WalkForwardValidator,
    calculate_consistency_score,
    calculate_degradation,
)

__all__ = [
    # FASE 5.3: Validation Module (New)
    # Models
    "MarketRegime",
    "OverfittingLevel",
    "OverfittingMetrics",
    "ParameterStabilityResult",
    "PeriodResult",
    "RegimeConfig",
    "RegimeType",
    "RegimeTransitionMatrix",
    "StabilityLevel",
    "TrendRegime",
    "VolatilityRegime",
    "WalkForwardConfig",
    "WalkForwardResult",
    # Walk-Forward Validation
    "WalkForwardValidator",
    "RollingWindowOptimizer",
    "calculate_degradation",
    "calculate_consistency_score",
    # Overfitting Detection
    "OverfittingDetector",
    "analyze_parameter_stability",
    "calculate_overfitting_metrics",
    "classify_stability",
    "calculate_stability_score",
    "detect_parameter_drift",
    "generate_stability_recommendation",
    # Regime Detection
    "RegimeDetector",
    "classify_market_state",
    "detect_regime_from_data",
    # Parameter Stability
    "ParameterStabilityAnalyzer",
    "calculate_parameter_stability",
    "detect_parameter_drift_simple",
    "filter_stable_parameters",
    "rank_parameters_by_stability",
    # Purged K-Fold CV (López de Prado Chapter 4)
    "PurgedKFold",
    "PurgedKFoldCV",  # Event-aware version from cross_validation.py
    "PurgedKFoldConfig",
    "PurgedCVConfig",
    "PurgedSplit",
    "PurgedSplitResult",
    "PurgedTimeSeriesSplit",
    "PurgedTimeSeriesSplitCV",
    "cv_score",
    "apply_embargo",
    "cross_validate_with_purging",
    "get_embargo_indices",
    "get_purge_indices",
    "purged_kfold_splits",
    # Bonferroni Correction (Ernest Chan)
    "BonferroniCorrector",
    "HypothesisTest",
    "MultipleTestResult",
    "ParameterTestResult",
    "correct_for_multiple_testing",
    "is_strategy_significant",
    # Cross-Sectional Consistency (Ilmanen)
    "CrossSectionalConsistencyChecker",
    "ConsistencyLevel",
    "DecileAnalysisResult",
    "CrossSectionalResult",
    "validate_cross_sectional_consistency",
    # Bias-Variance Analysis (Hastie)
    "BiasVarianceAnalyzer",
    "ModelComplexityLevel",
    "BiasVarianceResult",
    "LearningCurveResult",
    "StabilityTestResult",
    "analyze_bias_variance",
    # Feature Explosion Validator
    "FeatureExplosionValidator",
    "FeatureExplosionLevel",
    "FeatureExplosionResult",
    "MulticollinearityResult",
    "validate_feature_explosion",
    "analyze_multicollinearity",
    # ESL Cross-Validation Methods (Hastie Chapter 7)
    "CVMethod",
    "CVResult",
    "NestedCVResult",
    "KFoldCV",
    "LeaveOneOutCV",
    "StratifiedKFoldCV",
    "TimeSeriesSplitCV",
    "NestedCrossValidation",
    "CrossValidation",
    "cross_validate",
    "nested_cross_validate",
    # Task 17: Backtest Fixes
    "PnLValidator",
    "PnLValidationError",
    "DrawdownValidator",
    "DrawdownValidationError",
]
