# Comprehensive Services Matrix - AlgoTrading System

**Analysis Date**: 2026-02-07
**Scope**: Complete analysis of all services in `app/services/` and `app/data/`

---

## Executive Summary

| Category | Total Services | Integrated in comprehensive_5day_test.py | Integrated in run_backtesting_with_real_data.py |
|----------|----------------|---------------------------------------------|-----------------------------------------------|
| **Data Services** | 4 | 1 (CSV/yfinance) | 1 (Alpha Vantage) |
| **Market Universe** | 2 | 0 | 1 |
| **Profile Services** | 1 | 0 (hardcoded) | 1 ✅ |
| **Strategy Allocation** | 1 | 0 | 1 ✅ |
| **Trading Orchestrator** | 1 | 0 | 1 ✅ |
| **Risk Management** | 15+ | 0 | Partial |
| **Portfolio Management** | 10+ | 0 | 0 |
| **Reporting** | 5+ | 1 (JSON) | 1 ✅ |
| **Alerting** | 6 | 0 | 0 |
| **Validation** | 8+ | 0 | Partial |
| **Execution** | 10+ | 0 | 0 |
| **TOTAL** | **80+** | **~2%** | **~15%** |

---

## 1. DATA SERVICES

### 1.1 RealMarketDataFetcher ✅ EXISTS
**File**: `app/data/real_market_data.py`

```python
class RealMarketDataFetcher:
    """Fetch real market data from Alpha Vantage API."""

    async def fetch_sp500_top_n(n, start_date, end_date, use_cache)
    async def fetch_multiple_symbols(symbols, start_date, end_date, use_cache)
    def get_cache_stats()
    def clear_cache(symbol=None)
```

**Features**:
- Alpha Vantage API integration
- Rate limiting (5 calls/minute free tier)
- Data caching to disk
- Real S&P 500 top 50 stocks
- Progress logging

**Integration Status**:
- ❌ `comprehensive_5day_test.py`: NOT integrated (uses hardcoded symbols)
- ✅ `run_backtesting_with_real_data.py`: FULLY INTEGRATED

**S&P 500 Top 50 Available**:
AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, GOOG, BRK.B, LLY, AVGO, JPM, V, XOM, UNH, MA, JNJ, HD, PG, COST, MRK, CVX, ABBV, PEP, BAC, KO, ADBE, WMT, CRM, MCD, NFLX, AMD, CSCO, ORCL, CMCSA, ACN, INTC, DIS, QCOM, TXN, IBM, AMGN, BA, NKE, DHR, HON, CAT, GE, MDT, NOW, ISRG, PLD

---

### 1.2 DataLoader ✅ EXISTS (Used in comprehensive test)
**File**: `app/backtesting/data_loader.py`

```python
class DataLoader:
    def load_market_data(symbol, start_date, end_date, source="csv")
```

**Data Sources**:
- `csv`: Load from `data/historical/{symbol}.csv`
- `yfinance`: Download from Yahoo Finance API

**Integration Status**:
- ✅ `comprehensive_5day_test.py`: INTEGRATED (source="yfinance")
- ❌ `run_backtesting_with_real_data.py`: NOT used (uses RealMarketDataFetcher)

**Available CSV Data** (51 files):
AAPL, ABT, ABBV, ADBE, AMD, AMGN, AMZN, AVGO, BAC, BRK.B, CAT, CMCSA, COP, COST, CRM, CSCO, CVX, DHR, DIS, DUK, EOG, EQIX, GOOGL, GOOG, GS, HD, HON, INTC, JNJ, JPM, KO, LLNY, LMT, LOGI, MAIN, META, MSFT, MT, NEE, NET, NFLX, NKE, NVDA, ORCL, PEP, PFE, PG, PLD, PSA, QCOM, RE, SLB, SHOP, SNOW, SO, SRE, TMO, TRV, TSLA, TXN, UNH, UPS, V, VLO, VZ, WFC, WELL, WMT, WUBA, XOM

---

### 1.3 Feeds ✅ EXISTS
**File**: `app/data/feeds.py`

**Purpose**: Market data feed handlers (not analyzed in detail)

---

### 1.4 Synthetic Data ✅ EXISTS
**Directory**: `app/services/synthetic_data/`

**Purpose**: Generate synthetic market data for testing

---

