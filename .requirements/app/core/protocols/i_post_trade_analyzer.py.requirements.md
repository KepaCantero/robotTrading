# i_post_trade_analyzer.py

## Purpose
Protocol interface for post-trade analysis in trading system. Defines contract for trailing stops (R11), partial take profits (R12), pyramiding (R13), position metrics calculation, and exit signal generation.

---

## Type Definitions / Data Classes

### IPostTradeAnalyzer (Protocol)
```python
class IPostTradeAnalyzer(Protocol):
    async def update_trailing_stop(self, position_id: str, current_price: Decimal) -> Optional[Decimal]:
        """R11: Trailing Stop Dinámico"""

    async def check_partial_take_profit(self, position_id: str, current_pnl: Decimal) -> bool:
        """R12: Take Profit Parcial"""

    async def evaluate_pyramiding(self, position_id: str, unrealized_pnl: Decimal) -> bool:
        """R13: Pyramiding (solo ganadores)"""

    async def calculate_position_metrics(self, position_id: str) -> dict:
        """Calcular métricas de posición"""

    async def generate_exit_signal(self, position_id: str) -> Optional["TradeSignal"]:
        """Generar señal de salida"""
```

**Contract Rules:**
- All methods are async (use async def)
- All methods use `...` ellipsis for Protocol signature definition
- Return types are specified (Optional[Decimal], bool, dict, Optional["TradeSignal"])
- 5 methods maximum (as noted in class docstring)
- R11, R12, R13 compliance for trailing stop, partial TP, pyramiding

---

## Function Signatures (Contracts)

### `async update_trailing_stop(position_id: str, current_price: Decimal) -> Optional[Decimal]`
**Pre:** position_id must be valid, current_price must be positive
**Post:** Returns new trailing stop price if updated, None if no change
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient database failures
**Side Effects:** Updates trailing stop value in storage

### `async check_partial_take_profit(position_id: str, current_pnl: Decimal) -> bool`
**Pre:** position_id must be valid, current_pnl must be calculated
**Post:** Returns True if partial take profit should be triggered, False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient calculation failures
**Side Effects:** May trigger partial position close

### `async evaluate_pyramiding(position_id: str, unrealized_pnl: Decimal) -> bool`
**Pre:** position_id must be valid, unrealized_pnl must be positive (winning position)
**Post:** Returns True if pyramiding allowed (only winners), False otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient calculation failures
**Side Effects:** None (read-only evaluation)

### `async calculate_position_metrics(position_id: str) -> dict`
**Pre:** position_id must be valid with trade history
**Post:** Returns dictionary with metrics (entry price, current PnL, duration, etc.)
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient database failures
**Side Effects:** None (read-only calculation)

### `async generate_exit_signal(position_id: str) -> Optional["TradeSignal"]`
**Pre:** position_id must be valid with open position
**Post:** Returns TradeSignal if exit conditions met, None otherwise
**Raises:** NotImplementedError if not implemented
**Retry:** Yes - May retry on transient calculation failures
**Side Effects:** May trigger position close via signal generation

---

## Acceptance Criteria
- [ ] All 5 methods are defined as async def
- [ ] All methods use `...` ellipsis for Protocol body
- [ ] Return types are explicitly specified
- [ ] Methods align with R11, R12, R13 requirements
- [ ] pyramiding only allows winning positions (positive unrealized_pnl)
- [ ] trailing_stop uses Optional[Decimal] return type correctly
- [ ] Implementations log state changes for audit trail

---

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-11T16:00:00Z |
| **Auditor** | Ralph - Requirement Checker |
| **GAPs Found** | 0 P0, 0 P1, 0 P2, 1 P3 |
| **Notes** | Well-defined Protocol interface for post-trade analysis. R11/R12/R13 compliance documented. |

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-004 | BASE_RULES | Audit trail - log all trade decisions | ✅ OK - calculate_position_metrics for audit |
| SOL-004 | BASE_RULES | Interface Segregation | ✅ OK - Protocol has focused methods |
| SOL-005 | BASE_RULES | Dependency Inversion | ✅ OK - Protocol for abstraction |
| ASYNC-001 | BASE_RULES | Use async def | ✅ OK - All methods use async def |
| TYP-001 | BASE_RULES | 100% type coverage | ⚠️ P3 - Add type hints for dict return |
| TYP-006 | BASE_RULES | Use Protocol for duck typing | ✅ OK - Uses Protocol instead of ABC |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Method names clearly describe purpose |

---

## Dependencies
- **External:** typing (Protocol, Optional)
- **Internal:** decimal (Decimal)

---

## Required Tests
- **tests/core/protocols/test_i_post_trade_analyzer.py:**
  - Test Protocol can be subclassed by concrete implementation
  - Test all 5 methods are required (NotImplementedError raised)
  - Test async methods can be called on mock implementation
  - Test R11 trailing stop updates correctly
  - Test R12 partial take profit triggers at threshold
  - Test R13 pyramiding only for winning positions
  - Test Optional[Decimal] return handling

---

## Notes

**P3 - Type hints for dict return:**
```python
# CURRENT:
async def calculate_position_metrics(self, position_id: str) -> dict:

# SUGGESTED:
from typing import Any
async def calculate_position_metrics(self, position_id: str) -> dict[str, Any]:
```

**P3 - English/Spanish inconsistency:** Docstrings are in Spanish ("Análisis post-trade") but file-level comments use English. Consider standardizing to English for consistency with rest of codebase.

**Trading Context:** This Protocol implements R11 (Trailing Stop Dinámico), R12 (Take Profit Parcial), and R13 (Pyramiding solo ganadores) from SERVICE_REQUIREMENTS.md. These are advanced position management techniques for maximizing profits while protecting against losses.
