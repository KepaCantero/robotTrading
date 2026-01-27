# Profile Optimization Configuration System - Usage Guide

## Overview

The Profile Optimization Configuration System provides centralized management of all backtesting and strategy parameters, eliminating hardcoded values throughout the codebase.

## Files Created

1. **Configuration File**: `/Users/kepa.cantero/Projects/algoTrading/config/backtesting/profile_optimization.yaml`
   - Comprehensive YAML configuration with 50+ parameters
   - Profile-specific overrides (conservative, balanced, aggressive, income, growth, dividendos)
   - Tier-specific overrides (micro, small, medium, large)

2. **Config Loader**: `/Users/kepa.cantero/Projects/algoTrading/app/core/config/profile_config_loader.py`
   - Python loader with convenience methods
   - Automatic profile and tier override application
   - Parameter validation
   - Caching for performance

## Parameters Centralized

### Common Parameters
- `random_state`: Random seed for reproducibility (default: 42)
- `test_size`: Train/test split ratio (default: 0.2)
- `cv_folds`: Cross-validation folds (default: 5)
- `min_train_samples`: Minimum training samples (default: 100)

### Threading Configuration
- `max_workers`: Maximum parallel workers (null = auto-detect)
- `worker_multiplier`: CPU count multiplier (default: 0.75)
- `batch_size`: Batch size for parallel processing (default: 32)
- `task_timeout`: Task timeout in seconds (default: 300)

### Model Parameters

**Random Forest:**
- `n_estimators`: Number of trees (default: 100)
- `max_depth`: Maximum tree depth (default: 10)
- `min_samples_split`: Minimum samples to split (default: 10)
- `min_samples_leaf`: Minimum samples per leaf (default: 5)

**XGBoost:**
- `n_estimators`: 100
- `max_depth`: 6
- `learning_rate`: 0.1
- `subsample`: 0.8

**LightGBM:**
- `n_estimators`: 100
- `max_depth`: 6
- `learning_rate`: 0.1
- `num_leaves`: 31

### Reinforcement Learning

**Environment:**
- `initial_balance`: 100000
- `commission`: 0.001 (0.1%)
- `slippage`: 0.0005 (0.05%)

**Rewards:**
- `pnl_weight`: 1.0
- `sharpe_weight`: 0.3
- `drawdown_penalty`: 0.5
- `transaction_cost`: 0.001

**PPO Algorithm:**
- `learning_rate`: 0.0003
- `n_steps`: 2048
- `batch_size`: 64
- `gamma`: 0.99
- `gae_lambda`: 0.95
- `clip_range`: 0.2

### Threshold Optimization

**RSI:**
- `buy_threshold`: min=20, max=35, default=30
- `sell_threshold`: min=65, max=80, default=70

**Stochastic RSI:**
- `oversold_threshold`: min=10, max=25, default=20
- `overbought_threshold`: min=75, max=90, default=80

**Momentum:**
- `threshold`: min=0.01, max=0.03, default=0.015

**Volume Ratio:**
- `min`: 1.0, max=1.5, default=1.1

### Validation Thresholds
- `min_sharpe`: 0.5
- `max_drawdown`: 0.2
- `min_win_rate`: 0.45
- `min_trades`: 20
- `min_profit_factor`: 1.5

## Usage Examples

### Basic Usage

```python
from app.core.config import get_profile_config_loader

# Get loader with defaults
loader = get_profile_config_loader()

# Access common parameters
random_state = loader.get_random_state()  # 42
test_size = loader.get_test_size()        # 0.2
cv_folds = loader.get_cv_folds()          # 5

# Access model parameters
rf_params = loader.get_random_forest_params()
# {
#     'n_estimators': 100,
#     'max_depth': 10,
#     'min_samples_split': 10,
#     'min_samples_leaf': 5,
#     ...
# }

# Access with dot notation
n_estimators = loader.get("models.random_forest.n_estimators", 100)
```

### Profile-Specific Overrides

```python
# Conservative profile - more risk-averse
conservative_loader = get_profile_config_loader(profile="conservative")
conservative_rf = conservative_loader.get_random_forest_params()
# {
#     'n_estimators': 100,
#     'min_samples_split': 20,  # Higher than default
#     'min_samples_leaf': 10,    # Higher than default
#     ...
# }

# Aggressive profile - growth-focused
aggressive_loader = get_profile_config_loader(profile="aggressive")
aggressive_rf = aggressive_loader.get_random_forest_params()
# {
#     'min_samples_split': 5,   # Lower than default
#     'min_samples_leaf': 2,     # Lower than default
#     ...
# }
```

