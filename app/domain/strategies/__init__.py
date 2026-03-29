"""
Multi-Factor Strategy - Fama-French 5-Factor + Momentum

This module implements a multi-factor investment strategy based on the
Fama-French 5-factor model augmented with a Momentum factor (Carhart).

Strategy Objective: BALANCED_GROWTH
- Combine multiple factor premiums for consistent returns
- Target positive exposure to Value and Profitability factors
- Maintain diversification and risk control

Components:
- MultiFactorStrategy: Main strategy class
- FactorCalculator: Calculate Fama-French factor scores
- FactorModels: Implement FF3, FF5, and FF6 models
- FactorPortfolioConstructor: Build factor-tilted portfolios
- Models: Data models for factors and portfolios

Factor Definitions:
- Value (HML): High book-to-market ratio
- Size (SMB): Small market cap
- Profitability (RMW): High operating profitability (ROA/ROE)
- Investment (CMA): Conservative investment (low asset growth)
- Momentum (WML): 12-month price momentum excluding last month

Usage:
    from app.domain.strategies.multi_factor import MultiFactorStrategy

    # Create strategy
    config = {
        "name": "MyMultiFactor",
        "value_tilt": 0.2,
        "profitability_tilt": 0.2,
        "portfolio_size": 40,
    }
    strategy = MultiFactorStrategy(config)

    # Set universe
    strategy.set_universe(factor_profiles)

    # Construct portfolio
    portfolio = strategy.construct_initial_portfolio(capital)

References:
- Fama, E. F., & French, K. R. (2015). "A five-factor asset pricing model"
- Carhart, M. M. (1997). "On persistence in mutual fund performance"
- Berkin & Swedroe: "The Incredible Shrinking Alpha"
"""

from .factor_calculator import FactorCalculator, get_default_factor_premiums
from .factor_models import (
    CAPMModel,
    Carhart4FactorModel,
    FactorModelManager,
    FactorModelResult,
    FF3FactorModel,
    FF5FactorModel,
    FF6FactorModel,
)
from .models import (
    FactorOptimizationResult,
    FactorPortfolio,
    FactorPosition,
    FactorProfile,
    FactorRebalanceRecommendation,
    FactorScores,
    FactorStrategyConfig,
    FactorTilt,
    FactorTiltDirection,
    FactorType,
)
from .multi_factor_strategy import MultiFactorStrategy
from .portfolio_constructor import FactorPortfolioConstructor

__all__ = [
    "CAPMModel",
    "Carhart4FactorModel",
    "FF3FactorModel",
    "FF5FactorModel",
    "FF6FactorModel",
    # Calculator
    "FactorCalculator",
    # Models
    "FactorModelManager",
    "FactorModelResult",
    "FactorOptimizationResult",
    "FactorPortfolio",
    # Portfolio constructor
    "FactorPortfolioConstructor",
    "FactorPosition",
    "FactorProfile",
    "FactorRebalanceRecommendation",
    "FactorScores",
    # Data models
    "FactorStrategyConfig",
    "FactorTilt",
    "FactorTiltDirection",
    "FactorType",
    # Main strategy
    "MultiFactorStrategy",
    "get_default_factor_premiums",
]

# Strategy metadata for registry
STRATEGY_METADATA = {
    "name": "multi_factor",
    "description": "Multi-factor strategy (Fama-French 5-Factor + Momentum) for balanced growth",
    "category": "multi_factor",
    "tags": ["fama_french", "multi_factor", "value", "momentum", "balanced_growth"],
    "version": "1.0.0",
    "objetivo_inversion": "BALANCED_GROWTH",
    "risk_profile": "moderate",
    "horizon_recomendado": "long_term",
}
