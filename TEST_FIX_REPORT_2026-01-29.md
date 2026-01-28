# Test Fix Report - 2026-01-29

## Issue
Two test files in `tests/unit/core/` were experiencing import/collection errors:
1. `test_centralized_config_comprehensive.py`
2. `test_shadow_mode.py`

## Root Cause
The issue was caused by a circular import dependency chain that triggered a NumPy/matplotlib compatibility error:

```
app.core.__init__.py
  → app.core.compliance_integration
    → app.backtesting.labeling.meta_labeling
      → app.backtesting.labeling.triple_barrier
        → matplotlib.pyplot
          → ImportError (NumPy 1.x vs 2.0.2)
```

When importing any module from `app.core`, the entire `__init__.py` was executed, which tried to import `compliance_integration`. This module then imported `meta_labeling`, which eventually imported `matplotlib`. Since matplotlib was compiled with NumPy 1.x but the environment had NumPy 2.0.2, this caused an ImportError.

The tests themselves didn't need matplotlib or compliance_engine - they only needed `centralized_config` and `shadow_mode` modules.

## Solution
Modified `/Users/kepa.cantero/Projects/algoTrading/app/core/__init__.py` to make imports of modules with heavy dependencies lazy/optional using try/except blocks.

### Changes Made

**File: `app/core/__init__.py`**

Wrapped imports that could fail in try/except blocks:

1. **Compliance Engine imports** - Made optional:
```python
try:
    from app.core.compliance_engine import (
        ComplianceEngine,
        PreTradeAnalysis,
        PostTradeAnalysis,
        PortfolioOptimization,
        get_compliance_engine,
        quick_check,
        get_execution_plan,
        SystemAvailability,
    )
    _compliance_engine_available = True
except ImportError as e:
    # Import error - likely due to NumPy/matplotlib compatibility issues
    # Set these to None to prevent import errors when only using other core modules
    ComplianceEngine = None
    PreTradeAnalysis = None
    PostTradeAnalysis = None
    PortfolioOptimization = None
    get_compliance_engine = None
    quick_check = None
    get_execution_plan = None
    SystemAvailability = None
    _compliance_engine_available = False
```

2. **Compliance Integration imports** - Made optional (same pattern):
```python
try:
    from app.core.compliance_integration import (
        ComplianceIntegrationEngine as ComplianceIntegrationEngineDeprecated,
        get_compliance_integration_engine as get_compliance_integration_engine_deprecated,
        quick_pre_trade_check,
        get_execution_recommendation,
    )
    _compliance_integration_available = True
except ImportError as e:
    # Import error - likely due to NumPy/matplotlib compatibility issues
    ComplianceIntegrationEngineDeprecated = None
    get_compliance_integration_engine_deprecated = None
    quick_pre_trade_check = None
    get_execution_recommendation = None
    _compliance_integration_available = False
```

## Test Results

### Before Fix
- Import errors prevented tests from running
- NumPy/matplotlib compatibility errors appeared when importing from `app.core`

### After Fix
- ✅ **All 76 tests pass** (43 + 33)
- ✅ **All tests collectible** (no import/collection errors)
- ✅ **Direct imports work**:
  - `from app.core.centralized_config import ...` ✓
  - `from app.core.shadow_mode import ...` ✓

### Test Coverage

**test_centralized_config_comprehensive.py (43 tests):**
- Configuration Loading (5 tests)
- Configuration Validation (8 tests)
- Configuration Access (5 tests)
- Configuration Merging (4 tests)
- Configuration Defaults (4 tests)
- Configuration Caching (2 tests)
- Property-Based Tests (4 tests)
- Edge Cases and Error Handling (5 tests)
- Configuration Updates (2 tests)
- Thread Safety (1 test)
- Integration Tests (2 tests)

**test_shadow_mode.py (33 tests):**
- ShadowModeConfig validation (5 tests)
- ShadowModeExecutor functionality (21 tests)
- ShadowModeAwareBroker wrapper (3 tests)
- ShadowExecutionResult (1 test)
- Environment-based configuration (3 tests)

## Benefits

1. **Isolation**: Tests for specific core modules can now run without requiring all dependencies
2. **Graceful Degradation**: Core modules remain usable even if some optional dependencies fail to import
3. **Backward Compatibility**: Code that successfully imports ComplianceEngine still works
4. **Better DX**: Developers can test individual modules without fixing unrelated dependency issues

## Notes

- The NumPy/matplotlib compatibility warning still appears in output but doesn't prevent execution
- The actual modules (`centralized_config.py`, `shadow_mode.py`) did not require any changes
- This is a temporary fix; a better long-term solution would be to:
  1. Upgrade matplotlib to a version compatible with NumPy 2.x
  2. OR downgrade NumPy to < 2.0
  3. OR restructure imports to avoid heavy dependencies in `__init__.py`

## Files Modified
- `/Users/kepa.cantero/Projects/algoTrading/app/core/__init__.py`

## Verification Command
```bash
python -m pytest tests/unit/core/test_centralized_config_comprehensive.py tests/unit/core/test_shadow_mode.py -v
```

Result: **76 passed, 3 warnings in 7.13s**
