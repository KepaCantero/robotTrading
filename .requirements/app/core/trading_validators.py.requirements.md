# trading_validators.py

## Purpose
Trading validators to prevent financial disasters. Validates trading operations to ensure they comply with risk management rules and safety limits.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses a simple validator class with static methods. No Pydantic models.

### TradingValidator Class
```python
class TradingValidator:
    """
    Validates trading operations to prevent catastrophic losses.

    Enforces critical safety rules:
    - Position size limits relative to capital
    - Mandatory stop-loss requirements
    - Maximum exposure limits
    """
```

---

## Function Signatures (Contracts)

### `TradingValidator.validate_position_size(capital: Decimal, position_size: Decimal, max_position_percent: Optional[Decimal] = None) -> bool`
**Pre:** capital > 0, position_size > 0, max_position_percent in [0.01, 1.0]
**Post:** Returns True if position size within limits
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** Logs validation result

**Validations:**
- Capital must be positive
- Position size must be positive
- Max position percent defaults to 25% (conservative)
- Max position percent must be between 1% and 100%
- Position size cannot exceed max_position (capital * max_position_percent)
- Position size cannot exceed available capital

**Error messages include:**
- Capital amount
- Position size
- Maximum allowed
- Percentage of capital

### `TradingValidator.validate_stop_loss(entry_price: Decimal, stop_loss: Optional[Decimal], side: str = "long") -> bool`
**Pre:** entry_price > 0, stop_loss > 0, side in ["long", "short"]
**Post:** Returns True if stop-loss properly positioned
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** Logs validation result, warns if stop-loss too wide (>50%)

**CRITICAL:** Stop-loss is MANDATORY for all trades

**Validations:**
- Entry price must be positive
- Stop-loss is REQUIRED (cannot be None)
- Stop-loss price must be positive
- **Long positions:** stop-loss must be BELOW entry price
- **Short positions:** stop-loss must be ABOVE entry price
- Warns if stop-loss is more than 50% away from entry

### `TradingValidator.validate_trade_risk_reward(entry_price: Decimal, stop_loss: Decimal, take_profit: Optional[Decimal] = None, min_reward_risk_ratio: Decimal = Decimal("2.0")) -> bool`
**Pre:** entry_price > 0, stop_loss > 0
**Post:** Returns True if risk-reward ratio acceptable
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** Logs validation result

**Validations:**
- Stop-loss is required
- Entry price and stop-loss must be positive
- Take-profit (if provided) must be positive
- Reward/risk ratio must be >= min_reward_risk_ratio (default 2.0)
- Skips validation if no take-profit set

**Risk-reward calculation:**
- Risk = abs(entry_price - stop_loss)
- Reward = abs(take_profit - entry_price)
- Ratio = Reward / Risk

### `TradingValidator.validate_trading_hours(current_time, allowed_hours: Optional[set] = None) -> bool`
**Pre:** current_time has hour attribute
**Post:** Returns True if trading allowed at current time
**Raises:** ValueError if trading not allowed
**Retry:** No
**Side Effects:** Logs validation result

**Validations:**
- Default allowed hours: 9 AM - 4 PM (market hours)
- Current hour must be in allowed_hours set
- Prevents trading during high-risk periods

---

## Acceptance Criteria
- [ ] TRD-002: All orders validated before execution
- [ ] TRD-003: Position limits enforced (max 25% of capital by default)
- [ ] Position size cannot exceed available capital
- [ ] RSK-003: Drawdown limits (via position size limits)
- [ ] Stop-loss is MANDATORY for all trades
- [ ] Stop-loss positioned correctly (below for long, above for short)
- [ ] Warns if stop-loss too wide (>50%)
- [ ] Risk-reward ratio >= 2.0 (default)
- [ ] Trading hours validation (default 9 AM - 4 PM)
- [ ] All validations log results
- [ ] ValueError raised with descriptive messages for failures

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-002 | BASE_RULES.md | Risk validation | ✅ OK - Position size validated |
| TRD-003 | BASE_RULES.md | Position limits | ✅ OK - Max 25% default |
| RSK-003 | BASE_RULES.md | Drawdown control | ✅ OK - Via position limits |
| EXE-001 | BASE_RULES.md | Order validation | ✅ OK - All inputs validated |
| SEC-007 | BASE_RULES.md | Input validation | ✅ OK - Comprehensive validation |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - ValueError with details |
| LOG-004 | BASE_RULES.md | Error logging | ⚠️ PARTIAL - Logs errors but no stack traces |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK - debug/warning used |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses Optional |

**GAPS IDENTIFIED:**
1. **LOG-004 Partial**: Error logging exists but `exc_info=True` not used in error handlers
2. **CFG-003 Missing**: No field validation for max_position_percent range in type hints

---

## Dependencies
- **External:** logging, decimal, typing
- **Internal:** None

---

## Required Tests
- **tests/core/test_trading_validators.py:**
  - Test validate_position_size() passes for valid positions
  - Test validate_position_size() fails for zero/negative capital
  - Test validate_position_size() fails for zero/negative position_size
  - Test validate_position_size() fails when position exceeds capital
  - Test validate_position_size() fails when position exceeds max_percent
  - Test validate_position_size() with custom max_position_percent
  - Test validate_position_size() rejects invalid max_position_percent
  - Test validate_stop_loss() fails with None stop_loss
  - Test validate_stop_loss() fails for negative prices
  - Test validate_stop_loss() requires stop_loss below entry for long
  - Test validate_stop_loss() requires stop_loss above entry for short
  - Test validate_stop_loss() warns for wide stop-loss (>50%)
  - Test validate_stop_loss() accepts tight stop-loss
  - Test validate_trade_risk_reward() fails for None stop_loss
  - Test validate_trade_risk_reward() requires ratio >= 2.0
  - Test validate_trade_risk_reward() skips if no take_profit
  - Test validate_trade_risk_reward() with custom min_ratio
  - Test validate_trading_hours() fails outside allowed hours
  - Test validate_trading_hours() passes during allowed hours
  - Test validate_trading_hours() with custom allowed_hours
  - Test all ValueError messages are descriptive

---

## Notes
- **CRITICAL for trading safety** - All orders MUST pass validation before execution
- **Stop-loss is MANDATORY** - Trading without stop-loss is prohibited
- **Conservative defaults:**
  - Max position: 25% of capital
  - Risk-reward ratio: 2.0 minimum
  - Trading hours: 9 AM - 4 PM
- **Error messages are descriptive** - Include actual values, limits, and percentages
- **Logging** - Debug level for successes, warning for wide stop-losses
