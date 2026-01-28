"""
Hurst Exponent Analysis Example

This example demonstrates how to use the Hurst Exponent Analyzer to:
1. Calculate Hurst exponent for market data
2. Classify market regime (mean-reverting vs trending)
3. Recommend appropriate trading strategies
4. Detect regime changes over time
5. Monitor multiple symbols simultaneously

Compliance: Ernest Chan Rule 2.2 - Hurst Exponent Analysis
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

# Import Hurst Exponent Analyzer
from app.services.hurst_exponent_analyzer import (
    HurstExponentAnalyzer,
    MarketRegime,
    StrategyRecommendation,
    calculate_hurst_exponent,
    classify_regime,
    recommend_strategy_from_hurst,
    get_analyzer_info,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Hurst Exponent Calculation
# ============================================================================

def example_1_basic_calculation():
    """
    Example 1: Calculate Hurst exponent for a single symbol.

    This is the simplest use case - just get the Hurst value and classification.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Hurst Exponent Calculation")
    print("="*80)

    # Download historical data for AAPL
    print("\n📥 Downloading AAPL historical data...")
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period="6mo", interval="1d")

    if data.empty:
        print("❌ No data retrieved")
        return

    prices = data['Close'].values
    print(f"✅ Retrieved {len(prices)} price points")

    # Calculate Hurst exponent using convenience function
    print("\n🔬 Calculating Hurst exponent...")
    hurst = calculate_hurst_exponent(prices, method="rs", use_returns=True)

    print(f"\n📊 Results:")
    print(f"   Hurst Exponent: {hurst:.4f}")

    # Classify regime
    regime = classify_regime(hurst)
    print(f"   Market Regime: {regime.value}")

    # Recommend strategy
    strategy = recommend_strategy_from_hurst(hurst)
    print(f"   Recommended Strategy: {strategy.value}")

    # Interpret results
    print(f"\n💡 Interpretation:")
    if hurst < 0.5:
        print(f"   • H < 0.5 ({hurst:.4f}): Mean-reverting market")
        print(f"   • Consider mean reversion strategies (stat arb, pairs trading)")
        print(f"   • Avoid trend following strategies")
    elif hurst > 0.5:
        print(f"   • H > 0.5 ({hurst:.4f}): Trending market")
        print(f"   • Consider trend following strategies (breakout, momentum)")
        print(f"   • Avoid mean reversion strategies")
    else:
        print(f"   • H ≈ 0.5 ({hurst:.4f}): Random walk")
        print(f"   • Market is efficient - no clear edge")
        print(f"   • Consider neutral strategies (market making)")


# ============================================================================
# Example 2: Full Analysis with HurstExponentAnalyzer
# ============================================================================

