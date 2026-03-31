"""
Enhanced Portfolio Management Models

This module defines enhanced models for portfolio management including
performance metrics, risk analysis, and portfolio analytics.

NOTE: For canonical PerformanceMetrics used in backtesting, use app.backtesting.models.PerformanceMetrics
This module contains PortfolioPerformanceRecord which is a specialized model for portfolio persistence.
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.models.portfolio import Portfolio as BasePortfolio

logger = logging.getLogger(__name__)


class ExtendedPortfolio(BasePortfolio):
    """Extended portfolio model for analytics with additional fields."""

    id: UUID = Field(default_factory=uuid4, description="Portfolio identifier")
    name: str = Field(..., description="Portfolio name")
    description: Optional[str] = Field(None, description="Portfolio description")
    total_value: Decimal = Field(..., description="Total portfolio value")
    cash_balance: Decimal = Field(..., description="Cash balance")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    @model_validator(mode="after")
    def validate_portfolio_consistency(self) -> "ExtendedPortfolio":
        """Validate portfolio consistency."""
        logger.debug(
            "Validating extended portfolio consistency",
            extra={"portfolio_id": str(self.id), "name": self.name},
        )
        from app.shared.config.centralized_config import get_config

        cfg = get_config()

        if self.cash_balance != self.cash:
            logger.error(
                "ExtendedPortfolio validation failed: cash balance mismatch",
                extra={
                    "portfolio_id": str(self.id),
                    "cash_balance": str(self.cash_balance),
                    "cash": str(self.cash),
                },
            )
            raise ValueError("Cash balance must match cash field")

        # Calculate total value from positions and cash
        calculated_total = self.cash
        for position in self.positions:
            calculated_total += position.market_value

        # Get tolerance from config
        tolerance = Decimal(str(getattr(cfg.trading, "portfolio_value_tolerance", 0.01)))
        if abs(self.total_value - calculated_total) > tolerance:
            logger.error(
                "ExtendedPortfolio validation failed: total value mismatch",
                extra={
                    "portfolio_id": str(self.id),
                    "expected_total_value": str(calculated_total),
                    "actual_total_value": str(self.total_value),
                    "tolerance": str(tolerance),
                },
            )
            raise ValueError(
                f"Total value mismatch. Expected: {calculated_total}, Got: {self.total_value}"
            )

        logger.debug("ExtendedPortfolio validation passed", extra={"portfolio_id": str(self.id)})
        return self

    @property
    def equity_value(self) -> Decimal:
        """Calculate total equity value."""
        return Decimal(sum(pos.market_value for pos in self.positions))


class PortfolioStatus(str, Enum):
    """Portfolio status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class RiskLevel(str, Enum):
    """Risk level enumeration."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PerformancePeriod(str, Enum):
    """Performance calculation periods."""

    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"
    QUARTERLY = "3m"
    YEARLY = "1y"
    ALL_TIME = "all"


class PortfolioPerformanceRecord(BaseModel):
    """
    Portfolio performance record for persistence.

    This is a specialized model for storing portfolio performance history.
    It includes identity fields (id, portfolio_id, period, dates) and
    portfolio-specific fields (cash_value, equity_value, position_count).

    For backtesting performance metrics, use app.backtesting.models.PerformanceMetrics
    which is the canonical source of truth.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique metrics identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    period: PerformancePeriod = Field(..., description="Performance period")
    start_date: datetime = Field(..., description="Period start date")
    end_date: datetime = Field(..., description="Period end date")

    # Return Metrics
    total_return: Decimal = Field(..., description="Total return percentage")
    annualized_return: Decimal = Field(..., description="Annualized return percentage")
    cumulative_return: Decimal = Field(..., description="Cumulative return")

    # Risk Metrics
    volatility: Decimal = Field(..., description="Portfolio volatility (standard deviation)")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio")
    sortino_ratio: Decimal = Field(..., description="Sortino ratio")
    max_drawdown: Decimal = Field(..., description="Maximum drawdown percentage")
    var_95: Decimal = Field(..., description="Value at Risk (95% confidence)")
    var_99: Decimal = Field(..., description="Value at Risk (99% confidence)")

    # Additional Metrics
    calmar_ratio: Decimal = Field(..., description="Calmar ratio")
    information_ratio: Decimal = Field(..., description="Information ratio")
    treynor_ratio: Decimal = Field(..., description="Treynor ratio")
    jensen_alpha: Decimal = Field(..., description="Jensen's alpha")

    # Portfolio Composition
    total_value: Decimal = Field(..., description="Total portfolio value")
    cash_value: Decimal = Field(..., description="Cash value")
    equity_value: Decimal = Field(..., description="Equity value")
    position_count: int = Field(..., description="Number of positions")

    # Benchmark Comparison
    benchmark_return: Optional[Decimal] = Field(None, description="Benchmark return")
    excess_return: Optional[Decimal] = Field(None, description="Excess return vs benchmark")
    tracking_error: Optional[Decimal] = Field(None, description="Tracking error")

    # Timestamps
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Calculation timestamp"
    )

    @field_validator(
        "total_return",
        "annualized_return",
        "volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "var_95",
        "var_99",
        "calmar_ratio",
        "information_ratio",
        "treynor_ratio",
        "jensen_alpha",
    )
    @classmethod
    def validate_percentage_fields(cls, v: object) -> Decimal:
        """Validate percentage fields are reasonable."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Percentage fields must be numbers")

        # Allow reasonable ranges for financial metrics
        if v < Decimal("-100") or v > Decimal("1000"):
            raise ValueError(f"Percentage field out of reasonable range: {v}")

        return Decimal(str(v))

    @field_validator("total_value", "cash_value", "equity_value")
    @classmethod
    def validate_value_fields(cls, v: object) -> Decimal:
        """Validate value fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Value fields must be numbers")

        if v < 0:
            raise ValueError(f"Value fields must be non-negative: {v}")

        return Decimal(str(v))

    @model_validator(mode="after")
    def validate_metrics_consistency(self) -> "PortfolioPerformanceRecord":
        """Validate consistency between metrics."""
        logger.debug(
            "Validating portfolio performance record consistency",
            extra={"portfolio_id": str(self.portfolio_id), "period": self.period.value},
        )
        if self.start_date >= self.end_date:
            logger.error(
                "PortfolioPerformanceRecord validation failed: invalid date range",
                extra={
                    "portfolio_id": str(self.portfolio_id),
                    "start_date": str(self.start_date),
                    "end_date": str(self.end_date),
                },
            )
            raise ValueError("Start date must be before end date")

        if self.cash_value + self.equity_value != self.total_value:
            logger.error(
                "PortfolioPerformanceRecord validation failed: value components mismatch",
                extra={
                    "portfolio_id": str(self.portfolio_id),
                    "cash_value": str(self.cash_value),
                    "equity_value": str(self.equity_value),
                    "total_value": str(self.total_value),
                },
            )
            raise ValueError("Cash + Equity must equal total value")

        logger.debug(
            "PortfolioPerformanceRecord validation passed",
            extra={"portfolio_id": str(self.portfolio_id)},
        )
        return self


