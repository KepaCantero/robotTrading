# Hurst Exponent Analyzer - Quick Reference Guide

## What is Hurst Exponent?

The Hurst Exponent (H) measures the long-term memory of a time series and helps determine market regime:

- **H < 0.5**: Mean-reverting (anti-persistent) - Use mean reversion strategies
- **H ≈ 0.5**: Random walk (efficient market) - Use neutral strategies
- **H > 0.5**: Trending (persistent) - Use trend following strategies

## Quick Start

### Basic Usage

```python
from app.services.hurst_exponent_analyzer import (
    calculate_hurst_exponent,
    classify_regime,
    recommend_strategy_from_hurst
)

# Calculate Hurst exponent
hurst = calculate_hurst_exponent(prices)

# Get classification and recommendation
regime = classify_regime(hurst)
strategy = recommend_strategy_from_hurst(hurst)

print(f"Hurst: {hurst:.4f}")
print(f"Regime: {regime.value}")
print(f"Strategy: {strategy.value}")
```

### Full Analysis

```python
from app.services.hurst_exponent_analyzer import HurstExponentAnalyzer

# Create analyzer
analyzer = HurstExponentAnalyzer(
    method="rs",              # R/S analysis (or "variance")
    min_window=10,            # Minimum window size
    max_window_ratio=0.5,     # Max window as ratio of length
    num_windows=20,           # Number of windows to test
    confidence_level=0.95,    # Statistical confidence
    use_returns=True          # Analyze log returns (recommended)
)

# Perform analysis
result = analyzer.analyze(prices, symbol="AAPL", timestamp=datetime.now())

# Access results
print(f"Hurst: {result.hurst_exponent:.4f}")
print(f"Regime: {result.regime.value}")
print(f"Strategy: {result.strategy.value}")
print(f"Confidence: {result.confidence*100:.1f}%")
```

### Detect Regime Changes

```python
# Monitor over time
for timestamp, prices in historical_data:
    analyzer.analyze(prices, symbol="AAPL", timestamp=timestamp)

# Detect changes
change = analyzer.detect_regime_change("AAPL")
if change:
    print(f"Regime changed: {change.old_regime} -> {change.new_regime}")
    print(f"Hurst: {change.old_hurst:.4f} -> {change.new_hurst:.4f}")
```

### Monitor Multiple Symbols

```python
# Analyze multiple symbols
data = {
    "AAPL": aapl_prices,
    "MSFT": msft_prices,
    "GOOGL": googl_prices
}

results = analyzer.monitor_multiple_symbols(data)

# Display results
for symbol, result in results.items():
    print(f"{symbol}: H={result.hurst_exponent:.4f}, {result.strategy.value}")
```

## Strategy Selection Guide

### Mean-Reverting Market (H < 0.5)
**Use**: Mean reversion strategies
- Pairs trading (statistical arbitrage)
- Bollinger Bands reversal
- RSI/Stochastic oversold/overbought
- Mean reversion on factors

**Avoid**: Trend following strategies

### Trending Market (H > 0.5)
**Use**: Trend following strategies
- Moving average crossovers
- Breakout strategies
- Momentum strategies
- Trend following on factors

**Avoid**: Mean reversion strategies

### Random Walk (H ≈ 0.5)
**Use**: Neutral strategies
- Market making
- Delta-neutral strategies
- Volatility trading
- Options strategies (theta decay)

**Note**: Market appears efficient - no clear directional edge

## API Reference

### Functions

#### `calculate_hurst_exponent(series, method="rs", use_returns=True)`
Quick calculation of Hurst exponent.

**Parameters**:
- `series`: Price series (pandas Series, numpy array, or list)
- `method`: "rs" (R/S analysis) or "variance" (variance scaling)
- `use_returns`: Analyze log returns instead of prices (recommended)

**Returns**: `float` - Hurst exponent (0.0 to 1.0)

#### `classify_regime(hurst_exponent, tolerance=0.05)`
Classify market regime from Hurst value.

**Parameters**:
- `hurst_exponent`: Calculated Hurst value
- `tolerance`: Tolerance band around 0.5 (default: 0.05)

**Returns**: `MarketRegime` enum

#### `recommend_strategy_from_hurst(hurst_exponent, tolerance=0.05)`
Get strategy recommendation from Hurst value.

**Parameters**:
- `hurst_exponent`: Calculated Hurst value
- `tolerance`: Tolerance band around 0.5 (default: 0.05)

