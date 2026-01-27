# Stop-Loss Bug Fix Quick Reference

## 🚨 CRITICAL - DO NOT DEPLOY TO PRODUCTION

The stop-loss implementation has **6 CRITICAL BUGS** that could cause:
- Uncontrolled catastrophic losses
- Incorrect profit/loss reporting
- Positions not closing when expected

---

## Bug Fix Priority

### 🔴 P0 - FIX IMMEDIATELY (Production Blocker)

#### Bug #1: Catastrophic Loss Not Prevented
**Test**: `test_stop_loss_prevents_catastrophic_loss`
**File**: `app/backtesting/engine.py::_close_position()` (lines 1277-1373)
**Issue**: 50% crash causes >10% loss (should limit to ~5-7%)
**Fix**: Ensure stop-loss execution price limits loss to configured percentage

#### Bug #2: P&L Calculation Incorrect
**Test**: `test_stop_loss_with_commission_and_slippage`
**File**: `app/backtesting/engine.py::_close_position()` (lines 1308-1341)
**Issue**: Capital INCREASES after stop-loss (should decrease)
**Fix**: Review P&L formula - should be: `pnl = proceeds - cost - commissions - slippage`

#### Bug #3: Simultaneous SL/TP Not Handled
**Test**: `test_stop_loss_and_take_profit_same_bar`
**File**: `app/backtesting/engine.py::_check_exit_conditions()` (lines 1232-1275)
**Issue**: Position stays open when both SL and TP hit in same bar
**Fix**: Add explicit check - if both hit, close immediately (pessimistic: SL priority)

### 🟠 P1 - FIX THIS WEEK

#### Bug #4: Take-Profit Exact Threshold
**Test**: `test_take_profit_exact_threshold`
**File**: `app/backtesting/engine.py::_check_exit_conditions()` (line 1267-1274)
**Issue**: Take-profit at exact threshold doesn't trigger
**Fix**: Ensure `current_price >= take_profit_price` triggers at exact equality

#### Bug #5: Premature Stop-Loss Trigger
**Test**: `test_stop_loss_one_tick_above`
**File**: `app/backtesting/engine.py::_check_exit_conditions()` (line 1256-1263)
**Issue**: Stop-loss triggers ABOVE threshold
**Fix**: Check which price field is used (bid/ask/close/last) and fix comparison

### 🟡 P2 - FIX NEXT WEEK

#### Bug #6: Wide Stop-Loss Precision
**Test**: `test_wide_stop_loss_15_percent`
**File**: `app/backtesting/engine.py::_check_exit_conditions()` or `_close_position()`
**Issue**: 15% SL allows 20% loss
**Fix**: Account for slippage/commission in stop-loss threshold calculation

---

## Code Locations

### Primary Files to Modify

**File**: `/app/backtesting/engine.py`

**Function 1**: `_check_exit_conditions()` (lines 1232-1275)
```python
def _check_exit_conditions(self, market_data: Any):
    """Check for stop loss and take profit conditions."""
    # BUGS HERE:
    # - Simultaneous SL/TP not handled (Bug #3)
    # - Take-profit exact threshold (Bug #4)
    # - Premature SL trigger (Bug #5)
    # - Wide SL precision (Bug #6)
```

**Function 2**: `_close_position()` (lines 1277-1373)
```python
def _close_position(self, symbol: str, timestamp: datetime, reason: str, current_price: Decimal = None):
    """Close a position completely."""
    # BUGS HERE:
    # - Catastrophic loss not prevented (Bug #1)
    # - P&L calculation incorrect (Bug #2)
```

---

## Quick Fix Steps

### Step 1: Fix P&L Calculation (Bug #2)

**Current** (line 1340):
```python
pnl = total_sell_proceeds - total_buy_cost - total_commission_cost - slippage_cost_exit
```

**Debug**:
```python
# Add logging to see actual values
logger.info(f"DEBUG: total_sell_proceeds={total_sell_proceeds}")
logger.info(f"DEBUG: total_buy_cost={total_buy_cost}")
logger.info(f"DEBUG: total_commission_cost={total_commission_cost}")
logger.info(f"DEBUG: slippage_cost_exit={slippage_cost_exit}")
logger.info(f"DEBUG: calculated_pnl={pnl}")
```

**Expected**:
- After stop-loss: pnl should be NEGATIVE
- Capital should DECREASE

### Step 2: Fix Catastrophic Loss Protection (Bug #1)

