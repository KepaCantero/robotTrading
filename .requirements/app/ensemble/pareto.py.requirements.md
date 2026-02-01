# pareto.py

## Purpose
Implement NSGA-II (Non-dominated Sorting Genetic Algorithm II) for multi-objective optimization of strategy weights across return, risk, Sharpe, Sortino, drawdown, and diversification objectives.

---

## Type Definitions / Data Classes

### ParetoFrontOptimizer Class
```python
class ParetoFrontOptimizer:
    strategies: List[str]                     # REQUIRED - Strategy names (min 2)
    objective_config: ObjectiveConfig         # REQUIRED - Objectives and weights configuration
    population_size: int                      # REQUIRED - GA population size (min 10)
    mutation_rate: float                      # REQUIRED - Mutation probability (0-1)
    crossover_rate: float                     # REQUIRED - Crossover probability (0-1)
    random: random.Random                     # Random number generator instance
```

### ParetoSolution
```python
@dataclass
class ParetoSolution:
    strategy_weights: Dict[str, Decimal]     # REQUIRED - Weights summing to 1.0
    objective_values: Dict[str, float]        # REQUIRED - Objective function results
    rank: int                                 # Pareto rank (0 = non-dominated)
    crowding_distance: float                  # Diversity metric (higher = better)
    metrics: Dict[str, float]                 # Additional performance metrics
    timestamp: datetime                       # Solution creation timestamp

    @property
    def dominates(self) -> bool:              # rank == 0
    @property
    def is_diverse(self) -> bool:             # crowding_distance > 0.5
```

### OptimizationObjective (Enum)
```python
class OptimizationObjective(str, Enum):
    MAXIMIZE_RETURN = "maximize_return"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_SORTINO = "maximize_sortino"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_DIVERSIFICATION = "maximize_diversification"
```

---

## Function Signatures (Contracts)

### `__init__(strategies: List[str], objective_config: ObjectiveConfig, population_size: int, mutation_rate: float, crossover_rate: float) -> None`
**Pre:** strategies length >= 2, population_size >= 10, 0 <= mutation_rate <= 1, 0 <= crossover_rate <= 1
**Post:** Optimizer initialized with validated parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates random.Random instance

### `optimize(returns_data: Dict[str, np.ndarray], risk_data: Optional[Dict[str, np.ndarray]], generations: int, seed: Optional[int]) -> List[ParetoSolution]`
**Pre:** returns_data has all strategies, each array length >= 2, generations >= 1
**Post:** Returns Pareto front (rank 0 solutions) from final population
**Raises:** ValueError if data invalid, RuntimeError if optimization fails
**Retry:** No
**Side Effects:** Sets random seeds if seed provided

### `_validate_optimization_data(returns_data: Dict[str, np.ndarray], risk_data: Optional[Dict[str, np.ndarray]]) -> None`
**Pre:** None
**Post:** Raises ValueError if data missing, wrong type, or insufficient
**Raises:** ValueError for validation failures
**Retry:** No
**Side Effects:** None

### `_initialize_population() -> List[Dict[str, float]]`
**Pre:** strategies defined
**Post:** Returns list of weight allocations using Dirichlet distribution (sum to 1.0)
**Raises:** None
**Retry:** No
**Side Effects:** Uses np.random.dirichlet for valid distributions

### `_evaluate_population(population: List[Dict[str, float]], returns_data: Dict[str, np.ndarray], risk_data: Optional[Dict[str, np.ndarray]]) -> List[ParetoSolution]`
**Pre:** population is list of weight dicts summing to 1.0
**Post:** Returns list of ParetoSolutions with calculated objective_values
**Raises:** None (skips invalid solutions)
**Retry:** No
**Side Effects:** None

### `_calculate_objectives(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray], risk_data: Optional[Dict[str, np.ndarray]]) -> Dict[str, float]`
**Pre:** allocation sums to 1.0, returns_data valid
**Post:** Returns dict of objective values for each configured objective
**Raises:** None (returns 0.0 for failed calculations)
**Retry:** No
**Side Effects:** None

### `_calculate_portfolio_return(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray]) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized portfolio return (mean * 252)
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_portfolio_risk(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray]) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized portfolio volatility (std * sqrt(252))
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_downside_risk(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray]) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized downside deviation (std of negative returns * sqrt(252))
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_max_drawdown(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray]) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns maximum drawdown as positive value
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_diversification_ratio(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray]) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns weighted_avg_vol / portfolio_vol (>1 = diversification benefit)
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_metrics(allocation: Dict[str, float], returns_data: Dict[str, np.ndarray], risk_data: Optional[Dict[str, np.ndarray]]) -> Dict[str, float]`
**Pre:** allocation and returns_data valid
**Post:** Returns dict with skewness, kurtosis, var_95, expected_shortfall
**Raises:** None (returns {} on error)
**Retry:** No
**Side Effects:** None

### `_calculate_skewness(returns: np.ndarray) -> float`
**Pre:** returns is numpy array
**Post:** Returns skewness using scipy.stats.skew
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_kurtosis(returns: np.ndarray) -> float`
**Pre:** returns is numpy array
**Post:** Returns kurtosis using scipy.stats.kurtosis (fisher=False)
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_non_dominated_sort(population: List[ParetoSolution]) -> List[List[ParetoSolution]]`
**Pre:** population is list of ParetoSolutions with objective_values
**Post:** Returns list of fronts where front[0] = non-dominated solutions (rank 0)
**Raises:** None
**Retry:** No
**Side Effects:** Updates solution ranks in-place via model_copy

### `_dominates(solution1: ParetoSolution, solution2: ParetoSolution) -> bool`
**Pre:** Both solutions have objective_values
**Post:** Returns True if solution1 is better in all objectives and strictly better in at least one
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_crowding_distance(fronts: List[List[ParetoSolution]]) -> None`
**Pre:** fronts is list of solution lists
**Post:** Updates crowding_distance for all solutions (boundary = inf, interior = normalized distance)
**Raises:** None
**Retry:** No
**Side Effects:** Modifies solutions in-place via model_copy

