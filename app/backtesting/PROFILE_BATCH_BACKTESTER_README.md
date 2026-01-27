# Profile Batch Backtester - Complete Documentation

## Overview

The `ProfileBatchBacktester` is a comprehensive batch testing system that orchestrates baseline and optimization backtesting across 180 investor profile combinations (5 objectives × 3 risk levels × 3 capital tiers × 4 investment horizons).

## Key Features

### 1. Comprehensive Profile Generation
- **180 unique combinations** from:
  - 5 investment objectives (maximizar_capital, maximizar_dividendos, capital_preservation, balanced_growth, income_generation)
  - 3 risk tolerances (bajo, medio, alto)
  - 3 capital tiers (€50k, €150k, €500k)
  - 4 investment horizons (12, 24, 36, 60 months)

### 2. Dual Testing Pipeline
Each profile runs **BOTH**:
- **BASELINE**: Default parameters from config
- **OPTIMIZED**: Bayesian optimization using Optuna

### 3. Multi-Stage Validation
- FASE 1: Baseline backtest with default parameters
- FASE 2: Bayesian optimization (100 trials)
- FASE 3: Walk-forward validation (5 windows)
- FASE 4: Monte Carlo simulation (100 runs)
- FASE 5: Out-of-sample validation (20% holdout)

### 4. Statistical Comparison
- Baseline vs Optimized metrics
- Percentage improvements
- Statistical significance testing
- Parameter sensitivity analysis
- Automated recommendations

## Installation

### Requirements
```bash
# Core dependencies (already in requirements.txt)
pip install optuna>=3.4.0
pip install sqlalchemy>=2.0.0
pip install jinja2>=3.0.0
pip install openpyxl>=3.0.0  # For Excel export
```

### Database Setup
```bash
# SQLite (default)
# No setup required - automatically created

# PostgreSQL (optional)
createdb profile_batch_results
# Update config: database.url = "postgresql://user:pass@localhost/profile_batch_results"
```

## Configuration

### Config File Structure: `config/profile_batch_backtest.yaml`

```yaml
# Capital tiers for profile generation
capital_tiers:
  bajo: 50000      # €50k
  medio: 150000    # €150k
  alto: 500000     # €500k

# Risk parameters by tolerance
risk_parameters:
  bajo:
    max_position_pct: 0.05
    stop_loss_pct: 0.02
    take_profit_pct: 0.08
  medio:
    max_position_pct: 0.10
    stop_loss_pct: 0.03
    take_profit_pct: 0.12
  alto:
    max_position_pct: 0.20
    stop_loss_pct: 0.05
    take_profit_pct: 0.20

# Optimization settings
optimization:
  n_trials: 100              # Optuna trials
  timeout: null              # No timeout
  sampler: "TPESampler"
  pruner: "MedianPruner"
  n_jobs: 4                  # Parallel trials

# Validation settings
validation:
  walk_forward:
    n_windows: 5
    train_percentage: 0.6
  monte_carlo:
    n_simulations: 100
  out_of_sample:
    oos_percentage: 0.20
```

## Usage Examples

### Example 1: Run All Profiles (Parallel)

```python
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# Create backtester
backtester = ProfileBatchBacktester(
    config_path="config/profile_batch_backtest.yaml"
)

# Run all 180 profiles
results = backtester.run_all_profiles(
    parallel=True,    # Use parallel execution
    max_workers=20,   # Up to 20 workers
)

# Export results
backtester.export_results(format="json")
```

### Example 2: Single Profile Testing

```python
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from decimal import Decimal

# Create backtester
backtester = ProfileBatchBacktester(
    config_path="config/profile_batch_backtest.yaml"
)

# Define profile
profile = InputProfile(
    capital_initial=Decimal("100000"),
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    risk_tolerance=RiskTolerance.MEDIO,
    investment_horizon=24,
)

# Run profile
result = backtester.run_single_profile(profile)

# Print results
print(f"Baseline Sharpe: {result.baseline_results['sharpe_ratio']:.2f}")
print(f"Optimized Sharpe: {result.optimization_results['sharpe_ratio']:.2f}")
print(f"Improvement: {result.improvement_metrics['sharpe_improvement']:.1f}%")
print(f"Ready: {result.ready_for_paper_trading}")
```

### Example 3: Get Best Strategy

```python
# Get best configuration for specific criteria
best_config = backtester.get_best_strategy(
    objective="maximizar_capital",
    tier="medio",
    risk="medio"
)

print(f"Best Sharpe: {best_config['optimized_metrics']['sharpe_ratio']:.2f}")
print(f"Best Parameters: {best_config['best_parameters']}")
print(f"Recommendation: {best_config['recommendation']}")
```

### Example 4: Generate Comparison Report

