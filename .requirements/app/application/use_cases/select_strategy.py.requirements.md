# select_strategy.py

## Purpose
Select Strategy Use Case - orchestrates intelligent strategy selection based on user investment profile, market regime detection, Bayesian optimization, walk-forward validation, and performance scoring (FASE 6.6).

---

## Type Definitions / Data Classes

### StrategyConfiguration DataClass (Immutable)
```python
@dataclass(frozen=True)
class StrategyConfiguration:
    """Configuration for a strategy candidate (immutable value object)."""

    strategy_name: str                      # REQUIRED - Strategy name
    parameters: Dict[str, Any] = {}         # REQUIRED - Strategy parameters
    weights: Dict[str, float] = {}         # REQUIRED - Capital allocation weights
    expected_return: Decimal = 0            # REQUIRED - Expected annual return
    expected_risk: Decimal = 0              # REQUIRED - Expected risk (volatility)
    sharpe_ratio: Decimal = 0              # REQUIRED - Risk-adjusted return
    max_drawdown: Decimal = 0               # REQUIRED - Maximum expected drawdown
    win_rate: Decimal = 0                   # REQUIRED - Expected win rate
    suitability_score: Decimal = 0          # REQUIRED - Profile matching (0-100)
    validation_score: Decimal = 0           # REQUIRED - Walk-forward score (0-100)
    total_score: Decimal = 0                # REQUIRED - Combined score (0-100)
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary representation

### StrategySelectionCriteria DataClass
```python
@dataclass
class StrategySelectionCriteria:
    """Criteria for scoring and ranking strategies."""

    return_weight: float = 0.25            # Weight for return (0-1)
    risk_weight: float = 0.20               # Weight for risk (0-1)
    sharpe_weight: float = 0.25             # Weight for Sharpe (0-1)
    validation_weight: float = 0.20         # Weight for validation (0-1)
    suitability_weight: float = 0.10        # Weight for profile match (0-1)
    min_sharpe_ratio: Decimal = 0.5         # Minimum acceptable Sharpe
    max_drawdown_limit: Decimal = 0.30      # Maximum acceptable drawdown
    min_validation_score: Decimal = 60      # Minimum validation score
    require_walk_forward: bool = True       # Require walk-forward validation
```

**Methods:**
- `validate() -> None`: Validates weights sum to ~1.0

### StrategySelectionResult DataClass
```python
@dataclass
class StrategySelectionResult:
    """Result of strategy selection process."""

    selected_strategy: StrategyConfiguration     # REQUIRED - Best strategy
    alternative_strategies: List[StrategyConfiguration]  # REQUIRED - Ranked alternatives
    selection_timestamp: datetime                # REQUIRED - Selection time
    selection_criteria: StrategySelectionCriteria        # REQUIRED - Criteria used
    optimization_details: Dict[str, Any] = {}   # OPTIONAL - Bayesian opt details
    validation_details: Dict[str, Any] = {}     # OPTIONAL - Walk-forward details
```

**Methods:**
- `to_dict() -> Dict[str, Any]`: Convert to dictionary representation

### StrategySelector Class
```python
class StrategySelector:
    """
    Selects optimal strategy based on profile and validation.

    Integrates:
    - ProfileStrategyMapper: Maps profile to candidates
    - BayesianOptimizer: Optimizes parameters
    - WalkForwardValidator: Validates out-of-sample
    - Scoring system: Ranks by multiple criteria
    """

    _profile_mapper: ProfileStrategyMapper        # PRIVATE - Strategy mapper
    _optimizer: BayesianOptimizer                  # PRIVATE - Bayesian optimizer
    _validator: WalkForwardValidator               # PRIVATE - Walk-forward validator
    _default_criteria: StrategySelectionCriteria  # PRIVATE - Default criteria
