# profile_batch_backtester.py

## Purpose
Orchestrates comprehensive batch backtesting for investor profiles (180 combinations) with baseline testing, Bayesian optimization (Optuna), walk-forward validation, Monte Carlo simulation, out-of-sample testing, and statistical comparison reporting with database persistence.

---

## Type Definitions / Data Classes

### ProfileResultDB Class (SQLAlchemy Model)
```python
class ProfileResultDB(Base):
    """Database model for profile results."""
    __tablename__ = "profile_results"

    id: str (Column, PK)                          # REQUIRED - UUID
    profile_id: str (Column, unique)               # REQUIRED - Unique profile identifier
    objective: str (Column)                        # REQUIRED - Investment objective
    risk_tolerance: str (Column)                   # REQUIRED - Risk level (bajo/medio/alto)
    capital_tier: str (Column)                     # REQUIRED - Capital tier
    investment_horizon: int (Column)               # REQUIRED - Horizon in months
    # Baseline results
    baseline_sharpe: float (Column)                # OPTIONAL - Baseline Sharpe ratio
    baseline_return: float (Column)                # OPTIONAL - Baseline total return
    baseline_max_dd: float (Column)                # OPTIONAL - Baseline max drawdown
    baseline_win_rate: float (Column)              # OPTIONAL - Baseline win rate
    # Optimization results
    optimized_sharpe: float (Column)               # OPTIONAL - Optimized Sharpe ratio
    optimized_return: float (Column)               # OPTIONAL - Optimized total return
    optimized_max_dd: float (Column)               # OPTIONAL - Optimized max drawdown
    optimized_win_rate: float (Column)             # OPTIONAL - Optimized win rate
    # Improvement metrics
    sharpe_improvement: float (Column)             # OPTIONAL - Sharpe improvement %
    return_improvement: float (Column)             # OPTIONAL - Return improvement %
    max_dd_improvement: float (Column)             # OPTIONAL - Drawdown improvement %
    win_rate_improvement: float (Column)           # OPTIONAL - Win rate improvement %
    # Best parameters
    best_parameters: JSON (Column)                 # OPTIONAL - Best params from Optuna
    # Validation results
    walk_forward_passed: bool (Column)             # OPTIONAL - Walk-forward validation passed
    monte_carlo_passed: bool (Column)              # OPTIONAL - Monte Carlo validation passed
    out_of_sample_passed: bool (Column)            # OPTIONAL - Out-of-sample validation passed
    # Final recommendation
    ready_for_paper_trading: bool (Column)         # OPTIONAL - Ready for production
    recommendation: str (Column)                   # OPTIONAL - Text recommendation
    # Metadata
    created_at: datetime (Column)                  # Auto - Creation timestamp
    updated_at: datetime (Column)                  # Auto - Last update timestamp
```

**Validation Rules:**
- `profile_id` is unique (database constraint)
- All float columns can be NULL (not all metrics may be calculated)
- Boolean flags default to NULL (not all validations run)
- `investment_horizon > 0`

---

### BaselineOptimizationComparison Class
```python
@dataclass
class BaselineOptimizationComparison:
    sharpe_improvement: float                    # REQUIRED - Percentage improvement
    return_improvement: float                    # REQUIRED - Percentage improvement
    max_dd_improvement: float                    # REQUIRED - Positive is better
    win_rate_improvement: float                 # REQUIRED - Percentage improvement
    sharpe_significant: bool                     # REQUIRED - Statistical significance
    return_significant: bool                     # REQUIRED - Statistical significance
    parameter_importance: Dict[str, float]       # REQUIRED - Optuna importance scores
    recommended: str                             # REQUIRED - "baseline", "optimized", "inconclusive"
    confidence: float                            # REQUIRED - 0-1 confidence level
    reason: str                                  # REQUIRED - Explanation
```

**Validation Rules:**
- `0 <= confidence <= 1`
- `recommended in ["baseline", "optimized", "inconclusive"]`
- `parameter_importance` values sum to ~1.0

