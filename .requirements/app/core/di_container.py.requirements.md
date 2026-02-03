# Requirements: app/core/di_container.py

**File Path:** `app/core/di_container.py`
**Component:** Dependency Injection Container
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module provides a **simple dependency injection container** for managing application dependencies and their lifecycles. It supports singleton/transient lifecycles, factory functions, and automatic dependency resolution.

**Key Features:**
- Singleton lifecycle (default)
- Transient lifecycle (new instance each time)
- Factory functions for complex construction
- Automatic dependency resolution via inspect
- FastAPI Depends() integration helpers

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Classes & Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `DIContainer` | class | 16-157 | Main DI container |
| `get_container()` | function | 164-169 | Get global DI container |
| `reset_container()` | function | 172-175 | Reset container (testing) |
| `get_portfolio_service()` | function | 182-209 | FastAPI dependency for PortfolioService |
| `get_signal_scorer_service()` | function | 222-249 | FastAPI dependency for SignalScorerService |
| `get_strategy_registry()` | function | 268-292 | FastAPI dependency for StrategyRegistry |
| `get_strategy_config_loader()` | function | 295-319 | FastAPI dependency for StrategyConfigLoader |
| `get_strategy_logger()` | function | 322-346 | FastAPI dependency for StrategyLogger |
| `get_execution_engine()` | function | 349-378 | FastAPI dependency for ExecutionEngine |
| `reset_strategy_services()` | function | 381-390 | Reset strategy services (testing) |

### Dependencies

**External:**
- `inspect`, `typing`

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - Clean implementation of DI pattern.

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **DP-004** | Global singletons may cause issues in tests | 161, 179, etc. | Document thread-safety and test isolation |
| **CC-006** | Generic error handling in `_create_instance` | 134-140 | Catch specific exceptions |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **TYP-003** | Some `Any` types without justification | 80, 144 | Use TypeVar or Protocol |
| **ARCH-007** | Could use more composition | 204-208 | Hard-coded imports in factory functions |

### P3 (Low) Issues

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-001** | Variable naming could be clearer | 120 | `sig` → `signature` |

---

## Acceptance Criteria

### AC-DP-001: Dependency Injection
```bash
# Verify no direct instantiation in factory functions
grep -c "= PortfolioService(" app/core/di_container.py
# Expected: 1 (only in factory function, not scattered)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/di_container.py | wc -l
# Expected: All public functions
```

### AC-SOL-001: Single Responsibility
```bash
# Each class/method has one job
# DIContainer: manages dependencies only
# Factory functions: create specific services only
```

---

## File-Specific Requirements

### FSR-001: Singleton Lifecycle
**Priority:** P1
**Description:** Registered singletons must return same instance

**Requirements:**
- [ ] Singleton instances cached in container
- [ ] Multiple calls return same object reference
- [ ] Thread-safe for concurrent access

**Acceptance Test:**
```python
def test_singleton_lifecycle():
    container = DIContainer()
    instance = Database()
    
    container.register_singleton(Database, instance)
    
    result1 = container.get(Database)
    result2 = container.get(Database)
    
    assert result1 is result2  # Same object reference
```

### FSR-002: Transient Lifecycle
**Priority:** P1
**Description:** Transient registrations must create new instances

**Requirements:**
- [ ] Each call creates new instance
- [ ] Constructor called each time
- [ ] Dependencies auto-resolved

**Acceptance Test:**
```python
def test_transient_lifecycle():
    container = DIContainer()
    container.register_transient(Repository, SQLRepository)
    
    result1 = container.get(Repository)
    result2 = container.get(Repository)
    
    assert result1 is not result2  # Different objects
    assert isinstance(result1, SQLRepository)
    assert isinstance(result2, SQLRepository)
```

### FSR-003: Automatic Dependency Resolution
**Priority:** P2
**Description:** Container must resolve constructor dependencies

**Requirements:**
- [ ] Inspect constructor signatures
- [ ] Resolve dependencies from container
- [ ] Use default values if available
- [ ] Raise clear error if dependency missing

**Acceptance Test:**
```python
def test_automatic_dependency_resolution():
    container = DIContainer()
    container.register_singleton(Database, Database())
    container.register_transient(Repository, SQLRepository)
    
    # SQLRepository.__init__(db: Database)
    repo = container.get(Repository)
    
    assert isinstance(repo, SQLRepository)
    assert isinstance(repo.db, Database)
```

### FSR-004: Factory Functions
**Priority:** P2
**Description:** Support factory functions for complex construction

**Requirements:**
- [ ] Factory receives container reference
- [ ] Factory can access other dependencies
- [ ] Factory can perform custom logic

**Acceptance Test:**
```python
def test_factory_function():
    container = DIContainer()
    
    def create_service(c):
        db = c.get(Database)
        return PortfolioService(db, custom_setting=True)
    
    container.register_factory("portfolio", create_service)
    
    service = container.get("portfolio")
    assert service.custom_setting == True
```

### FSR-005: FastAPI Integration
**Priority:** P2
**Description:** Factory functions for FastAPI Depends()

**Requirements:**
- [ ] Lazy initialization (create on first use)
- [ ] Global singleton pattern
- [ ] Reset functions for testing
- [ ] Type hints for FastAPI

**Acceptance Test:**
```python
def test_fastapi_integration():
    reset_portfolio_service()
    
    service1 = get_portfolio_service()
    service2 = get_portfolio_service()
    
    assert service1 is service2  # Singleton
    
    reset_portfolio_service()
    service3 = get_portfolio_service()
    
    # New instance after reset
    assert service3 is not service1
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 90%
- **Critical Paths:** 100%

### Required Tests
1. **Lifecycle Tests:**
   - `test_singleton_lifecycle()`
   - `test_transient_lifecycle()`
   - `test_factory_function()`

2. **Resolution Tests:**
   - `test_automatic_dependency_resolution()`
   - `test_default_values_used()`
   - `test_missing_dependency_error()`

3. **Integration Tests:**
   - `test_fastapi_depends_integration()`
   - `test_reset_functions()`
   - `test_multiple_registrations()`

---

## Performance Requirements

- **Registration:** < 1ms per registration
- **Resolution:** < 5ms per dependency (including recursive resolution)
- **Memory:** Minimal overhead for singleton storage

---

## Security Requirements

- **No Code Injection:** Factory functions must not execute arbitrary code
- **Type Safety:** All registrations must be type-checked
- **Isolation:** Container instances must be isolated

---

## Documentation Requirements

1. **Architecture Guide:** DI pattern benefits and usage
2. **API Documentation:** All public methods documented
3. **Testing Guide:** How to use reset functions in tests
4. **Migration Guide:** Converting from direct instantiation

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

1. Improve error handling in `_create_instance`
2. Add thread-safety documentation
3. Add comprehensive tests
4. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
