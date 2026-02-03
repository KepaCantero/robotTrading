# Requirements: app/core/shadow_mode.py

**File Path:** `app/core/shadow_mode.py`
**Component:** Shadow Mode - Safe Production Testing
**Last Updated:** 2026-02-06
**Audit Status:** NEEDS_AUDIT

---

## Purpose

This module implements **Shadow Mode**, a critical SRE component that allows testing trading strategies with the REAL API without executing actual trades. This is different from paper trading - it intercepts execution calls while using real broker APIs.

**Key Features:**
- Real API interception without execution
- WAL (Write-Ahead Log) integration for crash recovery
- Data Sanity Layer validation
- Shadow vs Real comparison metrics
- Comprehensive audit trails

---

## References

See [../../BASE_RULES.md](../../BASE_RULES.md) for universal rules.

---

## File Analysis

### Classes & Functions

| Name | Type | Lines | Purpose |
|------|------|-------|---------|
| `ShadowModeType` | Enum | 76-81 | Shadow mode types (dry_run, shadow, production) |
| `ShadowModeConfig` | dataclass | 84-109 | Configuration for shadow mode execution |
| `ShadowExecutionResult` | dataclass | 112-156 | Result of shadow mode execution |
| `ShadowRealComparison` | dataclass | 159-174 | Comparison between shadow and real execution |
| `ShadowModeExecutor` | class | 177-835 | Main shadow mode executor |
| `ShadowModeAwareBroker` | class | 838-903 | Broker wrapper integrating shadow mode |
| `detect_shadow_mode_from_env()` | function | 906-940 | Load shadow config from environment |

### Dependencies

**Internal:**
- `app.core.interfaces.broker_base.Order`
- `app.sre.data_integrity.sanity_layer.DataSanityLayer`
- `app.sre.state_machine.wal_persistence.OrderLog, OrderState, OrderStateMachine`

**External:**
- `asyncio`, `logging`, `uuid`, `dataclasses`, `datetime`, `decimal`, `enum`, `typing`

---

## GAP Analysis

### P0 (Critical) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **TYP-001** | Missing type hints for some parameters | Various | Add type hints for parameters like `broker_client: Any` |
| **ARCH-001** | Direct dependency on concrete implementations | 198-202 | Should depend on IBroker interface, not `Any` |
| **CC-006** | Generic exception handling without specific types | 388-412 | Catch specific exceptions instead of broad ones |

### P1 (High) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **TYP-003** | Using `Any` type without justification | 198, 848 | Use proper Protocol or interface types |
| **LOG-005** | Sensitive data logging (order details) | 278-285 | Mask sensitive fields in logs |
| **SEC-005** | Audit logging incomplete | 810-830 | Ensure all shadow executions are logged |

### P2 (Medium) Violations

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-007** | Long functions (>20 lines) | 234-413 | Break down `execute_order_shadow` |
| **ARCH-004** | Some functions could be smaller | 457-577 | Extract simulation logic |
| **QL-007** | High parameter count (7 params) | 234-242 | Use parameter object pattern |

### P3 (Low) Issues

| Rule ID | Description | Line(s) | Fix Required |
|---------|-------------|---------|--------------|
| **CC-001** | Some variable names could be more descriptive | Various | Minor naming improvements |

---

## Acceptance Criteria

### AC-ARCH-001: Domain Layer Purity
```bash
# Verify no infrastructure imports in domain (N/A - this is infrastructure layer)
```

### AC-TYP-001: Type Hints Coverage
```bash
# All functions have return type hints
grep -E "def [a-z_]+.*->" app/core/shadow_mode.py | wc -l
# Expected: All public functions typed
```

### AC-SEC-001: No Hardcoded Secrets
```bash
# No API keys in code
grep -iE "api_key|secret|password|token" app/core/shadow_mode.py | grep -vE "os.environ|getenv|Secret" | wc -l
# Expected: 0 hardcoded secrets
```

### AC-LOG-001: Error Logging
```bash
# All exceptions logged
grep -c "logger.error" app/core/shadow_mode.py
# Expected: >= exception handlers
```

---

## File-Specific Requirements

### FSR-001: Shadow Mode Safety
**Priority:** P0
**Description:** Shadow mode must NEVER execute real trades

**Requirements:**
- [ ] Interceptor must verify shadow mode is enabled before execution
- [ ] All shadow orders must be tagged with `SHADOW_` prefix
- [ ] WAL integration must mirror real execution exactly
- [ ] Audit trail must be immutable

