# Requirements: app/core/config_validator.py

**File Path:** `app/core/config_validator.py`
**Component:** Configuration Validator
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module provides **validation for YAML configuration files and environment variables** to ensure production readiness. It validates syntax, required sections, placeholder values, and environment-specific settings.

**Key Features:**
- YAML syntax validation
- Environment-specific validation (production, staging, development)
- Placeholder detection
- Database/risk/circuit breaker config validation
- Batch backtest config validation

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Classes & Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `ProfileOptimizationConfigValidator` | BaseModel | 28-86 | Validator for profile_optimization.yaml |
| `BatchBacktestConfigValidator` | BaseModel | 88-173 | Validator for profile_batch_backtest.yaml |
| `ValidationErrorDetail` | BaseModel | 176-182 | Detailed validation error info |
| `ValidationResult` | BaseModel | 184-223 | Result of configuration validation |
| `DatabaseConfigValidator` | BaseModel | 225-250 | Database configuration validation |
| `RiskConfigValidator` | BaseModel | 253-275 | Risk management config validation |
| `CircuitBreakerValidator` | BaseModel | 278-293 | Circuit breaker config validation |
| `ConfigValidator` | class | 295-960 | Main configuration validator |

### Dependencies

**External:**
- `datetime`, `logging`, `os`, `re`, `sys`, `pathlib`, `typing`
- `yaml`, `pydantic`

---

## GAP Analysis

### P0 (Critical) Violations

**NONE** - Well-structured validation module.

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CFG-003** | Some validators missing edge cases | Various | Add more comprehensive validation |
| **LOG-005** | Error messages may contain sensitive data | 346, 519 | Sanitize config values in error messages |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long validation methods | 567-629, 668-762 | Break into smaller methods |
| **ARCH-004** | Some functions exceed 20 lines | Various | Extract helper methods |

### P3 (Low) Issues

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-001** | Some variable names could be clearer | Various | Minor naming improvements |

---

## Acceptance Criteria

### AC-CFG-001: Configuration Validation
```bash
# All configs must be validated before use
grep -c "validate_" app/core/config_validator.py
# Expected: Multiple validation methods
```

### AC-SEC-001: No Hardcoded Secrets
```bash
# No secrets in validator
grep -iE "api_key|secret|password" app/core/config_validator.py | grep -vE "env_file|getenv|placeholder|field" | wc -l
# Expected: 0
```

### AC-LOG-001: Error Logging
```bash
# Validation errors logged
grep -c "logger.error" app/core/config_validator.py
# Expected: >= validation error points
```

---

## File-Specific Requirements

### FSR-001: YAML Syntax Validation
**Priority:** P0
**Description:** Must validate YAML syntax before processing

**Requirements:**
- [ ] Use `yaml.safe_load()` to prevent code injection
- [ ] Catch YAML parsing errors
- [ ] Provide clear error messages with line numbers
- [ ] Handle malformed YAML gracefully

**Acceptance Test:**
```python
def test_yaml_syntax_validation():
    validator = ConfigValidator()
    
    # Create invalid YAML file
    invalid_yaml = Path("/tmp/invalid.yaml")
    invalid_yaml.write_text("invalid: [unclosed")
    
    result = validator.validate_yaml_syntax(invalid_yaml)
    assert not result.is_valid
    assert any("YAML" in error.message for error in result.errors)
```

### FSR-002: Production Configuration Validation
**Priority:** P0
**Description:** Production configs must meet strict standards

**Requirements:**
- [ ] Environment must be "production"
- [ ] Debug mode must be disabled
- [ ] No placeholder values allowed
- [ ] All required sections present
- [ ] No default secret keys

**Acceptance Test:**
```python
def test_production_validation():
    validator = ConfigValidator()
    
    # Create production config with debug enabled
    prod_yaml = validator.config_dir / "production.yaml"
    # ... write config with debug: True
    
    result = validator.validate_production_config()
    assert not result.is_valid
    assert any("debug" in error.message.lower() for error in result.errors)
```

