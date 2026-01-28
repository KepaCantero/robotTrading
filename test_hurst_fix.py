"""
Test script to verify hurst_exponent_analyzer fixes work.
This bypasses the app import chain that causes NumPy issues.
"""

import sys
import os

# Add the project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Direct imports to avoid conftest.py issues
import numpy as np
import pandas as pd
from decimal import Decimal

# Import directly from the file using importlib to avoid exec() issues
# The exec() approach causes problems with @jit(cache=True) decorators
import importlib.util
import importlib.machinery

def import_module_from_file(module_name, file_path):
    """Import a module directly from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import the hurst_exponent_analyzer module directly from file
# This bypasses the app/__init__.py import chain while preserving proper module structure
hurst_module_path = os.path.join(project_root, "app/services/hurst_exponent_analyzer.py")
hurst_module = import_module_from_file("hurst_module", hurst_module_path)

# Extract the classes we need
HurstExponentAnalyzer = hurst_module.HurstExponentAnalyzer
MarketRegime = hurst_module.MarketRegime
StrategyRecommendation = hurst_module.StrategyRecommendation
HurstResult = hurst_module.HurstResult
RegimeChange = hurst_module.RegimeChange

def test_hurst_analyzer_initialization():
    """Test that HurstExponentAnalyzer initializes with correct parameters."""
    analyzer = HurstExponentAnalyzer()

    # Test default parameters
    assert analyzer.min_window_size == 10
    assert analyzer.max_window_size == 100

    print("✓ HurstExponentAnalyzer initialization test passed")

def test_hurst_analyzer_custom_params():
    """Test that HurstExponentAnalyzer accepts custom parameters."""
    analyzer = HurstExponentAnalyzer(min_window_size=20, max_window_size=200)

    assert analyzer.min_window_size == 20
    assert analyzer.max_window_size == 200

    print("✓ HurstExponentAnalyzer custom parameters test passed")

def test_classify_regime():
    """Test regime classification."""
    analyzer = HurstExponentAnalyzer()

    # Test mean-reverting
    regime = analyzer.classify_regime(0.3)
    assert regime == MarketRegime.MEAN_REVERTING

    # Test random walk
    regime = analyzer.classify_regime(0.5)
    assert regime == MarketRegime.RANDOM_WALK

    # Test trending
    regime = analyzer.classify_regime(0.7)
    assert regime == MarketRegime.TRENDING

    print("✓ Regime classification test passed")

def test_get_strategy_recommendation():
    """Test strategy recommendations."""
    analyzer = HurstExponentAnalyzer()

    # Test mean-reversion recommendation
    strategy = analyzer.get_strategy_recommendation(0.3)
    assert strategy == StrategyRecommendation.MEAN_REVERSION

    # Test neutral recommendation
    strategy = analyzer.get_strategy_recommendation(0.5)
    assert strategy == StrategyRecommendation.NEUTRAL

    # Test trend-following recommendation
    strategy = analyzer.get_strategy_recommendation(0.7)
    assert strategy == StrategyRecommendation.TREND_FOLLOWING

    print("✓ Strategy recommendation test passed")

def test_market_regime_enum():
    """Test MarketRegime enum values."""
    assert MarketRegime.MEAN_REVERTING.value == "mean_reverting"
    assert MarketRegime.RANDOM_WALK.value == "random_walk"
    assert MarketRegime.TRENDING.value == "trending"

    # Test from string
    regime = MarketRegime("mean_reverting")
    assert regime == MarketRegime.MEAN_REVERTING

    print("✓ MarketRegime enum test passed")

def test_strategy_recommendation_enum():
    """Test StrategyRecommendation enum values."""
    assert StrategyRecommendation.MEAN_REVERSION.value == "mean_reversion"
    assert StrategyRecommendation.NEUTRAL.value == "neutral"
    assert StrategyRecommendation.TREND_FOLLOWING.value == "trend_following"

    print("✓ StrategyRecommendation enum test passed")

if __name__ == "__main__":
    print("Running Hurst Exponent Analyzer tests...")
    print()

    try:
        test_market_regime_enum()
        test_strategy_recommendation_enum()
        test_hurst_analyzer_initialization()
        test_hurst_analyzer_custom_params()
        test_classify_regime()
        test_get_strategy_recommendation()

        print()
        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except Exception as e:
        print()
        print("=" * 50)
        print(f"Test failed: {e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)
