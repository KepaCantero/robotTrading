# Backtesting Framework Rules

## Overview

This document defines the comprehensive backtesting framework for algorithmic trading systems. It covers all types of backtests, data generation methods, optimization approaches, learning engines, and stress tests.

---

## 1. Types of Backtesting

### 1.1 Baseline Backtest
**Purpose**: Establish performance baseline without ML optimization.

**Characteristics**:
- All strategy modules enabled
- No learning engines
- Standard parameter values
- Single-pass execution

**Script**: `scripts/backtesting/simple/run_baseline_backtest.py`

**Configuration**:
```yaml
baseline:
  modules_enabled:
    - ema_filter
    - rsi_filter
    - stoch_rsi_filter
    - momentum_filter
    - volume_filter
    - atr_filter
  learning_engine: null
```

**When to use**:
- Initial strategy evaluation
- Comparison baseline for optimization
- Performance reference point

---

### 1.2 Learning Engines Backtest
**Purpose**: Evaluate individual ML learning engines.

**Supported Engines**:
1. **Supervised Learning** - Traditional ML models (Random Forest, XGBoost)
2. **Deep Learning** - Neural Networks (LSTM, GRU, CNN)
3. **Reinforcement Learning** - RL agents (DQN, PPO, A3C)
4. **Transformer** - Attention-based models (BERT, GPT-style)

**Scripts**:
- `scripts/backtesting/simple/run_deep_learning_backtest.py`
- `scripts/backtesting/simple/run_transformer_backtest.py`

**Configuration**:
```yaml
learning_engines:
  supervised:
    enabled: true
    models:
      - random_forest
      - xgboost
      - lightgbm
    parameters:
      n_estimators: 100
      max_depth: 10

  deep:
    enabled: true
    models:
      - lstm
      - gru
      - cnn
    parameters:
      epochs: 50
      batch_size: 32
      learning_rate: 0.001

  reinforcement:
    enabled: true
    agents:
      - dqn
      - ppo
      - a3c
    parameters:
      episodes: 1000
      gamma: 0.99

  transformer:
    enabled: true
    models:
      - attention
      - temporal_fusion
    parameters:
      num_heads: 8
      num_layers: 6
      d_model: 512
```

**Metrics to Track**:
- Before/after training comparison
- Training convergence
- Overfitting detection
- Feature importance

---

### 1.3 Walk-Forward Optimization
**Purpose**: Time-series cross-validation for strategy parameters.

**Methodology**:
- Divide data into rolling windows
- Train on in-sample period
- Test on out-of-sample period
- Roll forward and repeat

**Configuration**:
```yaml
walk_forward:
  enabled: true
  train_period: 252  # 1 year
  test_period: 63    # 3 months
  step_period: 21    # 1 month
  min_observations: 100
```

**Output**:
- Parameter stability metrics
- Out-of-sample performance
- Regime-specific results

---

### 1.4 Monte Carlo Stress Test
**Purpose**: Evaluate strategy robustness under random market conditions.

**Methodology**:
- Generate N random price paths
- Execute strategy on each path
- Aggregate performance statistics

**Configuration**:
```yaml
monte_carlo:
  enabled: true
  simulations: 1000
  method: geometric_brownian_motion
  parameters:
    drift: 0.05
    volatility: 0.20
    time_steps: 252
  confidence_levels: [0.95, 0.99]
```

**Output**:
- VaR (Value at Risk)
- CVaR (Conditional VaR)
- Worst-case scenarios
- Probability of profit

---

### 1.5 Grid Search Optimization
**Purpose**: Systematic parameter space exploration.

**Script**: `scripts/backtesting/optimization/run_comprehensive_backtest.py` (with `grid_search` type)

**Configuration**:
```yaml
grid_search:
  enabled: true
  parameters:
    ema_short: [5, 10, 15, 20]
    ema_long: [50, 100, 150, 200]
    rsi_period: [14, 21, 28]
    rsi_overbought: [70, 75, 80]
    rsi_oversold: [20, 25, 30]
  optimization_metric: sharpe_ratio
  max_combinations: 1000
```

