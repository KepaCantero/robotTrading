# universe_manager.py

## Purpose
Manages backtesting universe with survivorship bias adjustment by including delisted, bankrupt, and failed companies to prevent inflated performance metrics.

---

## Type Definitions / Data Classes

### BACKTEST_UNIVERSE (Dict)
```python
BACKTEST_UNIVERSE = {
    "survivors": List[str],           # Currently active companies
    "delisted": List[Tuple],          # (symbol, name, date, reason)
    "spun_off": List[Tuple],          # (symbol, name, date, acquirer)
    "penny_stocks": List[Tuple],      # (symbol, name, start, end, notes)
}
```

---

## Function Signatures (Contracts)

### `UniverseManager.__init__(universe_config: Optional[Dict] = None) -> None`
**Pre:** None
**Post:** UniverseManager initialized with default or custom universe
**Raises:** None
**Retry:** No
**Side Effects:** Logs initialization

### `get_universe(start_date: datetime, end_date: datetime, include_delisted: bool = True, include_spun_off: bool = True, include_penny_stocks: bool = False) -> List[str]`
**Pre:** start_date < end_date
**Post:** Returns list of symbols active during period
**Raises:** ValueError if start_date >= end_date
**Retry:** No
**Side Effects:** Logs universe size

### `filter_by_market_cap(symbols: List[str], min_market_cap: Optional[Decimal] = None, max_market_cap: Optional[Decimal] = None, historical_date: Optional[datetime] = None) -> List[str]`
**Pre:** min_market_cap >= 0 if provided, max_market_cap >= 0 if provided
**Post:** Returns filtered symbol list
**Raises:** ValueError if market caps are negative
**Retry:** No
**Side Effects:** Logs filter results

### `calculate_survivorship_bias(survivor_returns: List[float], full_universe_returns: List[float]) -> Dict[str, float]`
**Pre:** Both lists have same length
**Post:** Returns bias metrics including detection flag
**Raises:** ValueError if list lengths differ
**Retry:** No
**Side Effects:** Logs warning if bias detected

### `_calculate_cagr_from_returns(returns: List[float]) -> float`
**Pre:** Returns list not empty (returns 0.0 if empty)
**Post:** Returns CAGR as decimal
**Raises:** None
**Retry:** No
**Side Effects:** None

**IMPORTANT:** TRD-007 - TRADING_DAYS Documentation
- This function assumes daily return frequency
- TRADING_DAYS = 252 represents typical US equity market trading days per year
- The formula returns period-level CAGR; to annualize daily returns, multiply by 252
- ✅ FIXED - 2026-02-01 - TRADING_DAYS constant now documented in function docstring

---

## Acceptance Criteria
- [x] Universe includes both survivors and failed companies
- [x] Date filtering works correctly for delisted/spun_off symbols
- [x] Market cap filtering validates non-negative values
- [x] Survivorship bias quantified with CAGR comparison
- [x] TRADING_DAYS=252 documented in CAGR calculation

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 100% type coverage | 02-type-hints.md | All functions have type hints | ✅ OK |
| VAL-001 Input validation | 08-validation.md | Validate date ranges, market caps | ✅ OK |
| ERR-001 Exception handling | 05-error-handling.md | Specific exceptions with context | ✅ OK |
| LOG-001 Structured logging | 06-logging.md | Log universe operations | ✅ OK |
| TRD-007 TRADING_DAYS docs | Trading rules | Document 252 trading days in CAGR | ✅ FIXED - 2026-02-01 |

---

## Dependencies
- **External:** numpy, logging, datetime, decimal, typing
- **Internal:** None

---

## Required Tests
- **test_universe_manager.py:**
  - Test get_universe with delisted included
  - Test get_universe with spun_off included
  - Test market cap filtering
  - Test survivorship bias calculation
  - Test CAGR calculation with documented TRADING_DAYS

---

## Notes
- TRADING_DAYS=252 is the industry standard for US equity markets
- This constant is critical for annualizing daily returns in CAGR calculations
- ✅ FIXED - 2026-02-01: TRD-007 addressed with comprehensive documentation in _calculate_cagr_from_returns()
