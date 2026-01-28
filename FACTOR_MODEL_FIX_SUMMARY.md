# Factor Model Factory Function Fix - 2026-01-28

## Summary

Fixed the ernest_chan system by adding the missing `get_factor_model()` factory function to `/Users/kepa.cantero/Projects/algoTrading/app/services/factor_models.py`.

## Problem

The ernest_chan system was failing because:
- The file `/app/services/factor_models.py` existed with classes `FamaFrenchFactorModel` and `APTModel`
- The factory function `get_factor_model()` was missing
- This caused import errors when trying to use the factor models

## Solution

Added the `get_factor_model()` factory function with the following features:

### Function Signature
```python
def get_factor_model(model_type: str = "fama_french", **kwargs)
```

### Supported Model Types

1. **Fama-French Factor Models** (`"fama_french"`, `"ff"`, `"fama-french"`)
   - Default: 3-factor model
   - Supports 5-factor model via `ff_model_type="five_factor"`
   - Supports Carhart 4-factor via `ff_model_type="carhart"`

2. **APT Model** (`"apt"`)
   - Default: 5 factors
   - Customizable via `n_factors` parameter

### Key Design Decisions

1. **Parameter Naming**: Used `ff_model_type` instead of `model_type` to avoid naming collision between the factory function parameter and the `FamaFrenchFactorModel` constructor parameter

2. **Case Insensitive**: Accepts various formats (`"fama_french"`, `"ff"`, `"Fama-French"`)

3. **Default Behavior**: Returns FamaFrenchFactorModel with 3-factor configuration when called without arguments

4. **Error Handling**: Raises `ValueError` with helpful message for unknown model types

### Usage Examples

```python
from app.services.factor_models import get_factor_model

# Default Fama-French 3-factor model
model = get_factor_model()

# Fama-French 5-factor model
model = get_factor_model("fama_french", ff_model_type="five_factor")

# APT model with custom number of factors
apt = get_factor_model("apt", n_factors=5)

# Case-insensitive shortcut
model = get_factor_model("FF")
```

## Testing

All tests passed successfully:
- ✅ Default model creation
- ✅ Explicit Fama-French model with 5-factor configuration
- ✅ APT model with custom factor count
- ✅ Case-insensitive model type handling
- ✅ Proper error handling for invalid model types

## Files Modified

- `/Users/kepa.cantero/Projects/algoTrading/app/services/factor_models.py`
  - Added `get_factor_model()` factory function (lines 736-785)

## Integration

The factory function is now available for use in:
- ernest_chan methods that require factor models
- Statistical arbitrage strategies
- Portfolio risk management
- Factor exposure analysis

## Next Steps

The ernest_chan system should now work correctly. Verify:
1. Integration tests for ernest_chan methods
2. Factor model usage in backtesting
3. Statistical arbitrage strategies
