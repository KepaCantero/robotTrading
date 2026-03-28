"""
Error Budget Integration - Connects Error Budget System to Existing Infrastructure

Integrates with:
- Health check endpoints (app/api/health.py)
- Deployment endpoints (app/api/deployment.py)
- Circuit breaker system (app/services/circuit_breaker_manager_v2.py)
- Alerting system (app/services/alerting_system/alerting_orchestrator.py)
- Monitoring system (app/services/monitoring/metrics_exporter.py)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from .budget_alerts import AlertRecipients, AlertSeverity, BudgetAlertConfig, BudgetAlertManager
from .development_gates import DevelopmentGate, DevelopmentGateConfig
from .error_budget_manager import BudgetPeriod, ErrorBudgetConfig, get_error_budget_manager
from .slo_tracker import SLOTracker

logger = logging.getLogger(__name__)


class ErrorBudgetIntegration:
    """
    Main integration point for error budget system.

    Coordinates all error budget components and integrates with
    existing infrastructure.
    """

    def __init__(
        self,
        service_name: str = "trading_system",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize error budget integration.

        Args:
            service_name: Name of the service
            config: Configuration dictionary
        """
        self.service_name = service_name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Initialize components
        self.budget_manager = get_error_budget_manager(
            service_name,
            self._create_budget_config(),
        )

        self.slo_tracker = SLOTracker(
            service_name=service_name,
            db_path=self.config.get("slo_db_path", "data/slo_metrics.db"),
        )

        self.alert_manager = BudgetAlertManager(
            service_name=service_name,
            config=self._create_alert_config(),
        )

        self.development_gate = DevelopmentGate(
            service_name=service_name,
            error_budget_manager=self.budget_manager,
            slo_tracker=self.slo_tracker,
            config=self._create_gate_config(),
        )

        # Integration callbacks
        self._setup_callbacks()

        self.logger.info(f"ErrorBudgetIntegration initialized for {service_name}")

    def _create_budget_config(self) -> ErrorBudgetConfig:
        """Create error budget configuration."""
        return ErrorBudgetConfig(
            target_slo=Decimal(self.config.get("target_slo", "0.995")),
            period=BudgetPeriod(self.config.get("period", "monthly")),
            warning_threshold_pct=Decimal(self.config.get("warning_threshold_pct", "50")),
            critical_threshold_pct=Decimal(self.config.get("critical_threshold_pct", "25")),
            exhausted_threshold_pct=Decimal(self.config.get("exhausted_threshold_pct", "10")),
            high_burn_rate_threshold=Decimal(self.config.get("high_burn_rate_threshold", "2.0")),
            db_path=self.config.get("budget_db_path", "data/error_budgets.db"),
        )

    def _create_alert_config(self) -> BudgetAlertConfig:
        """Create alert configuration."""
        recipients = AlertRecipients(
            emails=self.config.get("alert_emails", []),
            slack_channels=self.config.get("alert_slack_channels", []),
            pagerduty_services=self.config.get("alert_pagerduty_services", []),
            webhook_urls=self.config.get("alert_webhook_urls", []),
        )

        return BudgetAlertConfig(
            recipients=recipients,
            warning_threshold_pct=Decimal(self.config.get("warning_threshold_pct", "50")),
            critical_threshold_pct=Decimal(self.config.get("critical_threshold_pct", "25")),
            exhausted_threshold_pct=Decimal(self.config.get("exhausted_threshold_pct", "10")),
            burn_rate_threshold=Decimal(self.config.get("burn_rate_threshold", "2.0")),
            alert_cooldown_minutes=self.config.get("alert_cooldown_minutes", 15),
        )

    def _create_gate_config(self) -> DevelopmentGateConfig:
        """Create development gate configuration."""
        return DevelopmentGateConfig(
            budget_exhausted_threshold_pct=Decimal(
                self.config.get("exhausted_threshold_pct", "10")
            ),
            budget_warning_threshold_pct=Decimal(
                self.config.get("budget_warning_threshold_pct", "25")
            ),
            max_allowed_violations=self.config.get("max_allowed_violations", 0),
            slo_compliance_threshold=Decimal(self.config.get("slo_compliance_threshold", "0.95")),
            max_burn_rate=Decimal(self.config.get("max_burn_rate", "2.0")),
            allow_override=self.config.get("allow_override", True),
            override_require_approval=self.config.get("override_require_approval", True),
            override_approvers=self.config.get("override_approvers", []),
        )

    def _setup_callbacks(self) -> None:
        """Setup integration callbacks."""

        # Budget exhausted callback
        async def on_budget_exhausted(state):
            await self.alert_manager.check_and_alert(state)

        # Burn rate high callback
        async def on_burn_rate_high(state):
            await self.alert_manager.check_and_alert(state)

        # Set callbacks
        self.budget_manager.config.on_budget_exhausted = on_budget_exhausted
        self.budget_manager.config.on_burn_rate_high = on_burn_rate_high

        # SLO violation callback
        def on_slo_violation(violation):
            self.logger.error(f"SLO violation detected: {violation.slo_name}")

        def on_slo_resolved(violation):
            self.logger.info(f"SLO violation resolved: {violation.slo_name}")

        self.slo_tracker.set_violation_callback(on_slo_violation)
        self.slo_tracker.set_resolution_callback(on_slo_resolved)

    async def initialize(self) -> None:
        """Initialize all components."""
        try:
            await self.budget_manager.initialize()
            await self.slo_tracker.initialize()
            await self.alert_manager.initialize()

            self.logger.info("ErrorBudgetIntegration fully initialized")

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error initializing integration: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown all components."""
        await self.alert_manager.shutdown()
        self.logger.info("ErrorBudgetIntegration shutdown")

    async def record_downtime(
        self,
        downtime_minutes: int,
        error_type: str = "unknown",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record downtime and update all components.

        Args:
            downtime_minutes: Minutes of downtime
            error_type: Type of error
            description: Description
            metadata: Additional metadata

        Returns:
            Updated budget state
        """
        # Update error budget
        state = await self.budget_manager.record_downtime(
            downtime_minutes=downtime_minutes,
            error_type=error_type,
            description=description,
            metadata=metadata,
        )

        # Trigger alerts
        alerts = await self.alert_manager.check_and_alert(state)

        return {
            "budget_state": state.to_dict(),
            "alerts_triggered": len(alerts),
        }

    async def check_deployment_allowed(
        self,
        requesting_user: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if deployment is allowed.

        Args:
            requesting_user: User requesting deployment
            reason: Reason for deployment

        Returns:
            Deployment decision
        """
        allowed, decisions, blocker = await self.development_gate.check_deployment_allowed(
            requesting_user=requesting_user,
            reason=reason,
        )

        return {
            "allowed": allowed,
            "decisions": [d.to_dict() for d in decisions],
            "blocker": blocker.to_dict() if blocker else None,
        }

    async def get_budget_summary(self) -> Dict[str, Any]:
        """Get comprehensive budget summary."""
        budget_summary = await self.budget_manager.get_budget_summary()
        slo_summary = await self.slo_tracker.get_summary()
        alert_summary = await self.alert_manager.get_alert_summary()
        gate_summary = await self.development_gate.get_gate_summary()

        return {
            "budget": budget_summary,
            "slo": slo_summary,
            "alerts": alert_summary,
            "gates": gate_summary,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for error budget system."""
        try:
            state = await self.budget_manager.get_current_state()
            violations = await self.slo_tracker.get_active_violations()
            active_alerts = await self.alert_manager.get_active_alerts()
            blocker = await self.development_gate.get_current_blocker()

            # Determine health status
            if blocker:
                status = "unhealthy"
            elif violations:
                status = "degraded"
            else:
                status = "healthy"

            return {
                "status": status,
                "service": self.service_name,
                "budget_remaining": f"{state.remaining_percentage:.1f}%" if state else "unknown",
                "active_violations": len(violations),
                "active_alerts": len(active_alerts),
                "deployment_blocked": blocker is not None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error in health check: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# Singleton instance
_integration: Optional[ErrorBudgetIntegration] = None


def get_error_budget_integration(
    service_name: str = "trading_system",
    config: Optional[Dict[str, Any]] = None,
) -> ErrorBudgetIntegration:
    """
    Get or create error budget integration singleton.

    Args:
        service_name: Name of the service
        config: Optional configuration

    Returns:
        ErrorBudgetIntegration instance
    """
    global _integration
    if _integration is None:
        _integration = ErrorBudgetIntegration(service_name, config)
        logger.info(f"Created ErrorBudgetIntegration for {service_name}")
    return _integration


# API Router
def create_error_budget_router() -> APIRouter:
    """Create FastAPI router for error budget endpoints."""
    router = APIRouter(prefix="/sre/error-budgets", tags=["error-budgets"])

    @router.get("/summary")
    async def get_budget_summary():
        """Get comprehensive error budget summary."""
        try:
            integration = get_error_budget_integration()
            return await integration.get_budget_summary()
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def get_budget_health():
        """Get error budget system health."""
        try:
            integration = get_error_budget_integration()
            return await integration.health_check()
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/downtime")
    async def record_downtime(
        downtime_minutes: int,
        error_type: str = "unknown",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record downtime incident."""
        try:
            integration = get_error_budget_integration()
            return await integration.record_downtime(
                downtime_minutes=downtime_minutes,
                error_type=error_type,
                description=description,
                metadata=metadata,
            )
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/deployment/check")
    async def check_deployment(
        requesting_user: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Check if deployment is allowed."""
        try:
            integration = get_error_budget_integration()
            return await integration.check_deployment_allowed(
                requesting_user=requesting_user,
                reason=reason,
            )
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/slo/report")
    async def get_slo_report(
        slo_name: Optional[str] = None,
        hours: int = 24,
    ):
        """Get SLO compliance report."""
        try:
            integration = get_error_budget_integration()
            from datetime import timedelta

            period_end = datetime.utcnow()
            period_start = period_end - timedelta(hours=hours)

            reports = await integration.slo_tracker.generate_compliance_report(
                slo_name=slo_name,
                period_start=period_start,
                period_end=period_end,
            )

            return {
                "reports": [r.to_dict() for r in reports],
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                },
            }
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/alerts")
    async def get_alerts(
        limit: int = 100,
        severity: Optional[str] = None,
    ):
        """Get alert history."""
        try:
            integration = get_error_budget_integration()
            severity_enum = AlertSeverity(severity) if severity else None
            alerts = await integration.alert_manager.get_alert_history(
                limit=limit,
                severity=severity_enum,
            )
            return {
                "alerts": [a.to_dict() for a in alerts],
                "total": len(alerts),
            }
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(alert_id: str):
        """Acknowledge an alert."""
        try:
            integration = get_error_budget_integration()
            success = await integration.alert_manager.acknowledge_alert(alert_id)
            return {"acknowledged": success}
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/alerts/{alert_id}/resolve")
    async def resolve_alert(alert_id: str):
        """Resolve an alert."""
        try:
            integration = get_error_budget_integration()
            success = await integration.alert_manager.resolve_alert(alert_id)
            return {"resolved": success}
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/gates/clear-blocker")
    async def clear_deployment_blocker():
        """Clear current deployment blocker."""
        try:
            integration = get_error_budget_integration()
            success = await integration.development_gate.clear_blocker()
            return {"cleared": success}
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/incidents")
    async def get_incident_history(limit: int = 100):
        """Get downtime incident history."""
        try:
            integration = get_error_budget_integration()
            incidents = await integration.budget_manager.get_incident_history(limit=limit)
            return {
                "incidents": incidents,
                "total": len(incidents),
            }
        except (asyncio.TimeoutError, OSError) as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
