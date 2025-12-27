"""
T4.1 Capacity Fade Validator - Main Orchestrator

Coordinates all components to validate strategy capacity and feasibility.

Validates that strategy alpha is sustainable as capital scales to target level (€250k).
Uses sqrt(capacity) model with liquidity constraints and conservative assumptions.
"""

import logging
from decimal import Decimal
from typing import Optional

from .analyzers import AlphaDecayEstimator, HistoricalCapacityAnalyzer, LiquidityHeadroom
from .models import (
    CapacityFadeAnalysis,
    CapacityFadeRequest,
    CapacityFadeResponse,
    FeasibilityDecision,
    FeasibilityGate,
)

logger = logging.getLogger(__name__)


class CapacityFadeValidator:
    """
    Main orchestrator for capacity fade validation.

    Validates that strategy alpha is sufficient at target capital level.
    Acts as a hard gate: if alpha insufficient, strategy deployment is REJECTED.

    Features:
    - Historical capacity analysis
    - Liquidity headroom calculation
    - Alpha decay estimation
    - Feasibility gating (APPROVED/CONDITIONAL/REJECTED)
    """

    def __init__(self):
        """Initialize capacity fade validator with sub-components."""
        self.capacity_analyzer = HistoricalCapacityAnalyzer()
        self.liquidity_analyzer = LiquidityHeadroom()
        self.alpha_estimator = AlphaDecayEstimator()
        logger.info("✅ CapacityFadeValidator initialized")

    async def validate_capacity_feasibility(
        self,
        request: CapacityFadeRequest,
    ) -> CapacityFadeResponse:
        """
        Validate strategy capacity at target capital.

        Comprehensive validation including:
        1. Historical capacity impact analysis
        2. Liquidity headroom calculation
        3. Alpha decay estimation
        4. Feasibility gating

        Args:
            request: CapacityFadeRequest with strategy and capital parameters

        Returns:
            CapacityFadeResponse with feasibility decision
        """
        try:
            logger.info(
                f"🔍 Validating capacity fade for profile {request.profile_id}: "
                f"€{request.current_capital_usd:,.0f} → €{request.target_capital_usd:,.0f}"
            )

            # Step 1: Analyze historical capacity impact
            capacity_analysis = self.capacity_analyzer.analyze_capacity_impact(
                base_alpha_pct=request.base_alpha_pct,
                backtest_capital_usd=request.backtest_capital_usd,
                current_capital_usd=request.current_capital_usd,
                target_capital_usd=request.target_capital_usd,
                confidence_level=request.confidence_level,
            )

            if "error" in capacity_analysis:
                return CapacityFadeResponse(
                    success=False,
                    feasibility_gate=FeasibilityGate(
                        decision=FeasibilityDecision.REJECTED,
                        approved=False,
                        hard_gate=True,
                        analysis=CapacityFadeAnalysis(
                            base_alpha_pct=request.base_alpha_pct,
                            current_capital_usd=request.current_capital_usd,
                            target_capital_usd=request.target_capital_usd,
                            capacity_fade_ratio=Decimal("0"),
                            estimated_alpha_at_target=Decimal("0"),
                            alpha_sufficient=False,
                            liquidity_constrained=True,
                        ),
                        validation_message="Capacity analysis failed",
                    ),
                    analysis=CapacityFadeAnalysis(
                        base_alpha_pct=request.base_alpha_pct,
                        current_capital_usd=request.current_capital_usd,
                        target_capital_usd=request.target_capital_usd,
                        capacity_fade_ratio=Decimal("0"),
                        estimated_alpha_at_target=Decimal("0"),
                        alpha_sufficient=False,
                        liquidity_constrained=True,
                    ),
                    summary="Capacity analysis failed",
                    error_message=capacity_analysis.get("error"),
                )

            # Step 2: Calculate liquidity constraints
            liquidity_report = self.liquidity_analyzer.calculate_headroom(
                position_size_usd=request.avg_position_size_usd,
                daily_volume_usd=request.avg_position_size_usd
                * Decimal("10")
                * request.avg_daily_volume_multiplier,
                max_allowed_pct=Decimal("5.0"),
            )

            # Step 3: Estimate alpha at target capital
            alpha_decay = self.alpha_estimator.estimate_alpha_at_scale(
                base_alpha_pct=request.base_alpha_pct,
                current_capital_usd=request.current_capital_usd,
                target_capital_usd=request.target_capital_usd,
                fade_model=request.fade_model,
                liquidity_penalty_pct=(
                    Decimal("0") if liquidity_report.headroom_available else Decimal("2.0")
                ),
            )

            if "error" in alpha_decay:
                return CapacityFadeResponse(
                    success=False,
                    feasibility_gate=FeasibilityGate(
                        decision=FeasibilityDecision.REJECTED,
                        approved=False,
                        hard_gate=True,
                        analysis=CapacityFadeAnalysis(
                            base_alpha_pct=request.base_alpha_pct,
                            current_capital_usd=request.current_capital_usd,
                            target_capital_usd=request.target_capital_usd,
                            capacity_fade_ratio=Decimal("0"),
                            estimated_alpha_at_target=Decimal("0"),
                            alpha_sufficient=False,
                            liquidity_constrained=True,
                        ),
                        validation_message="Alpha decay estimation failed",
                    ),
                    analysis=CapacityFadeAnalysis(
                        base_alpha_pct=request.base_alpha_pct,
                        current_capital_usd=request.current_capital_usd,
                        target_capital_usd=request.target_capital_usd,
                        capacity_fade_ratio=Decimal("0"),
                        estimated_alpha_at_target=Decimal("0"),
                        alpha_sufficient=False,
                        liquidity_constrained=True,
                    ),
                    summary="Alpha decay estimation failed",
                    error_message=alpha_decay.get("error"),
                )

            # Step 4: Calculate required alpha
            required_alpha = Decimal("0")
            if request.target_monthly_return_usd:
                required_alpha = self.alpha_estimator.calculate_required_alpha(
                    target_monthly_return_usd=request.target_monthly_return_usd,
                    target_capital_usd=request.target_capital_usd,
                )

            estimated_alpha = Decimal(str(alpha_decay["estimated_alpha_pct"]))
            alpha_sufficient = estimated_alpha >= required_alpha if required_alpha > 0 else True
            capacity_fade_ratio = Decimal(str(alpha_decay["fade_pct"])) / Decimal("100")

            # Step 5: Determine feasibility decision
            feasibility_decision, validation_message, recommendations = self._determine_feasibility(
                estimated_alpha=estimated_alpha,
                required_alpha=required_alpha,
                alpha_sufficient=alpha_sufficient,
                liquidity_constrained=not liquidity_report.headroom_available,
                fade_pct=Decimal(str(alpha_decay["fade_pct"])),
            )

            # Step 6: Build analysis object
            analysis = CapacityFadeAnalysis(
                base_alpha_pct=request.base_alpha_pct,
                current_capital_usd=request.current_capital_usd,
                target_capital_usd=request.target_capital_usd,
                capacity_fade_ratio=capacity_fade_ratio,
                estimated_alpha_at_target=estimated_alpha,
                required_alpha_pct=required_alpha,
                alpha_sufficient=alpha_sufficient,
                fade_model=request.fade_model,
                liquidity_report=liquidity_report,
                liquidity_constrained=not liquidity_report.headroom_available,
                factors={
                    "capacity_scaling": float(capacity_analysis["backtest_to_target_ratio"]),
                    "fade_pct": float(alpha_decay["fade_pct"]),
                    "liquidity_penalty_pct": float(alpha_decay["liquidity_penalty_pct"]),
                    "confidence_level": request.confidence_level,
                },
            )

            # Step 7: Build feasibility gate
            gate = FeasibilityGate(
                decision=feasibility_decision,
                approved=feasibility_decision != FeasibilityDecision.REJECTED,
                hard_gate=feasibility_decision == FeasibilityDecision.REJECTED,
                analysis=analysis,
                validation_message=validation_message,
                recommendations=recommendations,
            )

            # Step 8: Build response
            summary = self._build_summary(
                profile_id=request.profile_id,
                decision=feasibility_decision,
                base_alpha=request.base_alpha_pct,
                estimated_alpha=estimated_alpha,
                required_alpha=required_alpha,
            )

            response = CapacityFadeResponse(
                success=True,
                feasibility_gate=gate,
                analysis=analysis,
                summary=summary,
                details={
                    "alpha_decay": alpha_decay,
                    "capacity_analysis": capacity_analysis,
                    "liquidity_report": liquidity_report.model_dump(),
                },
            )

            # Log result
            status = "✅" if gate.approved else "❌"
            logger.info(f"{status} Capacity validation complete: {feasibility_decision.value}")

            return response

        except Exception as e:
            logger.error(f"❌ Capacity validation failed: {str(e)}")
            return CapacityFadeResponse(
                success=False,
                feasibility_gate=FeasibilityGate(
                    decision=FeasibilityDecision.REJECTED,
                    approved=False,
                    hard_gate=True,
                    analysis=CapacityFadeAnalysis(
                        base_alpha_pct=request.base_alpha_pct,
                        current_capital_usd=request.current_capital_usd,
                        target_capital_usd=request.target_capital_usd,
                        capacity_fade_ratio=Decimal("0"),
                        estimated_alpha_at_target=Decimal("0"),
                        alpha_sufficient=False,
                        liquidity_constrained=True,
                    ),
                    validation_message=f"Validation error: {str(e)}",
                ),
                analysis=CapacityFadeAnalysis(
                    base_alpha_pct=request.base_alpha_pct,
                    current_capital_usd=request.current_capital_usd,
                    target_capital_usd=request.target_capital_usd,
                    capacity_fade_ratio=Decimal("0"),
                    estimated_alpha_at_target=Decimal("0"),
                    alpha_sufficient=False,
                    liquidity_constrained=True,
                ),
                summary="Validation failed",
                error_message=str(e),
            )

    def _determine_feasibility(
        self,
        estimated_alpha: Decimal,
        required_alpha: Decimal,
        alpha_sufficient: bool,
        liquidity_constrained: bool,
        fade_pct: Decimal,
    ) -> tuple:
        """
        Determine feasibility decision based on analysis.

        Args:
            estimated_alpha: Projected alpha at target capital
            required_alpha: Minimum alpha needed
            alpha_sufficient: Whether estimated >= required
            liquidity_constrained: Whether liquidity is a constraint
            fade_pct: Percentage alpha fade

        Returns:
            (FeasibilityDecision, validation_message, recommendations)
        """
        recommendations = []

        # Hard gate: if alpha insufficient, REJECT
        if not alpha_sufficient and required_alpha > 0:
            decision = FeasibilityDecision.REJECTED
            message = (
                "Alpha insufficient at target capital: "
                f"{estimated_alpha:.2f}% < {required_alpha:.2f}% required"
            )
            recommendations.append("Strategy cannot generate required returns at target capital")
            recommendations.append(
                "Consider: (1) Improving alpha, (2) Reducing target capital, (3) Lowering return targets"
            )
            return decision, message, recommendations

        # Marginal case: alpha sufficient but with constraints
        if fade_pct > Decimal("40") or liquidity_constrained:
            decision = FeasibilityDecision.CONDITIONAL
            message = (
                "Alpha sufficient but with constraints: "
                f"{estimated_alpha:.2f}% alpha after {fade_pct:.1f}% fade"
            )
            if fade_pct > Decimal("40"):
                recommendations.append(
                    f"High alpha fade ({fade_pct:.1f}%), requires close monitoring"
                )
            if liquidity_constrained:
                recommendations.append(
                    "Position sizing constrained by liquidity, may limit strategy effectiveness"
                )
            return decision, message, recommendations

        # Approved: sufficient alpha with reasonable fade
        decision = FeasibilityDecision.APPROVED
        message = (
            "Strategy feasible at target capital: "
            f"{estimated_alpha:.2f}% alpha after {fade_pct:.1f}% fade"
        )
        if fade_pct > Decimal("20"):
            recommendations.append(f"Monitor alpha fade ({fade_pct:.1f}%) during live trading")
        recommendations.append("Ready for deployment at target capital")

        return decision, message, recommendations

    def _build_summary(
        self,
        profile_id: str,
        decision: FeasibilityDecision,
        base_alpha: Decimal,
        estimated_alpha: Decimal,
        required_alpha: Decimal,
    ) -> str:
        """
        Build human-readable summary for decision makers.

        Args:
            profile_id: Strategy profile ID
            decision: Feasibility decision
            base_alpha: Base alpha from backtest
            estimated_alpha: Projected alpha at target capital
            required_alpha: Minimum required alpha

        Returns:
            Summary string
        """
        decision_text = {
            FeasibilityDecision.APPROVED: "✅ APPROVED",
            FeasibilityDecision.CONDITIONAL: "⚠️ CONDITIONAL",
            FeasibilityDecision.REJECTED: "❌ REJECTED",
        }[decision]

        alpha_text = f"Base: {base_alpha:.2f}% → Projected: {estimated_alpha:.2f}%"
        if required_alpha > 0:
            alpha_text += f" (Required: {required_alpha:.2f}%)"

        summary = f"{decision_text}: Strategy {profile_id} capacity validation - {alpha_text}"

        return summary


# Singleton instance
_validator: Optional[CapacityFadeValidator] = None


def get_capacity_fade_validator() -> CapacityFadeValidator:
    """Get or create singleton CapacityFadeValidator."""
    global _validator
    if _validator is None:

    return _validator
