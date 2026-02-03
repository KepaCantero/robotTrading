# robust_engine/models.py

## Purpose
Data models for the Robust Backtesting Engine. Defines all data structures for corporate actions, dividend tracking, survivorship bias correction, checkpointing, and progress tracking.

---

## Type Definitions / Data Classes

### CorporateActionType (Enum)
```python
class CorporateActionType(str, Enum):
    STOCK_SPLIT = "stock_split"           # Stock split events
    REVERSE_SPLIT = "reverse_split"       # Reverse stock splits
    MERGER = "merger"                     # Merger events
    ACQUISITION = "acquisition"           # Acquisition events
    SPINOFF = "spinoff"                   # Spin-off events
    DIVIDEND = "dividend"                 # Regular dividends
    SPECIAL_DIVIDEND = "special_dividend" # Special dividends
    RIGHTS_OFFERING = "rights_offering"   # Rights offerings
    TENDER_OFFER = "tender_offer"         # Tender offers
    DELISTING = "delisting"               # Delisting events
```

### DelistingReason (Enum)
```python
class DelistingReason(str, Enum):
    BANKRUPTCY = "bankruptcy"       # Company bankruptcy
    ACQUISITION = "acquisition"     # Acquired by another company
    MERGER = "merger"               # Merged with another company
    DELISTING = "delisting"         # Voluntary delisting
    PRIVATE_GOING = "private_going" # Went private
    REGULATORY = "regulatory"       # Regulatory delisting
    LIQUIDATION = "liquidation"     # Company liquidation
```

### CorporateAction (DataClass)
```python
@dataclass
class CorporateAction:
    action_id: UUID                           # REQUIRED - Unique identifier
    symbol: str                               # REQUIRED - Ticker symbol
    action_type: CorporateActionType          # REQUIRED - Type of action
    declaration_date: date                    # REQUIRED - Announcement date
    ex_date: date                             # REQUIRED - Ex-date
    record_date: Optional[date]               # OPTIONAL - Record date
    payment_date: Optional[date]              # OPTIONAL - Payment date
    description: str                          # REQUIRED - Human-readable description
    metadata: Dict[str, Any]                  # OPTIONAL - Additional data
```

**Validation Rules:**
- `action_id` defaults to UUID4
- `symbol` cannot be empty for valid actions
- `ex_date` must be on or after `declaration_date`
- `record_date` typically between declaration and ex_date

### StockSplit (DataClass)
```python
@dataclass
class StockSplit(CorporateAction):
    split_ratio: Decimal          # REQUIRED - Ratio as new_shares:old_shares (e.g., 2:1 = 2.0)
    adjustment_factor: Decimal    # REQUIRED - Factor to multiply historical prices
```

**Validation Rules:**
- `split_ratio` must be > 0
- `adjustment_factor` calculated as 1/split_ratio in `__post_init__`
- Sets `action_type` to `STOCK_SPLIT` automatically

### Merger (DataClass)
```python
@dataclass
class Merger(CorporateAction):
    target_symbol: str           # REQUIRED - Company being acquired
    acquirer_symbol: str         # REQUIRED - Acquiring company
    exchange_ratio: Decimal      # REQUIRED - Shares of acquirer per target share
    cash_consideration: Optional[Decimal]  # OPTIONAL - Cash amount per share
```

**Validation Rules:**
- `exchange_ratio` must be > 0
- Both symbols cannot be empty
- Sets `action_type` to `MERGER` automatically

### SpinOff (DataClass)
```python
@dataclass
class SpinOff(CorporateAction):
    parent_symbol: str          # REQUIRED - Original company symbol
    spinoff_symbol: str         # REQUIRED - New company symbol
    distribution_ratio: Decimal # REQUIRED - Ratio of spinoff shares per parent share
```

**Validation Rules:**
- `distribution_ratio` must be > 0
- Both symbols cannot be empty

### DividendPayment (DataClass)
```python
@dataclass
class DividendPayment(CorporateAction):
    amount: Decimal        # REQUIRED - Dividend per share
    frequency: str         # REQUIRED - Payment frequency
    qualified: bool        # REQUIRED - Tax qualification status
```

**Validation Rules:**
- `amount` must be >= 0
- `frequency` typically "monthly", "quarterly", "annual"

