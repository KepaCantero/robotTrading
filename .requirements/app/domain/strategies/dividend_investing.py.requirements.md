# dividend_investing.py

## Purpose
Implements dividend investing strategy based on dividend yield, growth, payout ratio, and sustainability metrics to select high-quality dividend-paying stocks.

---

## Type Definitions / Data Classes

### DividendSignal Class (Enum)
```python
class DividendSignal(str, Enum):
    BUY = "buy"        # Attractive dividend profile
    HOLD = "hold"      # Maintain current position
    SELL = "sell"      # Dividend cut risk or overvalued
    AVOID = "avoid"    # Not suitable for dividend strategy
```

**Validation Rules:**
- Enum values are validated by Python's Enum system

### DividendMetrics Class
```python
@dataclass
class DividendMetrics:
    symbol: str                       # REQUIRED - Stock symbol
    dividend_yield: float             # REQUIRED - Annual dividend / price, >= 0
    dividend_growth_rate: float       # REQUIRED - Historical CAGR of dividends
    payout_ratio: float               # REQUIRED - Dividends / earnings, >= 0
    free_cash_payout_ratio: float     # REQUIRED - Dividends / free cash flow, >= 0
    dividend_years: int               # REQUIRED - Consecutive years of payments, >= 0
    dividend_growth_years: int        # REQUIRED - Consecutive years of increases, >= 0
    earnings_yield: float             # REQUIRED - Earnings / price (inverse P/E)
    return_on_equity: float           # REQUIRED - ROE
    debt_to_equity: float             # REQUIRED - D/E ratio, >= 0
```

**Validation Rules:**
- dividend_yield >= 0 (with NaN handling)
- payout_ratio >= 0 (with NaN handling)
- free_cash_payout_ratio >= 0 (with NaN handling)
- dividend_years >= 0
- dividend_growth_years >= 0
- All float fields validated with np.isfinite()

### DividendPortfolio Class
```python
@dataclass
class DividendPortfolio:
    positions: Dict[str, float]       # REQUIRED - Symbol -> weight mapping
    portfolio_yield: float            # REQUIRED - Weighted average dividend yield
    portfolio_growth_rate: float      # REQUIRED - Weighted average dividend growth
    portfolio_payout_ratio: float     # REQUIRED - Weighted average payout ratio
    yield_on_cost: float = 0.0        # OPTIONAL - Expected yield on original cost
    expected_annual_income: float = 0.0  # OPTIONAL - Expected annual dividend income
```

**Validation Rules:**
- positions can be empty dict
- All float fields must be finite
- Weights should sum to 1.0 (normalized after construction)

---

## Function Signatures (Contracts)

### `DividendInvesting.__init__(min_yield, max_yield, min_growth_rate, max_payout_ratio, min_dividend_years, min_sustainability_score, target_portfolio_yield) -> None`
**Pre:** All parameters are finite and in valid ranges
**Post:** Strategy instance initialized with validated parameters
**Raises:** None
**Retry:** No
**Side Effects:** None

### `screen_dividend_stocks(dividend_metrics: Dict[str, DividendMetrics]) -> List[str]`
**Pre:** dividend_metrics is valid dictionary
**Post:** Returns list of symbols passing screen (can be empty)
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings for invalid metrics

### `_passes_screen(metrics: DividendMetrics) -> bool`
**Pre:** metrics is valid DividendMetrics instance
**Post:** Returns True if stock passes all screen criteria
**Raises:** None
**Retry:** No
**Side Effects:** Logs warnings for invalid metrics

