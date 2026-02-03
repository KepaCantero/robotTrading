# Requirements: app/core/secure_serialization.py

**File Path:** `app/core/secure_serialization.py`
**Component:** Secure Serialization with HMAC Signing
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module provides **binary-safe serialization with HMAC signature verification**, replacing insecure `pickle` usage. It automatically detects if data is JSON-serializable and falls back to msgpack for complex/binary data (numpy arrays, pandas DataFrames).

**Key Features:**
- Automatic format detection (JSON vs msgpack)
- HMAC-SHA256 signature verification
- Base64 encoding for safe transport
- Support for numpy/pandas objects

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `_get_secret_key()` | function | 37-57 | Get SECRET_KEY from environment |
| `_is_json_serializable()` | function | 60-102 | Check if object is JSON-serializable |
| `_convert_for_msgpack()` | function | 105-166 | Convert complex objects to msgpack format |
| `_restore_from_msgpack()` | function | 169-219 | Restore objects from msgpack format |
| `sign_and_dump()` | function | 222-278 | Sign and serialize data |
| `verify_and_load()` | function | 281-351 | Verify signature and deserialize |

### Dependencies

**External:**
- `base64`, `hashlib`, `hmac`, `json`, `logging`, `os`, `decimal`
- `msgpack`, `numpy`, `pandas` (required, no fallbacks)

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - This module follows security best practices.

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **SEC-001** | SECRET_KEY validation could be stronger | 46-56 | Add entropy check, not just length |
| **LOG-005** | Error messages may leak data structure | 274, 342 | Sanitize error messages |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long recursive functions | 105-166, 169-219 | Consider iterative approach for large objects |
| **QL-007** | Multiple parameters (could use object) | 222-231 | Consider SerializationConfig object |

### P3 (Low) Issues

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-001** | Some variable names could be clearer | Various | Minor naming improvements |

---

## Acceptance Criteria

### AC-SEC-001: No Hardcoded Secrets
```bash
# No API keys in code
grep -iE "api_key|secret|password|token" app/core/secure_serialization.py | grep -vE "os.environ|getenv|SECRET_KEY" | wc -l
# Expected: 0 hardcoded secrets
```

### AC-SEC-002: HMAC Verification
```bash
# Verify HMAC is always checked
grep -c "hmac.new" app/core/secure_serialization.py
# Expected: 2 (sign_and_dump, verify_and_load)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/secure_serialization.py | wc -l
# Expected: 6 (all functions)
```

---

## File-Specific Requirements

### FSR-001: HMAC Signature Verification
**Priority:** P0
**Description:** All serialized data must be signed with HMAC-SHA256

**Requirements:**
- [ ] Use constant-time comparison (`hmac.compare_digest`)
- [ ] 32-byte signature (SHA256 output)
- [ ] Fail fast if signature verification fails
- [ ] Log signature failures for security monitoring

**Acceptance Test:**
```python
def test_hmac_signature_verification():
    data = {"symbol": "AAPL", "quantity": 100}
    signed = sign_and_dump(data, "secret_key")
    
    # Tamper with data
    tampered = signed[:-10] + "XXXXXXXXXX"
    
    with pytest.raises(ValueError, match="Invalid signature"):
        verify_and_load(tampered, "secret_key")
```

### FSR-002: SECRET_KEY Validation
**Priority:** P1
**Description:** SECRET_KEY must be sufficiently strong

**Requirements:**
- [ ] Minimum 32 characters
- [ ] Error message must include generation command
- [ ] No fallback to insecure defaults
- [ ] Log warning if using weak key

**Acceptance Test:**
```python
def test_secret_key_validation():
    with pytest.raises(ValueError, match="SECRET_KEY environment variable"):
        _get_secret_key()  # No env var set
    
    os.environ["SECRET_KEY"] = "short"
    with pytest.raises(ValueError, match="too short"):
        _get_secret_key()
```

### FSR-003: Numpy/Pandas Support
**Priority:** P2
**Description:** Must correctly serialize and restore numpy/pandas objects

