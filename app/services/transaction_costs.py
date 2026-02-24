"""
Transaction Cost Models - Rishi Narang "Inside the Black Box" Chapter 5

This module implements the Transaction Cost Model architecture from Narang's framework:
- Commission models
- Market impact models
- Slippage estimation
- Total cost of ownership analysis

Key concepts from "Inside the Black Box":
- Transaction costs are a critical component of strategy profitability
- Total transaction cost = commission + spread + market impact + timing cost
- Market impact follows a square-root law (Almgren-Chriss model)
- Execution algorithms can minimize costs for large orders

From Narang: "Transaction costs are the enemy of the quantitative trader.
Every dollar spent on commissions, market impact, or slippage is a dollar
that cannot be retained as profit."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class CostComponent(str, Enum):
    """Components of transaction cost."""

    COMMISSION = "commission"
    SPREAD = "spread"
    MARKET_IMPACT = "market_impact"
    TIMING_RISK = "timing_risk"
    SLIPPAGE = "slippage"
    FEES = "fees"
    TAXES = "taxes"


class MarketImpactModel(str, Enum):
    """Models for estimating market impact."""

    SQUARE_ROOT = "square_root"  # Almgren-Chriss: impact ~ sqrt(participation)
    LINEAR = "linear"  # impact ~ participation
    POWER_LAW = "power_law"  # impact ~ participation^alpha
    NONE = "none"


class ExecutionAlgorithm(str, Enum):
    """Execution algorithms for minimizing costs."""

    VWAP = "vwap"  # Volume-weighted average price
    TWAP = "twap"  # Time-weighted average price
    POV = "pov"  # Percentage of volume
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"
    MARKET = "market"  # Immediate execution (not recommended for large orders)
    LIMIT = "limit"  # Limit orders only


@dataclass
class MarketData:
    """Market data for cost estimation."""

    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume: Decimal
    average_daily_volume: Decimal
    volatility: float  # Annualized
    timestamp: datetime

    @property
    def spread(self) -> Decimal:
        """Bid-ask spread."""
        return self.ask - self.bid

    @property
    def mid_price(self) -> Decimal:
        """Mid price."""
        return (self.bid + self.ask) / 2


@dataclass
class OrderSpecification:
    """Specification of an order for cost analysis."""

    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    order_type: str  # "market", "limit", etc.
    limit_price: Optional[Decimal] = None
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK
    execution_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.MARKET
    urgency: float = 0.5  # 0-1, higher = more urgent


@dataclass
class CostBreakdown:
    """
    Detailed breakdown of transaction costs.

    From Narang: Understanding cost components is essential for optimization.
    """

    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal

    # Cost components
    commission: Decimal
    spread_cost: Decimal
    market_impact: Decimal
    timing_risk: Decimal
    slippage: Decimal
    fees: Decimal
    taxes: Decimal

    # Aggregated costs
    total_cost: Decimal
    cost_per_share: Decimal
    cost_as_bps: float  # Basis points

    # Market impact details
    participation_rate: float  # Order size / ADV
    impact_model: MarketImpactModel

    # Execution details
    execution_algorithm: ExecutionAlgorithm
    expected_duration_seconds: float
    timestamp: datetime


@dataclass
class CostAnalysis:
    """Analysis of transaction costs for a strategy or portfolio."""

    total_trades: int
    total_commission: Decimal
    total_spread_cost: Decimal
    total_market_impact: Decimal
    total_timing_risk: Decimal
    total_slippage: Decimal
    total_fees: Decimal
    total_taxes: Decimal
    total_cost: Decimal

    # Average costs
    avg_cost_per_trade: Decimal
    avg_cost_per_share: Decimal
    avg_cost_as_bps: float

    # Cost breakdown by component
    cost_breakdown: Dict[str, Decimal]

    # Recommendations
    recommendations: List[str]


class TransactionCostModel:
    """
    Base transaction cost model implementing Narang's framework.

    From Narang Chapter 5: Transaction cost models serve to:
    1. Estimate costs before trading
    2. Analyze actual costs after execution
    3. Guide execution algorithm selection
    4. Inform position sizing decisions
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)

        # Commission settings
        self.commission_per_share = Decimal(str(config.get("commission_per_share", 0.005)))
        self.min_commission = Decimal(str(config.get("min_commission", 1.0)))
        self.max_commission = Decimal(str(config.get("max_commission", 50.0)))

        # Market impact settings
        self.impact_model = MarketImpactModel(config.get("impact_model", "square_root"))
        self.impact_coefficient = float(config.get("impact_coefficient", 0.1))

        # Spread settings
        self.spread_multiplier = float(config.get("spread_multiplier", 0.5))

        # Timing risk settings
        self.timing_risk_coefficient = float(config.get("timing_risk_coefficient", 1.0))

        # Thresholds
        self.max_participation_rate = float(config.get("max_participation_rate", 0.01))
        self.large_order_threshold = float(config.get("large_order_threshold", 0.05))

    def calculate_transaction_costs(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        order_id: str = "",
    ) -> CostBreakdown:
        """
        Calculate total transaction cost for an order.

        From Narang: Total cost = commission + spread + market impact + timing cost

        Args:
            order: Order specification
            market_data: Current market data
            order_id: Optional order identifier

        Returns:
            Detailed cost breakdown
        """
        # 1. Commission (fixed cost)
        commission = self._calculate_commission(order.quantity, order.side)

        # 2. Spread cost (half the spread for crossing the spread)
        spread_cost = self._calculate_spread_cost(order, market_data)

        # 3. Market impact (permanent price impact)
        market_impact, participation_rate = self._calculate_market_impact(order, market_data)

        # 4. Timing risk (temporary price movement during execution)
        timing_risk = self._calculate_timing_risk(order, market_data, participation_rate)

        # 5. Slippage (execution price vs expected)
        slippage = self._calculate_slippage(order, market_data, market_impact)

        # 6. Fees (exchange fees, regulatory fees, etc.)
        fees = self._calculate_fees(order, market_data)

        # 7. Taxes (if applicable)
        taxes = self._calculate_taxes(order, market_data)

        # Calculate execution price estimate
        execution_price = self._estimate_execution_price(order, market_data, market_impact)

        # Aggregate costs
        total_cost = (
            commission + spread_cost + market_impact + timing_risk + slippage + fees + taxes
        )

        # Calculate cost metrics
        cost_per_share = total_cost / order.quantity if order.quantity > 0 else Decimal("0")
        trade_value = order.quantity * execution_price
        # Use config value for BPS multiplier
        tt = get_config().trading_thresholds
        cost_as_bps = float(total_cost / trade_value * tt.bps_multiplier) if trade_value > 0 else 0.0

        # Estimate execution duration
        expected_duration = self._estimate_execution_duration(
            order, market_data, participation_rate
        )

        return CostBreakdown(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            execution_price=execution_price,
            commission=commission,
            spread_cost=spread_cost,
            market_impact=market_impact,
            timing_risk=timing_risk,
            slippage=slippage,
            fees=fees,
            taxes=taxes,
            total_cost=total_cost,
            cost_per_share=cost_per_share,
            cost_as_bps=cost_as_bps,
            participation_rate=participation_rate,
            impact_model=self.impact_model,
            execution_algorithm=order.execution_algorithm,
            expected_duration_seconds=expected_duration,
            timestamp=datetime.now(),
        )

    def _calculate_commission(self, quantity: Decimal, side: str) -> Decimal:
        """Calculate commission for a trade."""
        commission = quantity * self.commission_per_share

        # Apply min/max
        commission = max(commission, self.min_commission)
        commission = min(commission, self.max_commission)

        return commission.quantize(Decimal("0.01"))

    def _calculate_spread_cost(self, order: OrderSpecification, market_data: MarketData) -> Decimal:
        """
        Calculate spread cost.

        From Narang: Spread cost = (spread / 2) * quantity
        (We pay half the spread when we cross the spread)
        """
        spread_cost = (market_data.spread / 2) * order.quantity
        return spread_cost.quantize(Decimal("0.01"))

    def _calculate_market_impact(
        self, order: OrderSpecification, market_data: MarketData
    ) -> Tuple[Decimal, float]:
        """
        Calculate market impact cost using square-root model.

        From Narang (Almgren-Chriss):
        Market Impact = 0.1 * volatility * sqrt(participation_rate) * price * quantity

        where participation_rate = order_size / average_daily_volume
        """
        # Calculate participation rate
        adv = float(market_data.average_daily_volume)
        order_size = float(order.quantity)
        participation_rate = order_size / adv if adv > 0 else 0.0

        if self.impact_model == MarketImpactModel.NONE:
            return Decimal("0"), participation_rate

        # Calculate market impact
        if self.impact_model == MarketImpactModel.SQUARE_ROOT:
            # Square root model (Almgren-Chriss)
            impact = (
                self.impact_coefficient
                * market_data.volatility
                * np.sqrt(participation_rate)
                * float(market_data.mid_price)
                * order_size
            )
        elif self.impact_model == MarketImpactModel.LINEAR:
            # Linear model
            impact = (
                self.impact_coefficient
                * market_data.volatility
                * participation_rate
                * float(market_data.mid_price)
                * order_size
            )
        elif self.impact_model == MarketImpactModel.POWER_LAW:
            # Power law model: impact ~ participation^alpha
            alpha = self.config.get("power_law_alpha", 0.6)
            impact = (
                self.impact_coefficient
                * market_data.volatility
                * (participation_rate**alpha)
                * float(market_data.mid_price)
                * order_size
            )
        else:
            impact = 0.0

        return Decimal(str(impact)).quantize(Decimal("0.01")), participation_rate

    def _calculate_timing_risk(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        participation_rate: float,
    ) -> Decimal:
        """
        Calculate timing risk (temporary price impact during execution).

        From Narang: If order takes T hours to execute, price can move against us.
        Timing Risk = volatility * sqrt(expected_duration / trading_hours_per_year) * value
        """
        # Estimate expected duration in hours
        adv = float(market_data.average_daily_volume)
        order_size = float(order.quantity)

        # Assume 6.5 hour trading day
        trading_hours_per_day = 6.5
        trading_days_per_year = 252

        expected_hours = max(1, (order_size / adv) * trading_hours_per_day)
        expected_duration_years = expected_hours / (trading_hours_per_day * trading_days_per_year)

        # Calculate timing risk
        trade_value = float(market_data.mid_price) * order_size
        timing_risk = (
            self.timing_risk_coefficient
            * market_data.volatility
            * np.sqrt(expected_duration_years)
            * trade_value
        )

        return Decimal(str(timing_risk)).quantize(Decimal("0.01"))

    def _calculate_slippage(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        market_impact: Decimal,
    ) -> Decimal:
        """
        Calculate slippage (difference between expected and actual execution).

        Slippage is often correlated with market impact.
        Uses centralized config for market order slippage percentage.
        """
        # For market orders, slippage ≈ market impact
        if order.order_type == "market":
            tt = get_config().trading_thresholds
            slippage_pct = Decimal(str(tt.tx_market_order_slippage_pct))
            return market_impact * slippage_pct

        # For limit orders, less slippage but potential non-execution
        return Decimal("0")

    def _calculate_fees(self, order: OrderSpecification, market_data: MarketData) -> Decimal:
        """Calculate exchange and regulatory fees. Uses centralized config for fee rates."""
        # Get fee rates from centralized config
        tt = get_config().trading_thresholds
        sec_fee_rate = Decimal(str(tt.tx_sec_fee_per_share))
        trading_fee_rate = Decimal(str(tt.tx_trading_fee_per_share))

        # SEC fee (selling only)
        sec_fee = Decimal("0") if order.side == "buy" else order.quantity * sec_fee_rate

        # Trading fee
        trading_fee = order.quantity * trading_fee_rate

        # Total fees
        total_fees = sec_fee + trading_fee
        return total_fees.quantize(Decimal("0.01"))

    def _calculate_taxes(self, order: OrderSpecification, market_data: MarketData) -> Decimal:
        """Calculate taxes (usually not applicable at trade time)."""
        return Decimal("0")

    def _estimate_execution_price(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        market_impact: Decimal,
    ) -> Decimal:
        """
        Estimate expected execution price including market impact.
        """
        base_price = market_data.mid_price

        if order.side == "buy":
            # Buyers push price up
            impact_per_share = (
                market_impact / order.quantity if order.quantity > 0 else Decimal("0")
            )
            return base_price + impact_per_share
        else:
            # Sellers push price down
            impact_per_share = (
                market_impact / order.quantity if order.quantity > 0 else Decimal("0")
            )
            return base_price - impact_per_share

    def _estimate_execution_duration(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        participation_rate: float,
    ) -> float:
        """
        Estimate execution duration in seconds.
        """
        if order.execution_algorithm == ExecutionAlgorithm.MARKET:
            # Market orders execute almost immediately
            return 1.0

        # For algorithmic execution, estimate based on participation rate
        # Assume we want to participate in X% of volume
        target_participation = 0.1  # 10% of volume

        if participation_rate > target_participation:
            # Large order - need more time
            ratio = participation_rate / target_participation
            # Spread over 6.5 hour trading day
            return ratio * 6.5 * 3600  # Convert to seconds

        # Small order - execute quickly
        return 60.0  # 1 minute

    def validate_order_type(
        self, order: OrderSpecification, market_data: MarketData
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that order type is appropriate for order size.

        From Narang: "NUNCA uses Market Orders para órdenes > 1% ADV"
        Market orders only for small orders. Large orders MUST use execution algorithms.
        """
        participation_rate = float(order.quantity) / float(market_data.average_daily_volume)

        if order.order_type == "market" and participation_rate > self.max_participation_rate:
            return (
                False,
                f"Market order for {participation_rate:.1%} of ADV exceeds threshold "
                f"({self.max_participation_rate:.1%}). Use execution algorithm (VWAP/TWAP/POV).",
            )

        if order.execution_algorithm == ExecutionAlgorithm.MARKET and participation_rate > 0.05:
            return (
                False,
                f"Market execution for {participation_rate:.1%} of ADV is too large. "
                f"Consider VWAP or TWAP execution.",
            )

        return True, None

    def recommend_execution_algorithm(
        self, order: OrderSpecification, market_data: MarketData
    ) -> ExecutionAlgorithm:
        """
        Recommend the best execution algorithm based on order characteristics.

        From Narang Chapter 5: Algorithm choice depends on:
        - Order size relative to ADV
        - Urgency
        - Market conditions
        """
        participation_rate = float(order.quantity) / float(market_data.average_daily_volume)

        # Very small orders: market is fine
        if participation_rate < 0.01:
            return ExecutionAlgorithm.MARKET

        # Small to medium orders: depends on urgency
        if participation_rate < 0.05:
            if order.urgency > 0.7:
                return ExecutionAlgorithm.MARKET
            else:
                return ExecutionAlgorithm.LIMIT

        # Medium orders: use POV or TWAP
        if participation_rate < 0.10:
            if order.urgency > 0.7:
                return ExecutionAlgorithm.POV
            else:
                return ExecutionAlgorithm.TWAP

        # Large orders: use VWAP or implementation shortfall
        if order.urgency > 0.8:
            return ExecutionAlgorithm.POV
        else:
            return ExecutionAlgorithm.VWAP

    def analyze_cost_impact(self, cost_breakdown: CostBreakdown) -> Dict[str, Any]:
        """
        Analyze the impact of transaction costs on strategy profitability.

        From Narang: Understanding cost structure is key to strategy success.
        """
        # Cost breakdown by component
        components = {
            "commission": cost_breakdown.commission,
            "spread": cost_breakdown.spread_cost,
            "market_impact": cost_breakdown.market_impact,
            "timing_risk": cost_breakdown.timing_risk,
        }

        # Identify largest cost component
        largest_component = max(components.items(), key=lambda x: x[1])

        # Generate recommendations
        recommendations = []

        if cost_breakdown.market_impact > cost_breakdown.commission * 2:
            recommendations.append(
                "Market impact is dominant. Consider using execution algorithm (VWAP/TWAP)."
            )

        if cost_breakdown.participation_rate > 0.10:
            recommendations.append(
                f"Large order ({cost_breakdown.participation_rate:.1%} of ADV). "
                "Consider splitting into smaller orders."
            )

        if cost_breakdown.cost_as_bps > 50:
            recommendations.append(
                f"High transaction cost ({cost_breakdown.cost_as_bps:.1f} bps). "
                "Strategy may not be profitable."
            )

        if cost_breakdown.spread_cost > cost_breakdown.market_impact:
            recommendations.append(
                "Spread cost is high relative to market impact. Consider using limit orders."
            )

        return {
            "largest_component": largest_component[0],
            "largest_component_value": float(largest_component[1]),
            "cost_as_pct": cost_breakdown.cost_as_bps / 100,
            "recommendations": recommendations,
        }


class CommissionModel(TransactionCostModel):
    """Simple commission-only cost model."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.impact_model = MarketImpactModel.NONE


class AlmgrenChrissModel(TransactionCostModel):
    """
    Almgren-Chriss market impact model.

    From Narang: The Almgren-Chriss model is the industry standard for
    estimating market impact. It models both permanent and temporary impact.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.impact_model = MarketImpactModel.SQUARE_ROOT

        # Almgren-Chriss parameters
        self.permanent_impact_coef = float(config.get("permanent_impact_coef", 0.1))
        self.temporary_impact_coef = float(config.get("temporary_impact_coef", 0.5))
        self.liquidity_parameter = float(config.get("liquidity_parameter", 0.01))

    def _calculate_market_impact(
        self, order: OrderSpecification, market_data: MarketData
    ) -> Tuple[Decimal, float]:
        """
        Calculate Almgren-Chriss market impact.

        Permanent impact: eta * (order_size / ADV)
        Temporary impact: epsilon * sign(order) * (order_size / volume_participation_rate)
        """
        adv = float(market_data.average_daily_volume)
        order_size = float(order.quantity)
        participation_rate = order_size / adv if adv > 0 else 0.0

        # Permanent impact
        permanent_impact = (
            self.permanent_impact_coef
            * market_data.volatility
            * participation_rate
            * float(market_data.mid_price)
            * order_size
        )

        # Temporary impact
        sign = 1 if order.side == "buy" else -1
        temporary_impact = (
            self.temporary_impact_coef
            * sign
            * market_data.volatility
            * (participation_rate / self.liquidity_parameter)
            * float(market_data.mid_price)
            * order_size
        )

        total_impact = permanent_impact + abs(temporary_impact)

        return Decimal(str(total_impact)).quantize(Decimal("0.01")), participation_rate


def get_transaction_cost_model(config: Dict[str, Any]) -> TransactionCostModel:
    """
    Factory function to create transaction cost models.

    Args:
        config: Configuration with 'model_type' key

    Returns:
        TransactionCostModel instance
    """
    model_type = config.get("model_type", "almgren_chriss")

    if model_type == "commission":
        return CommissionModel(config)
    elif model_type == "almgren_chriss":
        return AlmgrenChrissModel(config)
    else:
        return TransactionCostModel(config)


__all__ = [
    "CostComponent",
    "MarketImpactModel",
    "ExecutionAlgorithm",
    "MarketData",
    "OrderSpecification",
    "CostBreakdown",
    "CostAnalysis",
    "TransactionCostModel",
    "CommissionModel",
    "AlmgrenChrissModel",
    "get_transaction_cost_model",
]
