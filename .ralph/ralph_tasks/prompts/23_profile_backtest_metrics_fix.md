# Task 23: Profile Backtest Metrics Fix - Implementation Prompt

## Auto-Iteration Mechanism

This task is designed to **self-iterate and learn** until metrics targets are achieved:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTO-ITERATION LOOP                          │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │Diagnose  │───▶│  Apply   │───▶│ Validate │───▶│ Decision │  │
│  │          │    │   Fix    │    │  Metrics │    │  Logic   │  │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘  │
│       ▲                                               │        │
│       │           ┌───────────────────────────────────┘        │
│       │           │                                            │
│       │     ┌─────▼─────┐                                      │
│       │     │  Sharpe   │                                      │
│       └─────│  < 0.5?   │                                      │
│             └───────────┘                                      │
│                  │                                             │
│         YES     │     NO                                       │
│       (iterate) │   (complete)                                 │
│                  ▼                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Variables de Estado (persistentes entre iteraciones)
- `iteration_count`: Contador de intentos
- `current_best_sharpe`: Mejor Sharpe alcanzado hasta ahora
- `attempt_history`: Historial de enfoques probados
- `target_sharpe`: 0.5 (objetivo mínimo)

### Decision Logic
```python
if current_sharpe >= 0.5:
    return COMPLETE_SUCCESS
elif current_sharpe > previous_best:
    update_best(current_sharpe)
    return ITERATE_WITH_NEW_APPROACH  # Keep improving
elif iteration_count >= max_iterations:
    return COMPLETE_PARTIAL  # Best effort
else:
    return ITERATE_DIFFERENT_APPROACH  # Try something new
```

---

## Objective
Diagnosticar y arreglar el Sharpe ratio negativo extremo y otras métricas pobres
en el profile backtest para lograr que el investor profile sea APPROVED.

**KEY:** Esta tarea se retroalimenta automáticamente. No parar hasta alcanzar
el objetivo o agotar intentos.

## Problem Statement

### Current State (REJECTED)
```
Profile ID: 74f80e26-d1fd-4194-8be7-3a7f13329f84
Duration: 417.54s
Ready for Paper Trading: False
Recommendation: REJECTED: Insufficient performance

Baseline Results:
  Sharpe Ratio: -1099.01 (CRITICAL - extremely poor)
  Return: N/A (not calculated)
  Max Drawdown: -18.29%

Optimized Results:
  Sharpe Ratio: -166.53 (84.8% improvement but still poor)
  Return: N/A

Compliance Checks:
  R6 Overfitting: PASS
  R5 Walk-Forward: PASS
  R7 Monte Carlo: PASS
  DATA-001 Purged CV: PASS
```

### Target State (APPROVED)
```
Sharpe Ratio: > 0.5 (minimum acceptable)
Return: > 0%
Win Rate: > 45%
Max Drawdown: < 25%
Ready for Paper Trading: True
```

## Root Cause Analysis Framework

### 1. Sharpe Ratio = -1099 Indicates:
- Extreme negative returns OR
- Near-zero volatility (division by ~0) OR
- Bug in calculation OR
- No profitable trades

### 2. Return = N/A Indicates:
- Returns not calculated OR
- No closed trades OR
- Error in equity curve construction

### 3. MaxDD = -18.29% Is Acceptable:
- But inconsistent with extreme negative Sharpe
- Suggests trades happened but all/most losing

## Implementation Steps

### Phase 1: Initial Diagnosis (2-3 hours)

#### Step 1.1: Analyze Sharpe Ratio Calculator
```bash
# Find Sharpe calculation
grep -rn "sharpe_ratio" app/backtesting/ --include="*.py"

# Check performance_calculator.py specifically
# Look for potential bugs in:
# - Return calculation
# - Volatility calculation
# - Annualization factor
# - Division by zero handling
```

#### Step 1.2: Verify Input Data
```bash
# Check what symbols are used
cat config/profile_batch_backtest.yaml | grep -A 20 "symbols"

# Check backtest period
cat config/profile_batch_backtest.yaml | grep -A 10 "backtest_period"

# Verify data exists for symbols
ls -la data/
```

#### Step 1.3: Analyze Current Strategy Config
```bash
# Check momentum_modular config
cat config/strategies/momentum_modular.yaml

# Check filter configurations
cat config/strategies/momentum_modular.yaml | grep -A 30 "filters"
```

#### Step 1.4: Review Optimization Parameters
```bash
# Check optimization ranges
cat config/profile_optimization.yaml

# Check if ranges are reasonable
cat config/profile_batch_backtest.yaml | grep -A 30 "optimization"
```

#### Step 1.5: Create Diagnosis Report
Create `.ralph/outputs/23_metrics_diagnosis.md` with findings:
- Root cause identification
- Affected components
- Recommended fixes

### Phase 2: Fix Implementation (4-6 hours)

#### Step 2.1: Fix Sharpe Ratio Calculation (if bug found)
- File: `app/backtesting/performance_calculator.py`
- Verify:
  - Return calculation from equity curve
  - Volatility calculation (std dev of returns)
  - Risk-free rate handling
  - Annualization (typically sqrt(252) for daily)
  - Edge case handling (zero volatility)

#### Step 2.2: Fix Parameter Ranges
- File: `app/backtesting/profile_batch_backtester.py` (lines 671-694)
- File: `config/profile_optimization.yaml`

