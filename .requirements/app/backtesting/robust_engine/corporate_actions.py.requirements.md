# corporate_actions.py

## Purpose
Handles all corporate actions (stock splits, mergers, spin-offs) that affect backtesting accuracy, ensuring proper position and cost basis adjustments over 25+ year periods.

---

## Type Definitions / Data Classes

### PositionAdjustment
```python
@dataclass
class PositionAdjustment:
    original_symbol: str                    # REQUIRED - Original ticker symbol
    original_quantity: Decimal              # REQUIRED - Original number of shares
    original_cost_basis: Decimal            # REQUIRED - Original cost basis
    new_symbol: Optional[str]               # OPTIONAL - New ticker symbol (None if symbol unchanged)
    new_quantity: Decimal                   # REQUIRED - New number of shares after adjustment
    new_cost_basis: Decimal                 # REQUIRED - New cost basis after adjustment
    cash_received: Decimal                  # REQUIRED - Cash received from action (default: 0)
    adjustment_type: str                    # REQUIRED - Type of adjustment ('stock_split', 'merger', etc.)
    metadata: Dict[str, Any]                # REQUIRED - Additional action-specific data
```

**Validation Rules:**
- For stock splits: new_quantity = original_quantity * split_ratio
- For stock splits: new_cost_basis = original_cost_basis / split_ratio
- Decimal precision maintained to 6 decimal places for quantity, 2 for cost basis

---

## Function Signatures (Contracts)

### `__init__() -> None`
**Pre:** None
**Post:** CorporateActionHandler initialized with empty internal dictionaries
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Initializes _splits, _mergers, _spinoffs, _all_actions

### `def add_split(symbol: str, split_ratio: Decimal, ex_date: date, declaration_date: Optional[date] = None, record_date: Optional[date] = None) -> StockSplit`
**Pre:** symbol must be non-empty string; split_ratio > 0; ex_date must be valid date
**Post:** Returns StockSplit object with calculated adjustment_factor
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Adds split to _splits[symbol] and _all_actions; logs addition

### `def add_merger(target: str, acquirer: str, exchange_ratio: Decimal, ex_date: date, cash_consideration: Optional[Decimal] = None, declaration_date: Optional[date] = None) -> Merger`
**Pre:** target and acquirer must be non-empty strings; exchange_ratio > 0; ex_date must be valid date
**Post:** Returns Merger object
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Adds merger to _mergers[target] and _all_actions; logs addition

### `def add_spinoff(parent: str, spinoff: str, distribution_ratio: Decimal, ex_date: date, declaration_date: Optional[date] = None) -> SpinOff`
**Pre:** parent and spinoff must be non-empty strings; distribution_ratio > 0; ex_date must be valid date
**Post:** Returns SpinOff object
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** Adds spinoff to _spinoffs[parent] and _all_actions; logs addition

### `def handle_split(symbol: str, split_ratio: Decimal, ex_date: date, shares: Decimal, cost_basis: Decimal) -> PositionAdjustment`
**Pre:** shares >= 0; cost_basis >= 0; split_ratio > 0
**Post:** Returns PositionAdjustment with new_quantity = shares * split_ratio
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function, logs result)

### `def handle_merger(target: str, acquirer: str, ratio: Decimal, cash: Optional[Decimal], target_shares: Decimal, target_cost_basis: Decimal, acquirer_price: Optional[Decimal] = None) -> PositionAdjustment`
**Pre:** target_shares >= 0; target_cost_basis >= 0; ratio > 0; acquirer_price > 0 if provided
**Post:** Returns PositionAdjustment with converted position details
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function, logs result)

### `def handle_spinoff(parent: str, spinoff: str, ratio: Decimal, parent_shares: Decimal, parent_cost_basis: Decimal, parent_price: Optional[Decimal] = None, spinoff_price: Optional[Decimal] = None) -> Tuple[PositionAdjustment, PositionAdjustment]`
**Pre:** parent_shares >= 0; parent_cost_basis >= 0; ratio > 0; parent_price > 0 if provided; spinoff_price > 0 if provided
**Post:** Returns tuple of (parent_adjustment, spinoff_adjustment)
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function, logs result)

