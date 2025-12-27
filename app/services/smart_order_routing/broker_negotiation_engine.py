"""
T2.1.1 - Broker Negotiation Engine

Negotiates commission rates based on account volume and asset class.
Implements tiered commission structure: retail → semi_pro → pro → institutional
"""

import logging
from decimal import Decimal
from typing import Dict

logger = logging.getLogger(__name__)


class BrokerNegotiationEngine:
    """
    Negotiates commission rates based on trading volume and account tier.

    Provides tiered commission rates that decrease with larger volumes,
    with additional adjustments for different asset classes.

    Commission Tiers:
    - Retail (<€50k): 0.1% (100 bps)
    - Semi-pro (€50k-€250k): 0.05% (50 bps)
    - Pro (€250k-€1M): 0.03% (30 bps)
    - Institutional (€1M+): 0.02% (20 bps)
    """

    # Base commission rates for each tier
    COMMISSION_TIERS = {
        "retail": Decimal("0.001"),  # 0.1%
        "semi_pro": Decimal("0.0005"),  # 0.05%
        "pro": Decimal("0.0003"),  # 0.03%
        "institutional": Decimal("0.0002"),  # 0.02%
    }

    # Volume thresholds for tier qualification
    VOLUME_THRESHOLDS = {
        "institutional": Decimal("1000000"),  # €1M+
        "pro": Decimal("250000"),  # €250k-€1M
        "semi_pro": Decimal("50000"),  # €50k-€250k
        "retail": Decimal("0"),  # <€50k
    }

    # Asset-class adjustment multipliers
    ASSET_CLASS_ADJUSTMENTS = {
        "equity": Decimal("1.0"),  # No adjustment
        "crypto": Decimal("1.5"),  # 50% premium (higher risk)
        "forex": Decimal("0.5"),  # 50% discount (higher volume)
        "commodity": Decimal("1.2"),  # 20% premium
        "bond": Decimal("0.7"),  # 30% discount
    }

    def __init__(self):
        """Initialize negotiation engine with tier structure."""
        logger.info("BrokerNegotiationEngine initialized with tiered commission structure")

    def get_rate_for_volume(
        self,
        symbol: str,
        volume_usd: Decimal,
        asset_class: str = "equity",
        account_tier: str = None,
    ) -> Decimal:
        """
        Get negotiated commission rate for a trade.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            volume_usd: Order volume in EUR/USD
            asset_class: Type of asset (equity, crypto, forex, commodity, bond)
            account_tier: Optional explicit tier (overrides volume calculation)

        Returns:
            Commission rate as decimal (e.g., 0.001 = 0.1%)

        Example:
            >>> engine = BrokerNegotiationEngine()
            >>> rate = engine.get_rate_for_volume("AAPL", Decimal("100000"))
            >>> # Returns Decimal("0.0003") = 0.03% for €100k equity trade
        """

        # Determine tier
        if account_tier:
            tier = account_tier
        else:
            tier = self._get_tier_for_volume(volume_usd)

        logger.debug(f"Volume €{volume_usd:,.0f} → Tier: {tier}")

        # Get base rate for tier
        base_rate = self.COMMISSION_TIERS.get(tier, Decimal("0.001"))

        # Apply asset-class adjustment
        adjustment = self.ASSET_CLASS_ADJUSTMENTS.get(asset_class, Decimal("1.0"))
        final_rate = base_rate * adjustment

        logger.info(
            f"Commission negotiation: {symbol} €{volume_usd:,.0f} "
            f"({asset_class}): {tier} tier, {final_rate:.4%}"
        )

        return final_rate

    def _get_tier_for_volume(self, volume_usd: Decimal) -> str:
        """
        Determine account tier based on trading volume.

        Args:
            volume_usd: Trade size in EUR/USD

        Returns:
            Tier name: retail | semi_pro | pro | institutional
        """

        volume_usd = Decimal(str(volume_usd))  # Ensure Decimal

        if volume_usd >= self.VOLUME_THRESHOLDS["institutional"]:
            return "institutional"
        elif volume_usd >= self.VOLUME_THRESHOLDS["pro"]:
            return "pro"
        elif volume_usd >= self.VOLUME_THRESHOLDS["semi_pro"]:
            return "semi_pro"
        else:
            return "retail"

    def get_all_tiers(self) -> Dict[str, Dict]:
        """
        Get all available commission tiers.

        Returns:
            Dict mapping tier name to {rate, min_volume}
        """

        return {
            tier: {
                "rate": self.COMMISSION_TIERS[tier],
                "min_volume": self.VOLUME_THRESHOLDS[tier],
            }
            for tier in self.COMMISSION_TIERS.keys()
        }

    def estimate_commission_savings(
        self,
        symbol: str,
        volume_usd: Decimal,
        asset_class: str = "equity",
    ) -> Dict[str, Decimal]:
        """
        Compare commission costs across tiers.

        Shows how much could be saved by scaling to higher tiers.

        Returns:
            Dict with commission for each tier and savings calculations
        """

        commission_costs = {}
        retail_cost = self.COMMISSION_TIERS["retail"] * volume_usd

        for tier in ["retail", "semi_pro", "pro", "institutional"]:
            base_rate = self.COMMISSION_TIERS[tier]
            adjustment = self.ASSET_CLASS_ADJUSTMENTS.get(asset_class, Decimal("1.0"))
            rate = base_rate * adjustment
            cost = rate * volume_usd
            savings = retail_cost - cost

            commission_costs[tier] = {
                "rate": rate,
                "cost": cost,
                "savings_vs_retail": savings,
                "min_volume": self.VOLUME_THRESHOLDS[tier],
            }

        return commission_costs


# Global singleton
_broker_negotiation_engine: BrokerNegotiationEngine = None


def get_broker_negotiation_engine() -> BrokerNegotiationEngine:
    """Get or create global BrokerNegotiationEngine instance."""
    global _broker_negotiation_engine
    if _broker_negotiation_engine is None:
        _broker_negotiation_engine = BrokerNegotiationEngine()
    return _broker_negotiation_engine
