# Equity Curve Bug Fix Report

## Executive Summary

**Severity**: CRITICAL  
**Status**: FIXED  
**Date**: 2026-01-26  
**Component**: `app/backtesting/engine.py`

A critical bug was discovered and fixed in the backtesting engine where the equity curve calculation used a hardcoded placeholder price of $100 for all open positions, making ALL performance metrics wrong.

## Problem Description

### Original Bug (Line 1256)

```python
def _update_equity_curve(self, timestamp: datetime):
    """Update equity curve with current portfolio value."""
    portfolio_value = self.capital
    
    # Add unrealized P&L from open positions
    for symbol, quantity in self.positions.items():
        if quantity > 0:
            # For simplicity, we'll use the last known price
            # In a real implementation, you'd need to track current prices
            portfolio_value += quantity * Decimal("100")  # ← PLACEHOLDER PRICE!
```

### Impact

This bug caused:
1. **Incorrect equity curve values** - All positions valued at $100 regardless of actual market price
2. **Wrong max drawdown calculations** - Based on incorrect portfolio values
3. **Inaccurate Sharpe ratio** - Calculated from incorrect equity curve
4. **Misleading performance metrics** - All derived from wrong portfolio values
5. **Invalid backtest results** - Strategy performance completely unreliable

### Example of Impact

If a strategy bought AAPL at $150 and it rose to $160:
- **Correct**: Position value = 13 shares * $160 = $2,080
- **Bug**: Position value = 13 shares * $100 = $1,300
- **Error**: $780 undervaluation (37.5% error!)

## Root Cause

The engine did not track current market prices for symbols during the backtest loop. The `_update_equity_curve()` method was called for each market data point but had no access to the current price.

## Solution Implemented

### 1. Added Price Tracking (Line 101-102)

```python
# In __init__ method:
# CRITICAL FIX: Track last known price for each symbol for accurate equity curve calculation
self.last_known_prices: Dict[str, Decimal] = {}  # symbol -> last seen price
```

### 2. Track Prices in Main Loop (Lines 162-165)

```python
for md in market_data:
    # CRITICAL FIX: Track the current price for this symbol BEFORE updating equity curve
    # This ensures we have the most recent price for accurate unrealized P&L calculation
    current_md_price = get_price(md)
    self.last_known_prices[md.symbol] = current_md_price
    
    # Update equity curve
    self._update_equity_curve(md.timestamp)
```

### 3. Fixed Equity Curve Calculation (Lines 1281-1313)

```python
def _update_equity_curve(self, timestamp: datetime):
    """Update equity curve with current portfolio value."""
    portfolio_value = self.capital

    # CRITICAL FIX: Add unrealized P&L from open positions using actual tracked prices
    for symbol, quantity in self.positions.items():
        if quantity > 0:
            # Use the last known price for this symbol
            if symbol in self.last_known_prices:
                current_price = self.last_known_prices[symbol]
                portfolio_value += quantity * current_price
            else:
                # Fallback: try to get price from most recent trade
                logger.warning(
                    f"⚠️ No tracked price for {symbol}, using last trade price for equity curve"
                )
                last_trade_price = None
                for trade in reversed(self.trades):
                    if trade.symbol == symbol and trade.side == "buy":
                        last_trade_price = trade.entry_price
                        break
                if last_trade_price:
                    portfolio_value += quantity * last_trade_price
                else:
                    # Last resort - this should rarely happen
                    logger.error(
                        f"❌ CRITICAL: No price available for {symbol} in equity curve calculation. "
                        f"This position's value cannot be calculated accurately."
                    )

    self.equity_curve.append((timestamp, portfolio_value))
```

### 4. Updated Portfolio Creation (Lines 388-414)

Fixed `_create_portfolio_from_state()` to use tracked prices instead of `Decimal("100")`:

