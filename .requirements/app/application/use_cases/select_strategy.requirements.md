# select_strategy.py

## Purpose
Select Strategy Use Case - Orchestrates intelligent strategy selection based on user profile, market regime detection, Bayesian optimization, walk-forward validation, and performance scoring.

---

## Type Definitions / Data Classes

### StrategyConfiguration (frozen=True)
```python
@dataclass(frozen=True)
class StrategyConfiguration:
    strategy_name: str                           # REQUIRED - Strategy identifier
    parameters: Dict[str, Any]                    # Default: {} - Optimized parameters
    weights: Dict[str, float]                     # Default: {} - Capital allocation weights
    expected_return: Decimal                      # Default: 0 - Expected annual return
    expected_risk: Decimal                        # Default: 0 - Expected risk (volatility)
    sharpe_ratio: Decimal                         # Default: 0 - Risk-adjusted return
    max_drawdown: Decimal                         # Default: 0 - Maximum expected drawdown
    win_rate: Decimal                             # Default: 0 - Expected win rate
    suitability_score: Decimal                    # Default: 0 - Profile matching (0-100)
    validation_score: Decimal                     # Default: 0 - Walk-forward score (0-100)
    total_score: Decimal                          # Default: 0 - Combined score (0-100)
```

**Properties:**
- Immutable (frozen=True)
- Value object (defined by strategy_name, no identity)

### StrategySelectionCriteria
```python
@dataclass
class StrategySelectionCriteria:
    return_weight: float                          # Default: 0.25 - Weight for return in scoring
    risk_weight: float                            # Default: 0.20 - Weight for risk in scoring
    sharpe_weight: float                          # Default: 0.25 - Weight for Sharpe in scoring
    validation_weight: float                      # Default: 0.20 - Weight for validation score
    suitability_weight: float                     # Default: 0.10 - Weight for profile matching
    min_sharpe_ratio: Decimal                     # Default: 0.5 - Minimum acceptable Sharpe
    max_drawdown_limit: Decimal                   # Default: 0.30 - Maximum acceptable drawdown
    min_validation_score: Decimal                 # Default: 60 - Minimum validation score
    require_walk_forward: bool                    # Default: True - Require walk-forward validation
```

**Invariants (enforced in validate()):**
- Weights must sum to approximately 1.0 (0.9 to 1.1)

### StrategySelectionResult
```python
@dataclass
class StrategySelectionResult:
    selected_strategy: StrategyConfiguration        # REQUIRED - Best matching strategy
    alternative_strategies: List[StrategyConfiguration]  # REQUIRED - Ranked alternatives
    selection_timestamp: datetime                  # REQUIRED - When selection was performed
    selection_criteria: StrategySelectionCriteria # REQUIRED - Criteria used for selection
    optimization_details: Dict[str, Any]           # Default: {} - Details from Bayesian optimization
    validation_details: Dict[str, Any]             # Default: {} - Details from walk-forward validation
```

---

## Function Signatures (Contracts) - StrategyConfiguration

### `StrategyConfiguration.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dictionary with all fields as strings or native types
**Raises:** None
**Retry:** No
**Side Effects:** None (pure serialization)

---

## Function Signatures (Contracts) - StrategySelectionCriteria

### `StrategySelectionCriteria.validate() -> None`
**Pre:** None
**Post:** Validates weights sum to ~1.0
**Raises:** `ValueError` if weights not in [0.9, 1.1]
**Retry:** No
**Side Effects:** None (validation only)

---

## Function Signatures (Contracts) - StrategySelectionResult

### `StrategySelectionResult.to_dict() -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dictionary with selected strategy and top 5 alternatives
**Raises:** None
**Retry:** No
**Side Effects:** None (pure serialization)

---

## Function Signatures (Contracts) - StrategySelector

### `StrategySelector.__init__(profile_mapper, optimizer, validator) -> None`
**Pre:** None
**Post:** StrategySelector initialized with dependencies
**Raises:** None
**Retry:** No
**Side Effects:** Creates default dependencies if None

**Default Dependencies:**
- profile_mapper: ProfileStrategyMapper() if None
- optimizer: None (parameter optimization optional)
- validator: WalkForwardValidator() if None

### `select_strategy(profile, market_data, criteria, progress_callback) -> StrategySelectionResult`
**Pre:** profile is valid InputProfile
**Post:** Returns StrategySelectionResult with best strategy
**Raises:** `ValueError` if no candidate strategies found
**Retry:** No
**Side Effects:** Logs strategy selection process

**Process:**
1. Map profile to candidate strategies
2. Optimize parameters for each candidate
3. Validate with walk-forward analysis
4. Score and rank strategies
5. Select best matching strategy

### `_analyze_strategy(strategy_name, profile, strategy_mapping, market_data, criteria) -> StrategyConfiguration`
**Pre:** strategy_name in enabled_strategies
**Post:** Returns StrategyConfiguration with scores
**Raises:** None (errors logged, returns zero-score config)
**Retry:** No
**Side Effects:** Calls optimizer and validator

