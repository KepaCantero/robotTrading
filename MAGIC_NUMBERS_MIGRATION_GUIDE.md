# Magic Numbers Migration Guide

## Overview

This guide explains how to migrate hardcoded magic numbers throughout the codebase to use the new centralized configuration system.

## What Was Done

### Created Configuration Files

1. **`config/indicators.yaml`** - Technical indicator thresholds
   - RSI periods and thresholds (30, 70, 45, 55)
   - Moving average periods (10, 20, 50, 200)
   - ATR periods and multipliers (14, 1.0, 2.0, 3.0)
   - Stochastic RSI, MACD, Bollinger Bands parameters
   - Volume thresholds
   - Z-score parameters

2. **`config/risk_management.yaml`** - Risk parameters
   - Position sizing (0.01, 0.10, 0.25)
   - Stop loss percentages (0.015, 0.05, 0.08)
   - Take profit percentages (0.02, 0.10, 0.15)
   - Risk/reward ratios (1.5, 2.0, 3.0, 4.0)
   - Leverage limits (1.0, 1.2, 1.5, 2.0)
   - Portfolio limits (max exposure, concentration)

3. **`config/capital_tiers.yaml`** - Capital tier thresholds
   - Tier boundaries (15000, 50000, 250000, 1000000)
   - Tier-specific position sizes
   - Tier-specific risk limits
   - Module permissions by tier
   - Commission rates by tier

4. **`app/core/config/strategy_config_loader.py`** - Configuration loader
   - Centralized config loading from YAML
   - Type-safe access methods
   - Tier-specific overrides
   - Caching for performance

### Updated Files

1. **`app/strategies/momentum_modular/modules/filters/rsi_filter.py`**
   - Now loads RSI thresholds from config
   - Falls back to hardcoded values if config unavailable
   - Demonstrates safe pattern for gradual migration

2. **`app/services/position_sizing_engine.py`**
   - ATR multipliers loaded from config
   - Risk per trade percentages loaded from config
   - Optional parameters with config defaults

3. **`app/core/tier_mapper.py`**
   - Capital thresholds loaded from config
   - Graceful fallback to hardcoded values
   - Lazy loading of config values

## How to Migrate Remaining Files

### Step 1: Identify Magic Numbers

Search for common magic number patterns:

```bash
# RSI thresholds
rg "(30|70|45|55)" app/ --type py -n | grep -i rsi

# Position sizing
rg "(0\.1|0\.25)" app/ --type py -n | grep -i position

# Risk parameters
rg "(5\.0|10\.0|1\.5)" app/ --type py -n | grep -i "stop_loss|take_profit|risk"

# Time periods
rg "(14|20|252)" app/ --type py -n | grep -i "period|lookback"

# Capital thresholds
rg "(15000|50000|250000)" app/ --type py -n | grep -i capital
```

### Step 2: Import Config Loader

Add at the top of your file:

```python
# Import centralized configuration
try:
    from app.core.config.strategy_config_loader import get_strategy_config
    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False
```

### Step 3: Replace Magic Numbers

#### Example 1: RSI Thresholds

**BEFORE:**
```python
if rsi < 30:
    return Signal.BUY
elif rsi > 70:
    return Signal.SELL
```

**AFTER:**
```python
# Load configuration
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    oversold_threshold = config.get_rsi_threshold('extreme_low')
    overbought_threshold = config.get_rsi_threshold('extreme_high')
else:
    # Fallback to hardcoded values
    oversold_threshold = 30
    overbought_threshold = 70

if rsi < oversold_threshold:
    return Signal.BUY
elif rsi > overbought_threshold:
    return Signal.SELL
```

#### Example 2: Position Sizing

**BEFORE:**
```python
max_position_size = capital * Decimal("0.10")
min_position_size = capital * Decimal("0.01")
```

**AFTER:**
```python
# Determine tier and load config
tier = TierMapper.get_tier_from_capital(capital) if HAS_CONFIG_LOADER else 'medium'

if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    max_position_size = capital * config.get_max_position_size(tier)
    min_position_size = capital * config.get_position_sizing(tier, 'min')
else:
    # Fallback to hardcoded values
    max_position_size = capital * Decimal("0.10")
    min_position_size = capital * Decimal("0.01")
```

#### Example 3: ATR Multiplier

**BEFORE:**
```python
atr_multiplier = 2.0
stop_distance = atr * atr_multiplier
```

**AFTER:**
```python
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    atr_multiplier = config.get_atr_multiplier('default_stop')
else:
    atr_multiplier = 2.0

stop_distance = atr * atr_multiplier
```

#### Example 4: Stop Loss Percentage

