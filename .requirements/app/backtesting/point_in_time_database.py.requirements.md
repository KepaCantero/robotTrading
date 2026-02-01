# point_in_time_database.py

## Purpose
Point-in-time database implementation to prevent look-ahead bias in backtesting by ensuring only data available at each historical point is used.

---

## Type Definitions / Data Classes

### HistoricalConstituent Class
```python
@dataclass
class HistoricalConstituent:
    symbol: str                              # REQUIRED - Stock symbol
    entry_date: datetime                     # REQUIRED - Date when symbol entered universe
    exit_date: Optional[datetime]            # OPTIONAL - Date when symbol exited
    exit_reason: Optional[str]               # OPTIONAL - 'delisted', 'merged', 'still_trading'
    market_cap: Optional[Decimal]            # OPTIONAL - Market capitalization
    sector: Optional[str]                    # OPTIONAL - Sector classification
```

**Validation Rules:**
- `exit_date` must be >= `entry_date` if both set
- `exit_reason` must be valid if `exit_date` is set

### PITDataSnapshot Class
```python
@dataclass
class PITDataSnapshot:
    as_of_date: datetime                     # REQUIRED - Snapshot date
    available_symbols: List[str]             # REQUIRED - Symbols available at this date
    total_universe_size: int                 # REQUIRED - Total count (gte 0)
    data_coverage: Dict[str, int]            # REQUIRED - symbol -> days of history available
```

**Validation Rules:**
- `total_universe_size` must equal `len(available_symbols)`
- `data_coverage` keys must be subset of `available_symbols`

### CorporateAction Class
```python
@dataclass
class CorporateAction:
    symbol: str                              # REQUIRED - Stock symbol
    action_type: str                         # REQUIRED - 'split', 'dividend', 'merger', 'spinoff'
    ex_date: datetime                        # REQUIRED - Ex-dividend date
    action_details: Dict[str, Any]           # REQUIRED - Action-specific details
    adjustment_factor: Decimal               # REQUIRED - Adjustment factor (gt 0)
```

**Validation Rules:**
- `action_type` must be valid corporate action type
- `adjustment_factor` must be positive

---

## Function Signatures (Contracts)

### `PointInTimeDatabase.__init__(pit_data_path: Optional[Path] = None, cache_size_mb: int = 100) -> None`
**Pre:** pit_data_path is None or valid path, cache_size_mb > 0
**Post:** Database initialized with cache
**Raises:** None
**Retry:** No
**Side Effects:** Initializes cache dictionaries

### `PointInTimeDatabase.get_universe_at_date(query_date: datetime, min_market_cap: Optional[Decimal] = None, sectors: Optional[List[str]] = None, max_universe_size: Optional[int] = None) -> List[str]`
**Pre:** query_date is valid datetime
**Post:** Returns list of symbols available at query_date
**Raises:** None (returns empty list on error)
**Retry:** No
**Side Effects:** May cache snapshot

### `PointInTimeDatabase.get_data_as_of_date(symbol: str, query_date: datetime, lookback_days: int = 252) -> Optional[pd.DataFrame]`
**Pre:** symbol is non-empty, query_date is valid, lookback_days > 0
**Post:** Returns DataFrame with data up to (not including) query_date, or None
**Raises:** None (returns None on error)
**Retry:** No
**Side Effects:** None

### `PointInTimeDatabase.apply_corporate_actions(symbol: str, data: pd.DataFrame, as_of_date: datetime) -> pd.DataFrame`
**Pre:** symbol is non-empty, data is valid DataFrame, as_of_date is valid
**Post:** Returns DataFrame with corporate actions applied
**Raises:** None (returns original data on error)
**Retry:** No
**Side Effects:** None

### `PointInTimeDatabase.create_pit_snapshot(as_of_date: datetime, current_symbols: List[str], data_sources: Dict[str, pd.DataFrame]) -> PITDataSnapshot`
**Pre:** as_of_date is valid, current_symbols is non-empty, data_sources has data for symbols
**Post:** Returns PITDataSnapshot for as_of_date
**Raises:** Exception on error
**Retry:** No
**Side Effects:** Caches snapshot

### `PointInTimeDatabase.validate_no_look_ahead(signals: pd.DataFrame, data: pd.DataFrame, date_column: str = "date") -> bool`
**Pre:** signals and data are valid DataFrames, date_column exists in both
**Post:** Returns True if no look-ahead bias detected
**Raises:** None (returns False on error)
**Retry:** No
**Side Effects:** Logs warnings if bias detected

---

## Acceptance Criteria
- [ ] Universe queries only return symbols available at query_date
- [ ] Data queries exclude data on or after query_date
- [ ] Corporate actions only applied if ex_date <= as_of_date
- [ ] Look-ahead validation detects future signal dates
- [ ] Cache size limit is enforced (max 1000 snapshots)
- [ ] Splits adjust price and volume correctly
- [ ] Dividends don't change historical prices
- [ ] All error cases return empty/None (never crash)
- [ ] All type hints are present and accurate

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - try/except with logging |
| BT-003 | BASE_RULES | No look-ahead bias | ✅ OK - Core functionality |
| BT-002 | BASE_RULES | Out-of-sample testing | ✅ OK - Prevents future data leakage |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - All errors logged |
| ARCH-006 | BASE_RULES | Value objects immutable | ❌ GAP - dataclass not frozen |
| LOG-005 | BASE_RULES | No sensitive data in logs | ✅ OK - No sensitive data logged |

---

## Dependencies
- **External:** logging, pandas, pathlib, decimal, datetime, typing
- **Internal:** None

---

## Required Tests
- **tests/unit/backtesting/test_point_in_time_database.py:**
  - Test universe retrieval for historical date
  - Test universe retrieval with market cap filter
  - Test universe retrieval with sector filter
  - Test universe retrieval with max size limit
  - Test data retrieval excludes future data
  - Test data retrieval with lookback_days limit
  - Test corporate action application for splits
  - Test corporate action application for dividends
  - Test corporate actions only applied if ex_date <= as_of_date
  - Test look-ahead bias validation detects future signals
  - Test look-ahead bias validation passes for valid data
  - Test snapshot creation and caching
  - Test cache size limit enforced
  - Test split adjustment multiplies price and divides volume
  - Test error handling returns empty/None
  - Test logging on errors

---

## Notes
- Implements Ernest Chan's critical recommendation for look-ahead-bias-free backtesting
- Only data available up to query_date is returned (no future data leakage)
- Corporate actions applied chronologically only if known by as_of_date
- Cache limited to 1000 snapshots to prevent memory issues
- All error cases return empty/None and log errors (never crash)
