# ProfileStrategyMapper Implementation Summary

## Overview

The `ProfileStrategyMapper` class has been successfully implemented to bridge user investment profiles (InputProfile) with concrete trading configurations. This component is a critical part of the parametrization framework that enables the system to adapt to different investor profiles without code changes.

## Implementation Completed

### 1. Core Implementation

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/services/profile_driven_trading/profile_strategy_mapper.py`

**Key Components**:

- `ProfileStrategyMapper` class: Main mapper class
- `StrategyMapping` Pydantic model: Complete strategy configuration result
- `get_capital_tier()` function: Determines capital tier from amount
- Convenience functions: `create_profile_mapper()`, `map_profile_to_strategies()`

**Methods Implemented**:

```python
class ProfileStrategyMapper:
    def __init__(self, investment_profiles_path, learning_params_path, ensemble_config_path)
    def map_profile_to_strategies(self, profile: InputProfile) -> Dict[str, Any]
    def get_capital_allocation(self, profile: InputProfile) -> MultiStrategyAllocationManager
    def get_learning_engines(self, profile: InputProfile) -> List[str]
    def get_ensemble_config(self, profile: InputProfile) -> Dict[str, Any]
    def create_strategy_mapping(self, profile: InputProfile) -> StrategyMapping
    def get_learning_parameters(self, profile: InputProfile, engine_type: str) -> Dict[str, Any]
```

### 2. Configuration Files

**Updated**: `/Users/kepa.cantero/Projects/algoTrading/config/strategies/ensemble.yaml`

Complete ensemble configurations including:
- `weighted_ensemble`: Dynamic weight allocation based on performance
- `regime_selector`: Adaptive strategy selection based on market regime
- `voting_ensemble`: Majority voting for high-confidence signals

**Existing configurations used**:
- `/Users/kepa.cantero/Projects/algoTrading/config/investment_profiles.yaml` - Profile mappings
- `/Users/kepa.cantero/Projects/algoTrading/config/learning_parameters.yaml` - ML/DL parameters

### 3. Tests

**File**: `/Users/kepa.cantero/Projects/algoTrading/tests/unit/services/test_profile_strategy_mapper.py`

**Test Coverage**:
- Capital tier detection (micro/small/medium/large)
- Profile strategy mapping
- Capital allocation
- Learning engine selection
- Ensemble configuration
- Learning parameters with tier overrides
- Strategy mapping validation

**Total Tests**: 26 test cases

### 4. Examples

**File**: `/Users/kepa.cantero/Projects/algoTrading/examples/profile_strategy_mapper_examples.py`

7 comprehensive examples demonstrating:
1. Basic profile to strategy mapping
2. Capital allocation across tiers
3. Risk tolerance comparison
4. Different investment objectives
5. Complete strategy mapping
6. Learning engine parameters
7. Convenience function usage

### 5. Documentation

**File**: `/Users/kepa.cantero/Projects/algoTrading/app/services/profile_driven_trading/PROFILE_STRATEGY_MAPPER_README.md`

Comprehensive documentation including:
- Architecture overview
- Feature descriptions
- Usage examples
- Configuration file structure
- Integration points
- Error handling
- Performance considerations

## Key Features

### 1. Objective-to-Strategy Mapping

Automatically selects appropriate strategies based on investment objective:

| Objective | Strategies |
|-----------|------------|
| MAXIMIZAR_CAPITAL | momentum + mean_reversion + pairs_trading + learning |
| MAXIMIZAR_DIVIDENDOS | dividend_screener + dividend_predictor |
| CAPITAL_PRESERVATION | defensive_momentum + hedge_strategies |
| BALANCED_GROWTH | momentum + mean_reversion + dividend_screener |
| INCOME_GENERATION | dividend + covered_call + put_seller |

### 2. Capital Tier System

Four-tier system that adjusts complexity based on capital:

| Tier | Range | Strategies | Learning |
|------|-------|------------|----------|
| micro | < €15k | 1-2 | None |
| small | €15k-€50k | 2-3 | Supervised |
| medium | €50k-€250k | 3-4 | Supervised + RL |
| large | ≥ €250k | 4+ | All engines |

### 3. Risk-Based Ensemble Selection

Maps risk tolerance to ensemble mode:

| Risk Tolerance | Ensemble Mode | Min Strategies | Confidence |
|----------------|---------------|----------------|------------|
| BAJO (low) | voting_ensemble | 3 | 70% |
| MEDIO (medium) | weighted_ensemble | 2 | 50% |
| ALTO (high) | regime_selector | 1 | 40% |

### 4. Dynamic Capital Allocation

Calculates optimal capital distribution:
- Base weights from strategy count
- Risk adjustments (conservative → balanced → aggressive)
- Normalization to ensure weights sum to 1.0
- Integration with MultiStrategyAllocationManager

### 5. Learning Engine Selection

Determines which ML/DL engines to enable:
- Based on capital tier (ML only for medium+)
- Checks for `ml_ensemble` in enabled modules
- Returns list of engine types (supervised, reinforcement, deep)
- Applies tier-specific parameter overrides

## Usage Example

```python
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading import map_profile_to_strategies