---

### OptimizedStrategy Class
```python
@dataclass
class OptimizedStrategy:
    profile_id: str                              # REQUIRED - Profile identifier
    baseline_metrics: Dict[str, Any]             # REQUIRED - Baseline performance
    optimized_metrics: Dict[str, Any]            # REQUIRED - Optimized performance
    best_parameters: Dict[str, Any]              # REQUIRED - Best parameters from Optuna
    optimization_history: List[Dict[str, Any]]   # REQUIRED - All Optuna trials
    walk_forward_results: Optional[Dict[str, Any]] # OPTIONAL - Walk-forward validation
    monte_carlo_results: Optional[Dict[str, Any]]  # OPTIONAL - Monte Carlo simulation
    out_of_sample_results: Optional[Dict[str, Any]] # OPTIONAL - Out-of-sample test
    comparison: BaselineOptimizationComparison   # REQUIRED - Comparison object
    ready_for_paper_trading: bool                # REQUIRED - Production readiness
    recommendation: str                          # REQUIRED - Text recommendation
```

**Validation Rules:**
- `0.0 <= comparison.confidence <= 1.0`
- `optimization_history` has at least one trial

---

### ProfileResult Class
```python
@dataclass
class ProfileResult:
    profile_id: str                              # REQUIRED - Unique identifier
    profile: InputProfile                        # REQUIRED - Profile configuration
    baseline_results: Dict[str, Any]             # REQUIRED - Baseline metrics
    optimization_results: Dict[str, Any]         # REQUIRED - Optimized metrics
    best_parameters: Dict[str, Any]              # REQUIRED - Best parameters
    improvement_metrics: Dict[str, float]        # REQUIRED - Improvement percentages
    comparison: BaselineOptimizationComparison   # REQUIRED - Comparison object
    ready_for_paper_trading: bool                # REQUIRED - Production flag
    recommendation: str                          # REQUIRED - Recommendation text
    created_at: datetime                         # Auto - Creation timestamp
    # Multi-strategy support fields
    strategy_mapping: Optional[StrategyMapping]  # OPTIONAL - Strategy mapping
    enabled_strategies: List[str]                # OPTIONAL - Enabled strategies
    learning_engines: List[str]                  # OPTIONAL - ML engines
    ensemble_config: Dict[str, Any]              # OPTIONAL - Ensemble configuration
    per_strategy_results: Dict[str, Dict[str, Any]] # OPTIONAL - Per-strategy results
```

---

## Function Signatures (Contracts)

### `ProfileBatchBacktester.__init__(config_path: str) -> None`
**Pre:** config_path points to valid YAML file with database, output_dir, capital_tiers, horizons, optimization, validation configs
**Post:** Backtester initialized with database engine, Session, output directories, config loader
**Raises:** ValueError if required configs missing, SQLAlchemy errors (logged, falls back to None for profile_config_loader/profile_mapper)
**Retry:** ❌ No
**Side Effects:** Creates database tables, creates output directories, initializes ProfileConfigLoader and ProfileStrategyMapper

---

### `ProfileBatchBacktester._load_config() -> Dict[str, Any]`
**Pre:** config_path points to valid YAML file
**Post:** Returns loaded config dict
**Raises:** FileNotFoundError, YAMLError (propagates)
**Retry:** ❌ No
**Side Effects:** None (reads file only)

---

### `ProfileBatchBacktester._increment_fallback_counter(fallback_type: str) -> None`
**Pre:** fallback_type in ["profile_config_loader", "profile_strategy_mapper", "config_key_mismatch"]
**Post:** Thread-safe increment of counter
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Modifies counter (thread-safe via lock)

---

### `ProfileBatchBacktester._validate_configurations() -> None`
**Pre:** None
**Post:** Validates capital_tiers, investment_horizons, optimization, validation configs exist
**Raises:** ValueError if capital_tiers or investment_horizons missing
**Retry:** ❌ No
**Side Effects:** Logs warnings for missing configs

