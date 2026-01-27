# Profile Backtesting System - Implementation Plan

**Date**: 2026-01-26
**Status**: Analysis Complete - Ready for Implementation

---

## Executive Summary

Based on comprehensive analysis of the existing codebase, **approximately 70% of the required infrastructure is already built**. The system has:

- ✅ Complete InputProfile framework (5 objectives × 4 tiers × 3 risk levels)
- ✅ Comprehensive backtesting engine with 10 test types
- ✅ Multi-market data services (stocks, forex, crypto)
- ✅ Profile-driven trading orchestrator
- ✅ Optimization infrastructure (grid search, walk-forward, Monte Carlo)

**Key Gap**: No batch processing system to test all 180 profile combinations systematically.

---

## 1. Existing Implementation Summary

### 1.1 InputProfile Framework ✅ COMPLETE

**Location**: `/app/core/models/input_profile.py`

**Objectivos de Inversión (5)**:
```python
class ObjectivoInversion(str, Enum):
    MAXIMIZAR_CAPITAL = "maximizar_capital"
    MAXIMIZAR_DIVIDENDOS = "maximizar_dividendos"
    CAPITAL_PRESERVATION = "capital_preservation"
    BALANCED_GROWTH = "balanced_growth"
    INCOME_GENERATION = "income_generation"
```

**Risk Tolerance (3)**:
```python
class RiskTolerance(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
```

**Capital Tiers (4)**:
```python
class CapitalTier(str, Enum):
    MICRO = "micro"    # < €15k
    SMALL = "small"    # €15k - €50k
    MEDIUM = "medium"   # €50k - €250k
    LARGE = "large"    # >= €250k
```

**Investment Horizons**: Supported via `investment_horizon_months` field

**Total Combinations Supported**: 5 × 4 × 3 × 3 = **180 profiles**

### 1.2 Profile Configuration System ✅ COMPLETE

**Location**: `/config/investment_profiles.yaml`

**Existing Configurations**: 20 profiles (5 objectives × 4 tiers)

Each profile configures:
- Risk profile (1-7 scale)
- Leverage factor
- Enabled modules
- Position sizing limits
- Sector allocation limits

**Example Profile Structure**:
```yaml
maximizar_capital:
  small:
    risk_profile: 6
    leverage_factor: 1.2
    enabled_modules:
      - momentum_modular
      - mean_reversion_modular
    max_position_size: 0.15
```

### 1.3 Backtesting Infrastructure ✅ COMPLETE

**ComprehensiveBacktestRunner** - 10 Test Types:
1. Baseline
2. Learning Engines
3. Walk-forward
4. Monte Carlo
5. Transformer Optimization
6. Ablation
7. Grid Search
8. Out-of-Sample
9. Multi-Strategy
10. Regime Test

**Key Features**:
- ✅ Fixed Sharpe ratio calculation (realized P&L)
- ✅ Configurable commission ($0 from YAML)
- ✅ Regime filter implementation
- ✅ Dynamic position sizing
- ✅ Parallel execution support

### 1.4 Strategy Implementation Status

| Strategy | Status | Location |
|----------|--------|----------|
| **ModularMomentum** | ✅ COMPLETE | `/strategies/momentum_modular/` |
| Mean Reversion | ✅ COMPLETE | `/strategies/mean_reversion.py` |
| Pairs Trading | ✅ COMPLETE | `/strategies/pairs_trading.py` |
| Momentum (Legacy) | ✅ COMPLETE | `/strategies/momentum.py` |
| **Dividend-Focused** | ❌ MISSING | - |
| **Preservation** | ❌ MISSING | - |
| **Balanced** | ⚠️ PARTIAL | Covered by momentum_modular preset |
| **Income** | ❌ MISSING | - |

### 1.5 Multi-Asset Support Status

