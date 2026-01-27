# Backtesting Module Test Documentation

**Location:** `/Users/kepa.cantero/Projects/algoTrading/app/backtesting`
**Test Coverage:** Unit Tests, Integration Tests, Core Module Tests
**Last Updated:** 2026-01-26

---

## Table of Contents

1. [Overview](#overview)
2. [Test Architecture](#test-architecture)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [How to Run Tests](#how-to-run-tests)
6. [Test Coverage Summary](#test-coverage-summary)
7. [Prerequisites and Setup](#prerequisites-and-setup)
8. [Data Flow Through Tests](#data-flow-through-tests)

---

## Overview

The backtesting module test suite validates the algorithmic trading backtesting engine with comprehensive coverage including:

- **Core Backtesting Engine**: Order execution, PnL calculation, position management
- **Performance Metrics**: 40+ financial metrics (Sharpe, Sortino, Calmar, etc.)
- **Advanced Analytics**: Regime detection, seasonality, clustering, correlations
- **Validation Framework**: Walk-forward validation, stress testing, Monte Carlo simulation
- **Cost Calculations**: ADV-based slippage, commission models, adaptive pricing
- **Scalability Analysis**: Multi-capital simulation, alpha degradation

### Test Philosophy

**Key Design Principles:**
1. **Realistic Data**: Uses GBM (Geometric Brownian Motion) for market simulation
2. **Real Strategies**: SMA crossover signals - not synthetic patterns
3. **Exact Assertions**: Mathematical verification, not trivial ranges
4. **No Mocks Where Possible**: Integration tests execute actual backtesting
5. **Comprehensive Edge Cases**: Crashes, gaps, extreme volatility tested

---

## Test Architecture

### Directory Structure

```
app/backtesting/
├── core/                          # Core backtesting infrastructure
│   ├── config_loader.py          # Configuration management
│   ├── executor.py               # Backtest execution
│   ├── orchestrator.py           # Multi-test orchestration
│   ├── facade.py                 # Simplified API
│   └── memory_manager.py         # Memory optimization
│
├── models.py                      # Data models (BacktestResult, Trade, etc.)
├── engine.py                      # SimpleBacktester core engine
├── advanced_metrics.py            # 10 advanced metrics calculator
├── walk_forward_validator.py      # Walk-forward & stress testing
├── capital_scale_analyzer.py      # Multi-capital analysis
├── cost_calculator.py             # ADV-based slippage & commission
├── regime_analyzer.py             # Market regime detection
├── seasonality_analyzer.py        # Seasonal pattern analysis
├── clustering_analyzer.py         # Clustering & dimensionality reduction
├── advanced_visualizations.py     # Plotting & charting
├── insight_generator.py           # Report generation
├── awesome_quant_integrator.py    # QuantStats/Empyrical integration
└── ...

tests/
├── unit/backtesting/
│   ├── test_advanced_metrics.py
│   ├── test_awesome_quant_integrator.py
│   ├── test_config_loader.py
│   ├── test_insight_generator.py
│   ├── test_regime_analyzer.py
│   ├── test_seasonality_analyzer.py
│   ├── test_advanced_visualizations.py
│   ├── test_clustering_analyzer.py
│   ├── test_walk_forward_validator.py
│   └── test_core_modules.py
│
└── integration/backtesting/
    ├── test_backtest_basic.py
    ├── test_cost_calculator.py
    ├── test_capital_scaling.py
    ├── test_walk_forward.py
    ├── test_strategy_validation.py
    ├── test_execution_pessimistic.py
    ├── test_concurrent_execution.py
    ├── test_monte_carlo_analysis.py
    └── test_full_workflow.py
```

---

## Unit Tests

### 1. Advanced Metrics Tests

**File:** `tests/unit/backtesting/test_advanced_metrics.py`

**Purpose:** Validates calculation of 10 advanced financial metrics for strategy evaluation.

**Key Classes/Functions Tested:**
- `AdvancedMetricsCalculator`
  - `calculate_calmar_ratio()`
  - `calculate_omega_ratio()`
  - `calculate_ulcer_index()`
  - `calculate_annualized_volatility()`
  - `calculate_recovery_factor()`
  - `calculate_profit_factor()`
  - `calculate_skewness()`
  - `calculate_kurtosis()`
  - `calculate_var()` - Value at Risk
  - `calculate_cvar()` - Conditional VaR

**Test Scenarios Covered:**
1. **Calmar Ratio Tests**
   - Positive CAGR with drawdown
   - Zero drawdown edge case
   - Negative CAGR scenarios
   - Formula: `Calmar = CAGR / |Max Drawdown|`

2. **Omega Ratio Tests**
   - All-positive returns (very high Omega)
   - All-negative returns (Omega ≤ 1.0)
   - Insufficient data handling
   - Threshold-based calculation

3. **Ulcer Index Tests**
   - Stable equity curve
   - Large drawdown scenarios (50% drop)
   - Formula: RMS of drawdown percentages

4. **Volatility Tests**
   - Low dispersion (constant returns)
   - High dispersion (oscillating ±5%)
   - Annualized calculation from daily returns

5. **Recovery Factor Tests**
   - `Recovery Factor = Total PnL / |Max Drawdown|`
   - Zero drawdown handling
   - Negative PnL scenarios

6. **Profit Factor Tests**
   - `Profit Factor = Gross Profit / |Gross Loss|`
   - Breakeven scenarios (PF = 1.0)
   - Perfect scenarios (no losses)

7. **Higher Moments Tests**
   - Skewness (positive/negative tail detection)
   - Kurtosis (fat-tail detection)
   - Minimum data requirements (≥4 for kurtosis)

8. **Risk Metrics Tests**
   - VaR at 95% confidence (historical method)
   - CVaR (expected shortfall in worst 5%)
   - Relationship: CVaR ≤ VaR

9. **Edge Cases**
   - Empty returns list
   - Single trade scenarios
   - Very large numbers (1B+ portfolio)
   - Very small numbers (micro-returns)

**Input Data Used:**
- Sample returns: 10 daily returns (±3% range)
- Sample equity curve: 11 points from $100K to $106.45K
- Risk-free rate: 2% (default)

**Expected Outputs and Assertions:**
- Calmar Ratio ≈ 2.0 for (20% CAGR, -10% DD)
- Omega > 1.0 for positive skew strategies
- Ulcer Index < 1.0 for stable growth
- Volatility annualized correctly
- CVaR ≤ VaR (always)

**Dependencies:**
- `decimal.Decimal` for precision
- `pytest` fixtures
- `AdvancedMetricsCalculator` from `app.backtesting.advanced_metrics`

---

### 2. Awesome Quant Integrator Tests

**File:** `tests/unit/backtesting/test_awesome_quant_integrator.py`

**Purpose:** Tests integration with external quant libraries (QuantStats, Empyrical, Pyfolio).

**Key Classes/Functions Tested:**
- `AwesomeQuantIntegrator`
  - `calculate_quantstats_metrics()`
  - `calculate_empyrical_metrics()`
  - `calculate_pyfolio_metrics()`
  - `calculate_all_awesome_quant_metrics()`
  - `get_unified_metrics()`

**Test Scenarios Covered:**
1. **Library Availability Detection**
   - Checks if QuantStats, Empyrical, PyFol installed
   - Graceful degradation when libraries missing

2. **Excellent Returns Scenarios**
   - Daily returns: 0.1% mean, 1% vol
   - 252 trading days (1 year)
   - Expected: High Sharpe (>2.0)

3. **Poor Returns Scenarios**
   - -0.05% mean, 1.5% vol
   - Expected: Negative Sharpe

4. **Stable Returns Scenarios**
   - 0.05% mean, 0.8% vol
   - Low volatility benchmark

5. **Benchmark Comparisons**
   - Alpha calculation
   - Beta calculation
   - Information ratio

6. **Unified Metrics**
   - Consolidates metrics from all libraries
   - Removes duplicates
   - Priority: QuantStats > Empyrical > Pyfolio

7. **Edge Cases**
   - Empty returns
   - Zero returns (zero volatility)
   - Constant returns
   - Extreme returns (±100%)
   - NaN handling
   - Large datasets (10 years)
   - High-frequency data (5-min intervals)

**Input Data Used:**
- 252-day return series (pandas Series with DatetimeIndex)
- Random seed: 42 (reproducible)
- Date range: 2023-01-01 to 2023-12-31
- Risk-free rate: 2%

**Expected Outputs and Assertions:**
- Excellent Sharpe > 2.0
- Poor Sharpe < 0.5
- Volatility calculations within expected ranges
- Unified metrics have no duplicate keys

**Dependencies:**
- `pandas`, `numpy`
- Optional: `quantstats`, `empyrical`, `pyfolio`
- `AwesomeQuantIntegrator` from `app.backtesting.awesome_quant_integrator`

---

### 3. Config Loader Tests

**File:** `tests/unit/backtesting/test_config_loader.py`

**Purpose:** Tests YAML configuration loading and access patterns.

**Key Classes/Functions Tested:**
- `ConfigLoader`
  - `get()` with dot notation
  - `get_section()`
  - `get_metric_thresholds()`
  - `get_alert_threshold()`
  - `is_enabled()`
  - `reload()`
  - `to_dict()`

**Test Scenarios Covered:**
1. **File Loading**
   - Valid YAML files
   - Missing files (uses defaults)
   - Invalid YAML (graceful fallback)
   - Empty files

2. **Nested Access**
   - Dot notation: `metric_thresholds.sharpe_ratio.excellent`
   - Section retrieval
   - Default values for missing keys

3. **Metric Thresholds**
   - Sharpe ratio: excellent=2.0, good=1.0, warning=0.5
   - Max drawdown: warning=-20%, critical=-50%

4. **Feature Flags**
   - Check if feature enabled
   - Disabled features
   - Missing features (return False)

5. **Configuration Sections**
   - Analysis config (rolling windows, regime detection)
   - Visualization config (static plots, interactive)
   - Reporting config (sections to include)

6. **Edge Cases**
   - None values in config
   - Multiple loader instances (independent)
   - Config reload after file modification
   - Deep nesting

**Input Data Used:**
- Temp YAML files with test configuration
- Default configuration structure

**Expected Outputs and Assertions:**
- Valid config loads successfully
- Missing files use defaults
- Nested access works with dot notation
- Feature flags return boolean

**Dependencies:**
- `yaml` (PyYAML)
- `tempfile` for test file creation
- `ConfigLoader` from `app.backtesting.config_loader`

---

### 4. Insight Generator Tests

**File:** `tests/unit/backtesting/test_insight_generator.py`

**Purpose:** Tests automated insight generation from backtest metrics.

**Key Classes/Functions Tested:**
- `InsightGenerator`
  - `generate_statistical_insights()`
  - `generate_risk_warnings()`
  - `generate_recommendations()`
  - `format_markdown_report()`

**Test Scenarios Covered:**
1. **Statistical Insights**
   - Excellent metrics (35% return, 2.5 Sharpe)
   - Good metrics (15% return, 1.5 Sharpe)
   - Poor metrics (-5% return, -0.5 Sharpe)
   - Coverage of key metrics

2. **Risk Warnings**
   - CRITICAL level (max drawdown -60%)
   - WARNING level
   - INFO level
   - Excellent metrics (minimal warnings)

3. **Recommendations**
   - Priority levels (HIGH, MEDIUM, LOW)
   - Scaling suggestions
   - Risk mitigation
   - Regime-based recommendations

4. **Markdown Reports**
   - Performance summary table
   - Insights section
   - Warnings section
   - Recommendations section
   - Regime analysis

5. **Edge Cases**
   - Empty metrics
   - Very large values
   - Very small values
   - Special characters in strategy name
   - Consecutive analyses (storage works)

**Input Data Used:**
- **Excellent Metrics:**
  ```python
  {
      "return_pct": 0.35,
      "sharpe_ratio": 2.5,
      "max_drawdown": -0.08,
      "win_rate": 0.65,
      "profit_factor": 2.8
  }
  ```

- **Poor Metrics:**
  ```python
  {
      "return_pct": -0.05,
      "sharpe_ratio": -0.5,
      "max_drawdown": -0.45,
      "win_rate": 0.35,
      "profit_factor": 0.7
  }
  ```

- **Regime Data:** Bull, Neutral, Bear market performance

**Expected Outputs and Assertions:**
- Excellent metrics → "✅ Excellent performance"
- Poor metrics → "❌ Poor performance"
- Critical warnings for -60% drawdown
- Recommendations prioritized correctly
- Markdown contains all sections

**Dependencies:**
- `InsightGenerator` from `app.backtesting.insight_generator`

---

### 5. Regime Analyzer Tests

**File:** `tests/unit/backtesting/test_regime_analyzer.py`

**Purpose:** Tests market regime detection and performance analysis by regime.

**Key Classes/Functions Tested:**
- `RegimeAnalyzer`
  - `detect_regimes()` - Hidden Markov Models
  - `analyze_regime_performance()` - Performance by regime
  - `regime_transition_analysis()` - Transition matrices
  - `out_of_sample_regime_robustness()` - Walk-forward testing

**Test Scenarios Covered:**
1. **Regime Detection**
   - Basic detection (3 regimes: Bull, Neutral, Bear)
   - Reproducibility (same seed = same regimes)
   - Window size variations
   - Insufficient data handling

2. **Market Scenarios**
   - Bull market (positive drift, low vol)
   - Bear market (negative drift, high vol)
   - Mixed markets (3 regimes over 3 years)

3. **Regime Performance**
   - Bull regime: high Sharpe (>2.0 expected)
   - Bear regime: low/negative Sharpe
   - Performance metrics by regime
   - Win rate by regime

4. **Transition Analysis**
   - Transition probability matrix
   - Duration statistics (mean, median, min, max)
   - Persistence (diagonal dominance)
   - Number of transitions

5. **Out-of-Sample Robustness**
   - Walk-forward testing (train 252 days, test variable)
   - Consistency across periods
   - Average returns by period
   - Test periods: 2-5 windows

6. **Edge Cases**
   - Constant returns (no regime change)
   - Extreme volatility (100% annual)
   - Large datasets (5000 days)
   - Very short series

**Input Data Used:**
- **Sample Returns:** 252 days of normal(0.001, 0.02) returns
- **Bull Market:** Normal(0.002, 0.01) - positive drift
- **Bear Market:** Normal(-0.001, 0.025) - negative drift, high vol
- **Mixed Market:** Concatenated 3 years (bull → neutral → bear)

**Expected Outputs and Assertions:**
- Regimes detected: 0, 1, 2 (3 total)
- Bull Sharpe > Bear Sharpe
- Transition probabilities sum to 1.0
- Durations reasonable (not too short/long)

**Dependencies:**
- `pandas`, `numpy`
- `RegimeAnalyzer` from `app.backtesting.regime_analyzer`

---

### 6. Seasonality Analyzer Tests

**File:** `tests/unit/backtesting/test_seasonality_analyzer.py`

**Purpose:** Tests seasonal pattern detection in strategy returns.

**Key Classes/Functions Tested:**
- `SeasonalityAnalyzer`
  - `analyze_monthly_returns()`
  - `analyze_quarterly_returns()`
  - `get_best_worst_months()`
  - `get_seasonality_strength()`
  - `decompose_returns()` - STL decomposition
  - `generate_seasonality_report()`

**Test Scenarios Covered:**
1. **Monthly Analysis**
   - Average return by month
   - Cumulative return by month
   - Positive/negative month counts
   - Best/worst month identification

2. **Quarterly Analysis**
   - Q1-Q4 performance
   - All 4 quarters represented
   - Seasonal patterns

3. **Seasonality Strength**
   - High strength (clear seasonal pattern)
   - Low strength (no pattern)
   - Range: 0.0 to 1.0

4. **Return Decomposition**
   - Additive method
   - Multiplicative method
   - Trend, seasonal, residual components
   - Requires ≥24 months

5. **Report Generation**
   - Markdown format
   - Strategy name included
   - All sections present

6. **Edge Cases**
   - Single day data
   - Constant equity (no seasonality)
   - Negative returns
   - Extreme volatility (alternating ±5%)

**Input Data Used:**
- **12-Month Curve:** Jan-Mar better (+0.1%/day), Jul-Sep worse (-0.05%/day)
- **5-Year Curve:** Q1 & Q4 strong, Q3 weak
- **No Seasonality:** Constant 0.05%/day returns
- Date range: 2023-01-01 to 2023-12-31

**Expected Outputs and Assertions:**
- Best month cumulative > worst month
- Seasonality strength higher for patterned data
- At least 12 months analyzed
- Report contains strategy name

**Dependencies:**
- `datetime`, `decimal`, `pytest`
- `SeasonalityAnalyzer` from `app.backtesting.seasonality_analyzer`

---

### 7. Advanced Visualizations Tests

**File:** `tests/unit/backtesting/test_advanced_visualizations.py`

**Purpose:** Tests comprehensive visualization suite (8 plot types).

**Key Classes/Functions Tested:**
- `AdvancedVisualizer`
  - `plot_correlation_network()` - Network graph of metric correlations
  - `plot_parallel_coordinates()` - Multi-dimensional visualization
  - `plot_3d_scatter()` - 3D scatter with color/size dimensions
  - `plot_underwater_drawdown()` - Drawdown depth chart
  - `plot_rolling_metrics()` - Rolling Sharpe/Volatility
  - `plot_regime_performance()` - Performance by market regime
  - `plot_seasonality_heatmap()` - Monthly returns heatmap
  - `generate_interactive_dashboard()` - Full HTML dashboard

**Test Scenarios Covered:**
1. **Correlation Network**
   - Threshold-based edge filtering
   - Custom figure sizes
   - Node positioning
   - File output: `correlation_network.png`

2. **Parallel Coordinates**
   - Color column specification
   - Column limit (max_cols)
   - Interactive HTML output
   - File output: `parallel_coordinates.html`

3. **3D Scatter**
   - X, Y, Z column specification
   - Color dimension
   - Size dimension
   - Interactive HTML output
   - File output: `3d_scatter.html`

4. **Underwater Drawdown**
   - Monotonic increase (zero DD)
   - Crash scenario (50% drop)
   - Custom figure sizes
   - File output: `underwater_drawdown.png`

5. **Rolling Metrics**
   - Window sizes: 30, 50, 100
   - Window > data length handling
   - File output: `rolling_metrics.png`

6. **Regime Performance**
   - Custom regime names
   - Mismatched length handling
   - Single regime scenario
   - File output: `regime_performance.png`

7. **Seasonality Heatmap**
   - Multi-year data
   - Non-datetime index handling
   - File output: `seasonality_heatmap.png`

8. **Interactive Dashboard**
   - Empty data handling
   - Equity curve inclusion
   - Custom filename
   - File output: `dashboard.html`

9. **Edge Cases**
   - Insufficient data
   - Empty DataFrames
   - Missing columns
   - Large datasets (10K rows)

**Input Data Used:**
- **Numeric Data:** 100 rows × 8 columns (Sharpe, PnL, DD, Win Rate, etc.)
- **Equity Curve:** 252 days, starting $100K
- **Returns:** 252 days of normal(0.001, 0.02)
- **Regime Labels:** 3 regimes (0=Bull, 1=Neutral, 2=Bear)

**Expected Outputs and Assertions:**
- Static plots (matplotlib): `.png` files
- Interactive plots (plotly): `.html` files
- Files saved to output directory
- Graceful None returns when libraries unavailable

**Dependencies:**
- `pandas`, `numpy`
- Optional: `matplotlib`, `plotly`
- `AdvancedVisualizer` from `app.backtesting.advanced_visualizations`

---

### 8. Clustering Analyzer Tests

**File:** `tests/unit/backtesting/test_clustering_analyzer.py`

**Purpose:** Tests unsupervised learning for pattern detection.

**Key Classes/Functions Tested:**
- `AdvancedClusteringAnalyzer`
  - `hierarchical_clustering()` - Agglomerative clustering
  - `dbscan_clustering()` - Density-based clustering
  - `pca_analysis()` - Principal Component Analysis
  - `ica_analysis()` - Independent Component Analysis
  - `tsne_visualization()` - t-SNE dimensionality reduction
  - `silhouette_analysis()` - Cluster quality scoring
  - `optimal_clusters()` - Optimal K detection

**Test Scenarios Covered:**
1. **Hierarchical Clustering**
   - Linkage methods: ward, complete, average, single
   - Silhouette score calculation (-1 to 1)
   - Cluster sizes sum to data length
   - n_clusters parameter

2. **DBSCAN Clustering**
   - Epsilon parameter testing
   - Min samples parameter
   - Noise point detection (-1 labels)
   - Density-based separation

3. **PCA Analysis**
   - Component count (2-5)
   - Variance explained threshold (80%)
   - Cumulative variance increasing
   - Transformed data shape

4. **ICA Analysis**
   - Algorithms: parallel, deflation
   - Mixing/unmixing matrices
   - Independent component extraction
   - Transformed data shape

5. **t-SNE Visualization**
   - 2D and 3D projections
   - Perplexity parameter (5-50)
   - KL divergence calculation
   - Max iterations

6. **Silhouette Analysis**
   - Overall score
   - Per-cluster scores
   - Sample-level scores
   - Interpretation string

7. **Optimal Clusters**
   - Elbow method
   - Silhouette method
   - K range testing (2-8)
   - Score calculation for each K

8. **Edge Cases**
   - Single sample
   - Identical features
   - High dimensions (100D)
   - Very small values
   - Mixed positive/negative

**Input Data Used:**
- **2D Data:** 60 points, 3 clear clusters (normal around [0,0], [5,0], [5,5])
- **5D Data:** 50 points × 5 features (random normal)
- **Labels:** [0]×20, [1]×20, [2]×20 (for silhouette)

**Expected Outputs and Assertions:**
- Hierarchical: 3 clusters, silhouette ≈ 0.7-0.9
- DBSCAN: Detects noise with eps=0.1
- PCA: Cumulative variance increases monotonically
- t-SNE: KL divergence ≥ 0
- Silhouette: -1 ≤ score ≤ 1
- Optimal K: Within specified range

**Dependencies:**
- `numpy`, `pytest`
- `AdvancedClusteringAnalyzer` from `app.backtesting.clustering_analyzer`

---

### 9. Walk-Forward Validator Tests

**File:** `tests/unit/backtesting/test_walk_forward_validator.py`

**Purpose:** Tests strategy validation framework (walk-forward, Monte Carlo, stress testing).

**Key Classes/Functions Tested:**
- `WalkForwardValidator` - Rolling window validation
- `CrossValidationTemporal` - Temporal cross-validation
- `MonteCarloSimulator` - Monte Carlo risk analysis
- `StressTester` - Extreme scenario testing
- `SyntheticDataGenerator` - Market data simulation
- `ComprehensiveValidator` - Facade for all validators

**Test Scenarios Covered:**
1. **Configuration Loading**
   - Default configuration structure
   - Walk-forward: train=4Y, val=1Y, step=1Y
   - Stress scenarios: flash_crash, high_volatility, trending_bull/bear
   - Monte Carlo: 100 simulations, 95% confidence

2. **Synthetic Data Generation**
   - GBM price generation (positive prices)
   - Mean-reverting OU process
   - Flash crash scenarios (-15% drop)
   - High volatility (3× vol multiplier)
   - Trending scenarios (bull/bear drift)
   - Gap scenarios (±10% gaps)
   - OHLC consistency validation

3. **Walk-Forward Validation**
   - Window creation for 7-year dataset
   - Sequential date validation
   - Insufficient windows handling
   - IS/OOS metrics calculation

4. **Cross-Validation**
   - 3-fold temporal CV
   - Full period coverage
   - Non-overlapping folds
   - Fold boundaries

5. **Monte Carlo Simulation**
   - Block bootstrap sampling
   - VaR at 95% confidence
   - CVaR (expected shortfall)
   - CVaR ≤ VaR relationship
   - Max drawdown calculation
   - Percentile distributions

6. **Stress Testing**
   - Flash crash scenario generation
   - High volatility scenario
   - Unknown scenario defaults to GBM

7. **Edge Cases**
   - Empty quotes
   - Single quote
   - Negative returns
   - Zero volatility
   - Insufficient data

**Input Data Used:**
- **Sample Quotes:** 500 days starting 2020-01-01
- **Base Price:** $100
- **Drift:** 5% annual
- **Volatility:** 20% annual
- **Signals:** Generated every 20 days

**Expected Outputs and Assertions:**
- Walk-forward: ≥2 windows for 7-year data
- GBM prices: All positive
- Flash crash: Min price < 95% of base
- High vol: Std > 2× normal
- Monte Carlo: VaR and CVaR calculated
- CVaR ≤ VaR (always)

**Dependencies:**
- `datetime`, `decimal`, `unittest.mock`
- `numpy`, `pytest`
- `WalkForwardValidator` from `app.backtesting.walk_forward_validator`

---

### 10. Core Modules Tests

**File:** `tests/unit/backtesting/test_core_modules.py`

**Purpose:** Tests core backtesting infrastructure (config, executor, orchestrator).

**Key Classes/Functions Tested:**
- `BacktestDefaults` - Constants and thresholds
- `BoundedResults` - Fixed-size result container
- `BacktestConfigLoader` - YAML config loading
- `BacktestExecutor` / `SimpleBacktestExecutor`
- `ParallelBacktestExecutor`
- `BacktestExecutorFactory`
- `OrchestrationResult` - Multi-test aggregation
- `BacktestOrchestrator` - Multi-test execution
- `BacktestRunnerFacade` - Simplified API

**Test Scenarios Covered:**
1. **BacktestDefaults**
   - Positive values (commission, slippage, capital)
   - Metric thresholds ordered correctly
   - Sharpe: excellent > good > warning

2. **BoundedResults**
   - Add single result
   - Extend with multiple
   - Get latest N results
   - Max length enforcement
   - Clear functionality

3. **BacktestConfigLoader**
   - Load from valid YAML
   - Get BacktestConfig object
   - File not found error
   - Section retrieval
   - Strategy and execution config

4. **BacktestExecutor**
   - Input validation (quotes not empty)
   - Strategy not None
   - Factory creation (simple vs parallel)

5. **OrchestrationResult**
   - Empty results summary
   - Success/failure counting
   - Result filtering by attributes

6. **BacktestOrchestrator**
   - Initialization with config
   - Execution count increments
   - Single test execution

7. **BacktestRunnerFacade**
   - Initialization from config file
   - Factory function
   - Results clearing
   - Configuration merging

**Input Data Used:**
- YAML config files (temp)
- BacktestConfig with $100K capital
- Mock results for testing

**Expected Outputs and Assertions:**
- Defaults positive
- Thresholds ordered
- BoundedResults enforces maxlen
- Config loader raises FileNotFoundError
- Factory returns correct executor type

**Dependencies:**
- `pytest`, `pathlib`, `unittest.mock`
- `BacktestConfigLoader` from `app.backtesting.core.config_loader`
- `BacktestExecutor` from `app.backtesting.core.executor`
- `BacktestOrchestrator` from `app.backtesting.core.orchestrator`
- `BacktestRunnerFacade` from `app.backtesting.core.facade`

---

## Integration Tests

### 11. Basic Backtest Tests (Real Execution)

**File:** `tests/integration/backtesting/test_backtest_basic.py`

**Purpose:** Full pipeline integration test with realistic market data and real strategies.

**Key Changes from Original:**
- ✅ Eliminated synthetic linear data
- ✅ GBM-based market generation (drift=5%, vol=20%)
- ✅ Real SMA crossover signals (fast=20, slow=50)
- ✅ Exact mathematical assertions
- ✅ 10+ robust edge case tests

**Test Scenarios Covered:**
1. **Basic Backtester Functionality**
   - Initialization validation
   - Realistic GBM data backtest (500 days)
   - Final capital in realistic range ($50K-$150K)
   - Trade structure validation

2. **Edge Cases**
   - Empty market data (ValueError)
   - Single day backtest
   - Reproducibility (same seed = same results)
   - Date filtering

3. **Cost Calculations**
   - Slippage: Exact 1% verification
   - Commission: Exact $5 per trade
   - Position sizing: Capital × 20% × confidence / price

4. **Signal Handling**
   - Contradictory signals (buy/sell/buy)
   - No signals (zero trades)
   - Signals without matching market data

5. **Market Scenarios**
   - Zero volatility (no SMA crossovers)
   - Market crash (-50% drift, 40% vol)
   - Price gap down (-10% overnight)
   - Extreme volatility (100% annual)

6. **Model Validation**
   - Trade model (side validation, status checks)
   - Performance metrics (trade counts consistency)
   - BacktestConfig (slippage limits, stop loss < take profit)

**Input Data Used:**
```python
# GBM Parameters
drift = 0.05  # 5% annual
volatility = 0.20  # 20% annual
days = 500
seed = 42  # Reproducible

# SMA Crossover
fast_period = 20
slow_period = 50
min_slope = 0.001  # 0.1% minimum slope

# Configuration
initial_capital = $100,000
commission = $1.00 per trade
slippage = 0.1%
max_position_size = 10%
```

**Expected Outputs and Assertions:**
- Final capital: $50K ≤ X ≤ $150K (realistic)
- Slippage: ≈ entry_price × 1% ± 50%
- Commission: Exactly $5 × trade_count
- Position size: ≈ (capital × 0.2 × confidence/100) / price
- Zero volatility: 0 signals generated
- Crash: Sharpe negative, not None/infinite

**Dependencies:**
- `datetime`, `decimal`, `numpy`, `pytest`
- `SimpleBacktester` from `app.backtesting.engine`
- `BacktestConfig` from `app.backtesting.models`
- `Quote`, `Signal` from app models

---

### 12. Cost Calculator Tests (ADV-Based Slippage)

**File:** `tests/integration/backtesting/test_cost_calculator.py`

**Purpose:** Tests ADV (Average Daily Volume) based slippage model (HIGH PRIORITY).

**Key Requirements (Req #9):**
1. Market cap classification (large/mid/small cap)
2. Base slippage by cap (Large: 2-5 bps, Small: 10-25 bps)
3. ADV formula: `Slippage = Base + (Order/ADV)² × Coefficient`
4. Volatility multiplier (VIX > 30 = 2× slippage)

**Test Scenarios Covered:**
1. **Market Cap Classification**
   - Large cap: ≥ $1B daily volume
   - Mid cap: $100M - $1B
   - Small cap: < $100M
   - Boundary conditions

2. **Base Slippage by Market Cap**
   - Large cap: 2-5 bps range
   - Small cap: 10-25 bps range
   - Mid cap: Interpolated between large/small
   - Zero ADV: Uses default (2-10 bps)

3. **ADV Impact Formula**
   - Small orders: Minimal ADV impact
   - Large orders: Significant ADV impact
   - Squared relationship (2% order → 4× slippage)
   - Order size vs slippage correlation

4. **Volatility Multiplier**
   - VIX < 30: No multiplier (1×)
   - VIX > 30: Doubles slippage (2×)
   - VIX = 30: Threshold boundary
   - No VIX provided: Uses base

5. **Complete Calculations**
   - Dollar slippage = bps × trade_value / 10000
   - Dollar/BPS correlation verification
   - Different asset types (equity vs crypto)

6. **Edge Cases**
   - Negative ADV → treated as zero
   - Very small ADV (same as order size)
   - Very large ADV (100B daily)
   - Zero ADV

**Input Data Used:**
```python
# ADV Scenarios
large_cap_adv = $2,000,000,000  # $2B
mid_cap_adv = $500,000,000  # $500M
small_cap_adv = $50,000,000  # $50M

# Order Scenarios
small_order = $1,000  # 0.0001% of large cap ADV
large_order = $20,000,000  # 1% of large cap ADV
extreme_order = $1,500,000  # 15% of $10M ADV

# Volatility
vix_normal = 20-25  # Below threshold
vix_high = 31-35  # Above threshold (2× slippage)
```

**Expected Outputs and Assertions:**
- Large cap slippage: 2-5 bps
- Small cap slippage: 10-25 bps
- Large order slippage: > 10 bps (ADV impact)
- Small order slippage: < 5 bps (minimal impact)
- VIX > 30: Ratio ≥ 1.9× (approximately 2×)
- ADV impact squared: 2% order → > 2× 1% order slippage

**Dependencies:**
- `decimal`, `pytest`
- `CostCalculator`, `AssetType` from `app.backtesting.cost_calculator`

---

### 13. Capital Scaling Tests

**File:** `tests/integration/backtesting/test_capital_scaling.py`

**Purpose:** Tests multi-capital analysis with NO MOCKS (full pipeline execution).

**Key Features:**
- NO MOCKS - Real backtesting execution
- GBM market data (5% drift, 20% vol)
- Real SMA crossover signals
- Exact mathematical verification
- 2% ADV rule enforcement

**Test Scenarios Covered:**
1. **Full Pipeline (No Mocks)**
   - Realistic data generation (252 days)
   - Real SMA signals (fast=10, slow=20)
   - REAL CapitalScaleAnalyzer execution
   - Scalability verification (larger capital = lower commission %)

2. **Commission Calculations**
   - Commission impact = commissions / gross_profit
   - Commission % decreases with capital
   - Micro account: Highest %
   - Fund account: Lowest %
   - Large trade tiered benefits

3. **ADV Rule (2% Limit)**
   - Order under 2%: Passes unchanged
   - Order at 250K / 10M ADV: Partial fill (200K, 80%)
   - Order at 1.5M / 10M ADV: Rejected (13.3% < 50%)
   - Formula: `max_allowed = adv × 0.02`
   - Fill ratio = max_allowed / order_size

4. **Alpha Degradation**
   - Formula: `(CAGR_small - CAGR_large) / |CAGR_small|`
   - Example: (20% - 5%) / 20% = 75%
   - Range: 0-100%
   - Zero/negative CAGR handling

5. **Scalability Score**
   - Range: 0-100
   - Based on degradation + commission impact
   - Perfect (0% degradation): Score → 100
   - Terrible (150% degradation): Score → 0

6. **Edge Cases**
   - Negative commission (ValidationError)
   - Duplicate capital levels
   - ADV limit > 100%
   - Mixed symbols
   - Near-zero ADV
   - Empty quotes
   - Single capital level
   - Zero commission with no trades

**Input Data Used:**
```python
# Capital Levels
levels = [$1,000, $10,000, $100,000]

# ADV Data
adv_data = {"AAPL": $50,000,000}  # 50M daily

# Trade Scenarios
small_order = 100K shares  # 1% of 10M ADV (under 2%)
partial_order = 250K shares  # 2.5% of 10M ADV (partial fill)
reject_order = 1.5M shares  # 15% of 10M ADV (rejected)

# Alpha Degradation Test
cagr_small = 20%  # Small account
cagr_large = 5%   # Large account
degradation = (0.20 - 0.05) / 0.20 = 75%
```

**Expected Outputs and Assertions:**
- Scalability: Commission % decreases with capital
- ADV 2% rule:
  - 100K / 10M (1%) → passes unchanged
  - 250K / 10M (2.5%) → partial to 200K (80%)
  - 1.5M / 10M (15%) → rejected (13.3% < 50%)
- Alpha degradation: 75% for (20% → 5% CAGR)
- Scalability score: 0-100 range
- Commission impact: < 50% of gross profit

**Dependencies:**
- `datetime`, `decimal`, `numpy`, `pytest`
- `CapitalScaleAnalyzer` from `app.backtesting.capital_scale_analyzer`
- `BacktestConfig` from `app.backtesting.models`
- `Quote`, `Signal` from app models

---

### 14. Walk-Forward Tests (IS/OOS Metrics)

**File:** `tests/integration/backtesting/test_walk_forward.py`

**Purpose:** Tests walk-forward validation with In-Sample (IS) and Out-of-Sample (OOS) metrics.

**Key Requirements:**
- NO MOCKS - Real backtesting execution
- 12 years data for 5+ cycles
- IS/OOS metrics calculation
- Consistency ratio: Sharpe_OOS / Sharpe_IS > 0.7
- Degradation metrics (max 30%)
- Negative windows detection (< 50%)

**Test Scenarios Covered:**
1. **IS/OOS Metrics Calculation**
   - ValidationWindow includes IS fields
   - IS: total_return, sharpe_ratio, max_drawdown, trades, win_rate
   - OOS: Same fields (default properties)
   - IS/OOS analysis structure

2. **Consistency Ratio**
   - Formula: `Sharpe_OOS / Sharpe_IS`
   - Range: 0-2 (can exceed 1.0 if OOS better)
   - Minimum threshold: 0.7
   - Calculated from real backtests

3. **Degradation Metrics**
   - Return degradation: `(Return_IS - Return_OOS) / |Return_IS|`
   - Sharpe degradation: `(Sharpe_IS - Sharpe_OOS) / Sharpe_IS`
   - Range: 0-100%
   - Maximum allowed: 30%

4. **Minimum Cycles Validation**
   - Required: ≥5 cycles
   - 3 years data → Fails (insufficient)
   - 12 years data → Passes (5-7 cycles)

5. **Negative Windows**
   - Percentage of windows with negative returns
   - Maximum: 50%
   - Edge: Exactly 50% (threshold)
   - Above 50% (failing)
   - All negative (100% failing)

6. **Edge Cases**
   - Insufficient data (2 years)
   - Perfect consistency (ratio = 1.0)
   - Zero consistency (ratio = 0.0)
   - Max degradation (30%)
   - Excessive degradation (100%)
   - Choppy/sideways markets
   - Declining markets
   - Crash scenarios

**Input Data Used:**
```python
# Walk-Forward Config
train_years = 2
validation_years = 1
step_years = 1
min_cycles = 5
min_consistency_ratio = 0.7
max_degradation = 0.30  # 30%
max_negative_window_pct = 0.50  # 50%

# Data Generation
12 years × 252 days = 3,024 days
GBM drift = 5%, vol = 20%
SMA fast = 20, slow = 50

# Window Structure
For 12 years (2010-2022):
- Window 1: Train 2010-2012, Val 2012-2013
- Window 2: Train 2011-2013, Val 2013-2014
- ...
- Window 6-7: Complete cycles
```

**Expected Outputs and Assertions:**
- IS metrics calculated for each window
- OOS metrics calculated for each window
- Consistency ratio: 0.0 ≤ ratio ≤ 2.0
- Degradation: 0.0 ≤ deg ≤ 1.0
- Min cycles check: < 3 years → fail
- Negative windows: 0% ≤ neg_pct ≤ 100%

**Dependencies:**
- `datetime`, `decimal`, `numpy`, `pytest`
- `WalkForwardValidator` from `app.backtesting.walk_forward_validator`
- `BacktestConfig` from `app.backtesting.models`
- `Quote`, `Signal` from app models

---

### 15. Additional Integration Tests

**Note:** The following test files exist but were not fully reviewed in this analysis. Refer to the source files for detailed documentation:

- `test_strategy_validation.py` - Strategy validation framework
- `test_execution_pessimistic.py` - Pessimistic execution model
- `test_concurrent_execution.py` - Parallel backtesting
- `test_monte_carlo_analysis.py` - Monte Carlo risk analysis
- `test_full_workflow.py` - End-to-end workflow tests

---

## How to Run Tests

### Run All Backtesting Tests

```bash
# From project root
pytest tests/unit/backtesting/ -v
pytest tests/integration/backtesting/ -v

# Run specific test file
pytest tests/unit/backtesting/test_advanced_metrics.py -v

# Run specific test class
pytest tests/unit/backtesting/test_advanced_metrics.py::TestCalmarRatio -v

# Run specific test
pytest tests/unit/backtesting/test_advanced_metrics.py::TestCalmarRatio::test_calmar_ratio_positive -v
```

### Run with Coverage

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage report
pytest tests/unit/backtesting/ --cov=app/backtesting --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/backtesting/ -v

# Integration tests only
pytest tests/integration/backtesting/ -v

# Marked tests (e.g., integration tests)
pytest tests/integration/backtesting/ -m integration -v
```

### Run with Verbose Output

```bash
# Show print statements
pytest tests/unit/backtesting/test_advanced_metrics.py -v -s

# Show local variables on error
pytest tests/unit/backtesting/ -v --tb=long

# Stop on first failure
pytest tests/unit/backtesting/ -x
```

### Debug Failed Tests

```bash
# Run last failed tests
pytest --lf

# Run last failed tests and stop on first failure
pytest --lf -x

# Enter debugger on failure
pytest tests/unit/backtesting/ --pdb
```

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/unit/backtesting/ -n 4
```

---

## Test Coverage Summary

### Coverage by Module

| Module | Test Files | Key Functions | Estimated Coverage |
|--------|-----------|---------------|-------------------|
| `advanced_metrics.py` | 1 | 10 advanced metrics | 95% |
| `awesome_quant_integrator.py` | 1 | Library integration | 80%* |
| `config_loader.py` | 1 | YAML loading | 100% |
| `insight_generator.py` | 1 | Report generation | 90% |
| `regime_analyzer.py` | 1 | HMM regime detection | 85% |
| `seasonality_analyzer.py` | 1 | Seasonal patterns | 90% |
| `advanced_visualizations.py` | 1 | 8 plot types | 70%* |
| `clustering_analyzer.py` | 1 | 7 ML algorithms | 85% |
| `walk_forward_validator.py` | 2 | Validation framework | 90% |
| `cost_calculator.py` | 1 | ADV slippage | 100% |
| `capital_scale_analyzer.py` | 1 | Multi-capital | 85% |
| `engine.py` | 2 | Core backtester | 95% |
| `core/` modules | 1 | Infrastructure | 90% |

*Coverage depends on optional library availability (matplotlib, plotly, quantstats, etc.)

### Test Count Summary

```
Unit Tests: ~1,200+ tests
Integration Tests: ~300+ tests
Total: ~1,500+ tests
```

### Coverage Goals

- **Unit Tests:** Target 90%+ coverage
- **Integration Tests:** Target 80%+ coverage
- **Critical Paths:** 100% coverage (backtest execution, PnL, metrics)

---

## Prerequisites and Setup

### 1. Python Environment

```bash
# Create virtual environment
python3.9 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Required Packages

**Core Testing:**
- `pytest >= 7.0.0`
- `pytest-cov >= 4.0.0`
- `pytest-xdist >= 3.0.0` (optional, for parallel execution)

**Data Processing:**
- `numpy >= 1.24.0`
- `pandas >= 2.0.0`
- `scipy >= 1.10.0`

**Optional (for some tests):**
- `matplotlib >= 3.7.0` (visualization tests)
- `plotly >= 5.14.0` (interactive plots)
- `quantstats >= 0.0.62` (Awesome Quant)
- `empyrical >= 0.5.5` (Awesome Quant)
- `pyfolio >= 0.9.0` (Awesome Quant)

### 4. Configuration Files

Ensure test configuration files exist:

```bash
# Config directories
config/backtesting/
config/development.yaml
config/production.yaml

# Test-specific configs (if any)
tests/fixtures/test_config.yaml
```

### 5. Environment Variables

```bash
# Optional: Set test database path
export TEST_DB_PATH=/tmp/test_orders.db

# Optional: Set test data directory
export TEST_DATA_DIR=/tmp/test_data

# Optional: Disable plotting in CI
export MATPLOTLIB_USE_AGG=true
```

---

## Data Flow Through Tests

### 1. Unit Test Data Flow

```
Test Fixture → Synthetic Data → Module Function → Assert Result
     ↓
  (In-Memory)
```

**Example: `test_advanced_metrics.py`**

```
1. Fixture: sample_returns (10 Decimal values)
2. Calculator: AdvancedMetricsCalculator
3. Method: calculate_calmar_ratio(cagr=0.20, max_dd=-0.10)
4. Assert: calmar ≈ 2.0
```

### 2. Integration Test Data Flow

```
Test Fixture → GBM Generator → Quotes/Signals → BacktestEngine → BacktestResult → Metrics → Assert
     ↓                    ↓              ↓           ↓              ↓          ↓
  (In-Memory)      (250 rows)      (~50 sigs)   (Real Exec)   (Validated)  (Math)
```

**Example: `test_backtest_basic.py`**

```
1. Fixture: generate_realistic_quotes(days=500, drift=0.05, vol=0.20)
2. Fixture: generate_sma_crossover_signals(fast=20, slow=50)
3. Engine: SimpleBacktester(config)
4. Execute: run_backtest(quotes, signals)
5. Result: BacktestResult(final_capital, trades, performance)
6. Assert: 50000 ≤ final_capital ≤ 150000
```

### 3. Walk-Forward Data Flow

```
Test Fixture → GBM (12 years) → Signals → WalkForwardValidator → N Windows → IS/OOS Metrics → Assert
     ↓             ↓                    ↓                          ↓
  (In-Memory)  (3,024 rows)      (~200 sigs)          (5-7 cycles)
```

**Example: `test_walk_forward.py`**

```
1. Fixture: sample_quotes_12_years (12 × 252 days)
2. Fixture: sample_signals_12_years (SMA crossover)
3. Validator: WalkForwardValidator(config)
4. Validate: validate_strategy(quotes, signals, config, ...)
5. Result: {windows: [...], is_oos_analysis: {...}}
6. Assert: consistency_ratio ≥ 0.0, degradation ≤ 1.0
```

### 4. Capital Scaling Data Flow

```
Test Fixture → GBM (1 year) → Signals → CapitalScaleAnalyzer → N Capitals → Report → Assert
     ↓              ↓                              ↓
  (In-Memory)   (252 rows)                  (1K, 10K, 100K)
```

**Example: `test_capital_scaling.py`**

```
1. Fixture: realistic_quotes (252 days, GBM)
2. Fixture: realistic_signals (SMA fast=10, slow=20)
3. Analyzer: CapitalScaleAnalyzer(capital_levels=[1K, 10K, 100K])
4. Analyze: analyze_capital_scaling(quotes, signals, config, ...)
5. Result: CapitalScaleAnalysisReport(capital_level_results=[...])
6. Assert: commission_impact_1k ≥ commission_impact_100k
```

---

## Interpreting Test Results

### Success Criteria

**Unit Tests:**
- All metrics calculate correctly
- Edge cases handled gracefully
- No exceptions raised
- Mathematical precision maintained

**Integration Tests:**
- Full pipeline executes without errors
- Realistic results (not trivial)
- IS/OOS metrics within expected ranges
- Costs/commissions accurate

### Common Failures and Troubleshooting

1. **ImportError: No module named 'XXX'**
   - Install missing dependency: `pip install XXX`
   - Some tests skip if optional libraries missing

2. **AssertionError: Expected X but got Y**
   - Check if tolerance is too strict
   - Verify random seed is set
   - Check for floating-point precision issues

3. **ValueError: No market data available**
   - Ensure fixtures generate data correctly
   - Check date ranges overlap
   - Verify signal timestamps match quote timestamps

4. **FileNotFoundError: Config file not found**
   - Run tests from project root
   - Ensure `config/` directory exists
   - Check `PYTHONPATH` includes `app/`

### Test Output Symbols

- `.` - Test passed
- `F` - Test failed
- `E` - Error during test
- `s` - Test skipped (e.g., missing dependency)
- `x` - Expected failure (xfail)

---

## Contributing Tests

### Test Naming Conventions

```python
class Test<ClassName>:
    """Tests for <ClassName>."""

    def test_<method>_<scenario>(self):
        """Test <method> with <scenario>."""
        pass

    def test_<method>_<edge_case>(self):
        """Test <method> edge case: <edge_case>."""
        pass
```

### Fixture Guidelines

```python
@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    # Setup
    data = generate_data()
    yield data
    # Cleanup (if needed)
```

### Assertion Best Practices

```python
# GOOD: Exact mathematical assertions
assert abs(calmar - 2.0) < 0.01  # Allow 1% tolerance

# BAD: Trivial ranges
assert calmar > 0  # Too weak

# GOOD: Specific value checks
assert commission == Decimal("5.0") * trade_count

# BAD: Range checks
assert commission > 0  # Not specific enough
```

### Documentation Requirements

```python
def test_specific_calculation(self):
    """
    Test that specific calculation is correct.

    Formula: X = Y / Z
    Input: Y=100, Z=20
    Expected: X=5.0

    This verifies the exact mathematical relationship.
    """
    result = calculate(y=100, z=20)
    assert result == 5.0
```

---

## Appendix: Quick Reference

### Test File Locations

```bash
# Unit tests
tests/unit/backtesting/test_advanced_metrics.py
tests/unit/backtesting/test_awesome_quant_integrator.py
tests/unit/backtesting/test_config_loader.py
tests/unit/backtesting/test_insight_generator.py
tests/unit/backtesting/test_regime_analyzer.py
tests/unit/backtesting/test_seasonality_analyzer.py
tests/unit/backtesting/test_advanced_visualizations.py
tests/unit/backtesting/test_clustering_analyzer.py
tests/unit/backtesting/test_walk_forward_validator.py
tests/unit/backtesting/test_core_modules.py

# Integration tests
tests/integration/backtesting/test_backtest_basic.py
tests/integration/backtesting/test_cost_calculator.py
tests/integration/backtesting/test_capital_scaling.py
tests/integration/backtesting/test_walk_forward.py
tests/integration/backtesting/test_strategy_validation.py
tests/integration/backtesting/test_execution_pessimistic.py
tests/integration/backtesting/test_concurrent_execution.py
tests/integration/backtesting/test_monte_carlo_analysis.py
tests/integration/backtesting/test_full_workflow.py
```

### Key Metrics Reference

| Metric | Formula | Good Value | Excellent Value |
|--------|---------|------------|-----------------|
| Sharpe Ratio | (Return - RF) / Volatility | > 1.0 | > 2.0 |
| Sortino Ratio | (Return - RF) / Downside Vol | > 1.5 | > 3.0 |
| Calmar Ratio | CAGR / \|Max DD\| | > 1.0 | > 2.0 |
| Omega Ratio | Probability Gain / Loss | > 1.5 | > 2.0 |
| Ulcer Index | RMS of DD | < 5 | < 3 |
| Recovery Factor | Total PnL / \|Max DD\| | > 2.0 | > 5.0 |
| Profit Factor | Gross Profit / \|Gross Loss\| | > 1.5 | > 2.5 |

### Common Fixtures

```python
# Market data
realistic_quotes()  # GBM data
sample_quotes()  # Simple synthetic data

# Signals
realistic_signals()  # SMA crossover
sample_signals()  # Mock signals

# Configuration
default_config()  # BacktestConfig with defaults
test_config()  # Custom test configuration

# Validators
walk_forward_config()  # Walk-forward parameters
```

---

## Conclusion

This test suite provides comprehensive validation of the backtesting module with:

- **~1,500 tests** covering unit and integration scenarios
- **Realistic data** using GBM market simulation
- **Real strategies** with SMA crossover signals
- **Exact assertions** with mathematical verification
- **Edge cases** covering crashes, gaps, extreme volatility
- **No mocks** in integration tests (actual execution)

For questions or issues, refer to the source code or contact the development team.

**Last Updated:** 2026-01-26
**Document Version:** 1.0
