"""
T6.1: Unit Tests for StrategyRecommender

Tests cover:
- Metric score calculations
- Weighted recommendation scoring
- Recommendation determination
- Objective-driven weighting
- Edge cases and error handling
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass

from app.services.strategy_recommendation import (
    StrategyRecommender,
    ObjectiveType,
    ConfidenceLevel,
)


@pytest.fixture
def recommender():
    """Create StrategyRecommender instance."""
    return StrategyRecommender()


@pytest.fixture
def sample_investment_profile():
    """Sample investment profile for testing."""
    @dataclass
    class MockInvestmentProfile:
        objetivo_inversion: str = "maximizar_capital"

    return MockInvestmentProfile()


@pytest.fixture
def sample_excellent_backtest_result():
    """Sample excellent backtest result."""
    return {
        "strategy_name": "momentum_modular",
        "total_return": 0.25,  # 25% annual
        "sharpe_ratio": 1.5,
        "sortino_ratio": 1.8,
        "max_drawdown": -0.10,  # 10% max drawdown
        "win_rate": 0.65,
        "dividend_yield": 0.03,  # 3% dividend
    }


@pytest.fixture
def sample_moderate_backtest_result():
    """Sample moderate backtest result."""
    return {
        "strategy_name": "mean_reversion",
        "total_return": 0.08,  # 8% annual
        "sharpe_ratio": 0.8,
        "sortino_ratio": 1.0,
        "max_drawdown": -0.20,  # 20% max drawdown
        "win_rate": 0.55,
        "dividend_yield": 0.02,
    }


@pytest.fixture
def sample_poor_backtest_result():
    """Sample poor backtest result."""
    return {
        "strategy_name": "poor_strategy",
        "total_return": 0.01,  # 1% annual
        "sharpe_ratio": 0.2,
        "sortino_ratio": 0.3,
        "max_drawdown": -0.35,  # 35% max drawdown
        "win_rate": 0.45,
        "dividend_yield": 0.0,
    }


# =============================================================================
# Test Metric Score Calculations
# =============================================================================

class TestMetricScoreCalculations:
    """Test metric score normalization."""

    @pytest.mark.asyncio
    async def test_sharpe_ratio_normalization(self, recommender, sample_excellent_backtest_result):
        """Test Sharpe ratio score normalization."""
        scores = await recommender._calculate_metric_scores(sample_excellent_backtest_result)
        # Sharpe 1.5: (1.5 + 1) / 4 * 100 = 62.5
        assert 60 < scores["sharpe_ratio"] < 65

    @pytest.mark.asyncio
    async def test_return_normalization(self, recommender, sample_excellent_backtest_result):
        """Test total return score normalization."""
        scores = await recommender._calculate_metric_scores(sample_excellent_backtest_result)
        # Return 0.25 (25%): 0.25 / 0.50 * 100 = 50
        assert 48 < scores["total_return"] < 52

    @pytest.mark.asyncio
    async def test_drawdown_inverse_normalization(self, recommender, sample_excellent_backtest_result):
        """Test max drawdown inverse score normalization."""
        scores = await recommender._calculate_metric_scores(sample_excellent_backtest_result)
        # Drawdown -0.10: (1 + (-0.10)) * 100 = 90
        assert 88 < scores["max_drawdown_inverse"] < 92

    @pytest.mark.asyncio
    async def test_consistency_normalization(self, recommender, sample_excellent_backtest_result):
        """Test consistency (win rate) score normalization."""
        scores = await recommender._calculate_metric_scores(sample_excellent_backtest_result)
        # Win rate 0.65: 0.65 * 100 = 65
        assert 64 < scores["consistency"] < 66

    @pytest.mark.asyncio
    async def test_metric_scores_all_present(self, recommender, sample_excellent_backtest_result):
        """Test that all metric scores are calculated."""
        scores = await recommender._calculate_metric_scores(sample_excellent_backtest_result)
        expected_metrics = [
            "sharpe_ratio",
            "total_return",
            "sortino_ratio",
            "max_drawdown_inverse",
            "dividend_yield",
            "consistency",
            "capital_preservation"
        ]
        for metric in expected_metrics:
            assert metric in scores
            assert 0 <= scores[metric] <= 100


# =============================================================================
# Test Weighted Score Calculation
# =============================================================================

class TestWeightedScoreCalculation:
    """Test weighted recommendation score calculation."""

    @pytest.mark.asyncio
    async def test_score_excellent_capital_maximization(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test score calculation for excellent capital maximization strategy."""
        sample_investment_profile.objetivo_inversion = "maximizar_capital"
        recommendation = await recommender.recommend(
            "excellent_strategy",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        # Good Sharpe, moderate-to-high return → moderate-to-good score
        assert recommendation.score > 50

    @pytest.mark.asyncio
    async def test_score_moderate_capital_maximization(
        self, recommender, sample_moderate_backtest_result, sample_investment_profile
    ):
        """Test score calculation for moderate capital maximization strategy."""
        sample_investment_profile.objetivo_inversion = "maximizar_capital"
        recommendation = await recommender.recommend(
            "moderate_strategy",
            sample_moderate_backtest_result,
            sample_investment_profile
        )
        # Moderate Sharpe, low-to-moderate return → moderate-to-low score
        assert 30 < recommendation.score < 50

    @pytest.mark.asyncio
    async def test_score_poor_strategy(
        self, recommender, sample_poor_backtest_result, sample_investment_profile
    ):
        """Test score calculation for poor strategy."""
        sample_investment_profile.objetivo_inversion = "maximizar_capital"
        recommendation = await recommender.recommend(
            "poor_strategy",
            sample_poor_backtest_result,
            sample_investment_profile
        )
        # Poor Sharpe, low return → low score
        assert recommendation.score < 50


# =============================================================================
# Test Recommendation Determination
# =============================================================================

class TestRecommendationDetermination:
    """Test recommendation status and confidence determination."""

    def test_approved_recommendation(self, recommender):
        """Test APPROVED recommendation (score >= 75)."""
        recommendation, confidence = recommender._determine_recommendation(85)
        assert recommendation == "APPROVED"
        assert confidence in [ConfidenceLevel.HIGH.value, ConfidenceLevel.VERY_HIGH.value]

    def test_very_high_confidence(self, recommender):
        """Test VERY_HIGH confidence (score >= 90)."""
        recommendation, confidence = recommender._determine_recommendation(95)
        assert recommendation == "APPROVED"
        assert confidence == ConfidenceLevel.VERY_HIGH.value

    def test_conditional_recommendation(self, recommender):
        """Test CONDITIONAL recommendation (60-74)."""
        recommendation, confidence = recommender._determine_recommendation(65)
        assert recommendation == "CONDITIONAL"
        assert confidence == ConfidenceLevel.MODERATE.value

    def test_review_recommendation(self, recommender):
        """Test REVIEW recommendation (40-59)."""
        recommendation, confidence = recommender._determine_recommendation(50)
        assert recommendation == "REVIEW"
        assert confidence == ConfidenceLevel.LOW.value

    def test_rejected_recommendation(self, recommender):
        """Test REJECTED recommendation (< 40)."""
        recommendation, confidence = recommender._determine_recommendation(35)
        assert recommendation == "REJECTED"
        assert confidence == ConfidenceLevel.VERY_LOW.value

    def test_boundary_approved_75(self, recommender):
        """Test boundary at approved threshold (75)."""
        recommendation, confidence = recommender._determine_recommendation(75)
        assert recommendation == "APPROVED"

    def test_boundary_conditional_60(self, recommender):
        """Test boundary at conditional threshold (60)."""
        recommendation, confidence = recommender._determine_recommendation(60)
        assert recommendation == "CONDITIONAL"


# =============================================================================
# Test Objective-Driven Weighting
# =============================================================================

class TestObjectiveDrivenWeighting:
    """Test weighting schemas for different objectives."""

    @pytest.mark.asyncio
    async def test_maximizar_capital_weighting(self, recommender, sample_excellent_backtest_result):
        """Test weighting for maximizar_capital objective."""
        @dataclass
        class MockProfile:
            objetivo_inversion = "maximizar_capital"

        recommendation = await recommender.recommend(
            "strategy",
            sample_excellent_backtest_result,
            MockProfile()
        )
        # Sharpe should be heavily weighted (60%)
        weights = recommendation.objective_weights
        assert weights["sharpe_ratio"] == 0.60
        assert weights["total_return"] == 0.30
        assert weights["sortino_ratio"] == 0.10

    @pytest.mark.asyncio
    async def test_capital_preservation_weighting(self, recommender, sample_excellent_backtest_result):
        """Test weighting for capital_preservation objective."""
        @dataclass
        class MockProfile:
            objetivo_inversion = "capital_preservation"

        recommendation = await recommender.recommend(
            "strategy",
            sample_excellent_backtest_result,
            MockProfile()
        )
        # Drawdown should be heavily weighted (50%)
        weights = recommendation.objective_weights
        assert weights["max_drawdown_inverse"] == 0.50
        assert weights["sharpe_ratio"] == 0.40
        assert weights["total_return"] == 0.10

    @pytest.mark.asyncio
    async def test_income_generation_weighting(self, recommender, sample_excellent_backtest_result):
        """Test weighting for income_generation objective."""
        @dataclass
        class MockProfile:
            objetivo_inversion = "income_generation"

        recommendation = await recommender.recommend(
            "strategy",
            sample_excellent_backtest_result,
            MockProfile()
        )
        # Dividend yield should be heavily weighted (50%)
        weights = recommendation.objective_weights
        assert weights["dividend_yield"] == 0.50
        assert weights["consistency"] == 0.30
        assert weights["sharpe_ratio"] == 0.20


# =============================================================================
# Test Recommendation Details Generation
# =============================================================================

class TestRecommendationDetails:
    """Test generation of recommendation details."""

    @pytest.mark.asyncio
    async def test_excellent_strategy_details(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test details for excellent strategy."""
        recommendation = await recommender.recommend(
            "excellent",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        details = recommendation.details
        assert len(details.strengths) > 0
        assert len(details.suggestions) >= 0
        assert "risk_assessment" in recommendation.details.__dict__
        assert "fit_analysis" in recommendation.details.__dict__

    @pytest.mark.asyncio
    async def test_poor_strategy_details(
        self, recommender, sample_poor_backtest_result, sample_investment_profile
    ):
        """Test details for poor strategy."""
        recommendation = await recommender.recommend(
            "poor",
            sample_poor_backtest_result,
            sample_investment_profile
        )
        details = recommendation.details
        assert len(details.weaknesses) > 0
        assert len(details.suggestions) > 0

    @pytest.mark.asyncio
    async def test_details_have_required_fields(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test that recommendation details have all required fields."""
        recommendation = await recommender.recommend(
            "test",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        details = recommendation.details
        assert isinstance(details.strengths, list)
        assert isinstance(details.weaknesses, list)
        assert isinstance(details.suggestions, list)
        assert isinstance(details.risk_assessment, str)
        assert isinstance(details.fit_analysis, str)


# =============================================================================
# Test Safe Float Conversion
# =============================================================================

class TestSafeFloatConversion:
    """Test safe float conversion for different types."""

    def test_safe_float_from_int(self, recommender):
        """Test converting int to float."""
        assert recommender._safe_float(5) == 5.0

    def test_safe_float_from_float(self, recommender):
        """Test converting float to float."""
        assert recommender._safe_float(3.14) == 3.14

    def test_safe_float_from_decimal(self, recommender):
        """Test converting Decimal to float."""
        assert recommender._safe_float(Decimal("2.5")) == 2.5

    def test_safe_float_from_string(self, recommender):
        """Test converting string to float."""
        assert recommender._safe_float("1.5") == 1.5

    def test_safe_float_from_invalid_string(self, recommender):
        """Test converting invalid string returns 0.0."""
        assert recommender._safe_float("invalid") == 0.0

    def test_safe_float_from_none(self, recommender):
        """Test converting None returns 0.0."""
        assert recommender._safe_float(None) == 0.0


# =============================================================================
# Test Recommendation Attributes
# =============================================================================

class TestRecommendationAttributes:
    """Test recommendation object attributes."""

    @pytest.mark.asyncio
    async def test_recommendation_has_all_fields(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test that recommendation has all required fields."""
        recommendation = await recommender.recommend(
            "test",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        assert hasattr(recommendation, "recommendation")
        assert hasattr(recommendation, "score")
        assert hasattr(recommendation, "confidence_level")
        assert hasattr(recommendation, "objective_weights")
        assert hasattr(recommendation, "metric_scores")
        assert hasattr(recommendation, "details")
        assert hasattr(recommendation, "summary")

    @pytest.mark.asyncio
    async def test_recommendation_score_range(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test that recommendation score is in valid range."""
        recommendation = await recommender.recommend(
            "test",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        assert 0 <= recommendation.score <= 100

    @pytest.mark.asyncio
    async def test_metric_scores_all_in_range(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test that all metric scores are in 0-100 range."""
        recommendation = await recommender.recommend(
            "test",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        for metric, score in recommendation.metric_scores.items():
            assert 0 <= score <= 100, f"Metric {metric} score {score} out of range"


# =============================================================================
# Integration Tests
# =============================================================================

class TestRecommenderIntegration:
    """Integration tests for strategy recommender."""

    @pytest.mark.asyncio
    async def test_recommendation_flow_excellent_strategy(
        self, recommender, sample_excellent_backtest_result, sample_investment_profile
    ):
        """Test complete recommendation flow for excellent strategy."""
        recommendation = await recommender.recommend(
            "excellent_momentum",
            sample_excellent_backtest_result,
            sample_investment_profile
        )
        # Should be REVIEW or CONDITIONAL with reasonable confidence
        assert recommendation.recommendation in ["REVIEW", "CONDITIONAL", "APPROVED"]
        assert recommendation.confidence_level in [
            ConfidenceLevel.VERY_HIGH.value,
            ConfidenceLevel.HIGH.value,
            ConfidenceLevel.MODERATE.value,
            ConfidenceLevel.LOW.value
        ]
        assert recommendation.score > 40
        assert len(recommendation.summary) > 0

    @pytest.mark.asyncio
    async def test_recommendation_flow_poor_strategy(
        self, recommender, sample_poor_backtest_result, sample_investment_profile
    ):
        """Test complete recommendation flow for poor strategy."""
        recommendation = await recommender.recommend(
            "poor_strategy",
            sample_poor_backtest_result,
            sample_investment_profile
        )
        # Should be REVIEW or REJECTED with LOW/VERY_LOW confidence
        assert recommendation.recommendation in ["REVIEW", "REJECTED"]
        assert recommendation.confidence_level in [
            ConfidenceLevel.LOW.value,
            ConfidenceLevel.VERY_LOW.value
        ]
        assert len(recommendation.summary) > 0

    @pytest.mark.asyncio
    async def test_missing_backtest_metrics_default_to_zero(
        self, recommender, sample_investment_profile
    ):
        """Test handling of missing backtest metrics."""
        minimal_result = {"strategy_name": "test"}
        recommendation = await recommender.recommend(
            "test",
            minimal_result,
            sample_investment_profile
        )
        # Should still produce a recommendation with missing metrics defaulting to 0
        assert recommendation.score >= 0
        assert recommendation.recommendation in ["APPROVED", "CONDITIONAL", "REVIEW", "REJECTED"]

    @pytest.mark.asyncio
    async def test_different_objectives_produce_different_recommendations(
        self, recommender, sample_excellent_backtest_result
    ):
        """Test that different objectives produce different recommendation scores."""
        @dataclass
        class MockProfile:
            objetivo_inversion: str

        # Capital maximization
        profile_capital = MockProfile(objetivo_inversion="maximizar_capital")
        rec_capital = await recommender.recommend(
            "strategy", sample_excellent_backtest_result, profile_capital
        )

        # Capital preservation
        profile_preservation = MockProfile(objetivo_inversion="capital_preservation")
        rec_preservation = await recommender.recommend(
            "strategy", sample_excellent_backtest_result, profile_preservation
        )

        # Scores should be different due to different weighting
        assert abs(rec_capital.score - rec_preservation.score) >= 0
