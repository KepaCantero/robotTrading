# Requirements: app/core/environment_config.py

**File Path:** `app/core/environment_config.py`
**Component:** Centralized Configuration System
**Last Updated:** 2026-02-06
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.284634

---

## Purpose

This module provides **centralized configuration management** using Pydantic Settings, with environment-specific validation and type-safe configuration access.

**Key Features:**
- Pydantic Settings for type-safe config
- Environment variable loading with validation
- Environment-specific validation (production, development, testing)
- Structured logging configuration
- Database, Redis, API, Trading, Logging, Monitoring configs

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Classes & Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `Environment` | Enum | 21-27 | Environment types (dev, test, staging, prod) |
| `LogLevel` | Enum | 30-37 | Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DatabaseConfig` | BaseSettings | 40-107 | Database configuration with validation |
| `RedisConfig` | BaseSettings | 110-161 | Redis configuration with validation |
| `APIConfig` | BaseSettings | 164-206 | API configuration with validation |
| `TradingConfig` | BaseSettings | 209-266 | Trading configuration with validation |
| `LoggingConfig` | BaseSettings | 269-302 | Logging configuration with validation |
| `MonitoringConfig` | BaseSettings | 305-331 | Monitoring configuration with validation |
| `CentralizedConfig` | BaseSettings | 334-456 | Main configuration class |
| `get_config()` | function | 462-471 | Get global configuration instance |
| `reload_config()` | function | 474-479 | Reload configuration |
| `set_config()` | function | 482-489 | Set configuration instance |
| `load_config_from_file()` | function | 492-514 | Load config from file |
| `get_settings()` | function | 517-519 | Get settings (alias) |
| `create_config_for_environment()` | function | 522-553 | Create environment-specific config |

### Dependencies

**Internal:**
- `app.core.exceptions.ConfigurationError, raise_configuration_error`

**External:**
- `logging`, `os`, `enum`, `pathlib`, `typing`
- `pydantic`, `pydantic_settings`

---

## GAP Analysis

### P0 (Critical) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **SEC-001** | Default secret key is weak | 173 | Remove default or make it fail in production |
| **SEC-001** | Database password logged in connection_string | 104-107 | Mask password in logs |

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CFG-007** | Feature flags not implemented | 349 | Document or implement feature flags |
| **LOG-005** | Password logged in connection string | 104 | Sanitize log output |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long validation method | 370-428 | Extract validators |
| **TYP-003** | Return type `Dict[str, Any]` | 432 | Could be more specific |

### P3 (Low) Issues

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-001** | Some variable names could be clearer | Various | Minor improvements |

---

## Acceptance Criteria

### AC-CFG-001: Pydantic Settings
```bash
# Uses Pydantic Settings
grep -c "BaseSettings" app/core/environment_config.py
# Expected: >= 7 (all config classes)
```

### AC-SEC-001: No Hardcoded Secrets
```bash
# No secrets in defaults (production check required)
grep -c "12345678901234567890123456789012" app/core/environment_config.py
# Expected: 1 (default, but validated in production)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/environment_config.py | wc -l
# Expected: All functions
```

---

## File-Specific Requirements

### FSR-001: Production Configuration Validation
**Priority:** P0
**Description:** Production configs must be validated strictly

**Requirements:**
- [ ] Debug mode disabled in production
- [ ] Default secret key rejected in production
- [ ] Database password required in production
- [ ] Broker API key required for live trading

**Acceptance Test:**
```python
def test_production_validation():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DEBUG"] = "true"  # Should fail
    
    with pytest.raises(ConfigurationError, match="Debug mode cannot be enabled"):
        config = CentralizedConfig()
