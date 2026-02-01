# low_volatility_anomaly.py

## Purpose
Low Volatility Anomaly strategy domain service - exploits the empirical finding that low-volatility stocks tend to deliver higher risk-adjusted returns.

---

## Type Definitions / Data Classes

### VolatilityCategory (Enum)
```python
class VolatilityCategory(str, Enum):
    LOW_VOLATILITY = "low_volatility"      # Bottom 30% by volatility
    MEDIUM_VOLATILITY = "medium_volatility"  # Middle 40%
    HIGH_VOLATILITY = "high_volatility"    # Top 30%
```

### VolatilityMetrics
```python
@dataclass
class VolatilityMetrics:
    symbol: str                    # REQUIRED - Stock symbol
    daily_volatility: float        # REQUIRED - Standard deviation of daily returns
    annualized_volatility: float   # REQUIRED - Annualized volatility (daily × √252)
    beta: float                    # REQUIRED - Market beta (cov/var_market)
    idiosyncratic_volatility: float # REQUIRED - Stock-specific volatility
    downside_deviation: float      # REQUIRED - Downside risk (std of negative returns)
    max_drawdown: float            # REQUIRED - Maximum historical drawdown
    sharpe_ratio: float            # REQUIRED - Risk-adjusted return
    sortino_ratio: float           # REQUIRED - Downside-adjusted return
    percentile_rank: float         # REQUIRED - Volatility rank (0-1)
```

**Properties:**
- `volatility_category` - Returns LOW_VOLATILITY if rank <= 0.3, HIGH_VOLATILITY if rank >= 0.7
- `is_low_volatility` - Returns True if percentile_rank <= 0.3
- `risk_adjusted_score` - Returns score (0-1) combining Sharpe (70%) and inverse volatility (30%)

### LowVolatilityPortfolio
```python
@dataclass
class LowVolatilityPortfolio:
    positions: Dict[str, float]    # REQUIRED - Symbol -> weight
    portfolio_volatility: float    # REQUIRED - Weighted average volatility
    portfolio_beta: float          # REQUIRED - Weighted average beta
    portfolio_sharpe: float        # REQUIRED - Expected portfolio Sharpe ratio
    volatility_exposure: float     # REQUIRED - Exposure to volatility factor
```

**Properties:**
- `is_low_vol_portfolio` - Returns True if portfolio_volatility < 0.15 (15% annual)
- `get_volatility_breakdown()` - Returns dict with total_volatility, market_beta, sharpe_ratio

---

## Function Signatures (Contracts)

### `LowVolatilityAnomaly.__init__(low_vol_threshold, max_beta, max_volatility, min_sharpe, rebalance_frequency, weighting_method) -> None`
**Pre:** low_vol_threshold in (0, 1]; max_beta > 0; max_volatility > 0; min_sharpe >= 0; weighting_method in ["inverse_variance", "min_variance", "equal_weight"]
**Post:** Strategy configured with parameters
**Raises:** None (initialization only)
**Retry:** No
**Side Effects:** None (initialization only)

### `calculate_volatility_metrics(returns, market_returns, risk_free_rate) -> VolatilityMetrics`
**Pre:** returns and market_returns are non-empty arrays; risk_free_rate >= 0
**Post:** Returns VolatilityMetrics with daily vol, annual vol (×√252), beta, idiosyncratic vol, downside deviation, max drawdown, Sharpe, Sortino
**Raises:** None (handles edge cases with defaults)
**Retry:** No
**Side Effects:** None (pure computation)

