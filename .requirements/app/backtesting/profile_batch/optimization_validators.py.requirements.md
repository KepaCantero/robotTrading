# optimization_validators.py

## Purpose
Provides validation components for the optimization pipeline including walk-forward validation, Monte Carlo simulation, and out-of-sample validation.

---

## Type Definitions / Data Classes

### WalkForwardValidator Class
```python
class WalkForwardValidator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]         # REQUIRED - Validation configuration
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `validation_config` must contain "walk_forward" section with n_windows and train_percentage
- `profile_config_loader` can be None

### MonteCarloSimulator Class
```python
class MonteCarloSimulator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]         # REQUIRED - Validation configuration
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `validation_config` must contain "monte_carlo" section with n_simulations and min_profitable_pct
- `profile_config_loader` can be None

### OutOfSampleValidator Class
```python
class OutOfSampleValidator:
    output_dir: Path                          # REQUIRED - Directory for temporary files
    validation_config: Dict[str, Any]         # REQUIRED - Validation configuration
    profile_config_loader: ProfileConfigLoader | None  # OPTIONAL - Profile config loader
```

**Validation Rules:**
- `validation_config` must contain "out_of_sample" section with train_percentage, min_oos_sharpe, max_performance_decay
- `profile_config_loader` can be None

### Type Aliases
```python
ConfigDict = Dict[str, Any]                              # Configuration dictionary
MetricsDict = Dict[str, Union[float, int, str, bool, None]]  # Metrics dictionary
ValidationResultDict = Dict[str, Any]                    # Contains 'passed' bool and validation metrics
```

---

## Function Signatures (Contracts)

### `WalkForwardValidator.__init__(output_dir, validation_config, profile_config_loader) -> None`
**Pre:** output_dir must be valid path
**Post:** WalkForwardValidator initialized
**Raises:** No
**Retry:** No
**Side Effects:** None (stores references)

### `WalkForwardValidator.validate(profile, config, params) -> ValidationResultDict`
**Pre:** profile valid, config has start_date/end_date, total_days >= 365
**Post:** Returns validation results with passed bool and metrics
**Raises:** No (returns {"passed": False, "error": "..."} on failure)
**Retry:** No
**Side Effects:** Creates temp config files, runs backtests, cleans up in finally

### `WalkForwardValidator._run_backtest_with_params(profile, config, params) -> MetricsDict`
**Pre:** profile valid, config valid
**Post:** Returns backtest metrics
**Raises:** No (returns empty metrics on failure)
**Retry:** No
**Side Effects:** Creates temp config file, runs backtest, cleans up in finally

### `WalkForwardValidator._get_empty_metrics() -> MetricsDict`
**Pre:** None
**Post:** Returns empty metrics dict
**Raises:** No
**Retry:** No
**Side Effects:** None

### `MonteCarloSimulator.__init__(output_dir, validation_config, profile_config_loader) -> None`
**Pre:** output_dir must be valid path
**Post:** MonteCarloSimulator initialized
**Raises:** No
**Retry:** No
**Side Effects:** None (stores references)

### `MonteCarloSimulator.simulate(profile, config, params) -> ValidationResultDict`
**Pre:** profile valid, config valid
**Post:** Returns simulation results with passed bool and metrics
**Raises:** No (returns {"passed": False, "error": "..."} on failure)
**Retry:** No
**Side Effects:** Gets backtest results, runs bootstrap simulation

### `MonteCarloSimulator._run_backtest_with_params(profile, config, params) -> MetricsDict`
**Pre:** profile valid, config valid
**Post:** Returns backtest metrics
**Raises:** No (returns empty metrics on failure)
**Retry:** No
**Side Effects:** Creates temp config file, runs backtest, cleans up in finally

### `MonteCarloSimulator._get_empty_metrics() -> MetricsDict`
**Pre:** None
**Post:** Returns empty metrics dict
**Raises:** No
**Retry:** No
**Side Effects:** None

### `OutOfSampleValidator.__init__(output_dir, validation_config, profile_config_loader) -> None`
**Pre:** output_dir must be valid path
**Post:** OutOfSampleValidator initialized
**Raises:** No
**Retry:** No
**Side Effects:** None (stores references)

### `OutOfSampleValidator.validate(profile, config, params) -> ValidationResultDict`
**Pre:** profile valid, config has start_date/end_date
**Post:** Returns validation results with passed bool and metrics
**Raises:** No (returns {"passed": False, "error": "..."} on failure)
**Retry:** No
**Side Effects:** Creates temp config files, runs train and OOS backtests, cleans up in finally

