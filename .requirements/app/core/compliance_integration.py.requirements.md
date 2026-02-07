# Requirements: app/core/compliance_integration.py

**File Path:** `app/core/compliance_integration.py`
**Component:** Unified Compliance Integration Facade
**Last Updated:** 2026-02-06
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.285301

---

## Purpose

This module provides a **simplified facade for compliance integration**, delegating to specialized coordinators (PreTradeChecker, PostTradeChecker, PortfolioOptimizer). It maintains backward compatibility while following SOLID principles.

**Key Features:**
- Facade pattern for simplified interface
- Lazy initialization of coordinators
- Service registry integration
- Backward compatible API
- Multi-system coordination (Chan, Narang, Lopez de Prado, Harris, O'Hara, Hull, SRE)

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Classes & Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `ComplianceIntegrationFacade` | class | 70-357 | Main compliance integration facade |
| `ComplianceIntegrationEngine` | class | 364-372 | Legacy alias (backward compatibility) |
| `get_compliance_integration_engine()` | function | 382-419 | Get/create global facade instance |
| `quick_pre_trade_check()` | function | 427-452 | Convenience function for fast decisions |
| `get_execution_recommendation()` | function | 455-487 | Get execution recommendation |

### Dependencies

**Internal:**
- `app.core.compliance` (all compliance modules)
- `app.engines.execution_engine.microstructure.order_book_analyzer` (optional)

**External:**
- `logging`, `dataclasses`, `datetime`, `decimal`, `pathlib`, `typing`
- `pandas`

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - Well-architected facade pattern.

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **SOL-001** | Singleton pattern could cause issues | 84-102 | Document thread-safety considerations |
| **TYP-003** | Some `Any` types without justification | 194 | Use proper type for order_book |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long conversion methods | 206-243, 275-293 | Extract to helper methods |
| **ARCH-004** | Some functions exceed 20 lines | 187-243 | Break into smaller methods |

### P3 (Low) Issues

**NONE** - Clear naming and structure.

---

## Acceptance Criteria

### AC-SOL-001: Single Responsibility
```bash
# Facade only delegates, doesn't implement logic
grep -c "def.*check" app/core/compliance_integration.py | grep -v "def comprehensive" | wc -l
# Expected: 0 (all checks delegated)
```

### AC-DP-001: Dependency Injection
```bash
# Services injected, not created
grep -c "PreTradeComplianceChecker()" app/core/compliance_integration.py
# Expected: 1 (lazy init in property)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/compliance_integration.py | wc -l
# Expected: All public functions
```

---

## File-Specific Requirements

### FSR-001: Facade Pattern Implementation
**Priority:** P0
**Description:** Facade must delegate to specialized coordinators

**Requirements:**
- [ ] No business logic in facade
- [ ] All checks delegated to coordinators
- [ ] Lazy initialization of coordinators
- [ ] Clear separation of concerns

**Acceptance Test:**
```python
def test_facade_delegates():
    facade = ComplianceIntegrationFacade()
    
    # Pre-trade check delegated
    result = facade.comprehensive_pre_trade_check(
        symbol="AAPL", side="BUY", quantity=Decimal("100"),
        current_price=Decimal("150")
    )
    
    # Verify delegation happened
    assert facade.pre_trade_checker.was_called
```

### FSR-002: Lazy Initialization
**Priority:** P1
**Description:** Coordinators created only when needed

**Requirements:**
- [ ] Coordinators created on first access
- [ ] Subsequent access returns same instance
- [ ] Thread-safe initialization

**Acceptance Test:**
```python
def test_lazy_initialization():
    facade = ComplianceIntegrationFacade()
    
    # Not initialized yet
    assert facade._pre_trade_checker is None
    
    # First access creates it
    checker = facade.pre_trade_checker
    assert isinstance(checker, PreTradeComplianceChecker)
    
    # Second access returns same instance
    assert facade.pre_trade_checker is checker
```

### FSR-003: Backward Compatibility
**Priority:** P1
**Description:** Legacy API must continue working

**Requirements:**
- [ ] `ComplianceIntegrationEngine` alias exists
- [ ] Legacy convenience functions work
- [ ] Return types match legacy format
- [ ] No breaking changes to existing code

**Acceptance Test:**
```python
def test_backward_compatibility():
    # Legacy class name works
    engine = ComplianceIntegrationEngine()
    assert isinstance(engine, ComplianceIntegrationFacade)
    
    # Legacy function works
    can_execute, reason = quick_pre_trade_check(
        symbol="AAPL", side="BUY", quantity=Decimal("100"), price=Decimal("150")
    )
    assert isinstance(can_execute, bool)
    assert isinstance(reason, str)
```

### FSR-004: Service Registry Integration
**Priority:** P2
**Description:** Must integrate with service registry

**Requirements:**
- [ ] Get registry singleton
- [ ] Check service availability
- [ ] Map legacy availability flags
- [ ] Report system availability

**Acceptance Test:**
```python
def test_service_registry_integration():
    facade = ComplianceIntegrationFacade()
    availability = facade.get_system_availability()
    
    # Should have all systems
    expected_systems = [
        "ernest_chan", "narang", "lopez_de_prado", 
        "harris", "ohara", "hull", "google_sre"
    ]
    
    for system in expected_systems:
        assert system in availability
        assert isinstance(availability[system], bool)
```

### FSR-005: Multi-System Coordination
**Priority:** P2
**Description:** Coordinate multiple compliance systems

**Requirements:**
- [ ] Pre-trade: regime, alpha, liquidity, risk
- [ ] Post-trade: execution quality, costs
- [ ] Portfolio: optimization, regime adjustment
- [ ] Handle missing systems gracefully

**Acceptance Test:**
```python
def test_multi_system_coordination():
    facade = ComplianceIntegrationFacade()
    
    # Pre-trade check coordinates multiple systems
    result = facade.comprehensive_pre_trade_check(
        symbol="AAPL", side="BUY", quantity=Decimal("100"),
        current_price=Decimal("150"), price_history=history_df
    )
    
    # Should have data from multiple systems
    assert result.market_regime is not None  # Chan
    assert result.alpha_signal is not None  # Narang
    assert result.liquidity_score is not None  # O'Hara
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 90%
- **Critical Paths:** 100%

### Required Tests
1. **Facade Tests:**
   - `test_facade_delegates()`
   - `test_lazy_initialization()`
   - `test_singleton_pattern()`

2. **Compatibility Tests:**
   - `test_backward_compatibility()`
   - `test_legacy_api()`

3. **Integration Tests:**
   - `test_service_registry_integration()`
   - `test_multi_system_coordination()`

---

## Performance Requirements

- **Facade Overhead:** < 10ms per call
- **Lazy Initialization:** < 100ms on first access
- **Coordinator Calls:** Delegated performance

---

## Security Requirements

- **No Secret Leakage:** Don't log sensitive data
- **Input Validation:** Validate all parameters
- **Error Handling:** Graceful degradation

---

## Documentation Requirements

1. **Architecture Guide:** Facade pattern benefits
2. **API Documentation:** All public methods
3. **Migration Guide:** Upgrading from legacy
4. **Integration Guide:** Adding new systems

---

## Checklist

- [x] All P0 violations fixed (none)
- [ ] All P1 violations fixed
- [ ] Type hints added to all functions
- [ ] Comprehensive test coverage
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Steps

1. Document thread-safety
2. Add proper type for order_book
3. Add comprehensive tests
4. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
