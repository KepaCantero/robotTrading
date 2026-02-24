"""
PHASE 3: Risk Scaling Monitor - Dashboard & API Interface

Provides real-time monitoring, alerting, and reporting for risk scaling system.
Interfaces between core risk scaling logic and user-facing dashboards/APIs.

Capabilities:
- Real-time risk scaling status
- Historical tracking and trends
- Alert generation and subscription
- Performance reporting
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import numpy as np

from app.services.risk_scaling.models import (
    AlertSubscription,
    RiskAlert,
    RiskAlertType,
    RiskLevel,
    RiskScalingReport,
    RiskScalingSnapshot,
    RiskScalingState,
    RiskScalingStatus,
)

logger = logging.getLogger(__name__)


class RiskScalingMonitor:
    """
    Real-time monitoring and alerting for risk scaling system.

    Provides:
    - Current scaling factors and status
    - Historical tracking (last 30 days)
    - Alert management and subscriptions
    - Performance statistics
    - Dashboard data

    Usage:
        monitor = RiskScalingMonitor()
        status = await monitor.get_scaling_status(portfolio_id)
        await monitor.subscribe_to_alerts(portfolio_id, [RiskAlertType.HALT_TRADING])
    """

    def __init__(self, history_retention_days: int = 30):
        """
        Initialize risk scaling monitor.

        Args:
            history_retention_days: How long to keep historical data (default 30)
        """
        self.history_retention_days = history_retention_days
        self.portfolio_states: Dict[str, RiskScalingState] = {}
        self.portfolio_history: Dict[str, List[RiskScalingSnapshot]] = {}
        self.alert_subscriptions: Dict[str, AlertSubscription] = {}
        self.alert_log: List[RiskAlert] = []

    async def get_scaling_status(
        self,
        portfolio_id: str,
    ) -> RiskScalingStatus:
        """
        Get current risk scaling status for dashboard display.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Current scaling status
        """
        if portfolio_id not in self.portfolio_states:
            raise ValueError(f"No scaling state for portfolio {portfolio_id}")

        state = self.portfolio_states[portfolio_id]

        # Determine risk level from combined scale
        combined = state.scaling_factors.combined_scale
        if state.scaling_factors.drawdown_scale == Decimal("0"):
            risk_level = RiskLevel.HALT
        elif combined < Decimal("0.5"):
            risk_level = RiskLevel.CRITICAL
        elif combined < Decimal("0.8"):
            risk_level = RiskLevel.WARNING
        elif combined < Decimal("1.0"):
            risk_level = RiskLevel.CAUTION
        else:
            risk_level = RiskLevel.SAFE

        # Get active alerts
        active_alerts = [a for a in state.active_alerts if not a.resolved]

        # Next recalc time (assume every minute)
        next_recalc = datetime.now() + timedelta(minutes=1)

        return RiskScalingStatus(
            portfolio_id=portfolio_id,
            scaling_factors=state.scaling_factors,
            risk_level=risk_level,
            active_alerts_count=len(active_alerts),
            active_alerts=active_alerts,
            last_update=state.updated_at,
            next_recalc_at=next_recalc,
        )

    async def get_scaling_history(
        self,
        portfolio_id: str,
        days: int = 30,
    ) -> List[RiskScalingSnapshot]:
        """
        Get historical scaling snapshots for trend analysis.

        Args:
            portfolio_id: Portfolio identifier
            days: Days of history to retrieve (default 30)

        Returns:
            List of scaling snapshots in chronological order
        """
        if portfolio_id not in self.portfolio_history:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        return [s for s in self.portfolio_history[portfolio_id] if s.timestamp >= cutoff]

    async def subscribe_to_alerts(
        self,
        portfolio_id: str,
        alert_types: List[RiskAlertType],
        min_severity: RiskLevel = RiskLevel.WARNING,
    ) -> AlertSubscription:
        """
        Subscribe to specific risk alerts.

        Args:
            portfolio_id: Portfolio to monitor
            alert_types: Types of alerts to receive
            min_severity: Minimum severity level for alerts

        Returns:
            AlertSubscription details
        """
        subscription = AlertSubscription(
            portfolio_id=portfolio_id,
            alert_types=alert_types,
            min_severity=min_severity,
        )

        self.alert_subscriptions[subscription.subscription_id] = subscription
        logger.info(
            f"Alert subscription created for {portfolio_id}: "
            f"types={[a.value for a in alert_types]}, "
            f"min_severity={min_severity.value}"
        )

        return subscription

    async def record_alert(
        self,
        alert: RiskAlert,
    ) -> None:
        """
        Record an alert and notify subscribers.

        Args:
            alert: Alert to record and distribute
        """
        # Store in log
        self.alert_log.append(alert)

        # Notify subscribers
        for sub in self.alert_subscriptions.values():
            if (
                sub.portfolio_id == alert.portfolio_id
                and alert.alert_type in sub.alert_types
                and alert.severity.value >= sub.min_severity.value
                and sub.enabled
            ):
                logger.info(
                    f"Alert dispatched to subscription {sub.subscription_id}: "
                    f"{alert.alert_type.value}"
                )
                # In real implementation, would send via webhook, email, etc.

    async def get_scaling_trends(
        self,
        portfolio_id: str,
        days: int = 7,
    ) -> Dict:
        """
        Analyze scaling trends over time period.

        Args:
            portfolio_id: Portfolio identifier
            days: Days to analyze (default 7)

        Returns:
            Dictionary with trend analysis
        """
        history = await self.get_scaling_history(portfolio_id, days=days)

        if not history:
            return {
                "portfolio_id": portfolio_id,
                "period_days": days,
                "data_points": 0,
                "trend": "insufficient_data",
            }

        # Analyze trends
        scales = [float(s.scaling_factors.combined_scale) for s in history]
        volatilities = [float(s.scaling_factors.volatility_scale) for s in history]
        sharpes = [float(s.scaling_factors.sharpe_scale) for s in history]
        losses = [float(s.scaling_factors.loss_scale) for s in history]
        drawdowns = [float(s.scaling_factors.drawdown_scale) for s in history]

        return {
            "portfolio_id": portfolio_id,
            "period_days": days,
            "data_points": len(history),
            "combined_scale": {
                "current": scales[-1],
                "avg": np.mean(scales),
                "min": min(scales),
                "max": max(scales),
                "trend": "increasing" if scales[-1] > scales[0] else "decreasing",
            },
            "volatility_scale": {
                "current": volatilities[-1],
                "avg": np.mean(volatilities),
                "min": min(volatilities),
                "max": max(volatilities),
            },
            "sharpe_scale": {
                "current": sharpes[-1],
                "avg": np.mean(sharpes),
                "min": min(sharpes),
                "max": max(sharpes),
            },
            "loss_scale": {
                "current": losses[-1],
                "avg": np.mean(losses),
                "min": min(losses),
                "max": max(losses),
            },
            "drawdown_scale": {
                "current": drawdowns[-1],
                "avg": np.mean(drawdowns),
                "min": min(drawdowns),
                "max": max(drawdowns),
            },
        }

    async def get_alert_history(
        self,
        portfolio_id: Optional[str] = None,
        alert_type: Optional[RiskAlertType] = None,
        severity: Optional[RiskLevel] = None,
        hours_back: int = 24,
    ) -> List[RiskAlert]:
        """
        Get alert history with optional filtering.

        Args:
            portfolio_id: Filter by portfolio (optional)
            alert_type: Filter by alert type (optional)
            severity: Filter by minimum severity (optional)
            hours_back: How far back to look (default 24 hours)

        Returns:
            List of matching alerts
        """
        cutoff = datetime.now() - timedelta(hours=hours_back)
        filtered = [a for a in self.alert_log if a.timestamp >= cutoff]

        if portfolio_id:
            filtered = [a for a in filtered if a.portfolio_id == portfolio_id]

        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]

        if severity:
            filtered = [a for a in filtered if a.severity.value >= severity.value]

        return filtered

    async def resolve_alert(
        self,
        alert_id: str,
        resolution_note: Optional[str] = None,
    ) -> Optional[RiskAlert]:
        """
        Mark an alert as resolved.

        Args:
            alert_id: Alert ID to resolve
            resolution_note: Optional resolution note

        Returns:
            Resolved alert or None if not found
        """
        for alert in self.alert_log:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert {alert_id} resolved")
                return alert

        return None

    def store_state(
        self,
        portfolio_id: str,
        state: RiskScalingState,
    ) -> None:
        """
        Store risk scaling state snapshot.

        Args:
            portfolio_id: Portfolio identifier
            state: State to store
        """
        self.portfolio_states[portfolio_id] = state

        if portfolio_id not in self.portfolio_history:
            self.portfolio_history[portfolio_id] = []

        # Add snapshot to history
        if state.scaling_history:
            for snapshot in state.scaling_history:
                self.portfolio_history[portfolio_id].append(snapshot)

        # Cleanup old snapshots
        cutoff = datetime.now() - timedelta(days=self.history_retention_days)
        self.portfolio_history[portfolio_id] = [
            s for s in self.portfolio_history[portfolio_id] if s.timestamp >= cutoff
        ]

    async def generate_daily_report(
        self,
        portfolio_id: str,
    ) -> RiskScalingReport:
        """
        Generate daily risk scaling report.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Daily report
        """
        if portfolio_id not in self.portfolio_states:
            raise ValueError(f"No state for portfolio {portfolio_id}")

        state = self.portfolio_states[portfolio_id]

        # Get alerts from last 24 hours
        recent_alerts = await self.get_alert_history(portfolio_id=portfolio_id, hours_back=24)

        return RiskScalingReport(
            portfolio_id=portfolio_id,
            period="last_24h",
            current_combined_scale=state.scaling_factors.combined_scale,
            volatility_scale=state.scaling_factors.volatility_scale,
            sharpe_scale=state.scaling_factors.sharpe_scale,
            loss_scale=state.scaling_factors.loss_scale,
            drawdown_scale=state.scaling_factors.drawdown_scale,
            current_atr=state.current_atr,
            avg_atr=state.current_atr,
            sharpe_ratio=state.sharpe_ratio,
            consecutive_losses=state.consecutive_losses,
            current_drawdown=state.current_drawdown,
            max_drawdown=state.max_drawdown,
            active_alerts=[f"{a.alert_type.value}: {a.message}" for a in recent_alerts],
            summary=self._summarize_daily_status(state),
        )

    def _summarize_daily_status(self, state: RiskScalingState) -> str:
        """Generate daily status summary."""
        combined = state.scaling_factors.combined_scale
        num_alerts = len([a for a in state.active_alerts if not a.resolved])

        parts = [f"Scale factor: {combined:.2f}x"]

        if num_alerts > 0:
            parts.append(f"{num_alerts} active alerts")

        if state.scaling_factors.drawdown_scale == Decimal("0"):
            parts.append("TRADING HALTED")
        elif combined < Decimal("0.5"):
            parts.append("Critical risk reduction")
        elif combined < Decimal("0.8"):
            parts.append("Significant risk reduction")

        return " | ".join(parts)

    async def get_portfolio_dashboard_data(
        self,
        portfolio_id: str,
    ) -> Dict:
        """
        Get all dashboard data for a portfolio in one call.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Dictionary with all dashboard metrics
        """
        status = await self.get_scaling_status(portfolio_id)
        trends = await self.get_scaling_trends(portfolio_id, days=7)
        recent_alerts = await self.get_alert_history(portfolio_id=portfolio_id, hours_back=24)

        return {
            "portfolio_id": portfolio_id,
            "status": status.model_dump(),
            "trends": trends,
            "recent_alerts": [a.model_dump() for a in recent_alerts],
            "last_updated": datetime.now().isoformat(),
        }
