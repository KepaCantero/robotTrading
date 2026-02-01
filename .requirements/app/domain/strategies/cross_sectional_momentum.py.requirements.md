# cross_sectional_momentum.py

## Purpose
Implements cross-sectional momentum (relative strength) strategy where assets are ranked based on past performance and top performers are selected while bottom performers are shorted.

---

## Type Definitions / Data Classes

### MomentumSignal Enum
```python
class MomentumSignal(str, Enum):
    LONG = "long"       # Go long on asset
    SHORT = "short"     # Go short on asset
    NEUTRAL = "neutral" # No position
```

### MomentumAsset DataClass
```python
@dataclass
class MomentumAsset:
    symbol: str               # REQUIRED - Asset symbol
    momentum_score: float     # REQUIRED - Return over lookback period
    rank: int                 # REQUIRED - Cross-sectional rank (1 is best)
    percentile: float         # REQUIRED - Percentile rank (0-1)
    signal: MomentumSignal    # REQUIRED - Generated trading signal
```

**Validation Rules:**
- `momentum_score` must be finite (can be negative)
- `rank` must be positive integer
- `percentile` must be in range [0, 1]
- `symbol` must be non-empty string

### MomentumPortfolio DataClass
```python
@dataclass
class MomentumPortfolio:
    long_positions: Dict[str, float]    # REQUIRED - Symbol -> weight for longs
    short_positions: Dict[str, float]   # REQUIRED - Symbol -> weight for shorts
    cash_weight: float                  # REQUIRED - Weight in cash [0-1]
    rebalance_date: pd.Timestamp         # REQUIRED - Portfolio construction date
```

**Properties:**
- `net_exposure`: Returns long_weight - short_weight
- `gross_exposure`: Returns long_weight + short_weight

**Validation Rules:**
- All weights must be in range [0, 1]
- Sum of long weights <= 1.0
- Sum of short weights <= 1.0
- cash_weight = max(0, 1 - gross_long - gross_short)

### MomentumMetrics DataClass
```python
@dataclass
class MomentumMetrics:
    total_return: float        # REQUIRED - Total portfolio return
    sharpe_ratio: float        # REQUIRED - Risk-adjusted return
    max_drawdown: float        # REQUIRED - Maximum drawdown
    hit_rate: float            # REQUIRED - Percentage of profitable trades
    average_hold_period: float # REQUIRED - Average holding period in days
```

### CrossSectionalMomentum Class
```python
class CrossSectionalMomentum:
    lookback_months: int = 12           # Lookback period for momentum
    top_percentile: float = 0.3         # Top percentile to go long
    bottom_percentile: float = 0.3      # Bottom percentile to short
    long_only: bool = True              # Long-only or long-short
    min_assets: int = 10                # Minimum assets to trade
    max_assets: int = 100               # Maximum assets to trade
    rebalance_frequency: str = "monthly" # Rebalancing frequency
```

**Validation Rules:**
- `lookback_months` must be positive
- `top_percentile` and `bottom_percentile` must be in range [0, 1]
- `min_assets` must be positive and <= `max_assets`
- `max_assets` must be positive
- `rebalance_frequency` must be one of: "monthly", "quarterly", "annual"

---

## Function Signatures (Contracts)

### `calculate_momentum_scores(returns: pd.DataFrame) -> Dict[str, MomentumAsset]`
**Pre:** returns DataFrame has shape (n_assets, n_periods) with n_periods >= 2
**Post:** Returns dictionary mapping symbol to MomentumAsset with computed scores
**Raises:** No exceptions (returns empty dict on error)
**Retry:** No
**Side Effects:** Logs warnings for invalid data

### `construct_portfolio(momentum_assets: Dict[str, MomentumAsset], current_prices: Dict[str, float], total_capital: float) -> MomentumPortfolio`
**Pre:** momentum_assets non-empty, current_prices valid, total_capital > 0
**Post:** Returns MomentumPortfolio with weighted positions
**Raises:** No exceptions
**Retry:** No
**Side Effects:** None

### `should_rebalance(last_rebalance: pd.Timestamp, current_date: pd.Timestamp) -> bool`
**Pre:** Both timestamps are valid
**Post:** Returns True if rebalancing needed based on frequency
**Raises:** No exceptions
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Type hints coverage: 100% of functions have return type hints (AC-TYPE-001)
- [ ] All dataclass fields have validation rules documented
- [ ] Input validation handles empty DataFrames, NaN values
- [ ] Momentum scores handle edge cases (insufficient data, NaN, inf)
- [ ] Portfolio construction respects min_assets and max_assets constraints
- [ ] Weights sum correctly (long + short + cash = 1.0)
- [ ] Rebalancing logic works for monthly, quarterly, annual frequencies
- [ ] No hardcoded trading parameters (all configurable via constructor)
- [ ] Logs warnings for all error conditions (AC-LOG-001)
- [ ] Domain layer purity: no infrastructure imports (AC-ARCH-001)
- [ ] Black formatting compliance (AC-FMT-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` for universal rules

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| ARCH-003 | BASE_RULES.md | No framework imports in domain | ✅ OK |
| LOG-001 | BASE_RULES.md | Structured logging with context | ⚠️ NOT APPLIED - Uses standard logging |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - Logs warnings on errors |
| TRD-005 | BASE_RULES.md | Price/market data validation | ✅ OK - Validates returns DataFrame |
| CC-006 | BASE_RULES.md | Explicit error handling | ⚠️ NOT APPLIED - Returns empty dict instead of raising |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ OK |
| TRD-006 | BASE_RULES.md | Transaction costs considered | ⚠️ NOT APPLIED - Pure ranking, no costs |

**GAP violations found:**
- ❌ GAP LOG-001: Uses standard logging instead of structured logging (priority P1)
  - Impact: Reduced observability in production
  - Recommendation: Use structlog for structured logging

---

## Dependencies
- **External:** numpy, pandas, logging, dataclasses, decimal, enum, typing
- **Internal:** None (pure domain service)

---

## Required Tests
- **test_cross_sectional_momentum.py:**
  - Success paths:
    - `test_calculate_momentum_scores` - Correctly ranks assets by returns
    - `test_construct_long_only_portfolio` - Creates equal-weight long portfolio
    - `test_construct_long_short_portfolio` - Creates long-short portfolio
    - `test_monthly_rebalancing` - Detects when monthly rebalance needed
    - `test_quarterly_rebalancing` - Detects when quarterly rebalance needed
  - Error paths:
    - `test_empty_returns_dataframe` - Returns empty dict for empty input
    - `test_insufficient_columns` - Returns empty dict when columns < 2
    - `test_nan_values_handling` - Handles NaN values with forward/backward fill
    - `test_inf_values_handling` - Replaces inf values with 0
  - Edge cases:
    - `test_percentile_bounds` - Ensures percentile always in [0, 1]
    - `test_min_assets_constraint` - Respects min_assets when available
    - `test_max_assets_constraint` - Limits to max_assets when many available
    - `test_weight_summation` - Verifies long + short + cash = 1.0
    - `test_net_exposure_calculation` - Correctly calculates net exposure
    - `test_gross_exposure_calculation` - Correctly calculates gross exposure

---

## Notes
Reference: Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers" - Classic 3-12 month momentum implementation with robust NaN/inf handling.
