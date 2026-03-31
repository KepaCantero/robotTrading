"""
PHASE 3 - Data Models for Dynamic Risk Scaling

Core data structures for risk scaling system with Pydantic validation.
Handles scaling factors, state management, alerts, and reporting.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class RiskAlertType(str, Enum):
    """Types of risk alerts."""

    VOLATILITY_SPIKE = "volatility_spike"
    SHARPE_DECLINE = "sharpe_decline"
    LOSS_STREAK = "loss_streak"
    DRAWDOWN_WARNING = "drawdown_warning"
    HALT_TRADING = "halt_trading"
    SCALING_EXTREME = "scaling_extreme"
    CIRCUIT_BREAKER = "circuit_breaker"


class RiskLevel(str, Enum):
    """Portfolio risk levels."""

    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    HALT = "halt"


# ============================================================================
# SCALING FACTORS & STATE MODELS
# ============================================================================


class RiskScalingFactors(BaseModel):
    """All scaling factors combined for a portfolio."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    volatility_scale: Decimal = Field(
        ...,
        ge=Decimal("0.5"),
        le=Decimal("1.5"),
        description="ATR-based scaling factor (0.5 to 1.5)",
    )
    sharpe_scale: Decimal = Field(
        ...,
        ge=Decimal("0.2"),
        le=Decimal("1.0"),
        description="Sharpe ratio-based scaling (0.2 to 1.0)",
    )
    loss_scale: Decimal = Field(
        ...,
        ge=Decimal("0.5"),
        le=Decimal("1.0"),
        description="Loss streak-based scaling (0.5 to 1.0)",
    )
    drawdown_scale: Decimal = Field(
        ..., ge=Decimal("0.0"), le=Decimal("1.0"), description="Drawdown-based scaling (0.0 to 1.0)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When these factors were calculated"
    )

    @property
    def combined_scale(self) -> Decimal:
        """Calculate combined scaling factor (product of all factors)."""
        return self.volatility_scale * self.sharpe_scale * self.loss_scale * self.drawdown_scale

    @property
    def is_extreme(self) -> bool:
        """Check if any single factor is at extreme value."""
        return (
            self.volatility_scale <= Decimal("0.6")
            or self.volatility_scale >= Decimal("1.4")
            or self.sharpe_scale <= Decimal("0.3")
            or self.loss_scale <= Decimal("0.6")
            or self.drawdown_scale <= Decimal("0.2")
        )

    @property
    def is_halted(self) -> bool:
        """Check if trading should be halted (drawdown_scale = 0)."""
        return self.drawdown_scale == Decimal("0")


class RiskScalingSnapshot(BaseModel):
    """Historical snapshot of risk scaling state at a point in time."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    snapshot_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique snapshot ID")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this snapshot was taken"
    )
    scaling_factors: RiskScalingFactors = Field(..., description="All scaling factors at this time")
    current_atr: Decimal = Field(..., ge=Decimal("0"), description="Current ATR value")
    average_atr: Decimal = Field(..., ge=Decimal("0"), description="Historical average ATR")
    sharpe_ratio: Decimal = Field(..., description="Current rolling Sharpe ratio")
    consecutive_losses: int = Field(
        default=0, ge=0, description="Number of consecutive losing trades"
    )
    current_drawdown: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Current drawdown as percentage (0-1)",
    )
    max_drawdown: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("1"), description="Max drawdown in period"
    )


class RiskAlert(BaseModel):
    """Single risk alert."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    alert_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique alert ID")
    alert_type: RiskAlertType = Field(..., description="Type of alert")
    severity: RiskLevel = Field(..., description="Severity level")
    message: str = Field(..., min_length=10, description="Human-readable alert message")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When alert was triggered"
    )
    portfolio_id: str = Field(..., description="Portfolio that triggered alert")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional context (current_value, threshold, etc)"
    )
    resolved: bool = Field(default=False, description="Whether alert has been resolved")
    resolved_at: Optional[datetime] = Field(None, description="When alert was resolved")


class RiskScalingState(BaseModel):
    """Complete risk scaling state snapshot for a portfolio."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    state_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique state ID")
    portfolio_id: str = Field(..., description="Portfolio ID being monitored")
    scaling_factors: RiskScalingFactors = Field(..., description="Current scaling factors")
    current_atr: Decimal = Field(..., ge=Decimal("0"), description="Current ATR value")
    sharpe_ratio: Decimal = Field(..., description="Rolling Sharpe ratio")
    consecutive_losses: int = Field(default=0, ge=0, description="Consecutive losing trades")
    current_drawdown: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("1"), description="Current drawdown %"
    )
    max_drawdown: Decimal = Field(
        default=Decimal("0"), ge=Decimal("0"), le=Decimal("1"), description="Max drawdown in period"
    )
    scaling_history: list[RiskScalingSnapshot] = Field(
        default_factory=list, description="Historical snapshots (last 30 days)"
    )
    active_alerts: list[RiskAlert] = Field(
        default_factory=list, description="Currently active alerts"
    )
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")


# ============================================================================
# SIGNAL & POSITION ADJUSTMENT MODELS
# ============================================================================


class AdjustedPositionSizes(BaseModel):
    """Position sizes after applying risk scaling."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    original_size: Decimal = Field(
        ..., gt=Decimal("0"), description="Original position size before scaling"
    )
    adjusted_size: Decimal = Field(
        ..., ge=Decimal("0"), description="Size after applying all scaling factors"
    )
    scaling_factor: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("1.5"), description="Final combined scaling factor applied"
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for size adjustment (high vol, negative Sharpe, etc)",
    )
    original_stop_loss: Optional[Decimal] = Field(None, description="Original stop loss price")
    adjusted_stop_loss: Optional[Decimal] = Field(
        None, description="Stop loss adjusted for volatility"
    )


