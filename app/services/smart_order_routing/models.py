"""
PHASE 2 T2.1 - Data Models for Smart Order Routing

Core data structures for execution planning, monitoring, and cost analysis.
All models use Pydantic for validation with strict mode and type checking.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# ============================================================================
# EXECUTION PLANNING MODELS
# ============================================================================


@dataclass
class TimeWindow:
    """Represents a time window for execution (used in scheduling)."""

    start: str  # HH:MM format
    end: str  # HH:MM format
    name: str  # "post_open", "post_lunch", etc


class OrderTranche(BaseModel):
    """
    Single execution tranche (part of a larger order).

    Tranches are executed sequentially or in parallel depending on strategy.
    Each tranche tracks its own execution timing, price, and status.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    tranche_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique identifier for this tranche"
    )
    symbol: str = Field(..., description="Trading symbol (e.g., 'AAPL')")
    size: Decimal = Field(
        ..., gt=Decimal("0"), description="Size of this tranche in currency units (€)"
    )
    execution_time: datetime = Field(..., description="Scheduled execution time")
    execution_window: Optional[TimeWindow] = Field(
        None, description="Time window constraints for execution"
    )
    target_price: Optional[Decimal] = Field(None, description="Target execution price (optional)")
    status: str = Field(
        default="pending", description="pending | submitted | filled | partial | rejected"
    )
    actual_price: Optional[Decimal] = Field(
        None, description="Actual execution price (filled after execution)"
    )
    actual_size: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), description="Actual executed size"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status is one of allowed values."""
        allowed = {"pending", "submitted", "filled", "partial", "rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("actual_size")
    @classmethod
    def validate_actual_size(cls, v: Decimal, info) -> Decimal:
        """Validate actual_size doesn't exceed size."""
        if "size" in info.data and v > info.data["size"]:
            raise ValueError("actual_size cannot exceed size")
        return v

    def is_filled(self) -> bool:
        """Check if tranche is fully filled."""
        return self.actual_size >= self.size

    def is_partially_filled(self) -> bool:
        """Check if tranche is partially filled."""
        return Decimal("0") < self.actual_size < self.size