### `rank_dividend_stocks(dividend_metrics: Dict[str, DividendMetrics]) -> List[Tuple[str, float]]`
**Pre:** dividend_metrics is valid dictionary
**Post:** Returns list of (symbol, score) sorted by score (descending)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_dividend_score(metrics: DividendMetrics) -> float`
**Pre:** metrics is valid DividendMetrics instance
**Post:** Returns composite score in [0, 1]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `construct_portfolio(dividend_metrics: Dict[str, DividendMetrics], capital: float, max_positions: int = 30, min_weight: float = 0.02, max_weight: float = 0.05) -> DividendPortfolio`
**Pre:** dividend_metrics is valid, capital > 0, 0 < min_weight <= max_weight
**Post:** Returns DividendPortfolio with weights summing to 1.0 (or empty if no qualified stocks)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_apply_weight_constraints(weights: Dict[str, float], min_weight: float, max_weight: float) -> Dict[str, float]`
**Pre:** weights is valid dict, 0 < min_weight <= max_weight
**Post:** Returns weights constrained to [min_weight, max_weight]
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rebalance_portfolio(current_portfolio: DividendPortfolio, dividend_metrics: Dict[str, DividendMetrics], capital: float, rebalance_threshold: float = 0.05) -> DividendPortfolio`
**Pre:** All inputs are valid
**Post:** Returns new portfolio if rebalancing needed, else current portfolio
**Raises:** None
**Retry:** No
**Side Effects:** None

### `generate_signal(metrics: DividendMetrics, current_price: float, fair_value: float = 0.0) -> DividendSignal`
**Pre:** metrics is valid, current_price > 0, fair_value >= 0
**Post:** Returns appropriate DividendSignal
**Raises:** None (returns AVOID for invalid price)
**Retry:** No
**Side Effects:** Logs warnings for invalid inputs

---

## Acceptance Criteria
- [ ] All DividendMetrics fields validated for NaN/inf before calculations
- [ ] dividend_sustainability_score returns value in [0, 1]
- [ ] dividend_attractiveness_score returns value in [0, 1]
- [ ] screen_dividend_stocks filters by yield, payout, years, sustainability
- [ ] construct_portfolio normalizes weights to sum to 1.0
- [ ] generate_signal returns AVOID for invalid current_price
- [ ] All dataclass fields have type hints
- [ ] No mutable default arguments
- [ ] Input validation uses np.isfinite() for all float parameters

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X \| None) | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ⚠️ NOT APPLIED - Uses returns/defaults (valid pattern) |
| LOG-004 | BASE_RULES | Error logging | ✅ OK - Logs warnings for invalid inputs |
| ARCH-003 | BASE_RULES | No framework in domain | ✅ OK - Only numpy, logging, dataclasses |
| TRD-002 | BASE_RULES | Risk validation | ✅ OK - Validates metrics, prices |
| ARCH-006 | BASE_RULES | Value objects immutable | ⚠️ NOT APPLIED - dataclasses not frozen |

**NOTE:** This analysis considers universal rules from BASE_RULES.md

---

## Dependencies
- **External:** numpy, logging, dataclasses, decimal, enum, typing
- **Internal:** None (pure domain service)

---

## Required Tests
- **tests/unit/domain/strategies/test_dividend_investing.py:**
  - Test DividendMetrics properties (is_dividend_aristocrat, is_dividend_king)
  - Test dividend_sustainability_score calculation with valid/edge-case inputs
  - Test dividend_attractiveness_score calculation
  - Test screen_dividend_stocks filtering logic
  - Test _passes_screen with various metric combinations
  - Test rank_dividend_stocks sorting
  - Test _calculate_dividend_score weighting
  - Test construct_portfolio weight calculation and normalization
  - Test _apply_weight_constraints min/max capping
  - Test rebalance_portfolio threshold logic
  - Test generate_signal for BUY/HOLD/SELL/AVOID scenarios
  - Test input validation (NaN, inf, negative values)
  - Test edge cases (empty metrics, single stock)

---

## Notes
- Pure domain service with no infrastructure dependencies
- Extensive NaN/inf handling for robustness
- Defensive programming (returns defaults rather than raising)
- Decimal imported but not used (uses float)
- Scores normalized to [0, 1] range
- Portfolio weights automatically normalized to sum to 1.0
