# Magic Numbers Quick Reference

Quick lookup guide for common magic numbers and their config locations.

## RSI Thresholds

| Magic Number | Config Path | Description |
|-------------|-------------|-------------|
| 30 | `rsi.thresholds.extreme_low` | Oversold threshold (buy zone) |
| 70 | `rsi.thresholds.extreme_high` | Overbought threshold (sell zone) |
| 45 | `rsi.thresholds.buy_signal` | Buy signal threshold |
| 55 | `rsi.thresholds.sell_signal` | Sell signal threshold |
| 14 | `rsi.period.default` | RSI calculation period |

**Usage:**
```python
config = get_strategy_config()
threshold = config.get_rsi_threshold('extreme_low')  # Returns 30
```

## Position Sizing

| Magic Number | Config Path | Description |
|-------------|-------------|-------------|
| 0.01 | `position_sizing.default.min_percent` | Minimum position (1%) |
| 0.10 | `position_sizing.default.percent` | Default position (10%) |
| 0.25 | `position_sizing.default.max_percent` | Maximum position (25%) |

**By Tier:**
| Tier | Max Position | Config Path |
|------|--------------|-------------|
| micro | 10% | `tiers.micro.max_position_percent` |
| small | 15% | `tiers.small.max_position_percent` |
| medium | 20% | `tiers.medium.max_position_percent` |
| large | 25% | `tiers.large.max_position_percent` |

**Usage:**
```python
config = get_strategy_config()
max_size = config.get_max_position_size('medium')  # Returns Decimal('0.20')
```

## Risk Parameters

### Stop Loss

| Magic Number | Config Path | Strategy |
|-------------|-------------|----------|
| 0.015 (1.5%) | `stop_loss.by_strategy.mean_reversion.tight` | Mean Reversion |
| 0.025 (2.5%) | `stop_loss.by_strategy.momentum.tight` | Momentum |
| 0.05 (5%) | `stop_loss.by_strategy.momentum.default` | Default |
| 0.08 (8%) | `stop_loss.by_strategy.momentum.wide` | Wide Stop |

**Usage:**
```python
config = get_strategy_config()
stop_loss = config.get_stop_loss('momentum', 'default')  # Returns Decimal('0.05')
```

### Take Profit

| Magic Number | Config Path | Strategy |
|-------------|-------------|----------|
| 0.06 (6%) | `take_profit.by_strategy.momentum.conservative` | Conservative |
| 0.08 (8%) | `take_profit.by_strategy.momentum.default` | Default |
| 0.10 (10%) | `take_profit.by_strategy.mean_reversion.default` | Default |
| 0.15 (15%) | `take_profit.by_strategy.momentum.aggressive` | Aggressive |

**Usage:**
```python
config = get_strategy_config()
take_profit = config.get_take_profit('momentum', 'default')  # Returns Decimal('0.08')
```

## Time Periods

| Magic Number | Config Path | Description |
|-------------|-------------|-------------|
| 5 | `moving_averages.periods.short` | Short MA period |
| 10 | `moving_averages.periods.very_short` | Very short MA |
| 14 | `atr.period.default` | ATR period |
| 20 | `moving_averages.periods.medium` | Medium MA |
| 50 | `moving_averages.periods.long` | Long MA |
| 200 | `moving_averages.periods.very_long` | Very long MA |
| 252 | `time_periods.trading_days_per_year` | Trading days/year |

**Usage:**
```python
config = get_strategy_config()
ma_period = config.get_ma_period('medium')  # Returns 20
atr_period = config.get_atr_period()  # Returns 14
```

## ATR Multipliers

| Magic Number | Config Path | Description |
|-------------|-------------|-------------|
| 1.0 | `atr.multipliers.tight_stop` | Tight stop (1x ATR) |
| 2.0 | `atr.multipliers.default_stop` | Default stop (2x ATR) |
| 3.0 | `atr.multipliers.wide_stop` | Wide stop (3x ATR) |

**Usage:**
```python
config = get_strategy_config()
multiplier = config.get_atr_multiplier('default_stop')  # Returns 2.0
```

## Capital Thresholds

| Magic Number | Tier | Config Path |
|-------------|------|-------------|
| 0 - 15,000 | micro | `thresholds.micro_small` |
| 15,000 | small boundary | `thresholds.micro_small` |
| 50,000 | medium boundary | `thresholds.small_medium` |
| 250,000 | large boundary | `thresholds.medium_large` |
| 1,000,000 | institutional | `thresholds.large_institutional` |

**Usage:**
```python
config = get_strategy_config()
tier = config.get_tier_from_capital(Decimal('100000'))  # Returns 'medium'
thresholds = config.get_tier_thresholds()  # Returns dict of all thresholds
```

