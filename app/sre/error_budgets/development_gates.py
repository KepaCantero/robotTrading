"""
Development Gates - Auto-Halt When Budget Exhausted (SRE Rule 20)

Implements deployment gates that automatically halt deployments
when error budgets are exhausted or at risk.

Gate Types:
- Budget Gate: Blocks deployment when budget exhausted
- SLO Gate: Blocks deployment when SLOs violated
- Burn Rate Gate: Warns when consuming budget too fast
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from .error_budget_manager import ErrorBudgetManager
from .slo_tracker import SLOTracker

logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    """Status of development gate."""

    PASS = "pass"  # Deployment allowed
    FAIL = "fail"  # Deployment blocked
    WARN = "warn"  # Deployment allowed with warnings


class GateType(str, Enum):
    """Types of development gates."""

    ERROR_BUDGET = "error_budget"  # Check error budget
    SLO_COMPLIANCE = "slo_compliance"  # Check SLO compliance
    BURN_RATE = "burn_rate"  # Check burn rate
    ACTIVE_VIOLATIONS = "active_violations"  # Check for active SLO violations


@dataclass
class GateDecision:
    """Decision from a development gate."""

    gate_type: GateType
    status: GateStatus
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    can_override: bool = False
    override_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gate_type": self.gate_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "can_override": self.can_override,
            "override_reason": self.override_reason,
        }


@dataclass
class DeploymentBlocker:
    """Information about why deployment is blocked."""

    block_reason: str
    blocking_gate: GateType
    budget_remaining_pct: Optional[Decimal] = None
    active_violations: List[str] = field(default_factory=list)
    blocked_at: datetime = field(default_factory=datetime.utcnow)
    estimated_recovery: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "block_reason": self.block_reason,
            "blocking_gate": self.blocking_gate.value,
            "budget_remaining_pct": (
                f"{self.budget_remaining_pct:.2f}%" if self.budget_remaining_pct else None
            ),
            "active_violations": self.active_violations,
            "blocked_at": self.blocked_at.isoformat(),
            "estimated_recovery": (
                self.estimated_recovery.isoformat() if self.estimated_recovery else None
            ),
        }


@dataclass
class DevelopmentGateConfig:
    """Configuration for development gates."""

    # Error budget thresholds
    budget_exhausted_threshold_pct: Decimal = Decimal("10")  # Block below 10%
    budget_warning_threshold_pct: Decimal = Decimal("25")  # Warn below 25%

    # SLO thresholds
    max_allowed_violations: int = 0  # Block with any active violation
    slo_compliance_threshold: Decimal = Decimal("0.95")  # 95% compliance required

    # Burn rate thresholds
    max_burn_rate: Decimal = Decimal("2.0")  # Warn above 2x normal

    # Override settings
    allow_override: bool = True
    override_require_approval: bool = True
    override_approvers: List[str] = field(default_factory=list)

    # Gate timeout (auto-recover after N minutes if conditions improve)
    gate_timeout_minutes: int = 60


class DevelopmentGate:
    """
    Development gate for deployment approval.

    Evaluates deployment readiness based on:
    - Error budget status
    - SLO compliance
    - Burn rate
    - Active violations

    Integrates with deployment pipeline to auto-halt when needed.
    """

    def __init__(
        self,
        service_name: str,
        error_budget_manager: ErrorBudgetManager,
        slo_tracker: Optional[SLOTracker] = None,
        config: Optional[DevelopmentGateConfig] = None,
    ):
        """
        Initialize development gate.

        Args:
            service_name: Name of the service
            error_budget_manager: Error budget manager
            slo_tracker: Optional SLO tracker
            config: Gate configuration
        """
        self.service_name = service_name
        self.error_budget_manager = error_budget_manager
        self.slo_tracker = slo_tracker
        self.config = config or DevelopmentGateConfig()
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Current block state
        self._current_blocker: Optional[DeploymentBlocker] = None

        # Decision history
        self._decision_history: List[GateDecision] = []

        # Override tracking
        self._active_overrides: Dict[str, datetime] = {}

        # Lock
        self._lock = asyncio.Lock()

        self.logger.info(f"DevelopmentGate initialized for {service_name}")

    async def check_deployment_allowed(
        self,
        requesting_user: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> tuple[bool, List[GateDecision], Optional[DeploymentBlocker]]:
        """
        Check if deployment is allowed.

        Args:
            requesting_user: User requesting deployment (for overrides)
            reason: Reason for deployment (for overrides)

        Returns:
            Tuple of (allowed, decisions, blocker)
        """
        async with self._lock:
            decisions = []

            try:
                # Check error budget gate
                budget_decision = await self._check_error_budget_gate()
                decisions.append(budget_decision)

                # Check SLO compliance gate
                if self.slo_tracker:
                    slo_decision = await self._check_slo_compliance_gate()
                    decisions.append(slo_decision)

                    # Check active violations gate
                    violation_decision = await self._check_active_violations_gate()
                    decisions.append(violation_decision)

                # Check burn rate gate
                burn_rate_decision = await self._check_burn_rate_gate()
                decisions.append(burn_rate_decision)

                # Determine overall result
                has_fail = any(d.status == GateStatus.FAIL for d in decisions)
                any(d.status == GateStatus.WARN for d in decisions)

                allowed = not has_fail

                # Create blocker if needed
                blocker = None
                if not allowed:
                    blocker = await self._create_blocker(decisions)

                    # Check for override
                    if await self._check_override(requesting_user, reason):
                        allowed = True
                        blocker = None
                        self.logger.warning(
                            f"Deployment override approved for user: {requesting_user}"
                        )

                # Record decision
                await self._record_decision(decisions, allowed)

                return allowed, decisions, blocker

            except (asyncio.TimeoutError, OSError) as e:
                self.logger.error(f"Error checking deployment gates: {e}")
                return False, decisions, None

    async def _check_error_budget_gate(self) -> GateDecision:
        """Check error budget gate."""
        try:
            state = await self.error_budget_manager.get_current_state()

            if state is None:
                return GateDecision(
                    gate_type=GateType.ERROR_BUDGET,
                    status=GateStatus.WARN,
                    message="No error budget data available",
                    details={"budget_state": None},
                    timestamp=datetime.utcnow(),
                )

            remaining_pct = state.remaining_percentage

            if remaining_pct < self.config.budget_exhausted_threshold_pct:
                return GateDecision(
                    gate_type=GateType.ERROR_BUDGET,
                    status=GateStatus.FAIL,
                    message=(
                        f"Error budget exhausted ({remaining_pct:.1f}% remaining < "
                        f"{self.config.budget_exhausted_threshold_pct}% threshold)"
                    ),
                    details={
                        "budget_remaining_pct": float(remaining_pct),
                        "threshold_pct": float(self.config.budget_exhausted_threshold_pct),
                        "consumed_downtime_minutes": state.consumption.downtime_minutes,
                        "burn_rate": float(state.burn_rate) if state.burn_rate else None,
                    },
                    timestamp=datetime.utcnow(),
                    can_override=self.config.allow_override,
                )

            elif remaining_pct < self.config.budget_warning_threshold_pct:
                return GateDecision(
                    gate_type=GateType.ERROR_BUDGET,
                    status=GateStatus.WARN,
                    message=(
                        f"Error budget low ({remaining_pct:.1f}% remaining < "
                        f"{self.config.budget_warning_threshold_pct}% threshold)"
                    ),
                    details={
                        "budget_remaining_pct": float(remaining_pct),
                        "threshold_pct": float(self.config.budget_warning_threshold_pct),
                    },
                    timestamp=datetime.utcnow(),
                )

            else:
                return GateDecision(
                    gate_type=GateType.ERROR_BUDGET,
                    status=GateStatus.PASS,
                    message=f"Error budget healthy ({remaining_pct:.1f}% remaining)",
                    details={"budget_remaining_pct": float(remaining_pct)},
                    timestamp=datetime.utcnow(),
                )

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error checking budget gate: {e}")
            return GateDecision(
                gate_type=GateType.ERROR_BUDGET,
                status=GateStatus.WARN,
                message=f"Error checking budget: {str(e)}",
                details={},
                timestamp=datetime.utcnow(),
            )

    async def _check_slo_compliance_gate(self) -> GateDecision:
        """Check SLO compliance gate."""
        if not self.slo_tracker:
            return GateDecision(
                gate_type=GateType.SLO_COMPLIANCE,
                status=GateStatus.PASS,
                message="SLO tracker not configured",
                details={},
                timestamp=datetime.utcnow(),
            )

        try:
            # Get compliance report
            reports = await self.slo_tracker.generate_compliance_report()

            if not reports:
                return GateDecision(
                    gate_type=GateType.SLO_COMPLIANCE,
                    status=GateStatus.WARN,
                    message="No SLO data available",
                    details={},
                    timestamp=datetime.utcnow(),
                )

            # Check if any SLOs are below threshold
            failing_slos = []
            for report in reports:
                if report.actual_slo < self.config.slo_compliance_threshold:
                    failing_slos.append(
                        {
                            "slo_name": report.slo_name,
                            "actual": f"{report.actual_slo * 100:.2f}%",
                            "target": f"{report.target_slo * 100:.2f}%",
                        }
                    )

            if failing_slos:
                return GateDecision(
                    gate_type=GateType.SLO_COMPLIANCE,
                    status=GateStatus.FAIL,
                    message=f"SLO compliance below threshold for {len(failing_slos)} SLO(s)",
                    details={
                        "failing_slos": failing_slos,
                        "threshold": f"{self.config.slo_compliance_threshold * 100:.2f}%",
                    },
                    timestamp=datetime.utcnow(),
                    can_override=self.config.allow_override,
                )

            return GateDecision(
                gate_type=GateType.SLO_COMPLIANCE,
                status=GateStatus.PASS,
                message="All SLOs compliant",
                details={
                    "slos_checked": len(reports),
                    "compliance_threshold": f"{self.config.slo_compliance_threshold * 100:.2f}%",
                },
                timestamp=datetime.utcnow(),
            )

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error checking SLO gate: {e}")
            return GateDecision(
                gate_type=GateType.SLO_COMPLIANCE,
                status=GateStatus.WARN,
                message=f"Error checking SLOs: {str(e)}",
                details={},
                timestamp=datetime.utcnow(),
            )

    async def _check_active_violations_gate(self) -> GateDecision:
        """Check for active SLO violations."""
        if not self.slo_tracker:
            return GateDecision(
                gate_type=GateType.ACTIVE_VIOLATIONS,
                status=GateStatus.PASS,
                message="SLO tracker not configured",
                details={},
                timestamp=datetime.utcnow(),
            )

        try:
            violations = await self.slo_tracker.get_active_violations()

            if len(violations) > self.config.max_allowed_violations:
                return GateDecision(
                    gate_type=GateType.ACTIVE_VIOLATIONS,
                    status=GateStatus.FAIL,
                    message=f"Active SLO violations detected ({len(violations)} violations)",
                    details={
                        "violations": [
                            {
                                "slo_name": v.slo_name,
                                "severity": v.severity,
                                "duration_minutes": v.duration_minutes(),
                            }
                            for v in violations
                        ],
                        "max_allowed": self.config.max_allowed_violations,
                    },
                    timestamp=datetime.utcnow(),
                    can_override=self.config.allow_override,
                )

            return GateDecision(
                gate_type=GateType.ACTIVE_VIOLATIONS,
                status=GateStatus.PASS,
                message="No active SLO violations",
                details={"active_violations": len(violations)},
                timestamp=datetime.utcnow(),
            )

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error checking violations gate: {e}")
            return GateDecision(
                gate_type=GateType.ACTIVE_VIOLATIONS,
                status=GateStatus.WARN,
                message=f"Error checking violations: {str(e)}",
                details={},
                timestamp=datetime.utcnow(),
            )

    async def _check_burn_rate_gate(self) -> GateDecision:
        """Check burn rate gate."""
        try:
            state = await self.error_budget_manager.get_current_state()

            if state is None or state.burn_rate is None:
                return GateDecision(
                    gate_type=GateType.BURN_RATE,
                    status=GateStatus.PASS,
                    message="No burn rate data available",
                    details={},
                    timestamp=datetime.utcnow(),
                )

            burn_rate = state.burn_rate

            if burn_rate > self.config.max_burn_rate:
                return GateDecision(
                    gate_type=GateType.BURN_RATE,
                    status=GateStatus.WARN,
                    message=f"High burn rate detected ({burn_rate:.2f} min/hr)",
                    details={
                        "burn_rate": float(burn_rate),
                        "threshold": float(self.config.max_burn_rate),
                        "rate_multiple": float(burn_rate / self.config.max_burn_rate),
                    },
                    timestamp=datetime.utcnow(),
                )

            return GateDecision(
                gate_type=GateType.BURN_RATE,
                status=GateStatus.PASS,
                message=f"Burn rate normal ({burn_rate:.2f} min/hr)",
                details={"burn_rate": float(burn_rate)},
                timestamp=datetime.utcnow(),
            )

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error checking burn rate gate: {e}")
            return GateDecision(
                gate_type=GateType.BURN_RATE,
                status=GateStatus.WARN,
                message=f"Error checking burn rate: {str(e)}",
                details={},
                timestamp=datetime.utcnow(),
            )

    async def _create_blocker(self, decisions: List[GateDecision]) -> DeploymentBlocker:
        """Create deployment blocker from failed decisions."""
        failed_decisions = [d for d in decisions if d.status == GateStatus.FAIL]

        if not failed_decisions:
            return None

        # Get primary blocking gate
        primary_decision = failed_decisions[0]

        # Extract details
        blocker = DeploymentBlocker(
            block_reason=primary_decision.message,
            blocking_gate=primary_decision.gate_type,
            blocked_at=datetime.utcnow(),
        )

        # Add budget remaining if available
        if primary_decision.gate_type == GateType.ERROR_BUDGET:
            blocker.budget_remaining_pct = Decimal(
                str(primary_decision.details.get("budget_remaining_pct", 0))
            )

        # Add active violations if available
        if primary_decision.gate_type == GateType.ACTIVE_VIOLATIONS:
            violations = primary_decision.details.get("violations", [])
            blocker.active_violations = [v.get("slo_name") for v in violations]

        self._current_blocker = blocker
        return blocker

    async def _check_override(
        self,
        requesting_user: Optional[str],
        reason: Optional[str],
    ) -> bool:
        """Check if override is allowed and approved."""
        if not self.config.allow_override:
            return False

        if not requesting_user:
            return False

        # Check if user is approved
        if self.config.override_require_approval and requesting_user not in self.config.override_approvers:
            self.logger.warning(f"Override requested by non-approved user: {requesting_user}")
            return False

        # Check for duplicate override
        override_key = f"{requesting_user}_{datetime.utcnow().date()}"
        if override_key in self._active_overrides:
            # Already overridden today
            return True

        # Require reason
        if not reason:
            self.logger.warning("Override requested without reason")
            return False

        # Record override
        self._active_overrides[override_key] = datetime.utcnow()
        self.logger.info(f"Deployment override approved: user={requesting_user}, reason={reason}")

        return True

    async def _record_decision(
        self,
        decisions: List[GateDecision],
        allowed: bool,
    ) -> None:
        """Record gate decision in history."""
        for decision in decisions:
            self._decision_history.append(decision)

        # Trim history
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]

    async def get_current_blocker(self) -> Optional[DeploymentBlocker]:
        """Get current deployment blocker."""
        return self._current_blocker

    async def get_decision_history(
        self,
        limit: int = 100,
    ) -> List[GateDecision]:
        """Get gate decision history."""
        return self._decision_history[-limit:]

    async def get_gate_summary(self) -> Dict[str, Any]:
        """Get gate summary."""
        blocker = await self.get_current_blocker()

        return {
            "service": self.service_name,
            "current_blocker": blocker.to_dict() if blocker else None,
            "override_enabled": self.config.allow_override,
            "override_approvers": (
                self.config.override_approvers if self.config.allow_override else []
            ),
            "recent_decisions": [d.to_dict() for d in self._decision_history[-10:]],
        }

    async def clear_blocker(self) -> bool:
        """
        Manually clear current blocker.

        Returns:
            True if cleared
        """
        if self._current_blocker:
            self._current_blocker = None
            self.logger.info("Deployment blocker cleared")
            return True
        return False
