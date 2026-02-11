# Requirements: app/presentation/controllers/assets.py

**File Path:** `app/presentation/controllers/assets.py`
**Layer:** Presentation (Controller)
**Last Updated:** 2025-02-05
**Status:** ✅ Compliant - Minor Issues Found

---

## Purpose
FastAPI endpoints for asset management and identification. Provides REST API for managing assets, identifying liquid assets, and retrieving asset rankings.

---

## Current State
- **Lines of Code:** 486
- **Endpoints:** 15
- **Dependencies:** fastapi, requests
- **Complexity:** Medium

---

## BASE Rules Compliance

### ✅ COMPLIANT Rules
- [FMT-001] Line length ≤ 100: **PASS**
- [FMT-007] No mutable defaults: **PASS**
- [TYP-001] Type coverage: **PASS** (90%+)
- [LOG-004] Error logging: **PASS** (via HTTPException)
- [SEC-007] Input validation: **PASS** (via Pydantic Query)

### ⚠️ MINOR Gaps
- [LOG-001] Structured logging: **MINOR** - Generic exception handling
- [ARCH-004] Small functions: **MINOR** - Some endpoints are long (40-60 lines)

---

## File-Specific Requirements

### REQ-CTRL-101: Asset Overview Endpoint
**Priority:** P0
**Description:** Get overview of all asset universes
**Current State:** ✅ COMPLIANT
```python
@router.get("/", response_model=Dict[str, Any])
async def get_assets_overview(...)
```

### REQ-CTRL-102: Liquid Assets Endpoint
**Priority:** P0
**Description:** Get top liquid assets with limit validation
**Current State:** ✅ COMPLIANT
```python
limit: int = Query(20, ge=1, le=100, description="Number of assets to return")
```

### REQ-CTRL-103: Asset Details Endpoint
**Priority:** P0
**Description:** Get detailed asset information with 404 on not found
**Current State:** ✅ COMPLIANT
```python
if not asset:
    raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")
```

### REQ-CTRL-104: Asset Rankings Endpoint
**Priority:** P1
**Description:** Get asset rankings by class
**Current State:** ✅ COMPLIANT

### REQ-CTRL-105: Asset Filter Endpoint
**Priority:** P1
**Description:** Filter assets based on criteria
**Current State:** ✅ COMPLIANT

### REQ-CTRL-106: Background Tasks
**Priority:** P2
**Description:** Support background task execution
**Current State:** ✅ COMPLIANT
```python
background_tasks.add_task(service.refresh_liquidity_data)
```

---

## Gaps Identified

### CRITICAL Gaps (P0)
**None**

### HIGH Priority Gaps (P1)
**None**

### MEDIUM Priority Gaps (P2)

1. **Generic exception handling**
   - Lines 40, 77, 100: Broad exception catching `(asyncio.TimeoutError, ConnectionError, OSError)`
   - **Fix:** Add specific error messages and logging
   - **Priority:** P2 (error handling)

2. **Line 23: Unused global variable**
   ```python
   _DEFAULT_BACKGROUND_TASKS = BackgroundTasks()
   ```
   **Issue:** Global BackgroundTasks instance may not work as intended
   - **Fix:** Use dependency injection properly
   - **Priority:** P2 (code quality)

### LOW Priority Gaps (P3)

1. **Long endpoints**
   - Several endpoints exceed 40 lines (get_asset_stats is 40+ lines)
   - **Priority:** P3 (code organization)

2. **Missing input validation**
   - No validation on symbol format (could add regex)
   - **Priority:** P3 (security hardening)

3. **No rate limiting**
   - Asset endpoints could be abused
   - **Priority:** P3 (security hardening)

---

## Testing Requirements

### TST-CTRL-101: Asset Endpoints
**Required Tests:**
- ✅ Test get_assets_overview
- ✅ Test get_liquid_assets with limit validation
- ✅ Test get_asset_details (404 on not found)
- ✅ Test get_liquidity_metrics (404 on not found)
- ✅ Test get_asset_rankings

### TST-CTRL-102: Filter Endpoints
**Required Tests:**
- ✅ Test filter_assets
- ✅ Test filter_assets_by_class
- ✅ Test with various filter criteria

### TST-CTRL-103: Background Tasks
**Required Tests:**
- ✅ Test refresh_liquidity_data background task
- ✅ Test identify_liquid_assets with background update

### TST-CTRL-104: Error Handling
**Required Tests:**
- ✅ Test timeout errors
- ✅ Test connection errors
- ✅ Test invalid asset class

---

## Dependencies
- `fastapi` - Web framework
- `app.models.assets` - Asset models
- `app.services.asset_identification` - Asset service

---

## Notes
- Well-structured asset management API
- Good use of Pydantic for validation
- Comprehensive endpoint coverage
- Minor issues with error handling specificity
- Consider adding more specific error messages
- Consider adding rate limiting
