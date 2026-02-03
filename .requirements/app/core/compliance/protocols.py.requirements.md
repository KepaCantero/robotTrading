# protocols.py

## Purpose
Defines protocol interfaces for all compliance services. Enables Dependency Inversion Principle - high-level modules depend on abstractions.

---

## Type Definitions / Data Classes

### ComplianceService (Protocol)
```python
class ComplianceService(Protocol):
    def is_available(self) -> bool: ...
    def get_service_name(self) -> str: ...
    def initialize(self) -> None: ...
```

### PreTradeCheckable (Protocol)
```python
class PreTradeCheckable(ComplianceService, Protocol):
    def check_pre_trade(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        price_history: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]: ...
```

### PostTradeCheckable (Protocol)
```python
class PostTradeCheckable(ComplianceService, Protocol):
    def check_post_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        **kwargs: Any,
    ) -> Dict[str, Any]: ...
```

---

## Function Signatures (Contracts)

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
| **Last Audit Date** | 2026-02-05T19:32:57.766731Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 11 / 11 total |

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
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 65) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 111) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 156) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 189) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 207) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 227) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 249) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 272) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 295) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 316) | ✅ FIXED (PP1) |
| TYP-003 | BASE_RULES | **kwargs: Any without justification (line 333) | ✅ FIXED (PP1) |

---

## Dependencies
- **External:** typing, dataclasses, decimal, datetime, logging, pandas
- **Internal: None (pure protocols)

---

## Required Tests
- **tests/unit/core/compliance/test_protocols.py:**
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

**Last Updated:** 2026-02-05T19:29:34.465558Z