**Acceptance Test:**
```python
async def test_shadow_mode_never_executes_real_trades():
    config = ShadowModeConfig(enabled=True)
    executor = ShadowModeExecutor(broker=real_broker, wal=wal, config=config)
    result = await executor.execute_order_shadow(symbol="AAPL", side="BUY", quantity=100)
    assert result.shadow_order_id.startswith("SHADOW_")
    assert not real_broker.was_called()
```

### FSR-002: WAL Integration
**Priority:** P0
**Description:** Shadow mode must write to WAL exactly like real execution

**Requirements:**
- [ ] Order state transitions: SUBMITTING → ACK_RECEIVED → FILLED/REJECTED
- [ ] All metadata must include `shadow_mode: True` flag
- [ ] WAL recovery must distinguish shadow from real orders

**Acceptance Test:**
```python
async def test_shadow_wal_integration():
    result = await executor.execute_order_shadow(...)
    wal_logs = await wal.get_logs(result.shadow_order_id)
    assert any(log.state == OrderState.SUBMITTING for log in wal_logs)
    assert any(log.state == OrderState.ACK_RECEIVED for log in wal_logs)
    assert log.metadata.get("shadow_mode") == True
```

### FSR-003: Price Validation
**Priority:** P1
**Description:** Shadow mode must validate prices with Data Sanity Layer

**Requirements:**
- [ ] Prices must be validated before execution
- [ ] Stale price warnings must be logged
- [ ] Failed validation must prevent execution

**Acceptance Test:**
```python
async def test_shadow_price_validation():
    validation = SanityCheckResult.FAIL, "Price is stale"
    with pytest.raises(ValueError, match="Price validation failed"):
        await executor.execute_order_shadow(..., price=stale_price)
```

### FSR-004: Shadow vs Real Comparison
**Priority:** P2
**Description:** Track performance differences between shadow and real execution

**Requirements:**
- [ ] Track price differences in basis points
- [ ] Track timing differences in milliseconds
- [ ] Alert if differences exceed thresholds

**Acceptance Test:**
```python
async def test_shadow_real_comparison():
    comparisons = await executor.compare_shadow_vs_real()
    for comp in comparisons:
        if comp.price_difference_bps:
            assert abs(comp.price_difference_bps) <= 50  # 50 bps threshold
```

### FSR-005: Audit Logging
**Priority:** P1
**Description:** All shadow executions must be logged to audit trail

**Requirements:**
- [ ] JSON-formatted log entries
- [ ] Include order details, timestamps, and results
- [ ] Atomic writes to prevent data loss

**Acceptance Test:**
```python
async def test_shadow_audit_log():
    result = await executor.execute_order_shadow(...)
    with open(audit_log_path) as f:
        log_entry = json.loads(f.readlines()[-1])
        assert log_entry["type"] == "SHADOW_EXECUTION"
        assert log_entry["data"]["shadow_order_id"] == result.shadow_order_id
```

---

## Testing Requirements

### Test Coverage
- **Minimum Coverage:** 90%
- **Critical Paths:** 100%

### Required Tests
1. **Unit Tests:**
   - `test_shadow_mode_config_validation()`
   - `test_shadow_order_id_generation()`
   - `test_fill_simulation_models()`

2. **Integration Tests:**
   - `test_shadow_wal_integration()`
   - `test_shadow_sanity_layer_integration()`
   - `test_shadow_broker_interception()`

3. **Safety Tests:**
   - `test_shadow_mode_never_executes_real_trades()`
   - `test_shadow_daily_limit_enforcement()`
   - `test_shadow_to_production_transition_validation()`

---

## Performance Requirements

- **Order Latency:** Shadow execution should complete within 200ms
- **WAL Write:** Must complete within 50ms
- **Comparison:** Should not add more than 10ms overhead

---

## Security Requirements

- **No Real Execution:** Shadow mode must be physically incapable of executing real trades
- **Audit Trail:** All shadow orders must be logged with `SHADOW_` prefix
- **Access Control:** Shadow mode configuration must require authentication
- **Secret Management:** No hardcoded credentials (Rule 28 compliant)

---

## Documentation Requirements

1. **Architecture Diagram:** Show Shadow Mode integration points
2. **API Documentation:** Document all public methods
3. **Runbook:** Troubleshooting guide for shadow mode issues
4. **Transition Guide:** How to safely transition from shadow to production

---

## Checklist

- [ ] All P0 violations fixed
- [ ] All P1 violations fixed or documented
- [ ] Type hints added to all functions
- [ ] Comprehensive test coverage
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Code review approved

---

## Next Steps

1. Fix P0 violations (type hints, interface dependencies)
2. Add comprehensive tests
3. Complete security review
4. Update documentation
5. Final code review

---

**Audited By:** Automated Audit System
**Date:** 2026-02-06
**Version:** 1.0.0
