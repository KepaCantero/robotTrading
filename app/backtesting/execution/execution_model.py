"""
Realistic Execution Model - Main Orchestration (FASE 5.2)

This module provides the main execution model that coordinates all
execution components:
- Transaction costs
- Slippage estimation
- Market impact (Almgren-Chriss)
- Order fill simulation
- Partial fills and rejections

The RealisticExecutionModel provides a simple interface for executing
orders with realistic costs and constraints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from .market_impact import ImpactConfig, MarketImpactModel
from .models import CostBreakdown, ExecutionResult, ExecutionSummary, MarketSnapshot, Order
from .order_fill_simulator import OrderFillSimulator, SimulatorConfig
from .slippage_model import SlippageConfig, SlippageModel
from .transaction_cost import CostConfig, TransactionCostCalculator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """
    Complete configuration for the execution model.

    This includes all sub-configurations for cost, slippage, and impact models.

    Attributes:
        cost_config: Transaction cost configuration
        slippage_config: Slippage model configuration
        impact_config: Market impact configuration
        max_participation_rate: Maximum % of ADV to participate in
        allow_partial_fills: Whether partial fills are allowed
        enable_logging: Whether to log execution details
    """

    cost_config: CostConfig = field(default_factory=CostConfig)
    slippage_config: SlippageConfig = field(default_factory=SlippageConfig)
    impact_config: ImpactConfig = field(default_factory=ImpactConfig)

    # Fill constraints
    max_participation_rate: Decimal = Decimal("0.10")  # 10% ADV max
    allow_partial_fills: bool = True
    min_fill_pct: Decimal = Decimal("0.0")  # No minimum

    # Logging
    enable_logging: bool = True

    def to_simulator_config(self) -> SimulatorConfig:
        """Convert to SimulatorConfig."""
        from .order_fill_simulator import FillConstraints

        return SimulatorConfig(
            cost_config=self.cost_config,
            slippage_config=self.slippage_config,
            impact_config=self.impact_config,
            fill_constraints=FillConstraints(
                max_participation_rate=self.max_participation_rate,
                allow_partial_fills=self.allow_partial_fills,
                min_fill_pct=self.min_fill_pct,
            ),
        )


class RealisticExecutionModel:
    """
    Comprehensive execution model with realistic costs and constraints.

    This model coordinates all execution components to provide realistic
    order execution simulation for backtesting.

    **Features:**
    1. **Transaction Costs:** US equity fee structure (SEC, FINRA, exchange)
    2. **Slippage:** Size and volatility-based slippage estimation
    3. **Market Impact:** Almgren-Chriss permanent and temporary impact
    4. **Partial Fills:** Orders may partially fill based on liquidity
    5. **Order Rejection:** Orders rejected if too large relative to ADV

    **Example Usage:**
        ```python
        # Configure execution model
        config = ExecutionConfig(
            max_participation_rate=Decimal("0.10"),  # 10% ADV max
            allow_partial_fills=True,
        )

        model = RealisticExecutionModel(config)

        # Execute order
        order = Order(
            order_id="ORD001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1000,
        )

        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            symbol="AAPL",
            bid=Decimal("149.98"),
            ask=Decimal("150.02"),
            last_price=Decimal("150.00"),
            volume=1000000,
            average_daily_volume=Decimal("50000000"),
        )

        result = await model.execute_order(order, snapshot)

        if result.is_fully_filled:
            logger.debug(f"Filled {result.total_filled_shares} shares")
            logger.debug(f"Average price: ${result.avg_fill_price}")
            logger.debug(f"Total cost: ${result.total_cost:.2f}")
        ```

    **Cost Components:**
    - Commission: Per-share commission (default $0.005/share)
    - SEC Fee: $0.0000078 per dollar sold (capped at $5.95)
    - FINRA TAF: $0.000145 per share
    - Exchange Fees: ~$0.003 per share
    - Slippage: 5-50 bps depending on size and volatility
    - Market Impact: Almgren-Chriss model

    **Typical All-In Cost:**
    - Large cap liquid stocks: 5-10 bps
    - Mid cap: 10-25 bps
    - Small cap: 25-50+ bps
    """

    def __init__(self, config: ExecutionConfig | None = None):
        """
        Initialize realistic execution model.

        Args:
            config: Execution configuration (uses defaults if not provided)
        """
        self.config = config or ExecutionConfig()

        # Initialize components
        self.cost_calculator = TransactionCostCalculator(self.config.cost_config)
        self.slippage_model = SlippageModel(self.config.slippage_config)
        self.impact_model = MarketImpactModel(self.config.impact_config)
        self.fill_simulator = OrderFillSimulator(
            cost_calculator=self.cost_calculator,
            slippage_model=self.slippage_model,
            impact_model=self.impact_model,
            config=self.config.to_simulator_config(),
        )

        # Execution summary tracking
        self.summary = ExecutionSummary()

    async def execute_order(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
    ) -> ExecutionResult:
        """
        Execute order with realistic costs and slippage.

        This method simulates the complete execution process:
        1. Validates order
        2. Checks liquidity constraints
        3. Calculates transaction costs
        4. Estimates slippage
        5. Calculates market impact
        6. Simulates fill (full, partial, or reject)
        7. Returns detailed execution result

        Args:
            order: Order to execute
            market_snapshot: Current market conditions

        Returns:
            ExecutionResult with complete execution details

        Raises:
            ValueError: If order parameters are invalid
        """
        if self.config.enable_logging:
            logger.info(
                f"Executing order: {order.order_id} - {order.side.value} "
                f"{order.quantity} shares of {order.symbol}"
            )

        # Simulate fill
        fill_result = await self.fill_simulator.simulate_fill(order, market_snapshot)

        # Build execution result
        if fill_result.filled:
            # Order was filled (fully or partially)
            total_filled = fill_result.filled_shares
            avg_price = fill_result.fill_price

            # Build cost breakdown
            Decimal(str(total_filled)) * avg_price

            # Get detailed cost breakdown
            cost_details = self.fill_simulator.get_cost_breakdown(order, market_snapshot)

            # Scale costs for partial fills
            fill_ratio = Decimal(str(total_filled)) / Decimal(str(order.quantity))
            cost_breakdown = CostBreakdown(
                commission=cost_details["commission"] * fill_ratio,
                sec_fee=cost_details["sec_fee"] * fill_ratio,
                finra_taf=cost_details["finra_taf"] * fill_ratio,
                exchange_fee=cost_details["exchange_fee"] * fill_ratio,
                slippage_cost=cost_details["slippage_cost"] * fill_ratio,
                market_impact_cost=cost_details["market_impact_cost"] * fill_ratio,
                spread_cost=Decimal("0"),  # Already included in slippage
            )

            # Determine status
            is_fully_filled = total_filled >= order.quantity
            is_partial_fill = fill_result.is_partial_fill
            is_rejected = False

            execution_summary = (
                f"{'Fully' if is_fully_filled else 'Partially'} filled "
                f"{total_filled} shares of {order.symbol} at ${avg_price}"
            )

        else:
            # Order was rejected
            total_filled = 0
            avg_price = Decimal("0")
            cost_breakdown = CostBreakdown()
            is_fully_filled = False
            is_partial_fill = False
            is_rejected = True
            execution_summary = f"Order rejected: {fill_result.fill_reason.value}"

        result = ExecutionResult(
            order=order,
            fills=[fill_result] if fill_result.filled else [],
            total_filled_shares=total_filled,
            avg_fill_price=avg_price,
            total_commission=cost_breakdown.commission if fill_result.filled else Decimal("0"),
            total_slippage_bps=fill_result.slippage_bps,
            total_market_impact_bps=fill_result.market_impact_bps,
            total_cost=fill_result.total_cost,
            first_fill_time=fill_result.fill_time if fill_result.filled else None,
            last_fill_time=fill_result.fill_time if fill_result.filled else None,
            is_fully_filled=is_fully_filled,
            is_partial_fill=is_partial_fill,
            is_rejected=is_rejected,
            cost_breakdown=cost_breakdown,
            execution_summary=execution_summary,
            warnings=list(fill_result.warnings),
        )

        # Update summary
        self.summary.add_execution(result)

        if self.config.enable_logging:
            logger.info(
                f"Execution result: {execution_summary} (Total cost: ${result.total_cost:.2f})"
            )

        return result

    async def execute_orders_batch(
        self,
        orders: list[Order],
        market_snapshots: dict[str, MarketSnapshot],
    ) -> list[ExecutionResult]:
        """
        Execute multiple orders in batch.

        Args:
            orders: List of orders to execute
            market_snapshots: Dictionary mapping symbol to MarketSnapshot

        Returns:
            List of ExecutionResult objects
        """
        results = []

        for order in orders:
            snapshot = market_snapshots.get(order.symbol)

            if snapshot is None:
                logger.warning(f"No market data for {order.symbol}, skipping order")
                continue

            result = await self.execute_order(order, snapshot)
            results.append(result)

        return results

    def get_execution_summary(self) -> ExecutionSummary:
        """
        Get summary of all executions.

        Returns:
            ExecutionSummary with aggregated statistics
        """
        return self.summary

    def reset_summary(self) -> None:
        """Reset execution summary statistics."""
        self.summary = ExecutionSummary()

    def estimate_execution_cost(
        self,
        symbol: str,
        side: str,
        shares: int,
        price: Decimal,
        adv: Decimal,
        volatility: Decimal | None = None,
    ) -> dict[str, Decimal]:
        """
        Quick estimate of execution cost without full simulation.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            shares: Number of shares
            price: Current price
            adv: Average daily volume (shares)
            volatility: Optional volatility measure

        Returns:
            Dictionary with estimated costs
        """
        # Transaction cost
        transaction_cost = self.cost_calculator.calculate_cost(
            symbol=symbol,
            side=side,
            shares=shares,
            price=price,
        )

        # Estimate slippage
        # (simplified, assumes reasonable spread)
        mid_price = price
        bid = price * Decimal("0.9998")  # Assume 2 bps spread
        ask = price * Decimal("1.0002")

        slippage_estimate = self.slippage_model.estimate_slippage(
            symbol=symbol,
            side=side,
            shares=shares,
            current_price=mid_price,
            bid=bid,
            ask=ask,
            adv=adv,
            volatility=volatility,
        )

        slippage_cost = (
            Decimal(str(shares)) * price * (slippage_estimate.basis_points / Decimal("10000"))
        )

        # Estimate market impact
        order_value = Decimal(str(shares)) * price
        adv_value = adv * price

        market_impact = self.impact_model.calculate_impact(
            order_size=order_value,
            adv=adv_value,
            volatility=volatility or Decimal("0.20"),
            side=side,
            base_price=price,
        )

        total_cost = (
            transaction_cost.total_cost + slippage_cost + market_impact.total_impact_dollars
        )

        return {
            "commission": transaction_cost.commission,
            "regulatory_fees": transaction_cost.regulatory_fees,
            "slippage_cost": slippage_cost.quantize(Decimal("0.01")),
            "market_impact_cost": market_impact.total_impact_dollars.quantize(Decimal("0.01")),
            "total_cost": total_cost.quantize(Decimal("0.01")),
            "total_cost_bps": (total_cost / order_value * Decimal("10000")).quantize(
                Decimal("0.01")
            ),
            "estimated_fill_price": slippage_estimate.estimated_fill_price,
        }

    def validate_order_feasibility(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
    ) -> tuple[bool, list[str]]:
        """
        Validate if order is likely to be filled.

        Checks liquidity constraints and returns warnings/issues.

        Args:
            order: Order to validate
            market_snapshot: Current market conditions

        Returns:
            Tuple of (is_feasible, list_of_warnings)
        """
        warnings = []

        # Check if market is open
        if not market_snapshot.is_market_open:
            return False, ["Market is closed"]

        if market_snapshot.is_trading_halt:
            return False, ["Trading halt in effect"]

        # Calculate participation rate
        order_value = Decimal(str(order.quantity)) * market_snapshot.last_price
        adv_value = market_snapshot.average_daily_volume * market_snapshot.last_price

        participation_rate = order_value / adv_value if adv_value > 0 else Decimal("1")

        # Check participation rate
        if participation_rate > self.config.max_participation_rate:
            warnings.append(
                f"Order size ({participation_rate * 100:.1f}% of ADV) exceeds "
                f"maximum participation rate ({self.config.max_participation_rate * 100:.0f}%)"
            )

        # Estimate fill probability
        fill_prob = self.fill_simulator.estimate_fill_probability(order, market_snapshot)

        if fill_prob < 0.5:
            warnings.append(f"Low fill probability: {fill_prob * 100:.0f}%")
        elif fill_prob < 0.8:
            warnings.append(f"Moderate fill probability: {fill_prob * 100:.0f}%")

        is_feasible = fill_prob > 0 and market_snapshot.is_market_open

        return is_feasible, warnings
