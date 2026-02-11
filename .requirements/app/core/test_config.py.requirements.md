# test_config.py Requirements

**File:** `app/core/test_config.py`  
**Purpose:** Test Configuration and Environment Isolation  
**Author:** Testing Reviewer Audit  
**Date:** 2026-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.287843

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/core/exceptions.py` (ConfigurationError)

---

## Purpose & Scope

This module provides isolated test configuration to prevent conflicts between test and production environments. It manages:

1. **Test environment variables** - Separate from production
2. **Test database configuration** - Different ports and databases
3. **Temporary directories** - Isolated file system resources
4. **Environment cleanup** - Restore original state after tests

**Critical for Testing:** Prevents test data from contaminating production databases and file systems.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods |
|-------|---------|---------|
| `TestEnvironmentConfig` | Test-specific Pydantic configuration | Field validators for ports, test-specific settings |
| `TestConfigManager` | Manages test environment lifecycle | `setup_test_environment()`, `cleanup_test_environment()`, temp directory management |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `get_test_config_manager()` | Get global test config manager | `TestConfigManager` |
| `setup_test_environment()` | Setup isolated test environment | `TestEnvironmentConfig` |
| `cleanup_test_environment()` | Cleanup test environment | `None` |
| `get_test_config()` | Get current test configuration | `TestEnvironmentConfig` |
| `get_test_temp_dir(name)` | Get temporary directory | `Path` |

---

## File-Specific Requirements

### TST-001: Environment Isolation
**Priority:** P0 (Critical - Prevents production contamination)

**Requirement:** Test environment must be completely isolated from production (different DB ports, databases, file paths).

**Acceptance Criteria:**
```python
config = setup_test_environment()
assert config.test_db_port == 5433  # Different from production
assert config.test_db_name == "algotrading_test"
assert "test" in config.environment
```

**Check:** Verify all test values differ from production

---

### TST-002: Temporary Directory Cleanup
**Priority:** P0 (Critical - Prevents disk space issues)

**Requirement:** All temporary directories must be cleaned up after tests complete.

**Acceptance Criteria:**
```python
manager = get_test_config_manager()
manager.setup_test_environment()
temp_dirs = manager.temp_dirs
manager.cleanup_test_environment()
# All temp dirs should be removed
for path in temp_dirs.values():
    assert not path.exists()
```

**Check:** Verify cleanup removes all temp files

---

### TST-003: Environment Restoration
**Priority:** P0 (Critical - Prevents test interference)

**Requirement:** Original environment variables must be restored after test cleanup.

**Acceptance Criteria:**
```python
original_value = os.environ.get("DB_PORT")
manager = get_test_config_manager()
manager.setup_test_environment()
assert os.environ["DB_PORT"] == "5433"
manager.cleanup_test_environment()
assert os.environ.get("DB_PORT") == original_value
```

**Check:** Verify environment variable restoration

---

### TST-004: Port Validation
**Priority:** P1 (High - Prevents binding errors)

**Requirement:** All test ports must be in valid range (1024-65535).

**Acceptance Criteria:**
```python
config = TestEnvironmentConfig(test_db_port=5433)
# Should pass
config = TestEnvironmentConfig(test_db_port=100)
# Should raise ValueError
```

**Check:** Pydantic field validators

---

### TST-005: Configuration Validation
**Priority:** P1 (High - Prevents invalid configs)

**Requirement:** Pydantic must validate all configuration values.

**Acceptance Criteria:**
```python
config = TestEnvironmentConfig()
assert config.environment == "testing"
assert config.debug == True
```

**Check:** Pydantic validation

---

### TST-006: No Production Database Access
**Priority:** P0 (Critical - Data safety)

**Requirement:** Tests must NEVER connect to production database.

**Acceptance Criteria:**
```python
config = setup_test_environment()
assert config.test_db_name != "algotrading"  # Production DB name
assert "test" in config.test_db_name.lower()
```

**Check:** String validation of database names

---

### TST-007: Unique Temporary Directories
**Priority:** P2 (Medium - Prevents test conflicts)

**Requirement:** Each test run should use unique temporary directory names.

**Acceptance Criteria:**
```python
manager1 = TestConfigManager()
manager1.setup_test_environment()
manager2 = TestConfigManager()
manager2.setup_test_environment()
assert manager1.temp_dirs["logs"] != manager2.temp_dirs["logs"]
```

**Check:** UUID usage in directory names

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **CFG-002:** Environment variables used ✅
- **CFG-003:** Pydantic validation ✅
- **LOG-004:** Error logging ✅

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **CC-006:** Explicit error handling ✅

### Medium Priority (P2)
- **TST-005:** Fixtures used ✅ (TestConfigManager as fixture)
- **QL-002:** No dead code ✅

---

## Known Issues & Technical Debt

### Issues
1. **Global state** - Single global manager may cause issues in parallel tests
2. **No parallel test support** - Temp directories may collide
3. **Hardcoded ports** - Should check if ports are available

### Technical Debt
1. Add **port availability checking** before using ports
2. Implement **test database auto-setup** (create/drop DB)
3. Add **Docker support** for containerized test environments

---

## Testing Requirements

### Unit Tests
- [ ] Test environment isolation
- [ ] Test temporary directory creation/cleanup
- [ ] Test environment variable restoration
- [ ] Test port validation
- [ ] Test Pydantic validation

### Integration Tests
- [ ] Test with actual database connection
- [ ] Test concurrent test runs
- [ ] Test cleanup after test failures

---

## Security Considerations

1. **No production secrets in tests** ✅ (uses test_password, etc.)
2. **Test credentials isolated** ✅
3. **No sensitive data in temp dirs** ✅

---

## Performance Considerations

1. **Temp directory creation** should be fast ✅
2. **Environment variable switching** minimal overhead ✅
3. **Cleanup should not block** ✅

---

## Dependencies

**External:**
- `pydantic` (settings, field validation)
- `pydantic_settings` (BaseSettings)
- `logging` (stdlib)
- `os` (stdlib)
- `tempfile` (stdlib)
- `pathlib` (stdlib)
- `typing` (stdlib)

**Internal:**
- `app.core.exceptions` (ConfigurationError)

---

## Migration Notes

**From old test config:**
1. Replace direct environment variable access with TestConfigManager
2. Use setup/cleanup in test fixtures
3. Update test database connection strings

**To new test config:**
1. Add TestConfigManager to conftest.py
2. Update all tests to use isolated environment
3. Add cleanup to pytest fixtures

---

## Changelog

### Version 1.0.0 (2026-02-06)
- Initial implementation
- Pydantic-based configuration
- Temporary directory management
- Environment isolation

---

**Last Updated:** 2026-02-06  
**Next Review:** After test suite migration
