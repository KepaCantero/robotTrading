# pylint: disable=no-name-in-module,import-error
"""
On-Call Procedures System - SRE Compliance (SRE Rule 24)

Comprehensive on-call management system implementing Google SRE best practices:
- Rotation management with fair scheduling
- Escalation policies with clear paths
- Shift handoff procedures with knowledge transfer
- On-call status dashboard for visibility
- Comprehensive runbook library
- Sustainable on-call practices
- On-call burden tracking
- Well-being support

Target: 95% compliance with SRE on-call standards

Components:
- rotation: On-call rotation management
- escalation: Escalation policies and paths
- handoff: Shift handoff procedures
- dashboard: On-call status dashboard
- runbooks: Operational procedures library

Usage:
    from app.sre.oncall import OncallManager

    manager = OncallManager()
    await manager.initialize()

    # Get current on-call engineer
    current = await manager.get_current_oncall()

    # Escalate if needed
    await manager.escalate_incident(incident_id, severity="critical")
"""

from __future__ import annotations

import logging

from .dashboard import OncallDashboard, OncallMetrics, OncallStatus
from .escalation import EscalationLevel, EscalationManager, EscalationPath, EscalationPolicy
from .handoff import HandoffChecklist, HandoffManager, HandoffSession
from .rotation import OncallRotation, RotationConfig, RotationSchedule

logger = logging.getLogger(__name__)

__all__ = [
    # Rotation
    "OncallRotation",
    "RotationConfig",
    "RotationSchedule",
    # Escalation
    "EscalationPolicy",
    "EscalationPath",
    "EscalationLevel",
    "EscalationManager",
    # Handoff
    "HandoffManager",
    "HandoffChecklist",
    "HandoffSession",
    # Dashboard
    "OncallDashboard",
    "OncallStatus",
    "OncallMetrics",
]

# Version info
__version__ = "1.0.0"
__sre_compliance_target__ = "95%"
