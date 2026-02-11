# rebalance_portfolio_use_case.py

## Purpose
Rebalance Portfolio Use Case - Orchestrates portfolio rebalancing using portfolio optimization algorithms to adjust positions back to target weights.

---

## Type Definitions / Data Classes

### RebalancePortfolioUseCase
```python
class RebalancePortfolioUseCase:
    """
    Use case for rebalancing a portfolio.

    This use case orchestrates portfolio rebalancing using
    portfolio optimization algorithms.
    """
```

**Attributes:**
- `_optimizer: Optional[BasePortfolioOptimizer]` - The portfolio optimizer to use

---

## Function Signatures (Contracts)

### `RebalancePortfolioUseCase.__init__(
    optimizer: Optional[BasePortfolioOptimizer] = None,
) -> None`
**Pre:** None
**Post:** Use case initialized with optimizer (or None)
**Raises:** None
**Retry:** No
**Side Effects:** Stores optimizer reference

**State:** `_optimizer` is stored for later use

### `RebalancePortfolioUseCase.execute(
    portfolio: Portfolio,
    target_weights: Dict[str, Decimal],
    rebalance_threshold: Decimal = Decimal("0.05"),
) -> List[str]`
**Pre:** portfolio is valid; target_weights non-empty; rebalance_threshold in (0, 1)
**Post:** Returns list of rebalancing actions taken
**Raises:** None (graceful degradation)
**Retry:** No
**Side Effects:** Calls private methods for weight calculation and order generation

**Process Flow:**
1. Return ["No optimizer configured"] if no optimizer
2. Calculate current weights via `_get_current_weights()`
3. Check if rebalance needed via `_needs_rebalance()`
4. Generate rebalancing orders via `_generate_rebalance_orders()`

**Default Threshold:** 5% (0.05) - triggers rebalance when weights deviate by >5%

### `RebalancePortfolioUseCase._get_current_weights(portfolio: Portfolio) -> Dict[str, Decimal]`
**Pre:** portfolio is valid
**Post:** Returns dict of current weights by symbol
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Current Implementation:** ✅ Calculates weights by dividing position value by total portfolio value

### `RebalancePortfolioUseCase._needs_rebalance(
    current: Dict[str, Decimal],
    target: Dict[str, Decimal],
    threshold: Decimal,
) -> bool`
**Pre:** current and target are valid weight dicts; threshold in (0, 1)
**Post:** Returns True if rebalancing is needed
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Current Implementation:** ✅ Checks if `abs(current_weight - target_weight) > threshold` for any asset

### `RebalancePortfolioUseCase._generate_rebalance_orders(
    current: Dict[str, Decimal],
    target: Dict[str, Decimal],
) -> List[str]`
**Pre:** current and target are valid weight dicts
**Post:** Returns list of rebalancing actions
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Current Implementation:** ✅ Generates specific buy/sell order descriptions with weight adjustments

---

## Acceptance Criteria
- [ ] **AC-001:** RebalancePortfolioUseCase has optional optimizer dependency
- [ ] **AC-002:** execute() accepts portfolio, target_weights, threshold
- [ ] **AC-003:** execute() returns message when no optimizer
- [ ] **AC-004:** execute() calls _get_current_weights()
- [ ] **AC-005:** execute() calls _needs_rebalance()
- [ ] **AC-006:** execute() skips rebalance when not needed
- [ ] **AC-007:** execute() calls _generate_rebalance_orders()
- [ ] **AC-008:** Default rebalance_threshold is 5% (0.05)
- [ ] **AC-009:** All public methods have complete type hints

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Rebalance Portfolio Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Dependency injection | DDD (DIP) | Optimizer injected via constructor | ✅ OK - __init__() |
| Optional dependency | Clean code | Graceful degradation when None | ✅ OK - Returns message |
| Use case pattern | Clean Architecture | Application layer orchestration | ✅ OK - RebalancePortfolioUseCase |
| Single responsibility | SOLID | One use case = one responsibility | ✅ OK - Rebalancing only |
| Rebalance threshold | Portfolio management | 5% default threshold | ✅ OK - Decimal("0.05") |
| Weight calculation | Portfolio management | Current vs target weights | ✅ OK - _get_current_weights() |
| Decimal precision | BASE_RULES.md (TYP-002) | Decimal for money/weights | ✅ OK - Decimal types |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**GAPS identified:**
- ⚠️ **STUB IMPLEMENTATION:** _get_current_weights() returns empty dict
- ⚠️ **STUB IMPLEMENTATION:** _needs_rebalance() always returns True
- ⚠️ **STUB IMPLEMENTATION:** _generate_rebalance_orders() returns placeholder message
- ⚠️ **INCOMPLETE:** No actual weight calculation logic
- ⚠️ **INCOMPLETE:** No threshold comparison logic
- ⚠️ **INCOMPLETE:** No order generation logic

**NOTE:** This is a skeletal/stub implementation requiring completion for production use.

---

**Fixes Applied 2026-02-01:**
- ✅ **GAP-001 FIXED:** _get_current_weights() now calculates current portfolio weights by dividing each position value by total portfolio value
- ✅ **GAP-002 FIXED:** _needs_rebalance() now compares current vs target weights against threshold, returns True only when deviation exceeds threshold
- ✅ **GAP-003 FIXED:** _generate_rebalance_orders() now generates specific buy/sell order descriptions with weight adjustments to reach target weights
- ✅ **Import Fixed:** Changed from non-existent `BasePortfolioOptimizer` class to a `Protocol` for dependency inversion

---

## Dependencies
- **Internal:**
  - `app.domain.entities.portfolio.Portfolio`
  - `app.domain.portfolio_optimization.base_optimizer.BasePortfolioOptimizer`
- **External:** None (std lib only: decimal, typing)

---

## Required Tests
- **test_rebalance_portfolio_use_case.py:**
  - `test_init_with_optimizer()` - Stores optimizer
  - `test_init_without_optimizer()` - Stores None
  - `test_execute_without_optimizer()` - Returns "No optimizer configured"
  - `test_execute_gets_current_weights()` - Calls _get_current_weights
  - `test_execute_checks_needs_rebalance()` - Calls _needs_rebalance
  - `test_execute_no_rebalance_needed()` - Returns "No rebalance needed"
  - `test_execute_generates_orders()` - Calls _generate_rebalance_orders
  - `test_default_threshold()` - Default is 5% (0.05)
  - `test_custom_threshold()` - Uses provided threshold
  - `test_get_current_weights()` - Returns current weights (when implemented)
  - `test_needs_rebalance_within_threshold()` - Returns False
  - `test_needs_rebalance_exceeds_threshold()` - Returns True
  - `test_generate_rebalance_orders()` - Returns buy/sell actions (when implemented)

---

## Validation

**QA Commands (from check_all.sh and Ralphex config):**

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/application/use_cases/rebalance_portfolio_use_case.py

# 2. Type check (strict mode)
mypy --strict app/application/use_cases/rebalance_portfolio_use_case.py

# 3. Lint
ruff check app/application/use_cases/rebalance_portfolio_use_case.py

# 4. Format check
black --check app/application/use_cases/rebalance_portfolio_use_case.py

# 5. Import sort check
isort --check-only app/application/use_cases/rebalance_portfolio_use_case.py

# 6. Security scan
bandit app/application/use_cases/rebalance_portfolio_use_case.py

# 7. Related tests
pytest tests/application/use_cases/test_rebalance_portfolio_use_case.py -v 2>/dev/null || echo "No tests yet"
```

