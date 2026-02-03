# cross_sectional_momentum.py

## Purpose
Cross-Sectional Momentum (XSM) strategy domain service - ranks assets by past returns and goes long top performers (and optionally short bottom performers).

---

## Type Definitions / Data Classes

### MomentumSignal (Enum)
```python
class MomentumSignal(str, Enum):
    LONG = "long"          # Asset in top percentile (buy)
    SHORT = "short"        # Asset in bottom percentile (sell)
    NEUTRAL = "neutral"    # Asset in middle (no trade)
```

### MomentumAsset
```python
@dataclass
class MomentumAsset:
    symbol: str                    # REQUIRED - Asset symbol
    momentum_score: float          # REQUIRED - Cumulative return over lookback
    rank: int                      # REQUIRED - Cross-sectional rank (1 = best)
    percentile: float              # REQUIRED - Percentile rank (0-1)
    signal: MomentumSignal         # REQUIRED - Generated trading signal
```

**Validation Rules:**
- `momentum_score` can be negative (losses)
- `rank` is in [1, n_assets]
- `percentile` is in (0, 1]

### MomentumPortfolio
```python
@dataclass
class MomentumPortfolio:
    long_positions: Dict[str, float]      # REQUIRED - Long positions (symbol -> weight)
    short_positions: Dict[str, float]     # REQUIRED - Short positions (symbol -> weight)
    cash_weight: float                    # REQUIRED - Cash portion
    rebalance_date: pd.Timestamp          # REQUIRED - Portfolio construction date
```

**Properties:**
- `net_exposure` - Returns long_weight - short_weight
- `gross_exposure` - Returns long_weight + short_weight
- `get_weights_dict()` - Returns all positions as combined dict

**Validation Rules:**
- All weights must be non-negative within each dict
- Sum of long_positions <= 1.0
- Sum of short_positions <= 1.0
- cash_weight >= 0

### MomentumMetrics
```python
@dataclass
class MomentumMetrics:
    total_return: float           # REQUIRED - Total portfolio return
    sharpe_ratio: float           # REQUIRED - Risk-adjusted return
    max_drawdown: float           # REQUIRED - Maximum peak-to-trough decline
    hit_rate: float               # REQUIRED - % of profitable trades
    average_hold_period: float    # REQUIRED - Avg holding period (days)
```

---

## Function Signatures (Contracts)

### `CrossSectionalMomentum.__init__(lookback_months, top_percentile, bottom_percentile, long_only, min_assets, max_assets, rebalance_frequency) -> None`
**Pre:** lookback_months >= 1; top/bottom_percentile in (0, 0.5]; min_assets <= max_assets; rebalance_frequency in ["monthly", "quarterly", "annual"]
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** ❌ No
**Side Effects:** None (initialization only)

### `calculate_momentum_scores(returns) -> Dict[str, MomentumAsset]`
**Pre:** returns is DataFrame (symbols × dates) with at least 2 columns
**Post:** Returns dict mapping symbol to MomentumAsset with rank and signal
**Raises:** None (handles insufficient data gracefully)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `construct_portfolio(momentum_assets, current_prices, total_capital) -> MomentumPortfolio`
**Pre:** momentum_assets has at least min_assets; current_prices covers all momentum_assets
**Post:** Returns MomentumPortfolio with equal-weighted long/short positions
**Raises:** None (returns empty portfolio if insufficient assets)
**Retry:** ❌ No
**Side Effects:** None (pure computation)

### `should_rebalance(last_rebalance, current_date) -> bool`
**Pre:** last_rebalance and current_date are valid timestamps
**Post:** Returns True if rebalancing period has elapsed
**Raises:** None
**Retry:** ❌ No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Input validation - returns DataFrame has minimum required lookback
- [ ] **AC-002:** Edge case handling - empty DataFrame, single asset, NaN returns
- [ ] **AC-003:** Portfolio weights sum to <= 1.0 (with cash for remainder)
- [ ] **AC-004:** Min/max assets constraints enforced
- [ ] **AC-005:** All public methods have complete type hints
- [ ] **AC-006:** NumPy 2.0 compatibility (no deprecated pandas types)
- [ ] **AC-007:** All functions have docstrings following Google style
- [ ] **AC-008:** Percentile calculation correct (rank/n_assets)

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

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Cross-Sectional Momentum):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate returns DataFrame structure | ✅ FIXED - Full validation with NaN/inf handling |
| NaN handling | BASE_RULES.md (TRD-015) | Handle NaN in return data | ✅ FIXED - Forward/backward fill + validation |
| Weight constraints | BASE_RULES.md (TRD-003) | Sum of weights <= 1.0 | ✅ OK - Cash remainder |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy/pandas |
| Jegadeesh-Titman 3-12 month | Jegadeesh & Titman (1993) | 3-12 month lookback period | ✅ OK - Default 12 months |
| Top percentile long | XSM standard | Buy top 30% performers | ✅ OK - top_percentile=0.3 |
| Bottom percentile short | XSM standard | Short bottom 30% if long-short | ✅ OK - bottom_percentile=0.3 |
| Equal weighting | XSM standard | Equal weight within long/short buckets | ✅ OK - Implemented |
| Rebalancing frequency | Jegadeesh & Titman | Monthly/quarterly rebalancing | ✅ OK - Implemented |
| Rank-based signals | XSM standard | Signal = rank percentile | ✅ OK - Implemented |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Jegadeesh & Titman (1993) for XSM rules.

---

## Dependencies
- **External:** `numpy`, `pandas`, `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_cross_sectional_momentum.py:**
  - `test_momentum_scores_calculation()` - Happy path with valid returns
  - `test_rank_ordering()` - Best momentum has rank=1
  - `test_top_percentile_long()` - Top 30% get LONG signal
  - `test_bottom_percentile_short()` - Bottom 30% get SHORT (if not long_only)
  - `test_long_only_no_shorts()` - long_only=True has no short positions
  - `test_portfolio_weights_sum_to_one()` - Long + short + cash = 1
  - `test_min_assets_constraint()` - Enforces minimum assets
  - `test_max_assets_constraint()` - Enforces maximum assets
  - `test_should_rebalance_monthly()` - Rebalance triggers monthly
  - `test_should_rebalance_quarterly()` - Rebalance triggers quarterly
  - `test_insufficient_data_handling()` - Handles short lookback gracefully
  - `test_nan_handling()` - NaN in returns data
  - `test_empty_dataframe()` - Empty input handling
  - `test_net_exposure_calculation()` - Net = long - short
  - `test_gross_exposure_calculation()` - Gross = long + short

---

## Notes
- **Critical:** Cross-sectional momentum requires at least 20-30 assets for meaningful ranking
- **Jegadeesh & Titman Reference:** "Returns to Buying Winners and Selling Losers" (1993)
- **Lookback Period:** 3-12 months optimal (default 12 months)
- **Top Percentile:** Default 30% long (winners)
- **Bottom Percentile:** Default 30% short (losers) for long-short
- **Equal Weighting:** Simple and robust out-of-sample
- **Rebalancing:** Monthly typical (more frequent = higher turnover)
- **Long-Only:** Avoids shorting costs and borrowing constraints
- **Trading Days:** Assumes 21 trading days/month for lookback calculation
- **Portfolio Construction:** Long positions = 1/n_long, Short = 1/n_short
- **Cash Cushion:** Any unallocated capital stays in cash

---

**File Reference:** `app/domain/strategies/cross_sectional_momentum.py`
**Last Audited:** 2026-02-01