---

### `ProfileBatchBacktester.get_fallback_metrics() -> Dict[str, int]`
**Pre:** None
**Post:** Returns dict with profile_config_loader_fallback_count, profile_strategy_mapper_fallback_count, config_key_mismatch_count
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (thread-safe read)

---

### `ProfileBatchBacktester.log_fallback_summary() -> None`
**Pre:** None
**Post:** Logs summary of all fallback metrics with interpretation
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (logging only)

---

### `ProfileBatchBacktester._load_investment_horizons() -> List[int]`
**Pre:** None
**Post:** Returns list of horizon values in months (positive integers)
**Raises:** ❌ No (returns defaults if config invalid)
**Retry:** ❌ No
**Side Effects:** Logs warnings for invalid values

---

### `ProfileBatchBacktester.generate_all_profiles() -> List[InputProfile]`
**Pre:** Config has valid capital_tiers
**Post:** Returns list of InputProfile combinations (objectives × risks × tiers × horizons = ~180 profiles)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (generates profiles)

---

### `ProfileBatchBacktester._get_capital_tier_key(profile: InputProfile) -> str`
**Pre:** profile has valid capital_flag
**Post:** Returns mapped tier key ("bajo", "medio", "alto") for config lookups
**Raises:** ❌ No (returns fallback "medio" if mapping fails)
**Retry:** ❌ No
**Side Effects:** Logs warning if tier mapper fails

---

### `ProfileBatchBacktester.run_single_profile(profile: InputProfile, multi_strategy: bool = False) -> ProfileResult`
**Pre:** profile is valid InputProfile
**Post:** Returns ProfileResult with baseline and optimization results
**Raises:** Exception (caught, logged, re-raised)
**Retry:** ❌ No
**Side Effects:** Creates temp config file, runs backtest, saves to database

---

### `ProfileBatchBacktester.run_all_profiles(parallel: bool = False, max_workers: int = 20) -> Dict[str, ProfileResult]`
**Pre:** None
**Post:** Returns dict of profile_id → ProfileResult for all generated profiles
**Raises:** Exception in parallel mode (caught, logged)
**Retry:** ❌ No
**Side Effects:** Runs backtests sequentially or in parallel, saves to database

---

### `ProfileBatchBacktester.get_best_strategy(objective: str, tier: str, risk: str) -> Optional[Dict]`
**Pre:** objective, tier, risk are valid values
**Post:** Returns best strategy config for given criteria
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (queries results dict)

---

### `ProfileBatchBacktester.generate_comparison_report() -> str`
**Pre:** At least one profile result exists
**Post:** Returns HTML report with comparison tables
**Raises:** Exception (propagates)
**Retry:** ❌ No
**Side Effects:** Uses Jinja2 template for rendering

---

### `ProfileBatchBacktester.export_results(format: str = "json") -> str`
**Pre:** format in ["json", "csv", "html"]
**Post:** Returns path to exported file
**Raises:** Exception (propagates)
**Retry:** ❌ No
**Side Effects:** Writes file to output_dir

---