def example_2_full_analysis():
    """
    Example 2: Complete analysis with detailed results.

    Use the full analyzer class for more detailed results including
    confidence intervals, R/S values, and more.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Full Analysis with Detailed Results")
    print("="*80)

    # Download data
    print("\n📥 Downloading SPY historical data...")
    ticker = yf.Ticker("SPY")
    data = ticker.history(period="1y", interval="1d")

    prices = data['Close'].values
    print(f"✅ Retrieved {len(prices)} price points")

    # Create analyzer with custom parameters
    analyzer = HurstExponentAnalyzer(
        method="rs",  # Use R/S analysis
        min_window=10,
        max_window_ratio=0.5,
        num_windows=20,
        confidence_level=0.95,
        use_returns=True  # Analyze log returns
    )

    # Perform analysis
    print("\n🔬 Performing comprehensive Hurst analysis...")
    result = analyzer.analyze(
        prices,
        symbol="SPY",
        timestamp=datetime.now()
    )

    # Display results
    print(f"\n📊 Comprehensive Results:")
    print(f"   Symbol: SPY")
    print(f"   Hurst Exponent: {result.hurst_exponent:.4f}")
    print(f"   Market Regime: {result.regime.value}")
    print(f"   Recommended Strategy: {result.strategy.value}")
    print(f"   Confidence: {result.confidence*100:.1f}%")
    print(f"   Method: {result.method}")

    # Display R/S values if available
    if result.rs_values and result.window_sizes:
        print(f"\n📈 R/S Analysis Details:")
        print(f"   Window Sizes: {len(result.window_sizes)} points")
        print(f"   Min Window: {min(result.window_sizes)}")
        print(f"   Max Window: {max(result.window_sizes)}")
        print(f"   R/S Range: [{min(result.rs_values):.4f}, {max(result.rs_values):.4f}]")


# ============================================================================
# Example 3: Compare Multiple Symbols
# ============================================================================

def example_3_compare_symbols():
    """
    Example 3: Compare Hurst exponent across multiple symbols.

    This is useful for finding the best opportunities across different assets.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Compare Multiple Symbols")
    print("="*80)

    # Define symbols to analyze
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "SPY", "TLT"]

    print(f"\n📥 Downloading data for {len(symbols)} symbols...")
    data_dict = {}

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="6mo", interval="1d")
            if not data.empty:
                data_dict[symbol] = data['Close']
                print(f"   ✅ {symbol}: {len(data)} data points")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")

    # Analyze all symbols
    print(f"\n🔬 Analyzing Hurst exponent for {len(data_dict)} symbols...")

    analyzer = HurstExponentAnalyzer(method="rs", use_returns=True)
    results = analyzer.monitor_multiple_symbols(data_dict, detect_changes=False)

    # Display results in a table
    print(f"\n📊 Results Summary:")
    print(f"{'Symbol':<10} {'Hurst':<10} {'Regime':<20} {'Strategy':<20} {'Confidence':<12}")
    print("-" * 80)

    for symbol in sorted(results.keys()):
        result = results[symbol]
        regime_short = result.regime.value[:20]
        strategy_short = result.strategy.value[:20]
        print(f"{symbol:<10} {result.hurst_exponent:<10.4f} {regime_short:<20} {strategy_short:<20} {result.confidence*100:<11.1f}%")

    # Find best opportunities
    print(f"\n💡 Best Opportunities:")

    # Most mean-reverting (best for stat arb)
    most_mean_reverting = min(
        [(s, r) for s, r in results.items() if r.regime == MarketRegime.MEAN_REVERTING],
        key=lambda x: x[1].hurst_exponent if x[1].regime == MarketRegime.MEAN_REVERTING else 1.0,
        default=None
    )
    if most_mean_reverting:
        symbol, result = most_mean_reverting
        print(f"   • Mean Reversion: {symbol} (H={result.hurst_exponent:.4f})")

    # Most trending (best for trend following)
    most_trending = max(
        [(s, r) for s, r in results.items() if r.regime == MarketRegime.TRENDING],
        key=lambda x: x[1].hurst_exponent if x[1].regime == MarketRegime.TRENDING else 0.0,
        default=None
    )
    if most_trending:
        symbol, result = most_trending
        print(f"   • Trend Following: {symbol} (H={result.hurst_exponent:.4f})")


# ============================================================================
# Example 4: Regime Change Detection
# ============================================================================

