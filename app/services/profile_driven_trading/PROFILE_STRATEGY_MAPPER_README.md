# ProfileStrategyMapper Implementation

## Overview

The `ProfileStrategyMapper` is a core component that translates user investment profiles into concrete trading configurations. It acts as the bridge between user intent (InputProfile) and strategy execution, using centralized configuration files to determine the optimal strategy combination, capital allocation, and risk parameters.

## Architecture

### Configuration Sources

The mapper uses three centralized configuration files:

1. **`config/investment_profiles.yaml`** - Defines strategy mappings for each objective and capital tier
2. **`config/learning_parameters.yaml`** - Parameters for ML/DL/RL learning engines
3. **`config/strategies/ensemble.yaml`** - Ensemble mode configurations

### Key Components

```
InputProfile
    ↓
ProfileStrategyMapper
    ↓
StrategyMapping {
    - enabled_strategies: List[str]
    - strategy_weights: Dict[str, float]
    - risk_params: Dict
    - capital_allocation: Dict[str, Decimal]
    - learning_engines: List[str]
    - ensemble_config: Dict
}
```

## Features

### 1. Objective-to-Strategy Mapping

Maps investment objectives to appropriate strategy combinations:

| Objective | Strategies |
|-----------|------------|
| `MAXIMIZAR_CAPITAL` | momentum + mean_reversion + pairs_trading + learning |
| `MAXIMIZAR_DIVIDENDOS` | dividend_screener + dividend_predictor |
| `CAPITAL_PRESERVATION` | defensive_momentum + hedge_strategies |
| `BALANCED_GROWTH` | momentum + mean_reversion + dividend_screener |
| `INCOME_GENERATION` | dividend + covered_call + put_seller |

### 2. Capital Tier System

Automatically determines capital tier and adjusts complexity:

| Tier | Capital Range | Strategies | Learning |
|------|---------------|------------|----------|
| `micro` | < €15k | 1-2 | None |
| `small` | €15k - €50k | 2-3 | Supervised |
| `medium` | €50k - €250k | 3-4 | Supervised + RL |
| `large` | ≥ €250k | 4+ | All engines |

### 3. Risk Tolerance to Ensemble Mapping

Adjusts ensemble mode based on risk tolerance:

| Risk Tolerance | Ensemble Mode | Min Strategies | Confidence |
|----------------|---------------|----------------|------------|
| `BAJO` | `voting_ensemble` | 3 | 70% |
| `MEDIO` | `weighted_ensemble` | 2 | 50% |
| `ALTO` | `regime_selector` | 1 | 40% |

### 4. Dynamic Capital Allocation

Calculates optimal capital distribution across strategies:

```python
# Example: €100,000 with balanced growth
{
    "momentum_modular": €50,000 (50%),
    "mean_reversion_modular": €30,000 (30%),
    "dividend_screener": €20,000 (20%),
}
```

Weights are adjusted based on:
- Risk tolerance (conservative → balanced weights)
- Strategy count (normalization)
- Performance expectations (momentum focus for aggressive)

### 5. Learning Engine Selection

Determines which ML/DL engines to enable:

- **Supervised Learning**: Random Forest, XGBoost, LightGBM
- **Deep Learning**: LSTM, GRU, Transformer models
- **Reinforcement Learning**: PPO, A2C, DDPG

Availability depends on:
- Capital tier (ML only for medium+)
- Objective (growth objectives enable learning)
- Profile configuration (`ml_ensemble` module)

## Usage

### Basic Usage

```python
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading.profile_strategy_mapper import (
    ProfileStrategyMapper,
    map_profile_to_strategies,
)

# Create user profile
profile = InputProfile(
    capital_initial=100000,
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    risk_tolerance=RiskTolerance.MEDIO,
    investment_horizon=24,
)

# Option 1: Use convenience function
mapping = map_profile_to_strategies(profile)

# Option 2: Use mapper directly
mapper = ProfileStrategyMapper()
mapping = mapper.create_strategy_mapping(profile)

# Access configuration
print(f"Strategies: {mapping.enabled_strategies}")
print(f"Allocation: {mapping.capital_allocation}")
print(f"Ensemble: {mapping.ensemble_mode}")
```

### Getting Strategy Configuration

```python
mapper = ProfileStrategyMapper()

# Get basic strategy configuration
strategy_config = mapper.map_profile_to_strategies(profile)

print(strategy_config)
# {
#     'enabled_strategies': ['momentum_modular', 'mean_reversion_modular'],
#     'risk_params': {'risk_profile': 4, 'leverage': 1.5},
#     'learning_engines': ['supervised'],
#     'ensemble_config': {'mode': 'weighted_ensemble', ...}
# }
```

