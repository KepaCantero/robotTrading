# Decimal Precision Fix Report

## Issue Identified

The codebase was using `round(price, 2)` for price rounding, which causes **data loss and incorrect trading decisions** for:
- **Forex pairs** (4-5 decimal places, e.g., EUR/USD 1.08452)
- **Crypto pairs** (8 decimal places, e.g., SAT/BTC 0.00001235)

## Impact

Before fix:
```python
price = 0.0000123456789  # SAT/BTC price
rounded = round(price, 2)  # Returns 0.0 - COMPLETE DATA LOSS!
```

After fix:
```python
from app.core.decimal_utils import round_price

price = 0.0000123456789  # SAT/BTC price
rounded = round_price(price, "crypto", "SAT/BTC")  # Returns 0.00001235
```

## Solution Implemented

### 1. Extended `app/core/decimal_utils.py`

Added asset class-specific precision handling:

- **Equity**: 2 decimals (e.g., $150.25)
- **Forex**: 5 decimals (e.g., EUR/USD 1.08453)
  - JPY pairs: 2 decimals (e.g., USD/JPY 149.12)
- **Crypto**: 8 decimals (e.g., SAT/BTC 0.00001235)
- **Commodity**: 2 decimals
- **Bond**: 4 decimals
- **Index**: 2 decimals

### 2. New Functions

```python
def get_price_precision(asset_class: str = "equity", symbol: Optional[str] = None) -> int:
    """Get appropriate price precision for asset class or specific trading pair."""

def round_price(value: Union[int, float, str, Decimal], 
                asset_class: str = "equity", 
                symbol: Optional[str] = None) -> Decimal:
    """Round price to appropriate precision for asset class - NEVER use round(price, 2)"""

def validate_price_for_asset_class(value: Union[int, float, str, Decimal],
                                   asset_class: str = "equity",
                                   symbol: Optional[str] = None) -> Decimal:
    """Validate and round a price for a specific asset class."""
```

### 3. Updated `realistic_data_generator.py`

- Added `asset_class` parameter to `__init__`
- Replaced all `round(..., 2)` with `round_price(..., asset_class, symbol)`
- Added appropriate minimum spread values per asset class

## Test Results

```python
# Equity
round_price('100.456789', 'equity') => Decimal('100.46')

# Forex EUR/USD (5 decimals)
round_price('1.084527', 'forex', 'EUR/USD') => Decimal('1.08453')

# Forex USD/JPY (2 decimals for Yen pairs)
round_price('149.123', 'forex', 'USD/JPY') => Decimal('149.12')

# Crypto SAT/BTC (8 decimals - CRITICAL)
round_price('0.0000123456789', 'crypto', 'SAT/BTC') => Decimal('0.00001235')

# Crypto BTC/USD (8 decimals)
round_price('45000.123456789', 'crypto', 'BTC/USD') => Decimal('45000.12345679')
```

## Files Still Needing Fixes

The following test files still contain `round(..., 2)` and need updating:
- `tests/integration/backtesting/*.py` (multiple files)
- `tests/unit/backtesting/test_walk_forward_validator.py`

## Migration Guide

**Before:**
```python
price = round(close_price, 2)
```

**After:**
```python
from app.core.decimal_utils import round_price

price = round_price(close_price, asset_class="equity", symbol=symbol)
```

## Critical Warning

**NEVER use `round(price, 2)` for prices in the trading system.**
- It breaks Forex precision
- It destroys Crypto precision  
- It causes incorrect order execution
- It produces invalid backtest results

**Always use `round_price()` from `app.core.decimal_utils`.**
