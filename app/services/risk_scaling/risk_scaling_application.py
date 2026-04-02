"""
T8.1.3: RiskScalingApplication - Orchestrate risk scaling end-to-end

Integrates RiskAdjustmentCalculator and LimitAdjuster to provide
comprehensive risk management for the trading pipeline.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from app.services.risk_scaling.limit_adjuster import get_limit_adjuster
from app.services.risk_scaling.risk_adjustment_calculator import get_risk_adjustment_calculator

logger = logging.getLogger(__name__)


class RiskScalingApplication:
    """
    T8.1.3: Applies dynamic risk scaling to portfolio allocations and orders.

    Orchestrates:
    1. RiskAdjustmentCalculator: Position sizing based on feasibility
    2. LimitAdjuster: Trading limits based on market conditions

    Provides risk-adjusted portfolio to DeployDecisionOrchestrator.
    """

    def __init__(self):
        """Initialize risk scaling application."""
        self.calculator = get_risk_adjustment_calculator()
        self.adjuster = get_limit_adjuster()
        logger.info("✅ RiskScalingApplication initialized")

    async def apply_risk_scaling(
        self,
        base_position_size: Decimal,
        feasibility_ratio: Decimal,
        capital: Decimal,
        capital_tier: str,
        risk_tolerance: int,
        current_volatility: Decimal,
        average_volatility: Decimal,
        current_drawdown_pct: Decimal,
        market_volatility_state: str = "normal",
    ) -> dict:
        """
        Apply comprehensive risk scaling to a position.

        Args:
            base_position_size: Original position size (€)
            feasibility_ratio: Strategy viability (≥1.0 is good)
            capital: Total account capital (€)
            capital_tier: micro/small/medium/large
            risk_tolerance: 1-7 (user risk profile)
            current_volatility: Current market volatility (ATR)
            average_volatility: Historical average volatility
            current_drawdown_pct: Portfolio current drawdown (0-1)
            market_volatility_state: normal/stressed/volatile

        Returns:
            Dict with adjusted position, limits, and reasoning
        """
        try:
            # Step 1: Calculate position scaling based on feasibility
            scaled_position, pos_reason = self.calculator.calculate_position_scaling(
                feasibility_ratio=feasibility_ratio,
                base_position_size=base_position_size,
                capital_tier=capital_tier,
                risk_tolerance=risk_tolerance,
            )

            # Step 2: Calculate leverage adjustment
            leverage, lev_reason = self.calculator.calculate_leverage_adjustment(
                feasibility_ratio=feasibility_ratio,
                capital_tier=capital_tier,
                market_volatility=market_volatility_state,
                risk_tolerance=risk_tolerance,
            )

            # Step 3: Get comprehensive limits
            limits = self.adjuster.get_comprehensive_limits(
                capital_tier=capital_tier,
                capital=capital,
                current_volatility=current_volatility,
                average_volatility=average_volatility,
                current_drawdown_pct=current_drawdown_pct,
            )

            # Step 4: Validate position against limits
            max_allowed_position = limits["max_position_eur"]
            final_position = min(scaled_position, max_allowed_position)

            # Step 5: Check if position should be halted
            is_halted = current_drawdown_pct > Decimal("0.20") or limits[
                "max_position_eur"
            ] == Decimal("0")

            result = {
                "base_position_size": base_position_size,
                "scaled_position_size": scaled_position,
                "final_position_size": final_position,
                "position_capped": final_position < scaled_position,
                "position_reason": pos_reason,
                "leverage": leverage,
                "leverage_reason": lev_reason,
                "limits": limits,
                "capital_at_risk": final_position * leverage,
                "pct_capital_at_risk": (
                    (final_position * leverage / capital) if capital > 0 else Decimal("0")
                ),
                "is_halted": is_halted,
                "halt_reason": "Excessive drawdown" if is_halted else None,
            }

            logger.info(
                "Risk scaling applied: "
                f"€{base_position_size:,.0f} → €{final_position:,.0f} "
                f"(feasibility {feasibility_ratio:.2f})"
            )

            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Error applying risk scaling: {e}")
            raise

    async def validate_order_against_limits(
        self,
        order_size: Decimal,
        account_limits: dict,
        current_capital_deployed: Decimal,
        capital: Decimal,
    ) -> tuple:
        """
        Check if an order complies with current limits.

        Args:
            order_size: Proposed order size (€)
            account_limits: Dict with max_position_eur, max_leverage, etc.
            current_capital_deployed: Current total deployed capital
            capital: Total account capital

        Returns:
            (is_valid, message)
        """
        order_size = Decimal(str(order_size))
        current_capital_deployed = Decimal(str(current_capital_deployed))
        capital = Decimal(str(capital))

        # Check position size limit
        if order_size > account_limits["max_position_eur"]:
            return False, (
                f"Order size €{order_size:,.0f} exceeds limit "
                f"€{account_limits['max_position_eur']:,.0f}"
            )

        # Check leverage limit
        new_leverage = (
            (current_capital_deployed + order_size) / capital
            if capital > Decimal("0")
            else Decimal("0")
        )
        if new_leverage > account_limits["max_leverage"]:
            return False, (
                f"New leverage {new_leverage:.2f}x exceeds limit "
                f"{account_limits['max_leverage']:.2f}x"
            )

        # Check daily loss limit
        # (Would need to track daily loss separately)

        logger.info(f"✅ Order €{order_size:,.0f} passes all limit checks")
        return True, "Order within limits"

    async def get_risk_status(
        self,
        capital: Decimal,
        current_capital_deployed: Decimal,
        current_drawdown_pct: Decimal,
        capital_tier: str,
    ) -> dict:
        """
        Get current risk status summary.

        Args:
            capital: Total capital (€)
            current_capital_deployed: Capital currently deployed (€)
            current_drawdown_pct: Current drawdown (0-1)
            capital_tier: Account tier

        Returns:
            Dict with risk status
        """
        capital = Decimal(str(capital))
        current_capital_deployed = Decimal(str(current_capital_deployed))
        current_drawdown_pct = Decimal(str(current_drawdown_pct))

        current_leverage = (
            (current_capital_deployed / capital) if capital > Decimal("0") else Decimal("0")
        )
        available_capital = capital - current_capital_deployed
        current_drawdown_pct * Decimal("100")

        # Determine risk state
        if current_drawdown_pct < Decimal("0.05"):
            risk_state = "HEALTHY"
        elif current_drawdown_pct < Decimal("0.10"):
            risk_state = "CAUTION"
        elif current_drawdown_pct < Decimal("0.15"):
            risk_state = "WARNING"
        elif current_drawdown_pct < Decimal("0.20"):
            risk_state = "CRITICAL"
        else:
            risk_state = "HALT"

        return {
            "capital_total": capital,
            "capital_deployed": current_capital_deployed,
            "capital_available": available_capital,
            "current_leverage": current_leverage,
            "current_drawdown_pct": current_drawdown_pct,
            "risk_state": risk_state,
            "can_trade": risk_state in ["HEALTHY", "CAUTION"],
            "should_reduce_positions": risk_state in ["WARNING", "CRITICAL"],
            "should_halt": risk_state == "HALT",
        }


# Singleton
_application: RiskScalingApplication | None = None


def get_risk_scaling_application() -> RiskScalingApplication:
    """Get or create singleton RiskScalingApplication."""
    global _application
    if _application is None:
        _application = RiskScalingApplication()

    return _application
