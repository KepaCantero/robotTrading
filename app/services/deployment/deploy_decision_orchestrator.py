"""
T10.1: DeployDecisionOrchestrator - Master deployment decision orchestrator

Synthesizes all components (validation, backtest, recommendation, portfolio)
into a final APPROVED|CONDITIONAL|REJECTED deployment decision.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeploymentDecision:
    """Final deployment decision with rationale."""

    status: str  # "APPROVED", "CONDITIONAL", "REJECTED"
    decision_id: str
    confidence_level: str  # "HIGH", "MODERATE", "LOW"
    feasibility_ratio: float
    validation_passed: bool
    recommendation_score: float
    portfolio_sharpe: float
    reasons: List[str]  # Why this decision was made
    risks: List[str]  # Identified risks
    recommendations: List[str]  # Recommendations for improvement
    next_steps: List[str]  # Actions to take


class DeployDecisionOrchestrator:
    """
    T10.1: Master orchestrator for deployment decisions.

    Synthesizes:
    - ValidationReport (passed/failed gates)
    - BacktestResult (feasibility_ratio, returns, Sharpe)
    - StrategyRecommendation (score, confidence)
    - PortfolioAllocation (diversification, volatility)

    Into final APPROVED|CONDITIONAL|REJECTED decision.
    """

    # Decision thresholds
    APPROVAL_THRESHOLDS = {
        "feasibility_ratio_approved": 1.0,  # Can fully meet target
        "feasibility_ratio_conditional": 0.7,  # Needs optimization
        "feasibility_ratio_rejected": 0.5,  # Not viable
        "recommendation_score_approved": 75,  # Strong recommendation
        "recommendation_score_conditional": 60,  # Moderate recommendation
        "recommendation_score_rejected": 40,  # Weak recommendation
        "sharpe_ratio_approved": 1.0,  # Good risk-adjusted return
        "sharpe_ratio_conditional": 0.5,  # Moderate risk-adjusted return
    }

    def __init__(self):
        """Initialize DeployDecisionOrchestrator."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ DeployDecisionOrchestrator initialized")

    async def orchestrate(
        self,
        validation_report: Dict,
        backtest_result: Dict,
        recommendation: Dict,
        allocation: Dict,
        investment_profile: Optional[Dict] = None,
    ) -> DeploymentDecision:
        """
        Master orchestration method synthesizing all components.

        Args:
            validation_report: Validation gate results
            backtest_result: Backtest metrics (return, Sharpe, feasibility_ratio)
            recommendation: Strategy recommendation (score, confidence)
            allocation: Portfolio allocation with metrics
            investment_profile: Optional profile for context

        Returns:
            DeploymentDecision with final status
        """
        try:
            # Extract key metrics
            validation_passed = validation_report.get("overall_status") == "APPROVED"
            feasibility_ratio = self._safe_float(backtest_result.get("feasibility_ratio", 0.0))
            recommendation_score = self._safe_float(recommendation.get("score", 0.0))
            sharpe_ratio = self._safe_float(backtest_result.get("sharpe_ratio", 0.0))
            portfolio_sharpe = self._safe_float(allocation.get("sharpe_ratio", 0.0))

            # Determine status based on decision matrix
            status, confidence = await self._determine_status(
                validation_passed, feasibility_ratio, recommendation_score, sharpe_ratio
            )

            # Generate reasons, risks, and recommendations
            reasons = await self._generate_reasons(
                status, validation_passed, feasibility_ratio, recommendation_score, sharpe_ratio
            )
            risks = await self._identify_risks(feasibility_ratio, sharpe_ratio, allocation)
            recommendations = await self._generate_recommendations(
                status, feasibility_ratio, recommendation_score
            )
            next_steps = await self._determine_next_steps(status)

            decision_id = f"decision_{self._get_timestamp()}"

            result = DeploymentDecision(
                status=status,
                decision_id=decision_id,
                confidence_level=confidence,
                feasibility_ratio=feasibility_ratio,
                validation_passed=validation_passed,
                recommendation_score=recommendation_score,
                portfolio_sharpe=portfolio_sharpe,
                reasons=reasons,
                risks=risks,
                recommendations=recommendations,
                next_steps=next_steps,
            )

            self.logger.info(
                f"🎯 Deployment decision: {status} "
                f"(feasibility: {feasibility_ratio:.2f}, recommendation: {recommendation_score:.1f})"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Error in orchestration: {e}")
            raise

    async def _determine_status(
        self,
        validation_passed: bool,
        feasibility_ratio: float,
        recommendation_score: float,
        sharpe_ratio: float,
    ) -> tuple:
        """
        Determine deployment status using decision matrix.

        Decision Logic:
        1. If validation failed → REJECTED (hard gate)
        2. If feasibility_ratio >= 1.0 AND recommendation >= 75 → APPROVED
        3. If feasibility_ratio >= 0.7 AND recommendation >= 60 → CONDITIONAL
        4. Otherwise → REJECTED
        """
        # Hard gate: validation must pass
        if not validation_passed:
            return "REJECTED", "LOW"

        # Feasibility and recommendation matrix
        if (
            feasibility_ratio >= self.APPROVAL_THRESHOLDS["feasibility_ratio_approved"]
            and recommendation_score >= self.APPROVAL_THRESHOLDS["recommendation_score_approved"]
        ):
            confidence = "HIGH" if sharpe_ratio > 1.0 else "MODERATE"
            return "APPROVED", confidence

        elif (
            feasibility_ratio >= self.APPROVAL_THRESHOLDS["feasibility_ratio_conditional"]
            and recommendation_score >= self.APPROVAL_THRESHOLDS["recommendation_score_conditional"]
        ):
            return "CONDITIONAL", "MODERATE"

        else:
            return "REJECTED", "LOW"

    async def _generate_reasons(
        self,
        status: str,
        validation_passed: bool,
        feasibility_ratio: float,
        recommendation_score: float,
        sharpe_ratio: float,
    ) -> List[str]:
        """Generate human-readable reasons for decision."""
        reasons = []

        if status == "APPROVED":
            reasons.append(f"✅ All validation gates passed")
            reasons.append(f"✅ Feasibility ratio {feasibility_ratio:.2f} exceeds 1.0 threshold")
            reasons.append(f"✅ Recommendation score {recommendation_score:.1f} is strong")
            if sharpe_ratio > 1.0:
                reasons.append(f"✅ Excellent risk-adjusted returns (Sharpe: {sharpe_ratio:.2f})")

        elif status == "CONDITIONAL":
            reasons.append(f"⚠️  Validation passed but with conditions")
            reasons.append(f"⚠️  Feasibility ratio {feasibility_ratio:.2f} is moderate (0.7-1.0)")
            reasons.append(f"⚠️  Recommendation score {recommendation_score:.1f} is acceptable")
            reasons.append(f"⚠️  Strategy requires optimization before full deployment")

        else:  # REJECTED
            if not validation_passed:
                reasons.append(f"❌ Validation gates failed")
            if feasibility_ratio < 0.7:
                reasons.append(f"❌ Feasibility ratio {feasibility_ratio:.2f} too low")
            if recommendation_score < 60:
                reasons.append(f"❌ Recommendation score {recommendation_score:.1f} insufficient")

        return reasons

    async def _identify_risks(
        self,
        feasibility_ratio: float,
        sharpe_ratio: float,
        allocation: Dict,
    ) -> List[str]:
        """Identify key risks in the strategy."""
        risks = []

        if feasibility_ratio < 0.8:
            risks.append("Low feasibility: May struggle to meet return targets")

        if sharpe_ratio < 0.5:
            risks.append("Poor risk-adjusted returns: High volatility relative to returns")

        if sharpe_ratio < 0:
            risks.append("CRITICAL: Negative Sharpe ratio indicates losses expected")

        # Check allocation concentration
        # Handle nested allocation structure {"allocation": {...}, "sharpe_ratio": ...}
        allocation_weights = (
            allocation.get("allocation", allocation)
            if isinstance(allocation.get("allocation"), dict)
            else allocation
        )
        weight_values = [v for v in allocation_weights.values() if isinstance(v, (int, float))]
        max_weight = max(weight_values) if weight_values else 0.0
        if max_weight > 0.50:
            risks.append(f"High concentration: {max_weight*100:.0f}% in single position")

        return risks

    async def _generate_recommendations(
        self,
        status: str,
        feasibility_ratio: float,
        recommendation_score: float,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if feasibility_ratio < 1.0:
            recommendations.append(
                "Optimize strategy parameters to improve returns or reduce capital requirements"
            )

        if recommendation_score < 75:
            recommendations.append("Review strategy for potential improvements in Sharpe ratio")

        if status == "CONDITIONAL":
            recommendations.append("Run additional sensitivity analysis before deployment")
            recommendations.append("Consider smaller initial position size and scale gradually")

        if status == "APPROVED":
            recommendations.append("Deploy strategy and monitor performance against benchmarks")
            recommendations.append("Implement automatic rebalancing at quarterly intervals")

        return recommendations

    async def _determine_next_steps(self, status: str) -> List[str]:
        """Determine next actions based on status."""
        next_steps = []

        if status == "APPROVED":
            next_steps.append("1. Review risk management parameters")
            next_steps.append("2. Set up position monitoring")
            next_steps.append("3. Begin deployment with allocated capital")
            next_steps.append("4. Schedule weekly performance reviews")

        elif status == "CONDITIONAL":
            next_steps.append("1. Perform sensitivity analysis on key parameters")
            next_steps.append("2. Test strategy with smaller position sizes")
            next_steps.append("3. Wait for market conditions to improve")
            next_steps.append("4. Re-evaluate before larger deployment")

        else:  # REJECTED
            next_steps.append("1. Review strategy parameters")
            next_steps.append("2. Optimize for better risk-adjusted returns")
            next_steps.append("3. Rerun backtest with optimized parameters")
            next_steps.append("4. Reassess for deployment reconsideration")

        return next_steps

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")
