# Requirements: app/core/di_config.py

**File Path:** `app/core/di_config.py`
**Component:** Dependency Injection Configuration
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module **configures the DI container** with all application dependencies. It follows the Dependency Inversion Principle - high-level modules depend on abstractions, not concrete implementations.

**Key Features:**
- Centralized DI container configuration
- Domain factories registration
- Repository registration (TODO)
- Application service registration (TODO)
- Infrastructure component registration

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `configure_container()` | function | 15-51 | Configure DI container with dependencies |
| `initialize_container()` | function | 54-63 | Initialize global DI container |

### Dependencies

**Internal:**
- `app.core.di_container.DIContainer, get_container`
- `app.domain.factories.AbstractEntityFactory, TradingEntityFactory`

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - Clean, minimal configuration file.

### P1 (High) Violations

**NONE** - Proper structure for DI configuration.

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **TYP-003** | Missing return type documentation | 15, 54 | Already typed, could add doc examples |

### P3 (Low) Issues

**NONE** - Clear and simple.

---

## Acceptance Criteria

### AC-DP-001: Dependency Injection
```bash
# Verify no direct instantiation in app initialization
grep -c "= Database()" app/core/di_config.py
# Expected: 0 (all through container)
```

### AC-ARCH-001: Layer Separation
```bash
# Domain factories registered correctly
grep -c "AbstractEntityFactory" app/core/di_config.py
# Expected: 1 (registered as interface)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/di_config.py | wc -l
# Expected: 2 (both functions)
```

---

## File-Specific Requirements

### FSR-001: Container Configuration
**Priority:** P1
**Description:** Configure container with all dependencies

**Requirements:**
- [ ] Register domain factories
- [ ] Register repositories (when available)
- [ ] Register application services (when available)
- [ ] Return configured container

**Acceptance Test:**
```python
def test_container_configuration():
    container = configure_container()
    
    # Should have factory registered
    factory = container.get(AbstractEntityFactory)
    assert isinstance(factory, TradingEntityFactory)
```

### FSR-002: Initialization
**Priority:** P1
**Description:** Initialize global container at startup

**Requirements:**
- [ ] Call configure_container
- [ ] Return initialized container
- [ ] Called once at application startup
- [ ] Accessible globally

**Acceptance Test:**
```python
def test_container_initialization():
    container = initialize_container()
    
    assert isinstance(container, DIContainer)
    
    # Should be same as global container
    global_container = get_container()
    assert container is global_container
```

### FSR-003: TODO Implementation
**Priority:** P2
**Description:** Complete TODO items for repositories and services

**Requirements:**
- [ ] Implement repository registrations
- [ ] Implement service registrations
- [ ] Remove TODO comments
- [ ] Add documentation

**Acceptance Test:**
```python
def test_repository_registration():
    container = configure_container()
    
    # When implemented:
    # repository = container.get(BacktestRepository)
    # assert isinstance(repository, SQLAlchemyBacktestRepository)
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 80%
- **Critical Paths:** 100%

### Required Tests
1. **Configuration Tests:**
   - `test_container_configuration()`
   - `test_factory_registration()`

2. **Initialization Tests:**
   - `test_container_initialization()`
   - `test_singleton_behavior()`

---

## Performance Requirements

- **Configuration Time:** < 100ms
- **Memory Overhead:** Minimal (just references)

---

## Security Requirements

- **No Code Injection:** Only register safe classes
- **Type Safety:** All registrations validated
- **Circular Dependencies:** Detect and prevent

---

## Documentation Requirements

1. **Architecture Guide:** DI pattern usage
2. **Registration Guide:** How to add new dependencies
3. **API Documentation:** All registration functions

---

## Checklist

- [x] All P0 violations fixed (none)
- [x] All P1 violations fixed (none)
- [x] Type hints added to all functions
- [ ] Comprehensive test coverage
- [ ] Complete TODO items
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Steps

1. Add repository registrations
2. Add service registrations
3. Add comprehensive tests
4. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
