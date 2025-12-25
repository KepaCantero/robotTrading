"""
T8.1: RiskScalingApplication - Conditional risk scaling

Applies risk scaling based on:
1. Market regime (bull/sideways/bear)
2. Volatility level (low/normal/high)
3. Current drawdown vs max acceptable drawdown

Risk scaling rules:
- Bear market: Reduce allocation to high-volatility modules
- High volatility: Decrease position sizes
- High drawdown: More conservative positioning

Fallback: If PHASE 3 not available, returns base portfolio unchanged.
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional

from app.services.portfolio_constructor import AllocationWeight, PortfolioAllocation
from .models import (
    RiskScalingRequest,
    RiskAdjustedPortfolio,
    AdjustedAllocationWeight,
)

logger = logging.getLogger(__name__)


class RiskScalingApplication:
    """
    Applies conditional risk scaling to portfolios.

    Adjusts module allocations based on market conditions:
    - Market regime (bull → aggressive, bear → defensive)
    - Volatility level (high → reduce positions)
    - Current drawdown (approaching limit → scale down)
    """

    # Market regime adjustment factors
    # Affects allocation to high-volatility modules
    REGIME_ADJUSTMENT_FACTORS = {
        "bull": {
            "high_volatility_weight_adjust": Decimal("1.2"),  # Increase aggressive modules
            "low_volatility_weight_adjust": Decimal("0.9"),
            "target_allocation_shift": Decimal("0.1"),  # Shift 10% to high-volatility
        },
        "sideways": {
            "high_volatility_weight_adjust": Decimal("1.0"),  # No change
            "low_volatility_weight_adjust": Decimal("1.0"),
            "target_allocation_shift": Decimal("0.0"),
        },
        "bear": {
            "high_volatility_weight_adjust": Decimal("0.7"),  # Reduce aggressive modules
            "low_volatility_weight_adjust": Decimal("1.3"),  # Increase defensive
            "target_allocation_shift": Decimal("-0.15"),  # Shift 15% to low-volatility
        },
    }

    # Volatility adjustment factors
    # Affects overall portfolio leverage
    VOLATILITY_ADJUSTMENT_FACTORS = {
        "low": Decimal("1.1"),  # Can be slightly more aggressive
        "normal": Decimal("1.0"),  # No change
        "high": Decimal("0.75"),  # Significantly reduce positions
    }

    # Drawdown adjustment factors
    # Affects overall portfolio size
    def _get_drawdown_adjustment_factor(
        self,
        current_dd_pct: Decimal,
        max_dd_pct: Decimal,
    ) -> Decimal:
        """Calculate adjustment factor based on current drawdown."""
        if max_dd_pct <= Decimal("0"):
            return Decimal("1.0")

        drawdown_ratio = current_dd_pct / max_dd_pct

        if drawdown_ratio < Decimal("0.5"):
            # Below 50% of max drawdown: normal operations
            return Decimal("1.0")
        elif drawdown_ratio < Decimal("0.75"):
            # 50-75%: Slight reduction (scale to 0.9)
            return Decimal("0.95")
        elif drawdown_ratio < Decimal("0.9"):
            # 75-90%: Moderate reduction (scale to 0.7)
            return Decimal("0.8")
        else:
            # Above 90%: Significant reduction (scale to 0.5)
            return Decimal("0.6")

    # Module characteristics for classification
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
        """Initialize risk scaling application."""
        self.scaling_history: List[RiskAdjustedPortfolio] = []
        logger.info("✅ RiskScalingApplication initialized")

    async def apply_risk_scaling(
        self,
        request: RiskScalingRequest,
    ) -> RiskAdjustedPortfolio:
        """
        Apply conditional risk scaling to portfolio.

        Decision: Scale or not scale based on market conditions.
        - If PHASE 3 not available: Return base portfolio unchanged
        - If conditions favorable: Return base portfolio unchanged
        - If conditions adverse: Apply scaling adjustments

        Args:
            request: Risk scaling request with market conditions

        Returns:
            RiskAdjustedPortfolio with potentially adjusted allocations
        """
        start_time = datetime.utcnow()

        try:
            # Check if scaling should be applied
            should_scale = (
                request.phase3_enabled
                and (request.market_regime == "bear" or request.volatility_level == "high"
                     or (request.current_drawdown_pct / max(request.max_acceptable_drawdown_pct, Decimal("1"))) > Decimal("0.7"))
            )

            if not should_scale:
                logger.info(f"Risk scaling not needed for {request.profile_id}")
                result = RiskAdjustedPortfolio(
                    success=True,
                    profile_id=request.profile_id,
                    base_allocation_method=request.base_portfolio.allocation_method,
                    risk_scaling_applied=False,
                    scaling_factor=Decimal("1.0"),
                    market_regime=request.market_regime,
                    volatility_level=request.volatility_level,
                    current_drawdown_pct=request.current_drawdown_pct,
                    max_acceptable_drawdown_pct=request.max_acceptable_drawdown_pct,
                    original_allocations=request.base_portfolio.allocations,
                    adjustment_rationale="Market conditions favorable, no scaling applied",
                )
                self.scaling_history.append(result)
                return result

            # Apply risk scaling
            adjusted_allocations = await self._calculate_adjusted_allocations(
                request.base_portfolio.allocations,
                request.market_regime,
                request.volatility_level,
                request.current_drawdown_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Calculate overall scaling factor
            overall_factor = await self._calculate_overall_scaling_factor(
                request.market_regime,
                request.volatility_level,
                request.current_drawdown_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Calculate expected return adjustment
            return_adjustment = await self._calculate_return_adjustment(adjusted_allocations)

            # Build rationale
            rationale = await self._build_adjustment_rationale(
                request.market_regime,
                request.volatility_level,
                request.current_drawdown_pct,
                request.max_acceptable_drawdown_pct,
                overall_factor,
            )

            result = RiskAdjustedPortfolio(
                success=True,
                profile_id=request.profile_id,
                base_allocation_method=request.base_portfolio.allocation_method,
                risk_scaling_applied=True,
                scaling_factor=overall_factor,
                market_regime=request.market_regime,
                volatility_level=request.volatility_level,
                current_drawdown_pct=request.current_drawdown_pct,
                max_acceptable_drawdown_pct=request.max_acceptable_drawdown_pct,
                original_allocations=request.base_portfolio.allocations,
                adjusted_allocations=adjusted_allocations,
                adjustment_rationale=rationale,
                expected_return_adjustment_pct=return_adjustment,
            )

            self.scaling_history.append(result)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ Risk scaling applied for {request.profile_id}, "
                f"factor={overall_factor:.2f}, elapsed={elapsed_ms:.0f}ms"
            )
            return result

        except Exception as e:
            logger.error(f"❌ Error applying risk scaling: {e}")
            return RiskAdjustedPortfolio(
                success=False,
                profile_id=request.profile_id,
                base_allocation_method=request.base_portfolio.allocation_method,
                market_regime=request.market_regime,
                volatility_level=request.volatility_level,
                current_drawdown_pct=request.current_drawdown_pct,
                max_acceptable_drawdown_pct=request.max_acceptable_drawdown_pct,
                original_allocations=request.base_portfolio.allocations,
                error_message=str(e),
            )

    async def _calculate_adjusted_allocations(
        self,
        original_allocations: List[AllocationWeight],
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> List[AdjustedAllocationWeight]:
        """Calculate adjusted allocations based on market conditions."""
        adjusted = []

        # Get regime factors
        regime_factors = self.REGIME_ADJUSTMENT_FACTORS.get(
            market_regime, self.REGIME_ADJUSTMENT_FACTORS["sideways"]
        )

        # Get volatility factor
        volatility_factor = self.VOLATILITY_ADJUSTMENT_FACTORS.get(
            volatility_level, Decimal("1.0")
        )

        # Get drawdown factor
        drawdown_factor = self._get_drawdown_adjustment_factor(
            current_drawdown_pct, max_drawdown_pct
        )

        # Classify modules and adjust
        regime_shift_amount = regime_factors["target_allocation_shift"]

        for allocation in original_allocations:
            # Get module volatility class
            vol_class = self.MODULE_VOLATILITY_CLASS.get(allocation.module_name, "medium")

            # Determine regime adjustment
            if vol_class in ["very_high", "high"]:
                regime_adj = regime_factors["high_volatility_weight_adjust"]
                # Apply regime shift for high-volatility modules
                if regime_shift_amount < Decimal("0"):
                    # Bear market: reduce high-volatility modules
                    regime_adj = regime_adj * (Decimal("1") + regime_shift_amount)
            else:
                regime_adj = regime_factors["low_volatility_weight_adjust"]
                # Apply regime shift for low-volatility modules
                if regime_shift_amount > Decimal("0"):
                    # Bull market: increase low-volatility modules slightly
                    regime_adj = regime_adj * (Decimal("1") + regime_shift_amount)

            # Combine all factors
            total_adjustment = regime_adj * volatility_factor * drawdown_factor

            adjusted_weight = allocation.weight_pct * total_adjustment

            # Ensure weight stays within bounds
            adjusted_weight = max(Decimal("0"), min(Decimal("100"), adjusted_weight))

            adjusted.append(
                AdjustedAllocationWeight(
                    module_name=allocation.module_name,
                    original_weight_pct=allocation.weight_pct,
                    adjusted_weight_pct=adjusted_weight,
                    adjustment_factor=total_adjustment,
                    rationale=f"Regime:{market_regime}(×{regime_adj:.2f}) "
                    f"Volatility:{volatility_level}(×{volatility_factor:.2f}) "
                    f"Drawdown:{current_drawdown_pct:.1f}%/{max_drawdown_pct:.1f}%(×{drawdown_factor:.2f})",
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

        return adjusted

    async def _calculate_overall_scaling_factor(
        self,
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> Decimal:
        """Calculate overall portfolio scaling factor."""
        volatility_factor = self.VOLATILITY_ADJUSTMENT_FACTORS.get(
            volatility_level, Decimal("1.0")
        )

        drawdown_factor = self._get_drawdown_adjustment_factor(
            current_drawdown_pct, max_drawdown_pct
        )

        # Regime affects scaling indirectly through weight allocation
        regime_factor = Decimal("1.0")
        if market_regime == "bear":
            regime_factor = Decimal("0.9")  # Slight overall reduction in bear market
        elif market_regime == "bull":
            regime_factor = Decimal("1.05")  # Slight increase in bull market

        overall = regime_factor * volatility_factor * drawdown_factor
        return overall

    async def _calculate_return_adjustment(
        self,
        adjusted_allocations: List[AdjustedAllocationWeight],
    ) -> Decimal:
        """Calculate expected return impact from adjustments."""
        total_adjustment = Decimal("0")

        for adj in adjusted_allocations:
            weight_change = adj.adjusted_weight_pct - adj.original_weight_pct
            adjustment = weight_change / max(adj.original_weight_pct, Decimal("0.1"))
            total_adjustment += adjustment

        # Average adjustment as percentage of portfolio
        avg_adjustment = total_adjustment / max(len(adjusted_allocations), 1)

        # Return impact is roughly 60% of weight adjustment
        return avg_adjustment * Decimal("0.6")

    async def _build_adjustment_rationale(
        self,
        market_regime: str,
        volatility_level: str,
        current_drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
        scaling_factor: Decimal,
    ) -> str:
        """Build human-readable adjustment rationale."""
        reasons = []

        if market_regime == "bear":
            reasons.append("Bear market: Reduced allocation to high-volatility modules")
        elif market_regime == "bull":
            reasons.append("Bull market: Increased allocation to growth-oriented modules")

        if volatility_level == "high":
            reasons.append("High volatility detected: Reduced position sizes across board")

        drawdown_ratio = current_drawdown_pct / max(max_drawdown_pct, Decimal("1"))
        if drawdown_ratio > Decimal("0.9"):
            reasons.append(f"Drawdown at {drawdown_ratio * Decimal('100'):.0f}% of limit: Defensive positioning")
        elif drawdown_ratio > Decimal("0.7"):
            reasons.append(f"Drawdown approaching limit ({drawdown_ratio * Decimal('100'):.0f}%): Cautious stance")

        rationale = "; ".join(reasons) if reasons else "Risk conditions stable"
        rationale += f". Overall scaling factor: {scaling_factor:.2f}x"

        return rationale

    async def get_scaling_history(
        self,
        limit: Optional[int] = None,
    ) -> List[RiskAdjustedPortfolio]:
        """Get scaling history."""
        results = self.scaling_history
        if limit:
            results = results[-limit:]
        return results

    def get_scaler_status(self) -> Dict:
        """Get scaler operational status."""
        successful = sum(1 for s in self.scaling_history if s.success)
        applied_count = sum(1 for s in self.scaling_history if s.risk_scaling_applied)
        total = len(self.scaling_history)

        avg_scaling_factor = Decimal("1.0")
        if applied_count > 0:
            factors = [
                s.scaling_factor for s in self.scaling_history if s.risk_scaling_applied and s.success
            ]
            if factors:
                avg_scaling_factor = sum(factors) / len(factors)

        return {
            "total_scalings": total,
            "successful_scalings": successful,
            "scaling_applied_count": applied_count,
            "success_rate": successful / max(1, total),
            "average_scaling_factor": float(avg_scaling_factor),
            "history_size": total,
        }


# Singleton
_scaler: Optional[RiskScalingApplication] = None


def get_risk_scaler() -> RiskScalingApplication:
    """Get or create singleton RiskScalingApplication."""
    global _scaler
    if _scaler is None:
        _scaler = RiskScalingApplication()
    return _scaler
