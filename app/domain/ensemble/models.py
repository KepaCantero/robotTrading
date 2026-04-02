"""
Data models for ensemble methods.

This module defines Pydantic models for ensemble configuration,
Pareto front solutions, and portfolio combination metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Optimization objective types."""

    MAXIMIZE_RETURN = "maximize_return"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_SORTINO = "maximize_sortino"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_DIVERSIFICATION = "maximize_diversification"


class ObjectiveConfig(BaseModel):
    """Configuration for multi-objective optimization.

    Attributes:
        objectives: List of objectives to optimize
        weights: Weights for each objective (must sum to 1.0)
        constraints: Optional constraints for optimization
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=False,  # Keep enums for internal use
    )

    objectives: list[OptimizationObjective] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="List of optimization objectives",
    )
    weights: list[float] = Field(
        ...,
        min_length=1,
        description="Weights for each objective (must sum to 1.0)",
    )
    constraints: dict[str, Any] | None = Field(
        default=None,
        description="Optional constraints for optimization",
    )
    tolerance: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Tolerance for Pareto dominance",
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: list[float]) -> list[float]:
        """Validate that weights sum to approximately 1.0."""
        if not all(isinstance(w, (int, float)) for w in v):
            logger.warning(
                "Invalid weight types detected",
                extra={"weights": v, "weight_types": [type(w).__name__ for w in v]},
            )
            raise ValueError("All weights must be numbers")

        total = sum(v)
        if abs(total - 1.0) > 0.01:
            logger.warning("Weights do not sum to 1.0", extra={"weights": v, "total": total})
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        if any(w < 0 for w in v):
            logger.warning("Negative weights detected", extra={"weights": v})
            raise ValueError("Weights cannot be negative")

        logger.debug("Weights validated successfully", extra={"weights": v, "total": total})
        return v

    @field_validator("objectives")
    @classmethod
    def validate_objectives_match_weights(
        cls, v: list[OptimizationObjective], info
    ) -> list[OptimizationObjective]:
        """Validate that number of objectives matches number of weights."""
        if "weights" in info.data and len(v) != len(info.data["weights"]):
            logger.warning(
                "Objectives count does not match weights count",
                extra={
                    "objectives_count": len(v),
                    "weights_count": len(info.data["weights"]),
                    "objectives": [obj.value for obj in v],
                },
            )
            raise ValueError(
                f"Number of objectives ({len(v)}) must match "
                f"number of weights ({len(info.data['weights'])})"
            )
        logger.debug("Objectives validated successfully", extra={"objectives_count": len(v)})
        return v


class ParetoSolution(BaseModel):
    """A solution on the Pareto front.

    Represents a non-dominated solution in multi-objective optimization space.

    Attributes:
        strategy_weights: Weight allocation for each strategy
        objective_values: Values for each objective
        rank: Pareto rank (0 = non-dominated)
        crowding_distance: Crowding distance for diversity
        metrics: Additional performance metrics
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    strategy_weights: dict[str, Decimal] = Field(
        ...,
        description="Weight allocation for each strategy",
    )
    objective_values: dict[str, float] = Field(
        ...,
        description="Values for each objective",
    )
    rank: int = Field(
        default=0,
        ge=0,
        description="Pareto rank (0 = non-dominated)",
    )
    crowding_distance: float = Field(
        default=0.0,
        ge=0.0,
        description="Crowding distance for diversity",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Additional performance metrics",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Solution creation timestamp",
    )

    def __hash__(self) -> int:
        """Make ParetoSolution hashable for use as dictionary key."""
        return hash(
            (
                tuple(sorted((k, str(v)) for k, v in self.strategy_weights.items())),
                tuple(sorted(self.objective_values.items())),
                self.rank,
                self.crowding_distance,
            )
        )

    @field_validator("strategy_weights")
    @classmethod
    def validate_strategy_weights(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        """Validate that strategy weights sum to approximately 1.0."""
        if not v:
            logger.warning("Empty strategy weights provided")
            raise ValueError("Strategy weights cannot be empty")

        # Convert to float for summation
        total = sum(float(w) for w in v.values())

        if abs(total - 1.0) > 0.01:
            logger.warning(
                "Strategy weights do not sum to 1.0",
                extra={"weights": {k: str(v) for k, v in v.items()}, "total": total},
            )
            raise ValueError(f"Strategy weights must sum to 1.0, got {total}")

        if any(w < 0 for w in v.values()):
            logger.warning(
                "Negative strategy weights detected",
                extra={"weights": {k: str(v) for k, v in v.items()}},
            )
            raise ValueError("Strategy weights cannot be negative")

        logger.debug(
            "Pareto solution strategy weights validated",
            extra={"strategies": list(v.keys()), "total": total},
        )
        return v

    @property
    def dominates(self) -> bool:
        """Check if this is a non-dominated solution (rank 0)."""
        return self.rank == 0

    @property
    def is_diverse(self) -> bool:
        """Check if this solution is diverse (high crowding distance)."""
        return self.crowding_distance > 0.5


class EnsembleMethod(str, Enum):
    """Ensemble combination methods."""

    MAJORITY_VOTING = "majority_voting"
    WEIGHTED_VOTING = "weighted_voting"
    SOFT_VOTING = "soft_voting"
    RANK_AVERAGING = "rank_averaging"
    PERFORMANCE_WEIGHTED = "performance_weighted"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


class EnsembleConfig(BaseModel):
    """Configuration for ensemble methods.

    Attributes:
        method: Ensemble combination method to use
        strategies: List of strategy names to include
        strategy_weights: Optional custom weights for strategies
        min_agreement: Minimum agreement threshold (0-1)
        confidence_threshold: Minimum confidence threshold
        rebalance_frequency: Rebalancing frequency in days
        lookback_period: Lookback period for performance calculation
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    method: EnsembleMethod = Field(
        ...,
        description="Ensemble combination method to use",
    )
    strategies: list[str] = Field(
        ...,
        min_length=2,
        description="List of strategy names to include",
    )
    strategy_weights: dict[str, float] | None = Field(
        default=None,
        description="Optional custom weights for strategies",
    )
    min_agreement: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum agreement threshold (0-1)",
    )
    confidence_threshold: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Minimum confidence threshold",
    )
    rebalance_frequency: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Rebalancing frequency in days",
    )
    lookback_period: int = Field(
        default=90,
        ge=1,
        description="Lookback period for performance calculation",
    )

    @field_validator("strategy_weights")
    @classmethod
    def validate_strategy_weights(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate strategy weights if provided."""
        if v is None:
            return v

        if not v:
            logger.warning("Empty strategy weights provided for ensemble config")
            raise ValueError("Strategy weights cannot be empty when provided")

        total = sum(v.values())

        if abs(total - 1.0) > 0.01:
            logger.warning(
                "Ensemble config strategy weights do not sum to 1.0",
                extra={"weights": v, "total": total},
            )
            raise ValueError(f"Strategy weights must sum to 1.0, got {total}")

        if any(w < 0 for w in v.values()):
            logger.warning("Negative strategy weights in ensemble config", extra={"weights": v})
            raise ValueError("Strategy weights cannot be negative")

        logger.debug(
            "Ensemble config strategy weights validated",
            extra={"strategies": list(v.keys()), "total": total},
        )
        return v


class EnsembleSignal(BaseModel):
    """Combined signal from ensemble methods.

    Attributes:
        signal_id: Unique signal identifier
        symbol: Trading symbol
        signal_type: Combined signal type
        confidence: Combined confidence score
        agreement: Agreement level among strategies
        strategy_votes: Votes from each strategy
        strategy_weights: Weights used for combination
        timestamp: Signal generation timestamp
        metadata: Additional signal metadata
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    signal_id: str = Field(
        default_factory=lambda: f"ensemble_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
        description="Unique signal identifier",
    )
    symbol: str = Field(..., description="Trading symbol")
    signal_type: str = Field(..., description="Combined signal type")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Combined confidence score",
    )
    agreement: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agreement level among strategies",
    )
    strategy_votes: dict[str, str] = Field(
        ...,
        description="Votes from each strategy",
    )
    strategy_weights: dict[str, float] = Field(
        ...,
        description="Weights used for combination",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Signal generation timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional signal metadata",
    )

    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable (high confidence and agreement)."""
        return self.confidence > 60.0 and self.agreement > 0.5

    @property
    def has_consensus(self) -> bool:
        """Check if strategies have consensus (unanimous agreement)."""
        if not self.strategy_votes:
            return False
        first_vote = next(iter(self.strategy_votes.values()))
        return all(vote == first_vote for vote in self.strategy_votes.values())


class AllocationMethod(str, Enum):
    """Portfolio allocation methods."""

    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    REGIME_DEPENDENT = "regime_dependent"
    BLACK_LITTERMAN = "black_litterman"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"


class StrategyAllocation(BaseModel):
    """Strategy weight allocation for portfolio combination.

    Attributes:
        strategy: Strategy name
        weight: Allocated weight (0-1)
        target_weight: Target weight for rebalancing
        actual_weight: Current actual weight
        contribution_risk: Risk contribution
        contribution_return: Return contribution
        last_rebalanced: Last rebalancing timestamp
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    strategy: str = Field(..., description="Strategy name")
    weight: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Allocated weight (0-1)",
    )
    target_weight: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Target weight for rebalancing",
    )
    actual_weight: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Current actual weight",
    )
    contribution_risk: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Risk contribution",
    )
    contribution_return: Decimal = Field(
        default=Decimal("0"),
        description="Return contribution",
    )
    last_rebalanced: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last rebalancing timestamp",
    )

    @property
    def drift(self) -> Decimal:
        """Calculate drift from target weight."""
        return abs(self.actual_weight - self.target_weight)

    @property
    def needs_rebalance(self) -> bool:
        """Check if allocation needs rebalancing (>5% drift)."""
        config = get_config()
        threshold = Decimal(str(getattr(config.trading, "portfolio_rebalance_threshold", 0.05)))
        return self.drift > threshold


class CombinedPortfolio(BaseModel):
    """Combined portfolio metrics from ensemble strategies.

    Attributes:
        total_return: Total portfolio return
        volatility: Portfolio volatility
        sharpe_ratio: Sharpe ratio
        sortino_ratio: Sortino ratio
        max_drawdown: Maximum drawdown
        diversification_ratio: Diversification ratio
        effective_n_strategies: Effective number of strategies
        correlation_mean: Mean correlation among strategies
        allocation: Strategy allocations
        metrics: Additional performance metrics
        timestamp: Portfolio snapshot timestamp
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    total_return: Decimal = Field(..., description="Total portfolio return")
    volatility: Decimal = Field(..., ge=Decimal("0"), description="Portfolio volatility")
    sharpe_ratio: Decimal = Field(default=Decimal("0"), description="Sharpe ratio")
    sortino_ratio: Decimal = Field(default=Decimal("0"), description="Sortino ratio")
    max_drawdown: Decimal = Field(
        default=Decimal("0"),
        le=Decimal("0"),
        description="Maximum drawdown",
    )
    diversification_ratio: Decimal = Field(
        default=Decimal("1"),
        ge=Decimal("1"),
        description="Diversification ratio",
    )
    effective_n_strategies: float = Field(
        default=1.0,
        ge=1.0,
        description="Effective number of strategies",
    )
    correlation_mean: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("-1"),
        le=Decimal("1"),
        description="Mean correlation among strategies",
    )
    allocation: list[StrategyAllocation] = Field(
        default_factory=list,
        description="Strategy allocations",
    )
    metrics: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Additional performance metrics",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Portfolio snapshot timestamp",
    )

    @property
    def is_well_diversified(self) -> bool:
        """Check if portfolio is well diversified."""
        return (
            self.diversification_ratio > Decimal("1.2")
            and self.effective_n_strategies >= 2.0
            and abs(self.correlation_mean) < Decimal("0.7")
        )

    @property
    def is_efficient(self) -> bool:
        """Check if portfolio is efficient (good risk-adjusted return)."""
        return self.sharpe_ratio > Decimal("1.0")


