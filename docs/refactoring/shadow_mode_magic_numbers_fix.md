# Shadow Mode Magic Numbers Refactoring

## Summary

Successfully eliminated all magic numbers from `shadow_mode.py` by integrating with the centralized configuration system. All hardcoded values have been replaced with configurable parameters while maintaining backward compatibility.

## Changes Made

### 1. Created New Configuration Module

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/shared/config/params/shadow_mode_config.py`

Added `ShadowModeConfigParams` class with all shadow mode parameters:
- Simulation settings (slippage_bps, fill_delay_ms, probabilities)
- Safety limits (max_shadow_orders_per_day)
- Price fallback settings (fallback_price, enable_fallback_price)
- Advanced simulation parameters (jitter ranges, partial fill percentages)

**Magic Numbers Replaced**:
- `5` → `slippage_bps: int = 5`
- `100` → `fill_delay_ms: int = 100`
- `0.1` → `partial_fill_probability: float = 0.1`
- `0.01` → `rejection_probability: float = 0.01`
- `1000` → `max_shadow_orders_per_day: int = 1000`
- `Decimal("100.00")` → `fallback_price: Decimal = Decimal("100.00")`
- `-20, 50` → `fill_delay_jitter_min_ms/max_ms: int = -20/50`
- `0.5, 0.9` → `partial_fill_min_pct/max_pct: float = 0.5/0.9`

### 2. Updated Centralized Configuration

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/shared/config/centralized_config.py`

- Added import for `ShadowModeConfigParams`
- Added `shadow_mode` field to `CentralizedConfig` class

### 3. Refactored ShadowModeConfig Dataclass

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/domain/services/shadow_mode.py`

**Lines 87-129**: Updated `ShadowModeConfig` to:
- Load defaults from centralized config via `__post_init__`
- Allow override of any parameter
- Maintain backward compatibility

**Before**:
```python
slippage_bps: int = 5  # Magic number
fill_delay_ms: int = 100  # Magic number
```

**After**:
```python
slippage_bps: int = None  # Loaded from centralized config
fill_delay_ms: int = None  # Loaded from centralized config

def __post_init__(self):
    config = get_config().shadow_mode
    if self.slippage_bps is None:
        self.slippage_bps = config.slippage_bps
```

### 4. Fixed Fallback Price Handling

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/domain/services/shadow_mode.py`

**Lines 535-560**: Replaced magic fallback price with proper error handling

**Before**:
```python
try:
    ticker = await self.broker.get_live_ticker(symbol)
    base_price = ticker.last
except Exception:
    base_price = price or Decimal("100.00")  # Magic number!
```

**After**:
```python
try:
    ticker = await self.broker.get_live_ticker(symbol)
    base_price = ticker.last
except Exception as e:
    if price is not None:
        base_price = price
        logger.warning(f"Using requested price {price}. Error: {e}")
    elif config.enable_fallback_price:
        base_price = config.fallback_price
        logger.warning(f"Using fallback price {config.fallback_price}. Error: {e}")
    else:
        raise ValueError(
            f"Cannot determine price for MARKET order: "
            f"broker ticker unavailable and no fallback provided"
        )
```

### 5. Replaced Jitter Magic Numbers

**Lines 511-513**: Replaced hardcoded jitter values

**Before**:
```python
delay_ms = self.config.fill_delay_ms + random.randint(-20, 50)  # Magic numbers!
```

**After**:
```python
config = get_config().shadow_mode
delay_ms = self.config.fill_delay_ms + random.randint(
    config.fill_delay_jitter_min_ms, config.fill_delay_jitter_max_ms
)
```

### 6. Replaced Partial Fill Magic Numbers

**Lines 580-584**: Replaced hardcoded partial fill percentages

**Before**:
```python
fill_pct = random.uniform(0.5, 0.9)  # Magic numbers!
```

**After**:
```python
fill_pct = random.uniform(config.partial_fill_min_pct, config.partial_fill_max_pct)
```

### 7. Enhanced Environment Variable Detection

**Lines 946-1008**: Updated `detect_shadow_mode_from_env()` to:
- Use centralized config as defaults
- Support all new environment variables
- Log all configuration values when enabled

**New Environment Variables**:
- `SHADOW_PARTIAL_FILL_PROB`
- `SHADOW_REJECTION_PROB`
- `SHADOW_MAX_ORDERS`
- `SHADOW_COMPARISON_WINDOW`

## Test Coverage

Created comprehensive test suite in:
`/Users/kepa.cantero/Projects/algoTrading/tests/unit/core/test_shadow_mode_config_refactoring.py`

**Tests verify**:
1. Default config uses centralized values
2. Override values work correctly
3. Fallback price settings exist
4. Simulation parameters are configurable
5. No magic numbers remain in code

**All tests pass**:
- Original shadow mode tests: 33/33 passed
- New refactoring tests: 5/5 passed

## Benefits

1. **Centralized Configuration**: All shadow mode parameters now configurable from one place
2. **Type Safety**: Pydantic validation ensures correct types and ranges
3. **Flexibility**: Easy to adjust parameters per environment
4. **Error Handling**: Better error messages when price unavailable
5. **Documentation**: All parameters documented with descriptions
6. **Testability**: Easier to test with configurable values
7. **Backward Compatibility**: Existing code continues to work

## Configuration Usage

### Using Centralized Config

```python
from app.shared.config.centralized_config import get_config

# Get shadow mode configuration
config = get_config().shadow_mode

# Access parameters
print(config.slippage_bps)  # 5
print(config.max_shadow_orders_per_day)  # 1000
print(config.fallback_price)  # Decimal('100.00')
```

### Using ShadowModeConfig

```python
from app.domain.services.shadow_mode import ShadowModeConfig

# Default config (loads from centralized)
config = ShadowModeConfig()

# Override specific values
config = ShadowModeConfig(
    slippage_bps=10,
    max_shadow_orders_per_day=500
)
```

### Environment Variables

```bash
# Override any parameter
export SHADOW_SLIPPAGE_BPS=10
export SHADOW_FILL_DELAY_MS=200
export SHADOW_MAX_ORDERS=500

# Enable shadow mode
export SHADOW_MODE_ENABLED=true
```

## Files Changed

1. **Created**:
   - `/Users/kepa.cantero/Projects/algoTrading/app/shared/config/params/shadow_mode_config.py`
   - `/Users/kepa.cantero/Projects/algoTrading/tests/unit/core/test_shadow_mode_config_refactoring.py`

2. **Modified**:
   - `/Users/kepa.cantero/Projects/algoTrading/app/shared/config/centralized_config.py`
   - `/Users/kepa.cantero/Projects/algoTrading/app/domain/services/shadow_mode.py`
   - `/Users/kepa.cantero/Projects/algoTrading/tests/unit/core/test_shadow_mode.py`

## Validation

All changes validated by:
- Unit tests (38/38 passed)
- Integration tests with centralized config
- Manual verification of configuration loading
- Backward compatibility checks

## Future Improvements

Potential enhancements:
1. Add YAML configuration file support
2. Add configuration validation on startup
3. Add configuration change notifications
4. Add per-strategy shadow mode settings
5. Add metrics for configuration values
