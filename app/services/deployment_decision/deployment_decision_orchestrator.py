"""
T20.1: Deployment Decision Orchestrator - Master orchestrator synthesizing all CAPA 2 outputs

Synthesizes validation, recommendation, portfolio allocation, and risk assessment
into final deployment decision (APPROVED, CONDITIONAL, REJECTED).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DeploymentAnalysis:
    """Analysis components contributing to deployment decision."""

    validation_passed: bool
    validation_failures: List[str]
    validation_warnings: List[str]

    feasibility_ratio: Decimal
    feasibility_assessment: str  # VIABLE, MARGINAL, NOT_VIABLE

    recommendation_confidence: str  # high, medium, low
    recommendation_score: Decimal  # 0-100

    portfolio_quality: Decimal  # 0-100 (diversification, concentration)
    portfolio_risk_assessment: str  # low, medium, high

    capital_tier: str
    objective: str
    risk_profile: str

    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeploymentDecision:
    """Final deployment decision with comprehensive analysis."""

    decision_status: str  # APPROVED, CONDITIONAL, REJECTED
    confidence_level: str  # high, medium, low

    primary_reason: str
    supporting_reasons: List[str]
    risk_warnings: List[str]

    # Detailed metrics
    analysis: DeploymentAnalysis

    # Recommendations if CONDITIONAL or REJECTED
    remediation_steps: List[str]
    alternative_strategies: List[str]

    # Decision timestamp and ID
    decision_timestamp: datetime = field(default_factory=datetime.utcnow)
    decision_id: str = field(default="")

    def __post_init__(self):
        """Generate decision ID if not provided."""
        if not self.decision_id:
            self.decision_id = (
                f"DEPLOY-{self.decision_timestamp.strftime('%Y%m%d%H%M%S')}-"
                f"{self.decision_status[0]}"
            )


class DeploymentDecisionOrchestrator:
    """
    Master orchestrator for deployment decisions.

    Synthesizes outputs from:
    - T15.1: Tax efficiency analysis
    - T16.1: Live trading readiness
    - T17.1: External integration status
    - T18.1: Portfolio allocation quality
    - T19.1: Strategy recommendation

    Returns comprehensive deployment decision.
    """

    def __init__(self):
        """Initialize deployment decision orchestrator."""
        self.decision_history: List[DeploymentDecision] = []
        self.decision_metrics: Dict[str, Dict] = {}
        logger.info("✅ DeploymentDecisionOrchestrator initialized")

    async def orchestrate(
        self,
        # Validation inputs
        validation_passed: bool,
        validation_failures: List[str],
        validation_warnings: List[str],
        # Backtest inputs
        feasibility_ratio: Decimal,
        backtest_return: Decimal,
        backtest_sharpe: Decimal,
        backtest_max_drawdown: Decimal,
        # Recommendation inputs
        recommendation_score: Decimal,
        recommendation_confidence: str,
        recommendation_alternatives: List[str],
        # Portfolio inputs
        portfolio_quality: Decimal,
        portfolio_diversification_score: Decimal,
        portfolio_concentration_risk: Decimal,
        portfolio_num_assets: int,
        # Risk assessment inputs
        portfolio_risk_level: str,
        estimated_max_loss: Decimal,
        # User profile inputs
        capital_tier: str,
        objective: str,
        risk_profile: str,
        target_monthly_return: Decimal,
        initial_capital: Decimal,
    ) -> DeploymentDecision:
        """
        Orchestrate deployment decision based on comprehensive analysis.

        Args:
            validation_passed: Whether all validation gates passed
            validation_failures: List of critical validation failures
            validation_warnings: List of validation warnings
            feasibility_ratio: Annual return / required return ratio
            backtest_return: Backtested annual return
            backtest_sharpe: Sharpe ratio from backtest
            backtest_max_drawdown: Maximum drawdown observed
            recommendation_score: Strategy recommendation score (0-100)
            recommendation_confidence: Confidence level (high/medium/low)
            recommendation_alternatives: Alternative strategy names
            portfolio_quality: Portfolio quality score (0-100)
            portfolio_diversification_score: Diversification metric (0-100)
            portfolio_concentration_risk: Concentration risk (0-100, higher is worse)
            portfolio_num_assets: Number of assets in portfolio
            portfolio_risk_level: Portfolio risk assessment
            estimated_max_loss: Estimated maximum loss in worst case
            capital_tier: Investment capital tier
            objective: Investment objective
            risk_profile: User risk tolerance
            target_monthly_return: Monthly return target in euros
            initial_capital: Initial capital amount

        Returns:
            DeploymentDecision with comprehensive analysis
        """

        # Step 1: Assess validation status (hard gate)
        validation_assessment = await self._assess_validation(
            validation_passed, validation_failures, validation_warnings
        )

        # Step 2: Assess feasibility ratio
        feasibility_assessment = await self._assess_feasibility(feasibility_ratio)

        # Step 3: Assess recommendation
        recommendation_assessment = await self._assess_recommendation(
            recommendation_score, recommendation_confidence
        )

        # Step 4: Assess portfolio quality
        portfolio_assessment = await self._assess_portfolio_quality(
            portfolio_quality,
            portfolio_diversification_score,
            portfolio_concentration_risk,
            portfolio_num_assets,
            portfolio_risk_level,
        )

        # Step 5: Perform comprehensive risk assessment
        risk_assessment = await self._assess_risk(
            backtest_max_drawdown,
            estimated_max_loss,
            portfolio_risk_level,
            risk_profile,
            initial_capital,
        )

        # Step 6: Determine primary decision status
        decision_status, decision_confidence = await self._determine_decision_status(
            validation_assessment,
            feasibility_assessment,
            recommendation_assessment,
            portfolio_assessment,
            risk_assessment,
            backtest_sharpe,
        )

        # Step 7: Generate reasoning
        primary_reason, supporting_reasons = await self._generate_reasoning(
            decision_status,
            validation_assessment,
            feasibility_assessment,
            recommendation_assessment,
            portfolio_assessment,
        )

        # Step 8: Generate remediation steps if not approved
        remediation_steps = await self._generate_remediation(
            decision_status, validation_failures, feasibility_assessment, recommendation_assessment
        )

        # Step 9: Create comprehensive analysis object
        analysis = DeploymentAnalysis(
            validation_passed=validation_assessment["passed"],
            validation_failures=validation_failures,
            validation_warnings=validation_warnings,
            feasibility_ratio=feasibility_ratio,
            feasibility_assessment=feasibility_assessment["assessment"],
            recommendation_confidence=recommendation_confidence,
            recommendation_score=recommendation_score,
            portfolio_quality=portfolio_quality,
            portfolio_risk_assessment=portfolio_risk_level,
            capital_tier=capital_tier,
            objective=objective,
            risk_profile=risk_profile,
        )

        # Step 10: Create final deployment decision
        decision = DeploymentDecision(
            decision_status=decision_status,
            confidence_level=decision_confidence,
            primary_reason=primary_reason,
            supporting_reasons=supporting_reasons,
            risk_warnings=risk_assessment["warnings"],
            analysis=analysis,
            remediation_steps=remediation_steps,
            alternative_strategies=recommendation_alternatives,
        )

        # Store in history and metrics
        self.decision_history.append(decision)
        await self._update_metrics(decision)

        logger.info(
            f"✅ Deployment decision: {decision_status} "
            f"(feasibility: {feasibility_ratio:.2f}, confidence: {decision_confidence})"
        )

        return decision

    async def _assess_validation(
        self, passed: bool, failures: List[str], warnings: List[str]
    ) -> Dict:
        """Assess validation status."""
        return {
            "passed": passed,
            "num_failures": len(failures),
            "num_warnings": len(warnings),
            "assessment": "PASSED" if passed else "FAILED",
        }

    async def _assess_feasibility(self, ratio: Decimal) -> Dict:
        """Assess feasibility ratio."""
        if ratio >= Decimal("1.0"):
            assessment = "VIABLE"
            level = "strong"
        elif ratio >= Decimal("0.7"):
            assessment = "MARGINAL"
            level = "moderate"
        else:
            assessment = "NOT_VIABLE"
            level = "weak"

        return {"ratio": ratio, "assessment": assessment, "level": level}

    async def _assess_recommendation(self, score: Decimal, confidence: str) -> Dict:
        """Assess recommendation quality."""
        score_level = (
            "strong"
            if score >= Decimal("75")
            else ("moderate" if score >= Decimal("60") else "weak")
        )

        confidence_weight = (
            Decimal("1.0")
            if confidence == "high"
            else (Decimal("0.7") if confidence == "medium" else Decimal("0.4"))
        )

        return {
            "score": score,
            "confidence": confidence,
            "score_level": score_level,
            "confidence_weight": confidence_weight,
        }

    async def _assess_portfolio_quality(
        self,
        quality: Decimal,
        diversification: Decimal,
        concentration: Decimal,
        num_assets: int,
        risk_level: str,
    ) -> Dict:
        """Assess portfolio quality."""
        quality_level = (
            "excellent"
            if quality >= Decimal("80")
            else (
                "good"
                if quality >= Decimal("65")
                else ("acceptable" if quality >= Decimal("50") else "poor")
            )
        )

        diversification_level = (
            "well_diversified"
            if diversification >= Decimal("75")
            else ("adequately_diversified" if diversification >= Decimal("60") else "concentrated")
        )

        concentration_risk = (
            "low"
            if concentration <= Decimal("20")
            else ("moderate" if concentration <= Decimal("40") else "high")
        )

        return {
            "quality": quality,
            "quality_level": quality_level,
            "diversification": diversification,
            "diversification_level": diversification_level,
            "concentration": concentration,
            "concentration_risk": concentration_risk,
            "num_assets": num_assets,
            "risk_level": risk_level,
        }

    async def _assess_risk(
        self,
        max_drawdown: Decimal,
        estimated_max_loss: Decimal,
        portfolio_risk_level: str,
        user_risk_profile: str,
        initial_capital: Decimal,
    ) -> Dict:
        """Assess risk compatibility."""
        warnings = []

        # Drawdown assessment
        drawdown_abs = abs(max_drawdown)
        if drawdown_abs > Decimal("0.30"):
            warnings.append(f"High drawdown risk: {drawdown_abs:.1%}")

        # Risk profile compatibility
        profile_risk_map = {
            "conservative": ["low", "medium"],
            "moderate": ["low", "medium", "high"],
            "aggressive": ["medium", "high"],
        }

        compatible = portfolio_risk_level in profile_risk_map.get(user_risk_profile, [])
        if not compatible:
            warnings.append(
                f"Portfolio risk ({portfolio_risk_level}) incompatible with "
                f"user profile ({user_risk_profile})"
            )

        # Maximum loss assessment
        if estimated_max_loss < -initial_capital * Decimal("0.40"):
            warnings.append("Potential loss exceeds 40% of capital")

        return {
            "drawdown": drawdown_abs,
            "estimated_max_loss": estimated_max_loss,
            "risk_compatible": compatible,
            "warnings": warnings,
        }

    async def _determine_decision_status(
        self,
        validation: Dict,
        feasibility: Dict,
        recommendation: Dict,
        portfolio: Dict,
        risk: Dict,
        sharpe_ratio: Decimal,
    ) -> Tuple[str, str]:
        """Determine final decision status."""

        # Hard gate: validation failure = REJECTED
        if not validation["passed"]:
            return "REJECTED", "low"

        # Hard gate: not viable feasibility = REJECTED
        if feasibility["assessment"] == "NOT_VIABLE":
            return "REJECTED", "medium"

        # Strong approval conditions
        approval_score = Decimal("0")

        # Feasibility contributes 40%
        if feasibility["assessment"] == "VIABLE":
            approval_score += Decimal("40")
        elif feasibility["assessment"] == "MARGINAL":
            approval_score += Decimal("20")

        # Recommendation contributes 30%
        if recommendation["confidence"] == "high":
            approval_score += Decimal("30")
        elif recommendation["confidence"] == "medium":
            approval_score += Decimal("20")
        else:
            approval_score += Decimal("10")

        # Portfolio quality contributes 20%
        if portfolio["quality_level"] in ["excellent", "good"]:
            approval_score += Decimal("20")
        elif portfolio["quality_level"] == "acceptable":
            approval_score += Decimal("10")

        # Risk compatibility contributes 10%
        if risk["risk_compatible"] and len(risk["warnings"]) == 0:
            approval_score += Decimal("10")
        elif risk["risk_compatible"]:
            approval_score += Decimal("5")

        # Sharpe bonus
        if sharpe_ratio >= Decimal("2.0"):
            approval_score += Decimal("5")
        elif sharpe_ratio >= Decimal("1.5"):
            approval_score += Decimal("2")

        # Determine status based on score
        if approval_score >= Decimal("85"):
            return "APPROVED", "high"
        elif approval_score >= Decimal("65"):
            return "CONDITIONAL", "medium"
        else:
            return "REJECTED", "low"

    async def _generate_reasoning(
        self,
        decision: str,
        validation: Dict,
        feasibility: Dict,
        recommendation: Dict,
        portfolio: Dict,
    ) -> Tuple[str, List[str]]:
        """Generate reasoning for decision."""
        supporting = []

        if decision == "APPROVED":
            primary = (
                f"Strategy is viable ({feasibility['assessment']}) with strong "
                f"recommendation ({recommendation['confidence']} confidence) and "
                f"quality portfolio ({portfolio['quality_level']})."
            )
            supporting.append("Feasibility ratio supports deployment")
            supporting.append(f"Portfolio quality is {portfolio['quality_level']}")
            supporting.append(f"Recommendation confidence is {recommendation['confidence']}")

        elif decision == "CONDITIONAL":
            primary = (
                "Strategy shows promise but requires optimization or monitoring. "
                f"Feasibility is {feasibility['assessment']}."
            )
            if feasibility["assessment"] == "MARGINAL":
                supporting.append("Feasibility ratio near threshold - monitor carefully")
            if recommendation["confidence"] == "low":
                supporting.append("Recommendation confidence is lower than preferred")
            if portfolio["quality_level"] in ["acceptable", "poor"]:
                supporting.append("Portfolio could be better optimized")

        else:  # REJECTED
            primary = "Strategy cannot be approved at this time."
            if not validation["passed"]:
                supporting.append(f"Validation failed ({validation['num_failures']} issues)")
            if feasibility["assessment"] == "NOT_VIABLE":
                supporting.append("Feasibility ratio indicates strategy is not viable")
            supporting.append("Review remediation steps before resubmitting")

        return primary, supporting

    async def _generate_remediation(
        self, decision: str, validation_failures: List[str], feasibility: Dict, recommendation: Dict
    ) -> List[str]:
        """Generate remediation steps if needed."""
        steps = []

        if decision == "APPROVED":
            steps = [
                "Monitor backtest results against live trading",
                "Implement position sizing from portfolio allocation",
                "Set up risk monitoring alerts",
            ]

        elif decision == "CONDITIONAL":
            if feasibility["assessment"] == "MARGINAL":
                steps.append("Optimize module parameters to improve expected return")
            if recommendation["confidence"] == "low":
                steps.append("Refine strategy selection with domain expert review")
            steps.append("Establish clear monitoring thresholds for live trading")
            steps.append("Plan regular rebalancing schedule")

        else:  # REJECTED
            steps = ["Address validation failures: " + "; ".join(validation_failures[:2])]
            if feasibility["assessment"] == "NOT_VIABLE":
                steps.append("Adjust target return or increase capital to improve feasibility")
            steps.append("Reassess investment objective and constraints")
            steps.append("Rerun optimization with revised parameters")

        return steps

    async def _update_metrics(self, decision: DeploymentDecision) -> None:
        """Update decision metrics tracking."""
        timestamp = decision.decision_timestamp.strftime("%Y-%m-%d")

        if timestamp not in self.decision_metrics:
            self.decision_metrics[timestamp] = {
                "total": 0,
                "approved": 0,
                "conditional": 0,
                "rejected": 0,
                "avg_feasibility": Decimal("0"),
                "decisions": [],
            }

        metrics = self.decision_metrics[timestamp]
        metrics["total"] += 1

        if decision.decision_status == "APPROVED":
            metrics["approved"] += 1
        elif decision.decision_status == "CONDITIONAL":
            metrics["conditional"] += 1
        else:
            metrics["rejected"] += 1

        metrics["avg_feasibility"] = (
            metrics.get("avg_feasibility", Decimal("0")) * (metrics["total"] - 1)
            + decision.analysis.feasibility_ratio
        ) / metrics["total"]

        metrics["decisions"].append(decision.decision_id)

    async def get_decision_history(
        self, limit: Optional[int] = None, status_filter: Optional[str] = None
    ) -> List[DeploymentDecision]:
        """
        Get decision history with optional filtering.

        Args:
            limit: Maximum decisions to return
            status_filter: Filter by status (APPROVED, CONDITIONAL, REJECTED)

        Returns:
            List of DeploymentDecision objects
        """
        decisions = self.decision_history

        if status_filter:
            decisions = [d for d in decisions if d.decision_status == status_filter]

        if limit:
            decisions = decisions[-limit:]

        return decisions

    async def get_deployment_statistics(self) -> Dict:
        """Get deployment decision statistics."""
        if not self.decision_history:
            return {
                "total_decisions": 0,
                "approval_rate": Decimal("0"),
                "conditional_rate": Decimal("0"),
                "rejection_rate": Decimal("0"),
            }

        total = len(self.decision_history)
        approved = sum(1 for d in self.decision_history if d.decision_status == "APPROVED")
        conditional = sum(1 for d in self.decision_history if d.decision_status == "CONDITIONAL")
        rejected = sum(1 for d in self.decision_history if d.decision_status == "REJECTED")

        return {
            "total_decisions": total,
            "approved_count": approved,
            "conditional_count": conditional,
            "rejected_count": rejected,
            "approval_rate": Decimal(approved) / Decimal(total) * Decimal("100"),
            "conditional_rate": Decimal(conditional) / Decimal(total) * Decimal("100"),
            "rejection_rate": Decimal(rejected) / Decimal(total) * Decimal("100"),
            "avg_feasibility_ratio": self._calculate_avg_feasibility(),
        }

    def _calculate_avg_feasibility(self) -> Decimal:
        """Calculate average feasibility ratio across decisions."""
        if not self.decision_history:
            return Decimal("0")

        total_feasibility = sum(d.analysis.feasibility_ratio for d in self.decision_history)
        return total_feasibility / Decimal(len(self.decision_history))

    def get_orchestrator_status(self) -> Dict:
        """Get orchestrator operational status."""
        return {
            "total_decisions_processed": len(self.decision_history),
            "metrics_entries": len(self.decision_metrics),
            "last_decision": (
                self.decision_history[-1].decision_id if self.decision_history else None
            ),
        }


# Singleton
_orchestrator: Optional[DeploymentDecisionOrchestrator] = None


def get_deployment_decision_orchestrator() -> DeploymentDecisionOrchestrator:
    """Get or create singleton DeploymentDecisionOrchestrator."""
    global _orchestrator
    if _orchestrator is None:

    return _orchestrator
