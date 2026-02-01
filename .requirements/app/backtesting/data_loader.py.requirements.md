# data_loader.py

## Purpose
Loads historical market data from multiple sources (CSV files, Yahoo Finance API, yahoo_fin) for backtesting. Provides vectorized data conversion and volume capping to handle large datasets efficiently.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses external data models but defines no dataclasses.

### External Dependencies
```python
from app.models.market_data import Quote  # External model
# Quote is defined in app/models/market_data.py with fields:
# - symbol: str
# - bid: Decimal
# - ask: Decimal
# - last: Decimal
# - volume: Decimal
# - timestamp: datetime
# - high: Decimal
# - low: Decimal
# - open: Decimal
# - close: Decimal
# - spread: Decimal (optional)
# - change: Decimal (optional)
# - change_percent: Decimal (optional)
# - metadata: Dict[str, Any] (optional)
```

**Validation Rules:**
- Volume is capped at Decimal("10000000000") (10B shares) to prevent validation errors
- All price fields converted to Decimal for precision
- Timestamps converted from various formats to datetime objects

---

## Function Signatures (Contracts)

### `DataLoader.__init__(base_path: Optional[Path] = None) -> None`
**Pre:** base_path is a valid directory path or None
**Post:** DataLoader instance initialized with base_path defaulting to "data/historical"
**Raises:** ❌ No
**Side Effects:** Initializes empty cache dictionary, sets base_path

### `DataLoader.load_market_data(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d", source: str = "csv") -> List[Quote]`
**Pre:** symbol is non-empty string, start_date < end_date, source in ["csv", "yfinance", "ibkr"]
**Post:** Returns list of Quote objects sorted by timestamp
**Raises:** ValueError if source not supported, FileNotFoundError if CSV missing
**Retry:** ❌ No
**Side Effects:** May make HTTP requests to Yahoo Finance API

### `DataLoader._load_from_csv(symbol: str, start_date: datetime, end_date: datetime) -> List[Quote]`
**Pre:** CSV file exists at base_path/symbol.csv
**Post:** Returns filtered list of Quote objects within date range
**Raises:** FileNotFoundError if CSV missing, ValueError/KeyError for malformed data
**Retry:** ❌ No
**Side Effects:** None (read-only)

### `DataLoader._load_from_yfinance(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]`
**Pre:** symbol is valid ticker, timeframe in ["1d", "1h", "15m"]
**Post:** Returns list of Quote objects from Yahoo Finance
**Raises:** RuntimeError if all data sources fail
**Retry:** ✅ Yes (tries 3 methods: v8 API, yfinance, yahoo_fin)
**Side Effects:** Makes HTTP requests to Yahoo Finance

### `DataLoader._load_from_yahoo_v8_api(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]`
**Pre:** symbol is valid ticker, timeframe in ["1d", "1h", "1m"]
**Post:** Returns list of Quote objects or empty list on failure
**Raises:** ❌ No (returns [] on error)
**Retry:** ❌ No (caller retries with other methods)
**Side Effects:** Makes HTTP request to query1.finance.yahoo.com/v8/finance/chart

### `DataLoader._convert_yfinance_to_quotes(hist: pd.DataFrame, symbol: str) -> List[Quote]`
**Pre:** hist is non-empty DataFrame with price columns
**Post:** Returns list of Quote objects with Decimal precision
**Raises:** ❌ No
**Side Effects:** None (pure transformation)

### `DataLoader._convert_dataframe_to_quotes(df: pd.DataFrame, symbol: str) -> List[Quote]`
**Pre:** df is non-empty DataFrame with price columns
**Post:** Returns list of Quote objects with fallback values for missing columns
**Raises:** ❌ No
**Side Effects:** None (pure transformation)

### `DataLoader.save_to_csv(data: List[Quote], filename: str) -> None`
**Pre:** data is non-empty list of Quote objects, filename is valid
**Post:** CSV file created at base_path/filename
**Raises:** ❌ No (but may fail on filesystem errors)
**Side Effects:** Writes file to disk

### `load_market_data(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1d") -> List[Quote]`
**Pre:** symbol is non-empty string, start_date < end_date
**Post:** Returns list of Quote objects using default source="csv"
**Raises:** See DataLoader.load_market_data
**Retry:** See DataLoader.load_market_data
**Side Effects:** Creates temporary DataLoader instance

---

## Acceptance Criteria
- [ ] All Quote objects have Decimal precision for price fields (not float)
- [ ] Volume values capped at 10B shares (Decimal("10000000000"))
- [ ] Timestamps are datetime objects (not strings)
- [ ] Vectorized operations used (no iterrows())
- [ ] Empty list returned when Yahoo Finance v8 API fails (not exception)
- [ ] RuntimeError raised when ALL Yahoo Finance methods fail
- [ ] CSV loader handles both 'date' and 'timestamp' column names
- [ ] Column names normalized to lowercase before processing
- [ ] Fallback values used when high/low/open missing (defaults to close)
- [ ] No hardcoded secrets or API keys

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | All functions have type hints | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES.md | Use modern syntax (list[T], X \| None) | ✅ OK - Uses Optional[T] |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear function names |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions |
| PERF-001 | BASE_RULES.md | Use vectorized operations | ✅ OK - No iterrows(), uses apply() |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No API keys in code |
| TRD-005 | BASE_RULES.md | Price validation | ⚠️ NOT APPLIED - Prices validated downstream |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ❌ GAP - Missing exc_info=True in some error handlers |
| ARCH-004 | BASE_RULES.md | Functions < 20 lines (ideally) | ❌ GAP - _convert_dataframe_to_quotes is 66 lines |
| TST-005 | BASE_RULES.md | Coverage > 80% | ⚠️ NOT APPLIED - No tests exist yet |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** pandas, numpy, yfinance, yahoo_fin (optional), requests
- **Internal:** app.models.market_data.Quote

---

## Required Tests
- **tests/unit/backtesting/test_data_loader.py:**
  - Success: Load from CSV with valid data
  - Success: Load from yfinance with valid symbol
  - Success: Vectorized operations produce correct results
  - Success: Volume capping at 10B shares
  - Success: Fallback to yfinance when v8 API fails
  - Success: Fallback to yahoo_fin when yfinance fails
  - Error: CSV file not found raises FileNotFoundError
  - Error: Invalid source raises ValueError
  - Error: RuntimeError when all Yahoo sources fail
  - Edge: Empty DataFrame returns empty list
  - Edge: Missing columns use fallback values
  - Edge: Both 'date' and 'timestamp' column names handled
  - Edge: Decimal precision maintained (no float conversion)

---

## Notes
- **Performance:** Uses vectorized pandas operations (100-1000x faster than iterrows)
- **Fallback Strategy:** Yahoo Finance v8 API → yfinance → yahoo_fin
- **Volume Capping:** Prevents validation errors for high-volume stocks (e.g., NVDA)
- **Thread Safety:** Not thread-safe due to mutable cache (consider in concurrent use)
