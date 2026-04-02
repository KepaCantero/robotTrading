"""
Acceptance Criteria Models.

Data classes for acceptance criteria validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class VerdictStatus(str, Enum):
    """Strategy verdict status."""

    APPROVED = "APPROVED"
    REVISION = "REVISION"
    REJECTED = "REJECTED"


@dataclass
class CriterionResult:
    """Result of a single criterion check."""

    name: str
    passed: bool
    value: float
    threshold: float
    description: str


@dataclass
class AcceptanceReport:
    """Complete acceptance criteria report."""

    strategy_name: str
    timestamp: datetime
    verdict: VerdictStatus
    overall_score: float  # 0-100

    # Criterion results
    basic_criteria: list[CriterionResult] = field(default_factory=list)
    advanced_criteria: list[CriterionResult] = field(default_factory=list)
    rejection_criteria: list[CriterionResult] = field(default_factory=list)

    # Benchmark comparison
    beats_benchmark: bool = False
    excess_return: float = 0.0

    # Warnings and recommendations
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Detailed metrics
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    profit_factor: float | None = None
    commission_impact: float | None = None
    monte_carlo_p5: float | None = None