**Steps:**
1. Calculate suitability score
2. Optimize parameters (if optimizer available)
3. Validate strategy (if required)
4. Estimate performance metrics
5. Calculate total score

### `_calculate_suitability_score(strategy_name, profile, strategy_mapping) -> Decimal`
**Pre:** None
**Post:** Returns suitability score (0-100)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Scoring Components:**
- Base score: 50
- Risk tolerance adjustment: ±20
- Investment objective adjustment: ±30
- Capital tier adjustment: ±15

### `_optimize_parameters(strategy_name, profile, market_data) -> Tuple[Dict[str, Any], Dict[str, Any]]`
**Pre:** optimizer is not None
**Post:** Returns (optimized_parameters, optimization_metrics)
**Raises:** Exception (logged, returns empty dict)
**Retry:** No
**Side Effects:** Runs Bayesian optimization

**Parameters:**
- max_iterations: 50
- metric: "sharpe_ratio"
- Uses placeholder objective function (TODO: integrate backtest)

### `_validate_strategy(strategy_name, parameters, market_data) -> Tuple[Decimal, Dict[str, Any]]`
**Pre:** validator is not None
**Post:** Returns (validation_score, validation_details)
**Raises:** Exception (logged, returns 50, error details)
**Retry:** No
**Side Effects:** Runs walk-forward validation

**Walk-Forward Config:**
- train_period_months: 24
- test_period_months: 6
- step_months: 3
- min_observations: 252

### `_calculate_total_score(suitability, validation_score, performance, criteria) -> Decimal`
**Pre:** None
**Post:** Returns total score (0-100)
**Raises:** None
**Retry:** No
**Side Effects:** None (pure computation)

**Scoring Formula:**
```
total = (return_score × return_weight
       + risk_score × risk_weight
       + sharpe_score × sharpe_weight
       + validation_score × validation_weight
       + suitability × suitability_weight)
```

---

## Function Signatures (Contracts) - SelectStrategyUseCase

### `SelectStrategyUseCase.__init__(selector) -> None`
**Pre:** None
**Post:** Use case initialized with selector
**Raises:** None
**Retry:** No
**Side Effects:** Creates default StrategySelector if None

### `SelectStrategyUseCase.execute(profile, market_data, criteria, progress_callback) -> StrategySelectionResult`
**Pre:** profile is valid InputProfile
**Post:** Returns StrategySelectionResult with selected strategy
**Raises:** None (errors propagated from selector)
**Retry:** No
**Side Effects:** Logs execution, calls selector

### `SelectStrategyUseCase.get_strategy_recommendations(profile, top_n) -> List[Dict[str, Any]]`
**Pre:** profile is valid InputProfile
**Post:** Returns top_n strategy recommendations (quick, no validation)
**Raises:** None
**Retry:** No
**Side Effects:** None (fast recommendation without optimization/validation)

---

## Acceptance Criteria
- [ ] **AC-001:** StrategyConfiguration is immutable (frozen=True)
- [ ] **AC-002:** StrategySelectionCriteria weights sum to ~1.0
- [ ] **AC-003:** select_strategy() returns best strategy
- [ ] **AC-004:** Alternative strategies ranked by total_score
- [ ] **AC-005:** Suitability score in range [0, 100]
- [ ] **AC-006:** Validation score in range [0, 100]
- [ ] **AC-007:** Total score in range [0, 100]
- [ ] **AC-008:** Walk-forward validation uses Pardo standards
- [ ] **AC-009:** Bayesian optimization for parameter tuning
- [ ] **AC-010:** Progress callback for long-running operations
- [ ] **AC-011:** get_strategy_recommendations() is fast (no validation)
- [ ] **AC-012:** All public methods have complete type hints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo (Select Strategy Use Case):

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Use case pattern | Clean Architecture | Application orchestrator | ✅ OK - SelectStrategyUseCase |
| Strategy selection | Narang (2013) | Profile-driven selection | ✅ OK - Implemented |
| Walk-forward validation | Pardo (2008) | Rolling window validation | ✅ OK - WalkForwardValidator |
| Bayesian optimization | ML optimization | Parameter tuning | ✅ OK - BayesianOptimizer |
| Multi-criteria scoring | Decision theory | Weighted scoring | ✅ OK - StrategySelectionCriteria |
| Suitability scoring | Risk management | Profile matching | ✅ OK - _calculate_suitability_score |
| Risk tolerance adjustment | Risk management | Conservative/aggressive | ✅ OK - _adjust_score_for_risk_tolerance |
| Objective matching | Investment policy | Goal alignment | ✅ OK - _adjust_score_for_objective |
| Capital tier adjustment | Trading | Small/large account | ✅ OK - _adjust_score_for_capital |
| Sharpe ratio scoring | Sharpe (1966) | Risk-adjusted return | ✅ OK - _calculate_total_score |
| Progress callback | UX | Long operation feedback | ✅ OK - progress_callback |
| Fast recommendations | Performance | Quick path | ✅ OK - get_strategy_recommendations |
| Error handling | BASE_RULES.md (LOG-001) | Log errors, continue | ✅ OK - try/except with logging |
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints | ✅ OK - Complete |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ✅ OK - Complete |

