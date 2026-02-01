# profile_batch_backtester.py

## Purpose
Orchestrates batch testing with baseline AND optimization reporting. Manages 180+ profile combinations, Bayesian optimization, walk-forward validation, Monte Carlo simulation, and statistical comparison reporting.

---

## Type Definitions / Data Classes

### ProfileResultDB (SQLAlchemy Model)
```python
class ProfileResultDB(Base):
    __tablename__ = "profile_results"
    id: str  # REQUIRED - Primary key (UUID)
    profile_id: str  # REQUIRED - Unique identifier (indexed)
    objective: str  # REQUIRED - Investment objective (indexed)
    risk_tolerance: str  # REQUIRED - Risk level (indexed)
    capital_tier: str  # REQUIRED - Capital tier (indexed)
    investment_horizon: int  # REQUIRED - Months
    # Baseline metrics
    baseline_sharpe: float | None  # OPTIONAL - Baseline Sharpe ratio
    baseline_return: float | None  # OPTIONAL - Baseline total return
    baseline_max_dd: float | None  # OPTIONAL - Baseline max drawdown
    baseline_win_rate: float | None  # OPTIONAL - Baseline win rate
    # Optimization metrics
    optimized_sharpe: float | None  # OPTIONAL - Optimized Sharpe ratio
    optimized_return: float | None  # OPTIONAL - Optimized total return
    optimized_max_dd: float | None  # OPTIONAL - Optimized max drawdown
    optimized_win_rate: float | None  # OPTIONAL - Optimized win rate
    # Improvement metrics
    sharpe_improvement: float | None  # OPTIONAL - Sharpe improvement %
    return_improvement: float | None  # OPTIONAL - Return improvement %
    max_dd_improvement: float | None  # OPTIONAL - DD improvement %
    win_rate_improvement: float | None  # OPTIONAL - Win rate improvement %
    best_parameters: dict | None  # OPTIONAL - Best parameters (JSON)
    # Validation
    walk_forward_passed: bool | None  # OPTIONAL - Walk-forward validation result
    monte_carlo_passed: bool | None  # OPTIONAL - Monte Carlo validation result
    out_of_sample_passed: bool | None  # OPTIONAL - OOS validation result
    # Recommendation
    ready_for_paper_trading: bool | None  # OPTIONAL - Ready for paper trading
    recommendation: str | None  # OPTIONAL - Text recommendation
    # Metadata
    created_at: datetime  # REQUIRED - Creation timestamp
    updated_at: datetime  # REQUIRED - Last update timestamp
```

**Validation Rules:**
- profile_id must be unique (database constraint)
- investment_horizon must be positive (months)
- All percentage metrics should be in decimal form (0.15 = 15%)
- to_dict() method returns dictionary representation

### BaselineOptimizationComparison
```python
@dataclass
class BaselineOptimizationComparison:
    sharpe_improvement: float  # REQUIRED - Percentage improvement
    return_improvement: float  # REQUIRED - Percentage improvement
    max_dd_improvement: float  # REQUIRED - Percentage improvement (positive is better)
    win_rate_improvement: float  # REQUIRED - Percentage improvement
    sharpe_significant: bool  # REQUIRED - Statistical significance of Sharpe
    return_significant: bool  # REQUIRED - Statistical significance of return
    parameter_importance: dict[str, float]  # REQUIRED - Parameter sensitivity scores
    recommended: str  # REQUIRED - "baseline", "optimized", or "inconclusive"
    confidence: float  # REQUIRED - 0-1 confidence score
    reason: str  # REQUIRED - Text explanation
```

**Validation Rules:**
- confidence must be in range [0, 1]
- recommended must be one of: "baseline", "optimized", "inconclusive"
- All improvement percentages are floats (e.g., 15.5 for 15.5%)

### OptimizedStrategy
```python
@dataclass
class OptimizedStrategy:
    profile_id: str  # REQUIRED - Profile identifier
    baseline_metrics: dict  # REQUIRED - Baseline performance metrics
    optimized_metrics: dict  # REQUIRED - Optimized performance metrics
    best_parameters: dict  # REQUIRED - Optimal parameter values
    optimization_history: list[dict]  # REQUIRED - Optuna trial history
    walk_forward_results: dict | None  # OPTIONAL - Walk-forward validation results
    monte_carlo_results: dict | None  # OPTIONAL - Monte Carlo simulation results
    out_of_sample_results: dict | None  # OPTIONAL - Out-of-sample test results
    comparison: BaselineOptimizationComparison  # REQUIRED - Comparison analysis
    ready_for_paper_trading: bool  # REQUIRED - Deployment readiness flag
    recommendation: str  # REQUIRED - Text recommendation
```

