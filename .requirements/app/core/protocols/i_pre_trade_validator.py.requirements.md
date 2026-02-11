# i_pre_trade_validator.py

## Purpose
Protocol interface for pre-trade validation in trading system. Defines contract for validating Kelly criterion (R1), drawdown limits (R2), risk-reward ratios (R4), stop loss requirements (R3), and market hours (R9).

---

## Type Definitions / Data Classes

### IPreTradeValidator (Protocol)
```python
class IPreTradeValidator(Protocol):
    async def validate_kelly(self, capital: Decimal, order_value: Decimal) -> bool:
        """R1: Kelly Criterion + 2% max"""

    async def validate_drawdown(self) -> bool:
        """R2: Drawdown 15% stop"""

    async def validate_rr_ratio(self, entry: Decimal, target: Decimal, stop: Decimal) -> bool:
        """R4: R:R 2:1 minimum"""

    async def validate_stop_loss(self, stop_loss: Optional[Decimal]) -> bool:
        """R3: Stop Loss SIEMPRE requerido"""

    async def validate_market_hours(self) -> bool:
        """R9: Evitar horarios de baja liquidez"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (bool, Optional[Decimal] param)
- 5 methods maximum (as noted in class docstring)
- R1, R2, R3, R4, R9 compliance for trading rules

---

## Function Signatures (Contracts)

### `async validate_kelly(capital: Decimal, order_value: Decimal) -> bool`
**Pre:** capital must be positive, order_value must be positive
**Post:** Returns True if position size <= 2% of capital (R1 compliance), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure validation function)

### `async validate_drawdown() -> bool`
**Pre:** Portfolio drawdown tracking must be initialized
**Post:** Returns True if drawdown < 15% (R2 compliance), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (read-only check)

### `async validate_rr_ratio(entry: Decimal, target: Decimal, stop: Decimal) -> bool`
**Pre:** entry, target, stop must be positive Decimals
**Post:** Returns True if risk-reward ratio >= 2:1 (R4 compliance), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure validation function)
**Calculation:** RR = abs(target - entry) / abs(entry - stop)

### `async validate_stop_loss(stop_loss: Optional[Decimal]) -> bool`
**Pre:** stop_loss may be None or Decimal
**Post:** Returns True if stop_loss is set (not None), False if missing (R3 compliance)
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (pure validation function)

### `async validate_market_hours() -> bool`
**Pre:** Market schedule data must be available
**Post:** Returns True if within trading hours (R9: avoid low liquidity), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** No
**Side Effects:** None (read-only check)

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified (bool)
- [ ] Methods align with R1, R2, R3, R4, R9 requirements
- [ ] validate_kelly enforces 2% maximum position size
- [ ] validate_drawdown enforces 15% drawdown limit
- [ ] validate_rr_ratio enforces 2:1 minimum risk-reward
- [ ] validate_stop_loss requires stop loss (not None)
- [ ] validate_market_hours checks for low liquidity periods

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 1 P3 |
| **Notes** | Excellent Protocol interface for pre-trade validation. All critical trading rules (R1-R4, R9) covered. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| R1 | SERVICE_REQUIREMENTS | Kelly Criterion + 2% max position size | ✅ OK - validate_kelly method |
| R2 | SERVICE_REQUIREMENTS | Drawdown 15% stop trading | ✅ OK - validate_drawdown method |
| R3 | SERVICE_REQUIREMENTS | Stop Loss SIEMPRE requerido | ✅ OK - validate_stop_loss method |
| R4 | SERVICE_REQUIREMENTS | Risk-Reward 2:1 minimum | ✅ OK - validate_rr_ratio method |
| R9 | SERVICE_REQUIREMENTS | Avoid low liquidity hours | ✅ OK - validate_market_hours method |
| TRD-002 | BASE_RULES | Validate orders before execution | ✅ OK - Protocol provides pre-trade validation |
| TRD-003 | BASE_RULES | Position limits | ✅ OK - Kelly (2%) and RR (2:1) enforced |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused validation methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All types specified |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |

---

## Dependencies
- **External:** typing (Protocol, Optional)
- **Internal:** decimal (Decimal)

---

## Required Tests
- **tests/core/protocols/test_i_pre_trade_validator.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test R1: validate_kelly rejects >2% position
  - Test R2: validate_drawdown rejects >=15% drawdown
  - Test R4: validate_rr_ratio rejects <2:1 ratio
  - Test R3: validate_stop_loss rejects None
  - Test R9: validate_market_hours checks trading hours

---

## Notes

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Validaciones pre-trade") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**Trading Context:** This Protocol implements critical pre-trade validation rules R1-R4 and R9 from SERVICE_REQUIREMENTS.md:
- **R1**: Kelly Criterion limits position size to 2% of available capital
- **R2**: Stop trading when drawdown reaches 15%
- **R3**: Every order MUST have a stop loss
- **R4**: Minimum risk-reward ratio of 2:1 required
- **R9**: Avoid trading during low liquidity hours

These rules prevent overtrading, control risk, and ensure positive expected value on all trades.