### Tier-Specific Overrides

```python
# Micro tier (<$15k) - conservative resource usage
micro_loader = get_profile_config_loader(tier="micro")
micro_rf = micro_loader.get_random_forest_params()
# {
#     'n_estimators': 50,   # Fewer trees
#     'max_depth': 8,       # Shallower trees
#     ...
# }

# Large tier (>$250k) - more resources
large_loader = get_profile_config_loader(tier="large")
large_rf = large_loader.get_random_forest_params()
# {
#     'n_estimators': 150,  # More trees
#     'max_depth': 12,      # Deeper trees
#     ...
# }
```

### Combined Profile and Tier

```python
# Apply both profile and tier overrides
loader = get_profile_config_loader(
    profile="aggressive",
    tier="large"
)

# RL configuration with overrides
rl_env = loader.get_rl_environment_config()
# {
#     'initial_balance': 250000,  # Tier override
#     'commission': 0.001,
#     'slippage': 0.0005,
#     ...
# }

rl_rewards = loader.get_rl_reward_config()
# {
#     'pnl_weight': 1.5,        # Profile override
#     'sharpe_weight': 0.3,
#     'drawdown_penalty': 0.3,  # Profile override
#     ...
# }
```

### Convenience Functions

```python
from app.core.config import (
    get_common_params,
    get_model_params,
    get_threshold_ranges,
    get_rl_config,
)

# Get all common parameters at once
common = get_common_params(profile="balanced")
# {
#     'random_state': 42,
#     'test_size': 0.2,
#     'cv_folds': 5,
#     'min_train_samples': 100,
# }

# Get model parameters directly
rf_params = get_model_params("random_forest", profile="conservative")

# Get threshold optimization ranges
rsi_ranges = get_threshold_ranges("rsi", tier="small")
# {
#     'buy_threshold': {'min': 30, 'max': 40, ...},
#     'sell_threshold': {'min': 60, 'max': 70, ...},
#     ...
# }

# Get complete RL configuration
rl_config = get_rl_config(profile="aggressive", tier="large")
```

### Integration with Existing Code

**Before (hardcoded):**
```python
from sklearn.ensemble import RandomForestClassifier

# Hardcoded parameters
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)
```

**After (config-driven):**
```python
from sklearn.ensemble import RandomForestClassifier
from app.core.config import get_model_params

# Load from config
params = get_model_params("random_forest", profile="balanced")
model = RandomForestClassifier(**params)
```

### Parameter Validation

```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()

# Validate a value against configured range
is_valid = loader.validate_parameter_range(
    "threshold_optimization.rsi.buy_threshold",
    25,  # Value to validate
    min_key="min",
    max_key="max"
)  # Returns: True (25 is between 20 and 35)

# Get parameter range
min_val, max_val, step = loader.get_parameter_range(
    "threshold_optimization.rsi.buy_threshold"
)  # Returns: (20, 35, 2)
```

### Threading Configuration

```python
from app.core.config import get_profile_config_loader
import multiprocessing

loader = get_profile_config_loader(tier="micro")

# Get max workers with CPU count auto-detection
cpu_count = multiprocessing.cpu_count()
max_workers = loader.get_max_workers(cpu_count)
# For tier=micro: 2 workers
# For tier=medium: ~0.75 * CPU_COUNT

# Get batch size
batch_size = loader.get_batch_size()  # 32

# Get timeout
timeout = loader.get_task_timeout()  # 300 seconds
```

### Backtesting Integration

```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(
    profile="aggressive",
    tier="medium"
)

# Get common backtesting parameters
config = {
    'random_state': loader.get_random_state(),
    'test_size': loader.get_test_size(),
    'cv_folds': loader.get_cv_folds(),
    'min_train_samples': loader.get_min_train_samples(),

    # Get model parameters
    'rf_params': loader.get_random_forest_params(),
    'xgb_params': loader.get_xgboost_params(),

    # Get RL configuration
    'rl_config': loader.get_rl_config(),

    # Get threshold optimization settings
    'threshold_config': loader.get_threshold_config("rsi"),
    'optimization_method': loader.get_optimization_method(),

    # Get validation settings
    'walk_forward': loader.get_walk_forward_config(),
    'monte_carlo': loader.get_monte_carlo_config(),
    'validation_thresholds': loader.get_validation_thresholds(),

    # Get reporting settings
    'output_dir': loader.get_output_directory(),
    'report_metrics': loader.get_report_metrics("advanced"),

    # Get memory management
    'memory_config': loader.get_memory_config(),
}

# Use in backtesting
backtester = Backtester(config)
```

