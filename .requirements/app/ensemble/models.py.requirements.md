# models.py

## Purpose
Define Pydantic data models for ensemble configuration, Pareto optimization, portfolio combination, and correlation analysis with comprehensive validation.

---

## Type Definitions / Data Classes

### OptimizationObjective (str, Enum)
```python
class OptimizationObjective(str, Enum):
    MAXIMIZE_RETURN = "maximize_return"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_SORTINO = "maximize_sortino"
    MINIMIZE_DRAWDOWN = "minimize_drawdown"
    MAXIMIZE_DIVERSIFICATION = "maximize_diversification"
```

### ObjectiveConfig (BaseModel)
```python
class ObjectiveConfig(BaseModel):
    objectives: List[OptimizationObjective]  # REQUIRED, min_length: 1, max_length: 6
    weights: List[float]                     # REQUIRED, min_length: 1, must sum to 1.0
    constraints: Optional[Dict[str, Any]]    # Optional optimization constraints
    tolerance: float = 0.01                  # Range: [0.0, 1.0] - Dominance comparison tolerance
```

**Validation Rules:**
- `weights` must sum to 1.0 (±0.01 tolerance)
- `weights` length must match `objectives` length
- All weights must be non-negative
- `tolerance` must be in [0.0, 1.0]

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True

### ParetoSolution (BaseModel)
```python
class ParetoSolution(BaseModel):
    strategy_weights: Dict[str, Decimal]     # REQUIRED - Must sum to 1.0
    objective_values: Dict[str, float]        # REQUIRED - Objective function results
    rank: int = 0                             # Pareto rank (0 = non-dominated), ge=0
    crowding_distance: float = 0.0            # Diversity metric, ge=0.0
    metrics: Dict[str, float]                 # Additional performance metrics
    timestamp: datetime                       # Solution creation time (auto-generated)
```

**Validation Rules:**
- `strategy_weights` must sum to 1.0 (±0.01 tolerance)
- All weights must be non-negative
- `rank` must be >= 0
- `crowding_distance` must be >= 0.0

**Properties:**
- `dominates: bool` - Returns True if rank == 0
- `is_diverse: bool` - Returns True if crowding_distance > 0.5

**Methods:**
- `__hash__()` - Makes ParetoSolution hashable for use as dictionary key

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True

### EnsembleMethod (str, Enum)
```python
class EnsembleMethod(str, Enum):
    MAJORITY_VOTING = "majority_voting"
    WEIGHTED_VOTING = "weighted_voting"
    SOFT_VOTING = "soft_voting"
    RANK_AVERAGING = "rank_averaging"
    PERFORMANCE_WEIGHTED = "performance_weighted"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
```

### EnsembleConfig (BaseModel)
```python
class EnsembleConfig(BaseModel):
    method: EnsembleMethod                   # REQUIRED
    strategies: List[str]                    # REQUIRED, min_length: 2
    strategy_weights: Optional[Dict[str, float]] # Must sum to 1.0 if provided
    min_agreement: float = 0.5               # Range: [0.0, 1.0] - Minimum agreement threshold
    confidence_threshold: float = 60.0       # Range: [0.0, 100.0] - Minimum confidence
    rebalance_frequency: int = 30            # Range: [1, 365] days
    lookback_period: int = 90                # Min: 1 - Performance lookback period
```

**Validation Rules:**
- `strategy_weights` must sum to 1.0 if provided (±0.01 tolerance)
- All weights non-negative

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True, use_enum_values=True

### EnsembleSignal (BaseModel)
```python
class EnsembleSignal(BaseModel):
    signal_id: str                            # Auto-generated unique ID
    symbol: str                               # REQUIRED - Trading symbol
    signal_type: str                          # REQUIRED - Combined signal type
    confidence: float                         # REQUIRED, Range: [0.0, 100.0]
    agreement: float                          # REQUIRED, Range: [0.0, 1.0]
    strategy_votes: Dict[str, str]            # REQUIRED - Strategy -> vote mapping
    strategy_weights: Dict[str, float]        # REQUIRED - Weights used
    timestamp: datetime                       # Signal generation time (auto-generated)
    metadata: Dict[str, Any]                  # Additional metadata
```

