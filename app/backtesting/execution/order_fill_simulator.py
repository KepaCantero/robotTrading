"""
Order Fill Simulator for Realistic Execution (FASE 5.2)

This module simulates realistic order fills by combining:
- Transaction costs (commission, fees)
- Slippage estimation
- Market impact (Almgren-Chriss)
- Partial fills
- Order rejection (liquidity constraints)

The simulator provides a realistic estimate of actual execution
results for backtesting.

SINGLE SOURCE OF TRUTH: Base values from CentralizedConfig.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

# SINGLE SOURCE OF TRUTH: Import CentralizedConfig
from app.core.centralized_config import get_config

from .market_impact import ImpactConfig, MarketImpactModel
from .models import FillReason, FillResult, MarketSnapshot, Order, OrderSide
from .slippage_model import SlippageConfig, SlippageModel
from .transaction_cost import CostConfig, TransactionCost, TransactionCostCalculator

logger = logging.getLogger(__name__)


def _get_backtesting_config():
    """Helper to get backtesting config from CentralizedConfig."""
    return get_config().backtesting


def _default_max_participation_rate():
    """Get default max participation rate from CentralizedConfig."""
    return _get_backtesting_config().adv_limit_pct


def _default_max_slippage_bps():
    """Get default max slippage (5x base)."""
    return _get_backtesting_config().base_slippage_bps * 5


@dataclass(frozen=True)
class FillConstraints:
    """
    Constraints on order fills.

    SINGLE SOURCE OF TRUTH: Base values from CentralizedConfig.

    Attributes:
        max_participation_rate: Maximum % of ADV to participate in
        max_slippage_bps: Maximum acceptable slippage
        max_market_impact_bps: Maximum acceptable market impact
        min_fill_pct: Minimum fill percentage (all-or-none if 100%)
        allow_partial_fills: Whether partial fills are allowed
    """

    max_participation_rate: Decimal = field(default_factory=_default_max_participation_rate)
    max_slippage_bps: Decimal = field(default_factory=_default_max_slippage_bps)
    max_market_impact_bps: Decimal = Decimal("100")  # 100 bps max
    min_fill_pct: Decimal = Decimal("0.0")  # No minimum by default
    allow_partial_fills: bool = True


@dataclass(frozen=True)
class SimulatorConfig:
    """
    Configuration for order fill simulator.

    SINGLE SOURCE OF TRUTH: Defaults from CentralizedConfig.

    Attributes:
        cost_config: Transaction cost configuration
        slippage_config: Slippage model configuration
        impact_config: Market impact configuration
        fill_constraints: Fill constraints
        rejection_threshold: Order size vs ADV threshold for rejection
    """

    cost_config: CostConfig = field(default_factory=CostConfig)
    slippage_config: SlippageConfig = field(default_factory=SlippageConfig)
    impact_config: ImpactConfig = field(default_factory=ImpactConfig)
    fill_constraints: FillConstraints = field(default_factory=FillConstraints)

    # Rejection thresholds - derived from CentralizedConfig
    rejection_threshold_adv_pct: Decimal = field(default_factory=lambda: _get_backtesting_config().adv_limit_pct * Decimal("2.5"))
    liquidity_warning_threshold: Decimal = field(default_factory=lambda: _get_backtesting_config().adv_limit_pct * Decimal("1.5"))


class OrderFillSimulator:
    """
    Realistic order fill simulator.

    This simulator combines all execution cost components to provide
    a realistic estimate of order execution results.

    **Process:**
    1. Validate order
    2. Check liquidity constraints (order size vs ADV)
    3. Calculate transaction costs
    4. Estimate slippage
    5. Calculate market impact
    6. Simulate fill (full, partial, or reject)
    7. Return detailed fill result

    Example:
        simulator = OrderFillSimulator()

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

        result = await simulator.simulate_fill(order, snapshot)
    """

    def __init__(
        self,
        cost_calculator: Optional[TransactionCostCalculator] = None,
        slippage_model: Optional[SlippageModel] = None,
        impact_model: Optional[MarketImpactModel] = None,
        config: Optional[SimulatorConfig] = None,
    ):
        """
        Initialize order fill simulator.

        Args:
            cost_calculator: Transaction cost calculator (created if not provided)
            slippage_model: Slippage model (created if not provided)
            impact_model: Market impact model (created if not provided)
            config: Simulator configuration (uses defaults if not provided)
        """
        self.config = config or SimulatorConfig()

        # Initialize components
        self.cost_calculator = cost_calculator or TransactionCostCalculator(self.config.cost_config)
        self.slippage_model = slippage_model or SlippageModel(self.config.slippage_config)
        self.impact_model = impact_model or MarketImpactModel(self.config.impact_config)

    def simulate_fill(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
    ) -> FillResult:
        """
        Simulate realistic order fill with all costs.

        Args:
            order: Order to simulate
            market_snapshot: Current market conditions

        Returns:
            FillResult with execution details

        Raises:
            ValueError: If order or market data is invalid
        """
        # Validate order
        order.validate()

        # Check if market is open
        if not market_snapshot.is_market_open:
            return self._create_rejected_result(
                order,
                FillReason.MARKET_CLOSED,
                "Market is closed",
            )

        # Check for trading halt
        if market_snapshot.is_trading_halt:
            return self._create_rejected_result(
                order,
                FillReason.MARKET_CLOSED,
                "Trading halt in effect",
            )

        # Calculate order value
        current_price = market_snapshot.last_price
        order_value = Decimal(str(order.quantity)) * current_price

        # Check liquidity constraints
        adv_value = market_snapshot.average_daily_volume * current_price
        participation_rate = order_value / adv_value if adv_value > 0 else Decimal("0")

        # Rejection threshold check
        if participation_rate > self.config.rejection_threshold_adv_pct:
            return self._create_rejected_result(
                order,
                FillReason.EXCEEDS_ADV,
                f"Order size ({participation_rate*100:.1f}% of ADV) exceeds rejection threshold",
            )

        # Liquidity warning
        warnings = []
        if participation_rate > self.config.liquidity_warning_threshold:
            warnings.append(f"Large order: {participation_rate*100:.1f}% of ADV")

        # 1. Calculate transaction costs
        transaction_cost = self.cost_calculator.calculate_cost(
            symbol=order.symbol,
            side=order.side.value,
            shares=order.quantity,
            price=current_price,
        )

        # 2. Estimate slippage
        slippage_estimate = self.slippage_model.estimate_slippage(
            symbol=order.symbol,
            side=order.side.value,
            shares=order.quantity,
            current_price=current_price,
            bid=market_snapshot.bid,
            ask=market_snapshot.ask,
            adv=market_snapshot.average_daily_volume,
            volatility=market_snapshot.historical_volatility_20d,
            vix=market_snapshot.vix,
            timestamp=market_snapshot.timestamp,
        )

        # Check slippage constraints
        if slippage_estimate.basis_points > self.config.fill_constraints.max_slippage_bps:
            if not self.config.fill_constraints.allow_partial_fills:
                return self._create_rejected_result(
                    order,
                    FillReason.PRICE_LIMIT,
                    f"Slippage ({slippage_estimate.basis_points} bps) exceeds maximum",
                )
            warnings.append(f"High slippage: {slippage_estimate.basis_points} bps")

        # 3. Calculate market impact
        market_impact = self.impact_model.calculate_impact(
            order_size=order_value,
            adv=adv_value,
            volatility=market_snapshot.historical_volatility_20d or Decimal("0.20"),
            side=order.side.value,
            base_price=current_price,
        )

        # Check market impact constraints
        if market_impact.total_impact_bps > self.config.fill_constraints.max_market_impact_bps:
            if not self.config.fill_constraints.allow_partial_fills:
                return self._create_rejected_result(
                    order,
                    FillReason.PRICE_LIMIT,
                    f"Market impact ({market_impact.total_impact_bps} bps) exceeds maximum",
                )
            warnings.append(f"High market impact: {market_impact.total_impact_bps} bps")

        # 4. Determine fill details
        fill_price = slippage_estimate.estimated_fill_price

        # Adjust for market impact
        impact_adjustment = market_impact.total_price_adjustment
        if order.side == OrderSide.BUY:
            fill_price = fill_price * (Decimal("1") + impact_adjustment)
        else:
            fill_price = fill_price * (Decimal("1") - impact_adjustment)

        fill_price = fill_price.quantize(Decimal("0.01"))

        # 5. Calculate total cost
        slippage_cost = order_value * (slippage_estimate.basis_points / Decimal("10000"))
        impact_cost = market_impact.total_impact_dollars
        total_cost = transaction_cost.total_cost + slippage_cost + impact_cost

        # 6. Determine if partial fill
        filled_shares = order.quantity
        is_partial_fill = False

        # Apply participation rate limit
        if participation_rate > self.config.fill_constraints.max_participation_rate:
            # Scale down to max participation rate
            scale_factor = self.config.fill_constraints.max_participation_rate / participation_rate
            filled_shares = int(order.quantity * float(scale_factor))
            is_partial_fill = True
            warnings.append(
                f"Partial fill: scaled down to {self.config.fill_constraints.max_participation_rate*100:.1f}% of ADV"
            )

        # Check minimum fill constraint
        if self.config.fill_constraints.min_fill_pct > 0:
            min_shares = int(order.quantity * float(self.config.fill_constraints.min_fill_pct))
            if filled_shares < min_shares:
                return self._create_rejected_result(
                    order,
                    FillReason.INSUFFICIENT_LIQUIDITY,
                    f"Cannot meet minimum fill requirement ({self.config.fill_constraints.min_fill_pct*100:.0f}%)",
                )

        # Scale costs for partial fill
        if is_partial_fill:
            fill_ratio = Decimal(str(filled_shares)) / Decimal(str(order.quantity))
            transaction_cost = TransactionCost(
                commission=transaction_cost.commission * fill_ratio,
                sec_fee=transaction_cost.sec_fee * fill_ratio,
                finra_taf=transaction_cost.finra_taf * fill_ratio,
                exchange_fee=transaction_cost.exchange_fee * fill_ratio,
                platform_fee=transaction_cost.platform_fee * fill_ratio,
                total_cost=transaction_cost.total_cost * fill_ratio,
            )
            slippage_cost = slippage_cost * fill_ratio
            impact_cost = impact_cost * fill_ratio
            total_cost = total_cost * fill_ratio

        # 7. Create fill result
        return FillResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled=True,
            filled_shares=filled_shares,
            fill_price=fill_price,
            fill_time=market_snapshot.timestamp,
            commission=transaction_cost.commission,
            slippage_bps=slippage_estimate.basis_points,
            market_impact_bps=market_impact.total_impact_bps,
            total_cost=total_cost.quantize(Decimal("0.01")),
            fill_reason=FillReason.FULL_FILL if not is_partial_fill else FillReason.PARTIAL_FILL,
            bid_at_fill=market_snapshot.bid,
            ask_at_fill=market_snapshot.ask,
            spread_at_fill_bps=market_snapshot.spread_bps,
            adv_at_fill=market_snapshot.average_daily_volume,
            volatility_at_fill=market_snapshot.historical_volatility_20d,
            is_partial_fill=is_partial_fill,
            remaining_shares=order.quantity - filled_shares,
            estimated_remaining_cost=(
                total_cost
                * (Decimal(str(order.quantity - filled_shares)) / Decimal(str(filled_shares)))
                if filled_shares > 0
                else Decimal("0")
            ),
            warnings=warnings,
        )

    def _create_rejected_result(
        self,
        order: Order,
        reason: FillReason,
        message: str,
    ) -> FillResult:
        """Create a rejected order result."""
        return FillResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            filled=False,
            filled_shares=0,
            fill_price=Decimal("0"),
            fill_time=None,
            commission=Decimal("0"),
            slippage_bps=Decimal("0"),
            market_impact_bps=Decimal("0"),
            total_cost=Decimal("0"),
            fill_reason=reason,
            warnings=[message] if message else [],
        )

    def simulate_fill_sequence(
        self,
        order: Order,
        market_snapshots: List[MarketSnapshot],
    ) -> List[FillResult]:
        """
        Simulate order fill across multiple time periods.

        Useful for simulating orders that may fill across multiple bars.

        Args:
            order: Order to simulate
            market_snapshots: Series of market snapshots

        Returns:
            List of FillResult objects (one per time period)
        """
        results = []
        remaining_order = order

        for snapshot in market_snapshots:
            if remaining_order.remaining_quantity <= 0:
                break

            # Create partial order for remaining quantity
            partial_order = Order(
                order_id=f"{order.order_id}_{len(results)}",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=remaining_order.remaining_quantity,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                created_at=order.created_at,
            )

            result = self.simulate_fill(partial_order, snapshot)
            results.append(result)

            if result.filled:
                remaining_order.filled_quantity += result.filled_shares

        return results

    def estimate_fill_probability(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
    ) -> float:
        """
        Estimate probability of order being filled.

        Args:
            order: Order to evaluate
            market_snapshot: Current market conditions

        Returns:
            Fill probability (0-1)
        """
        if not market_snapshot.is_market_open or market_snapshot.is_trading_halt:
            return 0.0

        # Calculate participation rate
        current_price = market_snapshot.last_price
        order_value = Decimal(str(order.quantity)) * current_price
        adv_value = market_snapshot.average_daily_volume * current_price

        participation_rate = order_value / adv_value if adv_value > 0 else Decimal("1")

        # Base probability on participation rate
        if participation_rate > self.config.rejection_threshold_adv_pct:
            return 0.0
        elif participation_rate > self.config.fill_constraints.max_participation_rate:
            # Will partially fill
            return float(self.config.fill_constraints.max_participation_rate / participation_rate)
        else:
            return 1.0

    def get_cost_breakdown(
        self,
        order: Order,
        market_snapshot: MarketSnapshot,
    ) -> Dict[str, Decimal]:
        """
        Get detailed cost breakdown without simulating fill.

        Args:
            order: Order to evaluate
            market_snapshot: Current market conditions

        Returns:
            Dictionary of cost components
        """
        current_price = market_snapshot.last_price
        order_value = Decimal(str(order.quantity)) * current_price

        # Transaction costs
        transaction_cost = self.cost_calculator.calculate_cost(
            symbol=order.symbol,
            side=order.side.value,
            shares=order.quantity,
            price=current_price,
        )

        # Slippage
        slippage_estimate = self.slippage_model.estimate_slippage(
            symbol=order.symbol,
            side=order.side.value,
            shares=order.quantity,
            current_price=current_price,
            bid=market_snapshot.bid,
            ask=market_snapshot.ask,
            adv=market_snapshot.average_daily_volume,
            volatility=market_snapshot.historical_volatility_20d,
            vix=market_snapshot.vix,
        )

        slippage_cost = order_value * (slippage_estimate.basis_points / Decimal("10000"))

        # Market impact
        adv_value = market_snapshot.average_daily_volume * current_price
        market_impact = self.impact_model.calculate_impact(
            order_size=order_value,
            adv=adv_value,
            volatility=market_snapshot.historical_volatility_20d or Decimal("0.20"),
            side=order.side.value,
        )

        return {
            "commission": transaction_cost.commission,
            "sec_fee": transaction_cost.sec_fee,
            "finra_taf": transaction_cost.finra_taf,
            "exchange_fee": transaction_cost.exchange_fee,
            "total_regulatory_fees": transaction_cost.regulatory_fees,
            "slippage_cost": slippage_cost,
            "market_impact_cost": market_impact.total_impact_dollars,
            "total_cost": (
                transaction_cost.total_cost + slippage_cost + market_impact.total_impact_dollars
            ),
            "cost_as_bps": (
                (transaction_cost.total_cost + slippage_cost + market_impact.total_impact_dollars)
                / order_value
                * Decimal("10000")
            ).quantize(Decimal("0.01")),
        }