## 2. MARKET UNIVERSE SERVICES

### 2.1 MarketUniverseLoader ✅ EXISTS
**File**: `app/services/market_universe_loader.py`

```python
class MarketUniverseLoader:
    """AAA Grade Market Universe Loader (OPTIMIZED)."""

    async def get_sp500_universe()
    async def get_nasdaq100_universe()
    async def get_ibex35_universe()
    async def get_crypto_universe(top_n=20)
    async def download_universe_data(tickers, period, interval)
```

**Features**:
- S&P 500, NASDAQ 100, IBEX 35 constituents
- Top cryptocurrencies by market cap
- Parallel data downloading with rate limiting
- Liquidity and volatility filtering
- Automatic retry with exponential backoff
- Circuit breaker pattern
- LRU cache

**Integration Status**:
- ❌ `comprehensive_5day_test.py`: NOT integrated
- ❌ `run_backtesting_with_real_data.py`: NOT integrated (uses hardcoded SP500_TOP_50)

---

### 2.2 MarketUniverseOrchestrator ✅ EXISTS
**File**: `app/services/market_universe_orchestrator.py`

**Purpose**: Orchestrates market universe loading and asset selection

**Integration Status**:
- ❌ NOT integrated in either test script

---

### 2.3 AssetIdentificationService ✅ EXISTS
**File**: `app/services/asset_identification.py`

```python
class AssetIdentificationService:
    """Service for identifying and ranking liquid assets."""

    async def identify_liquid_assets(asset_class, limit=20)
    async def get_top_liquid_assets(asset_class, limit=20)
    async def filter_assets(asset_class, filter_criteria)
    async def get_asset_by_symbol(symbol, asset_class=None)
```

**Asset Classes**:
- EQUITY (S&P 500 stocks)
- CRYPTO (top 20)
- FOREX (major pairs)
- COMMODITY (gold, silver, oil, etc.)

**Integration Status**:
- ❌ NOT integrated in either test script

---

## 3. PROFILE SERVICES

### 3.1 ProfileGenerator ✅ EXISTS
**Directory**: `app/services/profile_generator/`

```python
class ProfileGenerator:
    """Generate investment profiles from user input."""
```

**Integration Status**:
- ❌ `comprehensive_5day_test.py`: NOT used (hardcoded profiles)
- ✅ `run_backtesting_with_real_data.py`: INTEGRATED (via orchestrator)

---

### 3.2 InputProfile ✅ EXISTS (Model)
**File**: `app/core/models/input_profile.py`

```python
@dataclass
class InputProfile:
    input_id: str
    capital_initial: Decimal
    objetivo_inversion: ObjectivoInversion
    risk_tolerance: RiskTolerance
    investment_horizon: int  # months
    tax_residence: TaxResidence
```

**Objectives**: MAXIMIZAR_CAPITAL, MAXIMIZAR_DIVIDENDOS, CAPITAL_PRESERVATION, BALANCED_GROWTH
**Risk Levels**: BAJO, MEDIO, ALTO
**Horizons**: 12, 24, 36, 60 months

**Integration Status**:
- ✅ `comprehensive_5day_test.py`: USED (60 combinations generated)
- ✅ `run_backtesting_with_real_data.py`: USED

---

## 4. STRATEGY ALLOCATION SERVICES

### 4.1 StrategyStockAllocator ✅ EXISTS
**File**: `app/services/strategy_stock_allocator.py`

```python
class StrategyStockAllocator:
    """Professional, verifiable, and auditable stock allocation system."""

    def filter_stocks(historical_data)
    def calculate_wcm_scores(filtered)
    def allocate(historical_data, total_capital, strategy_allocations)
```

**Features**:
- Data validation (filter_stocks)
- Statistical classification (Hurst, ADF, KPSS, Half-Life)
- Scoring engines (Momentum, Mean Reversion, Pairs Trading)
- Weighted Scoring Model (WSM)
- ERC / Risk Parity optimization

**Scoring Models**:
- **Momentum**: High Hurst (>0.5), ADF non-stationary, positive trend
- **Mean Reversion**: Low Hurst (<0.5), ADF stationary, negative autocorr
- **Pairs Trading**: Cointegration test, half-life calculation