| Asset Class | Data Service | Strategy Support | Status |
|-------------|-------------|------------------|--------|
| **Stocks/ETFs** | ✅ Yahoo Finance, Alpha Vantage | ✅ Multiple strategies | **COMPLETE** |
| **Forex** | ⚠️ Placeholder (OANDA/FXCM) | ❌ No forex strategies | **PARTIAL** |
| **Crypto** | ⚠️ Placeholder (Binance/Coinbase) | ❌ No crypto strategies | **PARTIAL** |

**Multi-Market Orchestrator**: ✅ EXISTS at `/services/multi_market_orchestrator.py`
- Supports STOCKS_US, STOCKS_EU, FOREX, CRYPTO, DIVIDENDS
- Dynamic capital allocation by market
- Tax-optimized for Spanish residents

### 1.6 Data Services ✅ COMPLETE

**Stocks/ETFs**:
- S&P 500 (500+ constituents)
- NASDAQ 100 (100 stocks)
- IBEX 35 (Spanish)
- DOW JONES (30 stocks)
- 20+ years historical data available

**Forex**:
- 12+ currency pairs (EUR/USD, GBP/USD, USD/JPY, etc.)
- 60-minute cache
- Correlation data

**Crypto**:
- Top 10 cryptocurrencies (BTC, ETH, BNB, SOL, etc.)
- 24/7 market support
- 5-minute price cache

### 1.7 Optimization Infrastructure ✅ PARTIAL

**Hyperparameter Optimizer**: ✅ EXISTS
- Grid search implementation
- Random search capability
- Bayesian optimization ⚠️ PLANNED (not implemented)

**Parallel Execution**: ✅ COMPLETE
- ProcessPoolBacktestExecutor
- Monte Carlo simulations
- Grid search combinations

---

## 2. Gap Analysis - What Needs to Be Built

### 2.1 Critical Missing Components

#### 1. **Profile Batch Backtester** ❌ MISSING
**Purpose**: Test all 180 profile combinations systematically

**Required Features**:
- Generate all 180 InputProfile combinations
- Execute full optimization pipeline for each profile
- Compare results across profiles
- Identify best strategy per profile
- Export results for dashboard

**File Structure**:
```
app/backtesting/
└── profile_batch_backtester.py  # NEW
```

**Key Methods**:
```python
class ProfileBatchBacktester:
    def generate_all_profiles() -> List[InputProfile]
    def run_full_optimization(profile: InputProfile) -> OptimizedStrategy
    def identify_best_strategies() -> Dict[str, StrategyConfig]
    def export_results() -> pd.DataFrame
```

#### 2. **Missing Strategy Implementations** ❌ MISSING

**Dividend-Focused Strategy**:
- Objective: `MAXIMIZAR_DIVIDENDOS`
- Requirements: High dividend yield stocks, dividend growth, covered calls
- Location: `/strategies/dividend_focused/`

**Preservation Strategy**:
- Objective: `CAPITAL_PRESERVATION`
- Requirements: Low volatility, defensive sectors, bond allocation
- Location: `/strategies/preservation/`

**Income Strategy**:
- Objective: `INCOME_GENERATION`
- Requirements: REITs, bonds, covered calls, put selling
- Location: `/strategies/income/`

#### 3. **Bayesian Optimization** ⚠️ PLANNED

**Location**: `/strategies/momentum_modular/optimization/hyperparameter_optimizer.py`

**Requirements**:
- Integrate Optuna for Bayesian optimization
- Reduce 50,000 combinations to ~500 evaluations
- Multi-objective optimization (Sharpe + drawdown)

#### 4. **Results Database** ❌ MISSING

**Schema Required**:
```sql
CREATE TABLE profile_results (
    profile_id TEXT PRIMARY KEY,
    objetivo TEXT,
    capital_tier TEXT,
    risk_tolerance TEXT,
    investment_horizon INTEGER,
    best_sharpe REAL,
    best_return_pct REAL,
    best_win_rate REAL,
    best_max_drawdown REAL,
    params_json TEXT,
    in_sample_sharpe REAL,
    out_sample_sharpe REAL,
    monte_carlo_mean_sharpe REAL,
    optimization_status TEXT,
    ready_for_paper BOOLEAN
);
```

