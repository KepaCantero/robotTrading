# pareto.py

## Purpose
Implement NSGA-II genetic algorithm for multi-objective optimization of strategy weights across return, risk, Sharpe, and other objectives.

---

## Type Definitions / Data Classes

### ParetoFrontOptimizer Class
```python
class ParetoFrontOptimizer:
    strategies: List[str]                     # Strategy names (min 2)
    objective_config: ObjectiveConfig         # Objectives and weights
    population_size: int                      # GA population size (min 10)
    mutation_rate: float                      # Mutation probability (0-1)
    crossover_rate: float                     # Crossover probability (0-1)
    random: random.Random                     # Random number generator
```

---

## Function Signatures (Contracts)

### `__init__(strategies, objective_config, population_size, mutation_rate, crossover_rate) -> None`
**Pre:** strategies length >= 2, population_size >= 10, rates in [0,1]
**Post:** Optimizer initialized with validated parameters
**Raises:** ValueError if parameters invalid
**Retry:** No
**Side Effects:** Creates random.Random instance

### `optimize(returns_data, risk_data, generations, seed) -> List[ParetoSolution]`
**Pre:** returns_data has all strategies, each array length >= 2
**Post:** Returns Pareto front (rank 0 solutions) sorted by crowding
**Raises:** ValueError if data invalid, RuntimeError if optimization fails
**Retry:** No
**Side Effects:** Sets random seeds if provided

### `_validate_optimization_data(returns_data, risk_data) -> None`
**Pre:** None
**Post:** Raises ValueError if data missing or insufficient
**Raises:** ValueError if validation fails
**Retry:** No
**Side Effects:** None

### `_initialize_population() -> List[Dict[str, float]]`
**Pre:** None
**Post:** Returns list of weight allocations summing to 1.0
**Raises:** None
**Retry:** No
**Side Effects:** Uses np.random.dirichlet for valid distributions

### `_evaluate_population(population, returns_data, risk_data) -> List[ParetoSolution]`
**Pre:** population is list of weight dicts
**Post:** Returns list of ParetoSolutions with objective_values
**Raises:** None (skips invalid solutions)
**Retry:** No
**Side Effects:** None

### `_calculate_objectives(allocation, returns_data, risk_data) -> Dict[str, float]`
**Pre:** allocation sums to 1.0, returns_data valid
**Post:** Returns dict of objective values (return, risk, sharpe, etc.)
**Raises:** None (returns 0.0 for failed calculations)
**Retry:** No
**Side Effects:** None

### `_calculate_portfolio_return(allocation, returns_data) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized portfolio return
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_portfolio_risk(allocation, returns_data) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized portfolio volatility
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_downside_risk(allocation, returns_data) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns annualized downside deviation
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_max_drawdown(allocation, returns_data) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns maximum drawdown (positive value)
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_calculate_diversification_ratio(allocation, returns_data) -> float`
**Pre:** allocation and returns_data valid
**Post:** Returns weighted_avg_vol / portfolio_vol
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `_non_dominated_sort(population) -> List[List[ParetoSolution]]`
**Pre:** population is list of ParetoSolutions
**Post:** Returns list of fronts (rank 0 = non-dominated)
**Raises:** None
**Retry:** No
**Side Effects:** Updates solution ranks in-place

### `_dominates(solution1, solution2) -> bool`
**Pre:** Both solutions have objective_values
**Post:** Returns True if solution1 dominates solution2
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_crowding_distance(fronts) -> None`
**Pre:** fronts is list of solution lists
**Post:** Updates crowding_distance for all solutions
**Raises:** None
**Retry:** No
**Side Effects:** Modifies solutions in-place

### `_create_offspring(population) -> List[ParetoSolution]`
**Pre:** population is list of ParetoSolutions
**Post:** Returns offspring with crossover and mutation
**Raises:** None
**Retry:** No
**Side Effects:** Uses random for selection/crossover/mutation

### `_tournament_selection(population, tournament_size) -> ParetoSolution`
**Pre:** population not empty
**Post:** Returns selected solution based on rank and crowding
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_crossover(parent1, parent2) -> Tuple[Dict, Dict]`
**Pre:** parents have same strategies
**Post:** Returns two children with SBX crossover
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_mutate(weights) -> Dict[str, Decimal]`
**Pre:** weights is strategy → Decimal mapping
**Post:** Returns mutated weights (polynomial mutation)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_select_new_population(combined) -> List[ParetoSolution]`
**Pre:** combined has parent + offspring
**Post:** Returns selected population of size population_size
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] NSGA-II algorithm implemented correctly
- [ ] Non-dominated sort assigns rank 0 to Pareto front
- [ ] Crowding distance promotes diversity
- [ ] Tournament selection uses (rank, -crowding) key
- [ ] SBX crossover (eta = 20) for real-valued encoding
- [ ] Polynomial mutation (eta = 20)
- [ ] Weights normalized to sum to 1.0 after operations
- [ ] Portfolio return annualized (mean * 252)
- [ ] Portfolio risk annualized (std * sqrt(252))
- [ ] Max drawdown calculated from cumulative returns
- [ ] Diversification ratio = weighted_avg_vol / portfolio_vol

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-001 | BASE_RULES | Validate covariance matrix | ✅ OK - Portfolio risk uses np.cov |
| TRD-002 | BASE_RULES | Validate orders | ⚠️ NOT APPLIED - No order execution |
| TRD-007 | BASE_RULES | Document TRADING_DAYS | ✅ OK - Uses 252 for annualization |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Only imports models |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ PARTIAL - Logs generation errors |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |

---

## Dependencies
- **External:** numpy (np), random, decimal (Decimal), typing, scipy.stats (skew, kurtosis)
- **Internal:** app.ensemble.models (ObjectiveConfig, OptimizationObjective, ParetoSolution)

---

## Required Tests
- **tests/ensemble/test_pareto.py:**
  - Test optimizer initialization with valid parameters
  - Test optimizer initialization with invalid parameters (errors)
  - Test optimization returns Pareto front
  - Test non-dominated sorting correctness
  - Test domination comparison
  - Test crowding distance calculation
  - Test tournament selection
  - Test SBX crossover produces valid weights
  - Test polynomial mutation produces valid weights
  - Test population selection preserves best solutions
  - Test portfolio return calculation
  - Test portfolio risk calculation
  - Test max drawdown calculation
  - Test diversification ratio calculation
  - Test edge cases: single objective, zero variance

---

## Notes
NSGA-II from Deb et al. (2002). SBX crossover eta = 20, polynomial mutation eta = 20. Annualization assumes 252 trading days. Tolerance handles numerical precision in dominance comparison.
