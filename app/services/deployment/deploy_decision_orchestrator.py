"""
T10.1: DeployDecisionOrchestrator - Master deployment decision orchestrator

Synthesizes all components (validation, backtest, recommendation, portfolio)
into a final APPROVED|REJECTED deployment decision.

FIX 3 (owner 31-10): verdicts are BINARY. Four hard gates, none
compensable by score — a run passes ALL of them or it is REJECTED with
the exact list of what failed and the structural change that would
approve it. CONDITIONAL is retired (the 27-10 "the default must pass"
product rule is jubilated by the same decree):

1. validation gates passed (T5.1, incl. walk-forward)
2. Sharpe >= 0.50
3. max drawdown <= the risk profile's declared tolerance
   (aggressive 35 / moderate 30 / conservative 25)
4. feasibility ratio >= 1.0
5. strategy >= passive twin after costs, minus a 2 pp execution
   tolerance (the twin buys day-one with no costs; the engine enters
   t+1, pays commissions and respects liquidity caps)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar

logger = logging.getLogger(__name__)


@dataclass
class DeploymentDecision:
    """Final deployment decision with rationale."""

    status: str  # "APPROVED", "REJECTED"
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


#: execution tolerance (pp) vs the passive twin: the twin enters day-one
#: cost-free; the real engine enters t+1, pays commissions and respects
#: liquidity caps. A managed strategy must BEAT the twin, a passive one
#: may trail it by at most this
TWIN_EXECUTION_TOLERANCE_PP = 2.0

#: Sharpe floor for ANY deployment (owner 31-10: hard gate, not
#: compensable by score)
SHARPE_HARD_FLOOR = 0.50


def _dd_tolerance_for_risk(risk_profile: str | None) -> float:
    """DD tolerance (%, 0-100) for the run's risk profile (single source:
    ValidationEngine.DD_TOLERANCE_BY_RISK_PCT)."""
    from app.services.validation_engine.validation_engine import DD_TOLERANCE_BY_RISK_PCT

    key = (risk_profile or "").strip().lower()
    return float(DD_TOLERANCE_BY_RISK_PCT.get(key, Decimal("30")))


class DeployDecisionOrchestrator:
    """
    T10.1: Master orchestrator for deployment decisions.

    Synthesizes:
    - ValidationReport (passed/failed gates)
    - BacktestResult (feasibility_ratio, returns, Sharpe, drawdown, twin)
    - StrategyRecommendation (score, confidence — informational, NOT a gate)
    - PortfolioAllocation (diversification, passive-honesty metrics)

    Into a final APPROVED|REJECTED decision (binary, FIX 3).
    """

    # Decision thresholds (score is informational since FIX 3)
    APPROVAL_THRESHOLDS: ClassVar[dict] = {
        "feasibility_ratio_approved": 1.0,  # Can fully meet target
        "sharpe_hard_floor": SHARPE_HARD_FLOOR,
        "twin_execution_tolerance_pp": TWIN_EXECUTION_TOLERANCE_PP,
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
            max_drawdown = backtest_result.get("max_drawdown")
            max_drawdown = abs(self._safe_float(max_drawdown)) if max_drawdown is not None else None
            twin_return = backtest_result.get("universe_ew_return_pct")
            twin_return = self._safe_float(twin_return) if twin_return is not None else None
            strategy_return = self._safe_float(backtest_result.get("total_return"))
            total_trades = int(backtest_result.get("total_trades") or 0)
            commissions_pp = self._safe_float(backtest_result.get("commissions_paid_pct"))
            risk_profile = str((investment_profile or {}).get("risk_profile") or "")
            dd_tolerance = _dd_tolerance_for_risk(risk_profile)
            weight_dev_pp = allocation.get("max_weight_deviation_pct")
            avg_cash_pct = allocation.get("avg_cash_pct")

            # Determine status: binary, hard gates only (FIX 3)
            status, confidence, failures = await self._determine_status(
                validation_passed=validation_passed,
                feasibility_ratio=feasibility_ratio,
                recommendation_score=recommendation_score,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                dd_tolerance=dd_tolerance,
                twin_return=twin_return,
                strategy_return=strategy_return,
                total_trades=total_trades,
            )

            # Generate reasons, risks, and recommendations
            reasons = await self._generate_reasons(
                status,
                validation_passed,
                feasibility_ratio,
                recommendation_score,
                sharpe_ratio,
                failures=failures,
                max_drawdown=max_drawdown,
                dd_tolerance=dd_tolerance,
                twin_return=twin_return,
                strategy_return=strategy_return,
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
                failures=failures,
                weight_dev_pp=weight_dev_pp,
                avg_cash_pct=avg_cash_pct,
            )

            # Criterio 6 honesto: descomposición del gap vs el gemelo pasivo
            # del propio universo. EXCEPCIÓN static_ew: la estrategia YA ES
            # el pasivo — el gap residual es coste real de ejecución (entrada
            # t+1, comisiones, caps de liquidez), y se descompone en cifras:
            # caja media + comisiones + residual. Un residual >2 pp con
            # <20 trades NO es coste: es bug de despliegue y se marca como
            # tal (regla de honestidad 31-10 — nunca disfrazarlo de coste).
            ew_return = twin_return or 0.0
            strategy_name = str(
                recommendation.get("executed_strategy")
                or recommendation.get("recommendation")
                or ""
            )
            if ew_return > 0 and strategy_return < ew_return:
                gap_pp = ew_return - strategy_return
                cash_pp = (avg_cash_pct or 0.0) * (ew_return / 100.0)
                residual_pp = gap_pp - cash_pp - commissions_pp
                parts = [
                    f"~{cash_pp:.1f} pp average cash drag",
                    f"{commissions_pp:.1f} pp commissions",
                ]
                if strategy_name == "static_ew":
                    # descomposición honesta del gap YA aprobado (≤2 pp por el
                    # gate): lo explicado (caja, comisiones) y el residual de
                    # entrada escalonada t+1 + caps de liquidez
                    reasons.append(
                        f"The passive twin of this universe did {ew_return:+.1f}% vs "
                        f"{strategy_return:+.1f}% executed ({strategy_return - ew_return:+.1f} pp), "
                        "decomposed honestly: "
                        + ", ".join(parts)
                        + f", residual {residual_pp:.1f} pp (staggered t+1 entry and "
                        "liquidity caps) — this IS the static portfolio, deployed to "
                        "target with real execution."
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
        *,
        max_drawdown: float | None = None,
        dd_tolerance: float = 30.0,
        twin_return: float | None = None,
        strategy_return: float = 0.0,
        total_trades: int = 0,
    ) -> tuple:
        """Binary hard-gate evaluation (FIX 3, owner 31-10).

        Every gate is HARD — none compensable by recommendation score.
        Returns (status, confidence, failures): APPROVED only when ALL
        gates pass; otherwise REJECTED with the exact list of failures.
        CONDITIONAL is retired.
        """
        failures: list[str] = []
        if not validation_passed:
            failures.append("validation gates failed (see the validation report)")
        if sharpe_ratio < SHARPE_HARD_FLOOR:
            failures.append(f"Sharpe {sharpe_ratio:.2f} < {SHARPE_HARD_FLOOR:.2f} hard floor")
        if max_drawdown is not None and max_drawdown > dd_tolerance:
            failures.append(
                f"max drawdown {max_drawdown:.1f}% > {dd_tolerance:.0f}% tolerance "
                "for this risk profile"
            )
        if feasibility_ratio < self.APPROVAL_THRESHOLDS["feasibility_ratio_approved"]:
            failures.append(
                f"feasibility ratio {feasibility_ratio:.2f} < 1.0 "
                "(the run cannot reach its own target return)"
            )
        if (
            twin_return is not None
            and twin_return > 0
            and strategy_return < twin_return - TWIN_EXECUTION_TOLERANCE_PP
        ):
            trail_pp = twin_return - strategy_return
            failure = (
                f"strategy {strategy_return:+.1f}% trails the passive twin "
                f"{twin_return:+.1f}% by more than {TWIN_EXECUTION_TOLERANCE_PP:.0f} pp "
                "after execution costs"
            )
            # regla de honestidad 31-10: una brecha >2 pp con <20 trades NO
            # es coste de ejecución (ninguna ejecución honesta de 8 órdenes
            # cuesta eso) — es un bug de despliegue y se nombra como tal
            if total_trades < 20:
                failure += (
                    f" — a {trail_pp:.1f} pp gap on {total_trades} trades is a "
                    "DEPLOYMENT BUG, not execution cost"
                )
            failures.append(failure)

        if failures:
            return "REJECTED", "LOW", failures
        confidence = "HIGH" if sharpe_ratio > 1.0 else "MODERATE"
        return "APPROVED", confidence, []

    async def _generate_reasons(
        self,
        status: str,
        validation_passed: bool,
        feasibility_ratio: float,
        recommendation_score: float,
        sharpe_ratio: float,
        *,
        failures: list[str] | None = None,
        max_drawdown: float | None = None,
        dd_tolerance: float = 30.0,
        twin_return: float | None = None,
        strategy_return: float = 0.0,
    ) -> list[str]:
        """Generate human-readable reasons for decision.

        REJECTED carries the EXACT list of failed gates (owner 31-10) —
        one line per gate, with the number that failed it."""
        reasons = []

        if status == "APPROVED":
            reasons.append("✅ All validation gates passed")
            reasons.append(f"✅ Sharpe {sharpe_ratio:.2f} ≥ {SHARPE_HARD_FLOOR:.2f} hard floor")
            if max_drawdown is not None:
                reasons.append(
                    f"✅ Max drawdown {max_drawdown:.1f}% within the "
                    f"{dd_tolerance:.0f}% tolerance of this risk profile"
                )
            reasons.append(f"✅ Feasibility ratio {feasibility_ratio:.2f} ≥ 1.0")
            if twin_return is not None and twin_return > 0:
                verdict = "beats" if strategy_return >= twin_return else "trails within cost of"
                reasons.append(
                    f"✅ {verdict} the passive twin of its universe "
                    f"({strategy_return:+.1f}% vs {twin_return:+.1f}%)"
                )
            reasons.append(f"ℹ️ Recommendation score {recommendation_score:.1f}/100 (informational)")

        else:  # REJECTED — the exact failure list, one per gate
            for failure in failures or []:
                reasons.append(f"❌ {failure}")

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
                "More capital or a more modest target return closes the feasibility gap"
            )

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
        failures: list[str] | None = None,
        weight_dev_pp: float | None = None,
        avg_cash_pct: float | None = None,
    ) -> list[str]:
        """Determine next actions based on status. Copy is English (UI
        language) and data-driven.

        REJECTED (owner 31-10): each failed gate names the STRUCTURAL
        change that would approve it — a REJECTED default must tell the
        user what to change, not just "optimize".

        APPROVED static_ew claims "This IS the passive portfolio" ONLY
        when the executed weights stayed within 1 pp of 1/N and average
        cash stayed under 1% (FIX 4); otherwise it says NOT-passive with
        the exact numbers."""
        next_steps = []

        if status == "APPROVED":
            if strategy_name == "static_ew":
                dev = weight_dev_pp if weight_dev_pp is not None else float("nan")
                cash = avg_cash_pct if avg_cash_pct is not None else float("nan")
                if dev <= 1.0 and cash < 1.0:
                    next_steps.append(
                        "This IS the passive portfolio — weights within "
                        f"{dev:.2f} pp of 1/N, average cash {cash:.2f}%. Adopt it to "
                        "paper and let the drift band decide when to touch it"
                    )
                else:
                    next_steps.append(
                        "This is NOT the passive portfolio — weights deviated "
                        f"{dev:.2f} pp from 1/N, average cash {cash:.2f}% "
                        "(bar: <1 pp and <1%). Fix the deployment before adopting it"
                    )
            next_steps.append("1. Review risk management parameters")
            next_steps.append("2. Set up position monitoring")
            next_steps.append("3. Begin deployment with allocated capital")
            next_steps.append("4. Schedule weekly performance reviews")

        else:  # REJECTED — the structural change per failed gate
            steps: list[str] = []
            for failure in failures or []:
                if "Sharpe" in failure:
                    drag = (
                        f" (the universe's passive twin runs {universe_ew_sharpe:.2f})"
                        if universe_ew_sharpe
                        else ""
                    )
                    steps.append(
                        f"Sharpe {sharpe_ratio:.2f}{drag}: this universe/strategy "
                        "combination does not pay for its risk — a structurally "
                        "better risk-adjusted mix (e.g. a genuine bond cushion, not "
                        "another equity sleeve) is needed, not parameter tuning"
                    )
                elif "drawdown" in failure:
                    steps.append(
                        "Drawdown beyond this profile's tolerance: add real ballast "
                        "(bond sleeve) or accept a lower-risk profile — tuning "
                        "entry timing will not cut a 10-year drawdown"
                    )
                elif "feasibility" in failure:
                    steps.append(
                        f"Feasibility {feasibility_ratio:.2f}: the target return is "
                        "unreachable with this capital/universe — raise capital, "
                        "lower the target, or extend the horizon"
                    )
                elif "passive twin" in failure:
                    if "DEPLOYMENT BUG" in failure:
                        steps.append(
                            "The gap vs the passive twin is a DEPLOYMENT BUG (too few "
                            "trades for honest execution to cost that much) — report it; "
                            "do not deploy until it is fixed"
                        )
                    else:
                        steps.append(
                            "The passive twin beats this strategy after costs: deploy the "
                            "static equal-weight of the universe instead — the management "
                            "layer subtracts value here"
                        )
                elif "validation" in failure:
                    steps.append(
                        "Validation gates failed (walk-forward, capital or costs): "
                        "read the validation report — the run is not deployable as is"
                    )
            next_steps = [f"{i}. {s}" for i, s in enumerate(steps, start=1)] or [
                "1. Review the failed gates above and rerun"
            ]

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