# Backward compatibility alias
PerformanceMetrics = PortfolioPerformanceRecord


class RiskMetrics(BaseModel):
    """Portfolio risk metrics."""

    id: UUID = Field(default_factory=uuid4, description="Unique risk metrics identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Calculation timestamp"
    )

    # Volatility Metrics
    daily_volatility: Decimal = Field(..., description="Daily volatility")
    annualized_volatility: Decimal = Field(..., description="Annualized volatility")
    realized_volatility: Decimal = Field(..., description="Realized volatility")

    # Downside Risk
    downside_deviation: Decimal = Field(..., description="Downside deviation")
    semi_variance: Decimal = Field(..., description="Semi-variance")
    lower_partial_moment: Decimal = Field(..., description="Lower partial moment")

    # Tail Risk
    skewness: Decimal = Field(..., description="Return skewness")
    kurtosis: Decimal = Field(..., description="Return kurtosis")
    tail_ratio: Decimal = Field(..., description="Tail ratio")

    # Concentration Risk
    herfindahl_index: Decimal = Field(..., description="Herfindahl concentration index")
    effective_number_of_positions: Decimal = Field(..., description="Effective number of positions")
    largest_position_weight: Decimal = Field(..., description="Weight of largest position")

    # Correlation Risk
    average_correlation: Decimal = Field(..., description="Average correlation between positions")
    diversification_ratio: Decimal = Field(..., description="Diversification ratio")

    @field_validator(
        "daily_volatility",
        "annualized_volatility",
        "realized_volatility",
        "downside_deviation",
        "semi_variance",
        "lower_partial_moment",
    )
    @classmethod
    def validate_volatility_fields(cls, v: object) -> Decimal:
        """Validate volatility fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Volatility fields must be numbers")

        if v < 0:
            raise ValueError(f"Volatility fields must be non-negative: {v}")

        return Decimal(str(v))


class PortfolioAnalytics(BaseModel):
    """Comprehensive portfolio analytics."""

    id: UUID = Field(default_factory=uuid4, description="Unique analytics identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Analysis date")

    # Performance Summary
    performance_metrics: PortfolioPerformanceRecord = Field(
        ..., description="Performance metrics record"
    )
    risk_metrics: RiskMetrics = Field(..., description="Risk metrics")

    # Risk Assessment
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_score: Decimal = Field(..., description="Risk score (0-100)")

    # Portfolio Health
    health_score: Decimal = Field(..., description="Portfolio health score (0-100)")
    diversification_score: Decimal = Field(..., description="Diversification score (0-100)")
    liquidity_score: Decimal = Field(..., description="Liquidity score (0-100)")

    # Recommendations
    recommendations: list[str] = Field(
        default_factory=list, description="Portfolio recommendations"
    )
    warnings: list[str] = Field(default_factory=list, description="Portfolio warnings")

    # Metadata
    analysis_version: str = Field(default="1.0", description="Analysis version")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("risk_score", "health_score", "diversification_score", "liquidity_score")
    @classmethod
    def validate_score_fields(cls, v: object) -> Decimal:
        """Validate score fields are between 0 and 100."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Score fields must be numbers")

        if v < 0 or v > 100:
            raise ValueError(f"Score fields must be between 0 and 100: {v}")

        return Decimal(str(v))


