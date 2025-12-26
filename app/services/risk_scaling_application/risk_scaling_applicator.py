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

Architecture:
- RiskScalingApplication: Main orchestrator (delegator pattern)
- RiskAdjustmentCalculator: Calculation logic (extracted component)
- Singleton pattern for dependency injection
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
from .risk_adjustment_calculator import RiskAdjustmentCalculator, get_risk_adjustment_calculator

logger = logging.getLogger(__name__)


class RiskScalingApplication:
    """
    Applies conditional risk scaling to portfolios.

    Adjusts module allocations based on market conditions:
    - Market regime (bull → aggressive, bear → defensive)
    - Volatility level (high → reduce positions)
    - Current drawdown (approaching limit → scale down)

    Architecture:
    - Delegates calculation logic to RiskAdjustmentCalculator
    - Maintains scaling history and state
    - Orchestrates end-to-end scaling workflow
    """

    def __init__(self, calculator: Optional[RiskAdjustmentCalculator] = None):
        """
        Initialize risk scaling application.

        Args:
            calculator: RiskAdjustmentCalculator instance (optional for dependency injection)
        """
        self.calculator = calculator or get_risk_adjustment_calculator()
        self.scaling_history: List[RiskAdjustedPortfolio] = []
        logger.info("✅ RiskScalingApplication initialized with RiskAdjustmentCalculator")

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

            # Apply risk scaling (delegate to calculator)
            adjusted_allocations = self.calculator.calculate_adjusted_allocations(
                request.base_portfolio.allocations,
                request.market_regime,
                request.volatility_level,
                request.current_drawdown_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Calculate overall scaling factor
            overall_factor = self.calculator.calculate_overall_scaling_factor(
                request.market_regime,
                request.volatility_level,
                request.current_drawdown_pct,
                request.max_acceptable_drawdown_pct,
            )

            # Calculate expected return adjustment
            return_adjustment = self.calculator.calculate_return_adjustment(adjusted_allocations)

            # Build rationale
            rationale = self.calculator.build_adjustment_rationale(
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