## Replacing Hardcoded Values

### Common Replacements

| Hardcoded Value | Config Path | Function |
|----------------|-------------|----------|
| `42` | `common.random_state` | `loader.get_random_state()` |
| `0.2` | `common.test_size` | `loader.get_test_size()` |
| `5` | `common.cv_folds` | `loader.get_cv_folds()` |
| `100` | `models.random_forest.n_estimators` | `loader.get_model_params("random_forest")` |
| `0.0003` | `reinforcement_learning.algorithms.ppo.learning_rate` | `loader.get_rl_algorithm_params("ppo")` |
| `30` | `threshold_optimization.rsi.buy_threshold.default` | `loader.get_threshold_config("rsi")` |

### Migration Pattern

**Step 1**: Import the loader
```python
from app.core.config import get_profile_config_loader
```

**Step 2**: Get loader instance
```python
loader = get_profile_config_loader(profile="balanced", tier="medium")
```

**Step 3**: Replace hardcoded values
```python
# Before
model = RandomForestClassifier(n_estimators=100, random_state=42)

# After
params = loader.get_random_forest_params()
model = RandomForestClassifier(**params)
```

## Profile Definitions

### Conservative
- Higher validation requirements (cv_folds=10)
- More conservative model parameters
- Tighter thresholds (RSI buy: 30-40)
- Stricter validation thresholds (min_sharpe: 0.7, max_drawdown: 0.15)

### Balanced (Default)
- Uses all default values
- No overrides applied

### Aggressive
- Faster validation (cv_folds=3)
- Less conservative model parameters
- Wider thresholds (RSI buy: 15-30)
- Higher reward on P&L, lower drawdown penalty

### Income
- Focus on cash flow
- Higher volume requirements
- Higher win rate requirement (0.50)
- Higher profit factor requirement (2.0)

### Growth
- Larger position sizes
- More concurrent positions
- More RL training timesteps
- Lower momentum thresholds

### Dividendos
- Spanish dividend strategy
- Specific RSI thresholds (25-35 buy, 65-75 sell)
- More trades required (30)

## Tier Definitions

### Micro (<$15k)
- Limited workers (2)
- Fewer model estimators
- Fewer optimization iterations
- Fewer trades required

### Small ($15k-$50k)
- Moderate workers (4)
- Moderate model complexity
- Moderate optimization

### Medium ($50k-$250k)
- Uses default values

### Large (>$250k)
- Maximum workers
- More model estimators
- More optimization iterations
- Higher initial balance for RL
- More training timesteps
- More trades required

## Configuration Validation

The loader automatically validates parameter ranges:

```python
# Will log warning if value is outside configured range
loader.validate_parameter_range(
    "threshold_optimization.rsi.buy_threshold",
    10,  # Too low (min is 20)
    min_key="min",
    max_key="max"
)
# WARNING: Value 10 below minimum 20 for threshold_optimization.rsi.buy_threshold
```

## Cache Management

The loader caches instances for performance:

```python
from app.core.config import clear_loader_cache

# Clear cache to force reload (e.g., after config file changes)
clear_loader_cache()
```

## Best Practices

1. **Always use the loader**: Never hardcode parameters in code
2. **Specify profile and tier**: Let the config system handle variations
3. **Use convenience functions**: They provide cleaner APIs
4. **Validate parameters**: Use the built-in validation methods
5. **Document profile choices**: Add comments explaining why a specific profile was chosen

## Testing

```python
# Test profile loading
loader = get_profile_config_loader(profile="conservative")
assert loader.get_cv_folds() == 10  # Conservative override

# Test tier loading
loader = get_profile_config_loader(tier="micro")
assert loader.get_max_workers(8) == 2  # Micro override

# Test combined
loader = get_profile_config_loader(
    profile="aggressive",
    tier="large"
)
rf_params = loader.get_random_forest_params()
assert rf_params['min_samples_split'] == 5  # Profile override
assert rf_params['n_estimators'] == 150     # Tier override
```

## Summary

This configuration system centralizes 50+ parameters across:
- Common backtesting parameters
- Threading and parallelization
- Machine learning model parameters
- Reinforcement learning configuration
- Threshold optimization ranges
- Validation settings
- Reporting configuration
- Memory management

All while supporting:
- Profile-specific overrides (6 profiles)
- Tier-specific overrides (4 tiers)
- Parameter validation
- Default value handling
- Caching for performance