class PortfolioAllocation(BaseModel):
    """Portfolio allocation analysis."""

    id: UUID = Field(default_factory=uuid4, description="Unique allocation identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Analysis date")

    # Asset Class Allocation
    equity_allocation: Decimal = Field(..., description="Equity allocation percentage")
    fixed_income_allocation: Decimal = Field(..., description="Fixed income allocation percentage")
    cash_allocation: Decimal = Field(..., description="Cash allocation percentage")
    alternative_allocation: Decimal = Field(
        ..., description="Alternative investments allocation percentage"
    )

    # Geographic Allocation
    domestic_allocation: Decimal = Field(..., description="Domestic allocation percentage")
    international_allocation: Decimal = Field(
        ..., description="International allocation percentage"
    )

    # Sector Allocation
    sector_allocations: dict[str, Decimal] = Field(
        default_factory=dict, description="Sector allocations"
    )

    # Top Holdings
    top_holdings: list[dict[str, Any]] = Field(default_factory=list, description="Top holdings")

    # Allocation Quality
    target_allocation: Optional[dict[str, Decimal]] = Field(None, description="Target allocation")
    allocation_deviation: Optional[dict[str, Decimal]] = Field(
        None, description="Allocation deviation from target"
    )

    @field_validator(
        "equity_allocation",
        "fixed_income_allocation",
        "cash_allocation",
        "alternative_allocation",
        "domestic_allocation",
        "international_allocation",
    )
    @classmethod
    def validate_allocation_fields(cls, v: object) -> Decimal:
        """Validate allocation fields are between 0 and 100."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Allocation fields must be numbers")

        if v < 0 or v > 100:
            raise ValueError(f"Allocation fields must be between 0 and 100: {v}")

        return Decimal(str(v))

    @model_validator(mode="after")
    def validate_allocation_sum(self) -> "PortfolioAllocation":
        """Validate that allocations sum to 100%."""
        logger.debug(
            "Validating portfolio allocation sum", extra={"portfolio_id": str(self.portfolio_id)}
        )
        from app.shared.config.centralized_config import get_config

        cfg = get_config()

        total_allocation = (
            self.equity_allocation
            + self.fixed_income_allocation
            + self.cash_allocation
            + self.alternative_allocation
        )

        # Get tolerance from config
        tolerance = Decimal(str(getattr(cfg.trading, "portfolio_allocation_tolerance", 0.01)))
        if abs(total_allocation - Decimal("100")) > tolerance:
            logger.error(
                "PortfolioAllocation validation failed: allocations do not sum to 100%",
                extra={
                    "portfolio_id": str(self.portfolio_id),
                    "total_allocation": str(total_allocation),
                    "tolerance": str(tolerance),
                },
            )
            raise ValueError(f"Asset class allocations must sum to 100%, got {total_allocation}")

        logger.debug(
            "PortfolioAllocation validation passed",
            extra={
                "portfolio_id": str(self.portfolio_id),
                "total_allocation": str(total_allocation),
            },
        )
        return self


class PortfolioRebalance(BaseModel):
    """Portfolio rebalancing recommendations."""

    id: UUID = Field(default_factory=uuid4, description="Unique rebalance identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    rebalance_date: datetime = Field(default_factory=datetime.utcnow, description="Rebalance date")

    # Rebalancing Triggers
    trigger_reason: str = Field(..., description="Reason for rebalancing")
    trigger_threshold: Decimal = Field(..., description="Threshold that triggered rebalancing")

    # Current vs Target
    current_allocation: PortfolioAllocation = Field(..., description="Current allocation")
    target_allocation: PortfolioAllocation = Field(..., description="Target allocation")

    # Rebalancing Actions
    rebalance_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Rebalancing actions"
    )
    estimated_cost: Decimal = Field(default=Decimal("0"), description="Estimated rebalancing cost")

    # Risk Impact
    risk_impact: Decimal = Field(..., description="Expected risk impact")
    return_impact: Decimal = Field(..., description="Expected return impact")

    # Execution
    execution_date: Optional[datetime] = Field(None, description="Execution date")
    execution_status: str = Field(default="pending", description="Execution status")

    @field_validator("trigger_threshold", "estimated_cost", "risk_impact", "return_impact")
    @classmethod
    def validate_impact_fields(cls, v: object) -> Decimal:
        """Validate impact fields are reasonable."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Impact fields must be numbers")

        return Decimal(str(v))


