# result_aggregator.py

## Purpose
Aggregates and stores batch backtesting results in database, calculates improvement metrics, evaluates paper trading readiness, and queries best strategies.

---

## Type Definitions / Data Classes

### ProfileResultDB Class (SQLAlchemy ORM)
```python
class ProfileResultDB(Base):
    __tablename__ = "profile_results"
    id: Column(String, primary_key=True)           # REQUIRED - UUID
    profile_id: Column(String, unique=True, index=True)  # REQUIRED - Unique profile identifier
    objective: Column(String, index=True)           # REQUIRED - Investment objective
    risk_tolerance: Column(String, index=True)      # REQUIRED - Risk tolerance level
    capital_tier: Column(String, index=True)        # REQUIRED - Capital tier
    investment_horizon: Column(Integer)             # REQUIRED - Investment horizon in months
    baseline_sharpe: Column(Float)                  # OPTIONAL - Baseline Sharpe ratio
    baseline_return: Column(Float)                  # OPTIONAL - Baseline total return
    baseline_max_dd: Column(Float)                  # OPTIONAL - Baseline max drawdown
    baseline_win_rate: Column(Float)                # OPTIONAL - Baseline win rate
    optimized_sharpe: Column(Float)                 # OPTIONAL - Optimized Sharpe ratio
    optimized_return: Column(Float)                 # OPTIONAL - Optimized total return
    optimized_max_dd: Column(Float)                 # OPTIONAL - Optimized max drawdown
    optimized_win_rate: Column(Float)               # OPTIONAL - Optimized win rate
    sharpe_improvement: Column(Float)               # OPTIONAL - Sharpe improvement percentage
    return_improvement: Column(Float)               # OPTIONAL - Return improvement percentage
    max_dd_improvement: Column(Float)               # OPTIONAL - Max DD improvement percentage
    win_rate_improvement: Column(Float)             # OPTIONAL - Win rate improvement percentage
    best_parameters: Column(JSON)                   # OPTIONAL - Best parameters dict
    walk_forward_passed: Column(Boolean)            # OPTIONAL - Walk-forward validation passed
    monte_carlo_passed: Column(Boolean)             # OPTIONAL - Monte Carlo validation passed
    out_of_sample_passed: Column(Boolean)           # OPTIONAL - OOS validation passed
    ready_for_paper_trading: Column(Boolean)        # OPTIONAL - Paper trading ready flag
    recommendation: Column(String)                  # OPTIONAL - Text recommendation
    created_at: Column(DateTime)                    # REQUIRED - Creation timestamp
    updated_at: Column(DateTime)                    # REQUIRED - Last update timestamp
```

**Validation Rules:**
- profile_id must be unique (indexed)
- All float columns allow NULL
- JSON column validated by SQLAlchemy
- Timestamps auto-managed

### ProfileResult Class
```python
@dataclass
class ProfileResult:
    profile_id: str                                # REQUIRED - Unique identifier
    profile: InputProfile                           # REQUIRED - Input profile object
    baseline_results: Dict[str, Any]                # REQUIRED - Baseline metrics
    optimization_results: Dict[str, Any]            # REQUIRED - Optimized metrics
    best_parameters: Dict[str, Any]                 # REQUIRED - Best parameters
    improvement_metrics: Dict[str, float]           # REQUIRED - Improvement percentages
    comparison: Any                                 # REQUIRED - BaselineOptimizationComparison
    ready_for_paper_trading: bool                   # REQUIRED - Paper trading readiness
    recommendation: str                             # REQUIRED - Text recommendation
    created_at: datetime                            # REQUIRED - Creation timestamp
    strategy_mapping: Optional[StrategyMapping]     # OPTIONAL - Multi-strategy mapping
    enabled_strategies: List[str]                   # OPTIONAL - Enabled strategies list
    learning_engines: List[str]                     # OPTIONAL - Learning engines list
    ensemble_config: Dict[str, Any]                 # OPTIONAL - Ensemble configuration
    per_strategy_results: Dict[str, Dict[str, Any]] # OPTIONAL - Per-strategy results
```

**Validation Rules:**
- profile_id must be non-empty
- All required dicts must be non-empty
- ready_for_paper_trading is boolean

---

## Function Signatures (Contracts)