### `screen_low_volatility_stocks(volatility_metrics) -> List[str]`
**Pre:** volatility_metrics is dict of symbol -> VolatilityMetrics
**Post:** Returns list of symbols passing screening (rank <= 0.3, vol <= 25%, beta <= 0.8, Sharpe >= 0.5)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_passes_screen(metrics) -> bool` (private)
**Pre:** metrics valid
**Post:** Returns True if percentile_rank <= 0.3, annualized_volatility <= 0.25, beta <= 0.8, sharpe_ratio >= 0.5
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `rank_low_volatility_stocks(volatility_metrics) -> List[Tuple[str, float]]`
**Pre:** volatility_metrics is dict of symbol -> VolatilityMetrics
**Post:** Returns list of (symbol, score) sorted by risk_adjusted_score (descending)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `construct_portfolio(volatility_metrics, capital, max_positions, min_weight, max_weight) -> LowVolatilityPortfolio`
**Pre:** volatility_metrics non-empty; capital > 0; max_positions >= 1; 0 < min_weight <= max_weight <= 1
**Post:** Returns low volatility portfolio with weights summing to 1.0
**Raises:** None (returns empty portfolio if no stocks pass screen)
**Retry:** No
**Side Effects:** None (pure computation)

### `_inverse_variance_weights(selected, volatility_metrics) -> Dict[str, float]` (private)
**Pre:** selected non-empty; volatility_metrics has all selected symbols
**Post:** Returns weights proportional to 1/variance for each stock
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_minimum_variance_weights(selected, volatility_metrics) -> Dict[str, float]` (private)
**Pre:** selected non-empty; volatility_metrics has all selected symbols
**Post:** Returns weights proportional to 1/volatility (inverse volatility weighting)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `_apply_weight_constraints(weights, min_weight, max_weight) -> Dict[str, float]` (private)
**Pre:** weights non-empty; 0 < min_weight <= max_weight <= 1
**Post:** Returns weights with min/max constraints applied
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

### `calculate_volatility_premium(volatility_metrics, returns) -> Tuple[float, float, float]`
**Pre:** volatility_metrics and returns have matching symbols
**Post:** Returns (low_vol_return, medium_vol_return, high_vol_return) comparing returns by volatility category
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

---

## Acceptance Criteria
- [ ] **AC-001:** Annualized volatility = daily_volatility × √252
- [ ] **AC-002:** Beta = covariance(returns, market) / variance(market)
- [ ] **AC-003:** Idiosyncratic volatility = std(returns - beta × market_returns)
- [ ] **AC-004:** Downside deviation = std(negative returns only)
- [ ] **AC-005:** Max drawdown = min((cumulative - running_max) / running_max)
- [ ] **AC-006:** Sharpe ratio = (mean_return × 252 - rf) / annual_volatility
- [ ] **AC-007:** Sortino ratio = (mean_return × 252 - rf) / (downside_dev × √252)
- [ ] **AC-008:** Inverse variance weights ∝ 1/σ²
- [ ] **AC-009:** All public methods have complete type hints
- [ ] **AC-010:** NumPy 2.0 compatibility

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Low Volatility Anomaly):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Input validation | BASE_RULES.md (CC-006) | Validate returns array length | ✅ OK - Checks array length |
| NaN handling | BASE_RULES.md (TRD-015) | Handle NaN in return data | ✅ FIXED - Filters NaN with logging |
| Low vol anomaly | Blitz & van Vliet (2007) | Low vol stocks outperform on risk-adjusted basis | ✅ OK - Strategy |
| Volatility percentile | Low vol standard | Bottom 30% = low vol | ✅ OK - low_vol_threshold=0.3 |
| Annualization | Finance standard | Multiply daily by √252 | ✅ OK - Implemented |
| Beta calculation | CAPM | β = Cov(r, rm) / Var(rm) | ✅ OK - Implemented |
| Idiosyncratic vol | Factor models | σᵢ = std(εᵢ) where εᵢ = rᵢ - βᵢ×rm | ✅ OK - Implemented |
| Downside deviation | Risk metrics | std of negative returns only | ✅ OK - Implemented |
| Max drawdown | Risk metrics | max peak-to-trough decline | ✅ OK - Implemented |
| Sharpe ratio | Sharpe (1966) | (r - rf) / σ | ✅ OK - Implemented |
| Sortino ratio | Sortino & Knight (1995) | (r - rf) / σ_downside | ✅ OK - Implemented |
| Inverse variance weights | Risk parity | wᵢ ∝ 1/σᵢ² | ✅ OK - _inverse_variance_weights |
| Min variance weights | MVO | Approximated by inverse vol | ✅ OK - _minimum_variance_weights |
| Weight constraints | Risk management | Min/max position limits | ✅ OK - _apply_weight_constraints |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports | ✅ OK - Only numpy |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ✅ OK - Modern types |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Baker et al. (2011), Blitz & van Vliet (2007) for low volatility anomaly rules.