**Location**: `/app/backtesting/results_database.py`

#### 5. **Interactive Dashboard** ❌ MISSING

**Technology**: Streamlit or Dash

**Features**:
- Profile comparison filters
- Performance charts
- Monte Carlo distributions
- Download config for paper trading

**Location**: `/app/dashboard/profile_optimization_dashboard.py`

#### 6. **Paper Trading Launcher** ⚠️ PARTIAL

**Existing**: Paper trading infrastructure exists
**Missing**: Automated deployment from optimized configs

**Requirements**:
- Load optimized strategy config
- Deploy to paper trading (Alpaca/IB)
- Monitor performance vs backtest
- Alert on degradation

**Location**: `/app/services/deployment/paper_trading_launcher.py`

---

## 3. Implementation Priority

### Phase 1: Core Batch Processing (1-2 weeks) 🔴 HIGH

**Deliverables**:
1. `ProfileBatchBacktester` class
2. Results database schema and implementation
3. Basic summary reports

**Tasks**:
- [ ] Create `profile_batch_backtester.py`
- [ ] Implement profile combination generator (5×4×3×3 = 180)
- [ ] Integrate with existing `ComprehensiveBacktestRunner`
- [ ] Create results database
- [ ] Implement export to CSV/JSON

**Acceptance Criteria**:
- Can generate all 180 profiles
- Can run baseline backtest for each profile
- Results stored in database
- Can export to CSV

### Phase 2: Missing Strategies (2-3 weeks) 🔴 HIGH

**Deliverables**:
1. Dividend-focused strategy
2. Preservation strategy
3. Income strategy
4. Strategy registration in factory

**Tasks**:
- [ ] Implement dividend-focused strategy
- [ ] Implement preservation strategy
- [ ] Implement income strategy
- [ ] Register in StrategyFactory
- [ ] Create configuration templates
- [ ] Add tests for each strategy

**Acceptance Criteria**:
- All 5 objectives have corresponding strategies
- Strategies accessible via StrategyFactory
- Tests pass for each strategy

### Phase 3: Bayesian Optimization (1-2 weeks) 🟡 MEDIUM

**Deliverables**:
1. Optuna integration
2. Multi-objective optimization
3. Reduced evaluation count

**Tasks**:
- [ ] Install Optuna dependency
- [ ] Implement Bayesian optimization
- [ ] Multi-objective (Sharpe + drawdown)
- [ ] Pruning mechanism for slow trials
- [ ] Parallel execution support

**Acceptance Criteria**:
- Reduces evaluations from 50,000 to ~500
- Maintains or improves results vs grid search
- Parallel execution working

### Phase 4: Multi-Asset Expansion (2-3 weeks) 🟡 MEDIUM

**Deliverables**:
1. Forex-specific strategies
2. Crypto-specific strategies
3. Cross-asset correlation

**Tasks**:
- [ ] Implement forex trading strategies
- [ ] Implement crypto trading strategies
- [ ] Add cross-asset correlation analysis
- [ ] Integrate with multi-market orchestrator
- [ ] Update universe definitions

**Acceptance Criteria**:
- Can backtest forex pairs
- Can backtest crypto assets
- Multi-asset portfolios working

### Phase 5: Dashboard & Deployment (1-2 weeks) 🟢 LOW

**Deliverables**:
1. Interactive Streamlit dashboard
2. Paper trading launcher
3. Monitoring system

**Tasks**:
- [ ] Create Streamlit dashboard
- [ ] Profile comparison UI
- [ ] Performance charts
- [ ] Download functionality
- [ ] Paper trading launcher
- [ ] Performance monitoring

**Acceptance Criteria**:
- Dashboard accessible and functional
- Can deploy to paper trading
- Monitoring alerts working

---

## 4. Technical Specifications

### 4.1 Profile Combination Generator

