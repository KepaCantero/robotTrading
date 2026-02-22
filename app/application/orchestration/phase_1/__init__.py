"""
PHASE 1: Capital-Tier Aware Strategy Orchestration

T1.1: Capital Tier Strategy Selector
- CapitalTierSelector: Map capital → tier, strategy, features
- StrategyFeatureGatekeeper: Activate/deactivate features by tier
- RiskProfileScaler: Scale risk parameters by capital

T1.2: Absolute Return Optimizer
- TargetAlphaCalculator: Convert EUR targets → required alpha %
- CapacityFadeAnalyzer: Estimate alpha decay at scale
- ParameterOptimizer: Optimize position sizing, leverage
- FeasibilityValidator: Validate target feasibility
"""

from .absolute_return_optimizer import (
    CapacityFadeAnalyzer,
    FeasibilityValidator,
    ParameterOptimizer,
    TargetAlphaCalculator,
)
from .capital_tier_selector import CapitalTierSelector, RiskProfileScaler, StrategyFeatureGatekeeper
from .models import (
    AbsoluteReturnTarget,
    AbsoluteReturnValidation,
    CapitalTier,
    CapitalTierConfig,
    CapitalTierResult,
    CapitalTierThresholds,
    RiskProfile,
    StrategyFeatures,
)

# Models
__all__ = [
    "CapitalTier",
    "CapitalTierConfig",
    "CapitalTierResult",
    "CapitalTierThresholds",
    "RiskProfile",
    "StrategyFeatures",
    "AbsoluteReturnTarget",
    "AbsoluteReturnValidation",
    # T1.1 Selectors
    "CapitalTierSelector",
    "StrategyFeatureGatekeeper",
    "RiskProfileScaler",
    # T1.2 Optimizers
    "TargetAlphaCalculator",
    "CapacityFadeAnalyzer",
    "ParameterOptimizer",
    "FeasibilityValidator",
]
