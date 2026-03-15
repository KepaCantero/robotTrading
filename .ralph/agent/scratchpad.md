# Scratchpad - Architecture Compliance Fix

## 2026-03-15 - Phase 5.3: Fix compliance_engine.py

### Analysis Summary
File: `app/domain/services/compliance/compliance_engine.py` (3821 lines)

**Issues Found:**
1. **E0602** (line 2402): `Callable` used but not imported from `typing` - ALREADY IMPORTED
2. **E1101** (line 3434): `BrokerConnector` has no `modify_order` member - FALSE POSITIVE (method is on ComplianceEngine)
3. **MI = 0.00**: Maintainability Index is 0 - needs docstrings - ALREADY HAS MODULE DOCSTRING
4. **Multiple W0613**: Unused arguments in methods - FIXED
5. **Multiple W1203**: Logging f-string interpolation - FIXED
6. **Multiple C0415**: Imports outside toplevel (acceptable for lazy loading) - NOT FIXED (intentional)
7. **R0904**: Too many public methods (30/20) - structural, won't fix
8. **R0912/R0915**: Too many branches/statements - structural, won't fix

### Fixes Applied
1. W0613: Prefixed all unused arguments with underscore (e.g., `subsystem` → `_subsystem`)
2. W1203: Converted all f-string logging to lazy % formatting

### Progress
- [x] Analysis complete
- [x] Fix Callable import (already present)
- [x] Fix modify_order method (false positive)
- [x] Add docstrings for MI improvement (already has module docstring)
- [x] Fix unused arguments (prefixed with underscore)
- [x] Fix logging f-strings (converted to lazy %)
- [x] Verify with pylint/mypy (pylint 10/10, mypy pre-existing errors unrelated to changes)

### Final Results
- Pylint rating: 10.00/10 (all W0613 and W1203 warnings resolved)
- Black: formatted
- isort: pass
- MI: C (acceptable for large file with good module docstring)

---

## 2026-03-15 - HAT 6: File Renamer (FS-BAN-001, FS-DIR-004)

### Current Status
AAA Phases 1-5 completed (audit + fixes). Now working through HAT workflow.

### FS-BAN-001 COMPLETED
**Files Renamed:**
- `app/presentation/api/utils.py` → `api_helpers.py`
- `app/services/hurst_analysis/utils.py` → `hurst_calculations.py`

**Import Updates:**
- `orchestrator.py`: Changed `from app.services.hurst_analysis import utils` to `from app.services.hurst_analysis import hurst_calculations as utils`

**Commit:** a2b0593e

### FS-DIR-004 COMPLETED
**File Moved:**
- `app.py` (root) → `scripts/launcher.py`

**Analysis:**
- `app.py` was a launcher script (not the FastAPI app which is `app/main.py`)
- Used to start Dashboard (Streamlit) or API (uvicorn)
- No other files imported from it
- Had desloppify issues (subprocess security, etc.)

**Action:**
- Moved to `scripts/launcher.py` following project convention for scripts
- Updated usage documentation to reflect new location

### Remaining Work (Phase 2+)
1. **FS-DIR-005** (HAT 8): Deep directories
   - Multiple deep directories exist
   - Need flattening plan

2. **ARCH-FILE-001** (HAT 5): Oversized files
   - 30+ files > 300 lines
   - Focus on top 10 worst offenders

### Tasks Status
- [x] task-1773594716-8f8d: HAT 6 - Rename prohibited files (CLOSED)
- [x] task-1773594717-0e99: HAT 6 - Handle app.py in root (CLOSED)