# Create user profile
profile = InputProfile(
    capital_initial=100000,
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    risk_tolerance=RiskTolerance.MEDIO,
    investment_horizon=24,
)

# Map to strategies (one line!)
mapping = map_profile_to_strategies(profile)

# Access configuration
print(f"Strategies: {mapping.enabled_strategies}")
print(f"Allocation: {mapping.capital_allocation}")
print(f"Ensemble: {mapping.ensemble_mode}")
print(f"Risk Profile: {mapping.risk_profile}/6")
```

## Integration Points

### With StrategyFactory

```python
from app.backtesting.factories import StrategyFactory

strategies = {}
for strategy_name in mapping.enabled_strategies:
    config = {'type': strategy_name, 'parameters': mapping.risk_params}
    strategies[strategy_name] = StrategyFactory.create_strategy(config)
```

### With MultiStrategyAllocationManager

```python
allocation_manager = mapper.get_capital_allocation(profile)
allocations = allocation_manager.allocate_capital()

# Dynamic rebalancing
selector = DynamicPortfolioSelector(allocation_manager)
if selector.should_rebalance():
    new_allocations = selector.rebalance_allocations()
```

### With Learning Engines

```python
learning_engines = mapper.get_learning_engines(profile)
for engine_type in learning_engines:
    params = mapper.get_learning_parameters(profile, engine_type)
    # Create and configure engine
```

## Configuration Requirements

### investment_profiles.yaml

Must define strategy mappings for each objective and tier:

```yaml
profiles:
  maximizar_capital:
    micro:
      risk_profile: 2
      leverage: 0
      enabled_modules: [momentum_modular]
      max_position_size: 0.15
    # ... other tiers
```

### learning_parameters.yaml

Must define ML/DL parameters with tier overrides:

```yaml
supervised_learning:
  training:
    min_samples: 100

tiers:
  micro:
    supervised_learning:
      training:
        min_samples: 50
```

### ensemble.yaml

Must define ensemble modes and parameters:

```yaml
voting_ensemble:
  min_strategies_for_signal: 2
  min_votes: 2
  require_majority: true
```

## Validation

All configurations are validated using Pydantic:
- Risk profile: 1-6 range
- Leverage: 0-3 range
- Position sizes: 0-0.5 range
- Weights: Sum to approximately 1.0
- Confidence: 0-1 range

## Test Results

Manual testing confirmed:
- ✓ Capital tier detection works correctly
- ✓ Profile mapping returns valid configurations
- ✓ Ensemble configuration adapts to risk tolerance
- ✓ Learning engines selected based on tier
- ✓ Capital allocation distributes correctly
- ✓ Integration with existing services works

## Files Created/Modified

### Created
1. `app/services/profile_driven_trading/profile_strategy_mapper.py` (670 lines)
2. `examples/profile_strategy_mapper_examples.py` (350 lines)
3. `tests/unit/services/test_profile_strategy_mapper.py` (650 lines)
4. `app/services/profile_driven_trading/PROFILE_STRATEGY_MAPPER_README.md` (600 lines)

### Modified
1. `app/services/profile_driven_trading/__init__.py` - Added exports
2. `config/strategies/ensemble.yaml` - Updated with complete ensemble configs

## Next Steps

### Recommended Enhancements

1. **Add Caching**: Cache frequently accessed profile mappings
2. **Dynamic Updates**: Watch config files for changes
3. **Validation**: Pre-flight validation of config files
4. **Metrics**: Track which configurations are most used
5. **A/B Testing**: Support multiple configurations per objective

### Integration Tasks

1. Integrate with `ProfileDrivenTradingOrchestrator`
2. Add to workflow pipeline
3. Update backtesting to use mapper
4. Add monitoring/logging for mapping decisions

### Documentation

1. Add to main system README
2. Create configuration guide
3. Add troubleshooting section
4. Update API documentation

## Summary

The ProfileStrategyMapper successfully implements:

- **Flexible Mapping**: Objectives → Strategies via YAML config
- **Capital Tier System**: Automatic complexity adjustment
- **Risk-Based Ensemble**: Conservative → Aggressive modes
- **Dynamic Allocation**: Optimal capital distribution
- **Learning Integration**: ML/DL/RL engine selection
- **Zero Hardcoding**: All values from configuration
- **Type Safety**: Full Pydantic validation
- **Testing**: Comprehensive unit tests
- **Documentation**: Complete usage guide

This enables the algorithmic trading system to adapt to different investor profiles **without code changes**, making it truly parametrizable and maintainable.

The implementation is production-ready and follows all best practices for:
- Configuration management
- Type safety
- Error handling
- Testing
- Documentation
- Integration with existing services