### DelistedStock (DataClass)
```python
@dataclass
class DelistedStock:
    symbol: str                                    # REQUIRED - Stock ticker
    delisting_date: date                          # REQUIRED - Delisting date
    reason: DelistingReason                       # REQUIRED - Reason for delisting
    last_price: Decimal                           # REQUIRED - Last trading price
    recovery_rate: Decimal                        # REQUIRED - Estimated recovery (default 0.1)
    returns_daily: List[Tuple[date, Decimal]]     # OPTIONAL - Daily returns
    market_cap: Optional[Decimal]                 # OPTIONAL - Market cap at delisting
    volatility: Optional[float]                   # OPTIONAL - Volatility before delisting
```

**Validation Rules:**
- `recovery_rate` must be between 0 and 1
- `last_price` must be >= 0
- `returns_daily` is time series from listing to delisting

### BacktestCheckpoint (DataClass)
```python
@dataclass
class BacktestCheckpoint:
    checkpoint_id: UUID                    # REQUIRED - Unique identifier
    timestamp: datetime                    # REQUIRED - Checkpoint creation time
    current_date: date                     # REQUIRED - Simulation date
    capital: Decimal                       # REQUIRED - Current capital
    positions: Dict[str, Decimal]          # REQUIRED - Open positions
    cost_basis: Dict[str, Decimal]         # REQUIRED - Position cost basis
    year: int                              # REQUIRED - Year number (1-25)
    progress: float                        # REQUIRED - Progress 0-100
    metrics_snapshot: Dict[str, Any]       # REQUIRED - Performance snapshot
```

**Validation Rules:**
- `progress` must be between 0 and 100
- `year` must be positive
- `capital` must be >= 0
- Provides `to_dict()` and `from_dict()` for serialization

### ProgressUpdate (DataClass)
```python
@dataclass
class ProgressUpdate:
    current_year: int                      # REQUIRED - Current year being processed
    total_years: int                       # REQUIRED - Total years (default 25)
    current_date: date                     # REQUIRED - Current simulation date
    total_days: int                        # REQUIRED - Total days (default 252*25)
    capital: Decimal                       # REQUIRED - Current capital
    return_pct: Decimal                    # REQUIRED - Return percentage
    estimated_time_remaining: float        # REQUIRED - Seconds remaining
    trades_executed: int                   # REQUIRED - Trade count
    messages: List[str]                    # OPTIONAL - Info messages
```

**Validation Rules:**
- `progress_percentage()` calculated method
- `to_dict()` for JSON serialization

### DividendTracker (DataClass)
```python
@dataclass
class DividendTracker:
    total_dividends_received: Decimal      # REQUIRED - Total cash dividends
    total_dividends_reinvested: Decimal    # REQUIRED - Total reinvested
    dividend_yield: Decimal                # REQUIRED - Current yield %
    dividend_count: int                    # REQUIRED - Number of payments
    yield_on_cost: Decimal                 # REQUIRED - Yield on investment %
    dividend_history: List[DividendAction] # REQUIRED - All dividend actions
    _original_investment: Decimal          # PRIVATE - For yield on cost
```

**Validation Rules:**
- `add_dividend()` to record dividend actions
- `calculate_yield()` to compute yield metrics
- `set_original_investment()` to initialize yield on cost

### DripConfig (DataClass)
```python
@dataclass
class DripConfig:
    enable_drip: bool                      # REQUIRED - Enable DRIP
    reinvest_all: bool                     # REQUIRED - Reinvest all dividends
    reinvest_same_stock: bool              # REQUIRED - Reinvest in same stock
    min_reinvestment_amount: Decimal       # REQUIRED - Minimum amount (default 10)
    commission_drip: Decimal               # REQUIRED - Commission rate (default 0)
    fractional_shares: bool                # REQUIRED - Allow fractional shares
```

**Validation Rules:**
- `min_reinvestment_amount` must be >= 0
- `commission_drip` must be >= 0

---

## Function Signatures (Contracts)

### `BacktestCheckpoint.to_dict() -> Dict[str, Any]`
**Pre:** Checkpoint has valid data
**Post:** Returns serializable dictionary
**Raises:** None
**Retry:** No
**Side Effects:** None (pure conversion)

### `BacktestCheckpoint.from_dict(data: Dict[str, Any]) -> BacktestCheckpoint`
**Pre:** data has valid checkpoint structure
**Post:** Returns BacktestCheckpoint instance
**Raises:** KeyError, ValueError for invalid data
**Retry:** No
**Side Effects:** None (factory method)

