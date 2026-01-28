"""
Error Budgets System - SRE Rule 20 Compliance

Implements Google SRE error budget methodology:
- Define error budgets based on SLOs (e.g., 99.5% uptime = 4h/month downtime)
- Track budget consumption in real-time
- Auto-halt development when budget exhausted
- Alert on budget breaches
- Track SLO/SLI compliance

Components:
- ErrorBudgetManager: Main error budget tracking and calculation
- SLOTracker: SLO/SLI monitoring and compliance tracking
- BudgetAlerts: Alerting on budget breaches and warnings
- DevelopmentGates: Auto-halt deployment when budget exhausted
"""

from .budget_alerts import (
    AlertChannel,
    AlertSeverity,
    BudgetAlertConfig,
    BudgetAlertManager,
)
from .development_gates import (
    DeploymentBlocker,
    DevelopmentGate,
    GateDecision,
    GateStatus,
)
from .error_budget_manager import (
    BudgetPeriod,
    ErrorBudgetConfig,
    ErrorBudgetManager,
    ErrorBudgetState,
    get_error_budget_manager,
)
from .integration import (
    ErrorBudgetIntegration,
    create_error_budget_router,
    get_error_budget_integration,
)
from .slo_tracker import (
    SLIMetric,
    SLOComplianceReport,
    SLOConfig,
    SLOTracker,
    SLOViolation,
)

__all__ = [
    # Error Budget Manager
    "ErrorBudgetManager",
    "get_error_budget_manager",
    "ErrorBudgetConfig",
    "ErrorBudgetState",
    "BudgetPeriod",
    # SLO Tracker
    "SLOTracker",
    "SLOConfig",
    "SLIMetric",
    "SLOComplianceReport",
    "SLOViolation",
    # Budget Alerts
    "BudgetAlertManager",
    "BudgetAlertConfig",
    "AlertSeverity",
    "AlertChannel",
    # Development Gates
    "DevelopmentGate",
    "GateStatus",
    "GateDecision",
    "DeploymentBlocker",
    # Integration
    "ErrorBudgetIntegration",
    "get_error_budget_integration",
    "create_error_budget_router",
]
