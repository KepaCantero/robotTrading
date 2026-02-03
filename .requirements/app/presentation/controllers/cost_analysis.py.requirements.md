# Requirements: app/presentation/controllers/cost_analysis.py

**File Path:** `app/presentation/controllers/cost_analysis.py`
**Layer:** Presentation (Controller)
**Last Updated:** 2025-02-05
**Status:** ⚠️ Needs Improvement - Several Issues Found

---

## Purpose
Cost Analysis API endpoints. Provides FastAPI endpoints for cost analysis functionality including cost breakdown, profitability validation, and Cost Impact Ratio (CIR) analysis.

---

## Current State
- **Lines of Code:** 306
- **Endpoints:** 8
- **Dependencies:** fastapi, decimal, datetime
- **Complexity:** Medium

---

## BASE Rules Compliance

### ✅ COMPLIANT Rules
- [FMT-001] Line length ≤ 100: **PASS**
- [FMT-007] No mutable defaults: **PASS**
- [TYP-001] Type coverage: **PASS** (85%+)
- [SEC-007] Input validation: **PARTIAL** (manual conversion)

### ⚠️ Gaps
- [SEC-007] Input validation: **GAP** - Manual dict conversion without Pydantic models
- [ARCH-004] Small functions: **GAP** - analyze_strategy_costs is 75 lines
- [LOG-004] Error logging: **MINOR** - Generic exception handling

---

## File-Specific Requirements

### REQ-CTRL-301: Trade Cost Analysis Endpoint
**Priority:** P0
**Description:** Analyze costs for a single trade
**Current State:** ⚠️ NEEDS IMPROVEMENT
```python
@router.post("/analyze-trade")
async def analyze_trade_costs(trade_data: Dict[str, Any], ...):
    # Manual dict to Trade object conversion
    trade = Trade(
        trade_id=trade_data["id"],
        symbol=trade_data["symbol"],
        # ... 15+ fields
    )
```
**Issue:** Should use Pydantic model for request validation

### REQ-CTRL-302: Strategy Cost Analysis Endpoint
**Priority:** P0
**Description:** Analyze costs for entire trading strategy
**Current State:** ⚠️ NEEDS IMPROVEMENT
**Issue:** 75-line function, manual conversion

### REQ-CTRL-303: Profitability Validation Endpoint
**Priority:** P0
**Description:** Validate profitability of trading strategy
**Current State:** ✅ COMPLIANT

### REQ-CTRL-304: Cost Parameters Endpoints
**Priority:** P1
**Description:** Get and update cost parameters
**Current State:** ✅ COMPLIANT
```python
if rate > 0.1:  # Max 10% commission
    raise ValueError(...)
```

### REQ-CTRL-305: Placeholder Endpoints
**Priority:** P2
**Description:** Implement missing endpoints
**Current State:** ⚠️ NOT IMPLEMENTED
```python
@router.get("/cost-breakdown/{trade_id}")
async def get_cost_breakdown(...):
    return {"message": "Cost breakdown retrieval not yet implemented"}
```

---

## Gaps Identified

### CRITICAL Gaps (P0)

1. **Missing Pydantic request models**
   - Lines 28, 80, 156: Using `Dict[str, Any]` instead of Pydantic models
   - **Fix:** Create proper Pydantic models for requests
   - **Priority:** P0 (input validation)

2. **Manual data conversion without validation**
   - Lines 35-48, 93-109: Manual dict to Trade conversion
   - **Fix:** Use Pydantic models for automatic validation
   - **Priority:** P0 (security)

### HIGH Priority Gaps (P1)

1. **Unimplemented endpoints**
   - Lines 279-290, 293-305: Placeholder responses
   - **Fix:** Implement actual functionality
   - **Priority:** P1 (feature completeness)

2. **Very long function**
   - Lines 79-153: analyze_strategy_costs is 75 lines
   - **Fix:** Break into smaller functions
   - **Priority:** P1 (maintainability)

### MEDIUM Priority Gaps (P2)

1. **Generic exception handling**
   - Lines 75, 152, 199, 275: Broad exception catching
   - **Fix:** Add specific error handling
   - **Priority:** P2 (error handling)

### LOW Priority Gaps (P3)

1. **No rate limiting**
   - Cost analysis endpoints could be abused
   - **Priority:** P3 (security hardening)

2. **Missing input sanitization**
   - Direct dict access without validation
   - **Priority:** P3 (security)

---

## Testing Requirements

### TST-CTRL-301: Trade Analysis
**Required Tests:**
- ✅ Test analyze_trade_costs with valid data
- ✅ Test analyze_trade_costs with missing fields
- ✅ Test analyze_trade_costs with invalid data types

### TST-CTRL-302: Strategy Analysis
**Required Tests:**
- ✅ Test analyze_strategy_costs with multiple trades
- ✅ Test analyze_strategy_costs cost breakdown
- ✅ Test profitability validation

### TST-CTRL-303: Cost Parameters
**Required Tests:**
- ✅ Test get_cost_parameters
- ✅ Test update_cost_parameters with valid values
- ✅ Test update_cost_parameters with invalid values (> 0.1 commission)

### TST-CTRL-304: Error Handling
**Required Tests:**
- ✅ Test ValueError on commission > 0.1
- ✅ Test ValueError on slippage > 0.05
- ✅ Test missing required fields

---

## Dependencies
- `fastapi` - Web framework
- `app.backtesting.models` - Trade models
- `app.services.cost_analysis_service` - Cost analysis service

---

## Notes
- Functional but needs improvement
- **CRITICAL:** Should use Pydantic models for request validation
- **HIGH:** Implement placeholder endpoints
- **HIGH:** Refactor long function
- Consider adding comprehensive input validation
- Consider implementing missing endpoints
