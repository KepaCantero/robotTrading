"""
T10.1: DeployDecisionOrchestrator - Master deployment decision orchestrator

Synthesizes all components (validation, backtest, recommendation, portfolio)
into a final APPROVED|CONDITIONAL|REJECTED deployment decision.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import ClassVar

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
    reasons: list[str]  # Why this decision was made
    risks: list[str]  # Identified risks
    recommendations: list[str]  # Recommendations for improvement
    next_steps: list[str]  # Actions to take


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
    APPROVAL_THRESHOLDS: ClassVar[dict] = {
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
        validation_report: dict,
        backtest_result: dict,
        recommendation: dict,
        allocation: dict,
        investment_profile: dict | None = None,
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
            next_steps = await self._determine_next_steps(
                status,
                sharpe_ratio=sharpe_ratio,
                feasibility_ratio=feasibility_ratio,
                recommendation_score=recommendation_score,
                strategy_name=str(
                    recommendation.get("executed_strategy")
                    or recommendation.get("recommendation")
                    or ""
                ),
                universe_ew_sharpe=self._safe_float(backtest_result.get("universe_ew_sharpe"))
                or None,
            )

            # Criterio 6 honesto: si el equiponderado pasivo del propio
            # universo batió a la estrategia gestionada, la recomendación
            # desplegable ES el pasivo — decirlo explícitamente en vez de
            # esconder la underperformance tras "optimiza los parámetros".
            # EXCEPCIÓN: si la estrategia YA ES el pasivo (static_ew), el
            # gap residual es el coste real de ejecución (entrada t+1,
            # comisiones, caps de liquidez) — no una "capa de gestión que
            # resta valor", y no puede recomendarse desplegarse a sí mismo.
            ew_return = self._safe_float(backtest_result.get("universe_ew_return_pct"))
            strategy_return = self._safe_float(backtest_result.get("total_return"))
            strategy_name = str(
                recommendation.get("executed_strategy")
                or recommendation.get("recommendation")
                or ""
            )
            if ew_return > 0 and strategy_return < ew_return:
                if strategy_name == "static_ew":
                    # descomposición honesta: el término dominante es el
                    # objetivo de despliegue del 95% (5% de caja permanente
                    # que no compone), NO los costes de las 12 operaciones —
                    # críticas 31-10: "ningún coste realista se come 10 pp"
                    cash_floor_pp = ew_return * 0.05
                    reasons.append(
                        f"The passive twin of this universe did {ew_return:+.1f}% vs "
                        f"{strategy_return:+.1f}% executed "
                        f"({strategy_return - ew_return:+.1f} pp). Decomposed honestly: "
                        f"~{cash_floor_pp:.1f} pp is the engine's permanent 5% cash "
                        "floor (95% deployment target — cash does not compound), the "
                        "rest is staggered entry (t+1, liquidity caps) and commissions "
                        "— this IS the static portfolio, fully invested to 95% by design."
                    )
                else:
                    reasons.append(
                        f"Passive equal-weight of this universe did {ew_return:+.1f}% vs "
                        f"{strategy_return:+.1f}% for the managed strategy "
                        f"({strategy_return - ew_return:+.1f} pp): the management layer "
                        "subtracted value — deploying the static portfolio is the honest option."
                    )
                    next_steps.insert(
                        0,
                        "Deploy the static equal-weight of this universe (annual rebalance) "
                        f"instead of the managed strategy — it beat it by "
                        f"{ew_return - strategy_return:.1f} pp.",
                    )

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

        except (asyncio.TimeoutError, OSError) as e:
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

        # Sharpe gate (owner 31-10: "el umbral de Sharpe debería ser un gate
        # duro, no compensable por score"): bajo 0.5 no hay APPROVED —
        # degrada a CONDITIONAL en vez de REJECT para no romper la regla de
        # que el run por defecto pasa.
        sharpe_gate = sharpe_ratio >= 0.5

        # Feasibility and recommendation matrix
        if (
            feasibility_ratio >= self.APPROVAL_THRESHOLDS["feasibility_ratio_approved"]
            and recommendation_score >= self.APPROVAL_THRESHOLDS["recommendation_score_approved"]
        ):
            if not sharpe_gate:
                return "CONDITIONAL", "LOW"
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
    ) -> list[str]:
        """Generate human-readable reasons for decision."""
        reasons = []

        if status == "APPROVED":
            reasons.append("✅ All validation gates passed")
            reasons.append(f"✅ Feasibility ratio {feasibility_ratio:.2f} exceeds 1.0 threshold")
            reasons.append(f"✅ Recommendation score {recommendation_score:.1f} is strong")
            if sharpe_ratio > 1.0:
                reasons.append(f"✅ Excellent risk-adjusted returns (Sharpe: {sharpe_ratio:.2f})")

        elif status == "CONDITIONAL":
            reasons.append("⚠️  Validation passed but with conditions")
            if feasibility_ratio >= 1.0:
                reasons.append(
                    f"✅ Feasibility ratio {feasibility_ratio:.2f} exceeds 1.0 threshold"
                )
            else:
                reasons.append(
                    f"⚠️  Feasibility ratio {feasibility_ratio:.2f} is moderate (0.7-1.0)"
                )
            reasons.append(f"⚠️  Recommendation score {recommendation_score:.1f} is acceptable")
            reasons.append("⚠️  Strategy requires optimization before full deployment")

        else:  # REJECTED
            if not validation_passed:
                reasons.append("❌ Validation gates failed")
            if feasibility_ratio < 0.7:
                reasons.append(f"❌ Feasibility ratio {feasibility_ratio:.2f} too low")
            if recommendation_score < 60:
                reasons.append(f"❌ Recommendation score {recommendation_score:.1f} insufficient")

        return reasons

    async def _identify_risks(
        self,
        feasibility_ratio: float,
        sharpe_ratio: float,
        allocation: dict,
    ) -> list[str]:
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
            risks.append(f"High concentration: {max_weight * 100:.0f}% in single position")

        return risks

    async def _generate_recommendations(
        self,
        status: str,
        feasibility_ratio: float,
        recommendation_score: float,
    ) -> list[str]:
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

    async def _determine_next_steps(
        self,
        status: str,
        sharpe_ratio: float | None = None,
        feasibility_ratio: float | None = None,
        recommendation_score: float | None = None,
        strategy_name: str = "",
        universe_ew_sharpe: float | None = None,
    ) -> list[str]:
        """Determine next actions based on status. Copy is English (UI
        language), data-driven, and knows whether the run WAS the passive
        — satellite-era advice (and the old Spanish lines) made no sense
        for a static_ew portfolio."""
        next_steps = []

        if status == "APPROVED":
            next_steps.append("1. Review risk management parameters")
            next_steps.append("2. Set up position monitoring")
            next_steps.append("3. Begin deployment with allocated capital")
            next_steps.append("4. Schedule weekly performance reviews")

        elif status == "CONDITIONAL":
            steps: list[str] = []
            passive = strategy_name == "static_ew"
            if passive:
                steps.append(
                    "This IS the passive portfolio — adopt it to paper and let "
                    "the drift band decide when to touch it"
                )
            if sharpe_ratio is not None and sharpe_ratio < 0.5:
                steps.append(
                    f"Sharpe {sharpe_ratio:.2f} < 0.5: the strategy does not yet pay for its risk"
                )
            elif not passive:
                steps.append("Run sensitivity analysis on weights and rebalance frequency")
            if feasibility_ratio is not None and feasibility_ratio < 1.5:
                steps.append(
                    f"Feasibility {feasibility_ratio:.2f} is a thin margin — more "
                    "capital or a more modest target makes it robust"
                )
            if recommendation_score is not None and recommendation_score < 70:
                drag = (
                    f"Sharpe {sharpe_ratio:.2f} vs the universe's {universe_ew_sharpe:.2f}"
                    if universe_ew_sharpe
                    else "the return-per-risk ratio"
                )
                steps.append(
                    f"Score {recommendation_score:.0f}/100 — APPROVED needs 75: "
                    f"the drag is {drag}, not the portfolio"
                )
            else:
                steps.append("Walk-forward validation before larger deployment")
            next_steps = [f"{i}. {s}" for i, s in enumerate(steps, start=1)]

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
