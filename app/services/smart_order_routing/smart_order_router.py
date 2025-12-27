"""
T2.1 - Smart Order Router

Main orchestrator for intelligent order routing of large positions (€25k+).

Coordinates:
1. Market impact estimation (via MarketImpactEstimator)
2. Commission negotiation (via BrokerNegotiationEngine)
3. Order splitting optimization (via OrderSplittingOptimizer)
4. Execution cost monitoring (via ExecutionCostMonitor)

Returns ExecutionPlan with optimized tranches and cost budgets.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

from .broker_negotiation_engine import get_broker_negotiation_engine
from .execution_cost_monitor import get_execution_cost_monitor
from .market_impact_estimator import get_market_impact_estimator
from .models import ExecutionPlan
from .order_splitting_optimizer import get_order_splitting_optimizer

logger = logging.getLogger(__name__)


class SmartOrderRouter:
    """
    Intelligent order router for large positions (€25k+).

    Minimizes execution costs through:
    - Market impact estimation
    - Commission negotiation based on volume
    - Optimal order splitting (VWAP, TWAP, POI)
    - Real-time cost monitoring

    Workflow:
    1. Estimate market impact for this order size
    2. Negotiate commission rate based on volume and asset class
    3. Split order optimally to minimize cumulative market impact
    4. Create execution plan with tranches and cost budget
    5. Set up monitoring for execution
    """

    # Minimum order size for smart routing (€25k)
    MIN_ORDER_SIZE_FOR_ROUTING = Decimal("25000")

    # Cost overrun thresholds for different actions
    COST_OVERRUN_WARNING = Decimal("0.05")  # 5% over plan = warning
    COST_OVERRUN_ABORT = Decimal("0.15")  # 15% over plan = abort

    def __init__(self):
        """Initialize router with all specialist components."""
        self.market_impact_estimator = get_market_impact_estimator()
        self.broker_negotiation = get_broker_negotiation_engine()
        self.order_splitter = get_order_splitting_optimizer()
        self.cost_monitor = get_execution_cost_monitor()

        logger.info("SmartOrderRouter initialized with specialist components")

    async def route_order(
        self,
        symbol: str,
        total_size: Decimal,
        target_vwap: Optional[Decimal] = None,
        daily_volume: Optional[Decimal] = None,
        current_spread_bps: Optional[Decimal] = None,
        volatility_percentile: int = 50,
        max_execution_time_ms: int = 300_000,
        max_accepted_slippage_bps: Optional[Decimal] = None,
        asset_class: str = "equity",
        account_tier: Optional[str] = None,
        strategy: str = "vwap",
    ) -> ExecutionPlan:
        """
        Main routing logic: estimate costs, split order, create execution plan.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            total_size: Total order size in € (e.g., 50000)
            target_vwap: Target VWAP price (optional, for validation)
            daily_volume: Expected daily volume in € (required for impact estimation)
            current_spread_bps: Current bid-ask spread in basis points
            volatility_percentile: Current market volatility (0-100 percentile)
            max_execution_time_ms: Maximum time to execute all tranches (ms)
            max_accepted_slippage_bps: Maximum acceptable slippage (bps)
            asset_class: Asset class (equity, crypto, forex, commodity, bond)
            account_tier: Account tier for commission (overrides volume-based)
            strategy: Order splitting strategy (vwap, twap, poi, intraday_phased)

        Returns:
            ExecutionPlan with tranches, timing, and cost budget

        Raises:
            ValueError: If order too small, invalid parameters, or costs exceed limits
        """

        total_size = Decimal(str(total_size))
        daily_volume = Decimal(str(daily_volume or "0"))

        # Validate order size
        if total_size < self.MIN_ORDER_SIZE_FOR_ROUTING:
            raise ValueError(
                f"Order size €{total_size:,.0f} below minimum €{self.MIN_ORDER_SIZE_FOR_ROUTING:,.0f} "
                "for smart routing (use simple execution)"
            )

        logger.info(
            f"Routing {symbol}: €{total_size:,.0f} "
            f"(vol: €{daily_volume:,.0f}, vol%ile: {volatility_percentile})"
        )

        # =====================================================================
        # STEP 1: Estimate market impact
        # =====================================================================

        if daily_volume <= 0:
            raise ValueError(
                "daily_volume must be positive for market impact estimation "
                f"(got {daily_volume})"
            )

        impact_estimate = await self.market_impact_estimator.estimate(
            symbol=symbol,
            order_size=total_size,
            daily_volume=daily_volume,
            current_spread_bps=current_spread_bps,
            volatility_percentile=volatility_percentile,
            time_window_ms=max_execution_time_ms,
            asset_class=asset_class,
        )

        logger.info(
            f"{symbol}: Estimated market impact: "
            f"{impact_estimate.estimated_slippage_bps:.2f} bps "
            f"(€{impact_estimate.estimated_slippage_usd:,.2f})"
        )

        # =====================================================================
        # STEP 2: Negotiate commission rate
        # =====================================================================

        commission_rate = self.broker_negotiation.get_rate_for_volume(
            symbol=symbol,
            volume_usd=total_size,
            asset_class=asset_class,
            account_tier=account_tier,
        )

        commission_cost = total_size * commission_rate

        logger.info(
            f"{symbol}: Commission rate: {commission_rate:.4%} " f"(€{commission_cost:,.2f})"
        )

        # =====================================================================
        # STEP 3: Calculate total execution cost budget
        # =====================================================================

        # Total cost = market impact + commission
        total_slippage_cost = impact_estimate.estimated_slippage_usd
        total_cost_budget = total_slippage_cost + commission_cost
        total_cost_bps = (total_cost_budget / total_size) * Decimal("10000")

        logger.info(
            f"{symbol}: Total execution cost: "
            f"€{total_cost_budget:,.2f} ({total_cost_bps:.2f} bps)"
        )

        # =====================================================================
        # STEP 4: Validate against cost limits
        # =====================================================================

        # Default max acceptable slippage: 50 bps (0.5%)
        if max_accepted_slippage_bps is None:
            max_accepted_slippage_bps = Decimal("50")

        if total_cost_bps > max_accepted_slippage_bps:
            raise ValueError(
                f"Total execution cost {total_cost_bps:.2f} bps exceeds "
                f"limit {max_accepted_slippage_bps:.2f} bps"
            )

        # =====================================================================
        # STEP 5: Split order optimally
        # =====================================================================

        execution_plan = await self.order_splitter.optimize_execution(
            symbol=symbol,
            total_size=total_size,
            strategy=strategy,
            max_exec_time=max_execution_time_ms,
            constraints={
                "max_per_tranche": total_size * Decimal("0.25"),  # 25% per tranche
                "max_spread": Decimal("2"),  # 2 bps max spread
                "max_involvement_pct": Decimal("0.20"),  # 20% of tick volume
            },
        )

        # =====================================================================
        # STEP 6: Enrich execution plan with cost information
        # =====================================================================

        execution_plan.cost_budget = total_cost_budget
        execution_plan.estimated_avg_price = target_vwap
        execution_plan.max_execution_time_ms = max_execution_time_ms

        # Distribute commission across tranches proportionally
        for tranche in execution_plan.tranches:
            tranche.target_price = target_vwap if target_vwap else None

        logger.info(
            f"{symbol}: Created execution plan with {len(execution_plan.tranches)} "
            f"tranches, strategy: {strategy}"
        )

        # =====================================================================
        # STEP 7: Set up execution monitoring
        # =====================================================================

        # For strategies like POI with dynamic tranches, use minimum of 1
        total_tranches_for_monitoring = max(1, len(execution_plan.tranches))

        monitoring = self.cost_monitor.start_monitoring(
            execution_id=execution_plan.execution_id,
            planned_cost_budget=total_cost_budget,
            total_tranches=total_tranches_for_monitoring,
        )

        logger.info(f"{symbol}: Execution {execution_plan.execution_id} monitoring started")

        return execution_plan

    def get_cost_forecast(
        self,
        symbol: str,
        total_size: Decimal,
        daily_volume: Decimal,
        volatility_percentile: int = 50,
        asset_class: str = "equity",
    ) -> Dict:
        """
        Get cost forecast across different execution time windows.

        Useful for comparing strategies (TWAP at 5min vs TWAP at 30min, etc).

        Args:
            symbol: Trading symbol
            total_size: Total order size
            daily_volume: Expected daily volume
            volatility_percentile: Current volatility
            asset_class: Asset class

        Returns:
            Dict with cost forecasts for different time windows
        """

        total_size = Decimal(str(total_size))
        daily_volume = Decimal(str(daily_volume))

        # Get cost breakdown for different execution windows
        window_costs = self.market_impact_estimator.estimate_slippage_for_different_windows(
            symbol=symbol,
            order_size=total_size,
            daily_volume=daily_volume,
            volatility_percentile=volatility_percentile,
            asset_class=asset_class,
        )

        # Add commission cost (same regardless of window)
        commission_rate = self.broker_negotiation.get_rate_for_volume(
            symbol=symbol,
            volume_usd=total_size,
            asset_class=asset_class,
        )
        commission_cost = total_size * commission_rate

        # Summarize
        results = {
            "symbol": symbol,
            "total_size": total_size,
            "commission_cost": commission_cost,
            "commission_rate": commission_rate,
            "window_costs": {},
        }

        for time_ms, cost_data in window_costs.items():
            total_cost = cost_data["slippage_usd"] + commission_cost
            total_cost_bps = (total_cost / total_size) * Decimal("10000")

            results["window_costs"][int(cost_data["time_window_min"])] = {
                "time_minutes": int(cost_data["time_window_min"]),
                "slippage_cost": cost_data["slippage_usd"],
                "commission_cost": commission_cost,
                "total_cost": total_cost,
                "total_cost_bps": total_cost_bps,
            }

        logger.info(f"Cost forecast for {symbol}: {results}")
        return results

    def validate_execution_plan(
        self,
        execution_plan: ExecutionPlan,
    ) -> tuple:
        """
        Validate an execution plan for consistency.

        Args:
            execution_plan: ExecutionPlan to validate

        Returns:
            Tuple of (is_valid, message)
        """

        # Check basic consistency
        is_valid, message = execution_plan.validate()
        if not is_valid:
            return False, f"Execution plan validation failed: {message}"

        # Check cost budget
        if execution_plan.cost_budget and execution_plan.cost_budget <= Decimal("0"):
            return False, "cost_budget must be positive"

        # Check tranches
        if not execution_plan.tranches:
            return False, "Execution plan must have at least one tranche"

        for i, tranche in enumerate(execution_plan.tranches):
            if tranche.size <= Decimal("0"):
                return False, f"Tranche {i} has invalid size {tranche.size}"

            if not tranche.symbol:
                return False, f"Tranche {i} missing symbol"

        logger.info(f"Execution plan {execution_plan.execution_id} validated successfully")
        return True, "Execution plan valid"


# Global singleton
_smart_order_router: SmartOrderRouter = None


def get_smart_order_router() -> SmartOrderRouter:
    """Get or create global SmartOrderRouter instance."""
    global _smart_order_router
    if _smart_order_router is None:
        pass

    return _smart_order_router
