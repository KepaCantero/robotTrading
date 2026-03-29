"""
Dark Pool Router

Implements Harris Rule 6.7: Dark pool usage for large orders.

Dark pools are useful for:
- Hiding order flow (avoid front-running)
- Executing large orders without moving the market
- Reducing market impact for sizeable orders

But have drawbacks:
- Poor price discovery
- Potential information leakage
- Higher costs for smaller orders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import ClassVar

logger = logging.getLogger(__name__)


class ExecutionVenue(Enum):
    """Execution venue types."""

    LIT_EXCHANGE = "lit_exchange"
    DARK_POOL = "dark_pool"
    INTERNALIZATION = "internalization"
    OTC = "otc"


@dataclass
class DarkPoolDecision:
    """Dark pool routing decision."""

    use_dark_pool: bool
    confidence: float
    reason: str

    # Venue allocation
    venue_allocation: dict[str, Decimal]  # venue -> percentage

    # Expected costs
    expected_dark_cost_bps: float
    expected_lit_cost_bps: float

    # Recommendations
    dark_pool_names: list[str]
    order_type: str  # ICEBERG, VWAP, etc.


class DarkPoolRouter:
    """
    Dark Pool Router (Harris Rule 6.7).

    Determines when to use dark pools for order execution.
    """

    # Minimum order size thresholds for dark pool consideration
    MIN_DARK_POOL_PARTICIPATION = Decimal("0.10")  # 10% of ADV
    MIN_DARK_POOL_SIZE_USD = Decimal("100000")  # $100K

    # Dark pool characteristics (typical)
    DARK_POOL_DISCOUNT_BPS = 2.0  # Typical discount vs lit
    DARK_POOL_IMPROVEMENT_RATE = 0.3  # % of orders with price improvement

    # Information leakage risk thresholds
    INFORMATION_LEAKAGE_THRESHOLDS: ClassVar[dict] = {
        "HIGH": 0.8,
        "MEDIUM": 0.5,
        "LOW": 0.2,
    }

    def __init__(
        self,
        min_participation_rate: Decimal | None = None,
        min_order_size_usd: Decimal | None = None,
    ):
        """
        Initialize dark pool router.

        Args:
            min_participation_rate: Min participation rate for dark pool
            min_order_size_usd: Min order size (USD) for dark pool
        """
        if min_participation_rate is None:
            min_participation_rate = Decimal("0.10")
        if min_order_size_usd is None:
            min_order_size_usd = Decimal("100000")
        self.min_participation_rate = min_participation_rate
        self.min_order_size_usd = min_order_size_usd

        # Available dark pools (example configuration)
        self.dark_pools = {
            "pool1": {
                "name": "IBKR",
                "avg_fill_rate": 0.15,
                "avg_improvement_bps": 3.5,
                "min_size_usd": 50000,
            },
            "pool2": {
                "name": "Crossfinder",
                "avg_fill_rate": 0.20,
                "avg_improvement_bps": 2.0,
                "min_size_usd": 100000,
            },
            "pool3": {
                "name": "Liquidnet",
                "avg_fill_rate": 0.25,
                "avg_improvement_bps": 4.0,
                "min_size_usd": 250000,
            },
        }

        logger.info(
            f"DarkPoolRouter initialized: min_participation={min_participation_rate}, "
            f"min_size=${min_order_size_usd}"
        )

    def should_use_dark_pool(
        self,
        order_size: Decimal,
        adv: Decimal,
        order_value_usd: Decimal,
        information_leakage_risk: str = "MEDIUM",
        current_spread_bps: float = 5.0,
        volatility_percentile: float = 50.0,
    ) -> DarkPoolDecision:
        """
        Determine if dark pool should be used for this order.

        Args:
            order_size: Order quantity (shares)
            adv: Average daily volume (shares)
            order_value_usd: Order value in USD
            information_leakage_risk: Risk level (HIGH, MEDIUM, LOW)
            current_spread_bps: Current bid-ask spread
            volatility_percentile: Market volatility percentile

        Returns:
            DarkPoolDecision with recommendation
        """
        # Calculate participation rate
        participation_rate = order_size / adv if adv > 0 else Decimal("0")

        # Initialize decision
        use_dark = False
        confidence = 0.0
        reasons = []
        venue_allocation = {"lit_exchange": Decimal("1")}

        # Decision factors

        # 1. Size check
        size_factor = self._evaluate_size_factor(
            order_size, adv, order_value_usd, participation_rate
        )
        if size_factor["passes"]:
            use_dark = True
            confidence += size_factor["confidence"]
            reasons.append(size_factor["reason"])

        # 2. Information leakage risk
        leakage_factor = self._evaluate_information_leakage(
            information_leakage_risk, participation_rate
        )
        if leakage_factor["use_dark"]:
            use_dark = True
            confidence += leakage_factor["confidence"]
            reasons.append(leakage_factor["reason"])

        # 3. Market conditions
        market_factor = self._evaluate_market_conditions(current_spread_bps, volatility_percentile)
        if market_factor["use_dark"]:
            use_dark = True
            confidence += market_factor["confidence"]
            reasons.append(market_factor["reason"])

        # Normalize confidence
        confidence = min(1.0, confidence / 3.0 if reasons else 0.0)

        # Calculate expected costs
        expected_dark_cost = self._estimate_dark_pool_cost(order_value_usd)
        expected_lit_cost = float(order_value_usd) * current_spread_bps / 10000

        # Venue allocation
        if use_dark:
            venue_allocation = self._calculate_venue_allocation(order_value_usd, confidence)
            dark_pools = self._select_dark_pools(order_value_usd)
        else:
            dark_pools = []

        # Order type recommendation
        order_type = ("ICEBERG" if confidence > 0.7 else "VWAP") if use_dark else "LIMIT"

        return DarkPoolDecision(
            use_dark_pool=use_dark,
            confidence=confidence,
            reason="; ".join(reasons) if reasons else "Use lit exchange",
            venue_allocation=venue_allocation,
            expected_dark_cost_bps=expected_dark_cost,
            expected_lit_cost_bps=expected_lit_cost,
            dark_pool_names=dark_pools,
            order_type=order_type,
        )

    def _evaluate_size_factor(
        self,
        order_size: Decimal,
        adv: Decimal,
        order_value_usd: Decimal,
        participation_rate: Decimal,
    ) -> dict[str, any]:
        """Evaluate size factor for dark pool decision."""
        if participation_rate >= self.min_participation_rate:
            return {
                "passes": True,
                "confidence": 0.8,
                "reason": f"Order size ({participation_rate:.1%} of ADV) warrants dark pool",
            }
        elif order_value_usd >= self.min_order_size_usd:
            return {
                "passes": True,
                "confidence": 0.6,
                "reason": f"Order value (${order_value_usd:,.0f}) warrants dark pool",
            }
        else:
            return {
                "passes": False,
                "confidence": 0.0,
                "reason": "Order too small for dark pool benefits",
            }

    def _evaluate_information_leakage(
        self,
        risk_level: str,
        participation_rate: Decimal,
    ) -> dict[str, any]:
        """Evaluate information leakage risk."""
        threshold = self.INFORMATION_LEAKAGE_THRESHOLDS.get(risk_level, 0.5)

        # High participation + high leakage risk = use dark pool
        risk_score = float(participation_rate) * threshold

        if risk_score > 0.15:
            return {
                "use_dark": True,
                "confidence": min(1.0, risk_score * 3),
                "reason": f"High information leakage risk ({risk_level})",
            }
        else:
            return {
                "use_dark": False,
                "confidence": 0.0,
                "reason": "Low information leakage risk",
            }

    def _evaluate_market_conditions(
        self,
        spread_bps: float,
        volatility_percentile: float,
    ) -> dict[str, any]:
        """Evaluate market conditions for dark pool usage."""
        # Wide spread = dark pool attractive
        spread_factor = min(1.0, spread_bps / 20.0)  # 20 bps = max

        # High volatility = mixed signal
        # Some dark pools offer better prices in volatile conditions
        vol_factor = min(1.0, volatility_percentile / 80.0)

        combined_score = (spread_factor + vol_factor) / 2

        if combined_score > 0.5:
            return {
                "use_dark": True,
                "confidence": combined_score * 0.6,
                "reason": "Market conditions favor dark pool (wide spread/high vol)",
            }
        else:
            return {
                "use_dark": False,
                "confidence": 0.0,
                "reason": "Favorable lit market conditions",
            }

    def _estimate_dark_pool_cost(
        self,
        order_value_usd: Decimal,
    ) -> float:
        """Estimate dark pool execution cost in bps."""
        # Dark pools typically offer ~2-5 bps improvement vs lit
        # But have higher opportunity cost (partial fills)

        base_cost = self.DARK_POOL_DISCOUNT_BPS

        # Adjust for improvement rate
        expected_improvement = base_cost * self.DARK_POOL_IMPROVEMENT_RATE

        # Net cost (can be negative = improvement)
        net_cost = base_cost - expected_improvement

        return net_cost

    def _calculate_venue_allocation(
        self,
        order_value_usd: Decimal,
        confidence: float,
    ) -> dict[str, Decimal]:
        """Calculate venue allocation percentages."""
        # High confidence: more to dark pools
        dark_allocation = Decimal(str(confidence * 0.8))  # Max 80% to dark
        lit_allocation = Decimal("1") - dark_allocation

        # Allocate among dark pools
        qualified_pools = {
            k: v for k, v in self.dark_pools.items() if v["min_size_usd"] <= float(order_value_usd)
        }

        if qualified_pools:
            pool_allocation = dark_allocation / Decimal(str(len(qualified_pools)))
            allocation = {"lit_exchange": lit_allocation}

            for pool_name in qualified_pools:
                allocation[pool_name] = pool_allocation

            return allocation
        else:
            return {"lit_exchange": Decimal("1")}

    def _select_dark_pools(
        self,
        order_value_usd: Decimal,
    ) -> list[str]:
        """Select suitable dark pools for this order."""
        suitable = []

        for pool_id, pool_info in self.dark_pools.items():
            if pool_info["min_size_usd"] <= float(order_value_usd):
                suitable.append(f"{pool_info['name']} ({pool_id})")

        return suitable

    def compare_execution_venues(
        self,
        order_size: Decimal,
        adv: Decimal,
        order_value_usd: Decimal,
        current_spread_bps: float = 5.0,
    ) -> dict[str, dict[str, float]]:
        """
        Compare expected execution costs across venues.

        Returns cost estimates for:
        - Lit exchange (market impact + spread)
        - Dark pool (improvement - opportunity cost)
        - Internalization (if applicable)
        """
        # Lit exchange cost
        participation_impact = float(order_size / adv) ** 0.5 * 10  # sqrt impact
        lit_cost_bps = current_spread_bps / 2 + participation_impact

        # Dark pool cost
        dark_cost_bps = self._estimate_dark_pool_cost(order_value_usd)

        # Internalization (typical for retail order flow)
        internalization_bps = -1.5  # Typically 1-2 bps improvement

        results = {
            "lit_exchange": {
                "cost_bps": lit_cost_bps,
                "cost_usd": float(order_value_usd) * lit_cost_bps / 10000,
                "fill_probability": 1.0,
            },
            "dark_pool": {
                "cost_bps": dark_cost_bps,
                "cost_usd": float(order_value_usd) * dark_cost_bps / 10000,
                "fill_probability": 0.3,  # Typical fill rate
            },
            "internalization": {
                "cost_bps": internalization_bps,
                "cost_usd": float(order_value_usd) * internalization_bps / 10000,
                "fill_probability": 0.9,
            },
        }

        # Find best venue
        for _venue, metrics in results.items():
            expected_cost = metrics["cost_bps"] / metrics["fill_probability"]
            metrics["expected_cost_bps"] = expected_cost

        return results

    def optimize_dark_pool_split(
        self,
        total_order: Decimal,
        available_pools: list[str],
        min_fill_rate: float = 0.2,
    ) -> dict[str, Decimal]:
        """
        Optimize order split across dark pools.

        Args:
            total_order: Total order size
            available_pools: List of available dark pool IDs
            min_fill_rate: Minimum acceptable fill rate per pool

        Returns:
            Dict mapping pool_id -> order_size
        """
        allocation = {}
        remaining = total_order

        # Sort pools by fill rate (highest first)
        pool_fill_rates = [
            (pool, self.dark_pools[pool]["avg_fill_rate"])
            for pool in available_pools
            if pool in self.dark_pools
        ]
        pool_fill_rates.sort(key=lambda x: x[1], reverse=True)

        # Allocate to pools with acceptable fill rates
        for pool_id, fill_rate in pool_fill_rates:
            if fill_rate >= min_fill_rate and remaining > 0:
                # Allocate proportionally to fill rate
                pool_allocation = remaining * Decimal(str(fill_rate))
                allocation[pool_id] = pool_allocation
                remaining -= pool_allocation

        # If remaining, send to lit exchange
        if remaining > 0:
            allocation["lit_exchange"] = remaining

        return allocation


# Global singleton
_dark_pool_router: DarkPoolRouter = None


def get_dark_pool_router(
    min_participation_rate: Decimal | None = None,
    min_order_size_usd: Decimal | None = None,
) -> DarkPoolRouter:
    """Get or create global DarkPoolRouter instance."""
    if min_participation_rate is None:
        min_participation_rate = Decimal("0.10")
    if min_order_size_usd is None:
        min_order_size_usd = Decimal("100000")
    global _dark_pool_router
    if _dark_pool_router is None:
        _dark_pool_router = DarkPoolRouter(
            min_participation_rate=min_participation_rate,
            min_order_size_usd=min_order_size_usd,
        )

    return _dark_pool_router
