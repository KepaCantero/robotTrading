# Parameter Optimization Guide

## Overview

This guide covers the parameter optimization system implemented for the multi-strategy trading system.

## Features

### TASK-PARAM-1: Parameter Presets ✅

Centralized parameter presets system with Conservative, Moderate, and Aggressive configurations.

**Location**: `config/parameter_presets.yaml`

**Usage**:
```python
from app.services.parameter_preset_manager import get_preset_manager

manager = get_preset_manager()
preset = manager.get_preset("conservative")
momentum_params = manager.get_strategy_params("conservative", "momentum")
```

**Presets Available**:
- **Conservative**: Low risk, fewer signals, higher thresholds
- **Moderate**: Balanced risk/reward, moderate thresholds  
- **Aggressive**: Higher risk, more signals, lower thresholds

### TASK-PARAM-2: Grid Search with Walk-Forward ✅

Exhaustive grid search over parameter combinations, validated using walk-forward analysis.

**Location**: `app/optimization/grid_search_optimizer.py`

**Usage**:
```bash
python scripts/run_grid_search.py --years 10 --max-combinations 1000
```

**Features**:
- Tests all combinations of parameters from grids defined in `parameter_presets.yaml`
- Uses walk-forward validation to prevent overfitting
- Constraints: Max drawdown <= 25%, Min trades >= 20 per strategy
- Objective metric configurable (Sharpe, Sortino, Return, Calmar)

**Output**:
- `grid_search_results_*.csv`: All combinations tested
- `best_grid_search_config_*.json`: Best configuration found
- `grid_search_summary_*.json`: Summary with top 10 configs

### TASK-PARAM-3: Sensible Indicator Ranges ✅

Defined sensible ranges for all technical indicators to prevent invalid parameter combinations.

**Location**: `config/parameter_presets.yaml` → `indicator_ranges`

**Ranges Defined**:
- **RSI**: 20-80 (default: 40)
- **ATR Multiplier**: 1.5-3.0 (default: 2.0)
- **Volume Ratio**: 1.0-5.0 (default: 1.5, must be >1.0)
- **Z-Score**: 0.5-3.0 (default: 1.5)
- **Spread Threshold**: 0.5-3.0 (default: 1.5)
- **Correlation**: 0.4-0.9 (default: 0.65)

**Usage**:
```python
from app.services.parameter_preset_manager import get_preset_manager

manager = get_preset_manager()
rsi_range = manager.get_indicator_range("rsi")
# Returns: {"min": 20, "max": 80, "default": 40, "description": "..."}

is_valid, error = manager.validate_parameter_in_range("rsi", 85)
# Returns: (False, "rsi value 85 above maximum 80")
```

### TASK-MOM-OPT-1: Momentum Auto-Optimization ✅

Automatic monthly recalibration of momentum parameters (RSI, EMA, MACD) using walk-forward validation.

**Location**: `app/optimization/momentum_auto_optimizer.py`

**Features**:
- Monthly recalibration schedule (configurable)
- Walk-forward validation for robustness
- Stability checks to prevent excessive parameter changes
- Performance thresholds to require meaningful improvements
- Optimization history tracking

**Configuration**: `config/parameter_presets.yaml` → `auto_optimization`

**Usage**:
```python
from app.optimization.momentum_auto_optimizer import MomentumAutoOptimizer

optimizer = MomentumAutoOptimizer()

# Check if recalibration needed
if optimizer.should_recalibrate():
    # Optimize parameters
    quotes = [...]  # Load market data
    optimized_params = optimizer.optimize_parameters(
        quotes, start_date, end_date, current_params
    )
    
    # Get optimized config
    config = optimizer.get_optimized_config()
```

**Schedule**: Configured in `auto_optimization.recalibration.frequency`:
- `daily`: Recalibrate daily
- `weekly`: Recalibrate weekly
- `monthly`: Recalibrate monthly (default)
- `quarterly`: Recalibrate quarterly

## Workflow

### 1. Initial Setup

Define parameter grids in `config/parameter_presets.yaml`:
```yaml
grid_search:
  parameter_grids:
    momentum:
      rsi_threshold: [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
      momentum_threshold: [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
      ...
```

### 2. Run Grid Search

```bash
# Full grid search (may take hours)
python scripts/run_grid_search.py --years 10

# Limited combinations for testing
python scripts/run_grid_search.py --years 10 --max-combinations 100
```

### 3. Review Results

Best configuration saved to `docs/GRID_SEARCH_RESULTS/best_grid_search_config_*.json`

### 4. Enable Auto-Optimization

```yaml
auto_optimization:
  enabled: true
  strategy: "momentum"
  recalibration:
    frequency: "monthly"
```

## Best Practices

1. **Start with Presets**: Use conservative preset for initial testing
2. **Grid Search First**: Run grid search before enabling auto-optimization
3. **Review Stability**: Check optimization history for parameter stability
4. **Monitor Performance**: Ensure auto-optimization actually improves results
5. **Respect Constraints**: Never exceed indicator ranges or risk limits

## Integration

The optimization system integrates with:
- **Dashboard**: Uses `ParameterPresetManager` for preset selection
- **Backtesting**: All optimizers use `MultiStrategyBacktester`
- **Walk-Forward**: Grid search uses `WalkForwardValidator`
- **Config System**: All parameters loaded from YAML

