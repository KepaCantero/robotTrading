# backtest_presenter.py

## Purpose
Backtest Presenter Interface - Humble Object pattern for UI layer. Defines the contract for presenting backtest results to the UI, keeping presenter logic simple and testable by delegating business logic to use cases.

---

## Type Definitions / Data Classes

### BacktestPresenter (ABC)
```python
class BacktestPresenter(ABC):
    """
    Presenter interface for backtest results (Humble Object pattern).

    This interface follows the Humble Object pattern by keeping the
    presenter logic simple and testable, delegating complex business
    logic to use cases.
    """
```

**Pattern:** Humble Object Pattern
**Purpose:** Separate UI concerns from business logic

---

## Function Signatures (Contracts)

### `BacktestPresenter.present_backtest_result(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns presentation-ready dictionary or None if not found
**Raises:** None (implementations should handle errors gracefully)
**Retry:** No
**Side Effects:** None (pure presentation)

**Implementation Notes:**
- Should delegate to use case for business logic
- Format data for UI consumption
- Return None if backtest not found

### `BacktestPresenter.present_backtest_list(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]`
**Pre:** limit >= 0; offset >= 0
**Post:** Returns list of presentation-ready dictionaries
**Raises:** None (implementations should handle errors gracefully)
**Retry:** No
**Side Effects:** None (pure presentation)

**Default Parameters:**
- limit = 20 (maximum results)
- offset = 0 (no skip)

**Implementation Notes:**
- Should delegate to use case for business logic
- Apply pagination (limit/offset)
- Format data for UI consumption

### `BacktestPresenter.present_performance_summary(backtest_id: str) -> Optional[Dict[str, Any]]`
**Pre:** backtest_id is non-empty string
**Post:** Returns presentation-ready summary or None if not found
**Raises:** None (implementations should handle errors gracefully)
**Retry:** No
**Side Effects:** None (pure presentation)

**Implementation Notes:**
- Should delegate to use case for business logic
- Include key metrics: returns, Sharpe, drawdown, etc.
- Return None if backtest not found

### `BacktestPresenter.present_comparison(backtest_ids: List[str]) -> Optional[Dict[str, Any]]`
**Pre:** backtest_ids is non-empty list of valid IDs
**Post:** Returns presentation-ready comparison or None if invalid
**Raises:** None (implementations should handle errors gracefully)
**Retry:** No
**Side Effects:** None (pure presentation)

**Implementation Notes:**
- Should delegate to use case for business logic
- Compare multiple backtests side-by-side
- Return None if comparison cannot be made

### `BacktestPresenter.present_error(error_message: str) -> Dict[str, Any]`
**Pre:** error_message is non-empty string
**Post:** Returns presentation-ready error dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure presentation)

**Implementation Notes:**
- Format error for UI display
- Include error context if available
- Never returns None (always returns dict)

---

## Acceptance Criteria
- [ ] **AC-001:** BacktestPresenter is an abstract base class (ABC)
- [ ] **AC-002:** present_backtest_result() is abstract method
- [ ] **AC-003:** present_backtest_list() is abstract method
- [ ] **AC-004:** present_performance_summary() is abstract method
- [ ] **AC-005:** present_comparison() is abstract method
- [ ] **AC-006:** present_error() is abstract method
- [ ] **AC-007:** All methods have @abstractmethod decorator
- [ ] **AC-008:** All methods have complete type hints
- [ ] **AC-009:** present_backtest_list() has default limit=20, offset=0

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Backtest Presenter Interface):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Interface pattern | Clean Architecture | ABC for presenter contract | ✅ OK - BacktestPresenter(ABC) |
| Humble Object pattern | Clean Architecture | Thin presenters, delegate to use cases | ✅ OK - Docstring |
| Abstract methods | Python ABC | @abstractmethod decorator | ✅ OK - All methods |
| Dependency inversion | SOLID | Depend on abstractions | ✅ OK - Interface |
| Presentation layer separation | Clean Architecture | No business logic in presenter | ✅ OK - Interface contract |
| Return type consistency | Clean code | Dict for UI consumption | ✅ OK - Dict[str, Any] |
| Optional returns | Clean code | None when not found | ✅ OK - Optional[Dict] |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All methods documented | ✅ OK - Complete |

**NOTE:** This is an interface definition - implementations should follow the contract.

---

## Dependencies
- **External:** None (std lib only: abc, typing)
- **Internal:** None (application interface layer)

---

## Required Tests
- **test_backtest_presenter_interface.py:**
  - `test_backtest_presenter_is_abc()` - Cannot instantiate ABC
  - `test_present_backtest_result_is_abstract()` - Has @abstractmethod
  - `test_present_backtest_list_is_abstract()` - Has @abstractmethod
  - `test_present_performance_summary_is_abstract()` - Has @abstractmethod
  - `test_present_comparison_is_abstract()` - Has @abstractmethod
  - `test_present_error_is_abstract()` - Has @abstractmethod
  - `test_present_backtest_list_defaults()` - limit=20, offset=0

**Implementation Tests (for concrete implementations):**
  - `test_present_backtest_result_returns_dict()` - Returns Dict[str, Any]
  - `test_present_backtest_result_not_found()` - Returns None
  - `test_present_backtest_list_applies_limit()` - Respects limit param
  - `test_present_backtest_list_applies_offset()` - Respects offset param
  - `test_present_performance_summary_returns_metrics()` - Returns summary dict
  - `test_present_comparison_multiple_backtests()` - Compares multiple
  - `test_present_error_returns_dict()` - Always returns dict

---

## Notes
- **Critical:** This is an INTERFACE - concrete implementations must be provided
- **Humble Object Pattern:**
  - Keep presenters thin and simple
  - Delegate all business logic to use cases
  - Presenters only format data for UI
  - Makes UI layer testable
- **Interface Contract:**
  - Implementations MUST provide all 5 methods
  - Methods MUST handle errors gracefully (return None or error dict)
  - Methods MUST NOT contain business logic
- **Clean Architecture:**
  - Application layer defines interfaces for presentation
  - Presentation layer (FastAPI, CLI) implements interfaces
  - Domain layer knows nothing about presenters
- **Dependency Inversion Principle:**
  - Use cases depend on this abstraction
  - UI layer depends on this abstraction
  - Both depend on the interface, not concretions
- **Production Rule:** All presenter implementations should be trivial (<50 lines)

---

**File Reference:** `app/application/interfaces/backtest_presenter.py`
**Last Audited:** 2026-02-01
