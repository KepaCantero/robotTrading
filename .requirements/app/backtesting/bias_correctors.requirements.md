# bias_correctors.py

## Purpose
Implements Ernest P. Chan's methodologies for eliminating backtesting biases including look-ahead bias, survivorship bias, dividend/split adjustments, and data snooping detection to ensure realistic performance estimates.

---

## Type Definitions / Data Classes

### BiasDetectionResult Class
```python
@dataclass
class BiasDetectionResult:
    has_lookahead_bias: bool              # REQUIRED - True if look-ahead detected
    lookahead_bias_severity: float         # REQUIRED - 0-1 scale (higher = worse)
    has_survivorship_bias: bool           # REQUIRED - True if survivorship bias present
    survivorship_bias_adjustment: float    # REQUIRED - Adjustment factor for returns
    has_data_snooping_bias: bool          # REQUIRED - True if overfitting detected
    corrected_sharpe_ratio: float         # REQUIRED - Bias-adjusted Sharpe ratio
    original_sharpe_ratio: float          # REQUIRED - Unadjusted Sharpe ratio
    recommendations: List[str]            # REQUIRED - Actionable recommendations
```

**Validation Rules:**
- `0 <= lookahead_bias_severity <= 1`
- `survivorship_bias_adjustment > 0`
- All lists have at least one recommendation

---

### CorporateAction Class
```python
@dataclass
class CorporateAction:
    date: datetime                      # REQUIRED - Action date
    symbol: str                         # REQUIRED - Ticker symbol
    action_type: str                    # REQUIRED - 'split', 'dividend', etc.
    ratio: Optional[float] = None       # OPTIONAL - Split ratio (e.g., 0.5 for 2-for-1)
    amount: Optional[float] = None      # OPTIONAL - Dividend amount
    metadata: Optional[Dict[str, Any]]  # OPTIONAL - Additional data
```

**Validation Rules:**
- `action_type in ['split', 'dividend', 'dividend_return', 'rights_issue']`
- `ratio > 0` if specified
- `amount >= 0` if specified

---

### PointInTimeData Class
```python
@dataclass
class PointInTimeData:
    as_of_date: datetime                     # REQUIRED - Snapshot date
    available_symbols: List[str]             # REQUIRED - Symbols trading as of date
    delisted_symbols: List[str]              # REQUIRED - Symbols delisted before date
    new_listings: List[str]                  # REQUIRED - Symbols listed after date
    corporate_actions: List[CorporateAction] # REQUIRED - Actions as of date
```

**Validation Rules:**
- All lists are non-empty (can be empty lists)
- `as_of_date` is valid datetime

---

## Function Signatures (Contracts)

### `LookAheadBiasCorrector.__init__(strict_mode: bool = True) -> None`
**Pre:** None
**Post:** Corrector initialized, detected_issues is empty list
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

### `LookAheadBiasCorrector.validate_no_lookahead(signals: pd.DataFrame, market_data: pd.DataFrame, signal_columns: List[str], timestamp_column: str = "timestamp") -> BiasDetectionResult`
**Pre:** signals and market_data have timestamp_column, signal_columns exist in signals
**Post:** Returns BiasDetectionResult with findings (severity 0-1 based on issue count)
**Raises:** ValueError, TypeError, KeyError (caught, returns error result)
**Retry:** ❌ No
**Side Effects:** Modifies detected_issues list

---

### `LookAheadBiasCorrector._generate_lookahead_recommendations() -> List[str]`
**Pre:** detected_issues has been populated
**Post:** Returns actionable recommendations for each issue type
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

### `DividendAndSplitAdjuster.__init__(adjustment_method: str = "backwards") -> None`
**Pre:** adjustment_method in ["backwards", "forwards"]
**Post:** Adjuster initialized with specified method
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

