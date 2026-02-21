# Task 23: Profile Backtest Metrics Diagnosis Report

## Executive Summary
**Status**: DIAGNOSIS COMPLETE
**Root Cause Identified**: Two critical issues found
**Recommended Action**: Fix Sharpe calculation + Adjust parameter ranges

## Current State Analysis

### Observed Metrics (from database)
```
Profile: 5f840b75-6198-4597-93a6-1eb9009bcebf
- Baseline Sharpe: -952.81
- Optimized Sharpe: -952.81
- Baseline Return: -16.67%
- Win Rate: 0.0%
- Max Drawdown: -16.67%

Best Parameters Found:
- RSI Threshold: 23
- EMA Short: 18
- EMA Long: 31
- Volume Threshold: 1.14
- Stop Loss: 1.55%
- Take Profit: 18.09%
```

### Key Observations
1. **Win Rate = 0%** - ALL trades are losing
2. **Return = MaxDD** - Consistent with 100% losing trades
3. **Extreme negative Sharpe** - Indicates calculation issue

## Root Cause Analysis

### Issue 1: Sharpe Calculation Bug (CRITICAL)

**Location**: `app/backtesting/services/performance_calculator.py:144-211`

**Problem**:
The `_calculate_sharpe_ratio` method calculates returns per-trade, not per-day:
```python
# Current (WRONG):
returns = []
for i in range(1, len(equity_values)):
    ret = (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
    returns.append(ret)
```

When all trades lose similar amounts (e.g., -2% from stop loss):
- Mean return = -0.02 (per trade)
- Std dev = 0.001 (very small because all trades similar)
- After annualization:
  - `annual_mean = -0.02 * 252 = -5.04`
  - `annual_std = 0.001 * sqrt(252) = 0.0159`
  - `Sharpe = -5.04 / 0.0159 = -317` (extreme!)

**Fix**: Calculate daily returns from equity curve, not per-trade returns.

### Issue 2: Restrictive Parameter Ranges

**Location**:
- `app/backtesting/profile_batch_backtester.py:671-694`
- `config/backtesting/profile_optimization.yaml:305-360`

**Current Ranges**:
```python
rsi_buy_min, rsi_buy_max = 20, 35  # Too restrictive
vol_min, vol_max = 1.0, 1.5        # Requires above-average volume
```

**Problems**:
1. **RSI 20-35** is very restrictive - only trades when deeply oversold
2. **Volume 1.0-1.5** requires above-average volume - reduces signal frequency
3. **Stop loss 1-5%** with **Take profit 5-20%** creates asymmetric risk

**Result**: Very few trades, most getting stopped out before reaching profit target.

## Recommended Fixes

### Fix 1: Sharpe Calculation (HIGH PRIORITY)

Modify `_calculate_sharpe_ratio` to:
1. Build daily equity curve (not just trade points)
2. Calculate daily returns
3. Compute Sharpe from daily return distribution

Alternative (simpler): Use trade-based returns but cap extreme values:
```python
# Add volatility floor to prevent division by near-zero
min_volatility = Decimal("0.01")  # 1% minimum annualized volatility
annual_std = max(annual_std, min_volatility)
```

### Fix 2: Parameter Ranges (MEDIUM PRIORITY)

Widen ranges to generate more trades:

```python
# Recommended:
rsi_buy_min, rsi_buy_max = 15, 45   # More permissive
vol_min, vol_max = 0.7, 1.3         # Lower threshold

# Stop loss / Take profit ratio:
stop_loss: (0.02, 0.06)             # 2-6%
take_profit: (0.06, 0.15)           # 6-15% (min 2:1 R:R)
```

### Fix 3: Strategy Config (MEDIUM PRIORITY)

Update `config/strategies/momentum_modular.yaml`:
```yaml
rsi_filter:
  adaptive_thresholds:
    trend_up:
      buy_threshold: 40    # Raised from 35
    trend_down:
      buy_threshold: 30    # Raised from 25

volume_filter:
  thresholds:
    balanced:
      min_volume_ratio: 0.8  # Lowered from 0.9
```

## Next Steps

1. **Fix Sharpe calculation** - Add volatility floor
2. **Widen parameter ranges** - More trades = better statistics
3. **Re-run backtest** - Validate improvements
4. **Iterate** - If still not meeting targets, try more aggressive changes

## Files to Modify

1. `app/backtesting/services/performance_calculator.py` - Sharpe fix
2. `app/backtesting/profile_batch_backtester.py` - Parameter ranges
3. `config/backtesting/profile_optimization.yaml` - Optimization ranges
4. `config/strategies/momentum_modular.yaml` - Strategy thresholds

---
Generated: 2026-02-21
Iteration: 1