```python
def generate_all_profiles() -> List[InputProfile]:
    """Generate 180 InputProfile combinations"""
    profiles = []

    for objetivo in ObjectivoInversion:
        for tier in CapitalTier:
            for risk in RiskTolerance:
                for horizon in [12, 60, 240]:  # months
                    profile = InputProfile(
                        objetivo_inversion=objetivo,
                        capital_tier=tier,
                        risk_tolerance=risk,
                        investment_horizon_months=horizon,
                        capital_amount=_get_tier_amount(tier),
                        tax_residence="spain"  # Default
                    )
                    profiles.append(profile)

    return profiles  # 5 × 4 × 3 × 3 = 180 profiles
```

### 4.2 Optimization Pipeline Per Profile

```python
def optimize_profile(profile: InputProfile) -> OptimizedStrategy:
    """
    FASE 1: Grid Search / Bayesian (2-4 hours)
    FASE 2: Walk-Forward (1-2 hours)
    FASE 3: Monte Carlo (30 min)
    FASE 4: Regime Analysis (15 min)
    FASE 5: Out-of-Sample (30 min)

    TOTAL: ~4-8 hours per profile
    """

    # Use existing ComprehensiveBacktestRunner
    runner = ComprehensiveBacktestRunner(config_path)

    # FASE 1: Parameter optimization
    grid_results = runner.run_grid_search_baseline(
        strategy=get_strategy_for_objective(profile.objetivo_inversion),
        param_grid=get_profile_param_grid(profile)
    )

    # FASE 2: Walk-forward validation
    wf_results = runner.run_walk_forward_backtest(
        best_params=grid_results['best_params']
    )

    # FASE 3: Monte Carlo
    mc_results = runner.run_monte_carlo_backtest(
        strategy_config=wf_results['best_config']
    )

    # FASE 4: Regime analysis
    regime_results = runner.run_regime_test_backtest(
        strategy_config=wf_results['best_config']
    )

    # FASE 5: Out-of-sample validation
    oos_results = runner.run_out_of_sample_backtest(
        strategy_config=wf_results['best_config']
    )

    return OptimizedStrategy(
        profile=profile,
        best_params=wf_results['best_params'],
        in_sample_sharpe=grid_results['sharpe'],
        out_sample_sharpe=oos_results['sharpe'],
        monte_carlo_ci=mc_results['confidence_interval'],
        ready_for_paper_trading=oos_results['sharpe'] > 0.5 * grid_results['sharpe']
    )
```

### 4.3 Results Database Schema

```python
from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProfileResult(Base):
    __tablename__ = 'profile_results'

    # Primary Key
    profile_id = Column(String, primary_key=True)

    # Profile Dimensions
    objetivo = Column(String)
    capital_tier = Column(String)
    risk_tolerance = Column(String)
    investment_horizon = Column(Integer)

    # Best Results
    best_sharpe = Column(Float)
    best_return_pct = Column(Float)
    best_win_rate = Column(Float)
    best_max_drawdown = Column(Float)

    # Parameters (JSON)
    params_json = Column(String)

    # Validation
    in_sample_sharpe = Column(Float)
    out_sample_sharpe = Column(Float)
    monte_carlo_mean_sharpe = Column(Float)
    monte_carlo_p95 = Column(Float)

    # Status
    optimization_status = Column(String)
    ready_for_paper = Column(Boolean)

    # Timestamps
    optimization_started = Column(DateTime)
    optimization_completed = Column(DateTime)
    total_time_hours = Column(Float)
```

---

## 5. Configuration Templates

### 5.1 Grid Search Parameters (Partial Implementation)

**Location**: `/config/backtesting/grid_search_params.yaml` (NEW)

```yaml
# Parameters for profile optimization
rsi_filter:
  buy_threshold: [30, 35, 40, 45]
  sell_threshold: [60, 65, 70, 75]
  period: [10, 14, 20]

stoch_rsi:
  oversold: [15, 20, 25]
  overbought: [75, 80, 85]

risk_management:
  stop_loss: [0.05, 0.08, 0.10, 0.12, 0.15]
  take_profit: [0.10, 0.15, 0.20, 0.25]
  max_position_size: [0.10, 0.15, 0.20, 0.25]

strategy:
  combination_mode: ["ALL", "MAJORITY_4", "MAJORITY_5"]
  min_confidence: [0.6, 0.7, 0.8]
```

