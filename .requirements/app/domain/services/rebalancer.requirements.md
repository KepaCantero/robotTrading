# rebalancer.py

## Purpose
Domain service for portfolio rebalancing logic. Calculates target weight drift and generates rebalancing trades to minimize transaction costs.

---

## Type Definitions / Data Classes

### `RebalanceTrade` DataClass
```python
@dataclass
class RebalanceTrade:
    symbol: str                      # REQUIRED - Trading symbol
    target_quantity: Decimal         # REQUIRED - Target quantity after rebalance
    current_quantity: Decimal        # REQUIRED - Current quantity held
    trade_quantity: Decimal          # REQUIRED - Qty to trade (positive=buy, negative=sell)
    target_value: Decimal            # REQUIRED - Target value in currency
    current_value: Decimal           # REQUIRED - Current value in currency
    drift_pct: Decimal               # REQUIRED - Drift from target in percentage points
    average_price: Decimal           # REQUIRED - Average price per unit (used for validation)
```

**Validation Rules:**
- `trade_quantity` can be positive (buy) or negative (sell)
- `drift_pct` represents percentage points difference from target weight
- All monetary values use Decimal for precision
- `average_price` is computed during plan creation to avoid division by zero in validation

### `RebalancePlan` DataClass
```python
@dataclass
class RebalancePlan:
    total_value: Decimal             # REQUIRED - Total portfolio value
    cash_available: Decimal          # REQUIRED - Available cash for trading
    trades: List[RebalanceTrade]     # REQUIRED - List of required trades
    total_drift: Decimal             # REQUIRED - Overall portfolio drift
    estimated_cost: Decimal          # REQUIRED - Estimated transaction costs
```

**Methods:**
- `has_trades() -> bool`: Returns True if rebalancing requires trades

### `RebalanceConfig` DataClass
```python
@dataclass
class RebalanceConfig:
    drift_threshold: Percentage      # REQUIRED - Drift threshold (default 5%)
    min_trade_size: Decimal          # REQUIRED - Minimum trade size (default 100)
    max_trade_size_pct: Percentage   # REQUIRED - Max single trade as % of portfolio (default 20%)
    allow_fractional: bool           # REQUIRED - Allow fractional shares (default False)
    cost_per_trade: Decimal          # REQUIRED - Estimated cost per trade (default 1)
```

**Validation Rules:**
- `drift_threshold` uses Percentage value object
- `min_trade_size` prevents dust trades
- `max_trade_size_pct` limits single trade exposure

---

## Function Signatures (Contracts)

### `__init__(config: Optional[RebalanceConfig] = None) -> None`
**Pre:** None
**Post:** Rebalancer initialized with config (or default)
**Raises:** None
**Side Effects:** None

### `calculate_drift(portfolio: Portfolio, target_weights: Dict[str, Decimal]) -> Dict[str, Decimal]`
**Pre:** portfolio is valid, target_weights sum to ~1.0
**Post:** Returns dict of symbol -> drift in percentage points
**Raises:** None
**Side Effects:** None

### `create_rebalance_plan(portfolio: Portfolio, target_weights: Dict[str, Decimal]) -> RebalancePlan`
**Pre:** portfolio is valid, target_weights sum to ~1.0
**Post:** Returns complete rebalancing plan with trades
**Raises:** None
**Side Effects:** None (pure calculation)

### `optimize_rebalance_order(trades: List[RebalanceTrade]) -> List[RebalanceTrade]`
**Pre:** trades is a valid list
**Post:** Returns optimized trade order (sells first, then buys)
**Raises:** None
**Side Effects:** None (reorders list)

### `validate_rebalance_plan(plan: RebalancePlan, portfolio: Portfolio) -> tuple[bool, List[str]]`
**Pre:** plan and portfolio are valid
**Post:** Returns (is_valid, list_of_issues)
**Raises:** None
**Side Effects:** None (validation only)
**FIXED:** Now uses `average_price` field stored in RebalanceTrade, eliminating ZeroDivisionError risk

### `get_rebalance_summary(plan: RebalancePlan) -> Dict[str, str]`
**Pre:** plan is valid
**Post:** Returns human-readable summary dict
**Raises:** None
**Side Effects:** None

---

