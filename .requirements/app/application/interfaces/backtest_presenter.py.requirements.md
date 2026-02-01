# backtest_presenter.py

## Purpose
Backtest Presenter Interface - Humble Object pattern for UI layer, defines contract for presenting backtest results to UI with simple, testable presenters.

---

## Type Definitions / Data Classes

### BacktestPresenter Interface (ABC)
```python
class BacktestPresenter(ABC):
    """Presenter interface for backtest results (Humble Object pattern)."""
```

**Pattern:** Humble Object (keeps presenter logic simple, delegates to use cases)

---

## Function Signatures (Abstract Methods)

### `@abstractmethod present_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is valid string
**Post:** Returns presentation-ready dict or None
**Raises:** No (abstract method)
**Retry:** No
**Side Effects:** None (implementations delegate to use cases)

### `@abstractmethod present_backtest_list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]`
**Pre:** limit > 0, offset >= 0
**Post:** Returns list of presentation-ready dicts
**Raises:** No (abstract method)
**Retry:** No
**Side Effects:** None (implementations delegate to use cases)

**Pagination:** limit = max results, offset = skip count

### `@abstractmethod present_performance_summary(self, backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is valid string
**Post:** Returns presentation-ready summary or None
**Raises:** No (abstract method)
**Retry:** No
**Side Effects:** None (implementations delegate to use cases)

### `@abstractmethod present_comparison(self, backtest_ids: List[str]) -> Optional[Dict[str, Any]]`
**Pre:** backtest_ids is non-empty list
**Post:** Returns comparison dict or None
**Raises:** No (abstract method)
**Retry:** No
**Side Effects:** None (implementations delegate to use cases)

### `@abstractmethod present_error(self, error_message: str) -> Dict[str, Any]`
**Pre:** error_message is non-empty string
**Post:** Returns error dict
**Raises:** No (abstract method)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Interface uses ABC and @abstractmethod
- [ ] All methods return Dict[str, Any] or List[Dict[str, Any]]
- [ ] present_backtest_result returns None if not found
- [ ] present_backtest_list supports pagination (limit, offset)
- [ ] present_performance_summary returns summary metrics
- [ ] present_comparison handles multiple backtests
- [ ] present_error always returns dict (never None)
- [ ] All methods are abstract (no implementation)
- [ ] Follows Humble Object pattern (simple, testable)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Humble Object | BASE_RULES.md | Simple, delegates to use cases | ✅ OK |
| ABC Pattern | BASE_RULES.md | Use ABC and @abstractmethod | ✅ OK |
| Type Hints | BASE_RULES.md | All methods typed | ✅ OK |
| No Implementation | BASE_RULES.md | Abstract methods only | ✅ OK |

---

## Dependencies
- **External:** abc, typing
- **Internal:** None (pure interface)

---

## Required Tests
- **test_backtest_presenter.py:**
  - Test interface is abstract (cannot instantiate)
  - Test all methods are abstract
  - Test method signatures match contract
  - Test implementations will be tested separately

---

## Notes
- CRITICAL: This is Clean Architecture interface
- Humble Object pattern keeps presenters simple
- All business logic delegated to use cases
- Presenters format data for UI layer
- Implementations will be in application layer