**Integration Status**:
- ❌ `comprehensive_5day_test.py`: NOT integrated
- ✅ `run_backtesting_with_real_data.py`: INTEGRATED (Stage 3)

---

### 4.2 StrategyStockAllocator (Alternative) ✅ EXISTS
**Directory**: `app/services/strategy_stock_allocation/`

**Purpose**: Alternative implementation (not analyzed)

---

## 5. TRADING ORCHESTRATOR SERVICES

### 5.1 ProfileDrivenTradingOrchestrator ✅ EXISTS
**File**: `app/services/profile_driven_trading/orchestrator.py`

```python
class ProfileDrivenTradingOrchestrator:
    """Main orchestrator for profile-driven trading lifecycle."""

    async def execute_trading_lifecycle(input_profile)
    async def stage_1_generate_profile(input_profile)
    async def stage_2_select_universe()
    async def stage_3_allocate_capital(universe)
    async def stage_4_generate_signals(allocation)
    async def stage_5_optimize_taxes(allocation)
    async def stage_6_validate_risk(allocation)
    async def stage_7_backtest_validate()
    async def stage_8_execute_trades()
```

**8-Stage Pipeline**:
1. ✅ Profile Generation
2. ✅ Universe Selection (MarketUniverseOrchestrator)
3. ✅ Capital Allocation (StrategyStockAllocator)
4. ✅ Signal Generation
5. ✅ Tax Optimization
6. ✅ Risk Validation
7. ✅ Backtest Validation
8. ✅ Trade Execution

**Integration Status**:
- ❌ `comprehensive_5day_test.py`: NOT integrated (uses ComprehensiveBacktestRunner)
- ✅ `run_backtesting_with_real_data.py`: FULLY INTEGRATED

---

## 6. RISK MANAGEMENT SERVICES

### 6.1 Risk Scaling Services ✅ EXISTS
**Directory**: `app/services/risk_scaling/`

- `risk_scaling_orchestrator.py` - Main orchestrator
- `risk_scaling_monitor.py` - Monitor risk metrics
- `risk_adjustment_calculator.py` - Calculate adjustments
- `sharpe_ratio_monitor.py` - Sharpe ratio tracking
- `volatility_monitor.py` - Volatility tracking
- `drawdown_monitor.py` - Drawdown tracking
- `limit_adjuster.py` - Position limits

**Integration Status**: ❌ NOT integrated in either test

---

### 6.2 Other Risk Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `RiskModelsNarang` | `risk_models_narang.py` | Risk models | ❌ |
| `PortfolioRiskManager` | `portfolio_risk_manager.py` | Portfolio risk | ❌ |
| `AdvancedRiskManager` | `advanced_risk_manager.py` | Advanced risk | ❌ |
| `CircuitBreakerManager` | `circuit_breaker_manager.py` | Circuit breakers | ❌ |
| `CapitalViabilityGate` | `capital_viability_gate.py` | Capital viability | ❌ |
| `VARPositionLimiter` | `var_position_limiter.py` | VaR limits | ❌ |
| `ExpensiveModuleGate` | `expensive_module_gate.py` | Module gate | ❌ |

---

## 7. PORTFOLIO MANAGEMENT SERVICES

### 7.1 Portfolio Construction ✅ EXISTS
**Directory**: `app/services/portfolio_construction/`

- `rebalancing_engine.py`
- `allocation_recommender.py`

### 7.2 Other Portfolio Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `PortfolioBuilder` | `portfolio_builder.py` | Build portfolios | ❌ |
| `PortfolioRebalancer` | `portfolio_rebalancer.py` | Rebalance | ❌ |
| `MultiStrategyAllocation` | `multi_strategy_allocation.py` | Multi-strategy | ❌ |
| `DynamicCapitalReallocation` | `dynamic_capital_reallocation.py` | Dynamic reallocation | ❌ |
| `PositionSizingEngine` | `position_sizing_engine.py` | Position sizing | ❌ |
| `PortfolioConstructor` | `portfolio_constructor/portfolio_constructor.py` | Constructor | ❌ |

---

## 8. REPORTING SERVICES

### 8.1 Reporting Generator ✅ EXISTS
**Directory**: `app/services/reporting_generator/`

- `reporting_generator.py` - Main generator
- `html_template_engine.py` - HTML templates
- `quantstats_integrator.py` - QuantStats integration
- `pyfolio_integrator.py` - Pyfolio integration
- `visualization_generator.py` - Charts/visualizations
- `delivery_manager.py` - Report delivery