**Validation Rules:**
- optimization_history contains Optuna trial dictionaries
- ready_for_paper_trading requires all validations passed
- comparison must contain statistical significance tests

### ProfileResult
```python
@dataclass
class ProfileResult:
    profile_id: str  # REQUIRED - Profile identifier
    profile: InputProfile  # REQUIRED - Input profile object
    baseline_results: dict  # REQUIRED - Baseline metrics
    optimization_results: dict  # REQUIRED - Optimization metrics
    best_parameters: dict  # REQUIRED - Best parameters found
    improvement_metrics: dict[str, float]  # REQUIRED - Improvement calculations
    comparison: BaselineOptimizationComparison  # REQUIRED - Comparison object
    ready_for_paper_trading: bool  # REQUIRED - Deployment readiness
    recommendation: str  # REQUIRED - Text recommendation
    created_at: datetime  # REQUIRED - Timestamp (default: now)
    # Multi-strategy support (optional)
    strategy_mapping: StrategyMapping | None  # OPTIONAL - Strategy mapping object
    enabled_strategies: list[str]  # OPTIONAL - List of enabled strategies
    learning_engines: list[str]  # OPTIONAL - Learning engine names
    ensemble_config: dict  # OPTIONAL - Ensemble configuration
    per_strategy_results: dict  # OPTIONAL - Per-strategy metrics
```

**Validation Rules:**
- created_at defaults to datetime.now()
- Multi-strategy fields optional for backward compatibility
- All required metrics must be present before database storage

---

## Function Signatures (Contracts)

### `__init__(config_path: str) -> None`
**Pre:** config_path must exist and be valid YAML file
**Post:** ProfileBatchBacktester initialized with database, output_dir, config loaded
**Raises:** FileNotFoundError, yaml.YAMLError (invalid config), ValueError (missing required config)
**Retry:** No
**Side Effects:** Creates database tables, output directories, loads configuration

### `generate_all_profiles() -> List[InputProfile]`
**Pre:** Configuration loaded with capital_tiers and investment_horizons
**Post:** Returns list of InputProfile combinations (5 objectives × 3 risks × 3 tiers × N horizons)
**Raises:** No (returns empty list on error)
**Retry:** No
**Side Effects:** None (pure function)

### `run_single_profile(profile: InputProfile, multi_strategy: bool = False) -> ProfileResult`
**Pre:** profile must be valid InputProfile with capital_initial > 0
**Post:** Returns ProfileResult with baseline, optimization, comparison, recommendation
**Raises:** DatabaseError (storage failure), RuntimeError (backtest failure)
**Retry:** Yes (on database errors, max 3 attempts)
**Side Effects:** Stores result in database, logs to diagnostic logger

### `run_all_profiles(parallel: bool = True, max_workers: int = 20) -> Dict[str, ProfileResult]`
**Pre:** Configuration valid, database accessible
**Post:** Returns dict of profile_id -> ProfileResult for all combinations
**Raises:** No (continues on individual profile failures)
**Retry:** Yes (individual profile retry on failure)
**Side Effects:** Parallel execution with ProcessPoolExecutor, batch database storage

### `_run_baseline(profile: InputProfile, config: dict, multi_strategy: bool = False) -> dict`
**Pre:** profile valid, config contains required backtest parameters
**Post:** Returns baseline metrics dict (sharpe_ratio, return_pct, max_drawdown, win_rate, etc.)
**Raises:** RuntimeError (backtest execution failure)
**Retry:** No
**Side Effects:** Executes ComprehensiveBacktestRunner, creates temporary config file

### `_run_optimization_pipeline(...) -> OptimizedStrategy`
**Pre:** profile valid, config valid, baseline_metrics available
**Post:** Returns OptimizedStrategy with Optuna optimization and validation results
**Raises:** RuntimeError (optimization failure), DatabaseError (storage failure)
**Retry:** Yes (Optuna trials, max 100 attempts)
**Side Effects:** Runs Optuna study, stores trials, executes validations

### `log_fallback_summary() -> None`
**Pre:** None
**Post:** Logs summary of fallback metrics at INFO level
**Raises:** No
**Retry:** No
**Side Effects:** Logging only

---