### `ProgressUpdate.progress_percentage() -> float`
**Pre:** total_days > 0
**Post:** Returns progress 0-100
**Raises:** None (returns 0 if total_days == 0)
**Retry:** No
**Side Effects:** None

### `DividendTracker.add_dividend(action: DividendAction) -> None`
**Pre:** action is valid DividendAction
**Post:** Tracker updated with dividend data
**Raises:** None
**Retry:** No
**Side Effects:** Modifies tracker state

### `DividendTracker.calculate_yield(current_portfolio_value: Decimal) -> None`
**Pre:** current_portfolio_value >= 0
**Post:** dividend_yield and yield_on_cost calculated
**Raises:** None
**Retry:** No
**Side Effects:** Updates tracker metrics

---

## Acceptance Criteria
- [ ] All dataclasses use proper type hints
- [ ] All required fields have default values or validation
- [ ] Pydantic imports handled gracefully with try/except
- [ ] CorporateActionType enum covers all action types
- [ ] DelistingReason enum covers all delisting reasons
- [ ] StockSplit calculates adjustment_factor correctly
- [ ] BacktestCheckpoint serializes to/from dict correctly
- [ ] ProgressUpdate calculates progress_percentage correctly
- [ ] DividendTracker adds dividends and calculates yields correctly
- [ ] DripConfig has sensible defaults for DRIP settings

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

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All fields typed |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses List, Dict, Optional from typing |
| ARCH-006 | BASE_RULES.md | Value objects immutable | ⚠️ NOT APPLIED - Dataclasses not frozen (for mutability needs) |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear field names |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ NOT APPLIED - Dataclasses use default validation |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| TRD-004 | BASE_RULES.md | Audit trail | ✅ OK - Corporate actions have tracking fields |
| TRD-001 | BASE_RULES.md | Validation | ⚠️ GAP - No field validators in dataclasses |

**GAP Analysis:**

**TRD-001 GAP - Missing Field Validation**
- **Priority:** P2 (Medium)
- **Issue:** Dataclasses lack field validators (e.g., ensuring split_ratio > 0, recovery_rate between 0-1)
- **Impact:** Invalid data could be instantiated leading to runtime errors
- **Recommendation:** Add `__post_init__` validation methods or migrate to Pydantic models with field_validator

**ARCH-006 Note - Mutable Value Objects**
- **Status:** Intentionally not frozen
- **Justification:** BacktestCheckpoint and DividendTracker need mutability for state updates during backtesting
- **Trade-off:** Accept mutability for practical use in long-running simulations

---

## Dependencies
- **External:** dataclasses, datetime, decimal, enum, typing, uuid, pydantic (optional)
- **Internal:** None

---

## Required Tests
- **tests/backtesting/robust_engine/test_models.py:**
  - Test CorporateAction creation with required fields
  - Test StockSplit calculates adjustment_factor correctly
  - Test Merger sets action_type correctly
  - Test SpinOff sets action_type correctly
  - Test DividendPayment sets action_type correctly
  - Test DelistedStock with various delisting reasons
  - Test BacktestCheckpoint.to_dict() serialization
  - Test BacktestCheckpoint.from_dict() deserialization
  - Test BacktestCheckpoint handles Decimal conversion correctly
  - Test ProgressUpdate.progress_percentage() calculation
  - Test ProgressUpdate.progress_percentage() returns 0 when total_days=0
  - Test ProgressUpdate.to_dict() serialization
  - Test DividendTracker.add_dividend() updates totals
  - Test DividendTracker.calculate_yield() computes yields correctly
  - Test DividendTracker tracks reinvested dividends separately
  - Test DripConfig has sensible defaults
  - Test all dataclasses handle default values correctly
  - Test Pydantic fallback when pydantic not installed

---

## Notes
- This module defines all data structures for robust backtesting
- Uses standard library dataclasses with optional Pydantic support
- Handles corporate actions critical for survivorship bias correction
- Checkpointing enables resuming 25-year backtests
- Dividend tracking enables accurate total return calculations
- DRIP configuration enables dividend reinvestment strategies
- All monetary values use Decimal for precision
- Dates use date/datetime from standard library
- UUIDs for unique identification of actions and checkpoints
- Enum types ensure type safety for action categories
- List and Dict types use modern typing syntax (Python 3.9+)