**NOTE:** This analysis references BASE_RULES.md for universal rules and Narang (2013), Pardo (2008), Sharpe (1966) for strategy selection standards.

---

## Dependencies
- **External:** `pandas`, `numpy`, `logging`, `asyncio` (std), `dataclasses` (std), `decimal` (std), `datetime` (std), `typing` (std)
- **Internal:**
  - `app.backtesting.validation.models.WalkForwardConfig`
  - `app.backtesting.validation.walk_forward.WalkForwardValidator`
  - `app.core.models.input_profile.InputProfile`
  - `app.optimization.parameter.bayesian_optimizer.BayesianOptimizer`
  - `app.optimization.parameter.base_optimizer.OptimizationConfig`
  - `app.optimization.parameter.models.ParameterGrid`
  - `app.services.profile_driven_trading.profile_strategy_mapper.ProfileStrategyMapper`

---

## Required Tests
- **test_select_strategy_use_case.py:**
  - `test_strategy_configuration_frozen()` - Immutable
  - `test_strategy_configuration_to_dict()` - Serialization
  - `test_criteria_validate_weights_sum_to_one()` - Passes
  - `test_criteria_validate_weights_invalid_sum()` - Raises ValueError
  - `test_selector_init_default_deps()` - Creates defaults
  - `test_select_strategy_no_candidates()` - Raises ValueError
  - `test_select_strategy_returns_best()` - Highest score selected
  - `test_select_strategy_includes_alternatives()` - Top 5 alternatives
  - `test_suitability_score_range()` - 0-100
  - `test_risk_tolerance_adjustment_bajo()` - Defensive strategies
  - `test_risk_tolerance_adjustment_alto()` - Aggressive strategies
  - `test_objective_adjustment_dividend()` - Dividend strategies
  - `test_objective_adjustment_capital()` - Momentum strategies
  - `test_capital_adjustment_small()` - Simpler strategies
  - `test_capital_adjustment_large()` - Complex strategies
  - `test_total_score_calculation()` - Weighted sum
  - `test_total_score_clamped()` - 0-100 range
  - `test_optimize_parameters()` - Bayesian optimization
  - `test_validate_strategy()` - Walk-forward validation
  - `test_validation_scoring_consistency()` - Consistency score
  - `test_validation_scoring_degradation()` - Degradation score
  - `test_validation_scoring_os_sharpe()` - OS Sharpe score
  - `test_performance_estimation_momentum()` - Momentum metrics
  - `test_performance_estimation_pairs()` - Pairs trading metrics
  - `test_performance_adjustment_risk_bajo()` - Conservative adjustment
  - `test_performance_adjustment_risk_alto()` - Aggressive adjustment
  - `test_use_case_execute()` - Returns result
  - `test_use_case_get_recommendations()` - Quick recommendations
  - `test_progress_callback()` - Progress updates
  - `test_error_handling_optimization_fails()` - Logs, continues
  - `test_error_handling_validation_fails()` - Returns mid score

---

## Notes
- **Critical:** SelectStrategyUseCase is a USE CASE (Clean Architecture application layer)
- **Evans (DDD) Reference:** "Domain-Driven Design" (2003) - Application Service pattern
- **Use Case Pattern:** Orchestrates domain logic without containing business rules
- **Strategy Selection Process:**
  1. Profile → Candidate strategies (ProfileStrategyMapper)
  2. Candidates → Parameter optimization (BayesianOptimizer)
  3. Optimized → Walk-forward validation (WalkForwardValidator)
  4. Validated → Performance estimation
  5. All scores → Total score (weighted sum)
- **Scoring Components:**
  - Suitability: Profile matching (risk, objective, capital)
  - Validation: Walk-forward consistency and robustness
  - Performance: Expected return, risk, Sharpe, drawdown
- **StrategyConfiguration:** Immutable snapshot of strategy with all metrics
- **StrategySelectionCriteria:** Configurable weights for different priorities
- **Pardo Reference:** "The Evaluation and Optimization of Trading Strategies" (2008) - walk-forward validation
- **Narang Reference:** "Inside the Black Box" (2013) - strategy selection and evaluation
- **Bayesian Optimization:** Efficient parameter search (placeholder objective - TODO: integrate backtest)
- **Progress Callback:** Optional callback(str, float) for progress updates during long operations
- **Fast Recommendations:** get_strategy_recommendations() skips validation for quick results
- **Error Handling:** Errors in individual strategies logged and result in zero-score config
- **Default Criteria:** Adjusted based on risk tolerance (conservative → higher risk weight)
- **Performance Estimation:** Base expectations by strategy type, adjusted for risk tolerance

---

**File Reference:** `app/application/use_cases/select_strategy.py`
**Last Audited:** 2026-02-01