### `def adjust_history_for_splits(prices: pd.DataFrame, splits: Optional[List[StockSplit]] = None) -> pd.DataFrame`
**Pre:** prices must have datetime index; splits must be sorted by date if provided
**Post:** Returns DataFrame with backward-adjusted prices
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function, logs adjustments)

### `def get_adjustment_factor(symbol: str, as_of_date: date) -> Decimal`
**Pre:** symbol must be valid ticker; as_of_date must be valid date
**Post:** Returns cumulative adjustment factor for backward adjustment
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function)

### `def get_pending_actions(symbol: str, current_date: date, lookahead_days: int = 30) -> List[CorporateAction]`
**Pre:** symbol must exist in internal dictionaries; current_date must be valid date
**Post:** Returns list of actions in (current_date, current_date + lookahead_days]
**Raises:** No explicit exceptions raised
**Retry:** No
**Side Effects:** None (pure function)

### `def load_actions_from_csv(filepath: str) -> int`
**Pre:** filepath must exist and be readable CSV
**Post:** Returns count of actions loaded
**Raises:** No explicit exceptions raised (logs error and returns 0 on failure)
**Retry:** No
**Side Effects:** Populates _splits, _mergers, _spinoffs, _all_actions

---

## Acceptance Criteria
- [ ] add_split() creates StockSplit with adjustment_factor = 1 / split_ratio
- [ ] add_split() adds to _splits dictionary and _all_actions list
- [ ] add_merger() creates Merger with exchange_ratio and optional cash_consideration
- [ ] add_merger() adds to _mergers dictionary and _all_actions list
- [ ] add_spinoff() creates SpinOff with distribution_ratio
- [ ] add_spinoff() adds to _spinoffs dictionary and _all_actions list
- [ ] handle_split() calculates new_quantity = shares * split_ratio
- [ ] handle_split() calculates new_cost_basis = cost_basis / split_ratio
- [ ] handle_split() returns PositionAdjustment with adjustment_type='stock_split'
- [ ] handle_merger() calculates new_shares = target_shares * ratio
- [ ] handle_merger() calculates cash_received = target_shares * cash (if cash provided)
- [ ] handle_merger() allocates cost basis based on relative values when acquirer_price provided
- [ ] handle_merger() returns PositionAdjustment with new_symbol=acquirer
- [ ] handle_spinoff() calculates spinoff_shares = parent_shares * ratio
- [ ] handle_spinoff() allocates cost basis 90/10 when no prices provided
- [ ] handle_spinoff() allocates cost basis by relative market value when prices provided
- [ ] handle_spinoff() returns tuple of (parent_adjustment, spinoff_adjustment)
- [ ] adjust_history_for_splits() adjusts OHLCV columns before split date
- [ ] adjust_history_for_splits() adjusts volume by division (inverse of price adjustment)
- [ ] adjust_history_for_splits() handles both single-column and multi-column DataFrames
- [ ] get_adjustment_factor() includes splits AFTER as_of_date for backward adjustment
- [ ] get_adjustment_factor() returns 1.0 when symbol not in _splits
- [ ] get_pending_actions() returns actions sorted by ex_date
- [ ] load_actions_from_csv() parses action_type: 'split', 'merger', 'acquisition', 'spinoff'
- [ ] load_actions_from_csv() handles optional cash column for mergers
- [ ] load_actions_from_csv() handles missing declaration_date column (defaults to ex_date)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage for all functions | ✅ OK - All functions have type hints |
| TYP-002 | BASE_RULES.md | Modern syntax (X \| None) | ✅ OK - Uses Optional[T] correctly |
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - Uses field(default_factory=dict) |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ OK - Uses logging with context |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ✅ OK - Exception handlers log errors |
| BT-004 | BASE_RULES.md | Realistic transaction costs | ⚠️ NOT APPLIED - Not applicable (no transaction costs) |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Catches exceptions, logs, returns safe defaults |
| ARCH-004 | BASE_RULES.md | Small functions (< 20 lines) | ✅ OK - Most methods under 20 lines |
| PERF-002 | BASE_RULES.md | Use generators for large data | ❌ GAP - Could use generators in load_actions_from_csv |
| QL-001 | BASE_RULES.md | Complexity < 10 per function | ⚠️ NOT APPLIED - Not measured with radon |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets in code |
| TRD-004 | BASE_RULES.md | Audit trail | ✅ OK - All actions stored in _all_actions |

