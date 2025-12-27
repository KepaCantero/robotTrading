"""
T6.1: StrategyRecommender Tests

Tests for objective-driven strategy recommendation and scoring.
"""

from decimal import Decimal

import pytest

from app.services.strategy_recommender import (
    StrategyRecommendationRequest,
    StrategyRecommender,
    get_strategy_recommender,
)


# STRATEGY RECOMMENDER INITIALIZATION TESTS
class TestStrategyRecommenderInitialization:
    def test_recommender_init(self):
        """Test recommender initialization."""
        recommender = StrategyRecommender()
        assert len(recommender.recommendation_history) == 0

    def test_recommender_singleton(self):
        """Test recommender singleton pattern."""
        r1 = get_strategy_recommender()
        r2 = get_strategy_recommender()
        assert r1 is r2

    def test_recommender_status(self):
        """Test recommender status reporting."""
        recommender = StrategyRecommender()
        status = recommender.get_recommender_status()

        assert "total_recommendations" in status
        assert "successful_recommendations" in status
        assert "average_score" in status


# OBJECTIVE WEIGHTS TESTS
class TestObjectiveWeights:
    def test_get_weights_capital_maximization(self):
        """Test weights for capital maximization objective."""
        recommender = StrategyRecommender()
        weights = recommender._get_objective_weights("maximizar_capital")

        assert weights.sharpe_weight == Decimal("0.60")
        assert weights.return_weight == Decimal("0.30")
        assert weights.sortino_weight == Decimal("0.10")

    def test_get_weights_dividend_focus(self):
        """Test weights for dividend objective."""
        recommender = StrategyRecommender()
        weights = recommender._get_objective_weights("maximizar_dividendos")

        assert weights.dividend_yield_weight == Decimal("0.50")
        assert weights.sharpe_weight == Decimal("0.30")

    def test_get_weights_preservation(self):
        """Test weights for capital preservation objective."""
        recommender = StrategyRecommender()
        weights = recommender._get_objective_weights("capital_preservation")

        assert weights.drawdown_weight == Decimal("0.50")
        assert weights.sharpe_weight == Decimal("0.40")

    def test_get_weights_balanced_growth(self):
        """Test weights for balanced growth objective."""
        recommender = StrategyRecommender()
        weights = recommender._get_objective_weights("balanced_growth")

        assert weights.sharpe_weight == Decimal("0.40")
        assert weights.return_weight == Decimal("0.30")
        assert weights.drawdown_weight == Decimal("0.30")


# COMPONENT SCORING TESTS
class TestComponentScoring:
    @pytest.mark.asyncio
    async def test_score_excellent_strategy(self):
        """Test scoring of excellent strategy."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_excellent",
            input_id="user_001",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("2.0"),
            annual_return_pct=Decimal("20"),
            max_drawdown_pct=Decimal("5"),
            sortino_ratio=Decimal("2.5"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert result.overall_score >= Decimal("80")
        assert result.recommendation_status == "STRONG_BUY"

    @pytest.mark.asyncio
    async def test_score_average_strategy(self):
        """Test scoring of average strategy."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_average",
            input_id="user_002",
            objective="balanced_growth",
            sharpe_ratio=Decimal("1.0"),
            annual_return_pct=Decimal("10"),
            max_drawdown_pct=Decimal("15"),
            sortino_ratio=Decimal("1.2"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert Decimal("40") < result.overall_score < Decimal("70")

    @pytest.mark.asyncio
    async def test_score_poor_strategy(self):
        """Test scoring of poor strategy."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_poor",
            input_id="user_003",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("0.3"),
            annual_return_pct=Decimal("2"),
            max_drawdown_pct=Decimal("40"),
            sortino_ratio=Decimal("0.5"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert result.overall_score < Decimal("40")


# RECOMMENDATION STATUS TESTS
class TestRecommendationStatus:
    @pytest.mark.asyncio
    async def test_strong_buy_threshold(self):
        """Test STRONG_BUY recommendation (score >= 85)."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_strong_buy",
            input_id="user_004",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("2.5"),
            annual_return_pct=Decimal("25"),
            max_drawdown_pct=Decimal("3"),
            sortino_ratio=Decimal("3.0"),
        )

        result = await recommender.recommend(request)

        assert result.recommendation_status == "STRONG_BUY"
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_buy_threshold(self):
        """Test BUY recommendation (score 70-85)."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_buy",
            input_id="user_005",
            objective="balanced_growth",
            sharpe_ratio=Decimal("1.3"),
            annual_return_pct=Decimal("12"),
            max_drawdown_pct=Decimal("12"),
        )

        result = await recommender.recommend(request)

        assert result.recommendation_status in ["BUY", "STRONG_BUY"]
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_hold_threshold(self):
        """Test HOLD recommendation (score 50-70)."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_hold",
            input_id="user_006",
            objective="balanced_growth",
            sharpe_ratio=Decimal("0.8"),
            annual_return_pct=Decimal("8"),
            max_drawdown_pct=Decimal("18"),
        )

        result = await recommender.recommend(request)

        assert result.recommendation_status in ["HOLD", "BUY"]
        assert result.confidence_level == "medium"


