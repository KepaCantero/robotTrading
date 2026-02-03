# Requirements: app/core/numba_enforcer.py

**File Path:** `app/core/numba_enforcer.py`
**Component:** Numba Enforcement Module
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module **enforces 100% Numba acceleration** across all performance-critical code. Numba is REQUIRED (no fallbacks, no exceptions) for performance-critical numerical computations.

**Key Features:**
- Mandatory Numba availability check at import
- Version validation (>= 0.59.0)
- Function verification (decorators present)
- Performance-critical code detection
- Testing environment support

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `enforce_numba_available()` | function | 31-89 | Verify Numba is available (MANDATORY) |
| `get_numba_version()` | function | 92-104 | Get installed Numba version |
| `verify_numba_function()` | function | 107-146 | Verify function is Numba-compiled |
| `detect_performance_critical_code()` | function | 154-212 | Detect performance-critical patterns |
| `require_numba()` | function | 253-282 | Decorator to enforce Numba usage |

### Dependencies

**External:**
- `logging`, `os`, `typing`

**Conditional:**
- `numba` (required, no fallbacks)

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - Enforces Numba requirement correctly.

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-006** | Generic exception handling | 69-85 | Catch specific exceptions |
| **PERF-005** | Pattern detection could be more robust | 154-212 | More sophisticated code analysis |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long function | 154-212 | Extract pattern matchers |
| **TYP-003** | Return type `list` without element type | 154 | Should be `List[Dict[str, Any]]` |

### P3 (Low) Issues

**NONE** - Clear naming and structure.

---

## Acceptance Criteria

### AC-PERF-001: Numba Required
```bash
# Verify Numba enforcement happens
grep -c "enforce_numba_available" app/core/numba_enforcer.py
# Expected: 3 (definition, auto-call, decorator)
```

### AC-PERF-002: Version Check
```bash
# Verify version validation
grep -c "0.59.0" app/core/numba_enforcer.py
# Expected: >= 1
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/numba_enforcer.py | wc -l
# Expected: All functions
```

---

## File-Specific Requirements

### FSR-001: Mandatory Numba Check
**Priority:** P0
**Description:** Numba must be available at application startup

**Requirements:**
- [ ] Check runs automatically on module import
- [ ] Raises RuntimeError with clear message if Numba missing
- [ ] Validates minimum version (0.59.0)
- [ ] Includes installation instructions in error message

**Acceptance Test:**
```python
def test_numba_enforcement():
    # Should raise if Numba not available
    with unittest.mock.patch.dict(sys.modules, {'numba': None}):
        with pytest.raises(RuntimeError, match="Numba is REQUIRED"):
            import app.core.numba_enforcer
```

### FSR-002: Version Validation
**Priority:** P0
**Description:** Numba version must be >= 0.59.0

**Requirements:**
- [ ] Parse version string correctly
- [ ] Compare major and minor versions
- [ ] Provide upgrade command if version too old
- [ ] Log successful check

**Acceptance Test:**
```python
def test_version_validation():
    # Test with old version
    with unittest.mock.patch('numba.__version__', '0.55.0'):
        with pytest.raises(RuntimeError, match="0.59.0 or higher is REQUIRED"):
            enforce_numba_available()
    
    # Test with good version
    with unittest.mock.patch('numba.__version__', '0.59.0'):
        enforce_numba_available()  # Should pass
```

### FSR-003: Function Verification
**Priority:** P1
**Description:** Verify functions use Numba decorators

**Requirements:**
- [ ] Check for Numba-specific attributes
- [ ] Execute function to verify compilation
- [ ] Raise error if not compiled
- [ ] Support testing mode

**Acceptance Test:**
```python
def test_function_verification():
    # Numba-compiled function
    @numba.jit(nopython=True)
    def good_func(x):
        return x * 2
    
    verify_numba_function(good_func, 5)  # Should pass
    
    # Non-compiled function
    def bad_func(x):
        return x * 2
    
    with pytest.raises(RuntimeError, match="NOT Numba-compiled"):
        verify_numba_function(bad_func, 5)
```

### FSR-004: Performance-Critical Code Detection
**Priority:** P2
**Description:** Detect code patterns that need Numba

**Requirements:**
- [ ] Find NumPy operations in functions
- [ ] Find pandas operations in loops
- [ ] Find calculation functions without decorators
- [ ] Report severity level

**Acceptance Test:**
```python
def test_performance_critical_detection():
    code = """
def calculate_returns(prices):
    import numpy as np
    return np.diff(prices) / prices[:-1]
"""
    
    with open("/tmp/test.py", "w") as f:
        f.write(code)
    
    patterns = detect_performance_critical_code("/tmp/test.py")
    assert any(p["type"] == "calculation_without_numba" for p in patterns)
```

### FSR-005: Testing Environment Support
**Priority:** P2
**Description:** Support testing without Numba enforcement

**Requirements:**
- [ ] Check `TESTING` environment variable
- [ ] Skip enforcement if testing
- [ ] Log skip message
- [ ] Provide manual enforcement function

**Acceptance Test:**
```python
def test_testing_environment():
    os.environ["TESTING"] = "1"
    
    # Should not raise even without Numba
    import importlib
    import app.core.numba_enforcer
    importlib.reload(app.core.numba_enforcer)
    
    # Manually enforce still works
    with pytest.raises(RuntimeError):
        app.core.numba_enforcer.enforce_numba_available()
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 85%
- **Critical Paths:** 100%

### Required Tests
1. **Enforcement Tests:**
   - `test_numba_enforcement()`
   - `test_version_validation()`
   - `test_testing_environment_skip()`

2. **Verification Tests:**
   - `test_function_verification()`
   - `test_compilation_verification()`

3. **Detection Tests:**
   - `test_numpy_pattern_detection()`
   - `test_pandas_loop_detection()`
   - `test_calculation_detection()`

---

## Performance Requirements

- **Enforcement Check:** < 100ms at startup
- **Version Check:** < 50ms
- **Function Verification:** < 1s per function
- **Code Detection:** < 5s per file

---

## Security Requirements

- **No Code Execution:** Detection must not execute code
- **Safe Import:** Handle import errors gracefully
- **Error Messages:** Don't leak sensitive information

---

## Documentation Requirements

1. **Installation Guide:** How to install Numba
2. **Migration Guide:** Converting code to use Numba
3. **Best Practices:** When and how to use Numba
4. **Troubleshooting:** Common Numba issues

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

1. Improve exception handling
2. Add more robust pattern detection
3. Add comprehensive tests
4. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
