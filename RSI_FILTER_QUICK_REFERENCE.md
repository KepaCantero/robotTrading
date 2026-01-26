# RSI Filter Crossover Fix - Quick Reference

## What Changed

### Before (WRONG)
```python
# Buy at bottom (falling knife)
if rsi <= 30:
    return BUY  # Still falling!

# Sell at top (miss gains)
if rsi >= 70:
    return SELL  # Still rising!
```

### After (CORRECT)
```python
# Buy after reversal confirmed
if previous_rsi <= 30 and current_rsi > 30:
    return BUY  # Crossover confirmed!

# Sell after reversal confirmed
if previous_rsi >= 70 and current_rsi < 70:
    return SELL  # Crossover confirmed!
```

## Key Features

1. **Crossover Confirmation**: Waits for RSI to cross threshold, not just touch it
2. **Fallback Mode**: Uses stricter threshold (buy: 28, sell: 72) when no history
3. **Per-Symbol Tracking**: Maintains separate history for each trading symbol
4. **Adaptive Thresholds**: Works with existing market regime detection
5. **Comprehensive Logging**: INFO level logs for all crossover events

## Configuration

```yaml
rsi_filter:
  settings:
    use_crossover: true      # Enable crossover logic (default: true)
    fallback_offset: 2       # Stricter threshold offset (default: 2)
```

## Usage Examples

### Normal Operation
```python
from app.strategies.momentum_modular.modules.filters.rsi_filter import RSIFilter

filter_instance = RSIFilter()

# RSI at 25 (oversold, waiting)
result1 = filter_instance.evaluate(
    indicators={"rsi": 25.0, "symbol": "AAPL"},
    market_context={"type": "balanced"},
    signal_type="BUY"
)
# passed=False, "waiting for crossover"

# RSI crosses to 32 (reversal confirmed!)
result2 = filter_instance.evaluate(
    indicators={"rsi": 32.0, "symbol": "AAPL"},
    market_context={"type": "balanced"},
    signal_type="BUY"
)
# passed=True, "crossover detected"
```

### Managing History
```python
# Clear all history (useful for testing)
RSIFilter.clear_rsi_history()

# Clear specific symbol
RSIFilter.clear_rsi_history(symbol="AAPL")

# View current history
history = RSIFilter.get_rsi_history()
```

## Testing

Run the comprehensive test suite:
```bash
python -m pytest tests/unit/strategies/test_rsi_filter_crossover.py -v
```

Expected: 17 passed

## Expected Impact

### Fewer False Signals
- **Before**: Bought at RSI=25 (still falling)
- **After**: Waits for RSI to cross above 30 (reversal confirmed)

### Better Entry Prices
- **Before**: Caught falling knives
- **After**: Enter after reversal confirmed

### Better Exit Timing
- **Before**: Sold at first overbought sign
- **After**: Wait for trend to reverse

### Reduced Drawdown
- **Before**: Enter too early, ride losses down
- **After**: Wait for confirmation, enter with momentum

## Backward Compatibility

To disable crossover and use old logic:
```yaml
rsi_filter:
  settings:
    use_crossover: false
```

## Files Modified

1. `app/strategies/momentum_modular/modules/filters/rsi_filter.py`
   - Added crossover detection logic
   - Added history tracking
   - Added fallback mode
   - Added logging

2. `config/momentum_filters.yaml`
   - Updated documentation
   - Added crossover settings

3. `tests/unit/strategies/test_rsi_filter_crossover.py` (NEW)
   - 17 comprehensive tests
   - 100% passing

## Next Steps

1. Run backtests comparing old vs new logic
2. Validate in paper trading (2 weeks)
3. Deploy to production with monitoring
4. Measure improvement in win rate and drawdown

## Support

For issues or questions:
- Check logs for crossover events
- Use `RSIFilter.get_rsi_history()` for debugging
- Review test cases for examples