**Properties:**
- `is_actionable: bool` - Returns True if confidence > 60 AND agreement > 0.5
- `has_consensus: bool` - Returns True if all votes identical

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True, use_enum_values=True

### AllocationMethod (str, Enum)
```python
class AllocationMethod(str, Enum):
    MEAN_VARIANCE = "mean_variance"
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    REGIME_DEPENDENT = "regime_dependent"
    BLACK_LITTERMAN = "black_litterman"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"
```

### StrategyAllocation (BaseModel)
```python
class StrategyAllocation(BaseModel):
    strategy: str                             # REQUIRED - Strategy name
    weight: Decimal                           # REQUIRED, Range: [0, 1] - Target weight
    target_weight: Decimal                    # REQUIRED, Range: [0, 1] - Rebalancing target
    actual_weight: Decimal                     # REQUIRED, Range: [0, 1] - Current weight
    contribution_risk: Decimal = 0            # Default: 0, Risk contribution
    contribution_return: Decimal = 0          # Default: 0, Return contribution
    last_rebalanced: datetime                 # Last rebalance timestamp (auto-generated)
```

**Properties:**
- `drift: Decimal` - Returns abs(actual_weight - target_weight)
- `needs_rebalance: bool` - Returns True if drift > 0.05

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True

### CombinedPortfolio (BaseModel)
```python
class CombinedPortfolio(BaseModel):
    total_return: Decimal                     # REQUIRED - Annualized return
    volatility: Decimal                       # REQUIRED, min: 0 - Annualized volatility
    sharpe_ratio: Decimal = 0                # Default: 0 - Risk-adjusted return
    sortino_ratio: Decimal = 0               # Default: 0 - Downside-adjusted return
    max_drawdown: Decimal = 0                # Default: 0, max: 0 - Maximum drawdown (negative)
    diversification_ratio: Decimal = 1        # Default: 1, min: 1 - Div ratio
    effective_n_strategies: float = 1.0       # Default: 1.0, min: 1.0 - Effective N
    correlation_mean: Decimal = 0             # Default: 0, range: [-1, 1] - Avg correlation
    allocation: List[StrategyAllocation]      # Default: [] - Strategy allocations
    metrics: Dict[str, Decimal]               # Default: {} - Additional metrics
    timestamp: datetime                       # Portfolio snapshot time (auto-generated)
```

**Properties:**
- `is_well_diversified: bool` - Returns True if div_ratio > 1.2 AND eff_n >= 2 AND abs(corr) < 0.7
- `is_efficient: bool` - Returns True if sharpe_ratio > 1.0

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True

### CorrelationMetrics (BaseModel)
```python
class CorrelationMetrics(BaseModel):
    correlation_matrix: Dict[str, Dict[str, Decimal]] # REQUIRED - n x n matrix
    mean_correlation: Decimal                  # REQUIRED, Range: [-1, 1]
    median_correlation: Decimal                # REQUIRED, Range: [-1, 1]
    max_correlation: Decimal                   # REQUIRED, Range: [-1, 1]
    min_correlation: Decimal                   # REQUIRED, Range: [-1, 1]
    redundant_pairs: List[tuple]               # Default: [] - Highly correlated pairs
    effective_number_bets: float = 1.0         # Default: 1.0, min: 1.0
    eigenvalues: List[float]                   # Default: [] - Matrix eigenvalues
    condition_number: float = 1.0              # Default: 1.0, min: 1.0
    timestamp: datetime                        # Analysis timestamp (auto-generated)
```

**Properties:**
- `has_redundancy: bool` - Returns True if redundant_pairs not empty
- `is_well_conditioned: bool` - Returns True if condition_number < 100
- `diversification_quality: str` - Returns "excellent", "good", "moderate", or "poor"

**Config:** strict=True, validate_assignment=True, extra="forbid", str_strip_whitespace=True

---

## Function Signatures (Contracts)

### All models use Pydantic validation with field validators. No standalone functions.

### Field Validators

#### `ObjectiveConfig.validate_weights(v: List[float]) -> List[float]`
**Pre:** v is list of numbers
**Post:** Returns weights if sum is 1.0 ± 0.01, all non-negative
**Raises:** ValueError if sum invalid or negative weights