**Integration Status**:
- ⚠️ `comprehensive_5day_test.py`: JSON only (HTML disabled)
- ✅ `run_backtesting_with_real_data.py`: JSON report generation

---

### 8.2 Other Reporting Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `ReportingOrchestrator` | `reporting/reporting_orchestrator.py` | Orchestrator | ❌ |
| `PerformanceTracker` | `performance_tracker.py` | Track performance | ❌ |

---

## 9. ALERTING SERVICES

### 9.1 Alerting System ✅ EXISTS
**Directory**: `app/services/alerting_system/`

- `alerting_orchestrator.py` - Main orchestrator
- `alert_manager.py` - Alert management
- `alert_rule_engine.py` - Rule engine
- `rule_templates.py` - Rule templates
- `metrics_driven_alerter.py` - Metrics-based alerts
- `models.py` - Data models

**Integration Status**: ❌ NOT integrated in either test

---

## 10. VALIDATION SERVICES

### 10.1 Data Validation ✅ EXISTS
**File**: `app/services/data_validation_service.py`

```python
class DataValidationService:
    """Comprehensive data validation service."""

    def validate_market_data(data)
    def detect_gaps(data)
    def detect_outliers(data)
```

**Integration Status**: ❌ NOT integrated

---

### 10.2 Other Validation Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `DeploymentValidator` | `deployment_validator.py` | Deployment validation | ❌ |
| `CapacityFadeValidator` | `capacity_fade_validation/capacity_fade_validator.py` | Capacity fade | ❌ |
| `CountryDiversificationValidator` | `country_diversification_validator.py` | Country diversification | ❌ |
| `SectorDiversificationValidator` | `sector_diversification_validator.py` | Sector diversification | ❌ |
| `ProfitabilityValidationService` | `profitability_validation_service.py` | Profitability validation | ❌ |

---

## 11. EXECUTION SERVICES

### 11.1 Smart Order Routing ✅ EXISTS
**Directory**: `app/services/smart_order_routing/`

- `smart_order_router.py` - Main router
- `order_splitting_optimizer.py` - Order splitting
- `execution_cost_monitor.py` - Cost monitoring
- `broker_negotiation_engine.py` - Broker negotiation
- `market_impact_estimator.py` - Market impact

**Integration Status**: ❌ NOT integrated

---

### 11.2 Live Trading ✅ EXISTS
**Directory**: `app/services/live_trading/`

- `alert_to_trade_mapper.py` - Alert to trade mapping
- Broker adapters for Alpaca, etc.

**Integration Status**: ❌ NOT integrated

---

### 11.3 Other Execution Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `ExecutionAlgorithms` | `execution_algorithms.py` | Execution algos | ❌ |
| `SignalExecutionEngine` | `signal_execution_engine.py` | Signal execution | ❌ |
| `TradingErrorHandler` | `trading_error_handler.py` | Error handling | ❌ |
| `PaperTradingService` | `paper_trading_service.py` | Paper trading | ❌ |

---

## 12. ANALYSIS SERVICES

### 12.1 Technical Analysis ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `MomentumAnalysis` | `momentum_analysis.py` | Momentum analysis | ❌ |
| `MomentumAnalysisOptimized` | `momentum_analysis_optimized.py` | Optimized momentum | ❌ |
| `HurstExponentAnalyzer` | `hurst_exponent_analyzer.py` | Hurst exponent | ✅ (via StrategyStockAllocator) |
| `HalfLifeCalculator` | `half_life_calculator.py` | Half-life calc | ✅ (via StrategyStockAllocator) |
| `StationarityAnalyzer` | `stationarity_analyzer.py` | Stationarity tests | ✅ (via StrategyStockAllocator) |
| `MultiTimeframeService` | `multi_timeframe_service.py` | Multi-timeframe | ❌ |

---

### 12.2 Signal Services ✅ EXISTS

| Service | File | Purpose | Integration |
|---------|------|---------|-------------|
| `SignalScorer` | `signal_scorer.py` | Signal scoring | ❌ |
| `SignalScoringEngine` | `signal_scoring_engine.py` | Scoring engine | ❌ |
| `SignalEvaluationEngine` | `signal_evaluation_engine.py` | Evaluation | ❌ |
| `ValueSignalEnhancer` | `value_signal_enhancer.py` | Value enhancement | ❌ |

