# Profile Configuration Migration Guide

## Overview

This guide shows how to replace hardcoded values with the new profile configuration system in existing code.

## Migration Examples

### Example 1: Random Forest Parameters

**Before** (in `comprehensive_backtest_runner.py`):
```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1
)
```

**After**:
```python
from sklearn.ensemble import RandomForestClassifier
from app.core.config import get_model_params

params = get_model_params("random_forest", profile="balanced")
model = RandomForestClassifier(**params)
```

### Example 2: Train/Test Split

**Before**:
```python
from sklearn.model_selection import train_test_split

X_train, X_test = train_test_split(
    X,
    test_size=0.2,
    random_state=42
)
```

**After**:
```python
from sklearn.model_selection import train_test_split
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()
X_train, X_test = train_test_split(
    X,
    test_size=loader.get_test_size(),
    random_state=loader.get_random_state()
)
```

### Example 3: Cross-Validation

**Before**:
```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(
    model,
    X_train,
    y_train,
    cv=5,
    scoring='sharpe'
)
```

**After**:
```python
from sklearn.model_selection import cross_val_score
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()
scores = cross_val_score(
    model,
    X_train,
    y_train,
    cv=loader.get_cv_folds(),
    scoring=loader.get_optimization_scoring()
)
```

### Example 4: Reinforcement Learning Environment

**Before**:
```python
env_config = {
    'initial_balance': 100000,
    'commission': 0.001,
    'slippage': 0.0005,
}
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(tier="medium")
env_config = loader.get_rl_environment_config()
```

### Example 5: RL Reward Configuration

**Before**:
```python
reward_config = {
    'pnl_weight': 1.0,
    'sharpe_weight': 0.3,
    'drawdown_penalty': 0.5,
    'transaction_cost': 0.001,
}
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(profile="aggressive")
reward_config = loader.get_rl_reward_config()
```

### Example 6: RL Algorithm Parameters

**Before**:
```python
ppo_params = {
    'learning_rate': 0.0003,
    'n_steps': 2048,
    'batch_size': 64,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
}
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()
ppo_params = loader.get_rl_algorithm_params("ppo")
```

### Example 7: RSI Thresholds

**Before**:
```python
rsi_buy_threshold = 30
rsi_sell_threshold = 70
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()
rsi_config = loader.get_threshold_config("rsi")

rsi_buy_threshold = rsi_config['buy_threshold']['default']
rsi_sell_threshold = rsi_config['sell_threshold']['default']
```

### Example 8: Validation Thresholds

**Before**:
```python
MIN_SHARPE = 0.5
MAX_DRAWDOWN = 0.2
MIN_WIN_RATE = 0.45
MIN_TRADES = 20
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(profile="conservative")
thresholds = loader.get_validation_thresholds()

MIN_SHARPE = thresholds['min_sharpe']
MAX_DRAWDOWN = thresholds['max_drawdown']
MIN_WIN_RATE = thresholds['min_win_rate']
MIN_TRADES = thresholds['min_trades']
```

### Example 9: Threading Configuration

**Before**:
```python
import multiprocessing

max_workers = None  # Auto-detect
batch_size = 32
```

**After**:
```python
import multiprocessing
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(tier="micro")
cpu_count = multiprocessing.cpu_count()

max_workers = loader.get_max_workers(cpu_count)
batch_size = loader.get_batch_size()
```

### Example 10: Clustering with Random State

**Before** (in `clustering_analyzer.py`):
```python
from sklearn.cluster import KMeans

kmeans = KMeans(
    n_clusters=5,
    random_state=42,
    n_init=10
)
```

**After**:
```python
from sklearn.cluster import KMeans
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader()
kmeans = KMeans(
    n_clusters=5,
    random_state=loader.get_random_state(),
    n_init=10
)
```

### Example 11: Complete Backtest Config

**Before**:
```python
config = {
    'random_state': 42,
    'test_size': 0.2,
    'cv_folds': 5,
    'min_train_samples': 100,

    'rf_n_estimators': 100,
    'rf_max_depth': 10,
    'rf_min_samples_split': 10,

    'rl_initial_balance': 100000,
    'rl_commission': 0.001,
    'rl_learning_rate': 0.0003,

    'rsi_buy_min': 20,
    'rsi_buy_max': 35,
    'rsi_sell_min': 65,
    'rsi_sell_max': 80,

    'min_sharpe': 0.5,
    'max_drawdown': 0.2,
}
```

**After**:
```python
from app.core.config import get_profile_config_loader

loader = get_profile_config_loader(
    profile="balanced",
    tier="medium"
)

config = {
    # Common
    'random_state': loader.get_random_state(),
    'test_size': loader.get_test_size(),
    'cv_folds': loader.get_cv_folds(),
    'min_train_samples': loader.get_min_train_samples(),

    # Models
    'rf_params': loader.get_random_forest_params(),

    # RL
    'rl_env': loader.get_rl_environment_config(),
    'rl_rewards': loader.get_rl_reward_config(),
    'rl_training': loader.get_rl_training_params(),
    'rl_ppo': loader.get_rl_algorithm_params("ppo"),

    # Thresholds
    'rsi_thresholds': loader.get_threshold_config("rsi"),
    'optimization_method': loader.get_optimization_method(),
    'optimization_scoring': loader.get_optimization_scoring(),

    # Validation
    'validation_thresholds': loader.get_validation_thresholds(),
    'walk_forward': loader.get_walk_forward_config(),
    'monte_carlo': loader.get_monte_carlo_config(),

    # Reporting
    'output_dir': loader.get_output_directory(),
    'report_metrics': loader.get_report_metrics("advanced"),

    # Memory
    'memory_config': loader.get_memory_config(),
}
```

