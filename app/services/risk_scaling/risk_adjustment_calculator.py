"""
T8.1.1: RiskAdjustmentCalculator - Calculate dynamic risk adjustments

Determines position scaling and risk limits based on feasibility_ratio,
capital tier, and market conditions.
"""

import logging
from decimal import Decimal
from typing import ClassVar, Optional

logger = logging.getLogger(__name__)


class RiskAdjustmentCalculator:
    """
    Calculates position size and leverage adjustments based on strategy feasibility.

    Core Logic:
    - feasibility_ratio >= 1.0: Strategy can meet targets -> maintain 100% position
    - 0.7-1.0: Strategy marginal -> scale 70-100% (reduce to improve odds)
    - < 0.7: Strategy not viable -> reject or scale 0-70% (high risk, low confidence)

    Capital tier effects:
    - MICRO: Conservative scaling (smaller positions, tighter stops)
    - SMALL: Moderate scaling
    - MEDIUM: Moderate-aggressive
    - LARGE: Aggressive scaling available
    """

    # Position scaling multipliers by feasibility ratio
    POSITION_SCALING: ClassVar[dict] = {
        "very_high": (1.3, 1.5),  # >= 1.5: Can increase positions
        "high": (1.0, 1.5),  # 1.0-1.5: Hold or slightly increase
        "acceptable": (0.8, 1.0),  # 0.7-1.0: Scale down slightly
        "marginal": (0.5, 0.7),  # 0.5-0.7: Scale down significantly
        "unviable": (0.0, 0.5),  # < 0.5: Reject or minimal sizing
    }

    # Capital tier multipliers (affect max leverage/position sizing)
    CAPITAL_TIER_MULTIPLIERS: ClassVar[dict] = {
        "micro": Decimal("0.5"),  # €1k-€15k: Tight controls
        "small": Decimal("0.75"),  # €15k-€50k: Moderate controls
        "medium": Decimal("1.0"),  # €50k-€250k: Standard controls
        "large": Decimal("1.25"),  # €250k+: More flexibility
    }

    # Stop loss widening factors (based on volatility/risk_tolerance)
    STOP_LOSS_WIDENING: ClassVar[dict] = {
        1: Decimal("0.5"),  # Very tight stops (1% risk tolerance)
        2: Decimal("0.7"),
        3: Decimal("0.9"),
        4: Decimal("1.1"),
        5: Decimal("1.3"),
        6: Decimal("1.5"),
        7: Decimal("2.0"),  # Wide stops (7 = aggressive)
    }

    def __init__(self):
        """Initialize calculator."""
        logger.info("✅ RiskAdjustmentCalculator initialized")

    def calculate_position_scaling(
        self,
        feasibility_ratio: Decimal,
        base_position_size: Decimal,
        capital_tier: str,
        risk_tolerance: int = 4,
    ) -> tuple[Decimal, str]:
        """
        Calculate adjusted position size based on feasibility.

        Args:
            feasibility_ratio: Required return / Achievable return
                - >= 1.0: Can meet target
                - 0.7-1.0: Marginal
                - < 0.7: Unviable
            base_position_size: Original position size (€)
            capital_tier: micro/small/medium/large
            risk_tolerance: 1-7 (affects scale)

        Returns:
            (scaled_position_size, reason_string)
        """
        feasibility_ratio = Decimal(str(feasibility_ratio))
        base_position_size = Decimal(str(base_position_size))

        # Determine scaling category
        if feasibility_ratio >= Decimal("1.5"):
            category = "very_high"
            _scale_min, _scale_max = self.POSITION_SCALING["very_high"]
        elif feasibility_ratio >= Decimal("1.0"):
            category = "high"
            _scale_min, _scale_max = self.POSITION_SCALING["high"]
        elif feasibility_ratio >= Decimal("0.7"):
            category = "acceptable"
            _scale_min, _scale_max = self.POSITION_SCALING["acceptable"]
        elif feasibility_ratio >= Decimal("0.5"):
            category = "marginal"
            _scale_min, _scale_max = self.POSITION_SCALING["marginal"]
        else:
            category = "unviable"
            _scale_min, _scale_max = self.POSITION_SCALING["unviable"]

        # Calculate scale factor
        scale_factor = self._interpolate_scale(
            feasibility_ratio=feasibility_ratio,
            category=category,
            risk_tolerance=risk_tolerance,
        )

        # Apply capital tier modifier
        tier_multiplier = self.CAPITAL_TIER_MULTIPLIERS.get(capital_tier.lower(), Decimal("1.0"))
        final_scale = scale_factor * tier_multiplier

        # Cap scale to reasonable range
        final_scale = max(Decimal("0"), min(final_scale, Decimal("1.5")))

        # Calculate scaled position
        scaled_position = base_position_size * final_scale

        # Generate reason
        reason = (
            f"Feasibility ratio {feasibility_ratio:.2f} ({category}) -> "
            f"scale {final_scale:.2f}x ({capital_tier} tier) -> "
            f"€{scaled_position:,.0f}"
        )

        logger.info(f"Position scaling: {reason}")
        return scaled_position, reason

    def _interpolate_scale(
        self,
        feasibility_ratio: Decimal,
        category: str,
        risk_tolerance: int,
    ) -> Decimal:
        """
        Interpolate scale factor within category range.

        Risk tolerance affects scale:
        - Low risk tolerance (1-2): Use conservative end of range
        - Medium (3-5): Use midpoint
        - High (6-7): Use aggressive end of range
        """
        scale_min, scale_max = self.POSITION_SCALING[category]

        if risk_tolerance <= 2:
            # Conservative: use lower bound
            return Decimal(str(scale_min))
        elif risk_tolerance >= 6:
            # Aggressive: use upper bound
            return Decimal(str(scale_max))
        else:
            # Moderate: interpolate
            weight = Decimal(str((risk_tolerance - 3) / 2.0))  # 0-1
            return (
                Decimal(str(scale_min))
                + (Decimal(str(scale_max)) - Decimal(str(scale_min))) * weight
            )

    def calculate_leverage_adjustment(
        self,
        feasibility_ratio: Decimal,
        capital_tier: str,
        market_volatility: str = "normal",
        risk_tolerance: int = 4,
    ) -> tuple[Decimal, str]:
        """
        Calculate adjusted leverage based on strategy and market conditions.

        Args:
            feasibility_ratio: Strategy feasibility
            capital_tier: Account tier
            market_volatility: normal/stressed/volatile
            risk_tolerance: 1-7

        Returns:
            (leverage_multiplier, reason)
        """
        feasibility_ratio = Decimal(str(feasibility_ratio))

        # Base leverage by tier
        base_leverage = {
            "micro": Decimal("1.0"),  # No leverage for small accounts
            "small": Decimal("1.0"),
            "medium": Decimal("1.5"),  # 1.5x leverage allowed
            "large": Decimal("2.0"),  # 2x leverage allowed
        }.get(capital_tier.lower(), Decimal("1.0"))

        # Reduce leverage if strategy not viable
        if feasibility_ratio < Decimal("0.7"):
            leverage = base_leverage * Decimal("0.5")
            reason = (
                f"Low feasibility ({feasibility_ratio:.2f}) -> reduce leverage to {leverage:.2f}x"
            )
        elif feasibility_ratio < Decimal("1.0"):
            leverage = base_leverage * Decimal("0.75")
            reason = f"Marginal feasibility ({feasibility_ratio:.2f}) -> {leverage:.2f}x leverage"
        else:
            leverage = base_leverage
            reason = f"Good feasibility ({feasibility_ratio:.2f}) -> {leverage:.2f}x leverage"

        # Adjust for market volatility
        if market_volatility == "volatile":
            leverage = leverage * Decimal("0.8")
            reason += " (reduced for high volatility)"
        elif market_volatility == "stressed":
            leverage = leverage * Decimal("0.5")
            reason += " (emergency reduction for market stress)"

        # Adjust for risk tolerance
        if risk_tolerance <= 2:
            leverage = leverage * Decimal("0.75")
            reason += " (conservative risk profile)"
        elif risk_tolerance >= 6:
            # Aggressive profiles can use full leverage (already accounted for)
            pass

        # Cap leverage
        leverage = max(Decimal("1.0"), min(leverage, Decimal("2.5")))

        logger.info(f"Leverage adjustment: {reason}")
        return leverage, reason

    def calculate_stop_loss_adjustment(
        self,
        recommended_stop_loss_pct: Decimal,
        risk_tolerance: int,
        volatility_multiplier: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Calculate volatility-adjusted stop loss.

        Args:
            recommended_stop_loss_pct: Original stop loss as percentage (e.g., 0.02 = 2%)
            risk_tolerance: 1-7 (affects how loose stops can be)
            volatility_multiplier: Current vol / avg vol (e.g., 1.5 = 50% higher vol)

        Returns:
            Adjusted stop loss percentage
        """
        if volatility_multiplier is None:
            volatility_multiplier = Decimal("1.0")
        recommended_stop_loss_pct = Decimal(str(recommended_stop_loss_pct))
        volatility_multiplier = Decimal(str(volatility_multiplier))

        # Get widening factor for risk tolerance
        widening_factor = self.STOP_LOSS_WIDENING.get(risk_tolerance, Decimal("1.1"))

        # Apply volatility adjustment
        adjusted_stop = recommended_stop_loss_pct * widening_factor * volatility_multiplier

        # Cap very loose stops
        max_stop = Decimal("0.10")  # Never wider than 10%
        adjusted_stop = min(adjusted_stop, max_stop)

        logger.info(
            f"Stop loss: {recommended_stop_loss_pct:.2%} * "
            f"{widening_factor:.2f} (risk_tol) * "
            f"{volatility_multiplier:.2f} (vol) -> {adjusted_stop:.2%}"
        )

        return adjusted_stop

    def calculate_position_and_leverage(
        self,
        feasibility_ratio: Decimal,
        base_position_size: Decimal,
        capital: Decimal,
        capital_tier: str,
        risk_tolerance: int = 4,
        market_volatility: str = "normal",
    ) -> dict[str, any]:
        """
        Calculate both position and leverage adjustments comprehensively.

        Args:
            feasibility_ratio: Strategy viability metric
            base_position_size: Original position (€)
            capital: Total capital (€)
            capital_tier: Account tier
            risk_tolerance: 1-7
            market_volatility: normal/stressed/volatile

        Returns:
            Dict with position_size, leverage, max_capital_at_risk, reasons
        """
        position_size, pos_reason = self.calculate_position_scaling(
            feasibility_ratio=feasibility_ratio,
            base_position_size=base_position_size,
            capital_tier=capital_tier,
            risk_tolerance=risk_tolerance,
        )

        leverage, lev_reason = self.calculate_leverage_adjustment(
            feasibility_ratio=feasibility_ratio,
            capital_tier=capital_tier,
            market_volatility=market_volatility,
            risk_tolerance=risk_tolerance,
        )

        # Calculate capital at risk (position * leverage)
        capital_at_risk = position_size * leverage

        # Cap at available capital
        if capital_at_risk > capital:
            capital_at_risk = capital

        pct_capital_at_risk = (capital_at_risk / capital) if capital > 0 else Decimal("0")

        return {
            "position_size": position_size,
            "leverage": leverage,
            "capital_at_risk": capital_at_risk,
            "pct_capital_at_risk": pct_capital_at_risk,
            "position_reason": pos_reason,
            "leverage_reason": lev_reason,
        }


# Singleton
_calculator: Optional[RiskAdjustmentCalculator] = None


def get_risk_adjustment_calculator() -> RiskAdjustmentCalculator:
    """Get or create singleton RiskAdjustmentCalculator."""
    global _calculator
    if _calculator is None:
        _calculator = RiskAdjustmentCalculator()

    return _calculator
