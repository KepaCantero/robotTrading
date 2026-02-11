# Requirements: app/presentation/dto/requests.py

**File Path:** `app/presentation/dto/requests.py`
**Layer:** Presentation (DTO)
**Last Updated:** 2025-02-05
**Status:** ✅ Compliant - Minimal Changes Needed

---

## Purpose
Defines Pydantic request models for API input validation in the presentation layer.

---

## Current State
- **Lines of Code:** 23
- **Classes:** 2 (CreatePortfolioRequest, ExecuteStrategyRequest)
- **Dependencies:** pydantic, decimal
- **Complexity:** Low

---

## BASE Rules Compliance

### ✅ COMPLIANT Rules
- [FMT-001] Line length ≤ 100: **PASS**
- [FMT-006] F-strings: **N/A** (no string formatting)
- [FMT-007] No mutable defaults: **PASS** (uses `default_factory`)
- [TYP-001] Type coverage: **PASS** (100% coverage)
- [SEC-007] Input validation: **PASS** (Pydantic validation)

### ⚠️ MINOR Gaps (Low Priority)
- [FMT-002] Import organization: **MINOR** - Could add blank line between stdlib and third-party
- [TYP-002] Modern syntax: **N/A** - No collection types that need modernization
- [LOG-001] Structured logging: **N/A** - DTOs don't log

---

## File-Specific Requirements

### REQ-DTO-001: Request Model Validation
**Priority:** P0
**Description:** All request models must validate input using Pydantic
**Current State:** ✅ COMPLIANT
```python
class CreatePortfolioRequest(BaseModel):
    portfolio_id: str = Field(..., description="Portfolio ID")
    initial_capital: Decimal = Field(..., gt=0, description="Initial capital")
```

### REQ-DTO-002: Field Descriptions
**Priority:** P2
**Description:** All fields must have descriptive text
**Current State:** ✅ COMPLIANT - All fields have descriptions

### REQ-DTO-003: Decimal for Financial Values
**Priority:** P0
**Description:** Financial values use Decimal type
**Current State:** ✅ COMPLIANT - Uses Decimal for `initial_capital`

### REQ-DTO-004: Default Factory for Complex Types
**Priority:** P0
**Description:** Use default_factory for dict/list defaults
**Current State:** ✅ COMPLIANT - Uses `default_factory=dict`

---

## Gaps Identified

### No Critical Gaps
This file is well-written and compliant with BASE_RULES.

### Optional Enhancements (P3 - Low Priority)
1. **Add validator for portfolio_id format**
   - Could add regex validator for portfolio ID format
   - Example: `@field_validator('portfolio_id')`
   - **Priority:** P3 (optional enhancement)

2. **Add example values**
   - Could add `Field(examples=...)` for better API documentation
   - **Priority:** P3 (documentation improvement)

---

## Testing Requirements

### TST-DTO-001: Test Validation
**Required Tests:**
- ✅ Test valid request creation
- ✅ Test validation errors (negative capital, missing fields)
- ✅ Test Decimal type handling

### TST-DTO-002: Edge Cases
**Required Tests:**
- ✅ Test with zero capital (should fail gt=0)
- ✅ Test with very large numbers
- ✅ Test with invalid currency codes

---

## Dependencies
- `pydantic` - Data validation
- `decimal` - Precise financial calculations

---

## Notes
- This is a simple DTO file with minimal code
- No business logic, only data validation
- Pydantic handles most validation automatically
- Consider expanding validators for production use
