"""
BATCH E - T6.1: Unit Tests for StrategyRecommender with Objective-Aware Scoring

Tests:
- Strategy recommendation generation
- Objective-aware scoring (5 objectives)
- Risk profile matching
- Confidence level determination
- Suitability assessment
- Alternative recommendations
- Risk level assessment
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.services.strategy_recommendation.strategy_recommender import (
    StrategyRecommender,
)


@dataclass
class MockRankedStrategy:
    """Mock ranked strategy for testing."""

    strategy_name: str
    overall_score: Decimal
    return_score: Decimal
    stability_score: Decimal
    consistency_score: Decimal
    risk_score: Decimal


@pytest.fixture
def strategy_recommender():
    """Create StrategyRecommender instance for tests."""
    return StrategyRecommender()


class TestBasicRecommendation:
    """Test basic strategy recommendation generation."""

    @pytest.mark.asyncio
    async def test_recommend_single_strategy(self, strategy_recommender):
        """Test recommendation with single strategy."""
        strategies = [
            MockRankedStrategy(
                strategy_name="momentum_growth",
                overall_score=Decimal("78"),
                return_score=Decimal("85"),
                stability_score=Decimal("72"),
                consistency_score=Decimal("70"),
                risk_score=Decimal("65"),
            )
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation is not None
        assert recommendation.recommended_strategy == "momentum_growth"
        assert recommendation.overall_score == Decimal("78")
        assert len(recommendation.alternatives) == 0

    @pytest.mark.asyncio
    async def test_recommend_with_alternatives(self, strategy_recommender):
        """Test recommendation with alternatives."""
        strategies = [
            MockRankedStrategy(
                strategy_name="strategy_1",
                overall_score=Decimal("85"),
                return_score=Decimal("90"),
                stability_score=Decimal("80"),
                consistency_score=Decimal("75"),
                risk_score=Decimal("70"),
            ),
            MockRankedStrategy(
                strategy_name="strategy_2",
                overall_score=Decimal("78"),
                return_score=Decimal("80"),
                stability_score=Decimal("75"),
                consistency_score=Decimal("72"),
                risk_score=Decimal("68"),
            ),
            MockRankedStrategy(
                strategy_name="strategy_3",
                overall_score=Decimal("72"),
                return_score=Decimal("75"),
                stability_score=Decimal("70"),
                consistency_score=Decimal("68"),
                risk_score=Decimal("65"),
            ),
            MockRankedStrategy(
                strategy_name="strategy_4",
                overall_score=Decimal("68"),
                return_score=Decimal("70"),
                stability_score=Decimal("65"),
                consistency_score=Decimal("62"),
                risk_score=Decimal("60"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.recommended_strategy == "strategy_1"
        assert len(recommendation.alternatives) == 3
        assert recommendation.alternatives == ["strategy_2", "strategy_3", "strategy_4"]

    @pytest.mark.asyncio
    async def test_empty_strategies_list(self, strategy_recommender):
        """Test recommendation with empty strategies list."""
        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=[],
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.recommended_strategy == "NONE"
        assert recommendation.confidence_level == "low"
        assert recommendation.overall_score == Decimal("0")


class TestObjectiveAwareScoring:
    """Test objective-aware strategy recommendations."""

    @pytest.mark.asyncio
    async def test_maximizar_capital_objective(self, strategy_recommender):
        """Test recommendation for capital maximization objective."""
        # High return score should be valued for growth objective
        strategies = [
            MockRankedStrategy(
                strategy_name="high_return_strategy",
                overall_score=Decimal("80"),
                return_score=Decimal("95"),  # Very high return focus
                stability_score=Decimal("65"),
                consistency_score=Decimal("60"),
                risk_score=Decimal("50"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation.recommended_strategy == "high_return_strategy"
        # Should have good suitability for capital growth objective
        assert recommendation.suitability_score > Decimal("50")

    @pytest.mark.asyncio
    async def test_balanced_growth_objective(self, strategy_recommender):
        """Test recommendation for balanced growth objective."""
        strategies = [
            MockRankedStrategy(
                strategy_name="balanced_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("75"),  # Balanced
                stability_score=Decimal("75"),
                consistency_score=Decimal("75"),
                risk_score=Decimal("75"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.recommended_strategy == "balanced_strategy"

    @pytest.mark.asyncio
    async def test_income_generation_objective(self, strategy_recommender):
        """Test recommendation for income generation objective."""
        # High consistency and stability should be valued for income
        strategies = [
            MockRankedStrategy(
                strategy_name="income_strategy",
                overall_score=Decimal("78"),
                return_score=Decimal("70"),
                stability_score=Decimal("90"),  # High stability
                consistency_score=Decimal("92"),  # High consistency
                risk_score=Decimal("80"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="income_generation",
            risk_profile="conservative",
        )

        assert recommendation.recommended_strategy == "income_strategy"


class TestRiskProfileMatching:
    """Test risk profile matching in recommendations."""

    @pytest.mark.asyncio
    async def test_conservative_risk_profile(self, strategy_recommender):
        """Test recommendation for conservative risk profile."""
        strategies = [
            MockRankedStrategy(
                strategy_name="safe_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("70"),
                stability_score=Decimal("85"),
                consistency_score=Decimal("80"),
                risk_score=Decimal("90"),  # High risk score = low risk
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="capital_preservation",
            risk_profile="conservative",
        )

        assert recommendation.recommended_strategy == "safe_strategy"
        assert recommendation.risk_assessment == "low"

    @pytest.mark.asyncio
    async def test_aggressive_risk_profile(self, strategy_recommender):
        """Test recommendation for aggressive risk profile."""
        strategies = [
            MockRankedStrategy(
                strategy_name="aggressive_strategy",
                overall_score=Decimal("82"),
                return_score=Decimal("95"),  # High return for aggressive
                stability_score=Decimal("60"),
                consistency_score=Decimal("55"),
                risk_score=Decimal("40"),  # Lower risk score = higher risk
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation.recommended_strategy == "aggressive_strategy"
        assert recommendation.risk_assessment == "high"


class TestConfidenceLevelDetermination:
    """Test confidence level determination."""

    @pytest.mark.asyncio
    async def test_high_confidence_strong_scores(self, strategy_recommender):
        """Test high confidence with strong scores."""
        strategies = [
            MockRankedStrategy(
                strategy_name="excellent_strategy",
                overall_score=Decimal("85"),  # High overall
                return_score=Decimal("88"),
                stability_score=Decimal("85"),
                consistency_score=Decimal("80"),
                risk_score=Decimal("82"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_medium_confidence_moderate_scores(self, strategy_recommender):
        """Test medium confidence with moderate scores."""
        strategies = [
            MockRankedStrategy(
                strategy_name="moderate_strategy",
                overall_score=Decimal("65"),  # Moderate score
                return_score=Decimal("65"),
                stability_score=Decimal("65"),
                consistency_score=Decimal("65"),
                risk_score=Decimal("65"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.confidence_level == "medium"

    @pytest.mark.asyncio
    async def test_low_confidence_poor_scores(self, strategy_recommender):
        """Test low confidence with poor scores."""
        strategies = [
            MockRankedStrategy(
                strategy_name="poor_strategy",
                overall_score=Decimal("40"),  # Low score
                return_score=Decimal("35"),
                stability_score=Decimal("40"),
                consistency_score=Decimal("38"),
                risk_score=Decimal("35"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.confidence_level == "low"


class TestRiskAssessment:
    """Test risk assessment in recommendations."""

    @pytest.mark.asyncio
    async def test_low_risk_assessment(self, strategy_recommender):
        """Test low risk assessment."""
        strategies = [
            MockRankedStrategy(
                strategy_name="safe_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("70"),
                stability_score=Decimal("85"),
                consistency_score=Decimal("80"),
                risk_score=Decimal("85"),  # High risk score = low risk
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="capital_preservation",
            risk_profile="conservative",
        )

        assert recommendation.risk_assessment == "low"

    @pytest.mark.asyncio
    async def test_medium_risk_assessment(self, strategy_recommender):
        """Test medium risk assessment."""
        strategies = [
            MockRankedStrategy(
                strategy_name="balanced_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("75"),
                stability_score=Decimal("75"),
                consistency_score=Decimal("75"),
                risk_score=Decimal("65"),  # Medium risk score
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        assert recommendation.risk_assessment == "medium"

    @pytest.mark.asyncio
    async def test_high_risk_assessment(self, strategy_recommender):
        """Test high risk assessment."""
        strategies = [
            MockRankedStrategy(
                strategy_name="aggressive_strategy",
                overall_score=Decimal("80"),
                return_score=Decimal("95"),
                stability_score=Decimal("50"),
                consistency_score=Decimal("45"),
                risk_score=Decimal("30"),  # Low risk score = high risk
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation.risk_assessment == "high"


class TestReturnAndDrawdownEstimates:
    """Test return and drawdown estimates."""

    @pytest.mark.asyncio
    async def test_estimated_annual_return(self, strategy_recommender):
        """Test estimated annual return calculation."""
        strategies = [
            MockRankedStrategy(
                strategy_name="growth_strategy",
                overall_score=Decimal("80"),
                return_score=Decimal("85"),
                stability_score=Decimal("70"),
                consistency_score=Decimal("70"),
                risk_score=Decimal("65"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="maximizar_capital",
            risk_profile="aggressive",
        )

        assert recommendation.estimated_annual_return > Decimal("0")
        assert recommendation.estimated_annual_return <= Decimal("0.20")  # Max growth return

    @pytest.mark.asyncio
    async def test_max_expected_drawdown(self, strategy_recommender):
        """Test maximum expected drawdown calculation."""
        strategies = [
            MockRankedStrategy(
                strategy_name="test_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("75"),
                stability_score=Decimal("75"),
                consistency_score=Decimal("75"),
                risk_score=Decimal("60"),
            ),
        ]

        recommendation = await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        # Drawdown should be negative
        assert recommendation.max_expected_drawdown < Decimal("0")


class TestRecommendationHistory:
    """Test recommendation history tracking."""

    @pytest.mark.asyncio
    async def test_recommendation_history_tracked(self, strategy_recommender):
        """Test recommendations are tracked in history."""
        strategies = [
            MockRankedStrategy(
                strategy_name="test_strategy",
                overall_score=Decimal("75"),
                return_score=Decimal("75"),
                stability_score=Decimal("75"),
                consistency_score=Decimal("75"),
                risk_score=Decimal("75"),
            ),
        ]

        await strategy_recommender.recommend_strategy(
            ranked_strategies=strategies,
            objective="balanced_growth",
            risk_profile="moderate",
        )

        all_recommendations = await strategy_recommender.get_all_recommendations()
        assert len(all_recommendations) > 0
        assert all_recommendations[-1].recommended_strategy == "test_strategy"

    def test_recommender_status(self, strategy_recommender):
        """Test recommender status reporting."""
        status = strategy_recommender.get_recommender_status()

        assert "total_recommendations" in status
        assert "high_confidence" in status
        assert "medium_confidence" in status
        assert "low_confidence" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
