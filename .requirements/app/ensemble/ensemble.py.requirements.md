# ensemble.py

## Purpose
Implement ensemble voting methods (majority, weighted, soft, rank, performance, confidence) to combine trading signals from multiple strategies.

---

## Type Definitions / Data Classes

### EnsembleVoting Class
```python
class EnsembleVoting:
    config: EnsembleConfig                    # Ensemble configuration
    method: EnsembleMethod                    # Voting method to use
    strategies: List[str]                     # Strategy names (min 2)
    strategy_weights: Dict[str, float]        # Strategy weights (sum to 1.0)
    performance_history: Dict[str, List[float]] # Historical performance per strategy
```

---

## Function Signatures (Contracts)

### `__init__(config: EnsembleConfig) -> None`
**Pre:** config.strategies length >= 2, config valid
**Post:** Voting initialized with equal weights if none provided
**Raises:** ValueError if config invalid
**Retry:** No
**Side Effects:** Initializes performance_history for all strategies

### `combine_signals(signals: List[Signal]) -> Optional[EnsembleSignal]`
**Pre:** signals length == strategies length
**Post:** Returns EnsembleSignal or None if combination fails
**Raises:** ValueError if signal count mismatch
**Retry:** No
**Side Effects:** None (read-only)

### `_initialize_weights() -> Dict[str, float]`
**Pre:** strategies defined
**Post:** Returns equal weights (1.0 / n for each strategy)
**Raises:** None
**Retry:** No
**Side Effects:** None

### `_calculate_agreement(signals: List[Signal]) -> float`
**Pre:** signals not empty
**Post:** Returns agreement level (majority_count / total_count)
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

### `_majority_voting(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty
**Post:** Returns EnsembleSignal with majority decision
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_weighted_voting(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty, strategy_weights defined
**Post:** Returns EnsembleSignal with highest weighted score
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_soft_voting(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty
**Post:** Returns EnsembleSignal with highest avg confidence
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_rank_averaging(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty
**Post:** Returns EnsembleSignal with best average rank
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_performance_weighted(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty, performance_history has data
**Post:** Returns EnsembleSignal with performance-weighted votes
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_confidence_weighted(signals, agreement) -> EnsembleSignal`
**Pre:** signals not empty
**Post:** Returns EnsembleSignal with confidence-weighted votes
**Raises:** RuntimeError if voting fails
**Retry:** No
**Side Effects:** None

### `_calculate_performance_weights() -> Dict[str, float]`
**Pre:** performance_history initialized
**Post:** Returns normalized weights based on historical performance
**Raises:** None (returns equal weights on error)
**Retry:** No
**Side Effects:** None

### `update_performance(strategy, performance) -> None`
**Pre:** strategy in strategies list
**Post:** Appends performance to history, truncates to lookback_period
**Raises:** ValueError if strategy not found
**Retry:** No
**Side Effects:** Modifies performance_history

### `set_strategy_weights(weights) -> None`
**Pre:** weights has all strategies, sums to 1.0, non-negative
**Post:** Updates strategy_weights
**Raises:** ValueError if weights invalid
**Retry:** No
**Side Effects:** Updates instance variable

### `calculate_disagreement(signals) -> float`
**Pre:** signals not empty
**Post:** Returns 1.0 - agreement
**Raises:** None (returns 1.0 on error)
**Retry:** No
**Side Effects:** None

### `calculate_entropy(signals) -> float`
**Pre:** signals not empty
**Post:** Returns normalized entropy (0 to 1)
**Raises:** None (returns 0.0 on error)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] At least 2 strategies required
- [ ] Strategy weights sum to 1.0
- [ ] Agreement = majority_count / total_count
- [ ] Majority voting: most common signal type wins
- [ ] Weighted voting: highest weight sum wins
- [ ] Soft voting: highest average confidence wins
- [ ] Rank averaging: best (lowest) average rank wins
- [ ] Performance weighted: weights based on historical returns
- [ ] Confidence weighted: weights based on signal confidence
- [ ] Entropy normalized by max possible entropy

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules across 14 categories)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TRD-004 | BASE_RULES | Audit trail | ⚠️ NOT APPLIED - No audit logging |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Imports from models and signal |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions typed |
| LOG-004 | BASE_RULES | Log exceptions | ⚠️ NOT APPLIED - Silent fallbacks |
| SEC-007 | BASE_RULES | Input validation | ✅ OK - Validates signals and weights |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - Try/except with fallbacks |

---

## Dependencies
- **External:** collections (Counter), numpy (np), decimal (Decimal), typing
- **Internal:** app.ensemble.models (EnsembleConfig, EnsembleMethod, EnsembleSignal), app.models.signal (Signal, SignalType)

---

## Required Tests
- **tests/ensemble/test_ensemble.py:**
  - Test majority voting (unanimous/split/tie)
  - Test weighted voting (custom weights)
  - Test soft voting (confidence averaging)
  - Test rank averaging (confidence ranking)
  - Test performance weighted voting
  - Test confidence weighted voting
  - Test agreement calculation
  - Test disagreement calculation (1 - agreement)
  - Test entropy calculation (normalized)
  - Test performance weight calculation
  - Test strategy weight validation
  - Test performance history updates
  - Test signal combination with low agreement (returns None)
  - Test edge cases: empty signals, single strategy

---

## Notes
Ensemble methods reduce false signals by requiring agreement. Weight defaults to equal if not specified. Performance weights use lookback_period from config. Confidence threshold filters low-confidence signals before voting.
