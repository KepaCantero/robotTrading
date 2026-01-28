# Compliance Engine Systems Availability - Complete Analysis

## Executive Summary

**Current Status:** 17/21 systems available (81%)
**Target:** 21/21 systems (100%)
**Missing Systems:** 4 systems

---

## Missing Systems Identified

### 1. ernest_chan (MISSING - Missing Function)

**Root Cause:** `get_factor_model()` function doesn't exist in `app/services/factor_models.py`

**File Status:**
- File exists at: `/Users/kepa.cantero/Projects/algoTrading/app/services/factor_models.py`
- Contains classes: `FamaFrenchFactorModel`, `APTModel`, `StatisticalArbitrage`
- Missing: Factory function `get_factor_model()`

**Import Check:**
```python
from app.services.factor_models import get_factor_model  # ❌ FAILS
```

**Fix Required:** Add factory function to `app/services/factor_models.py`

---

### 2. execution_engine (FALSE POSITIVE)

**Root Cause:** Import works but check returns False

**Import Check:**
```python
from app.engines.execution_engine import ExecutionEngine  # ✅ WORKS
```

**Issue:** System marked as unavailable in availability dict despite successful import

**Fix Required:** Debug check logic in `SystemAvailability._check_execution_engine()`

---

### 3. lopez_de_prado (MISSING - NumPy Compatibility)

**Root Cause:** NumPy 2.0.2 incompatibility with matplotlib

**Error Chain:**
```
meta_labeling → triple_barrier → matplotlib → numpy.core.multiarray (FAILS)
```

**Full Error:**
```
ImportError: A module that was compiled using NumPy 1.x cannot be run in
NumPy 2.0.2 as it may crash.
```

**Import Check:**
```python
from app.backtesting.labeling.meta_labeling import get_meta_labeling  # ❌ FAILS
```

**Fix Required:** Fix NumPy version compatibility

---

### 4. hull (MISSING - Wrong Class Name)

**Root Cause:** Check imports wrong class name

**Wrong Name:**
```python
from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaR  # ❌
```

**Correct Name:**
```python
from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaRCalculator  # ✅
```

**Location:** Line 254 in `var_calculators.py`

**Fix Required:** Update compliance_engine.py line 222

---

## Solutions

### Solution 1: Fix NumPy Compatibility (CRITICAL - for lopez_de_prado)

**Recommended: Downgrade NumPy**
```bash
pip install 'numpy<2.0'
pip install --force-reinstall matplotlib scipy
```

**Alternative: Upgrade matplotlib**
```bash
pip install --upgrade matplotlib
```

**Why:** NumPy 2.0.2 breaks matplotlib which is imported by triple_barrier.py

---

### Solution 2: Add get_factor_model() Function

**File:** `app/services/factor_models.py`

**Add at end of file:**
```python
def get_factor_model(config: Optional[Dict[str, Any]] = None) -> Union[FamaFrenchFactorModel, APTModel]:
    """
    Factory function to get a factor model instance.

    Args:
        config: Configuration dictionary with optional parameters:
            - model_type: Type of factor model ('fama_french_3factor', 'fama_french_5factor', 'apt')
            - lookback_period: Period for factor calculation (default: 252)
            - n_factors: Number of APT factors (default: 5)

    Returns:
        Factor model instance configured as specified
    """
    from typing import Dict, Any, Union, Optional

    config = config or {}
    model_type = config.get('model_type', 'fama_french_3factor')

    if model_type in ['fama_french_3factor', 'fama_french_5factor', 'carhart']:
        return FamaFrenchFactorModel(
            model_type=model_type,
            lookback_period=config.get('lookback_period', 252)
        )
    elif model_type == 'apt':
        return APTModel(
            n_factors=config.get('n_factors', 5)
        )
    else:
        raise ValueError(f"Unknown factor model type: {model_type}")
```

---

### Solution 3: Fix Hull Check

**File:** `app/core/compliance_engine.py`

**Line 220-225:**
```python
# OLD (WRONG):
def _check_hull(self) -> bool:
    try:
        from app.engines.risk_engine.var_calculators.var_calculators import get_var_calculator
        from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaR  # ❌
        return True
    except ImportError:
        return False

# NEW (CORRECT):
def _check_hull(self) -> bool:
    try:
        from app.engines.risk_engine.var_calculators.var_calculators import get_var_calculator
        from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaRCalculator  # ✅
        return True
    except ImportError:
        return False
```

---

### Solution 4: Debug execution_engine Check

**Investigation needed:**

The import works:
```python
from app.engines.execution_engine import ExecutionEngine  # Works
```

But the check returns False. Need to debug `_check_execution_engine()` in `SystemAvailability`.

**Possible causes:**
- Exception caught by try/except
- Return value issue
- Caching problem

---

## Additional Findings

### Optional Dependencies (Not Blocking)

These packages are missing but don't prevent 100% availability:
- `arch` - GARCH models (has fallback)
- `statsmodels` - Advanced statistics (has fallback)
- `hmmlearn` - HMM regime detection (has fallback)
- `redis` - Distributed caching (has in-memory fallback)

---

## Implementation Priority

| Priority | System | Fix | Impact |
|----------|--------|-----|--------|
| 1 | lopez_de_prado | Fix NumPy | Unblocks meta-labeling |
| 2 | ernest_chan | Add get_factor_model() | Unblocks factor models |
| 3 | hull | Fix class name | Unblocks VaR calculator |
| 4 | execution_engine | Debug check | Fix false positive |

---

## Expected Results

**Before:**
```
Available: 17/21
Percentage: 81%

Missing:
  ❌ ernest_chan
  ❌ execution_engine
  ❌ lopez_de_prado
  ❌ hull
```

**After implementing fixes 1-3:**
```
Available: 20/21
Percentage: 95%

Missing:
  ❌ execution_engine (false positive - needs debug)
```

**After all fixes:**
```
Available: 21/21
Percentage: 100%

✅ ALL SYSTEMS AVAILABLE!
```

---

## Files to Modify

1. **requirements.txt** - Pin numpy to `<2.0`
2. **app/services/factor_models.py** - Add `get_factor_model()` function
3. **app/core/compliance_engine.py** - Fix `_check_hull()` class name

---

## Quick Test Commands

After fixes, test with:

```bash
# Test 1: Check system availability
python check_systems_availability.py

# Test 2: Import ernest_chan
python -c "from app.services.regime_detection_chan import get_regime_detector; from app.services.factor_models import get_factor_model; print('ernest_chan: OK')"

# Test 3: Import lopez_de_prado
python -c "from app.backtesting.labeling.meta_labeling import get_meta_labeling; print('lopez_de_prado: OK')"

# Test 4: Import hull
python -c "from app.engines.risk_engine.var_calculators.var_calculators import HistoricalVaRCalculator; print('hull: OK')"

# Test 5: Full engine test
python -c "from app.core.compliance_engine import ComplianceEngine; e = ComplianceEngine(); print(e.get_system_status())"
```

---

## Summary

**Main Blocker:** NumPy 2.0.2 compatibility
**Quick Wins:** Add get_factor_model(), fix Hull class name
**Investigation Needed:** execution_engine false positive

**Time Estimate:**
- NumPy fix: 5 minutes
- Add get_factor_model: 10 minutes
- Fix Hull check: 2 minutes
- Debug execution_engine: 15 minutes
- **Total:** ~30 minutes for 100% availability