---

## Dependencies
- **External:** `numpy`, `dataclasses` (std), `decimal` (std), `enum` (std)
- **Internal:** None (domain service)

---

## Required Tests
- **test_low_volatility_anomaly.py:**
  - `test_volatility_metrics_calculation()` - Daily, annual, beta, idiosyncratic
  - `test_annualized_volatility()` - daily × √252
  - `test_beta_calculation()` - Cov / Var
  - `test_idiosyncratic_volatility()` - Residual volatility
  - `test_downside_deviation()` - Std of negative returns only
  - `test_max_drawdown()` - Peak-to-trough calculation
  - `test_sharpe_ratio()` - (r - rf) / σ
  - `test_sortino_ratio()` - (r - rf) / σ_downside
  - `test_percentile_rank()` - Volatility ranking
  - `test_volatility_category()` - Rank mapping to category
  - `test_risk_adjusted_score()` - Sharpe + inverse vol
  - `test_screen_low_volatility()` - Filter by rank, vol, beta, Sharpe
  - `test_inverse_variance_weights()` - w ∝ 1/σ²
  - `test_min_variance_weights()` - w ∝ 1/σ
  - `test_portfolio_construction()` - Weights sum to 1.0
  - `test_volatility_premium()` - Low vs medium vs high vol returns
  - `test_zero_variance_handling()` - Handles zero variance
  - `test_empty_market_returns()` - Defaults beta to 1.0

---

## Notes
- **Critical:** Low volatility anomaly contradicts CAPM (which predicts higher return for higher risk)
- **Baker et al. Reference:** "Betas vs. Fama-French Factors: Evidence from the NYSE" (2011)
- **Blitz & van Vliet Reference:** "The Volatility Effect" (2007)
- **Low Vol Anomaly:** Low-beta stocks deliver similar returns with lower volatility
- **Volatility Percentile:** Bottom 30% = low vol, middle 40% = medium, top 30% = high
- **Annualization Factor:** √252 (assuming 252 trading days per year)
- **Beta (β):** Measures systematic risk/market sensitivity
- **Idiosyncratic Volatility:** Stock-specific volatility (unexplained by market)
- **Downside Deviation:** Risk measure considering only negative returns
- **Max Drawdown:** Maximum peak-to-trough decline in cumulative returns
- **Sharpe Ratio:** (Annual return - Risk-free rate) / Annual volatility
- **Sortino Ratio:** (Annual return - Risk-free rate) / (Downside deviation × √252)
- **Risk-Adjusted Score:** 70% normalized Sharpe + 30% inverse volatility
- **Screening Criteria:** Bottom 30% volatility, ≤ 25% annual vol, ≤ 0.8 beta, ≥ 0.5 Sharpe
- **Inverse Variance Weights:** wᵢ = (1/σᵢ²) / Σ(1/σⱼ²)
- **Minimum Variance Weights:** Approximated by inverse volatility wᵢ = (1/σᵢ) / Σ(1/σⱼ)
- **Equal Weights:** wᵢ = 1/N for all N stocks
- **Volatility Exposure:** Negative (-0.5) because portfolio shorts volatility factor
- **Rebalancing:** Monthly recommended (volatility regime changes slowly)

---

**File Reference:** `app/domain/strategies/low_volatility_anomaly.py`
**Last Audited:** 2026-02-01