### FSR-003: Placeholder Detection
**Priority:** P1
**Description:** Detect placeholder values that should be replaced

**Requirements:**
- [ ] Detect common placeholder patterns
- [ ] Warn (not error) for placeholders
- [ ] Support custom placeholder patterns
- [ ] Recursive search in nested structures

**Acceptance Test:**
```python
def test_placeholder_detection():
    validator = ConfigValidator()
    config = {
        "api_key": "your_api_key_here",
        "database_url": "https://example.com",
    }
    
    validator.validate_placeholders(config)
    assert len(validator.result.warnings) > 0
    assert any("placeholder" in w.message.lower() for w in validator.result.warnings)
```

### FSR-004: Database Configuration Validation
**Priority:** P1
**Description:** Database configs must be valid

**Requirements:**
- [ ] Valid database URL format
- [ ] Backup interval reasonable (60-3600 seconds)
- [ ] Retention period reasonable (1-168 hours)
- [ ] Connection string uses supported protocol

**Acceptance Test:**
```python
def test_database_config_validation():
    # Invalid backup interval
    with pytest.raises(ValidationError, match="must be at least 60 seconds"):
        DatabaseConfigValidator(backup_interval_seconds=30)
    
    # Invalid retention
    with pytest.raises(ValidationError, match="should not exceed 168 hours"):
        DatabaseConfigValidator(retention_hours=200)
```

### FSR-005: Risk Configuration Validation
**Priority:** P1
**Description:** Risk management configs must be safe

**Requirements:**
- [ ] Percentages between 0 and 1
- [ ] Leverage between 1 and 10
- [ ] VaR and position size limits reasonable

**Acceptance Test:**
```python
def test_risk_config_validation():
    # Invalid percentage
    with pytest.raises(ValidationError, match="between 0 and 1"):
        RiskConfigValidator(max_var_daily_pct=1.5)
    
    # Invalid leverage
    with pytest.raises(ValidationError, match="should not exceed 10.0"):
        RiskConfigValidator(max_leverage=15)
```

### FSR-006: Environment Variable Validation
**Priority:** P2
**Description:** Validate environment variable references

**Requirements:**
- [ ] Extract ${VAR} references
- [ ] Check against .env file
- [ ] Check system environment
- [ ] Report missing variables

**Acceptance Test:**
```python
def test_environment_variable_validation():
    validator = ConfigValidator()
    config = {"database_url": "${DATABASE_URL}"}
    
    # Without DATABASE_URL set
    result = validator.validate_environment_variables(config, env_file=None)
    assert "DATABASE_URL" in str(result.warnings)
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 90%
- **Critical Paths:** 100%

### Required Tests
1. **Validation Tests:**
   - `test_yaml_syntax_validation()`
   - `test_production_validation()`
   - `test_placeholder_detection()`

2. **Config Tests:**
   - `test_database_config_validation()`
   - `test_risk_config_validation()`
   - `test_circuit_breaker_validation()`

3. **Integration Tests:**
   - `test_batch_backtest_config_validation()`
   - `test_profile_optimization_config_validation()`

---

## Performance Requirements

- **YAML Parsing:** < 100ms for typical config files
- **Validation:** < 50ms for typical configs
- **Placeholder Detection:** < 200ms for large configs

---

## Security Requirements

- **No Code Execution:** Use `yaml.safe_load()` only
- **Secret Protection:** Don't log secret values
- **Input Validation:** Validate all config values
- **Path Traversal:** Validate file paths

---

## Documentation Requirements

1. **Configuration Guide:** All config options documented
2. **Validation Rules:** List of all validations
3. **Error Messages:** Clear explanations for each error
4. **Production Checklist:** Required settings for production

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

1. Add edge case validation
2. Sanitize error messages
3. Add comprehensive tests
4. Update documentation

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