**Requirements:**
- [ ] Preserve dtypes for DataFrames
- [ ] Preserve index for Series/DataFrames
- [ ] Handle Decimal precision correctly
- [ ] Support multi-dimensional arrays

**Acceptance Test:**
```python
def test_numpy_pandas_serialization():
    import numpy as np
    import pandas as pd
    
    data = {
        "array": np.array([1, 2, 3]),
        "df": pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
        "series": pd.Series([1, 2, 3], name="test"),
    }
    
    signed = sign_and_dump(data, "secret")
    restored = verify_and_load(signed, "secret")
    
    assert np.array_equal(restored["array"], data["array"])
    assert restored["df"].equals(data["df"])
    assert restored["series"].equals(data["series"])
```

### FSR-004: Format Detection
**Priority:** P2
**Description:** Automatically choose JSON vs msgpack based on data

**Requirements:**
- [ ] Use JSON for simple types (dict, list, str, int, float, bool)
- [ ] Use msgpack for complex types (numpy, pandas, bytes)
- [ ] Store format type in message header
- [ ] Handle mixed-type data structures

**Acceptance Test:**
```python
def test_automatic_format_detection():
    simple_data = {"key": "value", "number": 42}
    complex_data = {"array": np.array([1, 2, 3])}
    
    simple_signed = sign_and_dump(simple_data, "secret")
    complex_signed = sign_and_dump(complex_data, "secret")
    
    # Decode to check format type
    simple_decoded = base64.b64decode(simple_signed)
    complex_decoded = base64.b64decode(complex_signed)
    
    assert simple_decoded[:4] == b"json"
    assert complex_decoded[:4] == b"msgp"
```

### FSR-005: Base64 Encoding
**Priority:** P2
**Description:** Output must be ASCII-safe for transport

**Requirements:**
- [ ] Use base64 encoding for final output
- [ ] Decode to ASCII string (not bytes)
- [ ] Handle encoding errors gracefully

**Acceptance Test:**
```python
def test_base64_encoding():
    data = {"test": "value"}
    signed = sign_and_dump(data, "secret")
    
    # Must be ASCII string
    assert isinstance(signed, str)
    signed.encode("ascii")  # Should not raise
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 95%
- **Critical Paths:** 100%

### Required Tests
1. **Security Tests:**
   - `test_hmac_signature_verification()`
   - `test_tampered_data_rejection()`
   - `test_secret_key_validation()`

2. **Serialization Tests:**
   - `test_json_format_simple_data()`
   - `test_msgpack_format_complex_data()`
   - `test_numpy_array_serialization()`
   - `test_pandas_dataframe_serialization()`

3. **Edge Cases:**
   - `test_empty_data()`
   - `test_nested_structures()`
   - `test_large_objects()`

---

## Performance Requirements

- **JSON Serialization:** < 10ms for 1KB data
- **Msgpack Serialization:** < 20ms for 1MB numpy array
- **Signature Generation:** < 5ms
- **Signature Verification:** < 5ms

---

## Security Requirements

- **No Pickle:** Never use pickle for security reasons
- **HMAC Required:** All data must be signed
- **Secret Management:** SECRET_KEY from environment only (Rule 28)
- **Tamper Detection:** Must detect any data modification
- **Constant-Time Comparison:** Use `hmac.compare_digest` to prevent timing attacks

---

## Documentation Requirements

1. **Security Guide:** How to generate secure SECRET_KEY
2. **API Documentation:** All public functions documented
3. **Performance Guide:** When to use JSON vs msgpack
4. **Migration Guide:** Replacing pickle usage

---

## Checklist

- [x] All P0 violations fixed (none)
- [ ] All P1 violations fixed
- [ ] Type hints added to all functions
- [ ] Comprehensive test coverage
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Steps

1. Add entropy check for SECRET_KEY
2. Sanitize error messages
3. Add comprehensive tests
4. Complete security review
5. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
