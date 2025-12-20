"""
Currency Hedging Engine - TASK-5.5-CURRENCY-HEDGING

Calculates hedge recommendations, ratios, and costs for multi-currency portfolios.
Provides core hedging logic independent of portfolio service.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, Field

from app.models.portfolio import Portfolio
from app.services.forex_data_service import get_forex_fetcher

logger = logging.getLogger(__name__)


class HedgeUrgency(str, Enum):
    """Urgency levels for hedging recommendations."""

    IMMEDIATE = "immediate"
    NORMAL = "normal"
    LOW = "low"


class HedgeRecommendation(BaseModel):
    """Recommendation for hedging a currency exposure."""

    currency: str = Field(..., description="Currency code (e.g., EUR)")
    exposure_amount: Decimal = Field(..., description="Total exposure in base currency")
    forex_pair: str = Field(..., description="Forex pair to use for hedge (e.g., EUR/USD)")
    contract_size: Decimal = Field(..., description="Size of hedge position")
    hedge_ratio: Decimal = Field(..., description="Ratio of exposure to hedge (0-1)")
    duration_days: int = Field(default=30, description="Duration of hedge in days")
    estimated_cost_bps: Decimal = Field(..., description="Estimated cost in basis points")
    urgency: HedgeUrgency = Field(..., description="Urgency of hedging")
    rationale: str = Field(..., description="Explanation for recommendation")


class CurrencyHedgingEngine:
    """
    Engine for calculating hedging decisions and recommendations.

    Provides:
    - Currency exposure calculation
    - Hedge recommendation generation
    - Hedge ratio calculation
    - Cost estimation
    """

    def __init__(self, config: Dict = None):
        """
        Initialize hedging engine.

        Args:
            config: Optional config dict with thresholds
        """
        # Default configuration
        self.config = config or {
            "single_currency_max": 0.25,
            "total_fx_max": 0.50,
            "minimum_exposure": Decimal("50000"),
            "max_cost_bps": Decimal("10"),
            "hedge_strategy": "partial",
            "partial_hedge_percentage": 0.5,
        }

        self.forex_fetcher = get_forex_fetcher()
        self.total_hedges_generated = 0

    def calculate_currency_exposure(
        self, portfolio: Portfolio, base_currency: str = "USD"
    ) -> Dict[str, Decimal]:
        """
        Calculate aggregate currency exposure per non-base currency.

        Args:
            portfolio: Portfolio to analyze
            base_currency: Base currency for conversion

        Returns:
            Dict[currency, notional_amount]: Currency exposures in base currency
        """
        logger.debug(f"Calculating currency exposure for {len(portfolio.positions)} positions")
        exposure: Dict[str, Decimal] = {}

        for position in portfolio.positions:
            # Skip base currency and hedge positions
            if position.currency == base_currency or position.hedging.is_hedge:
                continue

            # Calculate position value in base currency
            position_value = position.market_value

            # Aggregate by currency
            if position.currency not in exposure:
                exposure[position.currency] = Decimal("0")
            exposure[position.currency] += position_value

        logger.info(f"Currency exposure: {len(exposure)} non-base currencies")
        return exposure

    def calculate_hedge_recommendations(
        self,
        portfolio: Portfolio,
        base_currency: str = "USD",
    ) -> List[HedgeRecommendation]:
        """
        Calculate hedge recommendations for portfolio.

        Args:
            portfolio: Portfolio to hedge
            base_currency: Base currency

        Returns:
            List of hedge recommendations
        """
        logger.debug("Calculating hedge recommendations")
        recommendations: List[HedgeRecommendation] = []

        # Get current exposures
        exposure = self.calculate_currency_exposure(portfolio, base_currency)
        if not exposure:
            logger.debug("No non-base currency exposure, no hedges needed")
            return []

        # Get forex data
        forex_pairs = self.forex_fetcher.get_available_pairs()
        correlations = self.forex_fetcher.get_correlations(base_currency)

        # Total portfolio value
        total_value = portfolio.total_equity

        # Calculate recommendations for each currency
        for currency, amount in sorted(exposure.items(), key=lambda x: x[1], reverse=True):
            # Check if exposure exceeds thresholds
            exposure_pct = amount / total_value if total_value > 0 else Decimal("0")

            if amount < self.config["minimum_exposure"]:
                logger.debug(f"  {currency}: {amount} < minimum, skipping")
                continue

            if exposure_pct < Decimal(str(self.config["single_currency_max"])):
                logger.debug(f"  {currency}: {exposure_pct} < max threshold, checking...")

            # Determine urgency
            if exposure_pct > Decimal("0.35"):
                urgency = HedgeUrgency.IMMEDIATE
            elif exposure_pct > Decimal("0.25"):
                urgency = HedgeUrgency.NORMAL
            else:
                urgency = HedgeUrgency.LOW

            # Calculate hedge ratio
            correlation = correlations.get(currency, Decimal("0.5"))
            hedge_ratio = self._calculate_hedge_ratio(exposure_pct, correlation, urgency)

            if hedge_ratio == Decimal("0"):
                logger.debug(f"  {currency}: hedge_ratio = 0, skipping")
                continue

            # Get forex pair
            forex_pair = forex_pairs.get(currency, f"{currency}/USD")

            # Calculate contract size
            contract_size = amount * hedge_ratio

            # Estimate cost
            cost_bps = self._estimate_hedge_cost(forex_pair, contract_size)

            # Check cost limit
            if cost_bps > self.config["max_cost_bps"] and self.config.get("enforce_cost_limit"):
                logger.warning(f"  {currency}: cost {cost_bps} bps > limit, skipping")
                continue

            # Create recommendation
            rec = HedgeRecommendation(
                currency=currency,
                exposure_amount=amount,
                forex_pair=forex_pair,
                contract_size=contract_size,
                hedge_ratio=hedge_ratio,
                duration_days=int(self.config.get("rolling_window_days", 30)),
                estimated_cost_bps=cost_bps,
                urgency=urgency,
                rationale=self._generate_rationale(
                    currency, amount, exposure_pct, correlation, hedge_ratio
                ),
            )

            recommendations.append(rec)
            logger.info(f"  {currency}: recommendation generated ({urgency.value})")

        self.total_hedges_generated += len(recommendations)
        logger.info(f"Total recommendations: {len(recommendations)}")
        return recommendations

    def _calculate_hedge_ratio(
        self,
        exposure_pct: Decimal,
        correlation: Decimal,
        urgency: HedgeUrgency,
    ) -> Decimal:
        """
        Calculate hedge ratio based on exposure and correlation.

        Args:
            exposure_pct: Exposure as percentage of portfolio
            correlation: Correlation with base currency
            urgency: Urgency level

        Returns:
            Hedge ratio (0-1)
        """
        strategy = self.config.get("hedge_strategy", "partial")

        if strategy == "full":
            # Full hedge
            base_ratio = Decimal("1.0")
        elif strategy == "partial":
            # Partial hedge based on configuration
            base_ratio = Decimal(str(self.config.get("partial_hedge_percentage", 0.5)))
        elif strategy == "rolling":
            # Rolling hedge adjusted by urgency
            base_ratio = Decimal("0.5")
            if urgency == HedgeUrgency.IMMEDIATE:
                base_ratio = Decimal("0.8")
            elif urgency == HedgeUrgency.NORMAL:
                base_ratio = Decimal("0.6")
        else:
            base_ratio = Decimal("0.5")

        # Adjust by correlation
        # Higher correlation = less hedge needed
        adjusted_ratio = base_ratio * (Decimal("1.0") - correlation * Decimal("0.5"))

        # Clamp to [0, 1]
        return max(Decimal("0"), min(Decimal("1.0"), adjusted_ratio))

    def _estimate_hedge_cost(self, forex_pair: str, contract_size: Decimal) -> Decimal:
        """
        Estimate cost of hedging in basis points.

        Args:
            forex_pair: Forex pair (e.g., "EUR/USD")
            contract_size: Size of hedge

        Returns:
            Cost in basis points
        """
        # Get bid-ask spread
        spread_bps = self.forex_fetcher.get_bid_ask_spread(forex_pair)

        # Assume 0.5x spread for execution
        execution_cost = spread_bps * Decimal("0.5")

        # Add slippage estimate (0.5 bps base)
        slippage = Decimal("0.5")

        # Scale by contract size (larger contracts may have better rates)
        size_factor = Decimal("1.0")
        if contract_size > Decimal("1000000"):
            size_factor = Decimal("0.8")

        total_cost = (execution_cost + slippage) * size_factor

        return min(total_cost, Decimal("100"))  # Cap at 100 bps

    def _generate_rationale(
        self,
        currency: str,
        amount: Decimal,
        exposure_pct: Decimal,
        correlation: Decimal,
        hedge_ratio: Decimal,
    ) -> str:
        """Generate human-readable rationale for recommendation."""
        return (
            f"Hedge {currency} exposure of {amount:,.0f} "
            f"({exposure_pct:.1%} of portfolio) with correlation {correlation:.2f} "
            f"using hedge ratio {hedge_ratio:.2%}"
        )

    def get_statistics(self) -> Dict[str, int]:
        """Get hedging engine statistics."""
        return {
            "total_recommendations_generated": self.total_hedges_generated,
        }