## Acceptance Criteria
- [ ] __init__ creates database tables if not exist
- [ ] __init__ initializes ProfileConfigLoader (falls back to None if error)
- [ ] __init__ initializes ProfileStrategyMapper (falls back to None if error)
- [ ] _validate_configurations raises ValueError if capital_tiers missing
- [ ] _validate_configurations raises ValueError if investment_horizons missing
- [ ] generate_all_profiles creates 5 objectives × 3 risks × 3 tiers × N horizons combinations
- [ ] _load_investment_horizons supports dict format {short: 12, medium: 24, ...}
- [ ] _load_investment_horizons supports list format [12, 24, 36, 60]
- [ ] _load_investment_horizons validates horizons > 0
- [ ] _load_investment_horizons returns defaults [12, 24, 36, 60] if config invalid
- [ ] _get_capital_tier_key uses map_profile_tier_to_config for consistency
- [ ] _get_capital_tier_key falls back to manual mapping if tier mapper fails
- [ ] run_single_profile creates temp config file for profile
- [ ] run_single_profile extracts strategy_mapping_metadata from config
- [ ] run_single_profile logs enabled_strategies, learning_engines, ensemble_mode
- [ ] run_all_profiles supports parallel execution with ProcessPoolExecutor
- [ ] run_all_profiles limits parallel workers to max_workers (default 20)
- [ ] _increment_fallback_counter is thread-safe (uses threading.Lock)
- [ ] get_fallback_metrics returns all three counters in dict
- [ ] log_fallback_summary interprets fallback counts (0=good, <5=low, <20=moderate, >=20=high)
- [ ] Database model ProfileResultDB has unique constraint on profile_id
- [ ] All database error handlers log errors and handle gracefully

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SOL-001 | BASE_RULES.md | Single Responsibility Principle | ⚠️ PARTIAL - Class handles orchestration, DB I/O, reporting (too broad) |
| SOL-005 | BASE_RULES.md | Dependency Inversion | ✅ OK - Uses ProfileConfigLoader, ProfileStrategyMapper abstractions |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Injects config_path, uses factory methods |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Catches SQLAlchemy errors, falls back gracefully |
| CC-007 | BASE_RULES.md | Small functions | ⚠️ ACCEPTED - run_single_profile() is ~80 lines due to: 1) Complex orchestration of baseline + optimization pipelines, 2) Multi-strategy result aggregation, 3) Strategy mapping metadata extraction, 4) Database persistence, 5) Readiness evaluation. Lower priority code style issue, no functional impact. Future refactoring could extract helper methods for config setup, result aggregation, and database operations. |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ FIXED - 2026-02-01 - Added type aliases (ConfigDict, MetricsDict, ParameterDict, ValidationResultDict, PerStrategyResultsDict, OptimizationHistoryEntry) and updated all return types |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ FIXED - 2026-02-01 - Added specific type aliases replacing Dict[str, Any] with more specific types where appropriate |
| ASYNC-007 | BASE_RULES.md | Run blocking in executor | ✅ OK - Uses ProcessPoolExecutor for parallel backtests |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - Supports walk_forward_results |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - Supports out_of_sample_results |
| BT-003 | BASE_RULES.md | No look-ahead bias | ✅ OK - Uses ComprehensiveBacktestRunner (should validate) |
| BT-004 | BASE_RULES.md | Realistic costs | ✅ OK - Uses ComprehensiveBacktestRunner (should include costs) |
| LOG-001 | BASE_RULES.md | Structured logging | ✅ OK - Uses logging module with context |
| LOG-004 | BASE_RULES.md | Log exceptions | ✅ OK - Logs all exceptions with context |
| ARCH-001 | BASE_RULES.md | Layered architecture (application) | ✅ OK - Application layer (orchestration) |

**NOTE:** This analysis considers ALL 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `yaml` (YAML config loading)
  - `sqlalchemy` (create_engine, declarative_base, sessionmaker, Column, JSON, Boolean, etc.)
  - `sqlalchemy.exc` (DatabaseError, IntegrityError, etc.)
  - `dataclasses` (dataclass, field)
  - `datetime` (datetime)
  - `decimal` (Decimal)
  - `pathlib` (Path)
  - `uuid` (uuid4)
  - `typing` (Any, Dict, List, Optional, Tuple)
  - `logging` (logger)
  - `threading` (Lock for thread safety)
  - `concurrent.futures` (ProcessPoolExecutor, as_completed)
  - `numpy` (np)
  - `pandas` (pd)
  - `optuna` (Bayesian optimization)
  - `jinja2` (Template for HTML reports)
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.backtesting.professional_reporter.ProfessionalReporter`
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile, ObjectivoInversion, RiskTolerance`
  - `app.core.tier_mapper.map_profile_tier_to_config`
  - `app.services.profile_driven_trading.profile_strategy_mapper.create_profile_mapper, StrategyMapping`

