# Profile Batch Backtester - Quick Reference Guide

## Quick Start

### New Import (Recommended)
```python
from app.backtesting.profile_batch import ProfileBatchBacktester

# Create backtester
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
html = backtester.generate_comparison_report()

# Export results
backtester.export_results(format="json")
```

## Component Usage

### Using Individual Components

#### ProfileGenerator
```python
from app.backtesting.profile_batch import ProfileGenerator

generator = ProfileGenerator("config/profile_batch_backtest.yaml")

# Generate all profiles
profiles = generator.generate_all_profiles()

# Create configuration for a profile
config = generator.create_profile_config(profile, output_dir)

# Get capital tier key
tier_key = generator.get_capital_tier_key(profile)

# Create profile ID
profile_id = generator.create_profile_id(profile)
```

#### BaselineBacktestExecutor
```python
from app.backtesting.profile_batch import BaselineBacktestExecutor

executor = BaselineBacktestExecutor(output_dir)

# Run baseline backtest
results = executor.run_baseline(profile, config, multi_strategy=False)

# Aggregate multi-strategy results
combined = executor.aggregate_multi_strategy_results(results, profile)
```

#### OptimizationPipeline
```python
from app.backtesting.profile_batch import OptimizationPipeline

pipeline = OptimizationPipeline(
    output_dir=output_dir,
    optimization_config=optimization_config,
    validation_config=validation_config,
    acceptance_criteria=acceptance_criteria,
    profile_config_loader=profile_config_loader
)

# Run complete pipeline
optimized = pipeline.run_optimization_pipeline(
    profile, config, baseline_metrics, multi_strategy=False
)
```

#### ResultAggregator
```python
from app.backtesting.profile_batch import ResultAggregator

aggregator = ResultAggregator(db_url, get_capital_tier_fn)

# Store result
aggregator.store_result(result)

# Batch store
aggregator.batch_store_results(results)

# Get best strategy
best = aggregator.get_best_strategy(objective, tier, risk)

# Calculate improvements
improvements = aggregator.calculate_improvements(baseline, optimized)

# Evaluate readiness
ready, rec = aggregator.evaluate_readiness(profile, optimized, improvements, criteria)
```

#### ReportGenerator
```python
from app.backtesting.profile_batch import ReportGenerator

reporter = ReportGenerator(output_dir)

# Generate HTML report
html = reporter.generate_comparison_report(results)

# Generate batch summary
reporter.generate_batch_summary(results, fallback_metrics)

# Export results
json_path = reporter.export_results(results, format="json")
csv_path = reporter.export_results(results, format="csv")
excel_path = reporter.export_results(results, format="excel")
```

## API Reference

### ProfileBatchBacktester

#### Methods
- `generate_all_profiles() -> List[InputProfile]`
- `run_single_profile(profile, multi_strategy=False) -> ProfileResult`
- `run_all_profiles(parallel=True, max_workers=20) -> Dict[str, ProfileResult]`
- `get_best_strategy(objective, tier, risk) -> Dict[str, Any]`
- `export_results(format="json") -> Path`
- `generate_comparison_report() -> str`
- `get_fallback_metrics() -> Dict[str, int]`

### ProfileResult

#### Fields
- `profile_id: str`
- `profile: InputProfile`
- `baseline_results: Dict[str, Any]`
- `optimization_results: Dict[str, Any]`
- `best_parameters: Dict[str, Any]`
- `improvement_metrics: Dict[str, float]`
- `comparison: BaselineOptimizationComparison`
- `ready_for_paper_trading: bool`
- `recommendation: str`

### OptimizedStrategy

#### Fields
- `profile_id: str`
- `baseline_metrics: Dict[str, Any]`
- `optimized_metrics: Dict[str, Any]`
- `best_parameters: Dict[str, Any]`
- `optimization_history: List[Dict[str, Any]]`
- `walk_forward_results: Optional[Dict[str, Any]]`
- `monte_carlo_results: Optional[Dict[str, Any]]`
- `out_of_sample_results: Optional[Dict[str, Any]]`
- `comparison: BaselineOptimizationComparison`
- `ready_for_paper_trading: bool`
- `recommendation: str`

## Configuration

### Required Configuration Files

1. **Workflow Config**: `config/profile_batch_backtest.yaml`
   - Database settings
   - Output directories
   - Backtest period
   - Symbols to trade

2. **Optimization Config**: `config/backtesting/profile_optimization.yaml`
   - Parameter ranges
   - Validation settings
   - Acceptance criteria

### Example Workflow Config

```yaml
database:
  url: "sqlite:///profile_backtest_results.db"

output_dir: "results/profile_batch_backtesting"

backtest_period:
  start_date: "2020-01-01"
  end_date: "2023-12-31"

symbols:
  - AAPL
  - MSFT
  - GOOGL
  - AMZN
  - TSLA

capital_tiers:
  bajo: 50000
  medio: 100000
  alto: 250000

investment_horizons:
  short: 12
  medium: 24
  long: 36

optimization:
  n_trials: 100
  timeout: null

validation:
  walk_forward:
    n_windows: 5
    train_percentage: 0.6
  monte_carlo:
    n_simulations: 1000
    min_profitable_pct: 0.95
  out_of_sample:
    train_percentage: 0.7
    min_oos_sharpe: 0.5

acceptance_criteria:
  min_sharpe: 1.0
  min_return: 0.10
  max_drawdown: -0.25
  significance_threshold: 5
  strong_significance_threshold: 10
```