### `OutOfSampleValidator._run_backtest_with_params(profile, config, params) -> MetricsDict`
**Pre:** profile valid, config valid
**Post:** Returns backtest metrics
**Raises:** No (returns empty metrics on failure)
**Retry:** No
**Side Effects:** Creates temp config file, runs backtest, cleans up in finally

### `OutOfSampleValidator._get_empty_metrics() -> MetricsDict`
**Pre:** None
**Post:** Returns empty metrics dict
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] WalkForwardValidator.validate() returns {"passed": False, "error": "Insufficient data"} if total_days < 365
- [ ] WalkForwardValidator.validate() calculates rolling windows correctly
- [ ] WalkForwardValidator.validate() passes if avg_sharpe >= 0.5
- [ ] WalkForwardValidator.validate() cleans up temp config files
- [ ] MonteCarloSimulator.simulate() uses bootstrapping with replacement
- [ ] MonteCarloSimulator.simulate() returns {"passed": False, "error": "..."} if no trade data
- [ ] MonteCarloSimulator.simulate() passes if profitable_pct >= min_profitable_pct
- [ ] MonteCarloSimulator.simulate() generates synthetic returns if returns_series missing
- [ ] OutOfSampleValidator.validate() splits data at train_percentage
- [ ] OutOfSampleValidator.validate() passes if oos_sharpe >= min_oos_sharpe AND sharpe_decay <= max_performance_decay AND oos_sharpe > 0
- [ ] OutOfSampleValidator.validate() returns {"passed": False, "error": "..."} on exception
- [ ] All validators clean up temp files in finally blocks
- [ ] All validators return empty metrics on backtest failure
- [ ] All validators use uuid for temp config file names

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | BASE_RULES.md | No mutable defaults | ✅ OK - No mutable defaults |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK - All functions have type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure layer |
| SOL-001 | BASE_RULES.md | Single Responsibility | ✅ OK - Each validator has single responsibility |
| BT-001 | BASE_RULES.md | Walk-forward validation | ✅ OK - WalkForwardValidator implements |
| BT-002 | BASE_RULES.md | Out-of-sample testing | ✅ OK - OutOfSampleValidator implements |
| LOG-003 | BASE_RULES.md | Appropriate logging levels | ✅ OK - Uses info, error appropriately |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** numpy, pandas, yaml, logging, uuid, pathlib, typing
- **Internal:**
  - `app.backtesting.comprehensive_backtest_runner.ComprehensiveBacktestRunner`
  - `app.core.config.profile_config_loader.ProfileConfigLoader`
  - `app.core.models.input_profile.InputProfile`

---

## Required Tests
- **tests/backtesting/profile_batch/test_optimization_validators.py:**
  - Test WalkForwardValidator.validate() with insufficient data (< 365 days)
  - Test WalkForwardValidator.validate() calculates correct window sizes
  - Test WalkForwardValidator.validate() passes when avg_sharpe >= 0.5
  - Test WalkForwardValidator.validate() fails when avg_sharpe < 0.5
  - Test WalkForwardValidator.validate() handles window failures gracefully
  - Test WalkForwardValidator.validate() cleans up temp files
  - Test MonteCarloSimulator.simulate() with valid returns_series
  - Test MonteCarloSimulator.simulate() with missing returns_series (synthetic generation)
  - Test MonteCarloSimulator.simulate() with no trade data
  - Test MonteCarloSimulator.simulate() passes when profitable_pct >= threshold
  - Test MonteCarloSimulator.simulate() uses bootstrapping with replacement
  - Test MonteCarloSimulator.simulate() cleans up temp files
  - Test OutOfSampleValidator.validate() splits data correctly
  - Test OutOfSampleValidator.validate() passes all three conditions
  - Test OutOfSampleValidator.validate() fails on low oos_sharpe
  - Test OutOfSampleValidator.validate() fails on high sharpe_decay
  - Test OutOfSampleValidator.validate() calculates sharpe_decay correctly
  - Test OutOfSampleValidator.validate() cleans up temp files
  - Test all _get_empty_metrics() return all required fields

---

## Notes
- Walk-forward validation default: n_windows=5, train_percentage=0.6
- Monte Carlo default: n_simulations=1000, min_profitable_pct=0.95
- Out-of-sample default: train_percentage=0.7, min_oos_sharpe=0.5, max_performance_decay=0.3
- All validators use uuid for temp config file names to avoid conflicts
- Temp files are cleaned up in finally blocks regardless of success/failure
- Monte Carlo uses bootstrapping with np.random.choice(replace=True)
- Sharpe decay calculated as (train_sharpe - oos_sharpe) / train_sharpe when train_sharpe > 0
- All validators return {"passed": False, "error": "..."} on failure for error handling