**BEFORE:**
```python
stop_loss_pct = 0.05  # 5%
stop_loss_price = entry_price * (1 - stop_loss_pct)
```

**AFTER:**
```python
# Load stop loss from config
strategy = 'momentum'  # or 'mean_reversion', 'pairs_trading'
variant = 'default'    # or 'tight', 'wide'

if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    stop_loss_pct = config.get_stop_loss(strategy, variant)
else:
    stop_loss_pct = 0.05

stop_loss_price = entry_price * (1 - stop_loss_pct)
```

#### Example 5: Capital Tier Thresholds

**BEFORE:**
```python
if capital < 15000:
    tier = "micro"
elif capital < 50000:
    tier = "small"
elif capital < 250000:
    tier = "medium"
else:
    tier = "large"
```

**AFTER:**
```python
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    tier = config.get_tier_from_capital(capital)
else:
    # Fallback to hardcoded thresholds
    if capital < 15000:
        tier = "micro"
    elif capital < 50000:
        tier = "small"
    elif capital < 250000:
        tier = "medium"
    else:
        tier = "large"
```

### Step 4: Configuration Reference

#### Indicator Config Methods

```python
from app.core.config.strategy_config_loader import get_strategy_config

config = get_strategy_config()

# RSI
rsi_period = config.get_rsi_period()                    # Default: 14
rsi_oversold = config.get_rsi_threshold('extreme_low')  # 30
rsi_overbought = config.get_rsi_threshold('extreme_high') # 70
rsi_buy_signal = config.get_rsi_threshold('buy_signal') # 45

# Adaptive RSI thresholds
volatile_buy = config.get_rsi_adaptive_threshold('volatile', 'buy_threshold')  # 25
volatile_sell = config.get_rsi_adaptive_threshold('volatile', 'sell_threshold') # 75

# Moving Averages
short_ma = config.get_ma_period('short')   # 10
medium_ma = config.get_ma_period('medium') # 20
long_ma = config.get_ma_period('long')     # 50

# ATR
atr_period = config.get_atr_period()                  # 14
atr_tight_mult = config.get_atr_multiplier('tight_stop')  # 1.0
atr_default_mult = config.get_atr_multiplier('default_stop') # 2.0
atr_wide_mult = config.get_atr_multiplier('wide_stop')    # 3.0
```

#### Risk Management Config Methods

```python
config = get_strategy_config()

# Position sizing (returns Decimal)
position_size = config.get_position_sizing('medium', 'default')  # Decimal('0.10')
max_position = config.get_max_position_size('large')             # Decimal('0.25')

# Stop loss (returns Decimal)
momentum_stop = config.get_stop_loss('momentum', 'default')  # Decimal('0.05')
mr_stop = config.get_stop_loss('mean_reversion', 'tight')    # Decimal('0.015')

# Take profit (returns Decimal)
momentum_tp = config.get_take_profit('momentum', 'default')   # Decimal('0.08')
mr_tp = config.get_take_profit('mean_reversion', 'aggressive') # Decimal('0.12')

# Risk/reward ratio
rr_ratio = config.get_risk_reward_ratio('momentum')  # 2.5

# Leverage
max_lev = config.get_max_leverage('medium')  # 1.5
```

#### Capital Tier Config Methods

```python
config = get_strategy_config()

# Determine tier from capital
tier = config.get_tier_from_capital(Decimal('100000'))  # 'medium'

# Get tier-specific values
max_positions = config.get_max_positions('small')  # 5
enabled_strategies = config.get_enabled_strategies('medium')  # ['momentum', 'mean_reversion', 'pairs_trading']

# Get tier thresholds
thresholds = config.get_tier_thresholds()
# Returns: {'micro': 0, 'small': 15000, 'medium': 50000, 'large': 250000, 'institutional': 1000000}

# Get any tier config value
tier_config = config.get_tier_config_value('medium', 'max_risk_per_trade')
```

## Migration Checklist

Use this checklist to track migration progress:

### Indicator Files
- [ ] `app/strategies/momentum_modular/modules/filters/stoch_rsi_filter.py` - RSI thresholds (30, 70)
- [ ] `app/strategies/mean_reversion.py` - Z-score thresholds (1.5, 2.5, 0.5)
- [ ] `app/engines/strategy_engines/momentum_engine.py` - MA periods
- [ ] `app/services/momentum_analysis.py` - Various periods and thresholds

### Risk Management Files
- [ ] `app/services/risk_scaling_application/limit_adjuster.py` - Position sizes (0.1, 0.25)
- [ ] `app/services/backtesting_orchestration/backtest_orchestrator.py` - Stop loss (5.0), take profit (10.0)
- [ ] `app/services/portfolio_rebalancer.py` - Rebalance thresholds
- [ ] `app/services/circuit_breaker_manager_v2.py` - Drawdown limits (5%, 10%, 15%)