def example_4_regime_change_detection():
    """
    Example 4: Detect regime changes over time.

    This simulates monitoring a symbol over multiple time periods
    and detecting when the market regime changes.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Regime Change Detection")
    print("="*80)

    # Download historical data
    print("\n📥 Downloading BTC-USD historical data (higher volatility for regime changes)...")
    ticker = yf.Ticker("BTC-USD")
    data = ticker.history(period="1y", interval="1d")

    if data.empty:
        print("❌ No data retrieved")
        return

    prices = data['Close'].values
    print(f"✅ Retrieved {len(prices)} price points")

    # Create analyzer
    analyzer = HurstExponentAnalyzer(method="rs", use_returns=True)

    # Simulate periodic analysis (e.g., weekly)
    window_size = 30  # days
    step_size = 7  # days (weekly analysis)

    print(f"\n🔬 Simulating weekly Hurst analysis over 1 year...")

    results_history = []
    for i in range(window_size, len(prices), step_size):
        # Get window of data
        window_prices = prices[max(0, i-window_size):i]

        # Get approximate date
        current_date = data.index[i-1] if i-1 < len(data.index) else datetime.now()

        # Analyze
        result = analyzer.analyze(
            window_prices,
            symbol="BTC-USD",
            timestamp=current_date
        )

        results_history.append({
            'date': current_date,
            'hurst': result.hurst_exponent,
            'regime': result.regime.value
        })

    # Display history
    print(f"\n📊 Analysis History ({len(results_history)} periods):")
    print(f"{'Date':<12} {'Hurst':<10} {'Regime':<20}")
    print("-" * 50)

    for entry in results_history[::2]:  # Show every other entry
        date_str = entry['date'].strftime('%Y-%m-%d')
        print(f"{date_str:<12} {entry['hurst']:<10.4f} {entry['regime']:<20}")

    # Detect regime changes
    print(f"\n🔍 Detecting Regime Changes...")

    changes = []
    for i in range(1, len(results_history)):
        prev_entry = results_history[i-1]
        curr_entry = results_history[i]

        if prev_entry['regime'] != curr_entry['regime']:
            changes.append({
                'date': curr_entry['date'],
                'old_regime': prev_entry['regime'],
                'new_regime': curr_entry['regime'],
                'old_hurst': prev_entry['hurst'],
                'new_hurst': curr_entry['hurst']
            })

    if changes:
        print(f"\n✅ Detected {len(changes)} regime changes:")
        for change in changes:
            print(f"\n   Date: {change['date'].strftime('%Y-%m-%d')}")
            print(f"   Change: {change['old_regime']} → {change['new_regime']}")
            print(f"   Hurst: {change['old_hurst']:.4f} → {change['new_hurst']:.4f}")
    else:
        print(f"\n✅ No significant regime changes detected in this period")


# ============================================================================
# Example 5: Synthetic Data with Known Hurst Values
# ============================================================================

def example_5_synthetic_data():
    """
    Example 5: Test with synthetic data having known Hurst characteristics.

    This validates that the analyzer correctly identifies different regimes.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Synthetic Data Validation")
    print("="*80)

    analyzer = HurstExponentAnalyzer(method="rs", use_returns=False)

    # 1. Mean-reverting (Ornstein-Uhlenbeck process)
    print("\n🔬 Testing Mean-Reverting Series (Ornstein-Uhlenbeck)...")
    np.random.seed(42)
    n = 1000
    theta = 0.1
    mu = 100.0
    sigma = 1.0
    dt = 0.01

    ou_process = np.zeros(n)
    ou_process[0] = mu
    for i in range(1, n):
        dx = theta * (mu - ou_process[i-1]) * dt + sigma * np.sqrt(dt) * np.random.randn()
        ou_process[i] = ou_process[i-1] + dx

    result_ou = analyzer.analyze(ou_process)
    print(f"   Hurst: {result_ou.hurst_exponent:.4f}")
    print(f"   Regime: {result_ou.regime.value}")
    print(f"   Expected: H < 0.5 (mean-reverting)")
    print(f"   ✅ PASS" if result_ou.hurst_exponent < 0.5 else "   ⚠️  UNEXPECTED")

    # 2. Random Walk (Geometric Brownian Motion)
    print("\n🔬 Testing Random Walk (Geometric Brownian Motion)...")
    np.random.seed(42)

    gbm = np.zeros(n)
    gbm[0] = 100.0
    for i in range(1, n):
        dx = 0.01 * np.sqrt(0.01) * np.random.randn()
        gbm[i] = gbm[i-1] * (1 + dx)

    result_gbm = analyzer.analyze(gbm)
    print(f"   Hurst: {result_gbm.hurst_exponent:.4f}")
    print(f"   Regime: {result_gbm.regime.value}")
    print(f"   Expected: H ≈ 0.5 (random walk)")
    print(f"   ✅ PASS" if 0.4 < result_gbm.hurst_exponent < 0.6 else "   ⚠️  UNEXPECTED")

    # 3. Trending Series
    print("\n🔬 Testing Trending Series...")
    np.random.seed(42)

    trending = np.zeros(n)
    trending[0] = 100.0
    for i in range(1, n):
        trending[i] = trending[i-1] * (1 + 0.0005) + 0.5 * np.random.randn()

    result_trending = analyzer.analyze(trending)
    print(f"   Hurst: {result_trending.hurst_exponent:.4f}")
    print(f"   Regime: {result_trending.regime.value}")
    print(f"   Expected: H > 0.5 (trending)")
    print(f"   ✅ PASS" if result_trending.hurst_exponent > 0.5 else "   ⚠️  UNEXPECTED")


# ============================================================================
# Example 6: Strategy Selection Guide
# ============================================================================