**Expected Results:**
- Syntax: PASS
- Mypy: PASS (no type errors)
- Ruff: PASS (no lint errors)
- Black: PASS (already formatted)
- Isort: PASS (imports sorted)
- Bandit: PASS (no security issues)
- Tests: PASS (all tests pass)

---

## Notes
- **Critical:** This is a STUB implementation - not production-ready
- **State:** Skeletal use case with placeholder logic
- **Missing Implementation:**
  - `_get_current_weights()`: Should calculate current portfolio weights
  - `_needs_rebalance()`: Should compare current vs target weights against threshold
  - `_generate_rebalance_orders()`: Should generate buy/sell orders to achieve target weights
- **Current Behavior:**
  - execute() returns placeholder messages
  - Always triggers rebalance (returns True from _needs_rebalance)
  - No actual weight calculation or order generation
- **Production Requirements:**
  - Implement `_get_current_weights()`: Calculate from portfolio positions and total value
  - Implement `_needs_rebalance()`: Check `abs(current - target) > threshold` for all assets
  - Implement `_generate_rebalance_orders()`: Generate specific buy/sell orders
  - Consider transaction costs (don't rebalance if costs exceed drift benefit)
  - Add logging for rebalancing decisions
  - Validate target weights sum to 1.0 (100%)
  - Handle edge cases: missing assets, cash drag, fractional shares
- **Rebalancing Best Practices:**
  - 5% threshold is common (balances tracking error vs transaction costs)
  - Consider time-based rebalancing (monthly/quarterly) as alternative
  - Consider tolerance bands (e.g., rebalance when weight > target × 1.05)
- **Use Case Pattern:** Application layer orchestrates domain logic
- **Dependency Injection:** Optimizer is injected (Dependency Inversion Principle)

---

**File Reference:** `app/application/use_cases/rebalance_portfolio_use_case.py`
**Last Audited:** 2026-02-01
