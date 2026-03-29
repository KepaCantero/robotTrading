"""
Data Models for Profile Batch Backtesting

This module contains all data models used by the profile batch backtesting
services and the main orchestrator.

Models:
- ProfileResultDB: SQLAlchemy model for database persistence
- BaselineOptimizationComparison: Comparison between baseline and optimized results
- OptimizedStrategy: Result of optimization pipeline
- ProfileResult: Complete result for a single profile
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Union

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

if TYPE_CHECKING:
    from app.domain.models.input_profile import InputProfile
    from app.services.profile_driven_trading.profile_strategy_mapper import StrategyMapping

logger = logging.getLogger(__name__)

# Type aliases for better type safety
ConfigDict = dict[str, Any]
MetricsDict = dict[str, Union[float, int, str, bool, None]]
ParameterDict = dict[str, Any]
OptimizationHistoryEntry = dict[str, Any]
ValidationResultDict = dict[str, Any]
PerStrategyResultsDict = dict[str, dict[str, Any]]

# SQLAlchemy Base
Base = declarative_base()


class ProfileResultDB(Base):
    """
    Database model for profile results.

    Stores baseline and optimization results for each investor profile
    along with validation outcomes and recommendations.
    """

    __tablename__ = "profile_results"
    id = Column(String, primary_key=True)
    profile_id = Column(String, unique=True, index=True)
    objective = Column(String, index=True)
    risk_tolerance = Column(String, index=True)
    capital_tier = Column(String, index=True)
    investment_horizon = Column(Integer)
    # Baseline results
    baseline_sharpe = Column(Float)
    baseline_return = Column(Float)
    baseline_max_dd = Column(Float)
    baseline_win_rate = Column(Float)
    # Optimization results
    optimized_sharpe = Column(Float)
    optimized_return = Column(Float)
    optimized_max_dd = Column(Float)
    optimized_win_rate = Column(Float)
    # Improvement metrics
    sharpe_improvement = Column(Float)
    return_improvement = Column(Float)
    max_dd_improvement = Column(Float)
    win_rate_improvement = Column(Float)
    # Best parameters
    best_parameters = Column(JSON)
    # Validation results
    walk_forward_passed = Column(Boolean)
    monte_carlo_passed = Column(Boolean)
    out_of_sample_passed = Column(Boolean)
    # Final recommendation
    ready_for_paper_trading = Column(Boolean)
    recommendation = Column(String)
    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> ConfigDict:
        """Convert to dictionary."""
        return {
            "profile_id": self.profile_id,
            "objective": self.objective,
            "risk_tolerance": self.risk_tolerance,
            "capital_tier": self.capital_tier,
            "investment_horizon": self.investment_horizon,
            "baseline_results": {
                "sharpe_ratio": self.baseline_sharpe,
                "total_return": self.baseline_return,
                "max_drawdown": self.baseline_max_dd,
                "win_rate": self.baseline_win_rate,
            },
            "optimization_results": {
                "sharpe_ratio": self.optimized_sharpe,
                "total_return": self.optimized_return,
                "max_drawdown": self.optimized_max_dd,
                "win_rate": self.optimized_win_rate,
            },
            "improvement_metrics": {
                "sharpe_improvement": self.sharpe_improvement,
                "return_improvement": self.return_improvement,
                "max_dd_improvement": self.max_dd_improvement,
                "win_rate_improvement": self.win_rate_improvement,
            },
            "best_parameters": self.best_parameters,
            "validation": {
                "walk_forward_passed": self.walk_forward_passed,
                "monte_carlo_passed": self.monte_carlo_passed,
                "out_of_sample_passed": self.out_of_sample_passed,
            },
            "ready_for_paper_trading": self.ready_for_paper_trading,
            "recommendation": self.recommendation,
        }


@dataclass
class BaselineOptimizationComparison:
    """
    Comparison between baseline and optimized results.

    Attributes:
        sharpe_improvement: Percentage improvement in Sharpe ratio
        return_improvement: Percentage improvement in returns
        max_dd_improvement: Percentage improvement in max drawdown (positive is better)
        win_rate_improvement: Percentage improvement in win rate
        sharpe_significant: Whether Sharpe improvement is statistically significant
        return_significant: Whether return improvement is statistically significant
        parameter_importance: Dictionary of parameter names to importance scores
        recommended: Recommendation ("baseline", "optimized", "inconclusive")
        confidence: Confidence level (0-1)
        reason: Explanation for the recommendation
    """

    sharpe_improvement: float  # Percentage improvement
    return_improvement: float  # Percentage improvement
    max_dd_improvement: float  # Percentage improvement (positive is better)
    win_rate_improvement: float  # Percentage improvement
    # Statistical significance
    sharpe_significant: bool
    return_significant: bool
    # Parameter sensitivity
    parameter_importance: dict[str, float]
    # Recommendation
    recommended: str  # "baseline", "optimized", "inconclusive"
    confidence: float  # 0-1
    reason: str


@dataclass
class OptimizedStrategy:
    """
    Result of optimization pipeline.

    Contains complete results from running optimization including
    baseline metrics, optimized metrics, best parameters, and
    validation results.
    """

    profile_id: str
    baseline_metrics: MetricsDict
    optimized_metrics: MetricsDict
    best_parameters: ParameterDict
    optimization_history: list[OptimizationHistoryEntry]
    walk_forward_results: ValidationResultDict | None
    monte_carlo_results: ValidationResultDict | None
    out_of_sample_results: ValidationResultDict | None
    comparison: BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str


@dataclass
class ProfileResult:
    """
    Complete result for a single profile.

    Contains all results from running a single investor profile through
    the batch backtesting pipeline including baseline, optimization,
    improvements, and recommendations.
    """

    profile_id: str
    profile: InputProfile
    baseline_results: MetricsDict
    optimization_results: MetricsDict
    best_parameters: ParameterDict
    improvement_metrics: dict[str, float]
    comparison: BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str
    created_at: datetime = field(default_factory=datetime.now)
    # Multi-strategy support fields
    strategy_mapping: StrategyMapping | None = None
    enabled_strategies: list[str] = field(default_factory=list)
    learning_engines: list[str] = field(default_factory=list)
    ensemble_config: ConfigDict = field(default_factory=dict)
    per_strategy_results: PerStrategyResultsDict = field(default_factory=dict)