```python
# Generate HTML report
html_report = backtester.generate_comparison_report()

# Save to file
with open("comparison_report.html", "w") as f:
    f.write(html_report)
```

### Example 5: Export Results

```python
# Export to JSON
json_path = backtester.export_results(format="json")

# Export to CSV
csv_path = backtester.export_results(format="csv")

# Export to Excel
excel_path = backtester.export_results(format="excel")
```

## Database Schema

### Table: `profile_results`

| Column | Type | Description |
|--------|------|-------------|
| `id` | String (PK) | Unique identifier |
| `profile_id` | String | Profile identifier |
| `objective` | String | Investment objective |
| `risk_tolerance` | String | Risk tolerance level |
| `capital_tier` | String | Capital tier |
| `investment_horizon` | Integer | Horizon in months |
| `baseline_sharpe` | Float | Baseline Sharpe ratio |
| `baseline_return` | Float | Baseline total return |
| `baseline_max_dd` | Float | Baseline max drawdown |
| `baseline_win_rate` | Float | Baseline win rate |
| `optimized_sharpe` | Float | Optimized Sharpe ratio |
| `optimized_return` | Float | Optimized total return |
| `optimized_max_dd` | Float | Optimized max drawdown |
| `optimized_win_rate` | Float | Optimized win rate |
| `sharpe_improvement` | Float | Sharpe improvement % |
| `return_improvement` | Float | Return improvement % |
| `max_dd_improvement` | Float | DD improvement % |
| `win_rate_improvement` | Float | Win rate improvement % |
| `best_parameters` | JSON | Best parameters from optimization |
| `walk_forward_passed` | Boolean | Walk-forward validation passed |
| `monte_carlo_passed` | Boolean | Monte Carlo validation passed |
| `out_of_sample_passed` | Boolean | OOS validation passed |
| `ready_for_paper_trading` | Boolean | Ready for paper trading |
| `recommendation` | String | Final recommendation |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Update timestamp |

## Output Files

### 1. JSON Export
```json
{
  "profile_id": "maximizar_capital_medio_medio_24m",
  "baseline_results": {
    "sharpe_ratio": 1.2,
    "return_pct": 15.5,
    "max_drawdown": -0.18,
    "win_rate": 52.0
  },
  "optimization_results": {
    "sharpe_ratio": 1.5,
    "return_pct": 18.2,
    "max_drawdown": -0.15,
    "win_rate": 55.0
  },
  "improvement_metrics": {
    "sharpe_improvement": 25.0,
    "return_improvement": 17.4,
    "max_dd_improvement": 16.7,
    "win_rate_improvement": 5.8
  },
  "best_parameters": {
    "rsi_threshold": 40,
    "ema_short": 12,
    "ema_long": 26,
    "volume_threshold": 1.5
  },
  "ready_for_paper_trading": true,
  "recommendation": "USE OPTIMIZED - Shows 25% Sharpe improvement"
}
```

### 2. CSV Export
| profile_id | objective | risk_tolerance | capital_tier | baseline_sharpe | optimized_sharpe | sharpe_improvement | ready |
|------------|-----------|----------------|--------------|----------------|------------------|-------------------|-------|
| max_cap_medio_medio_24m | maximizar_capital | medio | medio | 1.2 | 1.5 | 25.0 | true |

### 3. Excel Export
- **Summary sheet**: All profiles overview
- **Sheets by objective**: Detailed results per investment objective

### 4. HTML Comparison Report
Interactive HTML report with:
- Executive summary with key metrics
- Side-by-side baseline vs optimized comparison
- Improvement percentages (color-coded)
- Parameter importance analysis
- Best strategies by objective
- Recommendations

## Optimization Pipeline

### FASE 1: Baseline
```python
# Run with default parameters from config
baseline_metrics = run_baseline_backtest(profile, config)
```

### FASE 2: Bayesian Optimization (Optuna)
```python
# Define search space
search_space = {
    "rsi_threshold": (30, 70),
    "ema_short": (5, 20),
    "ema_long": (20, 50),
    "volume_threshold": (1.0, 3.0),
    "stop_loss": (0.01, 0.05),
    "take_profit": (0.05, 0.20),
}

# Optimize using Optuna
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)

best_params = study.best_params
best_metrics = evaluate_with_params(best_params)
```

### FASE 3: Walk-Forward Validation
```python
# Split data into train/test windows
windows = create_walk_forward_windows(
    n_windows=5,
    train_pct=0.6
)

# Validate on out-of-sample data
oos_metrics = []
for window in windows:
    train_on(window.train)
    test_on(window.test)
    oos_metrics.append(evaluate())

# Check degradation
avg_oos_sharpe = mean(oos_metrics)
degradation = (baseline - avg_oos_sharpe) / baseline
passed = degradation < 0.20  # < 20% degradation
```

