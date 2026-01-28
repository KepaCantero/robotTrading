# Profile Batch Backtester - Quick Reference Guide

## Refactoring Overview

The `profile_batch_backtester.py` file has been refactored from a 2,891-line monolith into focused, single-responsibility modules following Clean Architecture principles.

---

## Module Structure

```
app/backtesting/
├── profile_batch_backtester.py      # Main orchestrator (200 lines)
├── profile_batch_config.py          # Configuration classes (400 lines)
├── profile_batch_execution.py       # Execution logic (800 lines)
├── profile_batch_aggregation.py     # Result aggregation (400 lines)
├── profile_batch_validation.py      # Validation logic (300 lines)
└── profile_batch_storage.py         # Database operations (300 lines)
```

---

## Usage (Unchanged)

```python
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# Initialize
backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

# Generate profiles
profiles = backtester.generate_all_profiles()

# Run backtests
results = backtester.run_all_profiles(parallel=True, max_workers=20)

# Get best strategy
best = backtester.get_best_strategy(
    objective="maximizar_capital",
    tier="medio",
    risk="alto"
)

# Generate report
report = backtester.generate_comparison_report()

# Export results
backtester.export_results(format="json")
```

---

## Module Dependencies

```
profile_batch_backtester.py (Orchestrator)
    │
    ├── profile_batch_config.py (Configuration)
    │   ├── ProfileResultDB (Database model)
    │   ├── BaselineOptimizationComparison (Value object)
    │   ├── OptimizedStrategy (Value object)
    │   ├── ProfileResult (Domain entity)
    │   ├── BacktestConfig (Configuration)
    │   ├── OptimizationConfig (Configuration)
    │   ├── ValidationConfig (Configuration)
    │   └── ProfileBatchConfigManager (Manager)
    │
    ├── profile_batch_execution.py (Execution)
    │   ├── ProfileBatchExecutor (Executor)
    │   ├── ParallelExecutionCoordinator (Coordinator)
    │   └── FallbackMetricsTracker (Tracker)
    │
    ├── profile_batch_aggregation.py (Aggregation)
    │   └── ProfileBatchAggregator (Aggregator)
    │
    ├── profile_batch_validation.py (Validation)
    │   └── ProfileBatchValidator (Validator)
    │
    └── profile_batch_storage.py (Storage)
        ├── ProfileBatchStorage (Storage)
        └── ReportGenerator (Generator)
```

---

## Key Changes

### 1. Configuration (profile_batch_config.py)

**Before:**
```python
# Configuration scattered throughout main class
def _load_config(self) -> Dict[str, Any]:
    with open(self.config_path) as f:
        return yaml.safe_load(f)

def _validate_configurations(self) -> None:
    # Validation logic mixed with initialization
    ...
```

**After:**
```python
# Dedicated configuration manager with value objects
config_manager = ProfileBatchConfigManager(config_path)

# Get typed configuration objects
optimization_config = config_manager.get_optimization_config()
validation_config = config_manager.get_validation_config()

# Create profile-specific configuration
backtest_config = config_manager.create_profile_config(profile)
```

### 2. Execution (profile_batch_execution.py)

**Before:**
```python
# All execution logic in main class (1000+ lines)
def _run_baseline(self, profile, config, multi_strategy):
    # 100+ lines of baseline execution logic
    ...

def _run_optimization_pipeline(self, profile, config, baseline_metrics):
    # 200+ lines of optimization logic
    ...
```

**After:**
```python
# Dedicated executor with clear interface
executor = ProfileBatchExecutor(
    config=backtest_config,
    optimization_config=optimization_config,
    validation_config=validation_config,
    output_dir=output_dir
)

# Run baseline
baseline_results = executor.run_baseline(profile, backtest_config)

# Run optimization pipeline
optimized_strategy = executor.run_optimization_pipeline(
    profile, backtest_config, baseline_metrics
)
```

### 3. Aggregation (profile_batch_aggregation.py)

**Before:**
```python
# Aggregation logic mixed with execution
def _aggregate_multi_strategy_results(self, results, profile):
    # 100+ lines of aggregation logic
    ...

def _generate_comparison(self, baseline, optimized, optuna_results):
    # Comparison logic mixed with metrics
    ...
```

**After:**
```python
# Dedicated aggregator
aggregator = ProfileBatchAggregator(acceptance_criteria)

# Calculate improvements
improvements = aggregator.calculate_improvements(baseline, optimized)

# Generate comparison
comparison = aggregator.generate_comparison(
    baseline, optimized, optuna_results
)

# Aggregate multi-strategy results
combined = aggregator.aggregate_multi_strategy_results(results, profile)
```

### 4. Validation (profile_batch_validation.py)

**Before:**
```python
# Validation logic scattered across multiple methods
def _run_walk_forward(self, profile, config, params):
    # 200+ lines of validation logic
    ...

def _run_monte_carlo(self, profile, config, params):
    # 100+ lines of Monte Carlo logic
    ...
```

**After:**
```python
# Dedicated validator
validator = ProfileBatchValidator(validation_config)

# Run walk-forward validation
wf_results = validator.run_walk_forward(profile, config, params, executor)

# Run Monte Carlo simulation
mc_results = validator.run_monte_carlo(profile, config, params, executor)

# Run out-of-sample validation
oos_results = validator.run_out_of_sample(profile, config, params, executor)
```

### 5. Storage (profile_batch_storage.py)

**Before:**
```python
# Storage logic mixed with business logic
def _store_result(self, result):
    # Database operations mixed with business logic
    ...

def _batch_store_results(self, results):
    # 70+ lines of database operations
    ...
```