---

### 1.6 Ablation Study
**Purpose**: Measure individual module contribution.

**Methodology**:
- Test each module independently
- Compare to full baseline
- Identify critical components

**Configuration**:
```yaml
ablation:
  enabled: true
  modules:
    - ema_filter
    - rsi_filter
    - stoch_rsi_filter
    - momentum_filter
    - volume_filter
    - atr_filter
  baseline_modules: all
```

---

### 1.7 Out-of-Sample Validation
**Purpose**: Validate forward performance after optimization.

**Methodology**:
- Train: 70% of data
- Validation: 15% of data
- Test: 15% of data (holdout)

**Configuration**:
```yaml
out_of_sample:
  enabled: true
  train_ratio: 0.70
  val_ratio: 0.15
  test_ratio: 0.15
  min_test_size: 252
```

---

### 1.8 Multi-Strategy Backtest
**Purpose**: Test multiple strategies simultaneously.

**Configuration**:
```yaml
multi_strategy:
  enabled: true
  strategies:
    - momentum_modular
    - mean_reversion_modular
    - pairs_trading_modular
  allocation_method: equal_weight  # or risk_parity, kelly_criterion
  rebalance_frequency: monthly
```

---

### 1.9 Regime Test
**Purpose**: Evaluate performance across market regimes.

**Regimes**:
- Bull market
- Bear market
- Sideways/ranging
- High volatility
- Low volatility

**Configuration**:
```yaml
regime_test:
  enabled: true
  regime_detection_method: hmm  # hidden_markov_model
  min_regime_duration: 20
```

---

### 1.10 Hyperparameter Optimization
**Purpose**: Advanced optimization using Optuna.

**Script**: `scripts/backtesting/optimization/run_full_compliance_test.py` (includes hyperparameter optimization)

**Configuration**:
```yaml
hyperparameter_optimization:
  enabled: true
  optimizer: optuna
  n_trials: 100
  timeout: 3600
  sampler: TPE  # Tree-structured Parzen Estimator
  pruner: median  # Median pruning
  study_name: auto
  direction: maximize
  metric: sharpe_ratio
```

---

## 2. Data Generation Methods

### 2.1 Historical Data Loading
**Source**: CSV files, yfinance, Alpha Vantage

**Configuration**:
```yaml
data:
  source: csv  # or yfinance, alpha_vantage
  symbols: [AAPL, MSFT, GOOGL]
  start_date: 2020-01-01
  end_date: 2024-12-31
  timeframe: 1d  # 1d, 1h, 5m, 1m
```

---

### 2.2 Synthetic Data Generation
**Purpose**: Stress testing, scenario analysis.

**Methods**:
- Geometric Brownian Motion (GBM)
- Heston Model (stochastic volatility)
- Jump Diffusion
- Fractional Brownian Motion (rough volatility)

**Configuration**:
```yaml
synthetic_data:
  method: gbm  # or heston, jump_diffusion, fbm
  parameters:
    drift: 0.05
    volatility: 0.20
    jump_intensity: 0.1
    hurst_parameter: 0.7
  time_steps: 252
```

---

### 2.3 Bootstrapping
**Purpose**: Resampling with replacement.

**Configuration**:
```yaml
bootstrapping:
  enabled: true
  method: block_bootstrap  # or circular_bootstrap
  block_length: 20
  n_samples: 1000
```

---

## 3. Optimization Approaches

### 3.1 Grid Search
- Exhaustive parameter search
- Guaranteed optimal within grid
- Computationally expensive

### 3.2 Random Search
- Random parameter sampling
- More efficient than grid
- Good for high-dimensional spaces

### 3.3 Bayesian Optimization (Optuna)
- Sequential model-based optimization
- Balances exploration/exploitation
- Most efficient for expensive functions

