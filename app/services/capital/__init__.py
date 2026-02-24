"""
Capital Phase Management Services (R25, R26, R27)

This module provides dynamic risk management based on capital phases.
"""

from app.services.capital.capital_phase_manager import (
    CapitalPhaseEvent,
    CapitalPhaseManager,
)
from app.services.capital.phase_config import (
    PHASE_CONFIGS,
    PHASE_THRESHOLDS,
    CapitalPhase,
    PhaseRiskParameters,
)

__all__ = [
    # Main manager
    "CapitalPhaseManager",
    # Configuration
    "CapitalPhase",
    "PhaseRiskParameters",
    "PHASE_CONFIGS",
    "PHASE_THRESHOLDS",
    # Events
    "CapitalPhaseEvent",
]
