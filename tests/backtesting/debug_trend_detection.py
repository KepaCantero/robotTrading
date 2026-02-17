#!/usr/bin/env python3
"""
Debug script to investigate trend detection issues.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np

# Test the TrendDetector's EMA calculation
def test_ema_calculation():
    """Test EMA calculation with sample data."""
    from app.strategies.momentum_modular.modules.market_detectors.trend_detector import TrendDetector

    # Create sample price data that's trending UP
    # Simulate a bull market: prices going from 100 to 150
    prices = np.array([100 + i * 0.5 for i in range(100)])  # 100 to 150

    # Calculate EMAs
    detector = TrendDetector({})
    ema_fast = detector._ema_vectorized(prices, 12)
    ema_slow = detector._ema_vectorized(prices, 26)

    print("=" * 60)
    print("EMA CALCULATION TEST (Bull Market Data)")
    print("=" * 60)
    print(f"Prices: {prices[0]:.2f} -> {prices[-1]:.2f}")
    print(f"Price range: {prices[-1] - prices[0]:.2f} ({((prices[-1] - prices[0]) / prices[0] * 100):.1f}% increase)")
    print()

    if ema_fast is not None and ema_slow is not None:
        print(f"EMA12 (fast): {ema_fast[-1]:.4f}")
        print(f"EMA26 (slow): {ema_slow[-1]:.4f}")
        print(f"Current price: {prices[-1]:.4f}")
        print()
        print(f"Fast > Slow: {ema_fast[-1] > ema_slow[-1]}")
        print(f"Price > Fast: {prices[-1] > ema_fast[-1]}")
        print()

        # Calculate distance
        distance = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1]
        print(f"Distance (fast - slow) / slow: {distance:.4f} ({distance * 100:.2f}%)")

        # Calculate strength
        STRENGTH_DIVISOR = 0.25
        strength = min(1.0, abs(distance) / STRENGTH_DIVISOR)
        print(f"Strength (distance / {STRENGTH_DIVISOR}): {strength:.4f}")
        print()

        # Detect trend
        result = detector.detect(prices.tolist())
        print("DETECTION RESULT:")
        print(f"  Type: {result['type']}")
        print(f"  Strength: {result['strength']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Method: {result['method']}")
    else:
        print("ERROR: Could not calculate EMAs")

    print()

    # Now test with DOWN trending data
    print("=" * 60)
    print("EMA CALCULATION TEST (Bear Market Data)")
    print("=" * 60)

    # Simulate a bear market: prices going from 150 to 100
    prices_down = np.array([150 - i * 0.5 for i in range(100)])  # 150 to 100

    ema_fast_down = detector._ema_vectorized(prices_down, 12)
    ema_slow_down = detector._ema_vectorized(prices_down, 26)

    print(f"Prices: {prices_down[0]:.2f} -> {prices_down[-1]:.2f}")
    print(f"Price range: {prices_down[-1] - prices_down[0]:.2f} ({((prices_down[-1] - prices_down[0]) / prices_down[0] * 100):.1f}% decrease)")
    print()

    if ema_fast_down is not None and ema_slow_down is not None:
        print(f"EMA12 (fast): {ema_fast_down[-1]:.4f}")
        print(f"EMA26 (slow): {ema_slow_down[-1]:.4f}")
        print(f"Current price: {prices_down[-1]:.4f}")
        print()
        print(f"Fast > Slow: {ema_fast_down[-1] > ema_slow_down[-1]}")
        print(f"Price > Fast: {prices_down[-1] > ema_fast_down[-1]}")
        print()

        # Calculate distance
        distance_down = (ema_slow_down[-1] - ema_fast_down[-1]) / ema_fast_down[-1]
        print(f"Distance (slow - fast) / fast: {distance_down:.4f} ({distance_down * 100:.2f}%)")

        # Calculate strength
        strength_down = min(1.0, abs(distance_down) / STRENGTH_DIVISOR)
        print(f"Strength (distance / {STRENGTH_DIVISOR}): {strength_down:.4f}")
        print()

        # Detect trend
        result_down = detector.detect(prices_down.tolist())
        print("DETECTION RESULT:")
        print(f"  Type: {result_down['type']}")
        print(f"  Strength: {result_down['strength']}")
        print(f"  Confidence: {result_down['confidence']}")
        print(f"  Method: {result_down['method']}")

    print()


def test_with_real_data():
    """Test with real market data from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed, skipping real data test")
        return

    from app.strategies.momentum_modular.modules.market_detectors.trend_detector import TrendDetector

    print("=" * 60)
    print("REAL DATA TEST (AAPL 2021)")
    print("=" * 60)

    # Download AAPL data for 2021
    ticker = yf.Ticker("AAPL")
    df = ticker.history(start="2021-01-01", end="2021-12-31")

    if df.empty:
        print("ERROR: No data retrieved")
        return

    prices = df['Close'].values
    print(f"Data points: {len(prices)}")
    print(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Price range: {prices[0]:.2f} -> {prices[-1]:.2f}")
    print(f"Return: {((prices[-1] - prices[0]) / prices[0] * 100):.1f}%")
    print()

    # Detect trend
    detector = TrendDetector({})
    result = detector.detect(prices.tolist())

    print("DETECTION RESULT:")
    print(f"  Type: {result['type']}")
    print(f"  Strength: {result['strength']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Method: {result['method']}")

    if 'metadata' in result:
        print(f"  Metadata: {result['metadata']}")

    # Also check EMAs
    ema_fast = detector._ema_vectorized(prices, 12)
    ema_slow = detector._ema_vectorized(prices, 26)

    if ema_fast is not None and ema_slow is not None:
        print()
        print(f"EMA12 (fast): {ema_fast[-1]:.4f}")
        print(f"EMA26 (slow): {ema_slow[-1]:.4f}")
        print(f"Current price: {prices[-1]:.4f}")
        print(f"Fast > Slow: {ema_fast[-1] > ema_slow[-1]}")
        print(f"Price > Fast: {prices[-1] > ema_fast[-1]}")

        distance = abs(ema_fast[-1] - ema_slow[-1]) / min(ema_fast[-1], ema_slow[-1])
        print(f"Distance: {distance * 100:.2f}%")


def test_short_sequences():
    """Test with short price sequences like at backtest start."""
    from app.strategies.momentum_modular.modules.market_detectors.trend_detector import TrendDetector

    print("=" * 60)
    print("SHORT SEQUENCE TEST (Early Backtest)")
    print("=" * 60)

    detector = TrendDetector({})

    # Test with progressively longer sequences
    for length in [26, 30, 35, 40, 50, 60]:
        # Simulate uptrend
        prices = np.array([100 + i * 0.5 for i in range(length)])

        result = detector.detect(prices.tolist())

        ema_fast = detector._ema_vectorized(prices, 12)
        ema_slow = detector._ema_vectorized(prices, 26)

        if ema_fast is not None and ema_slow is not None:
            distance = abs(ema_fast[-1] - ema_slow[-1]) / min(ema_fast[-1], ema_slow[-1])
            strength = min(1.0, distance / 0.25)

            print(f"Length={length}: Type={result['type']}, Strength={result['strength']:.4f}, "
                  f"Distance={distance*100:.2f}%, CalcStrength={strength:.4f}")
        else:
            print(f"Length={length}: EMAs not available")

    print()


def test_volatile_data():
    """Test with volatile/choppy data that might cause extreme strength values."""
    from app.strategies.momentum_modular.modules.market_detectors.trend_detector import TrendDetector

    print("=" * 60)
    print("VOLATILE DATA TEST")
    print("=" * 60)

    detector = TrendDetector({})

    # Test with data that has a sharp drop (like a crash)
    np.random.seed(42)
    base = np.array([100 + i * 0.3 for i in range(60)])  # Slow uptrend
    crash = np.array([100 - i * 5 for i in range(20)])    # Sharp crash
    prices = np.concatenate([base, crash])

    print(f"Prices: {prices[0]:.2f} -> {prices[-1]:.2f}")
    print(f"Total points: {len(prices)}")
    print()

    result = detector.detect(prices.tolist())

    ema_fast = detector._ema_vectorized(prices, 12)
    ema_slow = detector._ema_vectorized(prices, 26)

    if ema_fast is not None and ema_slow is not None:
        print(f"EMA12: {ema_fast[-1]:.4f}")
        print(f"EMA26: {ema_slow[-1]:.4f}")
        print(f"Price: {prices[-1]:.4f}")
        print(f"Fast > Slow: {ema_fast[-1] > ema_slow[-1]}")
        print(f"Price > Fast: {prices[-1] > ema_fast[-1]}")

        if ema_fast[-1] > ema_slow[-1]:
            distance = (ema_fast[-1] - ema_slow[-1]) / ema_slow[-1]
        else:
            distance = (ema_slow[-1] - ema_fast[-1]) / ema_fast[-1]

        print(f"Distance: {distance*100:.2f}%")
        print(f"Strength: {min(1.0, distance / 0.25):.4f}")

    print()
    print("DETECTION RESULT:")
    print(f"  Type: {result['type']}")
    print(f"  Strength: {result['strength']}")
    print(f"  Confidence: {result['confidence']}")

    print()


if __name__ == "__main__":
    test_ema_calculation()
    test_short_sequences()
    test_volatile_data()
    test_with_real_data()
