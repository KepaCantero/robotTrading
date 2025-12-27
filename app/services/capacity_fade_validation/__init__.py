"""
T4.1 Priority 5: Capacity Fade Validation

Validates that strategy alpha is sustainable as capital scales to target level (€250k).

Key Components:
- HistoricalCapacityAnalyzer: Analyzes backtest performance degradation with capital size
- LiquidityHeadroom: Calculates daily volume constraints
- AlphaDecayEstimator: Projects alpha at target capital using sqrt(capacity) model
- CapacityFadeValidator: Orchestrates validation and gates infeasible strategies

Models:
- CapacityFadeAnalysis: Analysis results with fade ratio and feasibility
- LiquidityReport: Position sizing constraints based on daily volume
- FeasibilityGate: Final approval decision (APPROVED/CONDITIONAL/REJECTED)
"""

from .capacity_fade_validator import CapacityFadeValidator
from .models import (
    CapacityFadeAnalysis,
    CapacityFadeRequest,
    CapacityFadeResponse,
    FeasibilityDecision,
    FeasibilityGate,
    LiquidityReport,
)

    "CapacityFadeAnalysis",
    "CapacityFadeRequest",
    "CapacityFadeResponse",
    "FeasibilityGate",
    "FeasibilityDecision",
    "LiquidityReport",
    "CapacityFadeValidator",
]
