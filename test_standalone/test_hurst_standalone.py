"""
Standalone test for HurstExponentAnalyzer that bypasses conftest.py import issues.
Run with: python -m pytest test_standalone/test_hurst_standalone.py -v
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import pytest

# Direct import to avoid conftest.py
from app.services.hurst_exponent_analyzer import (
    HurstExponentAnalyzer,
    MarketRegime,
    StrategyRecommendation,
    HurstResult,
)


class TestMarketRegime:
    """Test suite for MarketRegime enum."""

    def test_market_regime_values(self):
        """Test MarketRegime enum values."""
        assert MarketRegime.MEAN_REVERTING.value == "mean_reverting"
        assert MarketRegime.RANDOM_WALK.value == "random_walk"
        assert MarketRegime.TRENDING.value == "trending"

    def test_market_regime_from_string(self):
        """Test creating MarketRegime from string."""
        regime = MarketRegime("mean_reverting")
        assert regime == MarketRegime.MEAN_REVERTING


class TestStrategyRecommendation:
    """Test suite for StrategyRecommendation enum."""

    def test_strategy_recommendation_values(self):
        """Test StrategyRecommendation enum values."""
        assert StrategyRecommendation.MEAN_REVERSION.value == "mean_reversion"
        assert StrategyRecommendation.NEUTRAL.value == "neutral"
        assert StrategyRecommendation.TREND_FOLLOWING.value == "trend_following"


class TestHurstAnalyzerInitialization:
    """Test suite for HurstExponentAnalyzer initialization."""

    def test_initialization_default_params(self):
        """Test initialization with default parameters."""
        analyzer = HurstExponentAnalyzer()
        assert analyzer.min_window_size == 10
        assert analyzer.max_window_size == 100

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        analyzer = HurstExponentAnalyzer(
            min_window_size=20,
            max_window_size=200,
        )
        assert analyzer.min_window_size == 20
        assert analyzer.max_window_size == 200


class TestRegimeClassification:
    """Test suite for market regime classification."""

    def test_classify_mean_reverting(self):
        """Test classification of mean-reverting regime."""
        analyzer = HurstExponentAnalyzer()
        regime = analyzer.classify_regime(0.3)
        assert regime == MarketRegime.MEAN_REVERTING

    def test_classify_random_walk(self):
        """Test classification of random walk regime."""
        analyzer = HurstExponentAnalyzer()
        regime = analyzer.classify_regime(0.5)
        assert regime == MarketRegime.RANDOM_WALK

    def test_classify_trending(self):
        """Test classification of trending regime."""
        analyzer = HurstExponentAnalyzer()
        regime = analyzer.classify_regime(0.7)
        assert regime == MarketRegime.TRENDING


class TestStrategyRecommendationTests:
    """Test suite for strategy recommendations."""

    def test_recommend_mean_reversion(self):
        """Test recommendation for mean-reverting regime."""
        analyzer = HurstExponentAnalyzer()
        strategy = analyzer.get_strategy_recommendation(0.3)
        assert strategy == StrategyRecommendation.MEAN_REVERSION

    def test_recommend_trend_following(self):
        """Test recommendation for trending regime."""
        analyzer = HurstExponentAnalyzer()
        strategy = analyzer.get_strategy_recommendation(0.7)
        assert strategy == StrategyRecommendation.TREND_FOLLOWING

    def test_recommend_neutral(self):
        """Test recommendation for random walk regime."""
        analyzer = HurstExponentAnalyzer()
        strategy = analyzer.get_strategy_recommendation(0.5)
        assert strategy == StrategyRecommendation.NEUTRAL
