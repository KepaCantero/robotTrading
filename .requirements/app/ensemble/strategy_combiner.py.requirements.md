# strategy_combiner.py

## Purpose
Combine multiple trading strategies with optimal weight allocation using mean-variance, risk parity, regime-dependent, and other portfolio optimization methods.

---

## Type Definitions / Data Classes

### StrategyCombiner Class
```python
class StrategyCombiner:
    strategies: List[str]                     # List of strategy names (min 2)
    method: AllocationMethod                  # Allocation method to use
    min_weight: float                         # Minimum weight per strategy
    max_weight: float                         # Maximum weight per strategy
    rebalance_threshold: float                # Drift threshold for rebalancing
    current_allocation: Dict[str, Decimal]     # Current strategy weights
    returns_history: Dict[str, List[float]]    # Historical returns per strategy
```

---

## Function Signatures (Contracts)

### `__init__(strategies, method, min_weight, max_weight, rebalance_threshold) -> None`
**Pre:** strategies length >= 2, 0 <= min_weight <= max_weight <= 1
**Post:** Combiner initialized with equal allocation
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Initializes allocation and returns history

### `calculate_allocation(returns_data, regime) -> List[StrategyAllocation]`
**Pre:** returns_data has all strategies, each array length >= 2
**Post:** Returns list of StrategyAllocation with weights summing to 1.0
**Raises:** ValueError if data missing/invalid, RuntimeError if calculation fails
**Retry:** No
**Side Effects:** Updates current_allocation

### `_mean_variance_allocation(returns_data) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays
**Post:** Returns optimal weights maximizing Sharpe ratio
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_risk_parity_allocation(returns_data) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays
**Post:** Returns weights proportional to 1/volatility
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_regime_dependent_allocation(returns_data, regime) -> Dict[str, float]`
**Pre:** returns_data valid
**Post:** Returns risk parity weights adjusted for regime
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_hierarchical_risk_parity_allocation(returns_data) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays
**Post:** Returns weights based on correlation distance
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_black_litterman_allocation(returns_data) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays
**Post:** Returns equilibrium-based weights
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `calculate_portfolio_metrics(allocation, returns_data) -> CombinedPortfolio`
**Pre:** allocation matches strategies, returns_data valid
**Post:** Returns portfolio metrics (return, vol, Sharpe, Sortino, drawdown)
**Raises:** RuntimeError if calculation fails
**Retry:** No
**Side Effects:** None

### `_calculate_diversification_ratio(allocation, returns_data) -> Decimal`
**Pre:** allocation and returns_data valid
**Post:** Returns weighted_avg_vol / portfolio_vol
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_effective_number_strategies(weights: np.ndarray) -> float`
**Pre:** weights is numpy array
**Post:** Returns exp(-sum(w * log(w)))
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `needs_rebalancing(allocation) -> bool`
**Pre:** allocation is list of StrategyAllocation
**Post:** Returns True if any strategy drift > 5%
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rebalance(current_allocation, target_allocation) -> Dict[str, Decimal]`
**Pre:** Allocations have same strategies
**Post:** Returns trades needed (positive = buy, negative = sell)
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] At least 2 strategies required
- [ ] Weights sum to 1.0 (normalization enforced)
- [ ] Min/max weight constraints applied
- [ ] Mean-variance uses inverse covariance matrix
- [ ] Risk parity uses 1/volatility weighting
- [ ] Regime adjustments: trend_up (trend*1.5), range (mean_rev*1.4)
- [ ] Portfolio metrics include Sharpe, Sortino, max drawdown
- [ ] Diversification ratio > 1 indicates benefit
- [ ] Effective N strategies calculated via entropy
- [ ] Rebalance triggered at 5% drift threshold

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix | ✅ OK - Adds regularization (eye * 1e-8) |
| TRD-003 | BASE_RULES | Position limits enforced | ✅ OK - min/max weight constraints |
| TRD-004 | BASE_RULES | Audit trail | ⚠️ NOT APPLIED - No logging of trades |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Imports from models and portfolio |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ PARTIAL - Logs on fallback, no stack traces |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |

---

## Dependencies
- **External:** numpy (np), decimal (Decimal), typing
- **Internal:** app.ensemble.models (AllocationMethod, CombinedPortfolio, StrategyAllocation), app.models.portfolio (MarketRegime)

---

## Required Tests
- **tests/ensemble/test_strategy_combiner.py:**
  - Test equal weight allocation
  - Test mean-variance allocation with valid data
  - Test mean-variance fallback on singular matrix
  - Test risk parity allocation
  - Test regime-dependent allocation adjustments
  - Test hierarchical risk parity allocation
  - Test Black-Litterman allocation
  - Test weight constraint application (min/max)
  - Test portfolio metrics calculation
  - Test diversification ratio calculation
  - Test effective number of strategies
  - Test rebalancing trade calculation
  - Test edge cases: single strategy, zero variance, correlation = 1

---

## Notes
Uses Markowitz (1952) mean-variance optimization. Risk parity equalizes risk contributions. Regime adjustments are heuristic and should be calibrated. Annualization assumes 252 trading days.
