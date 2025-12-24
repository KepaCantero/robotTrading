"""
T8.1: RiskScalingApplication - Conditional risk scaling for portfolios

Applies dynamic risk scaling based on market conditions and portfolio metrics.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskAdjustedAllocation:
    """Portfolio allocation with risk scaling applied."""
    original_allocation: Dict[str, float]
    adjusted_allocation: Dict[str, float]
    risk_scale_factor: float
    scaling_reason: str
    market_volatility: float
    portfolio_volatility: float
    is_scaled: bool


class RiskScalingApplicator:
    """
    T8.1: Applies risk scaling to portfolio allocation.

    Scales portfolio risk based on:
    - Market volatility conditions
    - Portfolio volatility
    - Risk tolerance
    - Historical VIX levels
    """

    def __init__(self):
        """Initialize RiskScalingApplicator."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("✅ RiskScalingApplicator initialized")

    async def apply_risk_scaling(
        self,
        allocation: Dict[str, float],
        portfolio_volatility: float,
        market_volatility: float,
        risk_tolerance: float = 1.0,
        max_scaling: float = 2.0,
        min_scaling: float = 0.5,
    ) -> RiskAdjustedAllocation:
        """
        Apply conditional risk scaling to portfolio.

        Args:
            allocation: Original portfolio allocation
            portfolio_volatility: Portfolio volatility (e.g., 0.15 = 15%)
            market_volatility: Market volatility/VIX level (e.g., 0.20 = 20%)
            risk_tolerance: Risk tolerance factor (1.0 = neutral)
            max_scaling: Maximum scaling factor (2.0 = 2x leverage)
            min_scaling: Minimum scaling factor (0.5 = 50% reduction)

        Returns:
            RiskAdjustedAllocation with scaled weights
        """
        try:
            # Calculate risk scaling factor based on volatility conditions
            scale_factor = await self._calculate_scale_factor(
                portfolio_volatility, market_volatility, risk_tolerance,
                max_scaling, min_scaling
            )

            # Determine scaling reason
            reason = await self._determine_scaling_reason(
                scale_factor, portfolio_volatility, market_volatility
            )

            # Apply scaling to allocation
            adjusted_allocation = {
                asset: weight * scale_factor for asset, weight in allocation.items()
            }

            # Renormalize to sum to 1.0
            total = sum(adjusted_allocation.values())
            if total > 0:
                adjusted_allocation = {
                    asset: weight / total for asset, weight in adjusted_allocation.items()
                }

            self.logger.info(
                f"📊 Risk scaling applied: factor={scale_factor:.2f}, reason: {reason}"
            )

            return RiskAdjustedAllocation(
                original_allocation=allocation,
                adjusted_allocation=adjusted_allocation,
                risk_scale_factor=scale_factor,
                scaling_reason=reason,
                market_volatility=market_volatility,
                portfolio_volatility=portfolio_volatility,
                is_scaled=(abs(scale_factor - 1.0) > 0.01)
            )

        except Exception as e:
            self.logger.error(f"❌ Error applying risk scaling: {e}")
            return RiskAdjustedAllocation(
                original_allocation=allocation,
                adjusted_allocation=allocation,
                risk_scale_factor=1.0,
                scaling_reason=f"Error: {str(e)}",
                market_volatility=market_volatility,
                portfolio_volatility=portfolio_volatility,
                is_scaled=False
            )

    async def _calculate_scale_factor(
        self,
        portfolio_vol: float,
        market_vol: float,
        risk_tolerance: float,
        max_scaling: float,
        min_scaling: float,
    ) -> float:
        """
        Calculate risk scaling factor.

        Logic:
        - If market_vol is high → reduce risk (scale < 1.0)
        - If market_vol is low → increase risk (scale > 1.0)
        - Scale factor = risk_tolerance * (base_vol / market_vol)
        """
        base_volatility = 0.15  # 15% is "normal" volatility

        # Volatility ratio determines scaling direction
        vol_ratio = base_volatility / max(market_vol, 0.01)

        # Apply risk tolerance
        scale_factor = risk_tolerance * vol_ratio

        # Clamp to min/max bounds
        scale_factor = max(min_scaling, min(max_scaling, scale_factor))

        return scale_factor

    async def _determine_scaling_reason(
        self, scale_factor: float, portfolio_vol: float, market_vol: float
    ) -> str:
        """Determine reason for scaling decision."""
        if abs(scale_factor - 1.0) < 0.01:
            return "No scaling: Normal market conditions"
        elif scale_factor > 1.0:
            return f"Increase risk: Low market volatility ({market_vol:.1%})"
        else:
            return f"Reduce risk: High market volatility ({market_vol:.1%})"

    def adjust_position_sizes(
        self,
        allocation: Dict[str, float],
        total_portfolio_value: float,
        scale_factor: float,
    ) -> Dict[str, float]:
        """
        Adjust position sizes based on risk scaling.

        Returns position sizes in currency terms.
        """
        return {
            asset: (weight * scale_factor) * total_portfolio_value
            for asset, weight in allocation.items()
        }

    def should_rebalance(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        rebalance_threshold: float = 0.05,
    ) -> bool:
        """
        Determine if portfolio should be rebalanced.

        Args:
            current_allocation: Current portfolio weights
            target_allocation: Target portfolio weights
            rebalance_threshold: Max deviation before rebalancing (default 5%)

        Returns:
            True if any asset drifts more than threshold
        """
        for asset in target_allocation:
            current_weight = current_allocation.get(asset, 0.0)
            target_weight = target_allocation.get(asset, 0.0)
            deviation = abs(current_weight - target_weight)
            if deviation > rebalance_threshold:
                return True
        return False