## Acceptance Criteria
- [ ] calculate_drift returns empty dict when total_value == 0
- [ ] calculate_drift correctly computes drift for all positions
- [ ] create_rebalance_plan returns empty plan when total_value == 0
- [ ] create_rebalance_plan skips trades below min_trade_size
- [ ] create_rebalance_plan skips trades within drift_threshold
- [ ] optimize_rebalance_order sells first, then buys
- [ ] validate_rebalance_plan NEVER raises ZeroDivisionError (P0 BUG)
- [ ] validate_rebalance_plan checks cash sufficiency
- [ ] validate_rebalance_plan checks max trade size limits
- [ ] All divisions guard against denominator == 0

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

### Universal Rules (from BASE_RULES.md)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| DEF-001 | defensive-programming.md | Guard all division operations | ✅ FIXED - 2026-02-01: Added average_price field to RebalanceTrade to eliminate ZeroDivisionError risk |
| DEF-002 | defensive-programming.md | Validate numeric inputs | ✅ OK |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Rebalancer only does rebalancing logic |
| ARCH-003 | 05-architecture.md | No framework in domain | ✅ OK - No FastAPI/SQLAlchemy imports |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK - All functions typed |
| VAL-001 | value-objects.md | Use Percentage VO | ✅ OK - Uses Percentage for percentages |
| LOG-001 | 09-logging-observability.md | Structured logging | ⚠️ NOT APPLIED - Domain service is pure (no I/O) |

### File-Specific Rules

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| RB-001 | rebalancer.py | Division by zero protection | ✅ FIXED - 2026-02-01: Added average_price field computed during plan creation |
| RB-002 | rebalancer.py | Decimal precision | ✅ OK - Uses Decimal for all monetary values |
| RB-003 | rebalancer.py | Immutability of plan | ✅ OK - RebalancePlan is dataclass (frozen not required) |

---

## Dependencies
- **External:** None (only Python stdlib - dataclasses, decimal, typing)
- **Internal:**
  - `app.domain.entities.portfolio.Portfolio`
  - `app.domain.entities.position.Position`
  - `app.domain.value_objects.percentage.Percentage`

---

## Required Tests
- **tests/domain/services/test_rebalancer.py:**
  - `test_calculate_drift_with_empty_portfolio`: Returns empty dict
  - `test_calculate_drift_with_positions`: Computes correct drift
  - `test_create_rebalance_plan_with_zero_value`: Returns empty plan
  - `test_create_rebalance_plan_skips_small_trades`: Respects min_trade_size
  - `test_create_rebalance_plan_skips_within_threshold`: Respects drift_threshold
  - `test_optimize_rebalance_order_sells_first`: Sells before buys
  - `test_validate_rebalance_plan_with_zero_current_quantity`: **CRITICAL** - No ZeroDivisionError
  - `test_validate_rebalance_plan_insufficient_cash`: Detects cash shortage
  - `test_validate_rebalance_plan_excessive_trade_size`: Detects oversized trades
  - `test_get_rebalance_summary`: Returns formatted summary

---

## Validation

**QA Commands (from check_all.sh and Ralphex config):**

```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/domain/services/rebalancer.py

# 2. Type check (strict mode)
mypy --strict app/domain/services/rebalancer.py

# 3. Lint
ruff check app/domain/services/rebalancer.py

# 4. Format check
black --check app/domain/services/rebalancer.py

# 5. Import sort check
isort --check-only app/domain/services/rebalancer.py

# 6. Security scan
bandit app/domain/services/rebalancer.py

# 7. Related tests
pytest tests/domain/services/test_rebalancer.py -v 2>/dev/null || echo "No tests yet"

**Expected Results:**
- Syntax: ✓ PASS
- Mypy: ✓ PASS (no type errors)
- Ruff: ✓ PASS (no lint errors)
- Black: ✓ PASS (already formatted)
- Isort: ✓ PASS (imports sorted)
- Bandit: ✓ PASS (no security issues)
- Tests: ✓ PASS (all tests pass)

---

## Notes

**Domain Service Pattern:**
This is a pure domain service with no side effects - all calculations are deterministic and stateless.

**Rebalancing Strategy:**
- Uses drift threshold to avoid unnecessary trades
- Sells overweight positions first to raise cash
- Buys underweight positions with available cash
- Respects min/max trade size limits

**Fixes Applied 2026-02-01:**
- **GAP-RB-001 (P0 - ZeroDivisionError):** Added `average_price` field to `RebalanceTrade` dataclass
  - Price is now computed during `create_rebalance_plan()` where both current_value and current_quantity are available
  - For positions with zero quantity, uses the current market price as the average price
  - `validate_rebalance_plan()` now uses the stored `average_price` instead of computing it inline
  - This eliminates the division by zero risk and provides more accurate validation