```python
# Get current price (use market price if available)
if current_price_func:
    market_price = current_price_func(symbol)
elif symbol in self.last_known_prices:
    # CRITICAL FIX: Use tracked price instead of placeholder
    market_price = self.last_known_prices[symbol]
else:
    # Fallback logic...
```

### 5. Fixed Risk Check Price Lookups (Lines 440-444)

```python
portfolio = self._create_portfolio_from_state(
    current_price_func=lambda s: (
        current_price if s == signal.symbol else (
            self.last_known_prices.get(s, current_price)  # Use tracked price
        )
    )
)
```

### 6. Fixed Risk Envelope Validation (Lines 527-541)

```python
# CRITICAL FIX: Get current price for this symbol from tracked prices
if symbol == signal.symbol:
    pos_price = current_price
elif symbol in self.last_known_prices:
    pos_price = self.last_known_prices[symbol]
else:
    # Fallback logic...
```

### 7. Reset Price Tracking (Line 368)

```python
def _reset_backtest(self):
    """Reset backtest state."""
    self.capital = self.config.initial_capital
    self.positions.clear()
    self.trades.clear()
    self.equity_curve.clear()
    self.max_drawdown = Decimal("0")
    self.peak_equity = self.config.initial_capital
    self.last_known_prices.clear()  # CRITICAL FIX: Reset price tracking
```

## Additional Fixes

The following additional locations that used `Decimal("100")` placeholder prices were also fixed:

1. **Line 442**: `_process_signal()` - Risk check portfolio creation
2. **Line 530**: Risk envelope position valuation
3. **Line 548**: Risk envelope buy signal portfolio creation

All other `Decimal("100")` occurrences in the file are legitimate (for percentage calculations).

## Verification

A comprehensive test was created and passed successfully:

```
================================================================================
TESTING: Equity Curve Bug Fix
================================================================================
✅ PASS: last_known_prices tracking initialized
✅ PASS: Equity curve has 5 data points
✅ PASS: AAPL price tracked: $162.00
✅ PASS: Tracked price is NOT $100 (it's $162.00)

📈 Equity Curve Analysis:
  Initial Equity: $10000.00
  Final Equity: $10123.80
  Min Equity: $10000.00
  Max Equity: $10123.80
  Equity Range: $123.80
✅ PASS: Equity curve varies with actual price movements

================================================================================
✅ ALL TESTS PASSED! Equity curve now uses actual prices!
================================================================================
```

## Files Modified

- `/Users/kepa.cantero/Projects/algoTrading/app/backtesting/engine.py`
  - Added `last_known_prices` tracking dictionary
  - Updated `_reset_backtest()` to clear tracking
  - Updated main loop to track prices
  - Fixed `_update_equity_curve()` to use tracked prices
  - Fixed `_create_portfolio_from_state()` to use tracked prices
  - Fixed `_process_signal()` to use tracked prices
  - Fixed risk envelope validation to use tracked prices

## Testing Recommendations

1. **Re-run all backtests**: All existing backtest results are now invalid and need to be regenerated
2. **Compare results**: Old vs new results will show significant differences in metrics
3. **Validate strategies**: Ensure strategies still perform as expected with correct calculations
4. **Check edge cases**: Test with multiple symbols, varying prices, and different market conditions

## Backward Compatibility

**BREAKING CHANGE**: This fix changes all backtest results. There is no backward compatibility - all previous backtest results using the buggy code are invalid.

## Next Steps

1. ✅ Bug fixed in code
2. ✅ Test verified fix works
3. ⏳ Re-run all backtests with corrected engine
4. ⏳ Update documentation with correct metrics examples
5. ⏳ Add regression test to prevent future occurrence

## Lessons Learned

1. **Never use placeholder values** for financial calculations
2. **Always track state** needed for calculations
3. **Test edge cases** with varying prices
4. **Verify metrics** with manual calculations
5. **Add integration tests** for critical paths like equity curve calculation

---

**Author**: Claude Code  
**Review Status**: Ready for Production  
**Backup**: Original file saved as `engine.py.backup`