### `_create_offspring(population: List[ParetoSolution]) -> List[ParetoSolution]`
**Pre:** population is list of ParetoSolutions
**Post:** Returns offspring with tournament selection, SBX crossover, and polynomial mutation
**Raises:** None
**Retry:** No
**Side Effects:** Uses random for selection/crossover/mutation

### `_tournament_selection(population: List[ParetoSolution], tournament_size: int = 2) -> ParetoSolution`
**Pre:** population not empty
**Post:** Returns best solution from tournament (lowest rank, highest crowding distance)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_crossover(parent1: Dict[str, Decimal], parent2: Dict[str, Decimal]) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]`
**Pre:** parents have same strategies with valid weights
**Post:** Returns two children using Simulated Binary Crossover (SBX, eta=20)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_mutate(weights: Dict[str, Decimal]) -> Dict[str, Decimal]`
**Pre:** weights is strategy -> Decimal mapping summing to 1.0
**Post:** Returns mutated weights using polynomial mutation (eta=20), normalized to sum 1.0
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_select_new_population(combined: List[ParetoSolution]) -> List[ParetoSolution]`
**Pre:** combined has parent + offspring populations
**Post:** Returns selected population of size population_size using NSGA-II selection
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] NSGA-II algorithm correctly implements non-dominated sorting
- [ ] Non-dominated sort assigns rank 0 to Pareto front (non-dominated solutions)
- [ ] Crowding distance promotes diversity in the Pareto front
- [ ] Tournament selection uses (rank, -crowding_distance) as sorting key
- [ ] SBX crossover uses eta = 20 for real-valued encoding
- [ ] Polynomial mutation uses eta = 20
- [ ] All weights normalized to sum to 1.0 after crossover and mutation
- [ ] Portfolio return annualized using 252 trading days
- [ ] Portfolio risk annualized using sqrt(252) factor
- [ ] Max drawdown calculated from cumulative returns peak-to-trough
- [ ] Diversification ratio = weighted_avg_vol / portfolio_vol
- [ ] VaR 95% calculated as 5th percentile of returns
- [ ] Expected Shortfall calculated as mean of returns below VaR
- [ ] All objective calculations handle edge cases (zero variance, empty data)
- [ ] Population initialization uses Dirichlet distribution for valid weights

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix | ✅ OK - Portfolio risk uses np.cov which handles PSD |
| TRD-002 | BASE_RULES | Validate orders | ⚠️ NOT APPLIED - No order execution |
| TRD-007 | BASE_RULES | Document TRADING_DAYS = 252 | ✅ OK - Uses 252 for annualization |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Only imports from models |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X\|None) | ✅ OK - Uses List, Optional, Tuple |
| LOG-004 | BASE_RULES | Log exceptions with stack traces | ❌ GAP - Logs generation errors without stack traces |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - All defaults are immutable |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy (np, array operations, linalg, random), random (Random), decimal (Decimal), typing, scipy.stats (skew, kurtosis)
- **Internal:** app.ensemble.models (ObjectiveConfig, OptimizationObjective, ParetoSolution)

---

## Required Tests
- **tests/unit/ensemble/test_pareto_optimizer.py:**
  - Test optimizer initialization with valid parameters
  - Test optimizer initialization with invalid parameters (errors)
  - Test optimization returns Pareto front (rank 0 solutions)
  - Test non-dominated sorting correctness
  - Test domination comparison logic
  - Test crowding distance calculation
  - Test tournament selection
  - Test SBX crossover produces valid weights summing to 1.0
  - Test polynomial mutation produces valid weights
  - Test population selection preserves best solutions
  - Test portfolio return calculation and annualization
  - Test portfolio risk calculation and annualization
  - Test downside risk calculation
  - Test max drawdown calculation
  - Test diversification ratio calculation
  - Test additional metrics (skewness, kurtosis, VaR, Expected Shortfall)
  - Test objective calculation for all 6 objective types
  - Test random seed produces reproducible results
  - Test edge cases: single objective, zero variance, empty population

---

## Notes
- NSGA-II algorithm from Deb et al. (2002) - "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II"
- SBX (Simulated Binary Crossover) uses eta = 20 for distribution index
- Polynomial mutation uses eta = 20 for distribution index
- Annualization assumes 252 trading days (standard for US equity markets)
- Tolerance parameter in ObjectiveConfig handles numerical precision in dominance comparison
- Boundary solutions in Pareto front get infinite crowding distance
- All weight allocations are normalized to sum to 1.0 after genetic operations
