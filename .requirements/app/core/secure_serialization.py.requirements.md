# secure_serialization.py

## Purpose
Provides secure serialization with HMAC signature verification, replacing insecure pickle with msgpack/JSON for binary-safe data transport.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### Conversion Type Mapping
```python
# numpy.ndarray → dict with __type__, dtype, shape, data
numpy.ndarray: {
    '__type__': 'numpy.ndarray',
    'dtype': str,        # Data type (e.g., 'float64')
    'shape': tuple,      # Array shape
    'data': list,        # Nested list representation
}

# pandas.DataFrame → dict with __type__, columns, index, dtypes, data
pandas.DataFrame: {
    '__type__': 'pandas.DataFrame',
    'columns': list,     # Column names
    'index': list,       # Index values
    'dtypes': list,      # Column data types
    'data': list,        # Nested list of values
}

# pandas.Series → dict with __type__, name, index, data
pandas.Series: {
    '__type__': 'pandas.Series',
    'name': str,         # Series name
    'index': list,       # Index values
    'data': list,        # Values
}

# decimal.Decimal → dict with __type__, value (string)
decimal.Decimal: {
    '__type__': 'decimal.Decimal',
    'value': str,        # String representation to preserve precision
}

# Primitives pass through: dict, list, str, int, float, bool, bytes
```

**Validation Rules:**
- All types must be serializable to JSON or msgpack
- SECRET_KEY must be minimum 32 characters
- HMAC signature must be 32 bytes (SHA256)
- Format type must be exactly 4 bytes (b'json' or b'msgp')

---

## Function Signatures (Contracts)

### `_get_secret_key() -> bytes`
**Pre:** SECRET_KEY environment variable set (min 32 chars)
**Post:** Secret key returned as bytes
**Raises:** ValueError if not set or too short
**Retry:** ❌ No
**Side Effects:** Logs warning if weak key, raises error (no hardcoded fallback)

### `_is_json_serializable(obj: Any) -> bool`
**Pre:** obj is any Python object
**Post:** Returns True if natively JSON-serializable without conversion
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `_convert_for_msgpack(obj: Any) -> Any`
**Pre:** obj contains numpy, pandas, or standard types
**Post:** Returns msgpack-compatible representation with type metadata
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Recursive conversion of nested structures

### `_restore_from_msgpack(obj: Any) -> Any`
**Pre:** obj is msgpack-unpacked data with type metadata
**Post:** Returns original Python objects (numpy arrays, pandas, etc.)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Recursive restoration of nested structures

### `sign_and_dump(data: Any, secret_key: Union[str, bytes] = None) -> str`
**Pre:** data is serializable, secret_key available (min 32 chars)
**Post:** Returns base64-encoded string with format + signature + data
**Raises:** ValueError if serialization fails or SECRET_KEY invalid
**Retry:** ❌ No
**Side Effects:** None

**Format Structure:** [format_type (4 bytes)] [HMAC-SHA256 (32 bytes)] [data (variable)]

### `verify_and_load(signed_data: str, secret_key: Union[str, bytes] = None) -> Any`
**Pre:** signed_data from sign_and_dump, secret_key matches signing key
**Post:** Returns deserialized data
**Raises:** ValueError if signature invalid, malformed, or format unknown
**Retry:** ❌ No
**Side Effects:** Logs errors with details

---

## Acceptance Criteria
- [ ] **AC-SEC-001**: All data automatically detected (JSON vs msgpack based on serializability)
- [ ] **AC-SEC-002**: HMAC-SHA256 signature prevents tampering (constant-time comparison)
- [ ] **AC-SEC-003**: Numpy arrays serialize/deserialize correctly with dtype and shape preserved
- [ ] **AC-SEC-004**: Pandas DataFrames serialize with columns, index, and dtypes preserved
- [ ] **AC-SEC-005**: Pandas Series serialize/deserialize correctly with index and name
- [ ] **AC-SEC-006**: Decimal precision preserved as string (not float conversion)
- [ ] **AC-SEC-007**: Constant-time comparison (hmac.compare_digest) for signature verification
- [ ] **AC-SEC-008**: SECRET_KEY never hardcoded, only from environment variable
- [ ] **AC-SEC-009**: Format auto-detection works (json/msgp prefix)
- [ ] **AC-SEC-010**: Base64 encoding for safe ASCII transport
- [ ] **AC-SEC-011**: Invalid SECRET_KEY raises ValueError (no fallback)
- [ ] **AC-SEC-012**: Tampered data raises ValueError with clear message

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES | No hardcoded secrets in code | ✅ OK - SECRET_KEY from environment only |
| SEC-004 | BASE_RULES | HMAC signing for API requests | ✅ OK - HMAC-SHA256 used |
| SEC-010 | BASE_RULES | Encryption at rest | ✅ OK - Data signed for tamper detection |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Specific ValueError with context |
| LOG-004 | BASE_RULES | Error logging with stack traces | ❌ GAP - Missing exc_info in error handlers (lines 274, 278, 342, 346, 350) |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - No mutable default arguments |
| SEC-PICKLE-001 | Security | Never use pickle module | ✅ OK - Uses msgpack/JSON instead |

**GAP Analysis:**
1. **LOG-004 (P0)**: Error handlers log without `exc_info=True` (lines 274, 278, 342, 346, 350)
   - Impact: Debugging signature failures and serialization errors harder without stack traces
   - Fix: Add `exc_info=True` to all `logger.error()` calls

---

## Dependencies
- **External:** `base64`, `hashlib`, `hmac`, `json`, `logging`, `os`, `decimal`, `msgpack`, `numpy`, `pandas`
- **Internal:** None (core utility module)

---

## Required Tests
- **test_secure_serialization.py:**
  - Success: JSON serialization for simple types (dict, list, str, int, float, bool)
  - Success: Msgpack serialization for complex types (numpy arrays, pandas)
  - Success: Numpy array roundtrip (1D, 2D, different dtypes)
  - Success: Pandas DataFrame roundtrip with dtypes preserved
  - Success: Pandas Series roundtrip with index and name
  - Success: Decimal precision preserved (not lost to float conversion)
  - Security: HMAC signature verification succeeds with correct key
  - Security: Tampering detection (invalid signature raises ValueError)
  - Security: Different secret key fails verification
  - Format: Auto-detection of json vs msgp format
  - Format: Base64 encoding/decoding works correctly
  - Error: Invalid SECRET_KEY (missing or too short) raises ValueError
  - Error: Malformed signed_data raises ValueError
  - Error: Unknown format type raises ValueError
  - Edge: Empty dict/list serializes correctly
  - Edge: Large numpy array (>1MB) serializes
  - Edge: Nested structure with mixed types
  - Performance: JSON format faster for simple data
  - Performance: Msgpack format handles binary data efficiently

---

## Notes
- **CRITICAL SECURITY MODULE** - This replaces insecure pickle usage
- All dependencies are required (no fallbacks) - fail fast if msgpack/numpy/pandas missing
- msgpack used for binary/complex data (faster, more compact than JSON)
- JSON used for simple data (faster, more human-readable)
- Constant-time comparison prevents timing attacks on signature verification
- SECRET_KEY must be set via environment variable before import
