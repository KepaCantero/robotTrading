# service_registry.py

## Purpose
Central registration point for all compliance services. Implements lazy initialization and thread-safe singleton pattern.

---

## Type Definitions / Data Classes

## Function Signatures (Contracts)

### `ComplianceServiceRegistry.getInstance() -> ComplianceServiceRegistry`
**Pre:** None
**Post:** Returns singleton instance
**Raises:** None
**Side Effects:** Creates instance on first call

### `ComplianceServiceRegistry.get_service(service_name: str) -> Optional[Any]`
**Pre:** service_name is registered
**Post:** Returns service instance or None
**Raises:** None
**Side Effects:** Lazy-creates service if not cached

### `ComplianceServiceRegistry.is_available(service_name: str) -> bool`
**Pre:** None
**Post:** Returns True if service available
**Raises:** None
**Side Effects:** May attempt service creation

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
| **Last Audit Date** | 2026-02-05T19:32:57.767998Z |
| **Audit Status** | PASSED |
| **BASE_RULES Version** | 2026-02-01 |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 32 / 32 total |

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
| ARCH-004 | BASE_RULES | _register_factories is 57 lines (line 104) | ✅ FIXED (PP2) |
| LOG-001 | BASE_RULES | f-string in logging call (line 178) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 201) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 210) | ✅ FIXED (PP1) |
| LOG-001 | BASE_RULES | f-string in logging call (line 213) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | __init__ missing return type (line 67) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_regime_detector missing return type (line 271) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_vwap_executor missing return type (line 278) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_twap_executor missing return type (line 285) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_is_executor missing return type (line 292) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_pov_executor missing return type (line 299) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_portfolio_optimizer missing return type (line 306) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_alpha_model missing return type (line 317) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_risk_model missing return type (line 327) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_cost_model missing return type (line 337) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_portfolio_constructor missing return type (line 344) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_execution_engine_narang missing return type (line 353) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_meta_labeling missing return type (line 364) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_purged_cv missing return type (line 371) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_harris_integrator missing return type (line 382) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_order_book_analyzer missing return type (line 394) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_dark_pool_router missing return type (line 403) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_order_flow_analyzer missing return type (line 416) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_liquidity_analyzer missing return type (line 423) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_price_discovery_analyzer missing return type (line 430) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_call_auction missing return type (line 437) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_var_calculator missing return type (line 448) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_greeks_calculator missing return type (line 458) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_stress_tester missing return type (line 465) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_golden_signals missing return type (line 478) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_trading_metrics missing return type (line 485) | ✅ FIXED (PP1) |
| TYP-001 | BASE_RULES | _create_toil_tracker missing return type (line 492) | ✅ FIXED (PP1) |

---

## Dependencies
- **External:** typing, dataclasses, decimal, datetime, logging, pandas
- **Internal: None (registry pattern, imports services lazily)

---

## Required Tests
- **tests/unit/core/compliance/test_service_registry.py:**
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

**Last Updated:** 2026-02-05T19:29:34.466713Z
