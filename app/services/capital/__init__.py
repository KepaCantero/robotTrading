"""
Capital Phase Management Services (R25, R26, R27)

This module provides dynamic risk management based on capital phases.
"""

from app.services.capital.capital_phase_manager import CapitalPhaseEvent, CapitalPhaseManager
from app.services.capital.phase_config import (
    PHASE_CONFIGS,
    PHASE_THRESHOLDS,
    CapitalPhase,
    PhaseRiskParameters,
)

__all__ = [
    "PHASE_CONFIGS",
    "PHASE_THRESHOLDS",
    # Configuration
    "CapitalPhase",
    # Events
    "CapitalPhaseEvent",
    # Main manager
    "CapitalPhaseManager",
    "PhaseRiskParameters",
]
