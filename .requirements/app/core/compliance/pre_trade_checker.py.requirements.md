# pre_trade_checker.py

## Purpose
Coordinates pre-trade compliance checks across multiple services. Aggregates results and provides unified execution decision.

---

## Type Definitions / Data Classes

## Function Signatures (Contracts)

### `PreTradeComplianceChecker.check_signal(...) -> PreTradeCheckResult`
**Pre:** symbol is valid trading symbol
**Post:** Returns aggregated pre-trade check result
**Raises:** None (logs warnings on service errors)
**Side Effects:** May update cache

---

## Acceptance Criteria
- [ ] All dataclasses use `frozen=True` for immutability
- [ ] All functions have complete type hints
- [ ] Logging uses structured format (keyword args, not f-strings)
- [ ] Error handlers include `exc_info=True` for exceptions
- [ ] No `Any` types without justification comments
- [ ] All functions follow Single Responsibility Principle

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-05T19:32:57.767509Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 7 / 7 total |

**Notes:**
- All GAP violations fixed on 2026-02-05
- All files marked as PASSED after audit
- Tests created and verified
- Code review completed successfully

**Status meanings:**
- **NEEDS_AUDIT** - File needs to be audited (default for new files)
- **PASSED** - All GAP violations fixed, audit passed
- **FAILED** - Audit found violations that need fixing
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-001 | BASE_RULES | f-string in logging call (line 223) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 264) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 295) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 329) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 357) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | __init__ missing return type (line 53) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 72) | ✅ FIXED (PP1) |

---

## Dependencies
- **External:** typing, dataclasses, decimal, datetime, logging, pandas
- **Internal: app.core.compliance.service_registry, app.core.compliance.results

---

## Required Tests
- **tests/unit/core/compliance/test_pre_trade_checker.py:**
  - Test dataclass serialization (to_dict methods)
  - Test initialization with valid inputs
  - Test handling of missing/None inputs
  - Test service registry integration
  - Test error logging and exception handling

---

## Notes
- Created during Layer 3 (Core Compliance Module) audit
- All files follow BASE_RULES.md patterns
- Uses modern Python 3.9+ type hints syntax
- Implements Dependency Inversion Principle via Protocols

---

**Last Updated:** 2026-02-05T19:29:34.466090Z
