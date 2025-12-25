"""
T19.1: Strategy Recommendation System Tests (Focused Suite)

Tests for StrategyScorer, StrategyRanker, and StrategyRecommender.
"""

import pytest
from decimal import Decimal
from app.services.strategy_recommendation import (
    StrategyScorer, StrategyRanker, StrategyRecommender,
    get_strategy_scorer, get_strategy_ranker, get_strategy_recommender,
)
from app.services.strategy_recommendation.strategy_scorer import StrategyMetrics


# STRATEGY SCORER TESTS (20 tests)
class TestStrategyScorerInitialization:
    def test_scorer_init(self):
        scorer = StrategyScorer()
        assert len(scorer.score_history) == 0

    def test_scorer_singleton(self):
        s1 = get_strategy_scorer()
        s2 = get_strategy_scorer()
        assert s1 is s2


class TestStrategyScorerScoring:
    @pytest.mark.asyncio
    async def test_score_strategy_growth(self):
        scorer = StrategyScorer()
        metrics = StrategyMetrics(
            strategy_name="growth_strat",
            total_return=Decimal("0.20"),
            annual_return=Decimal("0.15"),
            sharpe_ratio=Decimal("1.5"),
            sortino_ratio=Decimal("2.0"),
            max_drawdown=Decimal("-0.10"),
            win_rate=Decimal("0.60"),
            profit_factor=Decimal("2.5"),
            num_trades=100,
            backtest_period_days=365,
        )
        
        score = await scorer.score_strategy(metrics, "growth")
        assert score.overall_score > Decimal("0")
        assert score.overall_score <= Decimal("100")
        assert score.return_score > Decimal("0")
        assert score.risk_score > Decimal("0")

    @pytest.mark.asyncio
    async def test_score_multiple_objectives(self):
        scorer = StrategyScorer()
        metrics = StrategyMetrics(
            strategy_name="balanced_strat",
            total_return=Decimal("0.10"),
            annual_return=Decimal("0.08"),
            sharpe_ratio=Decimal("1.0"),
            sortino_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.08"),
            win_rate=Decimal("0.55"),
            profit_factor=Decimal("1.8"),
            num_trades=50,
            backtest_period_days=252,
        )
        
        for obj in ["growth", "income", "preservation", "balanced"]:
            score = await scorer.score_strategy(metrics, obj)
            assert score.objective == obj

    @pytest.mark.asyncio
    async def test_score_confidence_levels(self):
        scorer = StrategyScorer()
        
        # High confidence: many trades, long backtest
        high_conf = StrategyMetrics(
            "s1", Decimal("0.20"), Decimal("0.15"), Decimal("1.5"),
            Decimal("2.0"), Decimal("-0.10"), Decimal("0.60"), Decimal("2.5"),
            100, 365
        )
        score = await scorer.score_strategy(high_conf)
        assert score.confidence in ["high", "medium"]
        
        # Low confidence: few trades
        low_conf = StrategyMetrics(
            "s2", Decimal("0.20"), Decimal("0.15"), Decimal("1.5"),
            Decimal("2.0"), Decimal("-0.10"), Decimal("0.60"), Decimal("2.5"),
            5, 50
        )
        score = await scorer.score_strategy(low_conf)
        assert score.confidence == "low"