class CorrelationMetrics(BaseModel):
    """Correlation analysis results.

    Attributes:
        correlation_matrix: Correlation matrix as nested dict
        mean_correlation: Mean correlation value
        median_correlation: Median correlation value
        max_correlation: Maximum correlation value
        min_correlation: Minimum correlation value
        redundant_pairs: List of highly correlated pairs (>0.9)
        effective_number_bets: Effective number of independent bets
        eigenvalues: Eigenvalues of correlation matrix
        condition_number: Condition number of correlation matrix
        timestamp: Analysis timestamp
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    correlation_matrix: dict[str, dict[str, Decimal]] = Field(
        ...,
        description="Correlation matrix as nested dict",
    )
    mean_correlation: Decimal = Field(
        ...,
        ge=Decimal("-1"),
        le=Decimal("1"),
        description="Mean correlation value",
    )
    median_correlation: Decimal = Field(
        ...,
        ge=Decimal("-1"),
        le=Decimal("1"),
        description="Median correlation value",
    )
    max_correlation: Decimal = Field(
        ...,
        ge=Decimal("-1"),
        le=Decimal("1"),
        description="Maximum correlation value",
    )
    min_correlation: Decimal = Field(
        ...,
        ge=Decimal("-1"),
        le=Decimal("1"),
        description="Minimum correlation value",
    )
    redundant_pairs: list[tuple] = Field(
        default_factory=list,
        description="List of highly correlated pairs (>0.9)",
    )
    effective_number_bets: float = Field(
        default=1.0,
        ge=1.0,
        description="Effective number of independent bets",
    )
    eigenvalues: list[float] = Field(
        default_factory=list,
        description="Eigenvalues of correlation matrix",
    )
    condition_number: float = Field(
        default=1.0,
        ge=1.0,
        description="Condition number of correlation matrix",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analysis timestamp",
    )

    @property
    def has_redundancy(self) -> bool:
        """Check if there are redundant strategies."""
        return len(self.redundant_pairs) > 0

    @property
    def is_well_conditioned(self) -> bool:
        """Check if correlation matrix is well-conditioned."""
        return self.condition_number < 100.0

    @property
    def diversification_quality(self) -> str:
        """Assess diversification quality."""
        if self.effective_number_bets >= 4.0 and abs(self.mean_correlation) < 0.3:
            return "excellent"
        elif self.effective_number_bets >= 3.0 and abs(self.mean_correlation) < 0.5:
            return "good"
        elif self.effective_number_bets >= 2.0:
            return "moderate"
        else:
            return "poor"
