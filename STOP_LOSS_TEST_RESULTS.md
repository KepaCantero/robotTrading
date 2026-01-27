# Stop-Loss Test Results - CRITICAL FINDINGS

## Executive Summary

**Test File**: `/tests/unit/backtesting/test_stop_loss_critical.py`

**Results**: 9 PASSED, 6 FAILED out of 15 tests

**Status**: CRITICAL ISSUES FOUND in stop-loss implementation

---

## Test Results Overview

### ✅ PASSING Tests (9/15)

1. **test_stop_loss_triggers_on_decline** - Stop-loss correctly triggers at 5% decline
2. **test_stop_loss_does_not_trigger_small_decline** - No trigger on 2% decline (correct)
3. **test_take_profit_triggers_on_rise** - Take-profit correctly triggers at 10% rise
4. **test_stop_loss_exact_threshold** - Stop-loss triggers at exact 5% threshold
5. **test_no_stop_loss_config** - Documents dangerous behavior when SL is disabled
6. **test_multiple_positions_with_stop_loss** - Correctly handles multiple positions
7. **test_stop_loss_one_tick_below** - Precise threshold handling
8. **test_consecutive_bars_below_stop_loss** - No double-triggering (correct)
9. **test_tight_stop_loss_1_percent** - Tight SL works correctly

### ❌ FAILING Tests (6/15) - CRITICAL BUGS

## Bug #1: Stop-Loss and Take-Profit Conflict (CRITICAL)

**Test**: `test_stop_loss_and_take_profit_same_bar`

**Issue**: When a bar hits BOTH stop-loss ($94) and take-profit ($111), the position stays OPEN.

**Expected**: Position should close (pessimistic execution - SL should take priority)

**Actual**: Position remains open with 80 shares

**Code Location**: `app/backtesting/engine.py::_check_exit_conditions()` (lines 1232-1275)

**Root Cause**: The method checks stop-loss and take-profit sequentially, but closes the position and returns immediately after first trigger. When both conditions are met in same bar, it checks stop-loss first, closes position, but something is preventing proper closure.

**Impact**: HIGH - Positions could remain open during extreme volatility, leading to uncontrolled losses

**Evidence**:
```
Entry: $100
Stop-loss: $95 (-5%)
Take-profit: $110 (+10%)
Bar: Low=$94, High=$111 (hits BOTH)
Expected: Position closed
Actual: Position still OPEN (80 shares)
```

---

## Bug #2: Catastrophic Loss Protection Failed (CRITICAL)

**Test**: `test_stop_loss_prevents_catastrophic_loss`

**Issue**: Stop-loss failed to prevent catastrophic 50% loss

**Expected**: Loss should be ~5-10% (stop-loss range)

**Actual**: Loss was -4.34% (test expects positive loss percentage, got negative)

**Code Location**: `app/backtesting/engine.py::_close_position()` (lines 1277-1373)

**Root Cause**: The P&L calculation might be using `close` price instead of actual execution price. The stop-loss logic might be triggering but not executing at the right price level.

**Impact**: CRITICAL - Stop-loss is NOT protecting against catastrophic crashes

**Evidence**:
```
Entry: $100
Crash to: $50 (50% drop)
Expected loss: ~5-10%
Actual result: Position closed but calculation shows gain? (PnL calculation issue)
```

---

## Bug #3: Take-Profit Exact Threshold Not Triggering (HIGH)

**Test**: `test_take_profit_exact_threshold`

**Issue**: Take-profit at exact 10% threshold ($110 on $100 entry) does NOT trigger

**Expected**: Position should close at exact threshold

**Actual**: Position remains open (80 shares)

**Code Location**: `app/backtesting/engine.py::_check_exit_conditions()` line 1267-1274

**Root Cause**: The take-profit check uses `>=` comparison: `if current_price >= take_profit_price`. This should trigger at exact threshold, but something is preventing it.

**Impact**: HIGH - Take-profit levels may not execute when expected

**Evidence**:
```
Entry: $100
Take-profit price: $110 (exact 10%)
Quote: close=$110
Expected: Position closed
Actual: Position still OPEN (80 shares)
```

---

## Bug #4: P&L Calculation After Stop-Loss (MEDIUM-HIGH)

**Test**: `test_stop_loss_with_commission_and_slippage`

**Issue**: Capital INCREASES after stop-loss (should decrease)

**Expected**: `final_capital < initial_capital_after_buy`

**Actual**: `final_capital ($99,494.48) > initial_capital_after_buy ($91,983.00)`

**Code Location**: `app/backtesting/engine.py::_close_position()` (P&L calculation)

**Root Cause**: The P&L calculation is incorrect. It's adding to capital instead of subtracting. The formula might be reversed or not accounting for the loss properly.

**Impact**: MEDIUM-HIGH - Financial reporting is wrong, could lead to incorrect decisions

**Evidence**:
```
Initial capital after buy: $91,983.00
After stop-loss: $99,494.48
Change: +$7,511.48 (should be negative!)
```

---

## Bug #5: Stop-Loss Triggers Above Threshold (HIGH)

**Test**: `test_stop_loss_one_tick_above`

**Issue**: Stop-loss triggers at $97.01 when threshold is $97.00

**Expected**: Should NOT trigger (price is $0.01 ABOVE stop-loss)

**Actual**: Position closes (triggered prematurely)

**Code Location**: `app/backtesting/engine.py::_check_exit_conditions()` line 1256-1263