## Common Patterns

### Running a Single Profile
```python
from app.backtesting.profile_batch import ProfileBatchBacktester
from app.core.models.input_profile import InputProfile

backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

profile = InputProfile(
    capital_initial=100000,
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    risk_tolerance=RiskTolerance.ALTO,
    investment_horizon=24
)

result = backtester.run_single_profile(profile, multi_strategy=False)
print(result.recommendation)
```

### Running All Profiles
```python
from app.backtesting.profile_batch import ProfileBatchBacktester

backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

# Sequential execution
results = backtester.run_all_profiles(parallel=False)

# Parallel execution
results = backtester.run_all_profiles(parallel=True, max_workers=20)

# Check results
ready_count = sum(1 for r in results.values() if r.ready_for_paper_trading)
print(f"Ready for paper trading: {ready_count}/{len(results)}")
```

### Generating Reports
```python
from app.backtesting.profile_batch import ProfileBatchBacktester

backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
results = backtester.run_all_profiles()

# Generate HTML report
html = backtester.generate_comparison_report()

# Save to file
with open("report.html", "w") as f:
    f.write(html)

# Export to different formats
backtester.export_results(format="json")
backtester.export_results(format="csv")
backtester.export_results(format="excel")
```

### Querying Best Strategies
```python
from app.backtesting.profile_batch import ProfileBatchBacktester

backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")

# Get best strategy for specific criteria
best = backtester.get_best_strategy(
    objective="maximizar_capital",
    tier="medio",
    risk="alto"
)

print(f"Best Sharpe: {best['optimized_metrics']['sharpe_ratio']}")
print(f"Best Return: {best['optimized_metrics']['total_return']}%")
print(f"Parameters: {best['best_parameters']}")
```

## Error Handling

### Common Issues

1. **Missing Configuration**
   ```python
   # Error: FileNotFoundError
   # Solution: Check config path exists
   backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
   ```

2. **Database Connection**
   ```python
   # Error: SQLAlchemy error
   # Solution: Check database URL in config
   db_url = "sqlite:///profile_backtest_results.db"
   ```

3. **Insufficient Data**
   ```python
   # Error: Walk-forward fails
   # Solution: Increase backtest period
   backtest_period:
     start_date: "2018-01-01"  # More data
     end_date: "2023-12-31"
   ```

## Performance Tips

### Parallel Execution
```python
# Use parallel execution for large batches
results = backtester.run_all_profiles(
    parallel=True,
    max_workers=min(20, len(profiles))  # Don't exceed CPU cores
)
```

### Memory Management
```python
# Process results in chunks to avoid memory issues
for i, (profile_id, result) in enumerate(results.items()):
    if i % 10 == 0:
        # Process every 10th result
        process_result(result)
```

### Database Optimization
```python
# Use PostgreSQL for better concurrent writes
database:
  url: "postgresql://user:pass@localhost/profile_batch"
```

## Testing

### Unit Testing Components
```python
def test_profile_generator():
    from app.backtesting.profile_batch import ProfileGenerator

    generator = ProfileGenerator("config/profile_batch_backtest.yaml")
    profiles = generator.generate_all_profiles()

    assert len(profiles) == 180  # 5 × 3 × 3 × 4
    assert all(isinstance(p, InputProfile) for p in profiles)

def test_baseline_executor():
    from app.backtesting.profile_batch import BaselineBacktestExecutor

    executor = BaselineBacktestExecutor(output_dir)
    results = executor.run_baseline(profile, config)

    assert "sharpe_ratio" in results
    assert "return_pct" in results
```

### Integration Testing
```python
def test_full_pipeline():
    from app.backtesting.profile_batch import ProfileBatchBacktester

    backtester = ProfileBatchBacktester("config/profile_batch_backtest.yaml")
    result = backtester.run_single_profile(profile)

    assert result.profile_id is not None
    assert result.baseline_results is not None
    assert result.optimization_results is not None
    assert result.recommendation is not None
```

## Migration

### From Old Import
```python
# Old (deprecated)
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
```

### To New Import
```python
# New (recommended)
from app.backtesting.profile_batch import ProfileBatchBacktester
```

**Note**: Both imports work identically. No code changes needed!

## Support

For issues or questions:
1. Check `REFACTORING_MIGRATION_GUIDE.md` for detailed migration info
2. Check `REFACTORING_SUMMARY.md` for architecture overview
3. Review component docstrings in source files
4. Run tests to verify functionality: `pytest tests/unit/backtesting/test_profile_batch_backtester.py`

## Version History

- **v1.0** (2026-01-27): Initial refactoring
  - Extracted 6 components from God Object
  - Maintained 100% backward compatibility
  - Added comprehensive documentation
