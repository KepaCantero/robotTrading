"""
T10.1: DeployDecisionOrchestrator - Master deployment decision orchestration

Synthesizes outputs from all services:
1. BacktestOrchestrator (feasibility ratio)
2. ValidationEngine (validation results)
3. StrategyRecommender (recommendation score)
4. PortfolioConstructor (portfolio metrics)

Makes final APPROVED/CONDITIONAL/REJECTED decision.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from app.services.capacity_fade_validation import (
    CapacityFadeRequest,
    CapacityFadeValidator,
    FeasibilityDecision,
)

from .models import DeploymentDecision, DeploymentInput, DeploymentRationale

logger = logging.getLogger(__name__)


class DeployDecisionOrchestrator:
    """
    Master orchestrator for deployment decisions.

    Decision Logic:
    1. Check feasibility ratio (hard gate)
    2. Check validation results (hard gate)
    3. Assess recommendation score
    4. Evaluate risk metrics
    5. Synthesize into final decision
    """

    # Thresholds for different decision criteria
    FEASIBILITY_THRESHOLDS = {
        "approved": Decimal("1.0"),  # >= 1.0: Can meet target
        "conditional": Decimal("0.7"),  # 0.7-1.0: Marginal viability
        "rejected": Decimal("0"),  # < 0.7: Not viable
    }

    RECOMMENDATION_THRESHOLDS = {
        "strong_buy": Decimal("80"),
        "buy": Decimal("65"),
        "hold": Decimal("50"),
        "review": Decimal("35"),
        "not_recommended": Decimal("0"),
    }

    CONFIDENCE_THRESHOLDS = {
        "high": Decimal("75"),
        "medium": Decimal("50"),
        "low": Decimal("0"),
    }

    def __init__(self):
        """Initialize orchestrator."""
        self.decision_history: List[DeploymentDecision] = []
        self.capacity_fade_validator = CapacityFadeValidator()  # T4.1 injection
        logger.info("✅ DeployDecisionOrchestrator initialized with T4.1 CapacityFadeValidator")

    async def make_decision(
        self,
        deployment_input: DeploymentInput,
    ) -> DeploymentDecision:
        """
        Make final deployment decision.

        Decision Flow:
        1. HARD GATES: Feasibility & Validation
        2. SOFT GATES: Recommendation & Risk
        3. SYNTHESIS: Combine scores into final decision

        Args:
            deployment_input: Complete deployment input

        Returns:
            DeploymentDecision with status and rationale
        """
        start_time = datetime.utcnow()

        try:
            # Step 1: Assess feasibility
            feasibility_score = await self._assess_feasibility(deployment_input.feasibility_ratio)

            # Step 2: Assess validation
            validation_score = await self._assess_validation(
                deployment_input.validation_passed,
                deployment_input.validation_failures,
            )

            # Step 3: Assess recommendation
            recommendation_score = deployment_input.recommendation_score

            # Step 4: Assess risk
            risk_score = await self._assess_risk(
                deployment_input.max_drawdown_pct,
                deployment_input.max_acceptable_drawdown_pct,
                deployment_input.sharpe_ratio,
                deployment_input.win_rate_pct,
            )

            # Step 5: Assess capacity fade (T4.1 Integration - Active Validation)
            (
                capacity_fade_score,
                capacity_fade_feasible,
                capacity_fade_alpha,
            ) = await self._assess_capacity_fade(deployment_input)

            # Step 6: Calculate overall score (weighted average)
            overall_score = await self._calculate_overall_score(
                feasibility_score,
                validation_score,
                recommendation_score,
                risk_score,
                capacity_fade_score,
            )

            # Step 7: Determine status
            status, confidence_level = await self._determine_status(
                feasibility_score,
                validation_score,
                overall_score,
                deployment_input.recommendation_status,
                deployment_input.validation_passed,
                deployment_input.feasibility_ratio,
                capacity_fade_feasible,  # Use result from T4.1 validator
            )

            # Step 8: Generate rationale
            rationale = await self._generate_rationale(
                deployment_input,
                feasibility_score,
                validation_score,
                recommendation_score,
                risk_score,
                capacity_fade_score,
                overall_score,
                status,
            )

            # Step 8: Generate recommendation text
            recommendation_text = await self._generate_recommendation_text(
                status, overall_score, rationale
            )

            # Step 9: Determine next steps
            next_steps = await self._determine_next_steps(status, rationale, deployment_input)

            # Build result
            result = DeploymentDecision(
                success=True,
                decision_id=deployment_input.decision_id,
                profile_id=deployment_input.profile_id,
                strategy_name=deployment_input.strategy_name,
                status=status,
                confidence_level=confidence_level,
                feasibility_score=feasibility_score,
                validation_score=validation_score,
                recommendation_score=recommendation_score,
                risk_score=risk_score,
                capacity_fade_score=capacity_fade_score,
                overall_score=overall_score,
                rationale=rationale,
                key_metrics={
                    "feasibility_ratio": deployment_input.feasibility_ratio,
                    "annual_return_pct": deployment_input.annual_return_pct,
                    "max_drawdown_pct": deployment_input.max_drawdown_pct,
                    "sharpe_ratio": deployment_input.sharpe_ratio,
                    "win_rate_pct": deployment_input.win_rate_pct,
                },
                recommendation_text=recommendation_text,
                next_steps=next_steps,
            )

            self.decision_history.append(result)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ Deployment decision made for {deployment_input.profile_id}, "
                f"status={status}, score={overall_score:.0f}, elapsed={elapsed_ms:.0f}ms"
            )
            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Error making deployment decision: {e}")
            return DeploymentDecision(
                success=False,
                decision_id=deployment_input.decision_id,
                profile_id=deployment_input.profile_id,
                strategy_name=deployment_input.strategy_name,
                status="REJECTED",
                confidence_level="low",
                feasibility_score=Decimal("0"),
                validation_score=Decimal("0"),
                recommendation_score=Decimal("0"),
                risk_score=Decimal("0"),
                capacity_fade_score=Decimal("0"),
                overall_score=Decimal("0"),
                rationale=DeploymentRationale(
                    feasibility_assessment="Error occurred",
                    validation_assessment="Error occurred",
                    recommendation_assessment="Error occurred",
                    risk_assessment="Error occurred",
                    diversification_assessment="Error occurred",
                    overall_assessment=f"Error: {str(e)}",
                    critical_factors=[str(e)],
                    improvement_areas=[],
                ),
                key_metrics={},
                recommendation_text="Decision failed due to error",
                error_message=str(e),
            )

    async def _assess_feasibility(self, feasibility_ratio: Decimal) -> Decimal:
        """Assess feasibility score based on ratio."""
        if feasibility_ratio >= Decimal("1.2"):
            return Decimal("100")  # Excellent
        elif feasibility_ratio >= Decimal("1.0"):
            return Decimal("85")  # Good
        elif feasibility_ratio >= Decimal("0.8"):
            return Decimal("60")  # Marginal
        elif feasibility_ratio >= Decimal("0.7"):
            return Decimal("40")  # Poor
        else:
            return Decimal("0")  # Unviable

    async def _assess_validation(
        self,
        validation_passed: bool,
        validation_failures: List[str],
    ) -> Decimal:
        """Assess validation score."""
        if validation_passed:
            return Decimal("100")  # All gates passed
        elif not validation_failures:
            return Decimal("80")  # Passed with warnings only
        elif len(validation_failures) <= 2:
            return Decimal("50")  # Some failures but not critical
        else:
            return Decimal("0")  # Multiple critical failures

    async def _assess_risk(
        self,
        current_drawdown: Decimal,
        max_acceptable_drawdown: Decimal,
        sharpe_ratio: Decimal,
        win_rate: Decimal,
    ) -> Decimal:
        """Assess risk score (higher is better for risk mitigation)."""
        scores = []

        # Drawdown assessment (inverse - lower drawdown = higher score)
        if current_drawdown <= max_acceptable_drawdown * Decimal("0.5"):
            scores.append(Decimal("100"))
        elif current_drawdown <= max_acceptable_drawdown * Decimal("0.75"):
            scores.append(Decimal("80"))
        elif current_drawdown <= max_acceptable_drawdown:
            scores.append(Decimal("60"))
        else:
            scores.append(Decimal("30"))

        # Sharpe ratio assessment
        if sharpe_ratio >= Decimal("1.5"):
            scores.append(Decimal("100"))
        elif sharpe_ratio >= Decimal("1.0"):
            scores.append(Decimal("80"))
        elif sharpe_ratio >= Decimal("0.5"):
            scores.append(Decimal("60"))
        else:
            scores.append(Decimal("30"))

        # Win rate assessment
        if win_rate >= Decimal("55"):
            scores.append(Decimal("100"))
        elif win_rate >= Decimal("50"):
            scores.append(Decimal("80"))
        elif win_rate >= Decimal("45"):
            scores.append(Decimal("60"))
        else:
            scores.append(Decimal("30"))

        return sum(scores) / len(scores)

    async def _assess_capacity_fade(self, deployment_input: DeploymentInput) -> tuple:
        """
        Assess capacity fade score using T4.1 CapacityFadeValidator.

        T4.1 Capacity Fade Validation Integration (CRITICAL - 40% weight)
        Evaluates whether strategy alpha can be sustained as capital scales to €250k+.

        Returns:
            (capacity_fade_score, capacity_fade_feasible, estimated_alpha)
        """
        try:
            # If capital data not provided, return None for capacity_fade_score
            # This triggers weight redistribution in _calculate_overall_score()
            if deployment_input.current_capital is None or deployment_input.target_capital is None:
                logger.warning(
                    "⚠️ Capacity fade validation skipped: missing capital data, redistributing weights"
                )
                return None, None, None

            # Build request for T4.1 validator
            fade_request = CapacityFadeRequest(
                profile_id=deployment_input.profile_id,
                input_id=deployment_input.input_id,
                base_alpha_pct=deployment_input.annual_return_pct,  # Use backtest alpha
                backtest_capital_usd=deployment_input.current_capital,
                backtest_duration_years=Decimal("3"),  # Default assumption
                current_capital_usd=deployment_input.current_capital,
                target_capital_usd=deployment_input.target_capital,
                target_monthly_return_usd=Decimal("800"),  # Default: €800/month
                avg_position_size_usd=deployment_input.target_capital / Decimal("10"),  # 10% avg
                avg_daily_volume_multiplier=Decimal("1.0"),
                fade_model="sqrt",  # Conservative model
                confidence_level="conservative",
            )

            # Call T4.1 validator
            response = await self.capacity_fade_validator.validate_capacity_feasibility(
                fade_request
            )

            if not response.success:
                logger.error(f"❌ T4.1 validation failed: {response.error_message}")
                return Decimal("20"), False, Decimal("0")

            # Extract results from T4.1
            feasibility_decision = response.feasibility_gate.decision
            estimated_alpha = response.analysis.estimated_alpha_at_target

            # Map T4.1 decision to feasibility boolean
            is_feasible = feasibility_decision != FeasibilityDecision.REJECTED

            # Score based on alpha at scale
            if estimated_alpha >= Decimal("5"):
                score = Decimal("100")  # Strong alpha at scale
            elif estimated_alpha >= Decimal("3"):
                score = Decimal("85")  # Good alpha at scale (meets €800/month requirement)
            elif estimated_alpha >= Decimal("1"):
                score = Decimal("70")  # Marginal alpha at scale
            else:
                score = Decimal("40")  # Weak alpha at scale

            # Apply penalty if feasibility is conditional or rejected
            if feasibility_decision == FeasibilityDecision.CONDITIONAL:
                score = max(Decimal("40"), score - Decimal("20"))  # -20 for conditional
            elif feasibility_decision == FeasibilityDecision.REJECTED:
                score = Decimal("20")  # Hard penalty for rejected

            logger.info(
                f"✅ T4.1 Capacity Fade Validation: {feasibility_decision.value}, "
                f"alpha={estimated_alpha:.2f}%, score={score:.0f}"
            )

            return score, is_feasible, estimated_alpha

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ T4.1 Capacity Fade validation error: {str(e)}")
            return Decimal("20"), False, Decimal("0")

    async def _calculate_overall_score(
        self,
        feasibility: Decimal,
        validation: Decimal,
        recommendation: Decimal,
        risk: Decimal,
        capacity_fade: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate weighted overall score.

        T4.1 Integration: Capacity fade is CRITICAL gate (40% weight).

        Weights when capacity fade data is available (T4.1 Critical Integration):
        - Capacity Fade: 40% (CRITICAL - Prevents unsustainable scaling)
        - Feasibility: 25% (Return feasibility)
        - Validation: 15% (Technical validation)
        - Risk: 12% (Risk metrics)
        - Recommendation: 8% (Strategy quality)

        Weights when capacity fade data is NOT available (backward compatibility):
        - Feasibility: 42% (25 + 40 redistributed)
        - Validation: 25% (15 + 40 redistributed)
        - Risk: 20% (12 + 40 redistributed)
        - Recommendation: 13% (8 + 40 redistributed)

        Rationale:
        - Capacity fade is hardest gate: strategies must sustain alpha at €250k+
        - Without capacity fade validation, strategy will fail at scale
        - Other metrics secondary to capacity viability
        """
        if capacity_fade is not None:
            # Full T4.1 integration with capacity fade
            weighted_score = (
                capacity_fade * Decimal("0.40")  # CRITICAL: 40%
                + feasibility * Decimal("0.25")
                + validation * Decimal("0.15")
                + risk * Decimal("0.12")
                + recommendation * Decimal("0.08")
            )
        else:
            # Backward compatibility: redistribute capacity fade weight
            weighted_score = (
                feasibility * Decimal("0.42")
                + validation * Decimal("0.25")
                + risk * Decimal("0.20")
                + recommendation * Decimal("0.13")
            )

        return weighted_score

    async def _determine_status(
        self,
        feasibility_score: Decimal,
        validation_score: Decimal,
        overall_score: Decimal,
        recommendation_status: str,
        validation_passed: bool,
        feasibility_ratio: Decimal,
        capacity_fade_feasible: Optional[bool] = None,
    ) -> tuple:
        """
        Determine deployment status and confidence level.

        T4.1 PHASE 6: Adds capacity fade as a hard gate.
        """

        # HARD GATES - Automatic rejection
        # 1. Validation gate: validation_passed=False is a hard failure
        if not validation_passed:
            return "REJECTED", "low"

        # 2. Feasibility gate: feasibility_ratio < 0.7 is unviable
        if feasibility_ratio < Decimal("0.7"):
            return "REJECTED", "low"

        # 3. Capacity fade gate: capacity_fade_feasible=False is a hard failure (T4.1 PHASE 6)
        if capacity_fade_feasible is False:
            return "REJECTED", "low"

        # Check recommendation status
        if recommendation_status in ["NOT_RECOMMENDED", "REVIEW"]:
            if overall_score < Decimal("60"):
                return "REJECTED", "low"

        # Determine status based on overall score
        if overall_score >= Decimal("80"):
            status = "APPROVED"
            confidence = "high"
        elif overall_score >= Decimal("60"):
            status = "APPROVED"
            confidence = "medium"
        elif overall_score >= Decimal("45"):
            status = "CONDITIONAL"
            confidence = "medium"
        elif overall_score >= Decimal("30"):
            status = "CONDITIONAL"
            confidence = "low"
        else:
            status = "REJECTED"
            confidence = "low"

        # Upgrade to CONDITIONAL if feasibility is marginal (0.7-1.0)
        if Decimal("0.7") <= feasibility_ratio < Decimal("1.0"):
            status = "CONDITIONAL"
            # Keep confidence low if overall_score is also low
            if overall_score >= Decimal("60"):
                confidence = "medium"
            else:
                confidence = "low"

        return status, confidence

    async def _generate_rationale(
        self,
        input_data: DeploymentInput,
        feasibility_score: Decimal,
        validation_score: Decimal,
        recommendation_score: Decimal,
        risk_score: Decimal,
        capacity_fade_score: Decimal,
        overall_score: Decimal,
        status: str,
    ) -> DeploymentRationale:
        """Generate detailed decision rationale."""

        # Feasibility assessment
        if input_data.feasibility_ratio >= Decimal("1.0"):
            feasibility_text = (
                f"✅ Feasibility ratio {input_data.feasibility_ratio:.2f}x exceeds requirement. "
                f"Strategy can meet target annual return of {input_data.target_annual_return_pct:.1f}%."
            )
        elif input_data.feasibility_ratio >= Decimal("0.7"):
            feasibility_text = (
                f"⚠️ Feasibility ratio {input_data.feasibility_ratio:.2f}x is marginal. "
                f"Strategy may struggle to meet {input_data.target_annual_return_pct:.1f}% target."
            )
        else:
            feasibility_text = (
                f"❌ Feasibility ratio {input_data.feasibility_ratio:.2f}x is unacceptable. "
                f"Strategy cannot viably meet {input_data.target_annual_return_pct:.1f}% target."
            )

        # Validation assessment
        if input_data.validation_passed:
            validation_text = "✅ All validation gates passed successfully."
        elif not input_data.validation_failures:
            validation_text = (
                f"⚠️ Validation passed with {len(input_data.validation_warnings)} warning(s)."
            )
        else:
            validation_text = (
                f"❌ Validation failed with {len(input_data.validation_failures)} critical issue(s). "
                f"Issues: {', '.join(input_data.validation_failures[:2])}"
            )

        # Recommendation assessment
        if recommendation_score >= Decimal("80"):
            recommendation_text = f"✅ Strong recommendation score ({recommendation_score:.0f}/100). Strategy shows high potential."
        elif recommendation_score >= Decimal("65"):
            recommendation_text = (
                f"👍 Good recommendation score ({recommendation_score:.0f}/100). Strategy is viable."
            )
        elif recommendation_score >= Decimal("50"):
            recommendation_text = f"➖ Neutral recommendation score ({recommendation_score:.0f}/100). Marginal viability."
        else:
            recommendation_text = (
                f"❌ Weak recommendation score ({recommendation_score:.0f}/100). Caution advised."
            )

        # Risk assessment
        if input_data.max_drawdown_pct <= input_data.max_acceptable_drawdown_pct * Decimal("0.7"):
            risk_text = f"✅ Risk well-controlled. Drawdown {input_data.max_drawdown_pct:.1f}% is below acceptable {input_data.max_acceptable_drawdown_pct:.1f}%."
        elif input_data.max_drawdown_pct <= input_data.max_acceptable_drawdown_pct:
            risk_text = f"⚠️ Risk acceptable. Drawdown {input_data.max_drawdown_pct:.1f}% is near acceptable limit."
        else:
            risk_text = f"❌ Risk unacceptable. Drawdown {input_data.max_drawdown_pct:.1f}% exceeds limit {input_data.max_acceptable_drawdown_pct:.1f}%."

        # Diversification assessment
        if input_data.diversification_ratio >= Decimal("2.0"):
            div_text = f"✅ Well-diversified portfolio (ratio: {input_data.diversification_ratio:.2f}). Low concentration risk."
        elif input_data.diversification_ratio >= Decimal("1.5"):
            div_text = f"👍 Adequately diversified (ratio: {input_data.diversification_ratio:.2f}). Acceptable concentration."
        else:
            div_text = f"⚠️ Limited diversification (ratio: {input_data.diversification_ratio:.2f}). Consider broader allocation."

        # Capacity fade assessment (T4.1 PHASE 6)
        capacity_fade_text = ""
        if input_data.capacity_fade_feasible is False:
            capacity_fade_text = (
                "❌ Capital fade analysis: Strategy alpha fades below minimum threshold at target capital. "
                "Cannot scale to €250k while maintaining required returns."
            )
        elif input_data.capacity_fade_feasible is True:
            if (
                input_data.estimated_alpha_at_scale
                and input_data.estimated_alpha_at_scale >= Decimal("3")
            ):
                capacity_fade_text = (
                    f"✅ Capacity fade analysis: Strategy maintains strong alpha ({input_data.estimated_alpha_at_scale:.1f}%) "
                    "when scaled to target capital. Good capacity for growth."
                )
            elif (
                input_data.estimated_alpha_at_scale
                and input_data.estimated_alpha_at_scale >= Decimal("1")
            ):
                capacity_fade_text = (
                    f"⚠️ Capacity fade analysis: Strategy alpha moderates to {input_data.estimated_alpha_at_scale:.1f}% "
                    "at target capital. Feasible but with less margin."
                )
            else:
                capacity_fade_text = (
                    "⚠️ Capacity fade analysis: Strategy reaches target capital but with marginal alpha. "
                    "May need optimization for scale."
                )
        else:
            capacity_fade_text = (
                "➖ Capacity fade analysis: Not evaluated. Assuming capacity-neutral scaling. "
                "Recommend capacity fade validation before large-scale deployment."
            )

        # Critical factors
        critical_factors = []
        if input_data.feasibility_ratio < Decimal("0.7"):
            critical_factors.append("Feasibility ratio too low")
        if not input_data.validation_passed:
            critical_factors.append(f"Validation failures: {len(input_data.validation_failures)}")
        if recommendation_score < Decimal("50"):
            critical_factors.append("Low recommendation score")
        if input_data.max_drawdown_pct > input_data.max_acceptable_drawdown_pct:
            critical_factors.append("Drawdown exceeds acceptable limit")
        if input_data.capacity_fade_feasible is False:
            critical_factors.append("Strategy alpha fades below minimum at target capital scale")

        # Improvement areas
        improvement_areas = []
        if input_data.feasibility_ratio < Decimal("1.0"):
            improvement_areas.append("Enhance return optimization to improve feasibility ratio")
        if recommendation_score < Decimal("70"):
            improvement_areas.append("Review strategy parameters to improve recommendation score")
        if input_data.max_drawdown_pct > input_data.max_acceptable_drawdown_pct * Decimal("0.9"):
            improvement_areas.append("Add protective strategies to reduce drawdown risk")
        if input_data.top_allocation_pct > Decimal("50"):
            improvement_areas.append("Increase diversification to reduce concentration risk")
        if input_data.capacity_fade_feasible is False:
            improvement_areas.append("Optimize strategy to sustain alpha at higher capital levels")
        elif capacity_fade_score is not None and capacity_fade_score < Decimal("75"):
            improvement_areas.append(
                "Consider liquidity-aware position sizing to maintain alpha at scale"
            )

        # Overall assessment
        if status == "APPROVED":
            overall_assessment = (
                f"✅ APPROVED - Strategy {input_data.strategy_name} meets deployment criteria "
                f"with overall score of {overall_score:.0f}/100."
            )
        elif status == "CONDITIONAL":
            overall_assessment = (
                f"⚠️ CONDITIONAL - Strategy {input_data.strategy_name} is viable with improvements. "
                f"Overall score: {overall_score:.0f}/100."
            )
        else:
            overall_assessment = (
                f"❌ REJECTED - Strategy {input_data.strategy_name} does not meet minimum deployment criteria. "
                f"Overall score: {overall_score:.0f}/100."
            )

        return DeploymentRationale(
            feasibility_assessment=feasibility_text,
            validation_assessment=validation_text,
            recommendation_assessment=recommendation_text,
            risk_assessment=risk_text,
            diversification_assessment=div_text,
            capacity_fade_assessment=capacity_fade_text if capacity_fade_text else None,
            overall_assessment=overall_assessment,
            critical_factors=critical_factors,
            improvement_areas=improvement_areas,
        )

    async def _generate_recommendation_text(
        self,
        status: str,
        score: Decimal,
        rationale: DeploymentRationale,
    ) -> str:
        """Generate human-readable recommendation text."""
        if status == "APPROVED":
            text = (
                "✅ Recommended for deployment. This strategy demonstrates strong fundamentals "
                f"with an overall confidence score of {score:.0f}/100. "
                f"{rationale.overall_assessment} "
                "Consider deploying with normal monitoring."
            )
        elif status == "CONDITIONAL":
            text = (
                f"⚠️ Conditionally approved subject to improvements. Overall score: {score:.0f}/100. "
                f"{rationale.overall_assessment} "
                f"Recommended improvements: {', '.join(rationale.improvement_areas[:2])}. "
                "Deploy with enhanced monitoring and consider phased rollout."
            )
        else:
            text = (
                f"❌ Not recommended for deployment at this time. Score: {score:.0f}/100. "
                f"{rationale.overall_assessment} "
                f"Address critical issues before reconsidering: {', '.join(rationale.critical_factors[:2])}."
            )

        return text

    async def _determine_next_steps(
        self,
        status: str,
        rationale: DeploymentRationale,
        input_data: DeploymentInput,
    ) -> List[str]:
        """Determine recommended next steps."""
        next_steps = []

        if status == "APPROVED":
            next_steps.append("Deploy strategy to live trading")
            next_steps.append("Configure initial position sizing based on capital tier")
            next_steps.append("Set up performance monitoring dashboard")
            next_steps.append("Establish review checkpoints at 1, 3, and 6 months")

        elif status == "CONDITIONAL":
            next_steps.extend(rationale.improvement_areas[:3])
            next_steps.append("Conduct sensitivity analysis on key parameters")
            next_steps.append("Prepare contingency strategies if underperformance occurs")
            next_steps.append("Deploy to paper trading first for validation")

        else:  # REJECTED
            next_steps.append("Address critical factors listed above")
            next_steps.append("Re-optimize strategy parameters")
            next_steps.append("Resubmit for decision once improvements are validated")
            if input_data.feasibility_ratio < Decimal("0.5"):
                next_steps.append("Consider alternative strategy types or modules")

        return next_steps

    async def get_decision_history(
        self,
        limit: Optional[int] = None,
    ) -> List[DeploymentDecision]:
        """Get decision history."""
        results = self.decision_history
        if limit:
            results = results[-limit:]
        return results

    def get_orchestrator_status(self) -> Dict:
        """Get orchestrator operational status."""
        approved = sum(1 for d in self.decision_history if d.status == "APPROVED")
        conditional = sum(1 for d in self.decision_history if d.status == "CONDITIONAL")
        rejected = sum(1 for d in self.decision_history if d.status == "REJECTED")
        successful = sum(1 for d in self.decision_history if d.success)
        total = len(self.decision_history)

        avg_score = Decimal("0")
        if total > 0:
            avg_score = sum(d.overall_score for d in self.decision_history) / total

        return {
            "total_decisions": total,
            "approved": approved,
            "conditional": conditional,
            "rejected": rejected,
            "successful_decisions": successful,
            "success_rate": successful / max(1, total),
            "average_score": float(avg_score),
            "history_size": total,
        }


# Singleton
_orchestrator: Optional[DeployDecisionOrchestrator] = None


def get_deploy_orchestrator() -> DeployDecisionOrchestrator:
    """Get or create singleton DeployDecisionOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DeployDecisionOrchestrator()
        logger.info("✅ DeployDecisionOrchestrator singleton initialized")

    return _orchestrator