### 5.2 Asset Universe Configuration (Partial Implementation)

**Location**: `/config/backtesting/asset_universes.yaml` (NEW)

```yaml
# Multi-asset universes for 25-year backtest
etfs_stocks:
  core_etfs:
    - SPY   # S&P 500 (1993)
    - QQQ   # Nasdaq 100 (1999)
    - DIA   # Dow Jones (1998)
    - IWM   # Russell 2000 (2000)
    - EFA   # EAFE International (2001)
    - EEM   # Emerging Markets (2003)
    - AGG   # Bond Aggregate (2003)
    - VTI   # Total Stock Market (2001)
    - GLD   # Gold (2004)
    - TLT   # 20+ Year Treasury (2002)

  sector_etfs:
    - XLF XLE XLK XLV XLI XLY XLP XLU XLRE

  blue_chips:
    - AAPL MSFT JNJ PG KO WMT JPM BAC XOM CVX
    - IBM INTC CSCO DIS MCD

forex:
  major_pairs:
    - EUR/USD GBP/USD USD/JPY USD/CHF
    - AUD/USD USD/CAD

  cross_pairs:
    - EUR/GBP EUR/JPY GBP/JPY

crypto:
  top_coins:
    - BTC-USD ETH-USD BNB-USD SOL-USD
    - ADA-USD XRP-USD DOGE-USD DOT-USD
```

---

## 6. File Structure

### Current Structure (What Exists)

```
app/
├── backtesting/
│   ├── comprehensive_backtest_runner.py  ✅ EXISTS
│   ├── engine.py                         ✅ EXISTS (SimpleBacktester)
│   ├── multi_strategy_engine.py          ✅ EXISTS
│   ├── cost_calculator.py                ✅ EXISTS
│   ├── walk_forward_validator.py         ✅ EXISTS
│   ├── robustness_tester.py              ✅ EXISTS
│   ├── professional_reporter.py          ✅ EXISTS
│   └── test_summary.py                   ✅ EXISTS
│
├── core/models/
│   ├── input_profile.py                  ✅ EXISTS
│   └── investment_profile.py             ✅ EXISTS
│
├── strategies/
│   ├── momentum_modular/                 ✅ EXISTS (Most complete)
│   ├── momentum.py                       ✅ EXISTS
│   ├── mean_reversion.py                 ✅ EXISTS
│   └── pairs_trading.py                  ✅ EXISTS
│
├── services/
│   ├── profile_driven_trading/           ✅ EXISTS (Orchestrator)
│   ├── multi_market_orchestrator.py      ✅ EXISTS
│   ├── forex_data_service.py             ⚠️ PLACEHOLDER
│   └── crypto_data_service.py            ⚠️ PLACEHOLDER
│
└── data/
    └── feeds.py                          ✅ EXISTS
```

### New Structure (To Be Created)

```
app/
├── backtesting/
│   ├── profile_batch_backtester.py       ❌ NEW
│   ├── results_database.py               ❌ NEW
│   ├── strategy_optimizer.py             ⚠️ ENHANCE
│   └── multi_asset_engine.py             ❌ NEW
│
├── strategies/
│   ├── dividend_focused/                 ❌ NEW
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── filters/
│   │   └── config.yaml
│   ├── preservation/                     ❌ NEW
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   └── config.yaml
│   └── income/                           ❌ NEW
│       ├── __init__.py
│       ├── strategy.py
│       ├── covered_calls/
│       └── config.yaml
│
├── dashboard/
│   ├── profile_optimization_dashboard.py ❌ NEW
│   └── production_dashboard.py           ✅ EXISTS
│
├── services/
│   └── deployment/
│       └── paper_trading_launcher.py     ⚠️ ENHANCE
│
└── config/
    └── backtesting/
        ├── grid_search_params.yaml       ❌ NEW
        ├── asset_universes.yaml          ❌ NEW
        └── profile_optimization.yaml     ❌ NEW
```