class Signal(BaseModel):
    """Trade signal before applying risk scaling."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    signal_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique signal identifier"
    )
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="buy or sell")
    strength: Decimal = Field(
        ..., ge=Decimal("0"), le=Decimal("1"), description="Signal strength (0-1)"
    )
    base_position_size: Decimal = Field(..., gt=Decimal("0"), description="Base position size")
    entry_price: Decimal = Field(..., gt=Decimal("0"), description="Entry price")
    stop_loss_price: Optional[Decimal] = Field(None, description="Stop loss price")


class AdjustedSignal(BaseModel):
    """Trade signal after applying risk scaling."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    signal_id: str = Field(..., description="Original signal ID")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="buy or sell")
    original_position_size: Decimal = Field(
        ..., gt=Decimal("0"), description="Original position size"
    )
    adjusted_position_size: Decimal = Field(
        ..., ge=Decimal("0"), description="Size after scaling (may be 0 if rejected)"
    )
    is_rejected: bool = Field(
        default=False, description="True if signal was rejected due to scaling"
    )
    rejection_reason: Optional[str] = Field(None, description="Why signal was rejected")
    scaling_factors: Optional[RiskScalingFactors] = Field(
        None, description="Scaling factors applied"
    )
    original_stop_loss: Optional[Decimal] = Field(None, description="Original stop loss")
    adjusted_stop_loss: Optional[Decimal] = Field(
        None, description="Stop loss after volatility adjustment"
    )


# ============================================================================
# MONITORING & REPORTING MODELS
# ============================================================================


class RiskScalingStatus(BaseModel):
    """Current risk scaling status for dashboard/API."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    portfolio_id: str = Field(..., description="Portfolio ID")
    scaling_factors: RiskScalingFactors = Field(..., description="Current scaling factors")
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    active_alerts_count: int = Field(default=0, ge=0, description="Number of active alerts")
    active_alerts: list[RiskAlert] = Field(
        default_factory=list, description="List of active alerts"
    )
    last_update: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    next_recalc_at: datetime = Field(..., description="When scaling will be recalculated")


class AlertSubscription(BaseModel):
    """Alert subscription configuration."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    subscription_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique subscription ID"
    )
    portfolio_id: str = Field(..., description="Portfolio to monitor")
    alert_types: list[RiskAlertType] = Field(
        ..., min_length=1, description="Types of alerts to receive"
    )
    min_severity: RiskLevel = Field(
        default=RiskLevel.WARNING, description="Minimum severity to alert on"
    )
    subscribed_at: datetime = Field(
        default_factory=datetime.now, description="When subscription created"
    )
    enabled: bool = Field(default=True, description="Whether subscription is active")


class RiskScalingReport(BaseModel):
    """Human-readable risk scaling status report."""

    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        extra="forbid",
    )

    report_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique report ID")
    portfolio_id: str = Field(..., description="Portfolio ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Report generation time")
    period: str = Field(..., description="Reporting period (e.g., 'last_24h', 'last_7d')")

    # Scaling status
    current_combined_scale: Decimal = Field(..., description="Current combined scaling factor")
    volatility_scale: Decimal = Field(...)
    sharpe_scale: Decimal = Field(...)
    loss_scale: Decimal = Field(...)
    drawdown_scale: Decimal = Field(...)

    # Metrics
    current_atr: Decimal = Field(...)
    avg_atr: Decimal = Field(...)
    sharpe_ratio: Decimal = Field(...)
    consecutive_losses: int = Field(...)
    current_drawdown: Decimal = Field(...)
    max_drawdown: Decimal = Field(...)

    # Alerts & warnings
    active_alerts: list[str] = Field(
        default_factory=list, description="List of active alert messages"
    )
    recent_events: list[str] = Field(default_factory=list, description="Recent significant events")

    # Summary
    summary: str = Field(..., description="Human-readable summary of status")

    def __str__(self) -> str:
        """Generate formatted report string."""
        lines = [
            f"\n{'=' * 60}",
            f"RISK SCALING REPORT - {self.portfolio_id}",
            f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Period: {self.period}",
            f"{'=' * 60}\n",
            f"COMBINED SCALING FACTOR: {self.current_combined_scale:.3f}",
            f"  Volatility Scale (ATR): {self.volatility_scale:.3f}",
            f"  Performance Scale (Sharpe): {self.sharpe_scale:.3f}",
            f"  Loss Scale: {self.loss_scale:.3f}",
            f"  Drawdown Scale: {self.drawdown_scale:.3f}\n",
            "MARKET CONDITIONS:",
            f"  Current ATR: {self.current_atr:.4f}",
            f"  Average ATR (14d): {self.avg_atr:.4f}",
            f"  Volatility Status: {'HIGH' if self.current_atr > self.avg_atr else 'LOW'}\n",
            "PERFORMANCE:",
            f"  Sharpe Ratio (30d): {self.sharpe_ratio:.3f}",
            f"  Consecutive Losses: {self.consecutive_losses}",
            f"  Status: {'LOSS STREAK' if self.consecutive_losses > 2 else 'NORMAL'}\n",
            "RISK EXPOSURE:",
            f"  Current Drawdown: {self.current_drawdown:.1%}",
            f"  Max Drawdown: {self.max_drawdown:.1%}",
            f"  Status: {'HALT TRADING' if self.drawdown_scale == Decimal('0') else 'TRADING'}\n",
            f"ALERTS ({len(self.active_alerts)} active):",
        ]

        for alert in self.active_alerts:
            lines.append(f"  • {alert}")

        lines.extend(
            [
                f"\n{'=' * 60}",
                f"SUMMARY: {self.summary}",
                f"{'=' * 60}\n",
            ]
        )

        return "\n".join(lines)