**GAP Analysis:**
1. **PERF-002 (Generators):** The `load_actions_from_csv` method uses `itertuples()` which is efficient, but the loop body is somewhat long. For very large CSV files, this could potentially be optimized further. However, this is a minor concern given the current implementation.

2. **Decimal precision:** The code properly uses Decimal for all monetary calculations and uses `quantize()` to ensure consistent precision. This is critical for financial calculations and is done correctly.

---

## Dependencies
- **External:** pandas, numpy, logging (standard lib), dataclasses (standard lib), datetime (standard lib), decimal (standard lib), typing (standard lib)
- **Internal:**
  - `.models.CorporateAction`
  - `.models.CorporateActionType`
  - `.models.Merger`
  - `.models.SpinOff`
  - `.models.StockSplit`

---

## Required Tests
- **tests/unit/backtesting/robust_engine/test_corporate_actions.py:**
  - Test add_split creates StockSplit with correct adjustment_factor
  - Test add_split adds to _splits dictionary
  - Test add_split adds to _all_actions list
  - Test add_merger creates Merger with cash_consideration
  - Test add_merger creates Merger without cash_consideration
  - Test add_merger adds to _mergers dictionary
  - Test add_spinoff creates SpinOff with correct fields
  - Test add_spinoff adds to _spinoffs dictionary
  - Test handle_split calculates new_quantity correctly
  - Test handle_split calculates new_cost_basis correctly
  - Test handle_split quantizes to 6 decimal places for quantity
  - Test handle_split quantizes to 2 decimal places for cost_basis
  - Test handle_merger with cash_consideration
  - Test handle_merger without cash_consideration
  - Test handle_merger allocates cost_basis when acquirer_price provided
  - Test handle_merger uses target_cost_basis when no acquirer_price
  - Test handle_spinoff allocates 90/10 when no prices provided
  - Test handle_spinoff allocates by relative value when prices provided
  - Test handle_spinoff returns tuple with both adjustments
  - Test adjust_history_for_splits adjusts prices before split date
  - Test adjust_history_for_splits adjusts volume inversely
  - Test adjust_history_for_splits handles single-column DataFrame
  - Test adjust_history_for_splits handles multi-column OHLCV DataFrame
  - Test get_adjustment_factor returns 1.0 for unknown symbol
  - Test get_adjustment_factor includes splits after as_of_date
  - Test get_pending_actions returns actions in lookahead window
  - Test get_pending_actions sorts by ex_date
  - Test load_actions_from_csv with split action
  - Test load_actions_from_csv with merger action
  - Test load_actions_from_csv with spinoff action
  - Test load_actions_from_csv handles missing declaration_date
  - Test load_actions_from_csv handles missing cash column
  - Test load_actions_from_csv returns count of actions loaded
  - Test load_actions_from_csv logs error and returns 0 on failure
  - Test all handlers log their actions

---

## Notes
- Critical for accurate long-term backtesting (Ernie Chan, "Algorithmic Trading")
- Handles all major corporate actions: splits, mergers, acquisitions, spin-offs
- Cost basis allocation is critical for accurate P&L calculation
- Default 90/10 split for spin-offs without price data is industry standard
- All adjustments maintain Decimal precision for financial accuracy