## Acceptance Criteria
- [ ] AC-001: All 180+ profile combinations generated correctly (5×3×3×N)
- [ ] AC-002: Parallel execution completes without race conditions (thread-safe fallback counters)
- [ ] AC-003: Database storage handles SQLite concurrency correctly (sequential batch storage)
- [ ] AC-004: Fallback metrics tracked accurately for ProfileConfigLoader and ProfileStrategyMapper
- [ ] AC-005: Baseline and optimization metrics compared with statistical significance tests
- [ ] AC-006: Walk-forward validation executes with Tomasini methodology (50% step size)
- [ ] AC-007: Monte Carlo simulation generates 1000+ equity curve paths
- [ ] AC-008: Out-of-sample testing uses 20% holdout data
- [ ] AC-009: Investment horizons loaded from config (dict or list format)
- [ ] AC-010: Tier mapping uses centralized TierMapper for consistency
- [ ] AC-011: Multi-strategy execution aggregates per-strategy results correctly
- [ ] AC-012: Database rollback on error, commit on success
- [ ] AC-013: Temporary config files cleaned up after execution
- [ ] AC-014: Error handling for all SQLAlchemy exceptions (IntegrityError, OperationalError, etc.)
- [ ] AC-015: Type hints cover all function signatures (mypy --strict)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | 02-type-hints.md | 100% type coverage for all functions | ✅ OK |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ✅ OK |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK |
| CC-006 | 05-architecture.md | Explicit error handling | ✅ OK (comprehensive exception handling) |
| ASYNC-007 | 07-async-patterns.md | Use ProcessPoolExecutor for CPU-bound work | ✅ OK (parallel execution) |
| DP-004 | 04-design-patterns.md | Dependency injection | ✅ OK (ProfileConfigLoader, ProfileStrategyMapper injected) |
| BT-001 | 13-trading-specific-rules | Walk-forward validation required | ✅ OK (Tomasini methodology) |
| BT-002 | 13-trading-specific-rules | Out-of-sample testing required | ✅ OK (20% holdout) |
| BT-003 | 13-trading-specific-rules | No look-ahead bias | ✅ OK (temporal data splitting) |
| BT-004 | 13-trading-specific-rules | Realistic costs (slippage, commission) | ✅ OK (in config) |
| SEC-001 | 28-security-and-secrets.md | No hardcoded secrets | ✅ OK (config from YAML) |
| CFG-002 | 08-configuration.md | Environment variables for deployment | ✅ OK (database_url from config) |
| QL-001 | 00-checklist.md | Complexity < 10 per function | ⚠️ NOT APPLIED - Complex orchestration logic |
| TST-004 | 06-testing.md | Mock external deps in tests | ❌ GAP - Tests mock ComprehensiveBacktestRunner? |
| ARCH-001 | 05-architecture.md | Layered architecture (no domain coupling) | ✅ OK (orchestration layer) |

**NOTE:** This analysis should consider ALL 81 rules from /rules directory.

---

## Dependencies
- **External:** numpy, pandas, optuna, yaml, sqlalchemy, jinja2
- **Internal:**
  - app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner
  - app.backtesting.professional_reporter.ProfessionalReporter
  - app.core.config.profile_config_loader.ProfileConfigLoader
  - app.core.models.input_profile.InputProfile, ObjectivoInversion, RiskTolerance
  - app.core.tier_mapper.map_profile_tier_to_config
  - app.services.profile_driven_trading.profile_strategy_mapper.create_profile_mapper

---

## Required Tests
- **tests/unit/backtesting/test_profile_batch_backtester.py:**
  - Test generate_all_profiles creates correct combinations
  - Test parallel execution without race conditions (thread-safe counters)
  - Test fallback metrics tracking (ProfileConfigLoader, ProfileStrategyMapper)
  - Test database storage handles SQLite concurrency
  - Test investment horizons loading (dict and list formats)
  - Test tier mapping with centralized TierMapper
  - Test multi-strategy execution aggregation
  - Test database rollback on error
  - Test comprehensive error handling for all SQLAlchemy exceptions
  - Test temporary config file cleanup

- **tests/integration/backtesting/test_profile_batch_integration.py:**
  - Test full workflow: generate -> run -> store -> report
  - Test Optuna optimization convergence
  - Test walk-forward validation with Tomasini methodology
  - Test Monte Carlo simulation (1000+ paths)
  - Test out-of-sample testing (20% holdout)
  - Test baseline vs optimization comparison with statistical significance
  - Test parallel execution with 20 workers
  - Test database persistence and retrieval

---

## Notes
- Uses ProcessPoolExecutor for CPU-bound parallel execution (not ThreadPoolExecutor)
- Implements sequential batch storage after parallel execution to avoid SQLite race conditions
- Fallback mechanism tracks configuration failures for monitoring
- Integrates with ProfileStrategyMapper for multi-strategy support
- Generates 180+ profile combinations (can be configured via investment_horizons)
