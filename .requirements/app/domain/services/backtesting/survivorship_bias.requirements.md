# survivorship_bias.py

## Purpose
Handles survivorship bias correction in backtesting by tracking delisted stocks, adjusting returns for corporate actions, and including failed companies to prevent overestimation of returns following Lopez de Prado's financial machine learning principles.

---

## Type Definitions / Data Classes

### DelistingReason Enum
```python
class DelistingReason(str, Enum):
    BANKRUPTCY = "bankruptcy"        # Company went bankrupt
    MERGER = "merger"                # Merged with another company
    ACQUISITION = "acquisition"      # Acquired by another company
    DELISTING = "delisting"          # Forced delisting by exchange
    PRIVATE = "went_private"         # Taken private
    LIQUIDATION = "liquidation"      # Liquidated
    OTHER = "other"                  # Other reason
```
**Validation Rules:** Must be one of the seven defined delisting reasons

### CorporateActionType Enum
```python
class CorporateActionType(str, Enum):
    STOCK_SPLIT = "stock_split"          # Stock split (e.g., 2-for-1)
    REVERSE_SPLIT = "reverse_split"      # Reverse stock split
    SPINOFF = "spinoff"                  # Spinoff of subsidiary
    DIVIDEND = "dividend"                # Dividend payment
    RIGHTS_OFFERING = "rights_offering"  # Rights offering
    MERGER = "merger"                    # Merger
    ACQUISITION = "acquisition"          # Acquisition
    TENDER_OFFER = "tender_offer"        # Tender offer
    NAME_CHANGE = "name_change"          # Company name change
    SYMBOL_CHANGE = "symbol_change"      # Ticker symbol change
```
**Validation Rules:** Must be one of the ten defined corporate action types

### DelistingEvent DataClass
```python
@dataclass
class DelistingEvent:
    symbol: str                      # REQUIRED - Delisted symbol
    delisting_date: date             # REQUIRED - Date of delisting
    reason: DelistingReason          # REQUIRED - Reason for delisting
    last_price: Decimal              # REQUIRED - Last trading price
    last_volume: Optional[int] = None           # OPTIONAL - Last day's volume
    recovery_rate: Optional[float] = None       # OPTIONAL - Recovery rate (0-1)
    acquired_by: Optional[str] = None           # OPTIONAL - Acquiring company
    acquisition_terms: Optional[str] = None     # OPTIONAL - Terms of acquisition
```
**Validation Rules:**
- `last_price` must be >= 0
- `recovery_rate` in range [0, 1] if provided
- `is_bailout` property returns True if recovery_rate > 0
- `total_loss` property returns 1.0 - recovery_rate (or 1.0 if None)

### CorporateAction DataClass
```python
@dataclass
class CorporateAction:
    symbol: str                      # REQUIRED - Symbol of action
    action_date: date                # REQUIRED - Date of action
    action_type: CorporateActionType # REQUIRED - Type of action
    ratio: Optional[float] = None    # OPTIONAL - Ratio for splits/spinoffs
    cash_amount: Optional[Decimal] = None     # OPTIONAL - Cash amount
    new_symbol: Optional[str] = None          # OPTIONAL - New symbol after change
    description: Optional[str] = None         # OPTIONAL - Description
```
**Validation Rules:**
- `ratio` must be > 0 if provided
- `cash_amount` must be >= 0 if provided

### CorporateAction.adjust_price(price) -> Decimal
**Pre:** price >= 0
**Post:** For STOCK_SPLIT: returns price / ratio
**Post:** For REVERSE_SPLIT: returns price * ratio
**Post:** Otherwise: returns price unchanged

### CorporateAction.adjust_quantity(quantity) -> Decimal
**Pre:** quantity >= 0
**Post:** For STOCK_SPLIT: returns quantity * ratio
**Post:** For REVERSE_SPLIT: returns quantity / ratio
**Post:** Otherwise: returns quantity unchanged

### DelistingAdjustment DataClass
```python
@dataclass
class DelistingAdjustment:
    symbol: str                    # REQUIRED - Adjusted symbol
    delisting_date: date           # REQUIRED - Date of delisting
    adjustment_factor: float       # REQUIRED - Multiplier for returns
    recovery_return: float         # REQUIRED - Return on delisting day
```
**Validation Rules:**
- `adjustment_factor` can be negative (losses)
- `recovery_return` typically negative (except mergers with premium)

---

## Function Signatures (Contracts)

### `SurvivorshipBiasCorrector.__init__()`
**Pre:** None
**Post:** Corrector initialized with empty tracking
**Raises:** None
**Retry:** No
**Side Effects:** Initializes _delistings, _corporate_actions, _symbol_changes dicts

### `SurvivorshipBiasCorrector.add_delisting(delisting) -> None`
**Pre:** delisting is valid DelistingEvent
**Post:** Delisting added to tracking
**Raises:** None
**Retry:** No
**Side Effects:** Adds delisting to _delistings dict

### `SurvivorshipBiasCorrector.add_corporate_action(action) -> None`
**Pre:** action is valid CorporateAction
**Post:** Corporate action added to tracking
**Raises:** None
**Retry:** No
**Side Effects:** Appends action to _corporate_actions[symbol]
**Post:** If SYMBOL_CHANGE: adds mapping to _symbol_changes