### Getting Capital Allocation

```python
mapper = ProfileStrategyMapper()

# Get allocation manager
allocation_manager = mapper.get_capital_allocation(profile)

# Get allocated capital per strategy
allocations = allocation_manager.allocate_capital()

for strategy, capital in allocations.items():
    print(f"{strategy}: €{capital:,.2f}")
```

### Getting Learning Parameters

```python
mapper = ProfileStrategyMapper()

# Get parameters for specific engine
params = mapper.get_learning_parameters(profile, "supervised")

print(params)
# {
#     'training': {'test_size': 0.2, 'min_samples': 100},
#     'models': {'random_forest': {...}, 'xgboost': {...}}
# }
```

## Configuration Files

### investment_profiles.yaml Structure

```yaml
profiles:
  maximizar_capital:
    micro:
      risk_profile: 2
      leverage: 0
      enabled_modules:
        - momentum_modular
      max_position_size: 0.15
      max_sector_allocation: 0.20
      order_splitting_strategy: twap
      commission_negotiation: false

    small:
      risk_profile: 3
      leverage: 0.5
      enabled_modules:
        - momentum_modular
        - mean_reversion_modular
      # ...

    medium:
      # ...

    large:
      # ...

  balanced_growth:
    # ...

  # Other objectives...

defaults:
  risk_profile: 4
  leverage: 1.0
  max_position_size: 0.20
  # ...
```

### ensemble.yaml Structure

```yaml
voting_ensemble:
  name: "voting_ensemble"
  min_strategies_for_signal: 2
  min_votes: 2
  require_majority: true
  unanimous_boost: 1.2

weighted_ensemble:
  name: "weighted_ensemble"
  min_strategies_for_signal: 2
  weight_method: "sharpe"
  performance_lookback: 30
  weight_decay: 0.95

regime_selector:
  name: "regime_selector"
  min_strategies_for_signal: 1
  regime_lookback: 50
  regime_strategy_map:
    trending_up: [...]
    mean_reverting: [...]
```

### learning_parameters.yaml Structure

```yaml
supervised_learning:
  training:
    test_size: 0.2
    min_samples: 100
  models:
    random_forest:
      n_estimators: 100
      max_depth: 10

reinforcement_learning:
  algorithm:
    type: "PPO"
  training:
    total_timesteps: 100000

tiers:
  micro:
    supervised_learning:
      training:
        min_samples: 50
  large:
    reinforcement_learning:
      training:
        total_timesteps: 200000
```

## Advanced Features

### Custom Configuration Paths

```python
mapper = ProfileStrategyMapper(
    investment_profiles_path="config/custom_profiles.yaml",
    learning_params_path="config/custom_learning.yaml",
    ensemble_config_path="config/custom_ensemble.yaml",
)
```

### Strategy Weights Calculation

Weights are calculated based on:

1. **Base weight**: Equal distribution among strategies
2. **Risk adjustment**: Applied based on risk tolerance
3. **Normalization**: Ensures weights sum to 1.0

```python
def _calculate_strategy_weights(
    strategies,
    profile_config,
    risk_tolerance
):
    base_weight = 1.0 / len(strategies)

    risk_adjustments = {
        RiskTolerance.BAJO: {
            "momentum_modular": 0.8,  # Reduce momentum
            "mean_reversion_modular": 1.2,  # Increase mean reversion
            "dividend_screener": 1.5,  # Increase dividend
        },
        RiskTolerance.MEDIO: {
            # Balanced weights (1.0)
        },
        RiskTolerance.ALTO: {
            "momentum_modular": 1.3,  # Increase momentum
            "dividend_screener": 0.5,  # Reduce dividend
        },
    }

    # Apply adjustments and normalize
    # ...
```

### Tier-Specific Overrides

Learning parameters can be overridden per capital tier:

```yaml
tiers:
  micro:
    supervised_learning:
      training:
        min_samples: 50  # Lower minimum for micro

  large:
    reinforcement_learning:
      training:
        total_timesteps: 200000  # More training for large
```

The mapper automatically applies these overrides when fetching parameters.

## Testing

### Running Unit Tests

```bash
# Run all tests
pytest tests/unit/services/test_profile_strategy_mapper.py

# Run specific test class
pytest tests/unit/services/test_profile_strategy_mapper.py::TestProfileStrategyMapperInit

# Run with coverage
pytest --cov=app/services/profile_driven_trading/profile_strategy_mapper \
       tests/unit/services/test_profile_strategy_mapper.py
```

### Running Examples