def example_6_strategy_selection_guide():
    """
    Example 6: Practical guide for strategy selection based on Hurst exponent.

    This shows how to use Hurst analysis in actual trading decisions.
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Strategy Selection Guide")
    print("="*80)

    # Download data for analysis
    print("\n📥 Analyzing current market conditions...")
    ticker = yf.Ticker("SPY")
    data = ticker.history(period="3mo", interval="1d")

    if data.empty:
        print("❌ No data retrieved")
        return

    prices = data['Close'].values

    # Calculate Hurst
    analyzer = HurstExponentAnalyzer(method="rs", use_returns=True)
    result = analyzer.analyze(prices)

    print(f"\n📊 Analysis Results:")
    print(f"   Hurst Exponent: {result.hurst_exponent:.4f}")
    print(f"   Market Regime: {result.regime.value}")
    print(f"   Confidence: {result.confidence*100:.1f}%")

    # Strategy recommendations
    print(f"\n💼 Strategy Recommendations:")

    if result.strategy == StrategyRecommendation.MEAN_REVERSION:
        print(f"\n   ✅ USE MEAN REVERSION STRATEGIES")
        print(f"   Recommended approaches:")
        print(f"   • Pairs Trading (statistical arbitrage)")
        print(f"   • Bollinger Bands reversal")
        print(f"   • RSI/Stochastic oversold/overbought")
        print(f"   • Mean reversion on specific factors")
        print(f"\n   Avoid:")
        print(f"   • Trend following strategies")
        print(f"   • Breakout strategies")

    elif result.strategy == StrategyRecommendation.TREND_FOLLOWING:
        print(f"\n   ✅ USE TREND FOLLOWING STRATEGIES")
        print(f"   Recommended approaches:")
        print(f"   • Moving average crossovers")
        print(f"   • Breakout strategies")
        print(f"   • Momentum strategies")
        print(f"   • Trend following on specific factors")
        print(f"\n   Avoid:")
        print(f"   • Mean reversion strategies")
        print(f"   • Counter-trend strategies")

    else:  # NEUTRAL
        print(f"\n   ✅ USE NEUTRAL STRATEGIES")
        print(f"   Recommended approaches:")
        print(f"   • Market making")
        print(f"   • Delta-neutral strategies")
        print(f"   • Volatility trading")
        print(f"   • Options strategies (theta decay)")
        print(f"\n   Note:")
        print(f"   • Market appears efficient - no clear directional edge")

    # Risk management advice
    print(f"\n⚠️  Risk Management:")
    if result.hurst_exponent < 0.3:
        print(f"   • Strong mean reversion - use wider stops")
        print(f"   • Consider position sizing based on deviation")
    elif result.hurst_exponent > 0.7:
        print(f"   • Strong trend - use trailing stops")
        print(f"   • Let winners run, cut losers quickly")
    else:
        print(f"   • Moderate regime - use standard risk management")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("HURST EXPONENT ANALYZER - EXAMPLES")
    print("="*80)

    # Display analyzer info
    info = get_analyzer_info()
    print(f"\n🔧 Analyzer Configuration:")
    print(f"   Numba Available: {info['numba_available']}")
    print(f"   Methods: {', '.join(info['methods_available'])}")
    print(f"   Performance: {info['expected_performance']}")
    print(f"\n📚 Compliance:")
    for compliance_item in info['compliance']:
        print(f"   • {compliance_item}")

    # Run examples (comment out any you want to skip)
    try:
        example_1_basic_calculation()
    except Exception as e:
        logger.error(f"Example 1 failed: {e}")

    try:
        example_2_full_analysis()
    except Exception as e:
        logger.error(f"Example 2 failed: {e}")

    try:
        example_3_compare_symbols()
    except Exception as e:
        logger.error(f"Example 3 failed: {e}")

    try:
        example_4_regime_change_detection()
    except Exception as e:
        logger.error(f"Example 4 failed: {e}")

    try:
        example_5_synthetic_data()
    except Exception as e:
        logger.error(f"Example 5 failed: {e}")

    try:
        example_6_strategy_selection_guide()
    except Exception as e:
        logger.error(f"Example 6 failed: {e}")

    print("\n" + "="*80)
    print("EXAMPLES COMPLETE")
    print("="*80)
    print("\n💡 Key Takeaways:")
    print("   • Hurst Exponent identifies market regime (H < 0.5: mean-reverting, H > 0.5: trending)")
    print("   • Use appropriate strategies for each regime")
    print("   • Monitor for regime changes to adapt your approach")
    print("   • Combine with other analysis techniques for best results")
    print("\n")


if __name__ == "__main__":
    main()