### `store_result(result) -> None`
**Pre:** result is valid ProfileResult with all required fields
**Post:** Result inserted or updated in database, committed
**Raises:** IntegrityError, OperationalError, DatabaseError (caught, logged, rolled back)
**Retry:** No
**Side Effects:** DB write (INSERT or UPDATE)

### `batch_store_results(results) -> None`
**Pre:** results is dict of profile_id to ProfileResult
**Post:** All results stored in DB within single transaction, logged
**Raises:** DatabaseError (caught, logged, rolled back)
**Retry:** No
**Side Effects:** DB write (multiple INSERTs/UPDATEs)

### `get_best_strategy(objective, tier, risk) -> Dict[str, Any]`
**Pre:** objective, tier, risk are valid enum values
**Post:** Returns dict with best configuration (max optimized_sharpe) or empty dict
**Raises:** None (returns {} if not found)
**Retry:** No
**Side Effects:** None (DB read)

### `calculate_improvements(baseline, optimized) -> Dict[str, float]`
**Pre:** baseline and optimized dicts have matching metric keys
**Post:** Returns dict with 4 improvement percentages
**Raises:** ZeroDivisionError if baseline value is 0 (handled, returns 0)
**Retry:** No
**Side Effects:** None (calculation)

### `evaluate_readiness(profile, optimized, improvements, acceptance_criteria) -> Tuple[bool, str]`
**Pre:** optimized has metrics, acceptance_criteria has thresholds
**Post:** Returns (ready: bool, recommendation: str) based on criteria
**Raises:** None
**Retry:** No
**Side Effects:** None (evaluation logic)

---

## Acceptance Criteria
- [ ] Database table created with all columns and indexes on profile_id, objective, risk_tolerance, capital_tier
- [ ] store_result() inserts new record or updates existing (upsert behavior)
- [ ] batch_store_results() uses single transaction for all operations
- [ ] Database errors logged and rolled back (no partial commits)
- [ ] get_best_strategy() returns strategy with max optimized_sharpe
- [ ] calculate_improvements() handles zero baseline values (returns 0)
- [ ] evaluate_readiness() checks: sharpe >= min_sharpe, return >= min_return, max_dd >= threshold, ready_for_paper_trading
- [ ] Ready if ALL checks pass, REVISION if sharpe >= 0.8 * min_sharpe, else REJECTED
- [ ] All SQLAlchemy exceptions caught and logged with context
- [ ] Session management: try/commit/except/rollback/finally/close pattern

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96 rules with 23 P0 critical)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK |
| LOG-001 | BASE_RULES | Structured logging | ✅ OK - Logging with context |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - All SQLAlchemy exceptions caught |
| ARCH-005 | BASE_RULES | Early returns | ⚠️ NOT APPLIED - Function flow is linear |
| BT-004 | BASE_RULES | Realistic costs | ⚠️ NOT APPLIED - Uses provided metrics |
| TRD-004 | BASE_RULES | Audit trail | ✅ OK - Database provides audit trail |
| DP-001 | BASE_RULES | Repository pattern | ✅ OK - ResultAggregator is repository |
| CC-007 | BASE_RULES | Small functions | ⚠️ NOT APPLIED - Some functions > 20 lines |

**NOTE:** Database operations are NOT in async functions - this is intentional for batch processing where async overhead is not needed.

---

## Dependencies
- **External:** logging, dataclasses, datetime, typing, uuid, sqlalchemy (create_engine, Column, types, declarative_base, sessionmaker)
- **Internal:**
  - `app.core.models.input_profile.InputProfile`
  - `app.services.profile_driven_trading.profile_strategy_mapper.StrategyMapping`

---

## Required Tests
- **tests/backtesting/profile_batch/test_result_aggregator.py:**
  - Test store_result() inserts new record
  - Test store_result() updates existing record (same profile_id)
  - Test batch_store_results() stores multiple records
  - Test batch_store_results() partial failure handling
  - Test get_best_strategy() returns max Sharpe strategy
  - Test get_best_strategy() returns empty dict when no results
  - Test calculate_improvements() with zero baseline
  - Test calculate_improvements() with positive baseline
  - Test evaluate_readiness() APPROVED (all checks pass)
  - Test evaluate_readiness() REVISION (marginal performance)
  - Test evaluate_readiness() REJECTED (fails criteria)
  - Test database error handling and rollback
  - Test session management (close in finally)

---

## Notes
Uses SQLAlchemy ORM with declarative_base. Database URL injected via constructor for testability.