---

## Required Tests
- **tests/backtesting/test_profile_batch_backtester.py:**
  - Test __init__ creates database tables
  - Test __init__ initializes ProfileConfigLoader
  - Test __init__ falls back to None if ProfileConfigLoader fails
  - Test __init__ initializes ProfileStrategyMapper
  - Test __init__ increments fallback counter on mapper failure
  - Test __init__ creates output directory
  - Test _validate_configurations raises ValueError for missing capital_tiers
  - Test _validate_configurations raises ValueError for missing investment_horizons
  - Test _validate_configurations logs warnings for missing optimization config
  - Test _validate_configurations logs warnings for missing validation config
  - Test _load_investment_horizons with dict format
  - Test _load_investment_horizons with list format
  - Test _load_investment_horizons returns defaults for invalid format
  - Test _load_investment_horizons validates positive integers
  - Test _load_investment_horizons skips invalid values with error logging
  - Test _load_investment_horizons warns about out-of-range values (1-360 months)
  - Test _load_investment_horizons returns defaults if no valid values
  - Test generate_all_profiles creates correct number of combinations
  - Test generate_all_profiles includes all objectives
  - Test generate_all_profiles includes all risk tolerances
  - Test generate_all_profiles includes all capital tiers
  - Test generate_all_profiles includes all investment horizons
  - Test _get_capital_tier_key uses map_profile_tier_to_config
  - Test _get_capital_tier_key falls back to manual mapping on error
  - Test _get_capital_tier_key logs warning on fallback
  - Test _increment_fallback_counter increments profile_config_loader_fallback_count
  - Test _increment_fallback_counter increments profile_strategy_mapper_fallback_count
  - Test _increment_fallback_counter increments config_key_mismatch_count
  - Test _increment_fallback_counter is thread-safe (concurrent calls)
  - Test get_fallback_metrics returns all three counters
  - Test get_fallback_metrics is thread-safe
  - Test log_fallback_summary logs all metrics
  - Test log_fallback_summary interprets 0 as "No fallbacks"
  - Test log_fallback_summary interprets <5 as "Low fallback count"
  - Test log_fallback_summary interprets <20 as "Moderate fallback count" (warning)
  - Test log_fallback_summary interprets >=20 as "High fallback count" (error)
  - Test run_single_profile creates ProfileResult
  - Test run_single_profile saves to database
  - Test run_all_profiles runs sequentially when parallel=False
  - Test run_all_profiles runs in parallel when parallel=True
  - Test run_all_profiles respects max_workers limit
  - Test run_all_profiles handles exceptions gracefully
  - Test get_best_strategy returns best configuration
  - Test generate_comparison_report returns HTML
  - Test export_results exports to JSON
  - Test export_results exports to CSV
  - Test export_results exports to HTML
  - Test ProfileResultDB.to_dict converts all fields correctly
  - Test database unique constraint on profile_id

---

## Notes
This is a complex orchestration class that manages batch backtesting workflows. Key concerns: 1) Thread safety for fallback counters (uses threading.Lock). 2) Graceful degradation - falls back to None for ProfileConfigLoader/ProfileStrategyMapper if initialization fails. 3) Multi-format config support (dict vs list for investment_horizons). 4) Parallel execution with ProcessPoolExecutor for performance. 5) Database persistence with SQLAlchemy ORM. 6) Comprehensive validation with walk-forward, Monte Carlo, out-of-sample testing. 7) Statistical comparison between baseline and optimized results.

**Known issues (GAPs):** Class too broad (violates SRP) - should split into orchestrator, repository, reporter classes. Uses Dict[str, Any] extensively (could use TypedDict or dataclasses for better type safety). Some methods very long (>50 lines) - **CC-007 ACCEPTED** as documented above (lower priority, complex orchestration logic).