### FASE 4: Monte Carlo Simulation
```python
# Run 100 simulations with random variations
simulations = []
for i in range(100):
    # Add random noise to returns
    noisy_returns = returns + np.random.normal(0, 0.05)
    simulations.append(calculate_metrics(noisy_returns))

# Check profitability
profitable_pct = sum(1 for s in simulations if s > 0) / len(simulations)
passed = profitable_pct >= 0.95  # 95% must be profitable
```

### FASE 5: Out-of-Sample Validation
```python
# Hold out 20% of data
train_data, test_data = split_data(train_pct=0.8)

# Train on train data
train_model(train_data)

# Test on held-out data
oos_metrics = evaluate_on(test_data)

# Check performance
passed = oos_metrics['sharpe'] >= 0.8
```

## Acceptance Criteria

A profile is **READY_FOR_PAPER_TRADING** if:
- All validations passed (walk-forward, Monte Carlo, OOS)
- Sharpe ratio >= 1.0
- Total return >= 10%
- Max drawdown >= -25%

## Recommendations

The system generates one of three recommendations:

1. **USE OPTIMIZED**: Optimization shows significant improvement (>5% Sharpe, statistically significant)
2. **USE BASELINE**: Optimization degraded performance or showed no improvement
3. **NEUTRAL/INCONCLUSIVE**: Insufficient evidence to favor either configuration

## Performance

### Execution Time (approximate)
- **Single profile**: ~5-10 minutes (100 optimization trials)
- **180 profiles (sequential)**: ~15-30 hours
- **180 profiles (parallel, 20 workers)**: ~1-2 hours

### Memory Usage
- **Per worker**: ~500MB - 1GB
- **Total (20 workers)**: ~10GB - 20GB

### Storage
- **Per profile**: ~50KB (in database)
- **180 profiles**: ~9MB
- **Exported files**: ~1-5MB (depending on format)

## Troubleshooting

### Issue: Out of Memory
**Solution**: Reduce `max_workers` or process profiles in batches

```python
# Process in batches
all_profiles = backtester.generate_all_profiles()
batch_size = 50

for i in range(0, len(all_profiles), batch_size):
    batch = all_profiles[i:i+batch_size]
    for profile in batch:
        backtester.run_single_profile(profile)
```

### Issue: Optimization Not Converging
**Solution**: Increase `n_trials` or adjust search space

```yaml
optimization:
  n_trials: 200  # Increase from 100
  # Adjust search space bounds
```

### Issue: Database Lock Errors
**Solution**: Use SQLite in WAL mode or switch to PostgreSQL

```python
# SQLite WAL mode
engine = create_engine("sqlite:///results.db?mode=wal")
```

## Best Practices

1. **Start Small**: Test with 5-10 profiles before running all 180
2. **Monitor Progress**: Check logs regularly during batch execution
3. **Validate Results**: Review HTML report before proceeding to paper trading
4. **Store Configs**: Save configuration files used for reproducibility
5. **Backup Database**: Regular backups of SQLite database

## Integration with Existing System

### With ComprehensiveBacktestRunner
```python
# Uses existing runner for baseline tests
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

runner = ComprehensiveBacktestRunner(config_path)
baseline_results = runner.run_baseline_backtest()
```

### With ProfessionalReporter
```python
# Generate professional reports
from app.backtesting.professional_reporter import ProfessionalReporter

reporter = ProfessionalReporter()
professional_report = reporter.generate_complete_report(
    backtest_result=result,
    acceptance_report=acceptance
)
```

### With TestSummaryReporter
```python
# Generate test summaries
from app.backtesting.test_summary import TestSummaryReporter

summary_reporter = TestSummaryReporter()
summary_reporter.add_results(**metrics)
summary_reporter.save_reports()
```

## API Reference

### ProfileBatchBacktester

#### `__init__(config_path: str)`
Initialize backtester with configuration file.

#### `generate_all_profiles() -> List[InputProfile]`
Generate all 180 profile combinations.

#### `run_single_profile(profile: InputProfile) -> ProfileResult`
Run baseline and optimization for a single profile.

#### `run_all_profiles(parallel: bool = True, max_workers: int = 20) -> Dict[str, ProfileResult]`
Run all profiles with optional parallel execution.

#### `get_best_strategy(objective: str, tier: str, risk: str) -> Dict[str, Any]`
Get best strategy for specific criteria.

#### `export_results(format: str = "json") -> Path`
Export results to file (json, csv, excel).

#### `generate_comparison_report() -> str`
Generate HTML comparison report.

## License

This module is part of the algoTrading system and follows the same license.