**After:**
```python
# Dedicated storage handler
storage = ProfileBatchStorage(db_url, Session)

# Store single result
storage.store_result(result)

# Batch store results
storage.batch_store_results(results)

# Query best strategy
best = storage.get_best_strategy(objective, tier, risk)
```

---

## Testing

### Unit Tests (Per Module)

```python
# Test configuration manager
def test_config_loading():
    manager = ProfileBatchConfigManager("config/test.yaml")
    config = manager.get_optimization_config()
    assert config.n_trials == 100

# Test executor
def test_baseline_execution():
    executor = ProfileBatchExecutor(config, opt_config, val_config, criteria, output_dir)
    results = executor.run_baseline(profile, backtest_config)
    assert "sharpe_ratio" in results

# Test aggregator
def test_improvement_calculation():
    aggregator = ProfileBatchAggregator(criteria)
    improvements = aggregator.calculate_improvements(baseline, optimized)
    assert improvements["sharpe_improvement"] > 0

# Test validator
def test_walk_forward():
    validator = ProfileBatchValidator(validation_config)
    results = validator.run_walk_forward(profile, config, params, executor)
    assert "passed" in results

# Test storage
def test_result_storage():
    storage = ProfileBatchStorage(db_url, Session)
    storage.store_result(result)
    loaded = storage.load_result(result.profile_id)
    assert loaded.profile_id == result.profile_id
```

### Integration Tests

```python
def test_end_to_end_profile_execution():
    backtester = ProfileBatchBacktester(config_path)
    profiles = backtester.generate_all_profiles()
    results = backtester.run_all_profiles(parallel=False)
    assert len(results) > 0

def test_report_generation():
    backtester = ProfileBatchBacktester(config_path)
    results = backtester.run_all_profiles()
    report = backtester.generate_comparison_report()
    assert "<html>" in report
```

---

## Benefits

### For Developers

1. **Easier to Understand** - Each module has a single, clear purpose
2. **Easier to Test** - Components can be tested in isolation
3. **Easier to Modify** - Changes are localized to specific modules
4. **Easier to Extend** - New features can be added without modifying existing code
5. **Better IDE Support** - Smaller files improve navigation and autocomplete

### For the Codebase

1. **Clean Architecture** - Follows industry best practices
2. **Better Separation of Concerns** - Each module has one responsibility
3. **Reduced Coupling** - Components depend on interfaces, not implementations
4. **Increased Cohesion** - Related functionality is grouped together
5. **Improved Test Coverage** - 95%+ coverage achievable

### For the Business

1. **Faster Development** - Easier to add new features
2. **Fewer Bugs** - Better testing and isolation
3. **Easier Maintenance** - Changes are localized
4. **Better Scalability** - Components can be reused
5. **Lower Technical Debt** - Clean, maintainable code

---

## Common Tasks

### Add New Validation Type

```python
# In profile_batch_validation.py
class ProfileBatchValidator:
    def run_custom_validation(self, profile, config, params, executor) -> Dict[str, Any]:
        """Run custom validation logic."""
        # Implementation here
        return {"passed": True, "custom_metric": 0.95}
```

### Add New Aggregation Method

```python
# In profile_batch_aggregation.py
class ProfileBatchAggregator:
    def custom_aggregation(self, results: List[Dict]) -> Dict[str, Any]:
        """Custom aggregation logic."""
        # Implementation here
        return aggregated_results
```

### Add New Configuration Parameter

```python
# In profile_batch_config.py
@dataclass(frozen=True)
class CustomConfig:
    """Custom configuration parameters."""
    param1: float = 1.0
    param2: int = 100

class ProfileBatchConfigManager:
    def get_custom_config(self) -> CustomConfig:
        """Get custom configuration."""
        return CustomConfig(
            param1=self.config.get("custom", {}).get("param1", 1.0),
            param2=self.config.get("custom", {}).get("param2", 100)
        )
```

---

## Troubleshooting

### Import Errors

If you get import errors after refactoring:

```python
# Old imports (still work for backward compatibility)
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# New imports (for direct component access)
from app.backtesting.profile_batch_config import ProfileBatchConfigManager
from app.backtesting.profile_batch_execution import ProfileBatchExecutor
from app.backtesting.profile_batch_aggregation import ProfileBatchAggregator
from app.backtesting.profile_batch_validation import ProfileBatchValidator
from app.backtesting.profile_batch_storage import ProfileBatchStorage
```

### Configuration Issues

If configuration loading fails:

```python
# Check configuration validation
manager = ProfileBatchConfigManager(config_path)
manager._validate_configurations()  # Will raise ValueError if invalid

# Check fallback metrics
backtester = ProfileBatchBacktester(config_path)
metrics = backtester.get_fallback_metrics()
print(metrics)  # See how many fallbacks occurred
```

### Performance Issues

If execution is slow:

```python
# Adjust parallel execution
results = backtester.run_all_profiles(parallel=True, max_workers=10)

# Or run sequentially for debugging
results = backtester.run_all_profiles(parallel=False)
```

---

## Further Reading

- [REFACTORING_PLAN_profile_batch_backtester.md](./REFACTORING_PLAN_profile_batch_backtester.md) - Detailed refactoring plan
- [REFACTORING_SUMMARY_profile_batch_backtester.md](./REFACTORING_SUMMARY_profile_batch_backtester.md) - Summary of changes
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Robert C. Martin
- [Domain-Driven Design](https://domainlanguage.com/ddd/) - Eric Evans

---

**Last Updated:** 2026-01-28
**Version:** 1.0
**Status:** Ready for Review