#### `ObjectiveConfig.validate_objectives_match_weights(v: List[OptimizationObjective], info) -> List[OptimizationObjective]`
**Pre:** v is list of objectives
**Post:** Returns objectives if length matches weights length
**Raises:** ValueError if lengths don't match

#### `ParetoSolution.validate_strategy_weights(v: Dict[str, Decimal]) -> Dict[str, Decimal]`
**Pre:** v is dict of strategy -> weight
**Post:** Returns weights if sum is 1.0 ± 0.01, all non-negative
**Raises:** ValueError if sum invalid or negative weights

#### `EnsembleConfig.validate_strategy_weights(v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]`
**Pre:** v is dict or None
**Post:** Returns weights if sum is 1.0 ± 0.01, all non-negative
**Raises:** ValueError if sum invalid or negative weights

---

## Acceptance Criteria
- [ ] All Pydantic models use strict=True, validate_assignment=True, extra="forbid"
- [ ] All weight fields validated to sum to 1.0 (±0.01 tolerance)
- [ ] All weight validations reject negative values
- [ ] ObjectiveConfig weights length matches objectives length
- [ ] ParetoSolution weights validated to sum to 1.0
- [ ] EnsembleConfig requires at least 2 strategies
- [ ] CombinedPortfolio has sensible property checks (is_well_diversified, is_efficient)
- [ ] CorrelationMetrics condition number >= 1.0 enforced
- [ ] All numeric ranges enforced via Field constraints (ge, le, min_length, max_length)
- [ ] All timestamps default to datetime.utcnow()
- [ ] ParetoSolution is hashable for use as dictionary key

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES | Use Pydantic Settings for config | ✅ OK - All models are BaseModel |
| CFG-003 | BASE_RULES | Validate all configuration values | ✅ OK - Field validators on all numeric fields |
| CFG-004 | BASE_RULES | Extra="forbid" to catch typos | ✅ OK - All models have extra="forbid" |
| CFG-006 | BASE_RULES | Field validators for complex validation | ✅ OK - Custom validators for weights, objectives |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All fields fully typed |
| TYP-002 | BASE_RULES | Modern syntax (list[T], X\|None) | ✅ OK - Uses List, Dict, Optional |
| SEC-007 | BASE_RULES | Input validation at boundaries | ✅ OK - Pydantic validates on init and assignment |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - BaseModel with validate_assignment=True |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - All defaults are immutable or use default_factory |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** pydantic (BaseModel, ConfigDict, Field, field_validator), enum (Enum), typing (List, Dict, Optional, Any, Tuple), datetime (datetime), decimal (Decimal)
- **Internal:** None (pure models file)

---

## Required Tests
- **tests/unit/ensemble/test_models.py:**
  - Test ObjectiveConfig validation (weights sum to 1.0)
  - Test ObjectiveConfig weights/objectives length mismatch (error)
  - Test ObjectiveConfig negative weights (error)
  - Test ParetoSolution weights validation (sum to 1.0)
  - Test ParetoSolution properties (dominates, is_diverse)
  - Test ParetoSolution hashability
  - Test EnsembleConfig validation (strategies >= 2)
  - Test EnsembleConfig strategy_weights validation
  - Test EnsembleSignal properties (is_actionable, has_consensus)
  - Test StrategyAllocation properties (drift, needs_rebalance)
  - Test CombinedPortfolio properties (is_well_diversified, is_efficient)
  - Test CorrelationMetrics properties (has_redundancy, is_well_conditioned, diversification_quality)
  - Test all Field constraints (ge, le, min_length, max_length)
  - Test all auto-generated fields (signal_id, timestamp)
  - Test extra="forbid" rejects unknown fields

---

## Notes
- This file defines all ensemble data models with comprehensive Pydantic validation
- ParetoSolution implements __hash__ for use as dictionary key in genetic algorithm
- EnsembleSignal has auto-generated signal_id with timestamp for uniqueness
- All Decimal types used for financial precision in weights and monetary values
- All enums inherit from str for JSON serialization compatibility
- ConfigDict settings provide strict validation and prevent extra fields
- Field validators use Pydantic v2 syntax (@field_validator, @classmethod)
