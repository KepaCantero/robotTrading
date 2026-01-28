# Compliance Engine Systems Availability Report

**Date:** 2026-01-28
**Status:** 17/21 systems available (81%)
**Goal:** 21/21 systems (100%)

## Executive Summary

The Compliance Engine has **4 missing systems** preventing 100% availability:

1. **ernest_chan** - Missing `get_factor_model` function
2. **execution_engine** - False positive (actually working)
3. **lopez_de_prado** - NumPy 2.x compatibility issue
4. **hull** - Wrong class name in check (`HistoricalVaR` vs `HistoricalVaRCalculator`)

## Root Cause Analysis

### Primary Issue: NumPy 2.x Compatibility

The main blocker is **NumPy 2.0.2** which is incompatible with packages compiled against NumPy 1.x:

```
ImportError: A module that was compiled using NumPy 1.x cannot be run in NumPy 2.0.2
```

**Affected Systems:**
- `lopez_de_prado` - Indirectly imports `matplotlib` via `triple_barrier.py`
- Potentially affects other systems with matplotlib dependencies

**Impact Chain:**
```
meta_labeling → triple_barrier → matplotlib → numpy.core.multiarray (FAILS)
```

### Secondary Issues

1. **Missing Function in factor_models.py**
   - Expected: `get_factor_model()`
   - Actual: File exists but function is missing
   - Location: `/Users/kepa.cantero/Projects/algoTrading/app/services/factor_models.py`

2. **Wrong Class Name in ComplianceEngine Check**
   - Expected: `HistoricalVaR`
   - Actual: `HistoricalVaRCalculator` exists
   - Location: `app/engines/risk_engine/var_calculators/var_calculators.py:254`

3. **ExecutionEngine False Positive**
   - System marked as unavailable but import succeeds
   - Issue likely in the check logic

## Missing Systems Detail

### 1. ernest_chan (MISSING)

**Check Function:**
```python
def _check_chan(self) -> bool:
    try:
        from app.services.regime_detection_chan import get_regime_detector
        from app.services.factor_models import get_factor_model  # MISSING
        return True
    except ImportError:
        return False
```

**Issue:** `get_factor_model` function doesn't exist in `app/services/factor_models.py`

**File Status:** File exists, has classes but no factory function

**Fix Required:** Add `get_factor_model()` function to `app/services/factor_models.py`

### 2. execution_engine (FALSE POSITIVE)

**Check Function:**
```python
def _check_execution_engine(self) -> bool:
    try:
        from app.engines.execution_engine import ExecutionEngine
        return True
    except ImportError:
        return False
```

**Actual Status:** Import works fine

**Issue:** Check logic incorrectly reports False

**Fix Required:** Debug why availability dict shows False when import works

### 3. lopez_de_prado (MISSING - NumPy Issue)

**Check Function:**
```python
def _check_lopez_de_prado(self) -> bool:
    try:
        from app.backtesting.labeling.meta_labeling import get_meta_labeling
        return True
    except ImportError:
        return False
```

**Issue:** Import chain fails due to NumPy 2.x incompatibility

**Import Chain:**
```
meta_labeling → triple_barrier → matplotlib → numpy (FAILS)
```

**Fix Required:** Fix NumPy version (see Solutions section)

### 4. hull (MISSING - Wrong Class Name)

**Check Function:**
```python
def _check_hull(self) -> bool:
    try:
        from app.engines.risk_engine.var_calculators.var_calculators import get_var_calculator
        from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaR  # WRONG NAME
        return True
    except ImportError:
        return False
```

**Actual Class Name:** `HistoricalVaRCalculator` (line 254 in var_calculators.py)

**Fix Required:** Update check to use `HistoricalVaRCalculator`

## Solutions

### Solution 1: Fix NumPy Compatibility (REQUIRED for lopez_de_prado)

**Option A: Downgrade NumPy** (RECOMMENDED)
```bash
pip install 'numpy<2.0'
pip install --force-reinstall matplotlib scipy
```

**Option B: Upgrade matplotlib to NumPy 2.x compatible**
```bash
pip install --upgrade matplotlib
```

**Option C: Rebuild all scientific packages**
```bash
pip install --upgrade --force-reinstall numpy matplotlib scipy pandas
```

### Solution 2: Add Missing get_factor_model Function

Create function in `app/services/factor_models.py`:

```python
def get_factor_model(config: Optional[Dict[str, Any]] = None) -> FactorModel:
    """
    Factory function to get a factor model instance.

    Args:
        config: Configuration dictionary with optional parameters:
            - model_type: Type of factor model ('fama_french_3factor', 'fama_french_5factor', 'apt')
            - lookback_period: Period for factor calculation (default: 252)

    Returns:
        FactorModel instance configured as specified
    """
    config = config or {}
    model_type = config.get('model_type', 'fama_french_3factor')

    if model_type == 'fama_french_3factor':
        return FamaFrenchThreeFactorModel(
            lookback_period=config.get('lookback_period', 252)
        )
    elif model_type == 'fama_french_5factor':
        return FamaFrenchFiveFactorModel(
            lookback_period=config.get('lookback_period', 252)
        )
    elif model_type == 'apt':
        return APTModel(
            lookback_period=config.get('lookback_period', 252)
        )
    else:
        raise ValueError(f"Unknown factor model type: {model_type}")
```

### Solution 3: Fix Hull Check in ComplianceEngine

Update `app/core/compliance_engine.py` line 222:

```python
# OLD (WRONG):
from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaR

# NEW (CORRECT):
from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaRCalculator
```

### Solution 4: Debug execution_engine Check

Investigate why `_check_execution_engine()` returns False when the import works.

## Additional Dependencies (Optional)

These warnings don't block functionality but would enhance features:

```bash
# For GARCH volatility models
pip install arch

# For advanced statistics
pip install statsmodels

# For HMM regime detection
pip install hmmlearn

# For distributed caching
pip install redis
```

## Implementation Priority

1. **HIGH:** Fix NumPy compatibility (unblocks lopez_de_prado)
2. **HIGH:** Add `get_factor_model()` function (unblocks ernest_chan)
3. **MEDIUM:** Fix Hull check class name (unblocks hull)
4. **LOW:** Debug execution_engine false positive
5. **OPTIONAL:** Install additional dependencies (arch, statsmodels, hmmlearn, redis)

## Expected Result

After implementing solutions 1-3:

- **Before:** 17/21 systems (81%)
- **After:** 20/21 systems (95%)
- **After all fixes:** 21/21 systems (100%)

## Files to Modify

1. `app/core/compliance_engine.py` - Fix Hull check (line 222)
2. `app/services/factor_models.py` - Add `get_factor_model()` function
3. `requirements.txt` - Pin NumPy version to `<2.0`

## Testing

After fixes, run:

```bash
python check_systems_availability.py
```

Expected output:
```
Available: 21/21
Percentage: 100%

✅ ALL SYSTEMS AVAILABLE!
```
