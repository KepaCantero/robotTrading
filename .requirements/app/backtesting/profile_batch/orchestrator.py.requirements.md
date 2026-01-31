# orchestrator.py

## Purpose
Main orchestrator for batch backtesting with profile-driven optimization. Coordinates all components, manages parallel/sequential execution, and provides unified interface for running multi-profile backtests.

---

## Type Definitions / Data Classes

### ProfileBatchBacktester Class
```python
class ProfileBatchBacktester:
    config_path: str | Path                    # REQUIRED - Path to configuration YAML file
    config: Dict[str, Any]                     # Loaded from config_path
    profile_config_loader: ProfileConfigLoader | None  # Optional - may be None if init fails
    profile_generator: ProfileGenerator        # REQUIRED - Generates profile combinations
    baseline_executor: BaselineBacktestExecutor  # REQUIRED - Runs baseline backtests
    result_aggregator: ResultAggregator         # REQUIRED - Aggregates and stores results
    report_generator: ReportGenerator          # REQUIRED - Generates reports
    results: Dict[str, ProfileResult]          # Storage for backtest results
    _fallback_lock: threading.Lock             # Thread-safe fallback metrics
    _total_fallback_count: int                 # Total fallback counter
```

**Validation Rules:**
- `config_path` must exist and be valid YAML
- `profile_config_loader` can be None if initialization fails (fallback behavior)
- All components initialized in __init__ must be valid before use

---

## Function Signatures (Contracts)

### `ProfileBatchBacktester.__init__(config_path) -> None`
**Pre:** config_path must point to valid YAML file with required sections
**Post:** All components initialized, fallback metrics initialized with lock
**Raises:** FileNotFoundError, yaml.YAMLError for invalid config
**Retry:** ❌ No
**Side Effects:** Loads YAML, initializes all components, creates output directories

### `ProfileBatchBacktester.generate_all_profiles() -> List[InputProfile]`
**Pre:** config must be loaded, profile_generator must be initialized
**Post:** Returns list of all possible InputProfile combinations
**Raises:** ValueError, KeyError for missing config sections
**Retry:** ❌ No
**Side Effects:** None (pure delegation to profile_generator)

### `ProfileBatchBacktester.run_single_profile(profile, multi_strategy) -> ProfileResult`
**Pre:** profile must be valid InputProfile, all components must be initialized
**Post:** Returns ProfileResult with baseline, optimization, improvement metrics
**Raises:** ValueError, TypeError, KeyError, AttributeError for invalid inputs
**Retry:** ❌ No
**Side Effects:** Runs baseline backtest, runs optimization pipeline, stores result in database

### `ProfileBatchBacktester.run_all_profiles(parallel, max_workers) -> Dict[str, ProfileResult]`
**Pre:** All components must be initialized, profiles must be generatable
**Post:** Returns dict mapping profile_id to ProfileResult for all profiles
**Raises:** Concurrent futures errors for parallel execution failures
**Retry:** ✅ Yes - Individual profile failures don't stop batch
**Side Effects:** Runs backtests (parallel or sequential), generates summary report

### `ProfileBatchBacktester._run_parallel(profiles, max_workers) -> Dict[str, ProfileResult]`
**Pre:** max_workers must be positive, profiles must be valid list
**Post:** Returns results dict with completed profiles only
**Raises:** Concurrent futures execution errors
**Retry:** ✅ Yes - Failed profiles logged but don't stop batch
**Side Effects:** Spawns multiple processes, batch stores results after completion

### `ProfileBatchBacktester._run_sequential(profiles) -> Dict[str, ProfileResult]`
**Pre:** profiles must be valid list
**Post:** Returns results dict with successful profiles only
**Raises:** None (exceptions caught per profile)
**Retry:** ✅ Yes - Failed profiles logged but don't stop batch
**Side Effects:** Runs profiles one by one, stores each result