### 3.4 Genetic Algorithms
- Evolutionary approach
- Good for non-convex problems
- Parallelizable

---

## 4. Performance Metrics

### 4.1 Return Metrics
- Total Return
- Annualized Return
- CAGR (Compound Annual Growth Rate)

### 4.2 Risk Metrics
- Sharpe Ratio
- Sortino Ratio
- Max Drawdown
- Volatility
- VaR (Value at Risk)
- CVaR (Conditional VaR)

### 4.3 Trading Metrics
- Win Rate
- Profit Factor
- Average Win/Loss
- Trade Frequency
- Holding Period

### 4.4 Statistical Metrics
- Skewness
- Kurtosis
- Information Ratio
- Beta (market correlation)

---

## 5. Silent Killers Detection

### 5.1 Resource Leaks (PERF-002)
```python
# Garbage collection between backtests
import gc
for profile in profiles:
    result = runner.run_single(profile)
    gc.collect()  # Prevent OOM from ML models
```

### 5.2 Invalid Data (TRD-005)
```python
# Detect NaN and invalid weights
nan_count = sum(1 for v in returns if math.isnan(v))
has_valid_weights = all(0 <= w <= 1 for w in weights)
```

### 5.3 Idempotency Issues
```python
# Use unique run IDs
run_id = uuid.uuid4().hex[:8]
input_id = f"test_{run_id}_{objective}_{risk}_h{horizon}"
```

### 5.4 Overfitting Detection
```python
# Compare in-sample vs out-of-sample
in_sample_sharpe = calculate_sharpe(train_results)
out_sample_sharpe = calculate_sharpe(test_results)
overfitting = in_sample_sharpe - out_sample_sharpe > 0.5
```

---

## 6. Thread Safety Configuration

**CRITICAL**: Configure environment variables BEFORE any imports:

```python
import os

# Thread configuration (prevent mutex.cc deadlocks)
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'

# Disable CUDA to avoid threading issues
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# NOW import libraries
import numpy as np
import pandas as pd
```

---

## 7. Output Structure

```
results/
├── baseline/
│   ├── baseline_results_20240101_120000.json
│   ├── baseline_equity_curve_20240101_120000.csv
│   └── baseline_trades_20240101_120000.csv
├── learning_engines/
│   ├── deep_learning_results.json
│   ├── transformer_results.json
│   └── reinforcement_results.json
├── optimization/
│   ├── grid_search_results.csv
│   └── optuna_study.db
└── reports/
    ├── summary_index.md
    └── performance_comparison.pdf
```

---

## 8. Execution Order (Recommended)

1. **Baseline** - Establish reference
2. **Ablation** - Identify key modules
3. **Grid Search** - Find optimal parameters
4. **Learning Engines** - Test ML approaches
5. **Walk-Forward** - Validate time robustness
6. **Monte Carlo** - Stress test
7. **Out-of-Sample** - Final validation

---

## 9. Validation Checklist

Before deploying to production:

- [ ] All backtests pass without errors
- [ ] No NaN values in results
- [ ] Out-of-sample performance within 20% of in-sample
- [ ] Sharpe ratio > 1.0
- [ ] Max drawdown < 25%
- [ ] Win rate > 50%
- [ ] No memory leaks (OOM check)
- [ ] Results are reproducible (same seed)
- [ ] Unique run IDs for idempotency
- [ ] All metrics documented

---

## 10. Common Pitfalls

1. **Look-ahead bias**: Using future data in signals
2. **Survivorship bias**: Only testing surviving stocks
3. **Overfitting**: Too many parameters relative to data
4. **Ignoring costs**: Not including slippage/commission
5. **Short data period**: Less than 3 years recommended
6. **Single market test**: Test across different market conditions
7. **Unrealistic assumptions**: Perfect fills, no liquidity constraints

---

*Created: 2026-02-07*
*Framework Version: 1.0*