### `DividendAndSplitAdjuster.apply_stock_split(prices: pd.DataFrame, split_date: datetime, split_ratio: float, symbol_col: str = "symbol", price_col: str = "close", date_col: str = "date") -> pd.DataFrame`
**Pre:** prices has date_col and price_col, split_date valid, 0 < split_ratio <= 1
**Post:** Returns DataFrame with split-adjusted prices (backwards adjusts historical prices)
**Raises:** ValueError, TypeError, KeyError (caught, logs error, returns original prices)
**Retry:** ❌ No
**Side Effects:** None (returns copy, doesn't modify input)

---

### `DividendAndSplitAdjuster.calculate_total_return(prices: pd.Series, dividends: pd.Series) -> pd.Series`
**Pre:** prices and dividends have same index or can be aligned
**Post:** Returns total return series (price return + dividend return)
**Raises:** ValueError, TypeError (caught, returns price.pct_change())
**Retry:** ❌ No
**Side Effects:** None

---

### `DividendAndSplitAdjuster.reconstruct_adjusted_prices(raw_prices: pd.Series, dividends: pd.DataFrame, splits: pd.DataFrame) -> pd.Series`
**Pre:** raw_prices is Series with datetime index, dividends/splits have 'date' column
**Post:** Returns price series with all adjustments applied (splits oldest first)
**Raises:** ValueError, TypeError, KeyError (caught, returns raw_prices)
**Retry:** ❌ No
**Side Effects:** None

---

### `BacktestValidator.__init__(min_samples: int = 100, confidence_level: float = 0.95) -> None`
**Pre:** min_samples > 0, 0 < confidence_level < 1
**Post:** Validator initialized with corrector instances
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Creates LookAheadBiasCorrector and DividendAndSplitAdjuster instances

---

### `BacktestValidator.validate_backtest(returns: pd.Series, signals: pd.DataFrame, market_data: pd.DataFrame, benchmark_returns: Optional[pd.Series] = None) -> BiasDetectionResult`
**Pre:** returns has length >= 2, signals and market_data are valid DataFrames
**Post:** Returns comprehensive BiasDetectionResult with all bias checks
**Raises:** ValueError, TypeError (caught, returns error result)
**Retry:** ❌ No
**Side Effects:** None

---

### `BacktestValidator._calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float`
**Pre:** returns has at least 2 non-NaN values
**Post:** Returns annualized Sharpe ratio (252 trading days)
**Raises:** ValueError, ZeroDivisionError (returns 0.0)
**Retry:** ❌ No
**Side Effects:** None

---

### `BacktestValidator._check_data_snooping(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> bool`
**Pre:** returns has at least 2 values
**Post:** Returns True if data snooping likely detected (Sharpe > 3, high excess return, small sample)
**Raises:** ValueError, TypeError (returns False)
**Retry:** ❌ No
**Side Effects:** None

---

### `create_bias_correction_pipeline(raw_data: pd.DataFrame, dividend_data: Optional[pd.DataFrame] = None, split_data: Optional[pd.DataFrame] = None) -> pd.DataFrame`
**Pre:** raw_data is DataFrame with price data
**Post:** Returns DataFrame with all bias corrections applied
**Raises:** Exception (caught, logs error, returns raw_data)
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] LookAheadBiasCorrector detects signals after available data period
- [ ] LookAheadBiasCorrector detects indicators with no initial NaN values
- [ ] LookAheadBiasCorrector detects forward filling (repeated value ratio > 80%)
- [ ] DividendAndSplitAdjuster uses backwards method by default (Ernest Chan's preferred)
- [ ] apply_stock_split adjusts historical prices by split_ratio
- [ ] apply_stock_split adjusts open/high/low/close columns
- [ ] calculate_total_return aligns prices and dividends by index
- [ ] calculate_total_return fills NaN dividends with 0
- [ ] reconstruct_adjusted_prices applies splits oldest first (chronological)
- [ ] reconstruct_adjusted_prices calculates dividend returns
- [ ] BacktestValidator applies 30% Sharpe penalty for look-ahead bias severity
- [ ] BacktestValidator applies 5% baseline penalty for survivorship bias
- [ ] _calculate_sharpe_ratio annualizes with 252 trading days
- [ ] _check_data_snooping flags Sharpe > 3 as suspicious
- [ ] _check_data_snooping flags high excess return (> 0.2% daily)
- [ ] _check_data_snooping flags small samples (< 252 days)
- [ ] All error handlers return default values (no exceptions propagate)

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

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ✅ OK - Each class handles one bias type |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - All exceptions caught and logged |
| CC-007 | BASE_RULES.md | Small functions | ⚠️ PARTIAL - Some methods > 20 lines (validate_backtest, reconstruct_adjusted_prices) |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All methods have type hints |
| TYP-002 | BASE_RULES.md | Modern syntax | ✅ OK - Uses Optional[X] instead of X | None |
| BT-001 | BASE_RULES.md | Walk-forward validation | ⚠️ NOT APPLIED - Method exists but not implemented |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Validates signals don't use future data |
| BT-004 | BASE_RULES.md | Realistic costs | ⚠️ NOT APPLIED - Not in scope of this module |
| TRD-007 | BASE_RULES.md | Annualization (TRADING_DAYS = 252) | ✅ OK - Sharpe uses 252 in _calculate_sharpe_ratio |
| ARCH-001 | BASE_RULES.md | Layered architecture (domain) | ✅ OK - Domain logic, no infrastructure |

**NOTE:** This analysis considers ALL 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `dataclasses` (dataclass decorator)
  - `datetime` (datetime)
  - `typing` (Any, Dict, List, Optional, Tuple)
  - `logging` (logger)
  - `numpy` (np - for CAGR, array operations)
  - `pandas` (pd - DataFrame, Series operations)

---

## Required Tests
- **tests/backtesting/test_bias_correctors.py:**
  - Test LookAheadBiasCorrector detects signals after data period
  - Test LookAheadBiasCorrector detects missing initial NaN values
  - Test LookAheadBiasCorrector detects forward filling patterns
  - Test LookAheadBiasCorrector severity scales 0-1 based on issue count
  - Test DividendAndSplitAdjuster backwards adjustment method
  - Test apply_stock_split adjusts historical prices correctly
  - Test apply_stock_split adjusts all price columns (OHLC)
  - Test apply_stock_split handles errors gracefully
  - Test calculate_total_return aligns series by index
  - Test calculate_total_return fills NaN dividends with 0
  - Test calculate_total_return calculates dividend returns correctly
  - Test reconstruct_adjusted_prices applies splits chronologically
  - Test reconstruct_adjusted_prices calculates total return with dividends
  - Test reconstruct_adjusted_prices handles empty dividends/splits
  - Test BacktestValidator calls lookahead corrector
  - Test BacktestValidator applies Sharpe penalty for look-ahead bias
  - Test BacktestValidator applies baseline survivorship penalty
  - Test BacktestValidator checks for data snooping
  - Test BacktestValidator validates minimum sample size
  - Test _calculate_sharpe_ratio annualizes correctly (252 days)
  - Test _calculate_sharpe_ratio handles zero volatility
  - Test _calculate_sharpe_ratio handles short series
  - Test _check_data_snooping detects high Sharpe (> 3)
  - Test _check_data_snooping detects high excess returns
  - Test _check_data_snooping detects small samples
  - Test create_bias_correction_pipeline applies all corrections
  - Test all error handlers return default values
  - Test recommendations are actionable and specific

---

## Notes
This module implements Ernest P. Chan's backtesting bias correction methodologies from "Algorithmic Trading" (2013). Critical for realistic backtesting - biases can inflate Sharpe ratios by 20-50%. Uses backwards adjustment for splits (Ernest Chan's preference). Comprehensive error handling with default returns. Part of domain layer (backtesting infrastructure). Missing: walk-forward validation implementation (placeholder only).
