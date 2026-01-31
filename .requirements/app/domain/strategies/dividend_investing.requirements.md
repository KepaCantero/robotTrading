# dividend_investing.py

## Purpose
Dividend Investing strategy domain service - selects stocks based on dividend yield, growth, and sustainability metrics.

---

## Type Definitions / Data Classes

### DividendSignal (Enum)
```python
class DividendSignal(str, Enum):
    BUY = "buy"          # Attractive dividend profile
    HOLD = "hold"        # Maintain current position
    SELL = "sell"        # Dividend cut risk or overvalued
    AVOID = "avoid"      # Not suitable for dividend strategy
```

### DividendMetrics
```python
@dataclass
class DividendMetrics:
    symbol: str                         # REQUIRED - Stock symbol
    dividend_yield: float               # REQUIRED - Annual dividend / price
    dividend_growth_rate: float         # REQUIRED - Historical CAGR of dividends
    payout_ratio: float                 # REQUIRED - Dividends / earnings
    free_cash_payout_ratio: float       # REQUIRED - Dividends / free cash flow
    dividend_years: int                 # REQUIRED - Consecutive years of payments
    dividend_growth_years: int          # REQUIRED - Consecutive years of increases
    earnings_yield: float               # REQUIRED - Earnings / price (inverse P/E)
    return_on_equity: float             # REQUIRED - ROE
    debt_to_equity: float               # REQUIRED - D/E ratio
```

**Properties:**
- `is_dividend_aristocrat` - 25+ years of consecutive increases
- `is_dividend_king` - 50+ years of consecutive increases
- `dividend_sustainability_score` - (0-1) score based on payout, FCF, growth
- `dividend_attractiveness_score` - (0-1) score combining yield, growth, sustainability

### DividendPortfolio
```python
@dataclass
class DividendPortfolio:
    positions: Dict[str, float]         # REQUIRED - Symbol -> weight
    portfolio_yield: float              # REQUIRED - Weighted avg dividend yield
    portfolio_growth_rate: float        # REQUIRED - Weighted avg dividend growth
    portfolio_payout_ratio: float       # REQUIRED - Weighted avg payout ratio
    yield_on_cost: float = 0.0          # OPTIONAL - Yield on original cost
    expected_annual_income: float = 0.0  # OPTIONAL - Expected annual income
```

**Properties:**
- `current_yield` - Returns portfolio_yield
- `calculate_income(capital)` - Returns capital × portfolio_yield

---

## Function Signatures (Contracts)