# SUGGESTION GENERATION TESTS
class TestSuggestionGeneration:
    @pytest.mark.asyncio
    async def test_suggest_improve_sharpe_ratio(self):
        """Test suggestion to improve Sharpe ratio."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_low_sharpe",
            input_id="user_007",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("0.5"),
            annual_return_pct=Decimal("15"),
            max_drawdown_pct=Decimal("10"),
            sortino_ratio=Decimal("1.0"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_suggest_reduce_drawdown(self):
        """Test suggestion to reduce drawdown."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_high_drawdown",
            input_id="user_008",
            objective="capital_preservation",
            sharpe_ratio=Decimal("1.5"),
            annual_return_pct=Decimal("12"),
            max_drawdown_pct=Decimal("35"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert len(result.suggestions) > 0

    @pytest.mark.asyncio
    async def test_suggest_increase_dividend(self):
        """Test suggestion to increase dividend yield."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_low_dividend",
            input_id="user_009",
            objective="income_generation",
            sharpe_ratio=Decimal("1.5"),
            annual_return_pct=Decimal("12"),
            max_drawdown_pct=Decimal("10"),
            dividend_yield_pct=Decimal("1.0"),
        )

        result = await recommender.recommend(request)

        assert result.success


# CHARACTERISTICS IDENTIFICATION TESTS
class TestCharacteristicsIdentification:
    @pytest.mark.asyncio
    async def test_identify_strengths(self):
        """Test identification of strategy strengths."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_strengths",
            input_id="user_010",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("2.2"),
            annual_return_pct=Decimal("22"),
            max_drawdown_pct=Decimal("8"),
            sortino_ratio=Decimal("2.5"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert len(result.strengths) > 0

    @pytest.mark.asyncio
    async def test_identify_weaknesses(self):
        """Test identification of strategy weaknesses."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_weaknesses",
            input_id="user_011",
            objective="balanced_growth",
            sharpe_ratio=Decimal("0.4"),
            annual_return_pct=Decimal("3"),
            max_drawdown_pct=Decimal("45"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert len(result.weaknesses) > 0


# OBJECTIVE-SPECIFIC RECOMMENDATION TESTS
class TestObjectiveSpecificRecommendations:
    @pytest.mark.asyncio
    async def test_recommend_capital_maximization(self):
        """Test recommendation for capital maximization."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_capital_max",
            input_id="user_012",
            objective="maximizar_capital",
            sharpe_ratio=Decimal("2.0"),
            annual_return_pct=Decimal("20"),
            max_drawdown_pct=Decimal("10"),
            sortino_ratio=Decimal("2.2"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert result.overall_score >= Decimal("75")

    @pytest.mark.asyncio
    async def test_recommend_capital_preservation(self):
        """Test recommendation for capital preservation."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_preservation",
            input_id="user_013",
            objective="capital_preservation",
            sharpe_ratio=Decimal("1.5"),
            annual_return_pct=Decimal("8"),
            max_drawdown_pct=Decimal("3"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert result.overall_score >= Decimal("50")

    @pytest.mark.asyncio
    async def test_recommend_income_generation(self):
        """Test recommendation for income generation."""
        recommender = StrategyRecommender()
        request = StrategyRecommendationRequest(
            profile_id="test_income",
            input_id="user_014",
            objective="income_generation",
            sharpe_ratio=Decimal("1.2"),
            annual_return_pct=Decimal("8"),
            max_drawdown_pct=Decimal("12"),
            dividend_yield_pct=Decimal("5.0"),
            win_rate_pct=Decimal("60"),
        )

        result = await recommender.recommend(request)

        assert result.success
        assert result.overall_score >= Decimal("60")


# RECOMMENDATION HISTORY TESTS
class TestRecommendationHistory:
    @pytest.mark.asyncio
    async def test_history_tracking(self):
        """Test recommendation history is tracked."""
        recommender = StrategyRecommender()

        for i in range(3):
            request = StrategyRecommendationRequest(
                profile_id=f"test_hist_{i}",
                input_id=f"user_hist_{i}",
                objective="balanced_growth",
                sharpe_ratio=Decimal("1.5"),
                annual_return_pct=Decimal("12"),
                max_drawdown_pct=Decimal("10"),
            )
            await recommender.recommend(request)

        history = await recommender.get_recommendation_history()
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_history_limit(self):
        """Test history retrieval with limit."""
        recommender = StrategyRecommender()

        for i in range(5):
            request = StrategyRecommendationRequest(
                profile_id=f"test_limit_{i}",
                input_id=f"user_limit_{i}",
                objective="balanced_growth",
                sharpe_ratio=Decimal("1.5"),
                annual_return_pct=Decimal("12"),
                max_drawdown_pct=Decimal("10"),
            )
            await recommender.recommend(request)

        history = await recommender.get_recommendation_history(limit=2)
        assert len(history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
