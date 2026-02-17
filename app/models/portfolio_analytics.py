"""
Enhanced Portfolio Management Models

This module defines enhanced models for portfolio management including
performance metrics, risk analysis, and portfolio analytics.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.portfolio import Portfolio as BasePortfolio


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
        from app.core.centralized_config import get_config
        cfg = get_config()

        if self.cash_balance != self.cash:
            raise ValueError("Cash balance must match cash field")

        # Calculate total value from positions and cash
        calculated_total = self.cash
        for position in self.positions:
            calculated_total += position.market_value

        # Get tolerance from config
        tolerance = Decimal(str(getattr(cfg.trading, 'portfolio_value_tolerance', 0.01)))
        if abs(self.total_value - calculated_total) > tolerance:
            raise ValueError(
                f"Total value mismatch. Expected: {calculated_total}, Got: {self.total_value}"
            )

        return self

    @property
    def equity_value(self) -> Decimal:
        """Calculate total equity value."""
        return sum(pos.market_value for pos in self.positions)


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


class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics."""

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
    def validate_percentage_fields(cls, v) -> Decimal:
        """Validate percentage fields are reasonable."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Percentage fields must be numbers")

        # Allow reasonable ranges for financial metrics
        if v < Decimal("-100") or v > Decimal("1000"):
            raise ValueError(f"Percentage field out of reasonable range: {v}")

        return v

    @field_validator("total_value", "cash_value", "equity_value")
    @classmethod
    def validate_value_fields(cls, v) -> Decimal:
        """Validate value fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Value fields must be numbers")

        if v < 0:
            raise ValueError(f"Value fields must be non-negative: {v}")

        return v

    @model_validator(mode="after")
    def validate_metrics_consistency(self) -> "PerformanceMetrics":
        """Validate consistency between metrics."""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")

        if self.cash_value + self.equity_value != self.total_value:
            raise ValueError("Cash + Equity must equal total value")

        return self


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
    def validate_volatility_fields(cls, v) -> Decimal:
        """Validate volatility fields are non-negative."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Volatility fields must be numbers")

        if v < 0:
            raise ValueError(f"Volatility fields must be non-negative: {v}")

        return v


class PortfolioAnalytics(BaseModel):
    """Comprehensive portfolio analytics."""

    id: UUID = Field(default_factory=uuid4, description="Unique analytics identifier")
    portfolio_id: UUID = Field(..., description="Portfolio identifier")
    analysis_date: datetime = Field(default_factory=datetime.utcnow, description="Analysis date")

    # Performance Summary
    performance_metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    risk_metrics: RiskMetrics = Field(..., description="Risk metrics")

    # Risk Assessment
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_score: Decimal = Field(..., description="Risk score (0-100)")

    # Portfolio Health
    health_score: Decimal = Field(..., description="Portfolio health score (0-100)")
    diversification_score: Decimal = Field(..., description="Diversification score (0-100)")
    liquidity_score: Decimal = Field(..., description="Liquidity score (0-100)")

    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list, description="Portfolio recommendations"
    )
    warnings: List[str] = Field(default_factory=list, description="Portfolio warnings")

    # Metadata
    analysis_version: str = Field(default="1.0", description="Analysis version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("risk_score", "health_score", "diversification_score", "liquidity_score")
    @classmethod
    def validate_score_fields(cls, v) -> Decimal:
        """Validate score fields are between 0 and 100."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Score fields must be numbers")

        if v < 0 or v > 100:
            raise ValueError(f"Score fields must be between 0 and 100: {v}")

        return v


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
    sector_allocations: Dict[str, Decimal] = Field(
        default_factory=dict, description="Sector allocations"
    )

    # Top Holdings
    top_holdings: List[Dict[str, Any]] = Field(default_factory=list, description="Top holdings")

    # Allocation Quality
    target_allocation: Optional[Dict[str, Decimal]] = Field(None, description="Target allocation")
    allocation_deviation: Optional[Dict[str, Decimal]] = Field(
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
    def validate_allocation_fields(cls, v) -> Decimal:
        """Validate allocation fields are between 0 and 100."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Allocation fields must be numbers")

        if v < 0 or v > 100:
            raise ValueError(f"Allocation fields must be between 0 and 100: {v}")

        return v

    @model_validator(mode="after")
    def validate_allocation_sum(self) -> "PortfolioAllocation":
        """Validate that allocations sum to 100%."""
        from app.core.centralized_config import get_config
        cfg = get_config()

        total_allocation = (
            self.equity_allocation
            + self.fixed_income_allocation
            + self.cash_allocation
            + self.alternative_allocation
        )

        # Get tolerance from config
        tolerance = Decimal(str(getattr(cfg.trading, 'portfolio_allocation_tolerance', 0.01)))
        if abs(total_allocation - Decimal("100")) > tolerance:
            raise ValueError(f"Asset class allocations must sum to 100%, got {total_allocation}")

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
    rebalance_actions: List[Dict[str, Any]] = Field(
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
    def validate_impact_fields(cls, v) -> Decimal:
        """Validate impact fields are reasonable."""
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif not isinstance(v, Decimal):
            raise ValueError("Impact fields must be numbers")

        return v


class PortfolioComparison(BaseModel):
    """Portfolio comparison analysis."""

    id: UUID = Field(default_factory=uuid4, description="Unique comparison identifier")
    portfolio_ids: List[UUID] = Field(..., description="Portfolio IDs to compare")
    comparison_date: datetime = Field(
        default_factory=datetime.utcnow, description="Comparison date"
    )

    # Performance Comparison
    performance_comparison: Dict[str, PerformanceMetrics] = Field(
        ..., description="Performance comparison"
    )
    risk_comparison: Dict[str, RiskMetrics] = Field(..., description="Risk comparison")

    # Ranking
    performance_ranking: List[Tuple[UUID, Decimal]] = Field(..., description="Performance ranking")
    risk_ranking: List[Tuple[UUID, Decimal]] = Field(..., description="Risk ranking")
    sharpe_ranking: List[Tuple[UUID, Decimal]] = Field(..., description="Sharpe ratio ranking")

    # Analysis
    best_performer: UUID = Field(..., description="Best performing portfolio")
    lowest_risk: UUID = Field(..., description="Lowest risk portfolio")
    best_risk_adjusted: UUID = Field(..., description="Best risk-adjusted portfolio")

    # Summary
    comparison_summary: str = Field(..., description="Comparison summary")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")

    @model_validator(mode="after")
    def validate_comparison_data(self) -> "PortfolioComparison":
        """Validate comparison data consistency."""
        if len(self.portfolio_ids) < 2:
            raise ValueError("At least 2 portfolios required for comparison")

        if len(self.portfolio_ids) != len(self.performance_comparison):
            raise ValueError("Performance comparison must include all portfolios")

        return self