## Risk/Reward Ratios

| Magic Number | Config Path | Description |
|-------------|-------------|-------------|
| 1.5 | `risk_reward.by_strategy.pairs_trading.min_ratio` | Pairs Trading |
| 2.0 | `risk_reward.min_ratio` | Minimum |
| 2.5 | `risk_reward.by_strategy.momentum.min_ratio` | Momentum |
| 3.0 | `risk_reward.target_ratio` | Target |
| 4.0 | `risk_reward.ideal_ratio` | Ideal |

**Usage:**
```python
config = get_strategy_config()
rr_ratio = config.get_risk_reward_ratio('momentum')  # Returns 2.5
```

## Leverage

| Magic Number | Config Path | Tier |
|-------------|-------------|------|
| 1.0 | `leverage.max_leverage.micro` | Micro (no leverage) |
| 1.2 | `leverage.max_leverage.small` | Small |
| 1.5 | `leverage.max_leverage.medium` | Medium |
| 2.0 | `leverage.max_leverage.large` | Large |

**Usage:**
```python
config = get_strategy_config()
max_lev = config.get_max_leverage('medium')  # Returns 1.5
```

## Common Patterns

### Pattern 1: Get Indicator Threshold

```python
# BEFORE
if rsi < 30:
    signal = 'BUY'

# AFTER
config = get_strategy_config()
if rsi < config.get_rsi_threshold('extreme_low'):
    signal = 'BUY'
```

### Pattern 2: Get Position Size

```python
# BEFORE
max_size = capital * Decimal('0.10')

# AFTER
config = get_strategy_config()
tier = config.get_tier_from_capital(capital)
max_size = capital * config.get_max_position_size(tier)
```

### Pattern 3: Get Stop Loss

```python
# BEFORE
stop_pct = 0.05

# AFTER
config = get_strategy_config()
stop_pct = config.get_stop_loss('momentum', 'default')
```

### Pattern 4: Determine Tier

```python
# BEFORE
if capital < 15000:
    tier = 'micro'
elif capital < 50000:
    tier = 'small'
elif capital < 250000:
    tier = 'medium'
else:
    tier = 'large'

# AFTER
config = get_strategy_config()
tier = config.get_tier_from_capital(capital)
```

## Config File Locations

```
config/
├── indicators.yaml          # All indicator parameters
├── risk_management.yaml     # All risk parameters
└── capital_tiers.yaml       # All tier parameters
```

## Quick Import

```python
# Add to top of file
try:
    from app.core.config.strategy_config_loader import get_strategy_config
    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# Use in code
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    value = config.get_rsi_threshold('extreme_low')
else:
    value = 30  # Fallback
```

## Validator Checklist

When migrating magic numbers, ensure:

- [ ] Import config loader with try/except
- [ ] Use HAS_CONFIG_LOADER check
- [ ] Provide fallback value
- [ ] Use correct config path
- [ ] Match data type (int, float, Decimal)
- [ ] Test with config present
- [ ] Test without config (fallback)
- [ ] Update docstring

## Common Mistakes

### Mistake 1: No Fallback

```python
# WRONG - Will crash if config unavailable
config = get_strategy_config()
value = config.get_rsi_threshold('extreme_low')

# CORRECT - Has fallback
if HAS_CONFIG_LOADER:
    config = get_strategy_config()
    value = config.get_rsi_threshold('extreme_low')
else:
    value = 30
```

### Mistake 2: Wrong Type

```python
# WRONG - Returns int, needs Decimal
position = config.get_max_position_size('medium')
result = capital * position  # May fail

# CORRECT - Already Decimal
position = config.get_max_position_size('medium')  # Returns Decimal
result = capital * position  # Works fine
```

### Mistake 3: Hardcoded Tier

```python
# WRONG - Ignores actual capital tier
max_size = config.get_max_position_size('medium')

# CORRECT - Determines tier from capital
tier = config.get_tier_from_capital(capital)
max_size = config.get_max_position_size(tier)
```

## Support

For detailed information:
- See `MAGIC_NUMBERS_MIGRATION_GUIDE.md` for full migration guide
- See `MAGIC_NUMBERS_IMPLEMENTATION_REPORT.md` for implementation details
- Check config files in `/config/` for all available parameters

## Summary

| Category | Count | Config File |
|----------|-------|-------------|
| RSI | 5 | `indicators.yaml` |
| Position | 7 | `risk_management.yaml`, `capital_tiers.yaml` |
| Risk | 8 | `risk_management.yaml` |
| Periods | 7 | `indicators.yaml` |
| Capital | 5 | `capital_tiers.yaml` |
| **Total** | **32** | **3 files** |

All magic numbers now centralized! 🎉
