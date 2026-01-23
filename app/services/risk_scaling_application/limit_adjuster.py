"""
T8.1 LimitAdjuster - Position size and leverage limit enforcement

Manages position sizing constraints based on scaling adjustments.

Responsibilities:
- Adjust position limits based on scaling factors
- Validate limit breaches
- Apply leverage adjustments
- Enforce hard stops
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.services.portfolio_constructor import AllocationWeight

logger = logging.getLogger(__name__)


@dataclass
class AdjustedLimit:
    """Adjusted position limit after scaling."""

    module_name: str
    original_limit: Decimal
    adjusted_limit: Decimal
    scaling_applied: Decimal
    reason: str
    breached: bool = False


@dataclass
class LimitBreach:
    """Position limit breach detection."""

    module_name: str
    current_position: Decimal
    adjusted_limit: Decimal
    excess: Decimal
    severity: str  # "warning", "critical"
    recommendation: str


class LimitAdjuster:
    """
    Manages position sizing and leverage limits.

    Enforces constraints:
    - Position size limits (max € per position)
    - Leverage limits (max portfolio leverage)
    - Allocation limits (max % of portfolio)
    - Hard stops (critical breaches)
    """

    def __init__(
        self,
        default_position_limit: Decimal = Decimal("50000"),
        default_max_leverage: Decimal = Decimal("2.0"),
        default_max_allocation: Decimal = Decimal("25"),  # % of portfolio
    ):
        """
        Initialize limit adjuster.

        Args:
            default_position_limit: Default max € per position
            default_max_leverage: Default max portfolio leverage
            default_max_allocation: Default max % of portfolio per module
        """
        self.default_position_limit = default_position_limit
        self.default_max_leverage = default_max_leverage
        self.default_max_allocation = default_max_allocation
        logger.info("✅ LimitAdjuster initialized")

    # ========================================================================
    # Limit Adjustment
    # ========================================================================

    def adjust_position_limits(
        self,
        original_allocations: List[AllocationWeight],
        scaling_factor: Decimal,
        portfolio_value: Decimal,
    ) -> List[AdjustedLimit]:
        """
        Adjust position limits based on scaling factor.

        Args:
            original_allocations: Original allocation weights
            scaling_factor: Overall scaling factor from RiskAdjustmentCalculator
            portfolio_value: Current portfolio value

        Returns:
            List of adjusted limits
        """
        adjusted_limits = []

        for allocation in original_allocations:
            # Calculate base limit (5% of portfolio or default, whichever is smaller)
            base_limit = min(
                portfolio_value * (Decimal("5") / Decimal("100")),
                self.default_position_limit,
            )

            # Calculate allocation-based limit
            allocation_limit = portfolio_value * (allocation.weight_pct / Decimal("100"))

            # Use stricter of the two
            position_limit = min(base_limit, allocation_limit)

            # Apply scaling factor
            adjusted_limit = position_limit * scaling_factor

            # Enforce hard floor (never allow zero)
            adjusted_limit = max(adjusted_limit, Decimal("1000"))  # Min €1000

            # Enforce hard ceiling (never exceed portfolio value)
            adjusted_limit = min(adjusted_limit, portfolio_value)

            reason = f"Base: €{position_limit:,.0f}, Scaled by {scaling_factor:.2f}x"

            adjusted_limits.append(
                AdjustedLimit(
                    module_name=allocation.module_name,
                    original_limit=position_limit,
                    adjusted_limit=adjusted_limit,
                    scaling_applied=scaling_factor,
                    reason=reason,
                    breached=False,
                )
            )

        logger.info(f"✅ Adjusted position limits for {len(adjusted_limits)} modules")
        return adjusted_limits

    # ========================================================================
    # Breach Detection
    # ========================================================================

    def detect_limit_breaches(
        self,
        current_positions: Dict[str, Decimal],  # module_name → position value
        adjusted_limits: List[AdjustedLimit],
    ) -> List[LimitBreach]:
        """
        Detect position limit breaches.

        Args:
            current_positions: Current position values by module
            adjusted_limits: Adjusted limits for each module

        Returns:
            List of detected breaches
        """
        breaches = []

        for limit in adjusted_limits:
            current_pos = current_positions.get(limit.module_name, Decimal("0"))

            if current_pos > limit.adjusted_limit:
                excess = current_pos - limit.adjusted_limit
                excess_pct = (excess / limit.adjusted_limit) * Decimal("100")

                # Determine severity
                if excess_pct > Decimal("25"):
                    severity = "critical"
                    recommendation = f"⚠️ CRITICAL: Reduce {limit.module_name} by €{excess:,.0f} ({excess_pct:.1f}%)"
                else:
                    severity = "warning"
                    recommendation = f"⚠️ WARNING: Reduce {limit.module_name} by €{excess:,.0f} ({excess_pct:.1f}%)"

                breach = LimitBreach(
                    module_name=limit.module_name,
                    current_position=current_pos,
                    adjusted_limit=limit.adjusted_limit,
                    excess=excess,
                    severity=severity,
                    recommendation=recommendation,
                )
                breaches.append(breach)
                limit.breached = True

        if breaches:
            logger.warning(f"⚠️ Detected {len(breaches)} position limit breaches")
        return breaches

    # ========================================================================
    # Leverage Adjustment
    # ========================================================================

    def apply_leverage_adjustment(
        self,
        base_leverage: Decimal,
        scaling_factor: Decimal,
        market_condition: str = "normal",
    ) -> Tuple[Decimal, str]:
        """
        Adjust leverage based on scaling and market conditions.

        Args:
            base_leverage: Base portfolio leverage
            scaling_factor: Risk scaling factor
            market_condition: "bull", "normal", "bear"

        Returns:
            (adjusted_leverage, rationale)
        """
        adjusted_leverage = base_leverage * scaling_factor

        # Apply market condition adjustments
        if market_condition == "bear":
            # Reduce leverage in bear markets
            adjusted_leverage = adjusted_leverage * Decimal("0.8")
            condition_reason = "Bear market: 20% leverage reduction"
        elif market_condition == "bull":
            # Slightly increase leverage in bull markets
            adjusted_leverage = adjusted_leverage * Decimal("1.1")
            condition_reason = "Bull market: 10% leverage increase"
        else:
            condition_reason = "Normal market: No condition adjustment"

        # Enforce hard ceiling
        adjusted_leverage = min(adjusted_leverage, self.default_max_leverage)

        # Enforce hard floor
        adjusted_leverage = max(adjusted_leverage, Decimal("1.0"))

        rationale = f"Base: {base_leverage:.2f}x × Scaling: {scaling_factor:.2f}x = {adjusted_leverage:.2f}x. {condition_reason}"

        logger.info(f"✅ Leverage adjusted: {base_leverage:.2f}x → {adjusted_leverage:.2f}x")
        return adjusted_leverage, rationale

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_position_within_limits(
        self,
        module_name: str,
        proposed_position: Decimal,
        adjusted_limits: List[AdjustedLimit],
    ) -> Tuple[bool, str]:
        """
        Validate if proposed position is within adjusted limits.

        Args:
            module_name: Strategy module name
            proposed_position: Proposed position size
            adjusted_limits: Adjusted limits

        Returns:
            (is_valid, message)
        """
        # Find the limit for this module
        limit = None
        for adj_limit in adjusted_limits:
            if adj_limit.module_name == module_name:
                limit = adj_limit
                break

        if not limit:
            return False, f"No limit found for {module_name}"

        if proposed_position <= limit.adjusted_limit:
            pct_used = (proposed_position / limit.adjusted_limit) * Decimal("100")
            return True, f"✅ Position valid: {pct_used:.1f}% of limit"
        else:
            excess = proposed_position - limit.adjusted_limit
            return False, f"❌ Position exceeds limit by €{excess:,.0f}"

    def validate_leverage_within_limits(
        self,
        current_leverage: Decimal,
        max_leverage: Optional[Decimal] = None,
    ) -> Tuple[bool, str]:
        """
        Validate if current leverage is within limits.

        Args:
            current_leverage: Current portfolio leverage
            max_leverage: Max allowed leverage (uses default if not provided)

        Returns:
            (is_valid, message)
        """
        max_lev = max_leverage or self.default_max_leverage

        if current_leverage <= max_lev:
            pct_used = (current_leverage / max_lev) * Decimal("100")
            return True, f"✅ Leverage valid: {pct_used:.1f}% of limit"
        else:
            excess = current_leverage - max_lev
            return False, f"❌ Leverage exceeds limit by {excess:.2f}x"

    # ========================================================================
    # Enforcement
    # ========================================================================

    def enforce_hard_stops(
        self,
        breaches: List[LimitBreach],
        critical_action: str = "reduce",
    ) -> Tuple[bool, Dict]:
        """
        Enforce hard stops on critical breaches.

        Args:
            breaches: List of detected breaches
            critical_action: "reduce", "freeze", or "halt"

        Returns:
            (should_continue, action_details)
        """
        critical_breaches = [b for b in breaches if b.severity == "critical"]

        if not critical_breaches:
            return True, {"action": "none", "message": "No critical breaches"}

        if critical_action == "halt":
            return False, {
                "action": "halt",
                "message": f"⚠️ HALT: {len(critical_breaches)} critical breaches detected",
                "breaches": [
                    {
                        "module": b.module_name,
                        "excess": float(b.excess),
                        "recommendation": b.recommendation,
                    }
                    for b in critical_breaches
                ],
            }

        if critical_action == "reduce":
            reductions = {}
            for breach in critical_breaches:
                # Reduce to 80% of limit
                reduction_target = breach.adjusted_limit * Decimal("0.8")
                reduction_amount = breach.current_position - reduction_target
                reductions[breach.module_name] = {
                    "target_position": float(reduction_target),
                    "reduce_by": float(reduction_amount),
                    "percentage": float(
                        (reduction_amount / breach.current_position) * Decimal("100")
                    ),
                }

            return True, {
                "action": "reduce",
                "message": f"⚠️ REDUCE: {len(critical_breaches)} positions require reduction",
                "reductions": reductions,
            }

        # freeze action
        return True, {
            "action": "freeze",
            "message": f"⚠️ FREEZE: {len(critical_breaches)} positions frozen pending review",
            "frozen_modules": [b.module_name for b in critical_breaches],
        }

    # ========================================================================
    # Configuration
    # ========================================================================

    def set_position_limit(self, limit: Decimal) -> None:
        """Set default position limit."""
        self.default_position_limit = limit
        logger.info(f"✅ Position limit set to €{limit:,.0f}")

    def set_max_leverage(self, leverage: Decimal) -> None:
        """Set default max leverage."""
        self.default_max_leverage = leverage
        logger.info(f"✅ Max leverage set to {leverage:.2f}x")

    def set_max_allocation(self, allocation_pct: Decimal) -> None:
        """Set default max allocation percentage."""
        self.default_max_allocation = allocation_pct
        logger.info(f"✅ Max allocation set to {allocation_pct:.1f}%")


# Singleton instance
_adjuster: Optional[LimitAdjuster] = None


def get_limit_adjuster() -> LimitAdjuster:
    """Get or create singleton LimitAdjuster."""
    global _adjuster
    if _adjuster is None:
        _adjuster = LimitAdjuster()

    return _adjuster