### `DividendInvesting.__init__(min_yield, max_yield, min_growth_rate, max_payout_ratio, min_dividend_years, min_sustainability_score, target_portfolio_yield) -> None`
**Pre:** min_yield >= 0; max_yield > min_yield; max_payout_ratio <= 1; min_dividend_years >= 1; min_sustainability_score in [0, 1]; target_portfolio_yield > 0
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `screen_dividend_stocks(dividend_metrics) -> List[str]`
**Pre:** dividend_metrics is dict of symbol -> DividendMetrics
**Post:** Returns list of symbols passing all screening criteria
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `rank_dividend_stocks(dividend_metrics) -> List[Tuple[str, float]]`
**Pre:** dividend_metrics is dict of symbol -> DividendMetrics
**Post:** Returns list of (symbol, score) sorted by score (descending)
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `construct_portfolio(dividend_metrics, capital, max_positions, min_weight, max_weight) -> DividendPortfolio`
**Pre:** dividend_metrics non-empty; capital > 0; max_positions >= 1; 0 < min_weight <= max_weight <= 1
**Post:** Returns dividend portfolio with weights summing to 1.0
**Raises:** None (returns empty portfolio if no stocks pass screen)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `rebalance_portfolio(current_portfolio, dividend_metrics, capital, rebalance_threshold) -> DividendPortfolio`
**Pre:** current_portfolio valid; dividend_metrics updated
**Post:** Returns new portfolio if rebalancing needed, else current
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `generate_signal(metrics, current_price, fair_value) -> DividendSignal`
**Pre:** metrics valid; current_price > 0; fair_value >= 0
**Post:** Returns BUY/HOLD/SELL/AVOID signal
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_passes_screen(metrics) -> bool` (private)
**Pre:** metrics valid
**Post:** Returns True if stock passes all screening criteria
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_calculate_dividend_score(metrics) -> float` (private)
**Pre:** metrics valid
**Post:** Returns composite score (0-1) weighting attractiveness 50%, sustainability 30%, growth 20%
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `_apply_weight_constraints(weights, min_weight, max_weight) -> Dict[str, float]` (private)
**Pre:** weights non-empty; 0 < min_weight <= max_weight <= 1
**Post:** Returns weights with min/max constraints applied
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Screening validates yield, payout ratio, dividend history
- [ ] **AC-002:** Sustainability score uses payout ratio (ideal 40-60%)
- [ ] **AC-003:** Dividend aristocrat = 25+ years of increases
- [ ] **AC-004:** Portfolio weights respect min/max constraints
- [ ] **AC-005:** Rebalance triggers when weight deviation > threshold
- [ ] **AC-006:** All public methods have complete type hints
- [ ] **AC-007:** NumPy 2.0 compatibility
- [ ] **AC-008:** All functions have docstrings following Google style

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Dividend Investing):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate dividend metrics range | ❌ GAP - No validation |
| Yield screening | Dividend standard | 2-6% ideal yield range | ✅ OK - min/max_yield |
| Payout ratio screening | Arnott & Asness (2003) | < 80% payout ratio | ✅ OK - max_payout_ratio |
| Dividend aristocrat | S&P standard | 25+ years of increases | ✅ OK - Implemented |
| Dividend king | S&P standard | 50+ years of increases | ✅ OK - Implemented |
| Sustainability score | Dividend quality | Payout + FCF + growth + ROE + D/E | ✅ OK - Composite score |
| Attractiveness score | Dividend quality | Yield + growth + sustainability | ✅ OK - Composite score |
| Weight constraints | Risk management | Min/max weight per position | ✅ OK - Implemented |
| Rebalancing threshold | Portfolio management | 5% deviation triggers rebalance | ✅ OK - Implemented |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Arnott & Asness (2003) for dividend investing rules.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_dividend_investing.py:**
  - `test_screen_pass()` - Stock passes all criteria
  - `test_screen_fail_yield()` - Yield below minimum
  - `test_screen_fail_payout()` - Payout ratio too high
  - `test_screen_fail_years()` - Insufficient dividend history
  - `test_dividend_aristocrat()` - 25+ years of increases
  - `test_dividend_king()` - 50+ years of increases
  - `test_sustainability_score()` - Composite score calculation
  - `test_attractiveness_score()` - Yield + growth + sustainability
  - `test_rank_dividend_stocks()` - Sorted by score descending
  - `test_portfolio_construction()` - Weights sum to 1.0
  - `test_weight_constraints()` - Min/max weights enforced
  - `test_rebalance_needed()` - 5% deviation triggers rebalance
  - `test_rebalance_not_needed()` - Small deviation skips rebalance
  - `test_buy_signal()` - High score + undervalued
  - `test_sell_signal()` - Low score + high payout
  - `test_avoid_signal()` - Fails screening

---

## Notes
- **Critical:** High yield (>10%) often indicates yield trap (unsustainable dividend)
- **Arnott & Asness Reference:** "Surprise! Higher Dividends = Higher Earnings Growth" (2003)
- **Dividend Aristocrat:** S&P 500 stock with 25+ consecutive years of dividend increases
- **Dividend King:** Stock with 50+ consecutive years of dividend increases
- **Ideal Yield:** 2-6% (balance between income and sustainability)
- **Ideal Payout Ratio:** 40-60% (room for growth and reinvestment)
- **FCF Payout:** < 70% indicates cash flow coverage
- **Sustainability Score:** Payout (30%) + FCF (30%) + Growth consistency (20%) + ROE (10%) + D/E (10%)
- **Attractiveness Score:** Yield (40%) + Growth (30%) + Sustainability (30%)
- **Weight Constraints:** Min 2%, Max 5% per position (default)
- **Yield-Weighted:** Higher yield stocks get larger base weights
- **Rebalancing:** Triggered by 5% weight deviation from target

---

**File Reference:** `app/domain/strategies/dividend_investing.py`
**Last Audited:** 2026-02-01
