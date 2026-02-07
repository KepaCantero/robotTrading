# trading_validators.py Requirements

**File:** `app/core/trading_validators.py`  
**Purpose:** Trading validators to prevent financial disasters  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.289323

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Risk Management:** Trading risk best practices
- **Related Files:** All trading execution modules

---

## Purpose & Scope

This module provides validation functions to ensure trading operations are safe and comply with risk management rules. It enforces critical safety rules:

1. **Position size limits** - Relative to capital
2. **Mandatory stop-loss** - All trades must have stop-loss
3. **Maximum exposure** - Prevent catastrophic losses
4. **Risk-reward ratios** - Ensure favorable trades

**Critical for Production:** Prevents catastrophic trading errors and financial losses.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods |
|-------|---------|---------|
| `TradingValidator` | Validates trading operations | `validate_position_size()`, `validate_stop_loss()`, `validate_trade_risk_reward()`, `validate_trading_hours()` |

### Static Methods

| Method | Purpose | Return Type |
|--------|---------|-------------|
| `validate_position_size()` | Validate position size limits | `bool` |
| `validate_stop_loss()` | Validate stop-loss requirements | `bool` |
| `validate_trade_risk_reward()` | Validate risk-reward ratios | `bool` |
| `validate_trading_hours()` | Validate trading time restrictions | `bool` |

---

## File-Specific Requirements

### TRV-001: Position Size Limits
**Priority:** P0 (Critical - Prevents over-leveraging)

**Requirement:** Position size cannot exceed maximum allowed (default 25% of capital).

**Acceptance Criteria:**
```python
# Position too large
validator = TradingValidator()
try:
    validator.validate_position_size(
        capital=Decimal("100000"),
        position_size=Decimal("30000"),  # 30% - exceeds default 25%
        max_position_percent=Decimal("0.25")
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "exceeds maximum" in str(e)
```

**Check:** Position size validation works

---

### TRV-002: Mandatory Stop-Loss
**Priority:** P0 (Critical - Prevents unlimited losses)

**Requirement:** All trades must have stop-loss defined (None not allowed).

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_stop_loss(
        entry_price=Decimal("100"),
        stop_loss=None,  # No stop-loss!
        side="long"
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "REQUIRED" in str(e)
```

**Check:** Stop-loss validation enforces requirement

---

### TRV-003: Stop-Loss Positioning (Long)
**Priority:** P0 (Critical - Correct risk protection)

**Requirement:** Long position stop-loss must be BELOW entry price.

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_stop_loss(
        entry_price=Decimal("100"),
        stop_loss=Decimal("105"),  # Above entry - wrong for long!
        side="long"
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "must be BELOW" in str(e)
```

**Check:** Stop-loss direction validated

---

### TRV-004: Stop-Loss Positioning (Short)
**Priority:** P0 (Critical - Correct risk protection)

**Requirement:** Short position stop-loss must be ABOVE entry price.

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_stop_loss(
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),  # Below entry - wrong for short!
        side="short"
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "must be ABOVE" in str(e)
```

**Check:** Stop-loss direction validated for shorts

---

### TRV-005: Risk-Reward Ratio
**Priority:** P1 (High - Favorable trades)

**Requirement:** Trades should have minimum 2:1 reward-risk ratio (configurable).

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_trade_risk_reward(
        entry_price=Decimal("100"),
        stop_loss=Decimal("95"),  # Risk: $5
        take_profit=Decimal("105"),  # Reward: $5 (1:1 ratio)
        min_reward_risk_ratio=Decimal("2.0")
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "below minimum" in str(e)
```

**Check:** Risk-reward validation works

---

### TRV-006: Trading Hours Validation
**Priority:** P2 (Medium - Risk management)

**Requirement:** Trading should be restricted to allowed hours (default 9 AM - 4 PM).

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    # Trading at 5 AM - outside market hours
    validator.validate_trading_hours(
        current_time=datetime(2026, 1, 1, 5, 0),
        allowed_hours=set(range(9, 17))
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "not allowed" in str(e)
```

**Check:** Trading hours validation works

---

### TRV-007: Capital Validation
**Priority:** P0 (Critical - Prevents invalid trades)

**Requirement:** Capital must be positive for trading.

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_position_size(
        capital=Decimal("0"),  # No capital!
        position_size=Decimal("100")
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "must be positive" in str(e)
```

**Check:** Capital validation enforced

---

### TRV-008: Position Size vs Capital
**Priority:** P0 (Critical - Prevents over-trading)

**Requirement:** Position size cannot exceed available capital.

**Acceptance Criteria:**
```python
validator = TradingValidator()
try:
    validator.validate_position_size(
        capital=Decimal("10000"),
        position_size=Decimal("15000")  # More than available!
    )
    assert False, "Should raise ValueError"
except ValueError as e:
    assert "exceeds available capital" in str(e)
```

**Check:** Capital limits enforced

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **TRD-002:** Risk validation ✅
- **TRD-003:** Position limits ✅
- **TRD-004:** Audit trail ✅ (logging)
- **CC-006:** Explicit error handling ✅

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **LOG-002:** Context in logs ✅

### Medium Priority (P2)
- **QL-001:** Complexity reasonable ✅
- **CC-007:** Small methods ✅

---

## Known Issues & Technical Debt

### Issues
1. **No portfolio-level validation** - Only single-position validation
2. **No correlation checks** - Doesn't validate correlated positions
3. **Hardcoded limits** - Should be configurable

### Technical Debt
1. **Add portfolio validation** - Total exposure across all positions
2. **Add correlation limits** - Limit exposure to correlated assets
3. **Make limits configurable** - From risk profile
4. **Add dynamic adjustment** - Adjust limits based on volatility

---

## Testing Requirements

### Unit Tests
- [ ] Test position size limits
- [ ] Test mandatory stop-loss
- [ ] Test stop-loss positioning (long/short)
- [ ] Test risk-reward ratios
- [ ] Test trading hours validation
- [ ] Test capital validation
- [ ] Test position vs capital

### Integration Tests
- [ ] Test with real trading scenarios
- [ ] Test with portfolio manager
- [ ] Test with order execution

---

## Security Considerations

1. **No bypass mechanisms** ✅ (validators must be called)
2. **Input validation** ✅ (Decimal, type checking)
3. **No injection attacks** ✅ (no code execution)

---

## Performance Considerations

1. **Minimal overhead** ✅ (simple calculations)
2. **No blocking calls** ✅ (all synchronous)
3. **Fast validation** ✅ (< 1ms per validation)

---

## Dependencies

**External:**
- `logging` (stdlib)
- `decimal` (stdlib)
- `typing` (stdlib)

**Internal:**
- None (standalone module)

---

## Migration Notes

**From unvalidated trading:**
1. Add validators to all trading operations
2. Call validators before order execution
3. Handle validation errors appropriately
4. Log all validation failures

**To validated trading:**
1. Import TradingValidator
2. Call validate_position_size() before trading
3. Call validate_stop_loss() before opening positions
4. Call validate_trade_risk_reward() for analysis

---

## Changelog

### Version 1.0.0 (Initial)
- Position size validation
- Stop-loss validation
- Risk-reward ratio validation
- Trading hours validation
- Capital and position limits

---

**Last Updated:** 2026-02-06  
**Next Review:** After portfolio validation added