---

## 13. BACKTESTING SERVICES

### 13.1 ComprehensiveBacktestRunner ✅ EXISTS
**File**: `app/backtesting/comprehensive_backtest_runner.py`

```python
class ComprehensiveBacktestRunner:
    """Comprehensive backtesting runner with all framework types."""

    def run_baseline_backtest()
    def run_learning_engines_backtest()
    def run_walk_forward_backtest()
    def run_monte_carlo_backtest()
    def run_grid_search()
    def run_ablation_backtest()
    def run_transformer_optimization_backtest()
    def run_multi_strategy_backtest()
    # etc.
```

**Integration Status**:
- ✅ `comprehensive_5day_test.py`: FULLY INTEGRATED (all 10 types)
- ❌ `run_backtesting_with_real_data.py`: NOT used (uses orchestrator)

---

### 13.2 ProfileBatchBacktester ✅ EXISTS
**File**: `app/backtesting/profile_batch_backtester.py`

**Purpose**: Batch testing for multiple profiles

**Integration Status**: ❌ NOT integrated in either test

---

## 14. LEARNING ENGINES

### 14.1 Reinforcement Learning ✅ EXISTS
**File**: `app/strategies/momentum_modular/learning/reinforcement_learning_engine.py`

**Integration Status**:
- ⚠️ `comprehensive_5day_test.py`: ENABLED but may have NumPy 2.x issues
- ✅ `run_backtesting_with_real_data.py`: Available (configurable)

---

## 15. CONFIGURATION SERVICES

### 15.1 Centralized Config ✅ EXISTS
**Directory**: `app/core/centralized_config.py`

**Features**:
- `StockAllocationSettings` - Strategy allocation config
- `BacktestSettings` - Backtest config
- YAML-based configuration

**Integration Status**:
- ✅ `comprehensive_5day_test.py`: Partially used
- ✅ `run_backtesting_with_real_data.py`: Partially used

---

## 16. DATA AVAILABLE FOR TESTING

### 16.1 CSV Files in `data/historical/` (51 files)

**Technology**: AAPL, ADBE, AMD, AMGN, AMZN, AVGO, BRK.B, CAT, CMCSA, CRM, CSCO, CVX, DIS, GOOGL, GOOG, GS, HD, HON, INTC, IBM, JNJ, JPM, KO, LLY, LOGI, LMT, MAIN, META, MSFT, MT, NEE, NET, NFLX, NKE, NVDA, ORCL, PEP, PFE, PG, PLD, PSA, QCOM, RE, SHOP, SLB, SNOW, SO, SRE, TMO, TRV, TSLA, TXN, UNH, UPS, V, VLO, VZ, WFC, WELL, WMT, WUBA, XOM

**Analysis**:
- 51 CSV files available
- Covers Tech, Finance, Healthcare, Energy, Consumer, Industrial sectors
- Most have ~2500 records (about 10 years of daily data)

---

## 17. COMPARISON: TEST SCRIPTS

### comprehensive_5day_test.py

| Feature | Status | Notes |
|---------|--------|-------|
| **Data Source** | ⚠️ yfinance | 10 symbols hardcoded |
| **Profile Generation** | ❌ Hardcoded | 60 combinations |
| **Stock Selection** | ❌ Hardcoded | No StrategyStockAllocator |
| **Orchestrator** | ❌ Not used | Uses ComprehensiveBacktestRunner |
| **Backtest Types** | ✅ 10/10 | All framework types |
| **Reporting** | ⚠️ JSON | HTML disabled |
| **Risk Management** | ❌ None | No risk gates |
| **Tax Optimization** | ❌ None | Not integrated |

**Total Services Used**: ~2% of available

---

### run_backtesting_with_real_data.py

