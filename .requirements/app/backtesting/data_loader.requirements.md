# data_loader.py

## Purpose
Load historical market data from multiple sources (CSV files, Yahoo Finance API, yahoo_fin) for backtesting with vectorized operations for performance.

---

## Type Definitions / Data Classes

### Quote (from app.models.market_data)
```python
class Quote(BaseModel):
    symbol: str                      # REQUIRED - Trading symbol
    bid: Decimal                     # REQUIRED - Current bid price
    ask: Decimal                     # REQUIRED - Current ask price
    last: Decimal                    # REQUIRED - Last trade price
    volume: Decimal                  # REQUIRED - Volume (capped at 10B)
    timestamp: datetime              # REQUIRED - Quote timestamp
    high: Optional[Decimal] = None   # OPTIONAL - Daily high
    low: Optional[Decimal] = None    # OPTIONAL - Daily low
    open: Optional[Decimal] = None   # OPTIONAL - Daily open
    close: Optional[Decimal] = None  # OPTIONAL - Daily close
    spread: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    metadata: Optional[Dict[str, Any]] = None
```

**Validation Rules:**
- `volume` capped at 10B (10,000,000,000) to prevent validation errors
- All price fields use Decimal for precision
- bid < ask relationship maintained

---

## Function Signatures (Contracts)

### `DataLoader.__init__(base_path: Optional[Path] = None)`
**Pre:** base_path exists if provided
**Post:** DataLoader initialized with base_path defaulting to "data/historical"
**Raises:** None
**Retry:** No
**Side Effects:** Creates cache dict

### `load_market_data(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d", source: str = "csv") -> List[Quote]`
**Pre:** symbol non-empty, start_date < end_date
**Post:** Returns List[Quote] for date range, sorted by timestamp
**Raises:** FileNotFoundError if CSV not found, ValueError if unsupported source, RuntimeError if all Yahoo methods fail
**Retry:** ✅ Yes (tries multiple Yahoo Finance methods: v8 API → yfinance → yahoo_fin)
**Side Effects:** May cache results

### `_load_from_csv(symbol: str, start_date: datetime, end_date: datetime) -> List[Quote]`
**Pre:** CSV file exists at base_path/symbol.csv
**Post:** Returns filtered Quote list for date range
**Raises:** FileNotFoundError if CSV missing, ValueError/KeyError on parse error
**Retry:** No
**Side Effects:** None

### `_load_from_yfinance(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]`
**Pre:** symbol valid for Yahoo Finance
**Post:** Returns Quote list from Yahoo Finance
**Raises:** RuntimeError if all methods fail
**Retry:** ✅ Yes (v8 API → yfinance → yahoo_fin fallback)
**Side Effects:** None

### `_load_from_yahoo_v8_api(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]`
**Pre:** Valid symbol, date ranges
**Post:** Returns Quote list or empty list if API fails
**Raises:** None (returns [] on failure)
**Retry:** No
**Side Effects:** Makes HTTP request to Yahoo Finance API

### `_convert_yfinance_to_quotes(hist: pd.DataFrame, symbol: str) -> List[Quote]`
**Pre:** hist non-empty DataFrame with price columns
**Post:** Returns List[Quote] with vectorized conversion (100-1000x faster than iterrows)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_convert_dataframe_to_quotes(df: pd.DataFrame, symbol: str) -> List[Quote]`
**Pre:** df has price columns
**Post:** Returns List[Quote] using vectorized operations
**Raises:** None
**Retry:** No
**Side Effects:** None

### `save_to_csv(data: List[Quote], filename: str) -> None`
**Pre:** data non-empty list of Quotes
**Post:** CSV file saved to base_path/filename
**Raises:** IOError on write failure
**Retry:** No
**Side Effects:** Creates/overwrites CSV file

### `load_market_data(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]` (convenience function)
**Pre:** symbol valid, dates valid
**Post:** Returns Quote list using default DataLoader
**Raises:** Propagates from DataLoader.load_market_data
**Retry:** Yes (delegates to DataLoader)
**Side Effects:** None

---

## Acceptance Criteria
- [ ] CSV loading handles both 'date' and 'timestamp' column names
- [ ] Volume capped at 10B shares (NVDA can have >1B)
- [ ] Vectorized operations used for DataFrame to Quote conversion (100-1000x faster)
- [ ] Yahoo Finance v8 API tried first (most reliable)
- [ ] Fallback to yfinance if v8 API fails
- [ ] Fallback to yahoo_fin if yfinance fails
- [ ] RuntimeError raised if all Yahoo methods fail
- [ ] Column names normalized to lowercase
- [ ] Date range filtering works correctly
- [ ] Empty DataFrame handled gracefully (returns [])
- [ ] Timezone handling correct (dates not shifted)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-001 | 01-formatting-style.md | Line length ≤ 100 characters | ⚠️ GAP - Some lines exceed 100 chars |
| FMT-006 | 01-formatting-style.md | Use f-strings not .format() | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ✅ OK |
| TYP-003 | 02-type-hints.md | No Any without justification | ❌ GAP - current_price_func uses Any |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ⚠️ NOT APPLIED - Some long functions |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ✅ OK |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| PERF-001 | Custom | Use vectorized operations, not iterrows | ✅ OK - VECTORIZED comments present |

**Performance Optimization:**
- ✅ VECTORIZED: Volume capping using vectorized apply
- ✅ VECTORIZED: Decimal conversion using apply
- ✅ VECTORIZED: Quote creation using list comprehension
- ⚠️ GAP: _convert_dataframe_to_quotes has incorrect variable reference (name vs i)

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** logging, datetime, decimal, pathlib, pandas, yfinance, requests (for v8 API)
- **Internal:**
  - app.models.market_data.Quote

---

## Required Tests
- **test_data_loader.py:**
  - Success: Load from CSV file
  - Success: Load from Yahoo Finance v8 API
  - Success: Fallback to yfinance
  - Success: Fallback to yahoo_fin
  - Success: Vectorized conversion performance (should be fast)
  - Error: CSV file not found
  - Error: Invalid symbol
  - Error: All Yahoo methods fail (RuntimeError)
  - Edge: Empty CSV
  - Edge: Volume > 10B (should be capped)
  - Edge: Date range with no data
  - Edge: Column names uppercase vs lowercase
  - Integration: Save to CSV and reload

---

## Notes
- Volume capped at 10B to prevent Decimal validation errors (NVDA case)
- Yahoo Finance v8 API is most reliable (direct HTTP)
- Fallback pattern: v8 API → yfinance → yahoo_fin → RuntimeError
- Vectorized operations provide 100-1000x performance improvement over iterrows
- BUG: _convert_dataframe_to_quotes line 457 has undefined variable `name` (should use loop index)
