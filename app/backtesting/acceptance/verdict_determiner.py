"""
Verdict Determiner Service for Backtesting Acceptance Criteria.

Determines the final verdict based on validation results.
Follows Single Responsibility Principle (SOL-001).

Verdict Logic:
    The verdict determination follows a priority-based approach:
    1. REJECTION: If any rejection criterion fails, verdict is REJECTED
    2. APPROVAL: If all basic criteria pass, verdict is APPROVED
    3. REVISION: If score >= 60 and no rejections, verdict is REVISION
    4. REJECTION: If score < 60, verdict is REJECTED

This ensures critical rejection criteria are always checked first,
providing fail-safe behavior for backtest validation.
"""

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult, VerdictStatus


@dataclass
class VerdictDeterminer:
    """
    Determines final verdict based on criteria and rejection results.

    This class implements a multi-stage verdict determination process
    that prioritizes rejection criteria over basic acceptance criteria.

    Attributes:
        MIN_REVISION_SCORE: Minimum score threshold for REVISION verdict (default: 60.0)

    Example:
        >>> determiner = VerdictDeterminer()
        >>> verdict, warnings, recs = determiner.determine_verdict(
        ...     criteria=[CriterionResult(...)],
        ...     rejection=[CriterionResult(...)],
        ...     score=75.0
        ... )
    """

    MIN_REVISION_SCORE: float = 60.0

    def _check_rejection_criteria(self, rejection: list[CriterionResult]) -> tuple[bool, list[str]]:
        """
        Check if any rejection criteria have failed.

        Rejection criteria are hard constraints that must all pass.
        Failure of any single rejection criterion results in immediate
        rejection of the strategy.

        Args:
            rejection: List of rejection criterion results to evaluate

        Returns:
            Tuple of (is_rejected, warning_messages) where:
            - is_rejected: True if any rejection criterion failed
            - warning_messages: List of warning messages for failed criteria
        """
        warnings: list[str] = []
        is_rejected = False

        for criterion in rejection:
            if not criterion.passed:
                is_rejected = True
                warnings.append(f"REJECTED: {criterion.description}")

        return is_rejected, warnings

    def _get_failed_criteria_names(self, criteria: list[CriterionResult]) -> list[str]:
        """
        Extract names of all failed criteria.

        Args:
            criteria: List of criterion results to filter

        Returns:
            List of names of criteria that did not pass
        """
        return [c.name for c in criteria if not c.passed]

    def _determine_non_rejected_verdict(
        self,
        criteria: list[CriterionResult],
        score: float,
    ) -> tuple[VerdictStatus, list[str], list[str]]:
        """
        Determine verdict when no rejection criteria have failed.

        Uses score and basic criteria pass rate to determine final verdict:
        - All passed: APPROVED
        - Score >= MIN_REVISION_SCORE: REVISION
        - Score < MIN_REVISION_SCORE: REJECTED

        Args:
            criteria: List of basic criterion results
            score: Overall score (0-100)

        Returns:
            Tuple of (verdict, warnings, recommendations)
        """
        warnings: list[str] = []
        recommendations: list[str] = []
        all_passed = all(c.passed for c in criteria)

        if all_passed:
            return self._create_approved_verdict(recommendations)

        failed_names = self._get_failed_criteria_names(criteria)

        if score >= self.MIN_REVISION_SCORE:
            return self._create_revision_verdict(warnings, recommendations, failed_names)

        return self._create_low_score_rejected_verdict(warnings, recommendations, failed_names)

    def _create_approved_verdict(
        self, recommendations: list[str]
    ) -> tuple[VerdictStatus, list[str], list[str]]:
        """
        Create an APPROVED verdict with appropriate recommendations.

        Args:
            recommendations: List to append recommendations to

        Returns:
            Tuple of (APPROVED, empty_warnings, recommendations)
        """
        recommendations.append("Strategy meets all acceptance criteria")
        return VerdictStatus.APPROVED, [], recommendations

    def _create_revision_verdict(
        self,
        warnings: list[str],
        recommendations: list[str],
        failed_names: list[str],
    ) -> tuple[VerdictStatus, list[str], list[str]]:
        """
        Create a REVISION verdict with improvement suggestions.

        Args:
            warnings: List to append warnings to
            recommendations: List to append recommendations to
            failed_names: Names of failed criteria to improve

        Returns:
            Tuple of (REVISION, warnings, recommendations)
        """
        warnings.append("Strategy partially meets criteria - review recommended")
        recommendations.extend([f"Improve {name}" for name in failed_names])
        return VerdictStatus.REVISION, warnings, recommendations

    def _create_low_score_rejected_verdict(
        self,
        warnings: list[str],
        recommendations: list[str],
        failed_names: list[str],
    ) -> tuple[VerdictStatus, list[str], list[str]]:
        """
        Create a REJECTED verdict for low-scoring strategies.

        Args:
            warnings: List to append warnings to
            recommendations: List to append recommendations to
            failed_names: Names of failed criteria to address

        Returns:
            Tuple of (REJECTED, warnings, recommendations)
        """
        warnings.append("Strategy fails too many criteria")
        recommendations.extend([f"Address {name}" for name in failed_names])
        return VerdictStatus.REJECTED, warnings, recommendations

    def determine_verdict(
        self,
        criteria: list[CriterionResult],
        rejection: list[CriterionResult],
        score: float,
    ) -> tuple[VerdictStatus, list[str], list[str]]:
        """
        Determine verdict based on criteria and rejection factors.

        This method orchestrates the verdict determination process by:
        1. First checking rejection criteria (highest priority)
        2. If not rejected, evaluating basic criteria and score

        Args:
            criteria: List of basic criterion results
            rejection: List of rejection criterion results
            score: Overall score (0-100)

        Returns:
            Tuple of (verdict, warnings, recommendations) where:
            - verdict: Final VerdictStatus (APPROVED, REVISION, or REJECTED)
            - warnings: List of warning messages
            - recommendations: List of actionable recommendations
        """
        # Check rejection criteria first (highest priority)
        is_rejected, warnings = self._check_rejection_criteria(rejection)
        if is_rejected:
            return VerdictStatus.REJECTED, warnings, []

        # Determine verdict based on criteria and score
        return self._determine_non_rejected_verdict(criteria, score)