class PortfolioComparison(BaseModel):
    """Portfolio comparison analysis."""

    id: UUID = Field(default_factory=uuid4, description="Unique comparison identifier")
    portfolio_ids: list[UUID] = Field(..., description="Portfolio IDs to compare")
    comparison_date: datetime = Field(
        default_factory=datetime.utcnow, description="Comparison date"
    )

    # Performance Comparison
    performance_comparison: dict[str, PortfolioPerformanceRecord] = Field(
        ..., description="Performance comparison"
    )
    risk_comparison: dict[str, RiskMetrics] = Field(..., description="Risk comparison")

    # Ranking
    performance_ranking: list[tuple[UUID, Decimal]] = Field(..., description="Performance ranking")
    risk_ranking: list[tuple[UUID, Decimal]] = Field(..., description="Risk ranking")
    sharpe_ranking: list[tuple[UUID, Decimal]] = Field(..., description="Sharpe ratio ranking")

    # Analysis
    best_performer: UUID = Field(..., description="Best performing portfolio")
    lowest_risk: UUID = Field(..., description="Lowest risk portfolio")
    best_risk_adjusted: UUID = Field(..., description="Best risk-adjusted portfolio")

    # Summary
    comparison_summary: str = Field(..., description="Comparison summary")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")

    @model_validator(mode="after")
    def validate_comparison_data(self) -> "PortfolioComparison":
        """Validate comparison data consistency."""
        logger.debug(
            "Validating portfolio comparison data",
            extra={"num_portfolios": len(self.portfolio_ids)},
        )
        if len(self.portfolio_ids) < 2:
            logger.error(
                "PortfolioComparison validation failed: insufficient portfolios",
                extra={"num_portfolios": len(self.portfolio_ids)},
            )
            raise ValueError("At least 2 portfolios required for comparison")

        if len(self.portfolio_ids) != len(self.performance_comparison):
            logger.error(
                "PortfolioComparison validation failed: missing performance data",
                extra={
                    "num_portfolios": len(self.portfolio_ids),
                    "num_performance_records": len(self.performance_comparison),
                },
            )
            raise ValueError("Performance comparison must include all portfolios")

        logger.debug(
            "PortfolioComparison validation passed",
            extra={"num_portfolios": len(self.portfolio_ids)},
        )
        return self
