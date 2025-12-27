"""
T8.1 RiskAdjustmentCalculator - Risk adjustment calculations

Extracted from RiskScalingApplication to provide calculation logic.

Responsibilities:
- Calculate individual adjustment factors (regime, volatility, drawdown)
- Compute adjusted allocations
- Calculate scaling factors
- Estimate return impacts
"""

import logging
from decimal import Decimal
from typing import List, Tuple

from app.services.portfolio_constructor import AllocationWeight

from .models import AdjustedAllocationWeight

logger = logging.getLogger(__name__)


class RiskAdjustmentCalculator:
    """
    Calculates risk adjustments for portfolio allocations.

    Provides methods for computing adjustment factors based on:
    - Market regime (bull/sideways/bear)
    - Volatility levels (low/normal/high)
    - Current drawdown vs. maximum acceptable
    """

    # Market regime adjustment factors
    REGIME_ADJUSTMENT_FACTORS = {
        "bull": {
            "high_volatility_weight_adjust": Decimal("1.2"),
            "low_volatility_weight_adjust": Decimal("0.9"),
            "target_allocation_shift": Decimal("0.1"),
        },
        "sideways": {
            "high_volatility_weight_adjust": Decimal("1.0"),
            "low_volatility_weight_adjust": Decimal("1.0"),
            "target_allocation_shift": Decimal("0.0"),
        },
        "bear": {
            "high_volatility_weight_adjust": Decimal("0.7"),
            "low_volatility_weight_adjust": Decimal("1.3"),
            "target_allocation_shift": Decimal("-0.15"),
        },
    }

    # Volatility adjustment factors
    VOLATILITY_ADJUSTMENT_FACTORS = {
        "low": Decimal("1.1"),
        "normal": Decimal("1.0"),
        "high": Decimal("0.75"),
    }

    # Module volatility classification
    MODULE_VOLATILITY_CLASS = {
        "momentum": "high",
        "machine_learning_basic": "high",
        "transformer_engine": "very_high",
        "deep_learning_engine": "very_high",
        "reinforcement_learning": "very_high",
        "mean_reversion": "low",
        "pairs_trading": "very_low",
        "ensemble_strategy": "medium",
    }

    def __init__(self):
        """Initialize risk adjustment calculator."""
        logger.info("✅ RiskAdjustmentCalculator initialized")

    # ========================================================================
    # Individual Factor Calculations
    # ========================================================================

    def calculate_regime_adjustment(self, market_regime: str) -> Decimal:
        """
        Calculate regime adjustment factor.

        Args:
            market_regime: "bull", "sideways", or "bear"

        Returns:
            Regime adjustment factor for overall portfolio
        """
        regime_factor = Decimal("1.0")
        if market_regime == "bear":
            regime_factor = Decimal("0.9")
        elif market_regime == "bull":
            regime_factor = Decimal("1.05")

        logger.debug(f"Regime adjustment ({market_regime}): {regime_factor:.2f}x")
        return regime_factor

    def calculate_volatility_adjustment(self, volatility_level: str) -> Decimal:
        """
        Calculate volatility adjustment factor.

        Args:
            volatility_level: "low", "normal", or "high"

        Returns:
            Volatility adjustment factor
        """
        factor = self.VOLATILITY_ADJUSTMENT_FACTORS.get(volatility_level, Decimal("1.0"))
        logger.debug(f"Volatility adjustment ({volatility_level}): {factor:.2f}x")
        return factor

    def calculate_drawdown_adjustment(
        self,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> Decimal:
        """
        Calculate drawdown adjustment factor.

        Reduces portfolio size as drawdown approaches maximum acceptable level.

        Args:
            current_drawdown_pct: Current portfolio drawdown percentage
            max_drawdown_pct: Maximum acceptable drawdown percentage

        Returns:
            Drawdown adjustment factor (1.0 = no adjustment, <1.0 = reduction)
        """
        if max_drawdown_pct <= Decimal("0"):
            return Decimal("1.0")

        drawdown_ratio = current_drawdown_pct / max_drawdown_pct

        if drawdown_ratio < Decimal("0.5"):
            return Decimal("1.0")
        elif drawdown_ratio < Decimal("0.75"):
            return Decimal("0.95")
        elif drawdown_ratio < Decimal("0.9"):
            return Decimal("0.8")
        else:
            return Decimal("0.6")

    # ========================================================================
    # Combined Adjustment Calculations
    # ========================================================================

    def calculate_allocation_adjustment(
        self,
        module_name: str,
        original_weight_pct: Decimal,
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate adjusted weight for a single allocation.

        Args:
            module_name: Strategy module name
            original_weight_pct: Original allocation weight
            market_regime: Market regime
            volatility_level: Volatility level
            current_drawdown_pct: Current drawdown
            max_drawdown_pct: Max drawdown

        Returns:
            (adjusted_weight_pct, adjustment_factor, regime_adj, vol_adj)
        """
        regime_factors = self.REGIME_ADJUSTMENT_FACTORS.get(
            market_regime, self.REGIME_ADJUSTMENT_FACTORS["sideways"]
        )
        vol_factor = self.calculate_volatility_adjustment(volatility_level)
        dd_factor = self.calculate_drawdown_adjustment(current_drawdown_pct, max_drawdown_pct)

        # Get module volatility class
        vol_class = self.MODULE_VOLATILITY_CLASS.get(module_name, "medium")

        # Determine regime adjustment
        regime_shift_amount = regime_factors["target_allocation_shift"]
        if vol_class in ["very_high", "high"]:
            regime_adj = regime_factors["high_volatility_weight_adjust"]
            if regime_shift_amount < Decimal("0"):
                regime_adj = regime_adj * (Decimal("1") + regime_shift_amount)
        else:
            regime_adj = regime_factors["low_volatility_weight_adjust"]
            if regime_shift_amount > Decimal("0"):
                regime_adj = regime_adj * (Decimal("1") + regime_shift_amount)

        # Combine factors
        total_adjustment = regime_adj * vol_factor * dd_factor
        adjusted_weight = original_weight_pct * total_adjustment

        # Ensure bounds
        adjusted_weight = max(Decimal("0"), min(Decimal("100"), adjusted_weight))

        return adjusted_weight, total_adjustment, regime_adj, vol_factor

    def calculate_adjusted_allocations(
        self,
        original_allocations: List[AllocationWeight],
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> List[AdjustedAllocationWeight]:
        """
        Calculate adjusted allocations for all modules.

        Args:
            original_allocations: Original allocation weights
            market_regime: Market regime
            volatility_level: Volatility level
            current_drawdown_pct: Current drawdown
            max_drawdown_pct: Max drawdown

        Returns:
            List of adjusted allocation weights
        """
        adjusted = []
        dd_factor = self.calculate_drawdown_adjustment(current_drawdown_pct, max_drawdown_pct)

        for allocation in original_allocations:
            adj_weight, total_adj, regime_adj, vol_factor = self.calculate_allocation_adjustment(
                module_name=allocation.module_name,
                original_weight_pct=allocation.weight_pct,
                market_regime=market_regime,
                volatility_level=volatility_level,
                current_drawdown_pct=current_drawdown_pct,
                max_drawdown_pct=max_drawdown_pct,
            )

            adjusted.append(
                AdjustedAllocationWeight(
                    module_name=allocation.module_name,
                    original_weight_pct=allocation.weight_pct,
                    adjusted_weight_pct=adj_weight,
                    adjustment_factor=total_adj,
                    rationale=f"Regime:{market_regime}(×{regime_adj:.2f}) "
                    f"Vol:{volatility_level}(×{vol_factor:.2f}) "
                    f"DD:{current_drawdown_pct:.1f}%/{max_drawdown_pct:.1f}%(×{dd_factor:.2f})",
                )
            )

        # Normalize weights to sum to 100%
        total_weight = sum(a.adjusted_weight_pct for a in adjusted)
        if total_weight > Decimal("0"):
            adjusted = [
                AdjustedAllocationWeight(
                    module_name=a.module_name,
                    original_weight_pct=a.original_weight_pct,
                    adjusted_weight_pct=(a.adjusted_weight_pct / total_weight) * Decimal("100"),
                    adjustment_factor=a.adjustment_factor,
                    rationale=a.rationale,
                )
                for a in adjusted
            ]

        logger.info(f"✅ Calculated adjusted allocations for {len(adjusted)} modules")
        return adjusted

    def calculate_overall_scaling_factor(
        self,
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> Decimal:
        """
        Calculate overall portfolio scaling factor.

        Args:
            market_regime: Market regime
            volatility_level: Volatility level
            current_drawdown_pct: Current drawdown
            max_drawdown_pct: Max drawdown

        Returns:
            Overall scaling factor
        """
        regime_factor = self.calculate_regime_adjustment(market_regime)
        vol_factor = self.calculate_volatility_adjustment(volatility_level)
        dd_factor = self.calculate_drawdown_adjustment(current_drawdown_pct, max_drawdown_pct)

        overall = regime_factor * vol_factor * dd_factor
        logger.debug(f"Overall scaling factor: {overall:.2f}x")
        return overall

    def calculate_loss_streak_adjustment(self, consecutive_losses: int) -> Decimal:
        """
        Calculate adjustment factor based on consecutive losses.

        Args:
            consecutive_losses: Number of consecutive losing periods

        Returns:
            Adjustment factor (reduces positions as losses increase)
        """
        if consecutive_losses <= 0:
            return Decimal("1.0")
        elif consecutive_losses == 1:
            return Decimal("0.95")
        elif consecutive_losses == 2:
            return Decimal("0.85")
        elif consecutive_losses == 3:
            return Decimal("0.7")
        else:
            return Decimal("0.5")

    # ========================================================================
    # Impact Calculations
    # ========================================================================

    def calculate_return_adjustment(
        self,
        adjusted_allocations: List[AdjustedAllocationWeight],
    ) -> Decimal:
        """
        Calculate expected return impact from adjustments.

        Args:
            adjusted_allocations: Adjusted allocation weights

        Returns:
            Return adjustment percentage
        """
        total_adjustment = Decimal("0")

        for adj in adjusted_allocations:
            weight_change = adj.adjusted_weight_pct - adj.original_weight_pct
            adjustment = weight_change / max(adj.original_weight_pct, Decimal("0.1"))
            total_adjustment += adjustment

        # Average adjustment as percentage of portfolio
        avg_adjustment = total_adjustment / max(len(adjusted_allocations), 1)

        # Return impact is roughly 60% of weight adjustment
        return_impact = avg_adjustment * Decimal("0.6")
        logger.debug(f"Return adjustment: {return_impact:.2%}")
        return return_impact

    # ========================================================================
    # Rationale Building
    # ========================================================================

    def build_adjustment_rationale(
        self,
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
        scaling_factor: Decimal,
    ) -> str:
        """
        Build human-readable adjustment rationale.

        Args:
            market_regime: Market regime
            volatility_level: Volatility level
            current_drawdown_pct: Current drawdown
            max_drawdown_pct: Max drawdown
            scaling_factor: Overall scaling factor

        Returns:
            Rationale string
        """
        reasons = []

        if market_regime == "bear":
            reasons.append("Bear market: Reduced allocation to high-volatility modules")
        elif market_regime == "bull":
            reasons.append("Bull market: Increased allocation to growth-oriented modules")

        if volatility_level == "high":
            reasons.append("High volatility detected: Reduced position sizes across board")

        drawdown_ratio = current_drawdown_pct / max(max_drawdown_pct, Decimal("1"))
        if drawdown_ratio > Decimal("0.9"):
            reasons.append(
                f"Drawdown at {drawdown_ratio * Decimal('100'):.0f}% of limit: Defensive positioning"
            )
        elif drawdown_ratio > Decimal("0.7"):
            reasons.append(
                f"Drawdown approaching limit ({drawdown_ratio * Decimal('100'):.0f}%): Cautious stance"
            )

        rationale = "; ".join(reasons) if reasons else "Risk conditions stable"
        rationale += f". Overall scaling factor: {scaling_factor:.2f}x"

        return rationale


# Singleton instance
_calculator: RiskAdjustmentCalculator = None


def get_risk_adjustment_calculator() -> RiskAdjustmentCalculator:
    """Get or create singleton RiskAdjustmentCalculator."""
    global _calculator
    if _calculator is None:

    return _calculator