### `SurvivorshipBiasCorrector.get_delisting(symbol) -> Optional[DelistingEvent]`
**Pre:** symbol is valid string
**Post:** Returns DelistingEvent if found, else None
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.get_corporate_actions(symbol) -> List[CorporateAction]`
**Pre:** symbol is valid string
**Post:** Returns list of actions for symbol (empty if none)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.check_delisting_date(symbol, current_date) -> Optional[DelistingEvent]`
**Pre:** symbol valid, current_date valid
**Post:** Returns DelistingEvent if delisted on or before current_date
**Post:** Returns None if not delisted or delisting in future
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.adjust_returns_for_delisting(returns, symbol) -> pd.Series`
**Pre:** returns is pandas Series with datetime index
**Post:** Returns adjusted returns with delisting impact
**Post:** BANKRUPTCY: -50% to -100% return based on recovery_rate
**Post:** MERGER/ACQUISITION: 0-30% premium (recovery_rate - 1)
**Post:** OTHER: -50% default
**Post:** Future returns after delisting set to NaN
**Raises:** None
**Retry:** No
**Side Effects:** None (returns new Series)

### `SurvivorshipBiasCorrector.adjust_price_series(prices, symbol) -> pd.Series`
**Pre:** prices is pandas Series with datetime index
**Post:** Returns adjusted prices for stock splits/reverse splits
**Post:** Applies adjustments to prices BEFORE action date
**Raises:** None
**Retry:** No
**Side Effects:** None (returns new Series)

### `SurvivorshipBiasCorrector.get_current_symbol(historical_symbol, as_of_date) -> str`
**Pre:** historical_symbol valid, as_of_date valid
**Post:** Returns current symbol as of as_of_date
**Post:** Handles recursive symbol changes
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.calculate_universe_including_delisted(current_date, all_symbols, lookback_days) -> List[str]`
**Pre:** all_symbols is list of strings, lookback_days > 0
**Post:** Returns symbols tradable at current_date including delisted
**Post:** Includes delisted symbols if delisted within lookback period
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.handle_spinoff(parent_symbol, spinoff_symbol, spinoff_date, spinoff_ratio) -> None`
**Pre:** All parameters valid, spinoff_ratio > 0
**Post:** Adds SPINOFF corporate action for parent
**Raises:** None
**Retry:** No
**Side Effects:** Adds corporate action to _corporate_actions

### `SurvivorshipBiasCorrector.get_adjusted_close(raw_close, symbol, as_of_date) -> Decimal`
**Pre:** raw_close >= 0, all parameters valid
**Post:** Returns close price adjusted for future corporate actions
**Post:** Applies adjustments for actions with action_date > as_of_date
**Raises:** None
**Retry:** No
**Side Effects:** None

### `SurvivorshipBiasCorrector.calculate_survivorship_bias(survivor_returns, full_universe_returns) -> float`
**Pre:** survivor_returns is Series, full_universe_returns is DataFrame
**Post:** Returns bias amount (positive = survivors overstate returns)
**Formula:** survivor_mean - full_universe_mean
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] AC-SB-001: DelistingEvent.total_loss returns 1.0 - recovery_rate (or 1.0)
- [ ] AC-SB-002: DelistingEvent.is_bailout returns True only if recovery_rate > 0
- [ ] AC-SB-003: CorporateAction.adjust_price divides for stock splits
- [ ] AC-SB-004: CorporateAction.adjust_price multiplies for reverse splits
- [ ] AC-SB-005: CorporateAction.adjust_quantity multiplies for stock splits
- [ ] AC-SB-006: CorporateAction.adjust_quantity divides for reverse splits
- [ ] AC-SB-007: adjust_returns_for_delisting applies bankruptcy adjustment
- [ ] AC-SB-008: adjust_returns_for_delisting sets future returns to NaN
- [ ] AC-SB-009: adjust_price_series adjusts historical prices
- [ ] AC-SB-010: get_current_symbol handles recursive symbol changes
- [ ] AC-SB-011: calculate_universe_including_delisted includes recent delistings
- [ ] AC-SB-012: get_adjusted_close applies future corporate actions
- [ ] AC-SB-013: calculate_survivorship_bias returns positive if survivor bias exists
- [ ] AC-SB-014: SYMBOL_CHANGE actions tracked in _symbol_changes dict

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** See `../../BASE_RULES.md` for 96+ universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| BT-011 | papers/lopez-de-prado | Survivorship bias overestimates returns | ✅ OK |
| BT-003 | papers/backtesting | Include delisted securities | ✅ OK |
| ARCH-003 | BASE_RULES | Domain has no framework dependencies | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Safe calculations |
| LOG-004 | BASE_RULES | Error logging | ⚠️ NOT APPLIED - Pure functions |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - All defaults are immutable |

---

## Dependencies
- **External:** numpy, pandas
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/domain/services/backtesting/test_survivorship_bias.py:**
  - Test DelistingEvent properties (is_bailout, total_loss)
  - Test CorporateAction.adjust_price for stock splits
  - Test CorporateAction.adjust_price for reverse splits
  - Test CorporateAction.adjust_quantity for stock splits
  - Test CorporateAction.adjust_quantity for reverse splits
  - Test add_delisting and get_delisting
  - Test add_corporate_action and get_corporate_actions
  - Test check_delisting_date returns delisting if passed
  - Test check_delisting_date returns None if future
  - Test adjust_returns_for_delisting with BANKRUPTCY
  - Test adjust_returns_for_delisting with MERGER
  - Test adjust_returns_for_delisting sets future returns to NaN
  - Test adjust_price_series for stock splits
  - Test adjust_price_series adjusts historical prices only
  - Test get_current_symbol with single symbol change
  - Test get_current_symbol with recursive symbol changes
  - Test calculate_universe_including_delisted includes recent delistings
  - Test calculate_universe_including_delisted excludes old delistings
  - Test handle_spinoff creates SPINOFF action
  - Test get_adjusted_close applies future actions
  - Test calculate_survivorship_bias calculation

---

## Notes
Reference: Lopez de Prado, M. "Advances in Financial Machine Learning" - Survivorship bias is a critical issue that leads to significant overestimation of strategy performance. Must include delisted and failed companies in historical backtesting universes.
