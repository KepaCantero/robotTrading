"""
Verdict Determiner Service for Backtesting Acceptance Criteria.

Determines the final verdict based on validation results.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass
from typing import List, Tuple

from app.backtesting.acceptance.models import CriterionResult, VerdictStatus


@dataclass
class VerdictDeterminer:
    """
    Determines final verdict based on criteria and rejection results.

    Verdict logic:
    - Any rejection criterion failed → REJECTED
    - All criteria passed → APPROVED
    - Score >= 60 with no rejections → REVISION
    - Score < 60 → REJECTED
    """

    MIN_REVISION_SCORE: float = 60.0

    def determine_verdict(
        self,
        criteria: List[CriterionResult],
        rejection: List[CriterionResult],
        score: float,
    ) -> Tuple[VerdictStatus, List[str], List[str]]:
        """
        Determine verdict based on criteria and rejection factors.

        Args:
            criteria: List of basic criterion results
            rejection: List of rejection criterion results
            score: Overall score (0-100)

        Returns:
            Tuple of (verdict, warnings, recommendations)
        """
        warnings: List[str] = []
        recommendations: List[str] = []

        # Check rejection criteria first (highest priority)
        rejected = False
        for crit in rejection:
            if not crit.passed:
                rejected = True
                warnings.append(f"REJECTED: {crit.description}")

        if rejected:
            return VerdictStatus.REJECTED, warnings, recommendations

        # Check if all basic criteria passed
        all_passed = all(c.passed for c in criteria)

        if all_passed:
            verdict = VerdictStatus.APPROVED
            recommendations.append("Strategy meets all acceptance criteria")
        elif score >= self.MIN_REVISION_SCORE:
            verdict = VerdictStatus.REVISION
            warnings.append("Strategy partially meets criteria - review recommended")
            recommendations.extend([f"Improve {c.name}" for c in criteria if not c.passed])
        else:
            verdict = VerdictStatus.REJECTED
            warnings.append("Strategy fails too many criteria")
            recommendations.extend([f"Address {c.name}" for c in criteria if not c.passed])

        return verdict, warnings, recommendations