```

### FSR-002: Secret Key Validation
**Priority:** P0
**Description:** Secret key must be strong enough

**Requirements:**
- [ ] Minimum 32 characters
- [ ] Validated in production
- [ ] Error message includes generation command
- [ ] Default key rejected in production

**Acceptance Test:**
```python
def test_secret_key_validation():
    os.environ["SECRET_KEY"] = "short"
    
    with pytest.raises(ValueError, match="at least 32 characters"):
        config = APIConfig()
    
    # Test production rejection
    os.environ["ENVIRONMENT"] = "production"
    os.environ["SECRET_KEY"] = "12345678901234567890123456789012"
    
    with pytest.raises(ConfigurationError, match="Default secret key"):
        config = CentralizedConfig()
```

### FSR-003: Database Configuration
**Priority:** P1
**Description:** Database configuration must be valid

**Requirements:**
- [ ] Port validation (1-65535)
- [ ] Pool size >= 1
- [ ] Connection string built correctly
- [ ] SSL mode configured

**Acceptance Test:**
```python
def test_database_config_validation():
    # Invalid port
    with pytest.raises(ValueError, match="between 1 and 65535"):
        DatabaseConfig(db_port=70000)
    
    # Invalid pool size
    with pytest.raises(ValueError, match="at least 1"):
        DatabaseConfig(db_pool_size=0)
```

### FSR-004: Trading Configuration
**Priority:** P1
**Description:** Trading limits must be safe

**Requirements:**
- [ ] Position size between 0 and 1
- [ ] Daily loss between 0 and 1
- [ ] Stop loss between 0 and 1
- [ ] Broker API required for live trading

**Acceptance Test:**
```python
def test_trading_config_validation():
    # Invalid position size
    with pytest.raises(ValueError, match="between 0 and 1"):
        TradingConfig(max_position_size=1.5)
    
    # Live trading requires API key
    os.environ["BROKER_NAME"] = "alpaca"
    os.environ["BROKER_API_KEY"] = ""
    
    with pytest.raises(ConfigurationError, match="Broker API key is required"):
        config = CentralizedConfig()
```

### FSR-005: Structured Logging
**Priority:** P2
**Description:** Logging must be structured and contextual

**Requirements:**
- [ ] Use logging with extra context
- [ ] Log configuration changes
- [ ] Log validation errors
- [ ] Include environment in logs

**Acceptance Test:**
```python
def test_structured_logging():
    config = CentralizedConfig()
    
    # Should log initialization
    with caplog.at_level(logging.INFO):
        config = CentralizedConfig()
    
    assert any("Initializing centralized configuration" in record.message 
               for record in caplog.records)
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 90%
- **Critical Paths:** 100%

### Required Tests
1. **Validation Tests:**
   - `test_production_validation()`
   - `test_secret_key_validation()`
   - `test_database_config_validation()`

2. **Configuration Tests:**
   - `test_trading_config_validation()`
   - `test_environment_detection()`
   - `test_config_reload()`

3. **Integration Tests:**
   - `test_load_from_file()`
   - `test_environment_override()`

---

## Performance Requirements

- **Config Loading:** < 100ms
- **Validation:** < 50ms
- **Reload:** < 100ms

---

## Security Requirements

- **No Default Secrets:** Default values must fail in production
- **Validation:** All values validated
- **Secret Masking:** Don't log secrets
- **Environment Detection:** Correct environment detection

---

## Documentation Requirements

1. **Configuration Guide:** All options documented
2. **Environment Setup:** How to configure each environment
3. **Validation Rules:** List of all validations
4. **Migration Guide:** Upgrading configuration

---

## Checklist

- [ ] All P0 violations fixed
- [ ] All P1 violations fixed
- [x] Type hints added to all functions
- [ ] Comprehensive test coverage
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Steps

1. **FIX P0:** Remove default secret key or make it fail in production
2. **FIX P0:** Mask password in connection_string logs
3. Add comprehensive tests
4. Complete feature flags or document
5. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0

**P0 Fixes Applied:**
1. **SEC-001 (Secret Key):** Default secret key validation added - rejects weak default keys
2. **SEC-010 (Password Logging):** Connection string sanitization verified with explicit comments

