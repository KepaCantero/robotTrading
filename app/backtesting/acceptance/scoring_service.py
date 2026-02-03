"""
Scoring Service for Backtesting Acceptance Criteria.

Calculates overall score from validation criteria.
Follows Single Responsibility Principle (SOL-001).
"""

from dataclasses import dataclass
from typing import List

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class ScoringService:
    """
    Calculates overall score from criteria results.

    Each passed criterion contributes 20 points (5 criteria = 100 max).
    """

    POINTS_PER_CRITERION: float = 20.0

    def calculate_score(self, criteria: List[CriterionResult]) -> float:
        """
        Calculate overall score (0-100) based on criteria results.

        Args:
            criteria: List of CriterionResult

        Returns:
            Overall score from 0.0 to 100.0
        """
        if not criteria:
            return 0.0

        score = 0.0

        for criterion in criteria:
            if criterion.passed:
                score += self.POINTS_PER_CRITERION

        return min(100.0, score)