```

---

## Function Signatures (Contracts)

### StrategySelector Methods

### `__init__(self, profile_mapper: Optional[ProfileStrategyMapper] = None, optimizer: Optional[BayesianOptimizer] = None, validator: Optional[WalkForwardValidator] = None, default_criteria: Optional[StrategySelectionCriteria] = None) -> None`
**Pre:** Components compatible
**Post:** Selector initialized with components
**Raises:** ValueError if criteria validation fails
**Retry:** No
**Side Effects:** None

### `async select_strategy(self, profile: InputProfile, market_data: MarketData, criteria: Optional[StrategySelectionCriteria] = None) -> StrategySelectionResult`
**Pre:** profile valid, market_data provided
**Post:** Optimal strategy selected and validated
**Raises:** ValueError if no suitable strategies found
**Retry:** No
**Side Effects:** Logs selection process

**Flow:**
1. Get candidate strategies from profile mapper
2. Filter by criteria (Sharpe, drawdown, validation)
3. Optimize parameters with Bayesian optimizer
4. Validate with walk-forward
5. Score strategies by criteria
6. Rank and return best + alternatives

### `async _get_candidate_strategies(self, profile: InputProfile) -> List[StrategyMapping]`
**Pre:** profile valid
**Post:** Returns candidate strategy mappings
**Raises:** No
**Retry:** No
**Side Effects:** None

### `async _optimize_strategy(self, strategy_mapping: StrategyMapping, market_data: MarketData) -> Dict[str, Any]`
**Pre:** strategy_mapping valid, market_data provided
**Post:** Returns optimized parameters and metrics
**Raises:** No
**Retry:** No
**Side Effects:** Runs Bayesian optimization

### `async _validate_strategy(self, strategy_config: StrategyConfiguration, market_data: MarketData) -> Dict[str, Any]`
**Pre:** strategy_config valid, market_data provided
**Post:** Returns validation results
**Raises:** No
**Retry:** No
**Side Effects:** Runs walk-forward validation

### `_calculate_scores(self, config: StrategyConfiguration, criteria: StrategySelectionCriteria) -> StrategyConfiguration`
**Pre:** config and criteria valid
**Post:** Returns config with scores calculated
**Raises:** No
**Retry:** No
**Side Effects:** None

**Scoring:**
- Weighted sum of return, risk, Sharpe, validation, suitability
- Filters by min_sharpe_ratio, max_drawdown_limit, min_validation_score

### `async _rank_strategies(self, strategies: List[StrategyConfiguration], criteria: StrategySelectionCriteria) -> List[StrategyConfiguration]`
**Pre:** strategies have scores calculated
**Post:** Returns strategies ranked by total_score
**Raises:** No
**Retry:** No
**Side Effects:** None

**Ranking:** Descending by total_score

---

## Acceptance Criteria
- [ ] StrategyConfiguration is immutable (frozen=True)
- [ ] StrategyConfiguration.to_dict() converts all fields
- [ ] StrategySelectionCriteria weights sum to ~1.0
- [ ] StrategySelectionCriteria.validate() raises if weights invalid
- [ ] StrategySelector integrates 4 components (mapper, optimizer, validator, scorer)
- [ ] select_strategy returns StrategySelectionResult
- [ ] select_strategy filters by criteria
- [ ] select_strategy optimizes parameters
- [ ] select_strategy validates with walk-forward
- [ ] select_strategy returns top 5 alternatives
- [ ] All scores are 0-100 range
- [ ] Returns best strategy + ranked alternatives

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Clean Architecture | BASE_RULES.md | Use case orchestrates | ✅ OK |
| Immutability | CRITICAL_RULES.md | frozen=True for config | ✅ OK |
| Type Hints | BASE_RULES.md | All functions typed | ✅ OK |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| Decimal Precision | CRITICAL_RULES.md | Use Decimal for scores | ✅ OK |
| Error Handling | BASE_RULES.md | Specific exceptions | ✅ OK |
| Logging | BASE_RULES.md | All operations logged | ✅ OK |
| Async Operations | BASE_RULES.md | async/await used | ✅ OK |

---

## Dependencies
- **External:** logging, dataclasses, datetime, decimal, typing, pandas
- **Internal:**
  - app.backtesting.validation.models.WalkForwardConfig
  - app.backtesting.validation.walk_forward.WalkForwardValidator
  - app.core.models.input_profile.InputProfile, ObjectivoInversion, RiskTolerance
  - app.optimization.parameter.bayesian_optimizer.BayesianOptimizer
  - app.optimization.parameter.base_optimizer.OptimizationConfig
  - app.optimization.parameter.models.ParameterGrid, ParameterRange, ParameterType
  - app.services.profile_driven_trading.profile_strategy_mapper.ProfileStrategyMapper, StrategyMapping

---

## Required Tests
- **test_select_strategy.py:**
  - Test StrategyConfiguration.to_dict()
  - Test StrategySelectionCriteria.validate() with valid weights
  - Test StrategySelectionCriteria.validate() with invalid weights raises ValueError
  - Test StrategySelector.__init__ with components
  - Test StrategySelector.__init__ with invalid criteria raises ValueError
  - Test select_strategy returns StrategySelectionResult
  - Test select_strategy filters by min_sharpe_ratio
  - Test select_strategy filters by max_drawdown_limit
  - Test select_strategy filters by min_validation_score
  - Test select_strategy returns selected_strategy + alternatives
  - Test select_strategy requires walk-forward if configured
  - Test _calculate_scores weighted sum
  - Test _rank_strategies descending by total_score
  - Test integration with ProfileStrategyMapper
  - Test integration with BayesianOptimizer
  - Test integration with WalkForwardValidator

---

## Notes
- CRITICAL: This is a core application use case (FASE 6.6)
- Orchestrates 4 components for strategy selection
- Clean Architecture: Use case coordinates domain services
- Immutable configuration (frozen=True)
- Comprehensive scoring with 5 criteria
- Bayesian optimization for parameters
- Walk-forward validation for robustness
- Returns best strategy + 5 alternatives
- All financial values use Decimal