---

## 7. Dependencies

### Existing Dependencies ✅

- `pydantic` - Data validation
- `sqlalchemy` - Database (if used elsewhere)
- `pandas`, `numpy` - Data manipulation
- `yaml` - Configuration
- `pytest` - Testing

### New Dependencies Required ❌

```toml
# Add to requirements.txt
optuna>=3.0.0      # Bayesian optimization
streamlit>=1.20.0  # Dashboard
plotly>=5.0.0      # Interactive charts
```

---

## 8. Timeline Estimate

### Single-Threaded Execution
- 180 profiles × 6 hours/profile = **1,080 hours (45 days)**

### Parallel Execution (20 cores)
- 45 days / 20 = **2-3 days** 🎯

### Implementation Timeline
- Phase 1 (Core): 1-2 weeks
- Phase 2 (Strategies): 2-3 weeks
- Phase 3 (Optimization): 1-2 weeks
- Phase 4 (Multi-Asset): 2-3 weeks
- Phase 5 (Dashboard): 1-2 weeks

**Total: 7-12 weeks** for complete implementation

---

## 9. Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API rate limits | Medium | Medium | Implement caching, use multiple sources |
| Long optimization time | High | Medium | Parallel execution, early stopping |
| Strategy implementation errors | Low | High | Comprehensive testing |
| Data quality issues | Medium | High | Validation checks, fallback data |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Poor out-of-sample performance | Medium | High | Strict OOS validation criteria |
| Market regime changes | High | Medium | Regime-aware optimization |
| Overfitting to historical data | High | High | Walk-forward validation, regularization |

---

## 10. Success Criteria

### Phase 1 Success
- [ ] Can generate all 180 profiles
- [ ] Baseline backtest runs for all profiles
- [ ] Results stored in database
- [ ] Export to CSV/JSON working

### Phase 2 Success
- [ ] All 5 objectives have strategies
- [ ] Strategies registered in factory
- [ ] Tests passing for all strategies

### Phase 3 Success
- [ ] Bayesian optimization reducing evaluations
- [ ] Results comparable or better than grid search

### Phase 4 Success
- [ ] Forex backtesting working
- [ ] Crypto backtesting working
- [ ] Multi-asset portfolios functional

### Phase 5 Success
- [ ] Dashboard accessible
- [ ] Paper trading deployment automated
- [ ] Monitoring alerts working

### Overall Success
- [ ] 180 profiles fully optimized
- [ ] Results exportable for analysis
- [ ] Paper trading deployment verified
- [ ] Performance monitoring active

---

## 11. Next Steps

### Immediate (This Week)
1. Create `profile_batch_backtester.py` skeleton
2. Implement profile combination generator
3. Set up results database
4. Run baseline tests on small subset

### Short-term (Next 2-4 Weeks)
1. Complete missing strategy implementations
2. Integrate Bayesian optimization
3. Expand multi-asset support
4. Create basic dashboard

### Long-term (Next 2-3 Months)
1. Full 180-profile optimization run
2. Interactive dashboard deployment
3. Paper trading integration
4. Documentation and user guides

---

## 12. Notes

### Already Fixed Issues ✅
- Sharpe ratio now uses realized P&L
- Commission configurable via YAML
- Regime filter implemented
- Dynamic position sizing working

### Known Limitations ⚠️
- Forex/Crypto APIs are placeholders
- Survivorship bias not fully addressed
- Some asset classes (bonds, commodities) not implemented

### Architecture Decisions
- Use existing `ComprehensiveBacktestRunner` as base
- Extend rather than replace where possible
- Maintain compatibility with existing tests
- Parallel execution via ProcessPoolExecutor

---

**Document Status**: Analysis Complete - Ready for Implementation
**Next Review**: After Phase 1 completion
