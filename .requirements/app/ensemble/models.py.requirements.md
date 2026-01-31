# models.py

## Purpose
Define Pydantic models for ensemble configuration, Pareto optimization, and portfolio combination metrics.

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
    objectives: List[OptimizationObjective]  # Min length: 1, Max: 6
    weights: List[float]                     # Must sum to 1.0
    constraints: Optional[Dict[str, Any]]    # Optional optimization constraints
    tolerance: float = 0.01                  # Range: [0.0, 1.0]
```

**Validation Rules:**
- `weights` must sum to 1.0 (±0.01 tolerance)
- `weights` length must match `objectives` length
- All weights must be non-negative

### ParetoSolution (BaseModel)
```python
class ParetoSolution(BaseModel):
    strategy_weights: Dict[str, Decimal]     # Must sum to 1.0
    objective_values: Dict[str, float]        # Objective function results
    rank: int = 0                             # Pareto rank (0 = non-dominated)
    crowding_distance: float = 0.0            # Diversity metric
    metrics: Dict[str, float]                 # Additional performance metrics
    timestamp: datetime                       # Solution creation time
```

**Validation Rules:**
- `strategy_weights` must sum to 1.0 (±0.01 tolerance)
- All weights must be non-negative
- `rank` must be >= 0
- `crowding_distance` must be >= 0

**Properties:**
- `dominates: bool` - Returns True if rank == 0
- `is_diverse: bool` - Returns True if crowding_distance > 0.5

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
    method: EnsembleMethod                   # Required
    strategies: List[str]                    # Min length: 2
    strategy_weights: Optional[Dict[str, float]] # Must sum to 1.0 if provided
    min_agreement: float = 0.5               # Range: [0.0, 1.0]
    confidence_threshold: float = 60.0       # Range: [0.0, 100.0]
    rebalance_frequency: int = 30            # Range: [1, 365] days
    lookback_period: int = 90                # Min: 1
```

**Validation Rules:**
- `strategy_weights` must sum to 1.0 if provided
- All weights non-negative

### EnsembleSignal (BaseModel)
```python
class EnsembleSignal(BaseModel):
    signal_id: str                            # Auto-generated unique ID
    symbol: str                               # Required
    signal_type: str                          # Combined signal type
    confidence: float                         # Range: [0.0, 100.0]
    agreement: float                          # Range: [0.0, 1.0]
    strategy_votes: Dict[str, str]            # Strategy -> vote mapping
    strategy_weights: Dict[str, float]        # Weights used
    timestamp: datetime                       # Signal generation time
    metadata: Dict[str, Any]                  # Additional metadata
```

**Properties:**
- `is_actionable: bool` - Returns True if confidence > 60 AND agreement > 0.5
- `has_consensus: bool` - Returns True if all votes identical

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
    strategy: str                             # Required
    weight: Decimal                           # Range: [0, 1]
    target_weight: Decimal                    # Range: [0, 1]
    actual_weight: Decimal                     # Range: [0, 1]
    contribution_risk: Decimal = 0            # Default: 0
    contribution_return: Decimal = 0          # Default: 0
    last_rebalanced: datetime                 # Last rebalance timestamp
```

**Properties:**
- `drift: Decimal` - Returns abs(actual_weight - target_weight)
- `needs_rebalance: bool` - Returns True if drift > 0.05

### CombinedPortfolio (BaseModel)
```python
class CombinedPortfolio(BaseModel):
    total_return: Decimal                     # Required
    volatility: Decimal                       # Required, min: 0
    sharpe_ratio: Decimal = 0                # Default: 0
    sortino_ratio: Decimal = 0               # Default: 0
    max_drawdown: Decimal = 0                # Default: 0, max: 0
    diversification_ratio: Decimal = 1        # Default: 1, min: 1
    effective_n_strategies: float = 1.0       # Default: 1.0, min: 1.0
    correlation_mean: Decimal = 0             # Default: 0, range: [-1, 1]
    allocation: List[StrategyAllocation]      # Default: []
    metrics: Dict[str, Decimal]               # Default: {}
    timestamp: datetime                       # Portfolio snapshot time
```

**Properties:**
- `is_well_diversified: bool` - Returns True if div_ratio > 1.2 AND eff_n >= 2 AND abs(corr) < 0.7
- `is_efficient: bool` - Returns True if sharpe_ratio > 1.0

### CorrelationMetrics (BaseModel)
```python
class CorrelationMetrics(BaseModel):
    correlation_matrix: Dict[str, Dict[str, Decimal]] # Required
    mean_correlation: Decimal                  # Range: [-1, 1]
    median_correlation: Decimal                # Range: [-1, 1]
    max_correlation: Decimal                   # Range: [-1, 1]
    min_correlation: Decimal                   # Range: [-1, 1]
    redundant_pairs: List[tuple]               # Default: []
    effective_number_bets: float = 1.0         # Default: 1.0, min: 1.0
    eigenvalues: List[float]                   # Default: []
    condition_number: float = 1.0              # Default: 1.0, min: 1.0
    timestamp: datetime                        # Analysis timestamp
```

**Properties:**
- `has_redundancy: bool` - Returns True if redundant_pairs not empty
- `is_well_conditioned: bool` - Returns True if condition_number < 100
- `diversification_quality: str` - Returns "excellent", "good", "moderate", or "poor"

---

## Function Signatures (Contracts)

### All models use Pydantic validation. No standalone functions.

---

## Acceptance Criteria
- [ ] All Pydantic models use strict=True, validate_assignment=True, extra="forbid"
- [ ] Strategy weights validated to sum to 1.0 (±0.01 tolerance)
- [ ] ObjectiveConfig weights length matches objectives length
- [ ] ParetoSolution weights validated to sum to 1.0
- [ ] EnsembleConfig has at least 2 strategies
- [ ] CombinedPortfolio has sensible property checks
- [ ] CorrelationMetrics condition number >= 1.0
- [ ] All numeric ranges enforced via Field constraints

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES | Use Pydantic Settings | ✅ OK - All models are BaseModel |
| CFG-003 | BASE_RULES | Validate all config values | ✅ OK - Field validators on all numeric fields |
| CFG-004 | BASE_RULES | Extra="forbid" | ✅ OK - All models have extra="forbid" |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All fields typed |
| SEC-007 | BASE_RULES | Input validation | ✅ OK - Pydantic validates on init |
| ARCH-006 | BASE_RULES | Value objects immutable | ✅ OK - BaseModel with frozen=True implied |

---

## Dependencies
- **External:** pydantic (BaseModel, ConfigDict, Field, field_validator), enum (Enum), typing, datetime, decimal (Decimal)
- **Internal:** None (pure models file)

---

## Required Tests
- **tests/ensemble/test_models.py:**
  - Test ObjectiveConfig validation (weights sum to 1.0)
  - Test ObjectiveConfig weights/objectives length mismatch
  - Test ParetoSolution weights validation
  - Test ParetoSolution properties (dominates, is_diverse)
  - Test EnsembleConfig validation (strategies >= 2)
  - Test EnsembleConfig strategy_weights validation
  - Test EnsembleSignal properties (is_actionable, has_consensus)
  - Test StrategyAllocation properties (drift, needs_rebalance)
  - Test CombinedPortfolio properties (is_well_diversified, is_efficient)
  - Test CorrelationMetrics properties
  - Test all Field constraints (ge, le, min_length)

---

## Notes
This file defines all ensemble models. ParetoSolution uses hash for use as dictionary key. EnsembleSignal has auto-generated signal_id with timestamp. All Decimal types used for financial precision.