**Returns**: `StrategyRecommendation` enum

### Classes

#### `HurstExponentAnalyzer`
Comprehensive Hurst analyzer with regime change detection.

**Constructor Parameters**:
- `method`: "rs" or "variance" (default: "rs")
- `min_window`: Minimum window size (default: 10)
- `max_window_ratio`: Max window as ratio of length (default: 0.5)
- `num_windows`: Number of windows to test (default: 20)
- `confidence_level`: Statistical confidence (default: 0.95)
- `use_returns`: Analyze log returns (default: True)

**Methods**:

##### `analyze(series, symbol=None, timestamp=None)`
Perform full Hurst analysis.

**Returns**: `HurstResult` dataclass

##### `detect_regime_change(symbol, lookback_periods=10, threshold=0.1)`
Detect regime changes for a symbol.

**Returns**: `RegimeChange` or `None`

##### `monitor_multiple_symbols(data, detect_changes=True)`
Analyze multiple symbols.

**Returns**: `dict` mapping symbols to `HurstResult`

### Data Classes

#### `HurstResult`
Complete analysis results.

**Attributes**:
- `hurst_exponent` (float): Hurst value
- `regime` (MarketRegime): Classified regime
- `strategy` (StrategyRecommendation): Recommended strategy
- `confidence` (float): Statistical confidence (0-1)
- `method` (str): Calculation method used
- `std_error` (float, optional): Standard error
- `p_value` (float, optional): Statistical significance
- `rs_values` (list, optional): R/S values used
- `window_sizes` (list, optional): Window sizes used

#### `RegimeChange`
Regime transition detection.

**Attributes**:
- `timestamp` (datetime): When change was detected
- `old_regime` (MarketRegime): Previous regime
- `new_regime` (MarketRegime): Current regime
- `old_hurst` (float): Previous Hurst value
- `new_hurst` (float): Current Hurst value
- `confidence` (float): Confidence in detection (0-1)

### Enums

#### `MarketRegime`
- `MEAN_REVERTING`: H < 0.5
- `RANDOM_WALK`: H ≈ 0.5
- `TRENDING`: H > 0.5

#### `StrategyRecommendation`
- `MEAN_REVERSION`: For mean-reverting markets
- `NEUTRAL`: For random walk markets
- `TREND_FOLLOWING`: For trending markets

## Best Practices

1. **Use Log Returns**: Always set `use_returns=True` for better accuracy
2. **Sufficient Data**: Need at least 100-500 data points for reliable results
3. **Monitor Changes**: Track Hurst over time to detect regime changes
4. **Combine Methods**: Use both R/S and variance methods for robustness
5. **Check Confidence**: Low confidence (< 0.7) means unreliable results

## Performance

- **With Numba**: 50-100x faster (recommended)
- **Without Numba**: Pure Python fallback (slower but functional)
- **Typical Speed**: ~20-50ms for 10K data points (with Numba)

## Troubleshooting

### Issue: Hurst ≈ 0.5 for everything
**Solution**: Check if data is stationary. Use `use_returns=True` to analyze log returns.

### Issue: Inconsistent results
**Solution**: Increase `num_windows` for more robust estimation. Check data quality.

### Issue: Very slow calculation
**Solution**: Install Numba for 50-100x speedup: `pip install numba`

## Examples

See `examples/hurst_exponent_example.py` for comprehensive examples including:
1. Basic calculation
2. Full analysis
3. Multi-symbol comparison
4. Regime change detection
5. Synthetic data validation
6. Strategy selection guide

Run examples:
```bash
python examples/hurst_exponent_example.py
```

## Testing

Run tests:
```bash
pytest tests/unit/services/test_hurst_exponent_analyzer.py -v
```

## Compliance

- ✅ Ernest Chan Rule 2.2: Hurst Exponent Analysis
- ✅ Rule 19: High Performance Python (Numba JIT)
- ✅ Rule 3: López de Prado (Statistical Validation)
- ✅ Rule 32: Tsay (Time Series Best Practices)

## Support

For issues or questions:
1. Check the examples: `examples/hurst_exponent_example.py`
2. Run tests: `pytest tests/unit/services/test_hurst_exponent_analyzer.py -v`
3. Review implementation: `app/services/hurst_exponent_analyzer.py`
4. See full report: `HURST_EXPONENT_IMPLEMENTATION_REPORT.md`