| Feature | Status | Notes |
|---------|--------|-------|
| **Data Source** | ✅ Alpha Vantage | Real S&P 500 data |
| **Profile Generation** | ✅ ProfileGenerator | Full integration |
| **Stock Selection** | ✅ Hardcoded SP500_TOP_50 | Not MarketUniverseLoader |
| **Orchestrator** | ✅ Full 8-stage | Complete pipeline |
| **Allocation** | ✅ StrategyStockAllocator | Stage 3 |
| **Signals** | ✅ Signal generation | Stage 4 |
| **Tax** | ✅ TaxOptimizer | Stage 5 |
| **Risk** | ✅ RiskGates | Stage 6 |
| **Backtest** | ✅ BacktestValidator | Stage 7 |
| **Execution** | ✅ TradingBridge | Stage 8 |
| **Reporting** | ✅ JSON | Full report |

**Total Services Used**: ~15% of available

---

## 18. MISSING INTEGRATIONS

### High Priority (Core Features)

| Service | Benefit | Effort |
|---------|---------|--------|
| **MarketUniverseLoader** | Dynamic symbol selection | Medium |
| **AssetIdentificationService** | Asset ranking by class | Low |
| **Risk Scaling Services** | Real-time risk monitoring | High |
| **Smart Order Routing** | Optimal execution | High |
| **Alerting System** | Real-time alerts | Medium |
| **PortfolioRebalancer** | Dynamic rebalancing | Medium |
| **DataValidationService** | Data quality checks | Low |

### Medium Priority (Enhancement Features)

| Service | Benefit | Effort |
|---------|---------|--------|
| **MultiTimeframeService** | Multi-timeframe analysis | Medium |
| **SignalScoringEngine** | Advanced signal scoring | Medium |
| **ReportingGenerator** | HTML reports | Low |
| **Validation Services** | Comprehensive validation | Medium |

### Low Priority (Optional Features)

| Service | Benefit | Effort |
|---------|---------|--------|
| **PaperTradingService** | Simulated trading | Low |
| **Synthetic Data** | Stress testing | Low |
| **Compliance Services** | Regulatory compliance | High |

---

## 19. RECOMMENDATIONS

### For `comprehensive_5day_test.py`:

1. **Replace hardcoded symbols** with `MarketUniverseLoader`
2. **Integrate `StrategyStockAllocator`** for scientific stock selection
3. **Add `RiskGates`** for position limits
4. **Enable HTML reporting** via `ReportingGenerator`
5. **Add `DataValidationService`** for data quality

### For `run_backtesting_with_real_data.py`:

1. **Replace hardcoded SP500_TOP_50** with `MarketUniverseLoader.get_sp500_universe()`
2. **Add `MarketUniverseOrchestrator`** for multi-asset support
3. **Enable `ReportingGenerator`** for HTML reports
4. **Add risk monitoring** services

### New Test Script Suggestion:

**`test_full_pipeline.py`** - Complete integration test combining:
- `RealMarketDataFetcher` for data
- `ProfileDrivenTradingOrchestrator` for orchestration
- All 8 stages with real services
- Full reporting (JSON + HTML)
- Risk gates and validation
- Alert system integration

---

## 20. SERVICE DEPENDENCY GRAPH

```
Data Layer:
├── DataLoader (CSV/yfinance) ───────┐
├── RealMarketDataFetcher (Alpha Vantage) ─┤
└── SyntheticDataGenerator                │
                                         │
Market Universe Layer:                   │
├── MarketUniverseLoader ────────────────┤
├── MarketUniverseOrchestrator ──────────┤
└── AssetIdentificationService ───────────┘
                                         │
Profile Layer:                           │
└── ProfileGenerator ─────────────────────┤
                                         │
Strategy Layer:                           │
└── StrategyStockAllocator ───────────────┤
                                         │
Orchestration Layer:                     │
└── ProfileDrivenTradingOrchestrator ────┤
                                         │
Backtest Layer:                          │
└── ComprehensiveBacktestRunner ──────────┤
                                         │
Risk Layer:                              │
├── RiskScalingOrchestrator ──────────────┤
├── PortfolioRiskManager ─────────────────┤
└── [Other Risk Services] ─────────────────┘
                                         │
Execution Layer:                         │
├── SmartOrderRouter ──────────────────────┤
├── SignalExecutionEngine ─────────────────┤
└── TradingBridge ─────────────────────────┘
                                         │
Reporting Layer:                          │
├── ReportingGenerator ────────────────────┤
└── VisualizationGenerator ─────────────────┘
```

---

*Analysis Date: 2026-02-07*
*Total Services Analyzed: 80+*
*Integration Coverage: ~2% (comprehensive) / ~15% (real data)*
