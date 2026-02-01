# strategy_combiner.py

## Purpose
Combine multiple trading strategies with optimal weight allocation using mean-variance, risk parity, regime-dependent, HRP, and Black-Litterman portfolio optimization methods.

---

## Type Definitions / Data Classes

### StrategyCombiner Class
```python
class StrategyCombiner:
    strategies: List[str]                     # REQUIRED - List of strategy names (min 2)
    method: AllocationMethod                  # REQUIRED - Allocation method to use
    min_weight: float                         # REQUIRED - Minimum weight per strategy (0-1)
    max_weight: float                         # REQUIRED - Maximum weight per strategy (0-1)
    rebalance_threshold: float                # REQUIRED - Drift threshold for rebalancing
    current_allocation: Dict[str, Decimal]     # Current strategy weights (as Decimal)
    returns_history: Dict[str, List[float]]    # Historical returns per strategy
```

### AllocationMethod Enum
```python
class AllocationMethod(str, Enum):
    MEAN_VARIANCE = "mean_variance"           # Markowitz optimization
    RISK_PARITY = "risk_parity"               # Equal risk contribution
    EQUAL_WEIGHT = "equal_weight"             # 1/N allocation
    REGIME_DEPENDENT = "regime_dependent"     # Adjust based on market regime
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"  # HRP clustering
    BLACK_LITTERMAN = "black_litterman"       # BL equilibrium + views
```

### StrategyAllocation
```python
@dataclass
class StrategyAllocation:
    strategy: str                             # Strategy name
    weight: Decimal                           # Target weight (0-1)
    target_weight: Decimal                    # Target for rebalancing
    actual_weight: Decimal                    # Current actual weight
    contribution_risk: Decimal                # Risk contribution
    contribution_return: Decimal              # Return contribution
    last_rebalanced: datetime                 # Last rebalance timestamp

    @property
    def drift(self) -> Decimal:               # |actual - target|
    @property
    def needs_rebalance(self) -> bool:        # drift > 0.05
```

### CombinedPortfolio
```python
@dataclass
class CombinedPortfolio:
    total_return: Decimal                     # Annualized return
    volatility: Decimal                       # Annualized volatility
    sharpe_ratio: Decimal                     # Risk-adjusted return
    sortino_ratio: Decimal                    # Downside-adjusted return
    max_drawdown: Decimal                     # Maximum drawdown (negative)
    diversification_ratio: Decimal            # weighted_vol / portfolio_vol
    effective_n_strategies: float             # exp(-sum(w*log(w)))
    correlation_mean: Decimal                 # Average correlation
    allocation: List[StrategyAllocation]      # Strategy allocations
```

---

## Function Signatures (Contracts)

### `__init__(strategies: List[str], method: AllocationMethod, min_weight: float, max_weight: float, rebalance_threshold: float) -> None`
**Pre:** strategies length >= 2, 0 <= min_weight <= max_weight <= 1, 0 < rebalance_threshold <= 1
**Post:** Combiner initialized with equal allocation (1/N each)
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Initializes current_allocation and returns_history dicts

### `calculate_allocation(returns_data: Dict[str, np.ndarray], regime: Optional[MarketRegime]) -> List[StrategyAllocation]`
**Pre:** returns_data has all strategies, each array length >= 2
**Post:** Returns list of StrategyAllocation with weights summing to 1.0, updates current_allocation
**Raises:** ValueError if data missing/invalid, RuntimeError if calculation fails
**Retry:** No
**Side Effects:** Modifies current_allocation

### `_validate_returns_data(returns_data: Dict[str, np.ndarray]) -> None`
**Pre:** None
**Post:** Raises ValueError if data invalid
**Raises:** ValueError if missing strategy, wrong type, or insufficient data
**Retry:** No
**Side Effects:** None

### `_equal_weight_allocation() -> Dict[str, float]`
**Pre:** strategies defined
**Post:** Returns {strategy: 1.0/N for each strategy}
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_mean_variance_allocation(returns_data: Dict[str, np.ndarray]) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays >= 2
**Post:** Returns optimal weights maximizing Sharpe ratio (w = inv_cov @ mu)
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_risk_parity_allocation(returns_data: Dict[str, np.ndarray]) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays >= 2
**Post:** Returns weights proportional to 1/sqrt(diag(cov)) (inverse volatility)
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_regime_dependent_allocation(returns_data: Dict[str, np.ndarray], regime: Optional[MarketRegime]) -> Dict[str, float]`
**Pre:** returns_data valid
**Post:** Returns risk parity weights adjusted by regime factors
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_get_regime_adjustments(regime: MarketRegime) -> Dict[str, float]`
**Pre:** regime is valid MarketRegime enum
**Post:** Returns adjustment factors per strategy type
**Raises:** None (returns 1.0 for unknown strategies)
**Retry:** No
**Side Effects:** None

