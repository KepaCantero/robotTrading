# Profile Configuration Quick Reference

## Import
```python
from app.core.config import (
    get_profile_config_loader,
    get_common_params,
    get_model_params,
    get_threshold_ranges,
    get_rl_config,
)
```

## Quick Start

### Basic Usage
```python
loader = get_profile_config_loader()
random_state = loader.get_random_state()  # 42
```

### With Profile
```python
loader = get_profile_config_loader(profile="aggressive")
rf_params = loader.get_random_forest_params()
```

### With Tier
```python
loader = get_profile_config_loader(tier="micro")
max_workers = loader.get_max_workers()
```

### With Both
```python
loader = get_profile_config_loader(profile="conservative", tier="large")
```

## Common Methods

### Get Parameters
```python
loader.get_random_state()           # Random seed
loader.get_test_size()              # 0.2
loader.get_cv_folds()               # 5
loader.get_min_train_samples()      # 100
```

### Model Parameters
```python
loader.get_random_forest_params()   # Dict with all RF params
loader.get_xgboost_params()         # Dict with all XGBoost params
loader.get_lightgbm_params()        # Dict with all LightGBM params
```

### RL Configuration
```python
loader.get_rl_environment_config()  # Environment settings
loader.get_rl_reward_config()       # Reward configuration
loader.get_rl_algorithm_params("ppo")  # PPO parameters
loader.get_rl_training_params()     # Training settings
```

### Thresholds
```python
loader.get_threshold_config("rsi")  # RSI threshold ranges
loader.get_optimization_method()    # "grid_search"
loader.get_optimization_scoring()   # "sharpe"
```

### Validation
```python
loader.get_walk_forward_config()    # Walk-forward settings
loader.get_monte_carlo_config()     # Monte Carlo settings
loader.get_validation_thresholds()  # Performance thresholds
```

### Convenience Functions
```python
get_common_params()                 # Dict of common params
get_model_params("random_forest")   # Model params dict
get_threshold_ranges("rsi")         # Threshold ranges
get_rl_config()                     # Complete RL config
```

## Profiles

- `conservative` - Lower risk, stable returns
- `balanced` - Default profile
- `aggressive` - Higher risk, growth-focused
- `income` - Focus on cash flow
- `growth` - Long-term appreciation
- `dividendos` - Spanish dividend strategy

## Tiers

- `micro` - <$15k
- `small` - $15k-$50k
- `medium` - $50k-$250k
- `large` - >$250k

## Parameter Paths

### Common
```
common.random_state
common.test_size
common.cv_folds
common.min_train_samples
```

### Models
```
models.random_forest.n_estimators
models.xgboost.learning_rate
models.lightgbm.num_leaves
```

### RL
```
reinforcement_learning.environment.initial_balance
reinforcement_learning.rewards.pnl_weight
reinforcement_learning.algorithms.ppo.learning_rate
```

### Thresholds
```
threshold_optimization.rsi.buy_threshold
threshold_optimization.momentum.threshold
```

## Example: Full Backtest Config

```python
loader = get_profile_config_loader(
    profile="balanced",
    tier="medium"
)

config = {
    # Common
    'random_state': loader.get_random_state(),
    'test_size': loader.get_test_size(),
    'cv_folds': loader.get_cv_folds(),

    # Models
    'rf_params': loader.get_random_forest_params(),
    'xgb_params': loader.get_xgboost_params(),

    # RL
    'rl_env': loader.get_rl_environment_config(),
    'rl_rewards': loader.get_rl_reward_config(),

    # Thresholds
    'rsi_thresholds': loader.get_threshold_config("rsi"),

    # Validation
    'validation': loader.get_validation_thresholds(),
}
```

## Validation

```python
# Check if value is in range
is_valid = loader.validate_parameter_range(
    "threshold_optimization.rsi.buy_threshold",
    25
)

# Get range
min_val, max_val, step = loader.get_parameter_range(
    "threshold_optimization.rsi.buy_threshold"
)
```

## Clear Cache

```python
from app.core.config import clear_loader_cache
clear_loader_cache()
```