## File-by-File Migration

### 1. comprehensive_backtest_runner.py

**Find**:
```python
random_state=42
```

**Replace with**:
```python
from app.core.config import get_profile_config_loader
loader = get_profile_config_loader()
random_state = loader.get_random_state()
```

### 2. walk_forward_validator.py

**Find**:
```python
random_state = config.get("random_state", 42)
```

**Replace with**:
```python
from app.core.config import get_profile_config_loader
loader = get_profile_config_loader(tier=tier)
random_state = loader.get_random_state()
```

### 3. reinforcement_learning_engine.py

**Find**:
```python
reward_config = {
    "pnl_weight": 1.0,
    "sharpe_weight": 0.3,
    "drawdown_penalty": 0.5,
    "transaction_cost": 0.001,
}
```

**Replace with**:
```python
from app.core.config import get_profile_config_loader
loader = get_profile_config_loader(profile=profile)
reward_config = loader.get_rl_reward_config()
```

### 4. clustering_analyzer.py

**Find**:
```python
def __init__(self, random_state: int = 42, n_jobs: int = -1):
    self.random_state = random_state
```

**Replace with**:
```python
def __init__(self, random_state: Optional[int] = None, n_jobs: int = -1):
    from app.core.config import get_profile_config_loader
    loader = get_profile_config_loader()
    self.random_state = random_state or loader.get_random_state()
```

### 5. regime_analyzer.py

**Find**:
```python
def __init__(self, n_regimes: int = 3, window: int = 20, random_state: int = 42):
    self.random_state = random_state
```

**Replace with**:
```python
def __init__(self, n_regimes: int = 3, window: int = 20, random_state: Optional[int] = None):
    from app.core.config import get_profile_config_loader
    loader = get_profile_config_loader()
    self.random_state = random_state or loader.get_random_state()
```

## Testing Migrations

### Unit Test Example

**Before**:
```python
def test_random_forest():
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )
    assert model.n_estimators == 100
```

**After**:
```python
def test_random_forest():
    from app.core.config import get_model_params
    params = get_model_params("random_forest")
    model = RandomForestClassifier(**params)
    assert params['n_estimators'] == 100
    assert params['random_state'] == 42
```

### Integration Test Example

```python
def test_profile_overrides():
    from app.core.config import get_profile_config_loader

    # Test conservative profile
    conservative = get_profile_config_loader(profile="conservative")
    assert conservative.get_cv_folds() == 10

    # Test aggressive profile
    aggressive = get_profile_config_loader(profile="aggressive")
    assert aggressive.get_cv_folds() == 3

    # Test tier overrides
    micro = get_profile_config_loader(tier="micro")
    rf_params = micro.get_random_forest_params()
    assert rf_params['n_estimators'] == 50
```

## Best Practices

1. **Import at module level**:
   ```python
   from app.core.config import get_profile_config_loader
   ```

2. **Create loader once**:
   ```python
   loader = get_profile_config_loader(profile="balanced", tier="medium")
   ```

3. **Use convenience functions when possible**:
   ```python
   params = get_model_params("random_forest")  # Better
   # vs
   loader = get_profile_config_loader()
   params = loader.get_random_forest_params()  # More verbose
   ```

4. **Log profile choices**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   loader = get_profile_config_loader(profile="aggressive")
   logger.info(f"Using profile: aggressive")
   ```

5. **Validate parameters**:
   ```python
   loader = get_profile_config_loader()
   is_valid = loader.validate_parameter_range(
       "threshold_optimization.rsi.buy_threshold",
       user_value
   )
   ```

## Rollback Plan

If issues arise after migration:

1. **Check profile/tier**:
   ```python
   # Explicitly set to defaults
   loader = get_profile_config_loader()  # No profile, no tier
   ```

2. **Validate config exists**:
   ```python
   config_path = Path("config/backtesting/profile_optimization.yaml")
   assert config_path.exists()
   ```

3. **Clear cache**:
   ```python
   from app.core.config import clear_loader_cache
   clear_loader_cache()
   ```

4. **Check for missing keys**:
   ```python
   value = loader.get("some.key.path", default_value)
   ```

## Checklist

For each file to migrate:

- [ ] Import the config loader
- [ ] Identify all hardcoded parameters
- [ ] Replace with config calls
- [ ] Add profile/tier parameters if needed
- [ ] Update tests
- [ ] Add logging for profile choices
- [ ] Document migration in commit message
- [ ] Verify backward compatibility

## Common Patterns

### Pattern 1: Class Initialization

```python
class Backtester:
    def __init__(self, config=None, profile="balanced", tier="medium"):
        self.loader = get_profile_config_loader(profile=profile, tier=tier)
        self.config = config or self._get_default_config()

    def _get_default_config(self):
        return {
            'random_state': self.loader.get_random_state(),
            'test_size': self.loader.get_test_size(),
            # ...
        }
```

### Pattern 2: Function Arguments

```python
def run_backtest(
    symbol: str,
    profile: str = "balanced",
    tier: str = "medium"
):
    loader = get_profile_config_loader(profile=profile, tier=tier)
    config = { ... }
    # ...
```

### Pattern 3: Optional Override

```python
def train_model(params=None, profile="balanced"):
    loader = get_profile_config_loader(profile=profile)
    default_params = loader.get_random_forest_params()

    if params:
        default_params.update(params)

    model = RandomForestClassifier(**default_params)
    return model
```

## Summary

This migration guide provides:
- ✅ 11 specific code examples
- ✅ File-by-file migration instructions
- ✅ Testing strategies
- ✅ Best practices
- ✅ Rollback plan
- ✅ Common patterns

All hardcoded values can now be replaced with the centralized configuration system.
