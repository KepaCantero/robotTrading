"""
T9.1: ReportingGenerator - Models for performance reporting

Generates comprehensive performance reports with visualizations and metrics.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PerformanceMetric(BaseModel):
    """Individual performance metric."""

    name: str = Field(..., description="Metric name")
    value: Decimal = Field(..., description="Metric value")
    unit: str = Field(default="", description="Unit of measurement")
    target: Optional[Decimal] = Field(None, description="Target value")
    status: str = Field(default="neutral", description="Status: green/yellow/red")


class StrategyMetrics(BaseModel):
    """Comprehensive strategy performance metrics."""

    annual_return_pct: Decimal = Field(..., description="Annual return percentage")
    sharpe_ratio: Decimal = Field(..., description="Sharpe ratio")
    sortino_ratio: Decimal = Field(..., description="Sortino ratio")
    max_drawdown_pct: Decimal = Field(..., description="Maximum drawdown percentage")
    win_rate_pct: Decimal = Field(..., description="Win rate percentage")
    profit_factor: Decimal = Field(..., description="Profit factor (wins/losses)")
    calmar_ratio: Decimal = Field(..., description="Calmar ratio (return/max drawdown)")
    volatility_pct: Decimal = Field(..., description="Annual volatility")
    cumulative_return_pct: Decimal = Field(..., description="Cumulative return")
    num_trades: int = Field(default=0, description="Number of trades executed")


class AllocationSnapshot(BaseModel):
    """Portfolio allocation snapshot."""

    module_name: str = Field(..., description="Module name")
    allocation_pct: Decimal = Field(..., description="Allocation percentage")
    expected_return_contribution_pct: Decimal = Field(
        ..., description="Expected return contribution"
    )
    risk_contribution_pct: Decimal = Field(..., description="Risk contribution")


class ReportGenerationRequest(BaseModel):
    """Request for generating performance report."""

    report_id: str = Field(..., description="Unique report identifier")
    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="User input ID")
    strategy_name: str = Field(..., description="Name of the strategy")

    # Historical performance data
    backtest_metrics: StrategyMetrics = Field(..., description="Backtest performance metrics")

    # Portfolio allocation
    allocations: list[AllocationSnapshot] = Field(..., description="Portfolio allocations")

    # Additional context
    capital_eur: Decimal = Field(..., description="Capital in EUR")
    target_annual_return_pct: Decimal = Field(..., description="Target annual return")
    max_acceptable_drawdown_pct: Decimal = Field(..., description="Max acceptable drawdown")

    # Execution context
    execution_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation timestamp"
    )


class PerformanceReport(BaseModel):
    """Complete performance report."""

    success: bool = Field(default=True, description="Report generation success")
    report_id: str = Field(..., description="Report ID")
    profile_id: str = Field(..., description="Profile ID")
    strategy_name: str = Field(..., description="Strategy name")

    # Report content
    title: str = Field(..., description="Report title")
    summary: str = Field(..., description="Executive summary")

    # Detailed metrics
    metrics: StrategyMetrics = Field(..., description="Performance metrics")

    # Allocation details
    allocations: list[AllocationSnapshot] = Field(..., description="Portfolio allocations")

    # Performance assessment
    overall_rating: str = Field(
        default="neutral", description="Overall rating: excellent/good/neutral/poor"
    )
    strengths: list[str] = Field(default=[], description="Strategy strengths identified")
    weaknesses: list[str] = Field(default=[], description="Strategy weaknesses identified")
    recommendations: list[str] = Field(default=[], description="Recommendations for improvement")

    # Report metadata
    html_content: Optional[str] = Field(None, description="HTML report content")
    charts_data: Optional[dict[str, Any]] = Field(None, description="Chart data for visualization")

    # Report timing
    generation_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Report generation time"
    )

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")


logger.debug(
    "ReportingGenerator models loaded",
    extra={
        "component": "reporting_generator_models",
        "operation": "module_init",
        "models": [
            "PerformanceMetric",
            "StrategyMetrics",
            "AllocationSnapshot",
            "ReportGenerationRequest",
            "PerformanceReport",
        ],
    },
)
