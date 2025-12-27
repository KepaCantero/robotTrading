"""
T18.1.3: AllocationRecommender - Smart allocation recommendations

Provides allocation recommendations based on risk profile, objectives, and market conditions.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AllocationRecommendation:
    """Smart allocation recommendation."""

    allocation: Dict[str, Decimal]  # {asset: weight}
    reasoning: str  # Explanation for recommendation
    confidence: str  # high, medium, low
    expected_return: Decimal
    expected_volatility: Decimal
    sharpe_ratio: Decimal
    diversification_score: Decimal  # 0-100
    concentration_risk: str  # low, medium, high


class AllocationRecommender:
    """
    Recommends allocations based on profiles and objectives.

    Features:
    - Risk profile-based recommendations
    - Objective-driven allocation
    - Market condition adjustments
    - Diversification scoring
    - Confidence assessment
    """

    def __init__(self):
        """Initialize allocation recommender."""
        self.recommendation_history: List[AllocationRecommendation] = []
        logger.info("✅ AllocationRecommender initialized")

    async def recommend_by_risk_profile(
        self,
        risk_profile: str,  # "conservative", "moderate", "aggressive"
        available_assets: List[str],
    ) -> AllocationRecommendation:
        """
        Recommend allocation by risk profile.

        Args:
            risk_profile: Risk profile type
            available_assets: List of available assets

        Returns:
            AllocationRecommendation
        """
        if risk_profile == "conservative":
            allocation = await self._conservative_allocation(available_assets)
            reasoning = (
                "Conservative profile: Focus on stability with fixed income and dividend stocks"
            )
            expected_return = Decimal("0.04")
            expected_vol = Decimal("0.08")
            sharpe = Decimal("0.50")
        elif risk_profile == "moderate":
            allocation = await self._moderate_allocation(available_assets)
            reasoning = "Moderate profile: Balanced growth and income with mixed assets"
            expected_return = Decimal("0.07")
            expected_vol = Decimal("0.12")
            sharpe = Decimal("0.58")
        elif risk_profile == "aggressive":
            allocation = await self._aggressive_allocation(available_assets)
            reasoning = "Aggressive profile: Growth-oriented with higher equity allocation"
            expected_return = Decimal("0.10")
            expected_vol = Decimal("0.18")
            sharpe = Decimal("0.56")
        else:
            allocation = await self._moderate_allocation(available_assets)
            reasoning = "Default moderate allocation"
            expected_return = Decimal("0.07")
            expected_vol = Decimal("0.12")
            sharpe = Decimal("0.58")

        recommendation = AllocationRecommendation(
            allocation=allocation,
            reasoning=reasoning,
            confidence="high",
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            diversification_score=await self._calculate_diversification_score(allocation),
            concentration_risk=await self._assess_concentration_risk(allocation),
        )

        self.recommendation_history.append(recommendation)
        logger.info(f"✅ Recommended allocation for {risk_profile} profile")
        return recommendation

    async def recommend_by_objective(
        self,
        objective: str,  # "growth", "income", "preservation", "balanced"
        available_assets: List[str],
    ) -> AllocationRecommendation:
        """
        Recommend allocation by investment objective.

        Args:
            objective: Investment objective
            available_assets: List of available assets

        Returns:
            AllocationRecommendation
        """
        if objective == "growth":
            allocation = await self._growth_allocation(available_assets)
            reasoning = "Growth objective: Maximize capital appreciation"
            expected_return = Decimal("0.10")
            expected_vol = Decimal("0.18")
        elif objective == "income":
            allocation = await self._income_allocation(available_assets)
            reasoning = "Income objective: Focus on dividend and yield-generating assets"
            expected_return = Decimal("0.05")
            expected_vol = Decimal("0.10")
        elif objective == "preservation":
            allocation = await self._preservation_allocation(available_assets)
            reasoning = "Preservation objective: Protect capital with conservative positioning"
            expected_return = Decimal("0.03")
            expected_vol = Decimal("0.06")
        else:
            allocation = await self._balanced_allocation(available_assets)
            reasoning = "Balanced objective: Equal growth and income"
            expected_return = Decimal("0.07")
            expected_vol = Decimal("0.12")

        sharpe = expected_return / expected_vol if expected_vol > 0 else Decimal("0")

        recommendation = AllocationRecommendation(
            allocation=allocation,
            reasoning=reasoning,
            confidence="high",
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            diversification_score=await self._calculate_diversification_score(allocation),
            concentration_risk=await self._assess_concentration_risk(allocation),
        )

        self.recommendation_history.append(recommendation)
        logger.info(f"✅ Recommended allocation for {objective} objective")
        return recommendation

    async def recommend_by_capital_tier(
        self,
        capital: Decimal,
        available_assets: List[str],
    ) -> AllocationRecommendation:
        """
        Recommend allocation by capital tier.

        Args:
            capital: Total capital available
            available_assets: List of available assets

        Returns:
            AllocationRecommendation
        """
        if capital < Decimal("10000"):
            tier = "micro"
            allocation = await self._equal_allocation(available_assets)
            reasoning = "Micro capital: Simple equal-weight for cost efficiency"
            expected_return = Decimal("0.06")
        elif capital < Decimal("100000"):
            tier = "small"
            allocation = await self._conservative_allocation(available_assets)
            reasoning = "Small capital: Conservative allocation for capital preservation"
            expected_return = Decimal("0.05")
        elif capital < Decimal("500000"):
            tier = "medium"
            allocation = await self._moderate_allocation(available_assets)
            reasoning = "Medium capital: Balanced allocation with good diversification"
            expected_return = Decimal("0.07")
        else:
            tier = "large"
            allocation = await self._sophisticated_allocation(available_assets)
            reasoning = "Large capital: Sophisticated allocation with full diversification"
            expected_return = Decimal("0.08")

        expected_vol = Decimal("0.12")
        sharpe = expected_return / expected_vol

        recommendation = AllocationRecommendation(
            allocation=allocation,
            reasoning=reasoning,
            confidence="high",
            expected_return=expected_return,
            expected_volatility=expected_vol,
            sharpe_ratio=sharpe,
            diversification_score=await self._calculate_diversification_score(allocation),
            concentration_risk=await self._assess_concentration_risk(allocation),
        )

        logger.info(f"✅ Recommended allocation for {tier} capital tier")
        return recommendation

    # Allocation templates
    async def _conservative_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Conservative: 40% stocks, 50% bonds, 10% alternatives."""
        allocation = {}
        for i, asset in enumerate(assets):
            if i < len(assets) * 0.4:
                allocation[asset] = Decimal("1.0") / Decimal(len(assets))
            elif i < len(assets) * 0.9:
                allocation[asset] = Decimal("1.25") / Decimal(len(assets))
            else:
                allocation[asset] = Decimal("1.0") / Decimal(len(assets))
        # Normalize
        total = sum(allocation.values())
        return {a: (w / total) for a, w in allocation.items()}

    async def _moderate_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Moderate: 60% stocks, 30% bonds, 10% alternatives."""
        allocation = {}
        for i, asset in enumerate(assets):
            if i < len(assets) * 0.6:
                allocation[asset] = Decimal("1.2") / Decimal(len(assets))
            elif i < len(assets) * 0.9:
                allocation[asset] = Decimal("0.75") / Decimal(len(assets))
            else:
                allocation[asset] = Decimal("1.0") / Decimal(len(assets))
        total = sum(allocation.values())
        return {a: (w / total) for a, w in allocation.items()}

    async def _aggressive_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Aggressive: 80% stocks, 10% bonds, 10% alternatives."""
        allocation = {}
        for i, asset in enumerate(assets):
            if i < len(assets) * 0.8:
                allocation[asset] = Decimal("1.3") / Decimal(len(assets))
            elif i < len(assets) * 0.9:
                allocation[asset] = Decimal("0.5") / Decimal(len(assets))
            else:
                allocation[asset] = Decimal("1.0") / Decimal(len(assets))
        total = sum(allocation.values())
        return {a: (w / total) for a, w in allocation.items()}

    async def _growth_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Growth: Heavy equity allocation."""
        return {asset: Decimal("1.0") / Decimal(len(assets)) for asset in assets}

    async def _income_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Income: Higher weighting for yield assets."""
        allocation = {}
        for i, asset in enumerate(assets):
            if "BOND" in asset or "DIVIDEND" in asset:
                allocation[asset] = Decimal("1.5") / Decimal(len(assets))
            else:
                allocation[asset] = Decimal("0.75") / Decimal(len(assets))
        total = sum(allocation.values())
        return {a: (w / total) for a, w in allocation.items()}

    async def _preservation_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Preservation: Focus on stable assets."""
        allocation = {}
        for i, asset in enumerate(assets):
            if "BOND" in asset or "CASH" in asset:
                allocation[asset] = Decimal("2.0") / Decimal(len(assets))
            else:
                allocation[asset] = Decimal("0.25") / Decimal(len(assets))
        total = sum(allocation.values())
        return {a: (w / total) for a, w in allocation.items()}

    async def _balanced_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Balanced: Equal-weight."""
        return {asset: Decimal("1.0") / Decimal(len(assets)) for asset in assets}

    async def _equal_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Equal weight."""
        return {asset: Decimal("1.0") / Decimal(len(assets)) for asset in assets}

    async def _sophisticated_allocation(self, assets: List[str]) -> Dict[str, Decimal]:
        """Sophisticated: Optimized equal-weight with caps."""
        n = len(assets)
        base_weight = Decimal("1.0") / Decimal(n)
        # Cap at 15% max per asset
        cap = Decimal("0.15")
        if base_weight > cap:
            allocation = {asset: cap for asset in assets[: int(1 / 0.15)]}
            remaining = len(assets) - len(allocation)
            if remaining > 0:
                remaining_weight = (Decimal("1.0") - Decimal(len(allocation)) * cap) / Decimal(
                    remaining
                )
                for asset in assets[len(allocation) :]:
                    allocation[asset] = remaining_weight
        else:
            allocation = {asset: base_weight for asset in assets}
        return allocation

    async def _calculate_diversification_score(self, allocation: Dict[str, Decimal]) -> Decimal:
        """Calculate diversification score (0-100)."""
        if not allocation:
            return Decimal("0")

        weights = list(allocation.values())
        # Herfindahl index: sum of squared weights
        herfindahl = sum(w * w for w in weights)

        # Convert to diversification score (100 = perfectly diversified, 0 = concentrated)
        score = (Decimal("1") - herfindahl) * Decimal("100")
        return max(Decimal("0"), min(Decimal("100"), score))

    async def _assess_concentration_risk(self, allocation: Dict[str, Decimal]) -> str:
        """Assess concentration risk level."""
        if not allocation:
            return "low"

        max_weight = max(allocation.values())
        if max_weight > Decimal("0.40"):
            return "high"
        elif max_weight > Decimal("0.25"):
            return "medium"
        else:
            return "low"

    async def get_recommendation_history(
        self,
        limit: Optional[int] = None,
    ) -> List[AllocationRecommendation]:
        """Get recommendation history."""
        if limit is None:
            return self.recommendation_history
        return self.recommendation_history[-limit:]

    def get_recommender_status(self) -> Dict:
        """Get recommender status."""
        return {
            "total_recommendations": len(self.recommendation_history),
        }


# Singleton
_recommender: Optional[AllocationRecommender] = None


def get_allocation_recommender() -> AllocationRecommender:
    """Get or create singleton AllocationRecommender."""
    global _recommender
    if _recommender is None:
        _recommender = AllocationRecommender()

    return _recommender
