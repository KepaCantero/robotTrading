"""
T19.1.2: StrategyRanker - Ranks and compares multiple strategies

Provides ranking and comparison of strategies based on scored metrics.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .strategy_scorer import StrategyScore

logger = logging.getLogger(__name__)


@dataclass
class RankedStrategy:
    """Strategy with rank and comparison metrics."""

    rank: int
    strategy_name: str
    overall_score: Decimal
    return_score: Decimal
    risk_score: Decimal
    stability_score: Decimal
    consistency_score: Decimal
    percentile: Decimal  # 0-100, compared to other strategies


class StrategyRanker:
    """
    Ranks and compares multiple strategies.

    Features:
    - Multi-dimensional ranking
    - Percentile calculation
    - Comparative analysis
    - Best strategy identification
    - Ranking history
    """

    def __init__(self):
        """Initialize strategy ranker."""
        self.ranking_history: dict[str, list[RankedStrategy]] = {}
        self.current_ranking: list[RankedStrategy] = []
        logger.info("✅ StrategyRanker initialized")

    async def rank_strategies(
        self,
        scores: list["StrategyScore"],  # From StrategyScorer
        metric: str = "overall_score",
    ) -> list[RankedStrategy]:
        """
        Rank strategies by a specific metric.

        Args:
            scores: List of StrategyScore objects
            metric: Metric to rank by (overall_score, return_score, risk_score, etc.)

        Returns:
            List of RankedStrategy objects sorted by metric
        """
        if not scores:
            return []

        # Sort by specified metric
        sorted_scores = sorted(
            scores,
            key=lambda s: getattr(s, metric),
            reverse=True,
        )

        # Calculate percentiles
        ranked = []
        for rank, score in enumerate(sorted_scores, start=1):
            percentile = Decimal("100") * (
                Decimal("1") - Decimal(rank - 1) / Decimal(len(sorted_scores))
            )

            ranked_strategy = RankedStrategy(
                rank=rank,
                strategy_name=score.strategy_name,
                overall_score=score.overall_score,
                return_score=score.return_score,
                risk_score=score.risk_score,
                stability_score=score.stability_score,
                consistency_score=score.consistency_score,
                percentile=percentile,
            )
            ranked.append(ranked_strategy)

        self.current_ranking = ranked
        self.ranking_history[metric] = ranked

        logger.info(f"✅ Ranked {len(ranked)} strategies by {metric}")
        return ranked

    async def get_top_strategies(
        self,
        n: int = 5,
    ) -> list[RankedStrategy]:
        """
        Get top N strategies from current ranking.

        Args:
            n: Number of top strategies to return

        Returns:
            Top N strategies
        """
        return self.current_ranking[:n]

    async def get_bottom_strategies(
        self,
        n: int = 5,
    ) -> list[RankedStrategy]:
        """
        Get bottom N strategies from current ranking.

        Args:
            n: Number of bottom strategies to return

        Returns:
            Bottom N strategies
        """
        return self.current_ranking[-n:]

    async def get_best_strategy(self) -> Optional[RankedStrategy]:
        """Get best ranked strategy."""
        if self.current_ranking:
            return self.current_ranking[0]
        return None

    async def get_worst_strategy(self) -> Optional[RankedStrategy]:
        """Get worst ranked strategy."""
        if self.current_ranking:
            return self.current_ranking[-1]
        return None

    async def compare_strategies(
        self,
        strategy_names: list[str],
    ) -> list[RankedStrategy]:
        """
        Get comparison of specific strategies.

        Args:
            strategy_names: List of strategy names to compare

        Returns:
            Comparison data for specified strategies
        """
        comparison = [s for s in self.current_ranking if s.strategy_name in strategy_names]
        return comparison

    async def get_ranking_gaps(self) -> dict[str, Decimal]:
        """
        Calculate gaps between consecutive ranked strategies.

        Returns:
            Dictionary with gaps between each rank
        """
        gaps = {}
        for i in range(len(self.current_ranking) - 1):
            current = self.current_ranking[i]
            next_strategy = self.current_ranking[i + 1]
            gap = current.overall_score - next_strategy.overall_score
            gaps[f"rank_{i + 1}_to_{i + 2}"] = gap

        return gaps

    async def get_performance_clusters(
        self,
        num_clusters: int = 3,
    ) -> dict[str, list[RankedStrategy]]:
        """
        Cluster strategies into performance groups.

        Args:
            num_clusters: Number of clusters (good, medium, poor)

        Returns:
            Clustered strategies
        """
        if not self.current_ranking:
            return {}

        total = len(self.current_ranking)
        cluster_size = max(1, total // num_clusters)

        clusters = {}
        cluster_names = ["excellent", "good", "fair", "poor", "very_poor"]

        for i in range(num_clusters):
            start_idx = i * cluster_size
            end_idx = start_idx + cluster_size if i < num_clusters - 1 else total
            cluster_name = cluster_names[i] if i < len(cluster_names) else f"cluster_{i}"
            clusters[cluster_name] = self.current_ranking[start_idx:end_idx]

        return clusters

    async def get_pairwise_comparison(
        self,
        strategy1: str,
        strategy2: str,
    ) -> Optional[dict]:
        """
        Compare two strategies pairwise.

        Args:
            strategy1: First strategy name
            strategy2: Second strategy name

        Returns:
            Comparison dictionary
        """
        s1 = next((s for s in self.current_ranking if s.strategy_name == strategy1), None)
        s2 = next((s for s in self.current_ranking if s.strategy_name == strategy2), None)

        if not s1 or not s2:
            return None

        return {
            "better_overall": strategy1 if s1.overall_score > s2.overall_score else strategy2,
            "score_difference": abs(s1.overall_score - s2.overall_score),
            "better_return": strategy1 if s1.return_score > s2.return_score else strategy2,
            "better_risk": strategy1 if s1.risk_score > s2.risk_score else strategy2,
            "better_stability": strategy1 if s1.stability_score > s2.stability_score else strategy2,
            "better_consistency": (
                strategy1 if s1.consistency_score > s2.consistency_score else strategy2
            ),
        }

    def get_ranker_status(self) -> dict:
        """Get ranker status."""
        return {
            "current_ranking_count": len(self.current_ranking),
            "ranking_history_entries": len(self.ranking_history),
        }


# Singleton
_ranker: Optional[StrategyRanker] = None


def get_strategy_ranker() -> StrategyRanker:
    """Get or create singleton StrategyRanker."""
    global _ranker
    if _ranker is None:
        _ranker = StrategyRanker()

    return _ranker