**Current** (line 1256-1263):
```python
if self.config.stop_loss_percentage:
    stop_loss_price = entry_price * (
        Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
    )
    if current_price <= stop_loss_price:
        self._close_position(
            market_data.symbol, market_data.timestamp, "stop_loss", current_price
        )
```

**Issue**: When price crashes from $100 to $50, stop-loss at $95 should trigger, but position might close at $50.

**Fix Options**:
1. Use `stop_loss_price` instead of `current_price` for execution
2. Add max loss check in `_close_position()`
3. Implement limit order at stop-loss price

### Step 3: Fix Simultaneous SL/TP (Bug #3)

**Current** (lines 1256-1275):
```python
# Check stop loss
if self.config.stop_loss_percentage:
    stop_loss_price = entry_price * (
        Decimal("1") - self.config.stop_loss_percentage / Decimal("100")
    )
    if current_price <= stop_loss_price:
        self._close_position(...)
        return  # <-- Returns immediately

# Check take profit
if self.config.take_profit_percentage:
    take_profit_price = entry_price * (
        Decimal("1") + self.config.take_profit_percentage / Decimal("100")
    )
    if current_price >= take_profit_price:
        self._close_position(...)
        return
```

**Issue**: When a bar has Low=$94 (hit SL) and High=$111 (hit TP), only one condition is checked.

**Fix**:
```python
# Check BOTH conditions first
hit_stop_loss = False
hit_take_profit = False

if self.config.stop_loss_percentage:
    stop_loss_price = entry_price * (1 - self.config.stop_loss_percentage / 100)
    # Use low price for stop-loss check
    if hasattr(market_data, 'low') and market_data.low <= stop_loss_price:
        hit_stop_loss = True

if self.config.take_profit_percentage:
    take_profit_price = entry_price * (1 + self.config.take_profit_percentage / 100)
    # Use high price for take-profit check
    if hasattr(market_data, 'high') and market_data.high >= take_profit_price:
        hit_take_profit = True

# Pessimistic execution: if both hit, prioritize stop-loss
if hit_stop_loss and hit_take_profit:
    self._close_position(..., reason="stop_loss_pessimistic", ...)
    return
elif hit_stop_loss:
    self._close_position(..., reason="stop_loss", ...)
    return
elif hit_take_profit:
    self._close_position(..., reason="take_profit", ...)
    return
```

---

## Testing After Fixes

### Run All Tests
```bash
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py -v
```

### Expected Results After P0 Fixes
- All 9 currently passing tests should still pass ✅
- `test_stop_loss_prevents_catastrophic_loss` should pass ✅
- `test_stop_loss_with_commission_and_slippage` should pass ✅
- `test_stop_loss_and_take_profit_same_bar` should pass ✅

### Expected Results After P1 Fixes
- `test_take_profit_exact_threshold` should pass ✅
- `test_stop_loss_one_tick_above` should pass ✅

### Expected Results After P2 Fixes
- `test_wide_stop_loss_15_percent` should pass ✅

**Target**: 15/15 tests passing ✅

---

## Validation Checklist

Before deploying to production, ensure:

- [ ] All 15 tests pass
- [ ] Catastrophic loss (50% crash) is limited to configured stop-loss percentage
- [ ] P&L is negative after stop-loss (not positive)
- [ ] Capital decreases after stop-loss (not increases)
- [ ] Positions close when both SL and TP hit in same bar
- [ ] Take-profit triggers at exact threshold
- [ ] Stop-loss does NOT trigger above threshold
- [ ] Wide stop-loss enforces maximum loss (with slippage tolerance)

---

## Files Reference

### Test File
`/tests/unit/backtesting/test_stop_loss_critical.py`

### Documentation
- `/STOP_LOSS_TEST_RESULTS.md` - Detailed bug analysis
- `/STOP_LOSS_TEST_SUMMARY.md` - Executive summary
- `/STOP_LOSS_QUICK_REFERENCE.md` - This file

### Engine File
`/app/backtesting/engine.py`

---

## Contact

**Created**: 2026-01-27
**Purpose**: Fix critical stop-loss bugs before production deployment
**Status**: P0 bugs identified, fixes pending

---

## Appendix: Test Commands

```bash
# Run specific failing test
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py::TestStopLossCritical::test_stop_loss_prevents_catastrophic_loss -vv

# Run all critical tests
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py::TestStopLossCritical -v

# Run edge case tests
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py::TestStopLossEdgeCases -v

# Run different config tests
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py::TestStopLossWithDifferentConfigs -v

# Run with coverage
python -m pytest tests/unit/backtesting/test_stop_loss_critical.py --cov=app.backtesting.engine --cov-report=html
```