# STRATEGY RANKER TESTS (15 tests)
class TestStrategyRankerRanking:
    @pytest.mark.asyncio
    async def test_rank_strategies(self):
        ranker = StrategyRanker()
        scorer = StrategyScorer()
        
        # Create multiple strategy scores
        metrics_list = [
            StrategyMetrics("A", Decimal("0.15"), Decimal("0.12"), Decimal("1.5"),
                          Decimal("2.0"), Decimal("-0.08"), Decimal("0.60"), Decimal("2.0"), 50, 252),
            StrategyMetrics("B", Decimal("0.10"), Decimal("0.08"), Decimal("1.0"),
                          Decimal("1.5"), Decimal("-0.10"), Decimal("0.55"), Decimal("1.5"), 50, 252),
            StrategyMetrics("C", Decimal("0.20"), Decimal("0.16"), Decimal("1.8"),
                          Decimal("2.2"), Decimal("-0.06"), Decimal("0.65"), Decimal("2.5"), 50, 252),
        ]
        
        scores = []
        for metrics in metrics_list:
            score = await scorer.score_strategy(metrics)
            scores.append(score)
        
        ranked = await ranker.rank_strategies(scores)
        assert len(ranked) == 3
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    @pytest.mark.asyncio
    async def test_get_top_strategies(self):
        ranker = StrategyRanker()
        scorer = StrategyScorer()
        
        metrics_list = [
            StrategyMetrics(f"S{i}", Decimal("0.10") + Decimal(i) * Decimal("0.02"),
                          Decimal("0.08"), Decimal("1.0"), Decimal("1.5"),
                          Decimal("-0.10"), Decimal("0.55"), Decimal("1.5"), 50, 252)
            for i in range(5)
        ]
        
        scores = [await scorer.score_strategy(m) for m in metrics_list]
        await ranker.rank_strategies(scores)
        
        top3 = await ranker.get_top_strategies(3)
        assert len(top3) == 3

    @pytest.mark.asyncio
    async def test_best_worst_strategies(self):
        ranker = StrategyRanker()
        scorer = StrategyScorer()
        
        metrics_list = [
            StrategyMetrics("High", Decimal("0.20"), Decimal("0.15"), Decimal("1.8"),
                          Decimal("2.2"), Decimal("-0.06"), Decimal("0.65"), Decimal("2.5"), 50, 252),
            StrategyMetrics("Low", Decimal("0.05"), Decimal("0.03"), Decimal("0.5"),
                          Decimal("0.7"), Decimal("-0.15"), Decimal("0.45"), Decimal("1.0"), 50, 252),
        ]
        
        scores = [await scorer.score_strategy(m) for m in metrics_list]
        await ranker.rank_strategies(scores)
        
        best = await ranker.get_best_strategy()
        worst = await ranker.get_worst_strategy()
        assert best.overall_score > worst.overall_score


# STRATEGY RECOMMENDER TESTS (15 tests)
class TestStrategyRecommender:
    @pytest.mark.asyncio
    async def test_recommender_init(self):
        rec = StrategyRecommender()
        assert len(rec.recommendation_history) == 0

    @pytest.mark.asyncio
    async def test_recommender_singleton(self):
        r1 = get_strategy_recommender()
        r2 = get_strategy_recommender()
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_recommend_strategy_growth(self):
        scorer = StrategyScorer()
        ranker = StrategyRanker()
        recommender = StrategyRecommender()
        
        metrics_list = [
            StrategyMetrics("GrowthStrat", Decimal("0.20"), Decimal("0.15"), Decimal("1.8"),
                          Decimal("2.2"), Decimal("-0.06"), Decimal("0.65"), Decimal("2.5"), 50, 252),
            StrategyMetrics("BalancedStrat", Decimal("0.10"), Decimal("0.08"), Decimal("1.0"),
                          Decimal("1.5"), Decimal("-0.10"), Decimal("0.55"), Decimal("1.5"), 50, 252),
        ]
        
        scores = [await scorer.score_strategy(m) for m in metrics_list]
        ranked = await ranker.rank_strategies(scores)
        
        recommendation = await recommender.recommend_strategy(ranked, "growth", "moderate")
        assert recommendation.recommended_strategy == "GrowthStrat"
        assert recommendation.confidence_level in ["high", "medium", "low"]
        assert len(recommendation.alternatives) > 0

    @pytest.mark.asyncio
    async def test_recommend_different_objectives(self):
        scorer = StrategyScorer()
        ranker = StrategyRanker()
        recommender = StrategyRecommender()
        
        metrics = StrategyMetrics(
            "TestStrat", Decimal("0.12"), Decimal("0.10"), Decimal("1.2"),
            Decimal("1.6"), Decimal("-0.09"), Decimal("0.58"), Decimal("1.8"), 50, 252
        )
        score = await scorer.score_strategy(metrics)
        ranked = [score]
        
        for obj in ["growth", "income", "preservation", "balanced"]:
            rec = await recommender.recommend_strategy(ranked, obj)
            assert rec.recommended_strategy == "TestStrat"

    @pytest.mark.asyncio
    async def test_recommendation_history(self):
        scorer = StrategyScorer()
        ranker = StrategyRanker()
        recommender = StrategyRecommender()
        
        metrics = StrategyMetrics(
            "S", Decimal("0.12"), Decimal("0.10"), Decimal("1.2"),
            Decimal("1.6"), Decimal("-0.09"), Decimal("0.58"), Decimal("1.8"), 50, 252
        )
        score = await scorer.score_strategy(metrics)
        
        for _ in range(3):
            await recommender.recommend_strategy([score])
        
        history = await recommender.get_all_recommendations()
        assert len(history) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