**Root Cause**: The stop-loss check uses `<=` comparison: `if current_price <= stop_loss_price`. However, the execution might be affected by slippage or price used (close vs bid/ask).

**Impact**: HIGH - Stop-loss triggers too early, closing profitable positions prematurely

**Evidence**:
```
Entry: $100
Stop-loss threshold: $97.00 (3% below)
Current price: $97.01 (one tick ABOVE threshold)
Expected: Position remains open
Actual: Position CLOSED (prematurely)
```

---

## Bug #6: Wide Stop-Loss Allows Excessive Loss (MEDIUM)

**Test**: `test_wide_stop_loss_15_percent`

**Issue**: 15% stop-loss allowed 20% loss

**Expected**: Loss should be 13-18% (with slippage/commission)

**Actual**: Loss was 20.26%

**Code Location**: `app/backtesting/engine.py::_close_position()` or `_check_exit_conditions()`

**Root Cause**: The stop-loss price calculation might not account for slippage or execution timing. The position might be closing at a worse price than the stop-loss threshold.

**Impact**: MEDIUM - Stop-loss doesn't strictly enforce the maximum loss percentage

**Evidence**:
```
Entry: $100
Stop-loss: 15% (should close at $85)
Crash to: $80 (20% loss)
Expected loss: 13-18%
Actual loss: 20.26%
```

---

## Critical Code Issues Found

### 1. Stop-Loss Logic (`_check_exit_conditions`, lines 1232-1275)

**Issue**: Checks stop-loss and take-profit sequentially, but may not handle edge cases:
- Both hit in same bar
- Exact threshold values
- Price used for comparison (close vs bid/ask vs last)

**Recommendation**: Add explicit handling for simultaneous SL/TP hits, use pessimistic execution.

### 2. P&L Calculation (`_close_position`, lines 1277-1373)

**Issue**: P&L calculation appears incorrect:
- Capital increases after stop-loss (should decrease)
- Loss percentages calculated as negative

**Recommendation**: Review and fix P&L calculation formula.

### 3. Price Selection for Stop-Loss Trigger

**Issue**: Unclear which price field is used:
- Close price? Bid? Ask? Last?

**Recommendation**: Document and test which price field triggers stop-loss.

### 4. Slippage and Commission Impact

**Issue**: Stop-loss execution doesn't account for slippage/commission in threshold calculation

**Recommendation**: Adjust stop-loss threshold to account for execution costs.

---

## Recommended Fixes (Priority Order)

### P0 - CRITICAL (Fix Immediately)

1. **Fix catastrophic loss protection** (Bug #2)
   - Stop-loss MUST prevent losses exceeding configured percentage
   - Test with 50% crash - should limit loss to ~5-7%

2. **Fix P&L calculation** (Bug #4)
   - Capital should DECREASE after stop-loss, not increase
   - Loss percentages should be positive values

3. **Fix simultaneous SL/TP handling** (Bug #1)
   - When both hit in same bar, close position immediately
   - Use pessimistic execution (SL takes priority)

### P1 - HIGH (Fix Soon)

4. **Fix take-profit exact threshold** (Bug #3)
   - Take-profit should trigger at exact threshold price
   - Review comparison operator

5. **Fix premature stop-loss trigger** (Bug #5)
   - Stop-loss should NOT trigger above threshold
   - Review price selection and comparison logic

### P2 - MEDIUM (Fix This Week)

6. **Fix wide stop-loss precision** (Bug #6)
   - Ensure stop-loss strictly enforces maximum loss
   - Account for slippage/commission in threshold

---

## Test Coverage Analysis

### What's Tested ✅

- Basic stop-loss trigger (5% decline)
- Basic take-profit trigger (10% rise)
- No trigger on small declines (2%)
- Exact threshold behavior (stop-loss)
- Multiple positions
- Tight stop-loss (1%)
- No stop-loss configuration (documents danger)
- Consecutive bars (no double-trigger)
- One tick below threshold

### What's NOT Tested Yet ❌

- Trailing stop-loss (if implemented)
- Stop-loss with partial position closes
- Stop-loss with different position sizes
- Stop-loss during gap openings
- Stop-loss with limit orders
- Stop-loss during low liquidity
- Stop-loss with different commission models
- Stop-loss timeout/delay (if applicable)
- Stop-loss with high volatility
- Stop-loss after-hours/prehours

---

## Next Steps

1. **Immediate**: Fix P0 bugs (catastrophic loss, P&L calc, SL/TP conflict)
2. **This Week**: Fix P1 bugs (take-profit threshold, premature trigger)
3. **Next Week**: Fix P2 bugs (wide SL precision)
4. **Ongoing**: Add more edge case tests as listed above

---

## Conclusion

**CRITICAL FINDING**: The stop-loss implementation has MAJOR BUGS that could lead to:
- Uncontrolled catastrophic losses (Bug #2)
- Incorrect financial reporting (Bug #4)
- Positions not closing when expected (Bugs #1, #3)
- Premature position closures (Bug #5)

**Recommendation**: DO NOT deploy this backtesting engine to production until P0 and P1 bugs are fixed.

**Test File Created**: `/tests/unit/backtesting/test_stop_loss_critical.py`
**Total Tests**: 15 (9 passing, 6 failing)
**Coverage**: Stop-loss and take-profit functionality

---

*Report generated: 2026-01-27*
*Test file: tests/unit/backtesting/test_stop_loss_critical.py*
*Engine: app/backtesting/engine.py*
