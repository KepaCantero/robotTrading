# Fallback Values Fix - Implementation Summary

**Date**: 2026-01-26
**Status**: ✅ **COMPLETED**
**Task**: Verify and fix hardcoded fallback values to match profile_optimization.yaml defaults

---

## Issues Found and Fixed

### 1. RSI Buy Threshold Range Mismatch

**Location**: `app/backtesting/profile_batch_backtester.py` lines 1198, 1206

**Before**:
```python
rsi_buy_min, rsi_buy_max = 30, 70  # INCORRECT
```

**After**:
```python
rsi_buy_min, rsi_buy_max = 20, 35  # rsi.buy_threshold: min=20, max=35
```

**Issue**: The old values `30, 70` appeared to be mixing the default buy (30) and sell (70) threshold values, but this was being used as the optimization search range. The correct buy_threshold range from config is `min: 20, max: 35`.

**Config Reference**:
```yaml
threshold_optimization:
  rsi:
    buy_threshold:
      min: 20
      max: 35
      step: 2
      default: 30
```

---

### 2. Volume Ratio Range Mismatch

**Location**: `app/backtesting/profile_batch_backtester.py` lines 1199, 1207

**Before**:
```python
vol_min, vol_max = 1.0, 3.0  # INCORRECT - max was 2x config value
```

**After**:
```python
vol_min, vol_max = 1.0, 1.5  # volume_ratio: min=1.0, max=1.5
```

**Issue**: The old max value `3.0` was 2x the config value of `1.5`, causing the optimization to search a parameter space twice as large as intended.

**Config Reference**:
```yaml
threshold_optimization:
  volume_ratio:
    min: 1.0
    max: 1.5
    step: 0.1
    default: 1.1
```

---

## Changes Made

### File: `app/backtesting/profile_batch_backtester.py`

#### Lines 1186-1198 (Exception Handler Fallback)
```python
except Exception as e:
    logger.warning(f"Failed to load parameter ranges from ProfileConfigLoader: {e}")
    logger.info("Falling back to default parameter ranges")
    # Fallback to hardcoded defaults
    # Values match profile_optimization.yaml threshold_optimization ranges
    rsi_buy_min, rsi_buy_max = 20, 35  # rsi.buy_threshold: min=20, max=35
    vol_min, vol_max = 1.0, 1.5        # volume_ratio: min=1.0, max=1.5
```

#### Lines 1193-1207 (Else Branch Fallback)
```python
else:
    # Use hardcoded defaults when ProfileConfigLoader is not available
    # Values match profile_optimization.yaml threshold_optimization ranges
    logger.info("Using default parameter ranges (ProfileConfigLoader not initialized)")
    # Track fallback
    self._increment_fallback_counter("profile_config_loader")
    rsi_buy_min, rsi_buy_max = 20, 35  # rsi.buy_threshold: min=20, max=35
    vol_min, vol_max = 1.0, 1.5        # volume_ratio: min=1.0, max=1.5
```

### File: `tests/unit/backtesting/test_fallback_values.py` (NEW)

Created comprehensive validation test suite with the following test cases:

1. **`test_rsi_buy_fallback_matches_config`**: Verifies RSI buy threshold values match config
2. **`test_volume_ratio_fallback_matches_config`**: Verifies volume ratio values match config
3. **`test_ema_distance_config_exists`**: Documents EMA distance config (currently unused in optimization)
4. **`test_momentum_config_exists`**: Documents momentum config (currently unused in optimization)
5. **`test_fallback_values_have_config_comments`**: Ensures code has comments referencing config
6. **`test_no_incorrect_hardcoded_values`**: Prevents regression of old incorrect values
7. **Integration tests**: Validate ranges are reasonable and min < max

---

## Verification Results

```
Config values:
  RSI buy: min=20, max=35
  Volume: min=1.0, max=1.5
✓ RSI fallback values correct (20, 35)
✓ Volume fallback values correct (1.0, 1.5)
✓ Old incorrect RSI values removed
✓ Old incorrect volume values removed
All checks passed!
```

---

## Impact Assessment

### Before Fixes
- **RSI optimization range**: 30-70 (incorrect, mixing buy/sell defaults)
- **Volume optimization range**: 1.0-3.0 (2x larger than config)
- **Consequences**: Optimization searching incorrect parameter spaces, potentially suboptimal results

### After Fixes
- **RSI optimization range**: 20-35 (matches config buy_threshold)
- **Volume optimization range**: 1.0-1.5 (matches config)
- **Consequences**: Optimization aligned with configuration intent, correct parameter search spaces

---

## Additional Notes

### Other Available Thresholds (Currently Unused in Optimization)

The following thresholds are defined in `profile_optimization.yaml` but not currently used in the Bayesian optimization fallback code:

1. **EMA Distance**:
   - Range: 0.002 - 0.01
   - Default: 0.005
   - Status: Configured but not used in optimization

2. **Momentum**:
   - Range: 0.01 - 0.03
   - Default: 0.015
   - Status: Configured but not used in optimization

3. **Stochastic RSI**:
   - Oversold: 10-25 (default: 20)
   - Overbought: 75-90 (default: 80)
   - Status: Configured but not used in optimization

**Recommendation**: Consider adding these thresholds to the optimization search space for more comprehensive strategy optimization.

---

## Testing

### Manual Verification
```bash
# Quick verification script
python -c "
import yaml
from pathlib import Path

config_path = Path('config/backtesting/profile_optimization.yaml')
with open(config_path) as f:
    config = yaml.safe_load(f)

threshold_config = config.get('threshold_optimization', {})

# Extract values
rsi_buy_min = threshold_config.get('rsi', {}).get('buy_threshold', {}).get('min', 20)
rsi_buy_max = threshold_config.get('rsi', {}).get('buy_threshold', {}).get('max', 35)
vol_min = threshold_config.get('volume_ratio', {}).get('min', 1.0)
vol_max = threshold_config.get('volume_ratio', {}).get('max', 1.5)

print('Config values:')
print(f'  RSI buy: min={rsi_buy_min}, max={rsi_buy_max}')
print(f'  Volume: min={vol_min}, max={vol_max}')
"
```

### Unit Tests
```bash
# Run fallback values validation test
python -m pytest tests/unit/backtesting/test_fallback_values.py -v
```

---

## Documentation Created

1. **`FALLBACK_VALUES_VERIFICATION_REPORT.md`**: Detailed analysis report with all comparisons
2. **`FALLBACK_VALUES_FIX_SUMMARY.md`**: This implementation summary
3. **`tests/unit/backtesting/test_fallback_values.py`**: Validation test suite

---

## Compliance with Requirements

- ✅ All fallback values now match config defaults
- ✅ Comments added showing where each default comes from
- ✅ Config file NOT changed (as required)
- ✅ Validation test added to prevent future drift
- ✅ Summary of mismatches and fixes provided

---

## Sign-off

- **Developer**: Backend Developer (Polyglot Implementer)
- **Date**: 2026-01-26
- **Status**: ✅ Complete and verified
- **Files Modified**:
  - `app/backtesting/profile_batch_backtester.py` (fixed fallback values)
- **Files Created**:
  - `tests/unit/backtesting/test_fallback_values.py` (validation tests)
  - `FALLBACK_VALUES_VERIFICATION_REPORT.md` (detailed report)
  - `FALLBACK_VALUES_FIX_SUMMARY.md` (this summary)
- **Config Files**: Unchanged (as required)