class ExecutionPlan(BaseModel):
    """
    Master execution plan with all tranches and constraints.

    Contains the complete strategy for executing a large order,
    including timing, sizing, cost budget, and constraints.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    execution_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique execution plan identifier"
    )
    symbol: str = Field(..., description="Trading symbol")
    total_size: Decimal = Field(
        ..., gt=Decimal("0"), description="Total order size in currency units (€)"
    )
    tranches: List[OrderTranche] = Field(
        ..., description="List of execution tranches (empty for dynamic strategies like POI)"
    )
    strategy: str = Field(
        ..., description="Execution strategy: vwap | twap | poi | intraday_phased"
    )
    cost_budget: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Max allowed execution cost in €"
    )
    max_execution_time_ms: int = Field(
        default=300_000, gt=0, description="Max execution time in milliseconds"
    )
    estimated_avg_price: Optional[Decimal] = Field(
        None, gt=Decimal("0"), description="Estimated average fill price"
    )
    constraints: Dict[str, Decimal] = Field(
        default_factory=dict, description="Execution constraints (max_per_tranche, max_spread, etc)"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Plan creation timestamp"
    )

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate strategy is recognized."""
        allowed = {"vwap", "twap", "poi", "intraday_phased"}
        if v not in allowed:
            raise ValueError(f"Strategy must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_plan_consistency(self) -> "ExecutionPlan":
        """Validate that tranches sum to total_size (except for dynamic strategies like POI)."""
        # POI strategy leaves tranches empty for dynamic execution
        if self.strategy == "poi":
            return self

        # For other strategies, tranches must sum to total_size
        if self.tranches:  # Only validate if tranches exist
            tranches_total = sum(t.size for t in self.tranches)
            if tranches_total != self.total_size:
                raise ValueError(
                    f"Tranche sizes {tranches_total} don't sum to total_size {self.total_size}"
                )
        return self

    def validate(self) -> Tuple[bool, str]:
        """
        Comprehensive validation of execution plan.

        Returns:
            (is_valid, message)
        """
        try:
            self.model_validate(self.model_dump())
            return True, "Execution plan valid"
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            return False, str(e)


# ============================================================================
# MARKET IMPACT & COST ESTIMATION MODELS
# ============================================================================


class MarketImpactEstimate(BaseModel):
    """
    Estimated execution cost breakdown.

    Combines market impact, spread impact, and other costs
    to estimate total execution cost in basis points and currency.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    symbol: str = Field(..., description="Trading symbol")
    participation_rate: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("1"), description="Order size / daily volume"
    )
    sqrt_impact: Decimal = Field(
        ..., ge=Decimal("0"), description="sqrt(participation_rate) - market impact multiplier"
    )
    volatility_multiplier: Decimal = Field(
        ..., ge=Decimal("0"), description="Volatility adjustment factor"
    )
    spread_impact: Decimal = Field(
        ..., ge=Decimal("0"), description="Bid-ask spread impact in basis points"
    )
    estimated_slippage_bps: Decimal = Field(
        ..., ge=Decimal("0"), description="Total estimated slippage in basis points (1 bps = 0.01%)"
    )
    estimated_slippage_usd: Decimal = Field(
        ..., ge=Decimal("0"), description="Total estimated slippage in currency units (€)"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Estimate timestamp")

    @field_validator("estimated_slippage_bps")
    @classmethod
    def validate_slippage_realistic(cls, v: Decimal) -> Decimal:
        """Validate slippage is within realistic bounds (0-500 bps)."""
        if v > Decimal("500"):
            raise ValueError(f"Slippage {v} bps exceeds realistic max (500 bps)")
        return v


# ============================================================================
# EXECUTION MONITORING MODELS
# ============================================================================


class ExecutionMonitoring(BaseModel):
    """
    Real-time monitoring of execution against planned budget.

    Tracks actual costs vs planned, provides alerts on overruns,
    and calculates performance metrics.
    """

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    execution_id: str = Field(..., description="Execution plan ID being monitored")
    planned_cost: Decimal = Field(
        ..., ge=Decimal("0"), description="Planned maximum cost budget in €"
    )
    actual_costs: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), description="Actual accumulated costs so far in €"
    )
    tranches_completed: int = Field(default=0, ge=0, description="Number of tranches completed")
    tranches_total: int = Field(..., gt=0, description="Total number of tranches in execution plan")
    started_at: datetime = Field(
        default_factory=datetime.now, description="Execution start timestamp"
    )
    completed_at: Optional[datetime] = Field(None, description="Execution completion timestamp")

    @property
    def cost_overrun(self) -> Decimal:
        """Calculate cost overrun vs budget."""
        return max(Decimal("0"), self.actual_costs - self.planned_cost)

    @property
    def cost_overrun_pct(self) -> Decimal:
        """Calculate cost overrun percentage."""
        if self.planned_cost == Decimal("0"):
            return Decimal("0")
        return (self.cost_overrun / self.planned_cost) * Decimal("100")

    @property
    def is_within_budget(self) -> bool:
        """Check if execution is within planned budget."""
        return self.actual_costs <= self.planned_cost

    @property
    def progress_pct(self) -> Decimal:
        """Calculate completion progress percentage."""
        if self.tranches_total == 0:
            return Decimal("0")
        return (Decimal(self.tranches_completed) / Decimal(self.tranches_total)) * Decimal("100")

    @property
    def execution_duration(self) -> Optional[timedelta]:
        """Calculate execution duration."""
        if self.completed_at is None:
            return None
        return self.completed_at - self.started_at

    def validate(self) -> Tuple[bool, str]:
        """Validate monitoring data consistency."""
        if self.tranches_completed > self.tranches_total:
            return False, "tranches_completed exceeds tranches_total"
        return True, "Monitoring valid"

    def log_cost_overrun_alert(self):
        """Log a warning if cost overrun detected."""
        if self.cost_overrun > Decimal("0"):
            logger.warning(
                f"Execution {self.execution_id}: Cost overrun detected! "
                f"Actual: €{self.actual_costs:,.2f}, "
                f"Budget: €{self.planned_cost:,.2f}, "
                f"Overrun: €{self.cost_overrun:,.2f} ({self.cost_overrun_pct:.1f}%)"
            )


# ============================================================================
# COMMISSION & BROKER MODELS
# ============================================================================


class CommissionTier(BaseModel):
    """Represents a commission tier for a broker."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    name: str = Field(..., description="Tier name (retail, semi_pro, pro, institutional)")
    min_volume: Decimal = Field(
        ..., ge=Decimal("0"), description="Minimum volume to qualify for this tier"
    )
    max_volume: Optional[Decimal] = Field(None, description="Maximum volume (None = unlimited)")
    commission_rate: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("0.01"),
        description="Commission rate as decimal (e.g., 0.001 = 0.1%)",
    )

    @field_validator("max_volume")
    @classmethod
    def validate_volume_range(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate max >= min."""
        if v is None:
            return None
        if "min_volume" in info.data and v < info.data["min_volume"]:
            raise ValueError("max_volume must be >= min_volume")
        return v