### `_hierarchical_risk_parity_allocation(returns_data: Dict[str, np.ndarray]) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays >= 2
**Post:** Returns weights based on inverse correlation distance
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_black_litterman_allocation(returns_data: Dict[str, np.ndarray]) -> Dict[str, float]`
**Pre:** returns_data has matching length arrays >= 2
**Post:** Returns equilibrium weights (w = inv_cov @ pi)
**Raises:** None (falls back to equal weights on error)
**Retry:** No
**Side Effects:** None

### `_apply_weight_constraints(weights: Dict[str, float]) -> Dict[str, float]`
**Pre:** weights dict for all strategies
**Post:** Returns weights clipped to [min_weight, max_weight], normalized to sum 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `calculate_portfolio_metrics(allocation: List[StrategyAllocation], returns_data: Dict[str, np.ndarray]) -> CombinedPortfolio`
**Pre:** allocation matches strategies, returns_data valid
**Post:** Returns CombinedPortfolio with annualized metrics (252 trading days)
**Raises:** RuntimeError if calculation fails
**Retry:** No
**Side Effects:** None

### `_calculate_diversification_ratio(allocation: List[StrategyAllocation], returns_data: Dict[str, np.ndarray]) -> Decimal`
**Pre:** allocation and returns_data valid
**Post:** Returns weighted_avg_vol / portfolio_vol (>1 = diversification benefit)
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_effective_number_strategies(weights: np.ndarray) -> float`
**Pre:** weights is numpy array
**Post:** Returns exp(-sum(w * log(w))) for w > 0
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_mean_correlation(returns_data: Dict[str, np.ndarray], weights: np.ndarray) -> Decimal`
**Pre:** returns_data valid, weights matches strategies
**Post:** Returns weighted average of upper triangular correlations
**Raises:** None (returns 0 on error)
**Retry:** No
**Side Effects:** None

### `needs_rebalancing(allocation: List[StrategyAllocation]) -> bool`
**Pre:** allocation is list of StrategyAllocation
**Post:** Returns True if any strategy.drift > 0.05
**Raises:** None
**Retry:** No
**Side Effects:** None

### `rebalance(current_allocation: List[StrategyAllocation], target_allocation: List[StrategyAllocation]) -> Dict[str, Decimal]`
**Pre:** Allocations have same strategies
**Post:** Returns {strategy: target - actual} for trades
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_allocation_summary(allocation: List[StrategyAllocation]) -> Dict[str, Any]`
**Pre:** allocation is list of StrategyAllocation
**Post:** Returns summary dict with statistics
**Raises:** None (returns {} on error)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] At least 2 strategies required for initialization
- [ ] All allocation methods produce weights summing to 1.0
- [ ] Min/max weight constraints applied and enforced
- [ ] Mean-variance uses inverse covariance with regularization (eye * 1e-8)
- [ ] Risk parity uses 1/volatility weighting
- [ ] Regime adjustments applied: TRENDING_UP (trend*1.5, momentum*1.3), RANGING (mean_rev*1.4)
- [ ] HRP uses inverse correlation distance weighting
- [ ] Black-Litterman uses market equilibrium returns
- [ ] Portfolio metrics annualized using 252 trading days
- [ ] Diversification ratio > 1.0 indicates diversification benefit
- [ ] Effective N strategies calculated via entropy formula
- [ ] Rebalance triggered when drift > 5%
- [ ] All methods fall back to equal weights on calculation error
- [ ] Covariance matrix validation with regularization

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix is PSD | ✅ OK - Adds regularization (eye * 1e-8) |
| TRD-003 | BASE_RULES | Position limits enforced | ✅ OK - min/max weight constraints |
| TRD-004 | BASE_RULES | Audit trail for trading decisions | ⚠️ NOT APPLIED - No logging of weight changes |
| TRD-007 | BASE_RULES | Annualization uses TRADING_DAYS = 252 | ✅ OK - Uses 252 for annualization |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Imports from models and portfolio |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X\|None) | ✅ OK - Uses List, Optional |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - Silent fallbacks, no logging |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - Uses None and initializes in __init__ |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy (np, array operations, linalg), decimal (Decimal), typing
- **Internal:** app.ensemble.models (AllocationMethod, CombinedPortfolio, StrategyAllocation), app.models.portfolio (MarketRegime)

---

## Required Tests
- **tests/unit/ensemble/test_strategy_combiner.py:**
  - Test initialization with valid/invalid parameters
  - Test equal weight allocation (1/N)
  - Test mean-variance allocation with valid covariance
  - Test mean-variance fallback on singular matrix
  - Test risk parity allocation (1/vol)
  - Test regime-dependent allocation (TRENDING_UP, RANGING, VOLATILE)
  - Test hierarchical risk parity allocation
  - Test Black-Litterman allocation
  - Test weight constraint application (min/max clipping)
  - Test portfolio metrics calculation (Sharpe, Sortino, drawdown)
  - Test diversification ratio calculation
  - Test effective number of strategies calculation
  - Test mean correlation calculation
  - Test rebalancing trigger at 5% drift
  - Test rebalance trade calculation
  - Test allocation summary output
  - Test edge cases: zero variance, perfect correlation, single strategy

---

## Notes
- Implements Markowitz (1952) mean-variance optimization
- Risk parity equalizes risk contributions across strategies
- HRP uses Lopez de Prado (2016) hierarchical clustering
- Black-Litterman uses Fischer/Black (1990) equilibrium approach
- Regime adjustments are heuristic and should be calibrated with historical data
- Annualization assumes 252 trading days (standard for US equity markets)
- All allocation methods have fallback to equal weights for robustness