### `ProfileBatchBacktester._run_profile_worker(config_path, profile) -> ProfileResult` (static)
**Pre:** config_path must be valid, profile must be valid InputProfile
**Post:** Returns ProfileResult from single profile execution
**Raises:** Value/Type/Key/Attribute errors for invalid inputs
**Retry:** ❌ No
**Side Effects:** Creates new ProfileBatchBacktester instance, runs single profile

---

## Acceptance Criteria
- [ ] Orchestrator initializes all 5 required components (generator, executor, pipeline, aggregator, reporter)
- [ ] run_single_profile() returns ProfileResult with all required fields
- [ ] run_all_profiles() with parallel=True uses ProcessPoolExecutor
- [ ] run_all_profiles() with parallel=False runs sequentially
- [ ] Parallel execution uses configurable max_workers (default: 20)
- [ ] Failed profiles are logged but don't stop batch execution
- [ ] Batch summary is generated after all profiles complete
- [ ] Results are stored in database via ResultAggregator
- [ ] Fallback metrics are tracked thread-safely with lock
- [ ] Multi-strategy mode extracts per-strategy results when available
- [ ] ProfileBatchBacktester is pickle-able for ProcessPoolExecutor

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - Config from file |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Some methods lack return types |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Orchestrator pattern |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Coordinates only |
| DP-004 | BASE_RULES.md | Dependency injection | ✅ OK - Components injected |
| ASYNC-001 | BASE_RULES.md | Use async def | ❌ N/A - Sync multiprocessing used |
| QL-001 | BASE_RULES.md | Complexity < 10 | ⚠️ PARTIAL - run_single_profile is complex |
| TRD-004 | BASE_RULES.md | Audit trail logging | ⚠️ PARTIAL - Logging present but not structured |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** yaml, logging, threading, pathlib, concurrent.futures
- **Internal:**
  - `app.backtesting.profile_batch.profile_generator.ProfileGenerator`
  - `app.backtesting.profile_batch.baseline_executor.BaselineBacktestExecutor`
  - `app.backtesting.profile_batch.optimization_pipeline.OptimizationPipeline`
  - `app.backtesting.profile_batch.result_aggregator.ResultAggregator, ProfileResult`
  - `app.backtesting.profile_batch.report_generator.ReportGenerator`
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_orchestrator.py:**
  - Test __init__() loads config and initializes all components
  - Test __init__() handles ProfileConfigLoader initialization failure gracefully
  - Test generate_all_profiles() returns correct number of profiles
  - Test run_single_profile() returns ProfileResult with all fields
  - Test run_single_profile() with multi_strategy=True includes per-strategy results
  - Test run_all_profiles() with parallel=True uses ProcessPoolExecutor
  - Test run_all_profiles() with parallel=False runs sequentially
  - Test run_all_profiles() handles profile failures gracefully
  - Test _run_parallel() limits workers to max_workers
  - Test _run_parallel() batch stores results after completion
  - Test _run_sequential() continues on individual profile failures
  - Test _run_profile_worker() is pickle-able for multiprocessing
  - Test get_fallback_metrics() returns thread-safe metrics
  - Test log_fallback_summary() logs correct summary
  - Test export_results() delegates to ReportGenerator
  - Test generate_comparison_report() delegates to ReportGenerator
  - Test get_best_strategy() delegates to ResultAggregator

---

## Notes
- ProfileBatchBacktester must be pickle-able for ProcessPoolExecutor (no unpickle-able lambdas, threads, etc.)
- _fallback_lock uses threading.Lock for thread safety (not multiprocessing safe)
- run_single_profile() is complex (200+ lines) - consider breaking into smaller methods
- ProfileConfigLoader failure is logged but doesn't stop initialization (fallback behavior)
- Multi-strategy mode populates per_strategy_results from baseline_results
- Orchestrator follows the Orchestrator pattern - coordinates but doesn't implement business logic