### Capital Tier Files
- [ ] `app/services/learning_capital_gate.py` - Thresholds (15000, 50000, 250000)
- [ ] `app/services/expensive_module_gate.py` - Thresholds (15000, 50000, 250000)
- [ ] `app/services/deployment_validator.py` - Thresholds (15000, 50000, 250000)
- [ ] `app/services/capital_viability_gate.py` - Thresholds (50000)
- [ ] `app/maestro/phase_1/models.py` - Thresholds (15000, 50000, 250000)
- [ ] `app/services/account_configuration.py` - Thresholds (15000, 50000, 250000)

### Time Period Files
- [ ] `app/engines/data_engine/data_engine.py` - Lookback periods
- [ ] `app/services/strategy_stock_allocator.py` - Lookback max days
- [ ] `app/backtesting/walk_forward_validator.py` - Periods

## Best Practices

### 1. Always Provide Fallbacks

```python
# GOOD: Has fallback
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    threshold = config.get_rsi_threshold('extreme_low')
else:
    threshold = 30  # Fallback

# BAD: No fallback, will crash if config unavailable
config = get_strategy_config()
threshold = config.get_rsi_threshold('extreme_low')
```

### 2. Use Type Hints

```python
# GOOD: Type hints
rsi_threshold: int = config.get_rsi_threshold('extreme_low')
position_size: Decimal = config.get_position_sizing('medium')

# BAD: No type hints
threshold = config.get_rsi_threshold('extreme_low')
```

### 3. Document Config Dependencies

```python
"""
This module uses configuration from:
- config/indicators.yaml: RSI thresholds, periods
- config/risk_management.yaml: Position sizing, stop loss

Magic numbers migrated:
- 30, 70 -> config/indicators.yaml (rsi.thresholds.extreme_low/high)
- 0.10, 0.25 -> config/risk_management.yaml (position_sizing)
"""
```

### 4. Lazy Load Config

```python
# GOOD: Lazy load in __init__
class MyStrategy:
    def __init__(self):
        self._config = None

    @property
    def config(self):
        if self._config is None and HAS_CONFIG_LOADER:
            self._config = get_strategy_config()
        return self._config

# BAD: Load at module level
config = get_strategy_config()  # Runs on import
```

### 5. Tier-Aware Configuration

```python
# GOOD: Tier-aware
tier = config.get_tier_from_capital(capital)
max_position = config.get_max_position_size(tier)

# BAD: Ignores tier
max_position = Decimal("0.10")  # Same for all accounts
```

## Testing

After migrating a file, test:

1. **Config Available**: Test with config files present
2. **Config Missing**: Test without config files (fallbacks work)
3. **Tier Variations**: Test with different capital amounts
4. **Edge Cases**: Test boundary conditions (e.g., capital exactly at threshold)

```python
# Example test
def test_rsi_filter_with_config():
    filter = RSIFilter()
    assert filter.period == 14  # Loaded from config

def test_rsi_filter_without_config():
    # Mock HAS_CONFIG_LOADER = False
    filter = RSIFilter()
    assert filter.period == 14  # Fallback value
```

## Validation

After migration, validate:

```python
from app.core.config.strategy_config_loader import get_strategy_config

config = get_strategy_config()

# Validate all config can be loaded
assert config.get_rsi_period() > 0
assert config.get_max_position_size('medium') > 0
assert config.get_stop_loss('momentum') > 0

# Validate tier thresholds
thresholds = config.get_tier_thresholds()
assert thresholds['micro'] < thresholds['small']
assert thresholds['small'] < thresholds['medium']
assert thresholds['medium'] < thresholds['large']
```

## Rollback Plan

If issues arise:

1. **Disable Config**: Set `HAS_CONFIG_LOADER = False` in affected files
2. **Fallback Values**: Ensure all fallback values are correct
3. **Revert File**: Use git to revert specific files if needed
4. **Fix Config**: Correct YAML files if syntax errors

```bash
# Revert a specific file
git checkout HEAD -- app/services/my_file.py

# Disable config loading
# Edit file to set HAS_CONFIG_LOADER = False
```

## Support

For questions or issues:
1. Check this guide first
2. Review config file structure in `/config/`
3. Review example implementations in migrated files
4. Check log output for config loading errors

## Summary

This migration centralizes 157+ magic numbers into 3 configuration files, providing:
- **Single source of truth** for all thresholds
- **Easy adjustment** without code changes
- **Tier-specific customization**
- **Backward compatibility** with fallbacks
- **Type-safe access** with validation

Take your time, migrate gradually, and test thoroughly.
