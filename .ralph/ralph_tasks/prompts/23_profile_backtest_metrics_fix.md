# Task 23: Profile Backtest Metrics Fix - Implementation Prompt

## Current Status (2026-02-21)

| Metric | Current Value | Target | Status |
|--------|---------------|--------|--------|
| Sharpe | -0.67 | > 0.5 | Needs improvement |
| Win Rate | 0% | > 40% | Critical |
| Return | N/A (bug) | > 0% | Fix key |
| MaxDD | -18.29% | < 25% | OK |

## Confirmed Diagnosis

**ROOT PROBLEM:** Signal generation logic is fundamentally flawed for 2021 bull market.

**SYMPTOMS:**
- 0% win rate
- All trades hit stop loss
- Sharpe -0.67 (negative but in coherent range)

**CAUSE:**
The momentum_modular strategy is configured for mean-reversion:
- RSI buy_threshold = 30 (only buys on oversold)
- In bull market, stocks are rarely oversold
- Result: few signals, and when they enter, they go against trend

---

## Auto-Iteration Mechanism

```
+------------------------------------------------------------------+
|                    AUTO-ITERATION LOOP                            |
|                                                                   |
|  +----------+    +----------+    +----------+    +----------+     |
|  | Analyze  |--->|  Apply   |--->| Validate |--->| Decision |     |
|  | Signals  |    |   Fix    |    |  Metrics |    |  Logic   |     |
|  +----------+    +----------+    +----------+    +-----+----+     |
|       ^                                                |          |
|       |           +------------------------------------+          |
|       |           |                                                 |
|       |     +-----v-----+                                           |
|       |     |  Sharpe   |                                           |
|       +-----|  < 0.5?   |                                           |
|             | Win Rate  |                                           |
|             |  < 40%?   |                                           |
|             +-----------+                                           |
|                  |                                                  |
|         YES     |     NO                                            |
|       (iterate) |   (complete)                                      |
|                  v                                                  |
+------------------------------------------------------------------+
```

### State Variables
- `current_best_sharpe`: -0.67 (baseline)
- `current_best_win_rate`: 0% (baseline)
- `target_sharpe`: 0.5
- `target_win_rate`: 0.40

---

## Implementation Steps

### PHASE 1: Quick Fix - Test Bug (5 min)

**File:** `tests/backtesting/test_profile_backtest_simple.py`

```python
# Line 82 - BEFORE:
print(f"  Return: {result.baseline_results.get('total_return', 'N/A')}%")

# Line 82 - AFTER:
print(f"  Return: {result.baseline_results.get('return_pct', 'N/A')}%")

# Line 88 - BEFORE:
print(f"  Return: {result.optimization_results.get('total_return', 'N/A')}%")

# Line 88 - AFTER:
print(f"  Return: {result.optimization_results.get('return_pct', 'N/A')}%")
```

### PHASE 2: Fix Filter Configuration (30 min)

**File:** `config/strategies/momentum_modular.yaml`

**Problem:** Filters configured for mean-reversion, not for bull market.

**Solution:** Adjust RSI thresholds for trend-following:

```yaml
filters:
  rsi_filter:
    enabled: true
    parameters:
      period: 14
    # NEW: Adaptive thresholds by regime
    adaptive_thresholds:
      trend_up:           # Bull market
        buy_threshold: 45   # Allow buys in trend (was 30)
        sell_threshold: 85  # Only sell at extremes (was 70)
      trend_down:
        buy_threshold: 30
        sell_threshold: 70
      range:
        buy_threshold: 35
        sell_threshold: 65
```

### PHASE 3: Fix Entry Logic (1-2 hours)

**Files:**
- `app/strategies/momentum_modular/decision/decision_engine.py`
- `app/strategies/momentum_modular/strategy.py`

**Changes:**

1. **Trend Confirmation** - Only trade in trend direction:
```python
def _confirm_trend(self, data: pd.DataFrame) -> bool:
    price = data['close'].iloc[-1]
    ema_50 = data['ema_50'].iloc[-1]
    return price > ema_50  # Bull trend
```

2. **Pullback Entry** - Do not buy at peaks:
```python
def _is_pullback(self, data: pd.DataFrame) -> bool:
    recent_high = data['high'].rolling(20).max().iloc[-1]
    current_price = data['close'].iloc[-1]
    pullback_pct = (recent_high - current_price) / recent_high
    return 0.02 <= pullback_pct <= 0.05
```

### PHASE 4: Fix Stop Loss (30 min)

**File:** `config/strategies/momentum_modular.yaml`

```yaml
risk_manager:
  stop_loss:
    method: "atr"           # Change from fixed % to ATR-based
    atr_multiplier: 2.0
    max_stop_loss_pct: 0.08

  take_profit:
    value: 0.12             # Increase from 5% to 12%
    min_risk_reward: 2.0    # Ensure 2:1 R:R minimum
```

### PHASE 5: Validate (10 min)

```bash
python tests/backtesting/test_profile_backtest_simple.py
```

**Success criteria:**
- Sharpe > 0.5
- Win Rate > 40%
- Return calculated (not N/A)

---

## Learning from Failed Attempts

### Attempt History
Save to `.ralph/outputs/23_attempt_history.json`:

```json
[
  {
    "iteration": 1,
    "action": "fixed_sharpe_calculation",
    "sharpe_before": -1099,
    "sharpe_after": -0.67,
    "result": "SUCCESS"
  },
  {
    "iteration": 2,
    "action": "fix_test_bug_return_key",
    "result": "PENDING"
  }
]
```

### Strategy Selection Based on History

| If Previous Was | And Result | Next Try |
|-----------------|------------|----------|
| Test bug fix | N/A resolved | Fix filters |
| Filter fix | No improvement | Fix entry logic |
| Entry fix | No improvement | Fix stop loss |
| All tried | No improvement | Review strategy completely |

---

## Expected Output

When finished, the test should show:

```
================================================================================
RESULTS
================================================================================
Profile ID: xxx
Ready for Paper Trading: True
Recommendation: APPROVED

Baseline:
  Sharpe: 0.5+
  Return: X%
  MaxDD: < 25%

Optimized:
  Sharpe: 0.7+
  Return: Y%

Improvement:
  Sharpe: Z%
```

## Files to Modify

1. `tests/backtesting/test_profile_backtest_simple.py` - Fix return key
2. `config/strategies/momentum_modular.yaml` - Fix filter thresholds
3. `app/strategies/momentum_modular/decision/decision_engine.py` - Fix entry logic
4. `config/backtesting/profile_optimization.yaml` - Fix parameter ranges

## Success Criteria

| Metric | Minimum Acceptable | Target |
|--------|-------------------|--------|
| Sharpe | 0.5 | 1.0+ |
| Win Rate | 40% | 50%+ |
| Return | 0% | 5%+ |
| MaxDD | < 30% | < 20% |
| Status | APPROVED | - |