```bash
# Run all examples
python examples/profile_strategy_mapper_examples.py

# Expected output:
# EXAMPLE 1: Basic Profile to Strategy Mapping
# User Profile:
#   Capital: €100,000.00
#   Objective: maximizar_capital
#   Risk Tolerance: medio
#   Horizon: 24 months
# ...
```

## Integration Points

### With StrategyFactory

```python
from app.backtesting.factories import StrategyFactory

mapper = ProfileStrategyMapper()
mapping = mapper.create_strategy_mapping(profile)

# Create strategies using factory
strategies = {}
for strategy_name in mapping.enabled_strategies:
    config = {
        'type': strategy_name,
        'parameters': mapping.risk_params,
        'thresholds': {...}
    }
    strategies[strategy_name] = StrategyFactory.create_strategy(config)
```

### With MultiStrategyAllocationManager

```python
from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

mapper = ProfileStrategyMapper()
allocation_manager = mapper.get_capital_allocation(profile)

# The manager is already configured with proper allocations
allocations = allocation_manager.allocate_capital()

# Update based on performance
selector = DynamicPortfolioSelector(allocation_manager)
if selector.should_rebalance():
    new_allocations = selector.rebalance_allocations()
```

### With Learning Engines

```python
from app.strategies.momentum_modular.learning import (
    SupervisedLearningEngine,
    ReinforcementLearningEngine,
)

mapper = ProfileStrategyMapper()
learning_engines = mapper.get_learning_engines(profile)

engines = {}
for engine_type in learning_engines:
    params = mapper.get_learning_parameters(profile, engine_type)

    if engine_type == "supervised":
        engine = SupervisedLearningEngine(params)
    elif engine_type == "reinforcement":
        engine = ReinforcementLearningEngine(params)

    engines[engine_type] = engine
```

## Error Handling

The mapper handles missing configurations gracefully:

```python
# Missing objective → falls back to defaults
# Missing tier → falls back to closest tier
# Missing file → logs warning, uses empty config
# Invalid enum → raises ValueError with clear message
```

Example error handling:

```python
try:
    mapping = mapper.create_strategy_mapping(profile)
except ValueError as e:
    logger.error(f"Invalid profile configuration: {e}")
    # Handle error: use defaults or notify user
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle unexpected error
```

## Performance Considerations

1. **Configuration Loading**: YAML files are loaded once at initialization
2. **Caching**: Strategy mappings are not cached (recreate for each profile)
3. **Validation**: Pydantic validates all configurations on creation

## Future Enhancements

Potential improvements:

1. **Caching**: Add LRU cache for frequently accessed profiles
2. **Dynamic Updates**: Watch config files for changes and reload
3. **Validation**: Add pre-flight validation of configuration files
4. **Metrics**: Track which configurations are most commonly used
5. **A/B Testing**: Support multiple configurations per objective

## Files Created

1. **`app/services/profile_driven_trading/profile_strategy_mapper.py`** - Main implementation
2. **`examples/profile_strategy_mapper_examples.py`** - Usage examples
3. **`tests/unit/services/test_profile_strategy_mapper.py`** - Unit tests
4. **`config/strategies/ensemble.yaml`** - Ensemble configurations (updated)

## Dependencies

- `pyyaml` - YAML configuration parsing
- `pydantic` - Data validation
- `decimal` - Precise financial calculations
- Existing services: `MultiStrategyAllocationManager`, `StrategyFactory`

## Migration Guide

If you're migrating from hardcoded strategy selection:

### Before (Hardcoded)

```python
if capital < 50000:
    strategies = ["momentum"]
    leverage = 0.5
elif capital < 250000:
    strategies = ["momentum", "mean_reversion"]
    leverage = 1.0
else:
    strategies = ["momentum", "mean_reversion", "pairs"]
    leverage = 2.0
```

### After (Config-Driven)

```python
mapper = ProfileStrategyMapper()
mapping = mapper.create_strategy_mapping(profile)

strategies = mapping.enabled_strategies
leverage = mapping.leverage

# All values from config/investment_profiles.yaml
```

## Support

For questions or issues:

1. Check configuration files exist in `config/`
2. Review examples in `examples/profile_strategy_mapper_examples.py`
3. Run unit tests to verify installation
4. Check logs for validation errors

## Summary

The ProfileStrategyMapper provides:

- **Flexible Mapping**: Objectives → Strategies via YAML config
- **Capital Tier System**: Automatic complexity adjustment
- **Risk-Based Ensemble**: Conservative → Aggressive modes
- **Dynamic Allocation**: Optimal capital distribution
- **Learning Integration**: ML/DL/RL engine selection
- **Zero Hardcoding**: All values from configuration

This enables the system to adapt to different investor profiles without code changes, making it truly parametrizable and maintainable.