Current (potentially problematic):
```python
rsi_buy_min, rsi_buy_max = 20, 35  # Too restrictive?
vol_min, vol_max = 1.0, 1.5
```

Recommended adjustments based on diagnosis:

**If too few trades:**
```python
rsi_buy_min, rsi_buy_max = 15, 45  # Wider range
vol_min, vol_max = 0.8, 1.3        # Lower threshold
```

**If all losing trades:**
```python
# Adjust stop_loss and take_profit ranges
stop_loss: (0.02, 0.06)
take_profit: (0.06, 0.15)  # Higher reward potential
```

#### Step 2.3: Update Strategy Configuration
- File: `config/strategies/momentum_modular.yaml`

Key areas to adjust:
```yaml
filters:
  rsi_filter:
    adaptive_thresholds:
      trend_up:
        buy_threshold: 35   # More permissive
      trend_down:
        buy_threshold: 25

  volume_filter:
    thresholds:
      balanced:
        min_volume_ratio: 0.9  # Lower threshold

risk_manager:
  stop_loss:
    value: 0.03
  take_profit:
    value: 0.08
    min_risk_reward: 2.0  # Ensure positive R:R
```

#### Step 2.4: Increase Optimization Trials
```yaml
optimization:
  n_trials: 200  # From 100
  timeout: 1800  # 30 min
```

### Phase 3: Validation (2-3 hours)

#### Step 3.1: Run Test After Each Fix
```bash
python tests/backtesting/test_profile_backtest_simple.py
```

#### Step 3.2: Compare Metrics
Track before/after for each fix:
| Metric | Before | After Fix 1 | After Fix 2 | Target |
|--------|--------|-------------|-------------|--------|
| Sharpe | -1099  | ?           | ?           | > 0.5  |
| Return | N/A    | ?           | ?           | > 0%   |
| MaxDD  | -18%   | ?           | ?           | < 25%  |

#### Step 3.3: Iterate If Needed
- If metrics improve but not enough: adjust more
- If metrics worsen: revert and try different approach
- If stuck: add more diagnostic logging

### Phase 4: Documentation (1-2 hours)

#### Step 4.1: Create Summary Report
File: `.ralph/outputs/23_metrics_fix_summary.md`

Include:
- Root cause(s) identified
- Fixes applied
- Before/after metrics
- Remaining issues (if any)
- Recommendations for future

#### Step 4.2: Update Config Persistence
Verify that when strategy is APPROVED:
- Parameters are persisted to YAML
- CentralizedConfig is updated
- Database stores the results

## Key Files to Modify

1. `app/backtesting/performance_calculator.py` - Sharpe calculation
2. `app/backtesting/profile_batch_backtester.py` - Parameter ranges
3. `config/profile_optimization.yaml` - Optimization config
4. `config/strategies/momentum_modular.yaml` - Strategy config
5. `config/profile_batch_backtest.yaml` - Backtest config

## Success Criteria

1. **Sharpe Ratio** > 0.5 (minimum acceptable for paper trading)
2. **Return** > 0% (any positive return)
3. **Win Rate** > 45%
4. **Max Drawdown** < 25%
5. **Ready for Paper Trading** = True
6. **Compliance Checks** all passing (already passing)

## Common Issues and Solutions

### Issue 1: Zero Volatility
**Symptom:** Division by zero in Sharpe calculation
**Solution:** Add minimum volatility floor (e.g., 0.01)

### Issue 2: No Trades Generated
**Symptom:** Zero trades, N/A return
**Solution:** Relax filter thresholds, especially RSI and volume

### Issue 3: All Losing Trades
**Symptom:** Negative return but trades exist
**Solution:** Adjust stop_loss/take_profit ratio, require min R:R

### Issue 4: Data Issues
**Symptom:** Missing or corrupt price data
**Solution:** Verify data availability, extend date range if needed

---

## Learning from Failed Attempts

This section guides how to learn from previous iterations:

### Attempt History Analysis
Before each new attempt, check `.ralph/outputs/23_attempt_history.json`:

```json
[
  {"iteration": 1, "action": "widened_rsi", "sharpe": -500, "result": "improved"},
  {"iteration": 2, "action": "widened_volume", "sharpe": -300, "result": "improved"},
  {"iteration": 3, "action": "adjusted_stop_loss", "sharpe": -400, "result": "worse"},
  {"iteration": 4, "action": "fixed_sharpe_calc", "sharpe": -50, "result": "improved"}
]
```

### Strategy Selection Based on History

| If Previous Tried | And Result | Next Try |
|-------------------|------------|----------|
| Parameter widening | Improved | Continue widening different params |
| Parameter widening | No change | Try strategy config changes |
| Strategy config | No change | Check for calculation bugs |
| Calculation fix | Improved | Validate and iterate |
| Everything tried | Still negative | Try radical approach (disable filters) |

### Radical Approaches (last resort)
If all else fails:
1. Disable RSI filter entirely
2. Use only EMA crossover signals
3. Reduce to single symbol for testing
4. Extend backtest period significantly

---

## Output
Event: `profile_backtest_metrics_fix.complete` with:
- Status: SUCCESS/NEEDS_ITERATION/PARTIAL/FAILED
- Final metrics
- Files modified
- Recommendations
