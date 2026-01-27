# Profile Backtesting System - Implementation Plan V2

**Date**: 2026-01-26
**Status**: Updated with Multi-Strategy Analysis
**Key Insight**: ~80% of required infrastructure already exists

---

## Executive Summary - UPDATED

Based on comprehensive analysis including multi-strategy capabilities, **approximately 80% of the required infrastructure is already built**. The system has:

- ✅ Complete InputProfile framework (5 objectives × 4 tiers × 3 risk levels)
- ✅ **MultiStrategyBacktester** with parallel execution
- ✅ **StrategyCapitalAllocation** with dynamic rebalancing
- ✅ Comprehensive backtesting engine with 10 test types
- ✅ Multi-market data services (stocks, forex, crypto)
- ✅ Profile-driven trading orchestrator
- ✅ StrategyFactory with registration system

**Main Gap**: Integration layer between profiles and multi-strategy system + batch processing capability.

---

## 1. Existing Multi-Strategy Implementation ✅

### 1.1 MultiStrategyBacktester Class

**Location**: `/app/backtesting/multi_strategy_engine.py`

**Key Features**:
```python
class MultiStrategyBacktester:
    """
    Already implemented with:
    - Parallel strategy execution
    - Intelligent stock allocation via StrategyStockAllocator
    - Dynamic capital reallocation (30-day rebalancing)
    - Comprehensive results aggregation
    """

    def run_multi_strategy_backtest(
        self,
        quotes: List[Quote],
        strategies: Dict[str, BaseStrategy],
        allocation_manager: MultiStrategyAllocationManager,
        start_date: datetime,
        end_date: datetime
    ) -> MultiStrategyResult:
        """
        Runs multiple strategies simultaneously with allocated capital.

        Returns:
            MultiStrategyResult with:
            - Combined portfolio metrics
            - Individual strategy performance
            - Weighted Sharpe ratio
            - Trade aggregation
        """
```

**Existing Capabilities**:
- ✅ Parallel execution of multiple strategies
- ✅ Capital allocation management (50% momentum, 25% mean reversion, 25% pairs)
- ✅ Dynamic rebalancing based on 30-day performance
- ✅ Stock allocation by statistical classification
- ✅ Performance aggregation across strategies
- ✅ Risk envelope validation

### 1.2 Capital Allocation System

**Location**: `/app/services/multi_strategy_allocation.py`

**StrategyCapitalAllocation Class**:
```python
class StrategyCapitalAllocation:
    """
    Manages capital allocation across strategies.

    Features:
    - Target weights per strategy
    - Min/max weight constraints
    - Performance tracking for rebalancing
    """

    target_allocations: Dict[str, Decimal] = {
        "momentum": Decimal("0.50"),
        "mean_reversion": Decimal("0.25"),
        "pairs_trading": Decimal("0.25")
    }
```

**DynamicPortfolioSelector**:
- Rebalances based on rolling 30-day performance
- Drift threshold-based rebalancing
- Normalizes allocations to 100%

### 1.3 Existing Strategy Portfolio

**Currently Supported Strategies**:
1. **Momentum Strategy** (`/strategies/momentum.py`)
   - RSI, EMA, volume-based signals

2. **Mean Reversion Strategy** (`/strategies/mean_reversion.py`)
   - Z-score based mean reversion

3. **Pairs Trading Strategy** (`/strategies/pairs_trading.py`)
   - Statistical arbitrage

4. **Modular Momentum Strategy** (`/strategies/momentum_modular/`)
   - Most advanced with 6 filters + learning engines
   - 3 presets: conservative, balanced, aggressive

**StrategyFactory**: Dynamic strategy creation and registration

---

## 2. What's Missing - Integration Gaps

### 2.1 Profile ↔ Strategy Bridge ❌ MISSING

**Problem**: No direct connection between:
- Profile configurations (`config/investment_profiles.yaml`)
- Multi-strategy system (`MultiStrategyBacktester`)

**Solution Needed**:
```python
class ProfileStrategyMapper:
    """
    Maps InputProfile configurations to MultiStrategyBacktester.

    Features:
    - Strategy selection based on profile objective
    - Capital allocation based on capital tier
    - Risk parameters based on risk tolerance
    - Investment horizon integration
    """

    def map_profile_to_strategies(
        self,
        profile: InputProfile
    ) -> Dict[str, BaseStrategy]:
        """
        Returns strategy instances configured for the profile.

        Example:
        - MAXIMIZAR_CAPITAL + HIGH + LARGE → momentum + mean_reversion
        - MAXIMIZAR_DIVIDENDOS + LOW + MEDIUM → dividend strategy
        - CAPITAL_PRESERVATION + LOW + SMALL → preservation only
        """

    def get_capital_allocation(
        self,
        profile: InputProfile
    ) -> StrategyCapitalAllocation:
        """
        Returns capital allocation based on capital tier and risk tolerance.

        Example:
        - MICRO tier → Conservative allocation (max 2 strategies)
        - LARGE tier → Aggressive allocation (4+ strategies)
        - BAJO risk → Lower volatility strategies
        - ALTO risk → Higher volatility strategies
        """
```

### 2.2 Batch Processing System ❌ MISSING

**Problem**: No system to:
- Generate all 180 profile combinations
- Run multi-strategy backtest for each profile
- Compare results across profiles
- Identify best strategy per profile

**Solution Needed**:
```python
class ProfileBatchBacktester:
    """
    Orchestrates batch testing of all profile combinations.

    Features:
    - Generate 180 profiles (5×4×3×3)
    - Map each profile to strategy combination
    - Run MultiStrategyBacktester for each profile
    - Aggregate and compare results
    - Store in database for analysis
    """

    def run_all_profiles(
        self,
        parallel: bool = True,
        max_workers: int = 20
    ) -> Dict[str, MultiStrategyResult]:
        """
        Runs full optimization pipeline for all 180 profiles.

        Returns:
            Dictionary mapping profile_id to results
        """
```

### 2.3 Missing Strategy Implementations ❌

**Required for Complete Profile Coverage**:

| Objective | Required Strategy | Status |
|-----------|-------------------|--------|
| `MAXIMIZAR_CAPITAL` | Momentum (✅) | EXISTS |
| `BALANCED_GROWTH` | Momentum + Mean Reversion (✅) | EXISTS |
| `MAXIMIZAR_DIVIDENDOS` | Dividend-Focused | ❌ MISSING |
| `CAPITAL_PRESERVATION` | Preservation Strategy | ❌ MISSING |
| `INCOME_GENERATION` | Income Strategy | ❌ MISSING |

---

## 3. Implementation Architecture - UPDATED

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PROFILE BATCH BACKTESTER                 │
│                  (NEW - Orchestrator Layer)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROFILE STRATEGY MAPPER                    │
│              (NEW - Integration Layer)                       │
│  - Maps profiles to strategy combinations                   │
│  - Configures capital allocation                            │
│  - Sets risk parameters                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MULTI STRATEGY BACKTESTER ✅                    │
│                 (EXISTS - Core Engine)                       │
│  - Parallel strategy execution                              │
│  - Capital allocation management                            │
│  - Performance aggregation                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    STRATEGY PORTFOLIO ✅                     │
│  Momentum │ Mean Reversion │ Pairs Trading │ Modular        │
│   (✅)    │     (✅)        │      (✅)      │   (✅)         │
│                                                          │
│  Dividend │ Preservation │ Income │ (Strategies to add)      │
│   (❌)    │     (❌)       │   (❌)    │                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
1. GENERATE PROFILES
   InputProfileGenerator → 180 profiles

2. MAP TO STRATEGIES
   ProfileStrategyMapper → Strategy combinations per profile

3. EXECUTE BACKTEST
   MultiStrategyBacktester → Results per profile

4. AGGREGATE RESULTS
   ProfileBatchBacktester → Comparison database

5. IDENTIFY BEST
   ResultsAnalyzer → Best strategy per profile
```

---

## 4. Implementation Plan - REVISED

### Phase 1: Integration Layer (1 week) 🔴 HIGH

**Deliverables**:
1. `ProfileStrategyMapper` class
2. Profile → Strategy mapping logic
3. Capital tier → Allocation mapping

**Tasks**:
- [ ] Create `ProfileStrategyMapper` class
- [ ] Implement `map_profile_to_strategies()`
- [ ] Implement `get_capital_allocation()`
- [ ] Read from `config/investment_profiles.yaml`
- [ ] Add strategy parameters per profile
- [ ] Create unit tests

**Files to Create**:
```
app/services/profile_driven_trading/
└── profile_strategy_mapper.py  # NEW
```

**Acceptance Criteria**:
- Can map any InputProfile to strategy combination
- Capital allocation reflects capital tier and risk tolerance
- Strategy parameters match profile requirements
- Unit tests pass

### Phase 2: Batch Orchestrator (1-2 weeks) 🔴 HIGH

**Deliverables**:
1. `ProfileBatchBacktester` class
2. Results database
3. Summary reporting

**Tasks**:
- [ ] Create `ProfileBatchBacktester` class
- [ ] Implement profile generator (180 combinations)
- [ ] Integrate with `MultiStrategyBacktester`
- [ ] Create results database schema
- [ ] Implement parallel execution
- [ ] Add progress tracking
- [ ] Export to CSV/JSON

**Files to Create**:
```
app/backtesting/
├── profile_batch_backtester.py  # NEW
└── profile_results_database.py   # NEW
```

**Acceptance Criteria**:
- Generates all 180 profiles correctly
- Runs multi-strategy backtest for each profile
- Results stored in database
- Parallel execution working (20 workers)
- Export functionality working

### Phase 3: Missing Strategies (2-3 weeks) 🔴 HIGH

**Deliverables**:
1. Dividend-focused strategy
2. Preservation strategy
3. Income strategy
4. Strategy registration

**Tasks**:
- [ ] Implement dividend-focused strategy
- [ ] Implement preservation strategy
- [ ] Implement income strategy
- [ ] Register in StrategyFactory
- [ ] Add to ProfileStrategyMapper
- [ ] Create configuration templates
- [ ] Add tests

**Files to Create**:
```
app/strategies/
├── dividend_focused/     # NEW
│   ├── __init__.py
│   ├── strategy.py
│   ├── filters/
│   └── config.yaml
├── preservation/         # NEW
│   ├── __init__.py
│   ├── strategy.py
│   └── config.yaml
└── income/               # NEW
    ├── __init__.py
    ├── strategy.py
    ├── covered_calls/
    └── config.yaml
```

**Acceptance Criteria**:
- All 5 objectives have corresponding strategies
- Strategies accessible via StrategyFactory
- Tests pass for each strategy
- ProfileStrategyMapper maps correctly

### Phase 4: Bayesian Optimization (1-2 weeks) 🟡 MEDIUM

**Deliverables**:
1. Optuna integration
2. Profile-aware optimization
3. Reduced evaluation count

**Tasks**:
- [ ] Install Optuna dependency
- [ ] Implement Bayesian optimization
- [ ] Profile-specific parameter spaces
- [ ] Multi-objective optimization (Sharpe + drawdown)
- [ ] Parallel execution with pruning
- [ ] Integration with MultiStrategyBacktester

**Files to Modify**:
```
app/strategies/momentum_modular/optimization/
└── hyperparameter_optimizer.py  # ENHANCE
```

**Acceptance Criteria**:
- Reduces evaluations from 50,000 to ~500
- Profile-specific parameter optimization
- Results comparable or better than grid search

### Phase 5: Dashboard (1-2 weeks) 🟢 LOW

**Deliverables**:
1. Streamlit dashboard
2. Profile comparison UI
3. Download functionality

**Tasks**:
- [ ] Create Streamlit dashboard
- [ ] Profile filters (objective, tier, risk)
- [ ] Performance charts
- [ ] Monte Carlo distributions
- [ ] Download config for paper trading
- [ ] Results database integration

**Files to Create**:
```
app/dashboard/
└── profile_optimization_dashboard.py  # NEW
```

**Acceptance Criteria**:
- Dashboard accessible and functional
- Can filter and compare profiles
- Download working for paper trading configs

---

## 5. Code Examples

### 5.1 ProfileStrategyMapper Usage

```python
from app.core.models.input_profile import InputProfile, ObjectivoInversion, CapitalTier, RiskTolerance
from app.services.profile_driven_trading.profile_strategy_mapper import ProfileStrategyMapper

# Create a profile
profile = InputProfile(
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    capital_tier=CapitalTier.LARGE,
    risk_tolerance=RiskTolerance.ALTO,
    investment_horizon_months=60,
    capital_amount=Decimal("300000"),
    tax_residence="spain"
)

# Map to strategies
mapper = ProfileStrategyMapper()
strategies = mapper.map_profile_to_strategies(profile)
# Returns: {
#     "momentum": MomentumStrategy(config=config_aggressive),
#     "mean_reversion": MeanReversionStrategy(config=config_high_risk),
#     "pairs_trading": PairsTradingStrategy(config=config_active)
# }

# Get capital allocation
allocation = mapper.get_capital_allocation(profile)
# Returns: StrategyCapitalAllocation with {
#     "momentum": Decimal("0.50"),
#     "mean_reversion": Decimal("0.30"),
#     "pairs_trading": Decimal("0.20")
# }
```

### 5.2 ProfileBatchBacktester Usage

```python
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# Create batch backtester
batch = ProfileBatchBacktester(
    config_path="config/backtesting/comprehensive_backtest.yaml"
)

# Run all profiles (180 combinations)
results = batch.run_all_profiles(
    parallel=True,
    max_workers=20
)

# Get best strategy for specific profile
best = batch.get_best_strategy(
    objetivo="maximizar_capital",
    capital_tier="large",
    risk_tolerance="alto"
)

# Export results
batch.export_to_csv("results/profile_backtest_results.csv")
batch.export_to_json("results/profile_backtest_results.json")
```

### 5.3 Integration with MultiStrategyBacktester

```python
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

# Use existing MultiStrategyBacktester via ProfileBatchBacktester
class ProfileBatchBacktester:
    def run_single_profile(self, profile: InputProfile):
        # Map profile to strategies
        strategies = self.mapper.map_profile_to_strategies(profile)
        allocation = self.mapper.get_capital_allocation(profile)

        # Create allocation manager
        allocation_manager = MultiStrategyAllocationManager(
            total_capital=profile.capital_amount,
            target_allocations=allocation.target_allocations
        )

        # Use existing MultiStrategyBacktester
        backtester = MultiStrategyBacktester(
            allocation_manager=allocation_manager,
            strategies=strategies,
            config_params=self._get_config_params()
        )

        # Run backtest
        results = backtester.run_multi_strategy_backtest(
            quotes=self.quotes,
            start_date=self.start_date,
            end_date=self.end_date
        )

        return results
```

---

## 6. Database Schema - UPDATED

```sql
-- Profile results with multi-strategy support
CREATE TABLE profile_results (
    -- Primary Key
    profile_id TEXT PRIMARY KEY,

    -- Profile Dimensions
    objetivo TEXT,
    capital_tier TEXT,
    risk_tolerance TEXT,
    investment_horizon INTEGER,
    capital_amount DECIMAL(15,2),

    -- Best Strategy Configuration
    best_strategy_combination TEXT,  -- JSON: ["momentum", "pairs_trading"]
    best_allocation TEXT,            -- JSON: {"momentum": 0.6, "pairs": 0.4}
    best_sharpe REAL,
    best_return_pct REAL,
    best_win_rate REAL,
    best_max_drawdown REAL,

    -- Strategy Breakdown
    strategy_results TEXT,  -- JSON: individual strategy performance

    -- Validation
    in_sample_sharpe REAL,
    out_sample_sharpe REAL,
    monte_carlo_mean_sharpe REAL,
    monte_carlo_p95 REAL,

    -- Status
    optimization_status TEXT,
    ready_for_paper BOOLEAN,

    -- Timestamps
    optimization_started TIMESTAMP,
    optimization_completed TIMESTAMP,
    total_time_hours REAL
);

CREATE TABLE individual_strategy_results (
    backtest_id TEXT PRIMARY KEY,
    profile_id TEXT,
    strategy_name TEXT,
    allocation_weight REAL,
    sharpe REAL,
    total_return REAL,
    win_rate REAL,
    max_drawdown REAL,
    total_trades INTEGER,
    timestamp TIMESTAMP
);
```

---

## 7. File Structure - UPDATED

### Current Structure (What Exists ✅)

```
app/
├── backtesting/
│   ├── multi_strategy_engine.py          ✅ EXISTS
│   ├── comprehensive_backtest_runner.py  ✅ EXISTS
│   ├── engine.py                         ✅ EXISTS
│   ├── cost_calculator.py                ✅ EXISTS
│   └── test_summary.py                   ✅ EXISTS
│
├── services/
│   ├── multi_strategy_allocation.py      ✅ EXISTS
│   ├── profile_driven_trading/           ✅ EXISTS
│   │   └── orchestrator.py               ✅ EXISTS
│   └── strategy_stock_allocator.py       ✅ EXISTS
│
├── strategies/
│   ├── momentum_modular/                 ✅ EXISTS
│   ├── momentum.py                       ✅ EXISTS
│   ├── mean_reversion.py                 ✅ EXISTS
│   ├── pairs_trading.py                  ✅ EXISTS
│   └── factories.py                      ✅ EXISTS
│
└── core/models/
    ├── input_profile.py                  ✅ EXISTS
    └── investment_profile.py             ✅ EXISTS
```

### New Structure (To Be Created ❌)

```
app/
├── backtesting/
│   ├── profile_batch_backtester.py       ❌ NEW
│   ├── profile_results_database.py       ❌ NEW
│   └── profile_strategy_optimizer.py     ❌ NEW (Bayesian)
│
├── services/
│   └── profile_driven_trading/
│       └── profile_strategy_mapper.py    ❌ NEW
│
├── strategies/
│   ├── dividend_focused/                 ❌ NEW
│   ├── preservation/                     ❌ NEW
│   └── income/                           ❌ NEW
│
├── dashboard/
│   └── profile_optimization_dashboard.py ❌ NEW
│
└── config/
    └── backtesting/
        ├── profile_strategy_mapping.yaml  ❌ NEW
        └── optimization_params.yaml       ❌ NEW
```

---

## 8. Updated Timeline Estimate

### Development Time
- **Phase 1 (Integration)**: 1 week
- **Phase 2 (Batch Orchestrator)**: 1-2 weeks
- **Phase 3 (Missing Strategies)**: 2-3 weeks
- **Phase 4 (Bayesian Optimization)**: 1-2 weeks
- **Phase 5 (Dashboard)**: 1-2 weeks

**Total: 6-10 weeks** (reduced from 7-12 weeks due to existing multi-strategy foundation)

### Execution Time (Parallel)
- 180 profiles × 4 hours/profile = 720 hours (single-threaded)
- 720 hours / 20 workers = **36 hours (~1.5 days)** 🎯

---

## 9. Key Advantages of Existing Multi-Strategy

### 9.1 What We DON'T Need to Build

1. ❌ **Parallel execution engine** → Already exists in `MultiStrategyBacktester`
2. ❌ **Capital allocation system** → Already exists in `MultiStrategyAllocationManager`
3. ❌ **Performance aggregation** → Already exists in `_consolidate_results()`
4. ❌ **Stock allocation logic** → Already exists in `StrategyStockAllocator`
5. ❌ **Dynamic rebalancing** → Already exists in `DynamicPortfolioSelector`

### 9.2 What We DO Need to Build

1. ✅ **Profile → Strategy mapping** (Integration layer)
2. ✅ **Batch orchestration** (180 profiles)
3. ✅ **Results database** (Comparison storage)
4. ✅ **Missing strategies** (Dividend, Preservation, Income)
5. ✅ **Dashboard** (Results visualization)

---

## 10. Success Criteria - UPDATED

### Phase 1 Success
- [ ] ProfileStrategyMapper maps all 5 objectives to strategies
- [ ] Capital allocation reflects capital tier (micro/small/medium/large)
- [ ] Risk tolerance affects strategy selection

### Phase 2 Success
- [ ] Can generate all 180 profiles
- [ ] Multi-strategy backtest runs for each profile
- [ ] Results stored with strategy breakdown
- [ ] Export to CSV/JSON working

### Phase 3 Success
- [ ] All 5 objectives have strategies
- [ ] Strategies work with MultiStrategyBacktester
- [ ] Tests pass for all strategies

### Phase 4 Success
- [ ] Bayesian optimization reduces evaluations
- [ ] Profile-specific parameter optimization
- [ ] Results better than grid search

### Overall Success
- [ ] 180 profiles tested with multi-strategy combinations
- [ ] Best strategy identified per profile
- [ ] Results exportable for paper trading
- [ ] Dashboard functional

---

## 11. Next Steps

### Immediate (This Week)
1. Create `ProfileStrategyMapper` class
2. Define strategy mapping rules
3. Create capital allocation rules per tier
4. Write unit tests

### Short-term (Next 2-3 Weeks)
1. Complete batch orchestrator
2. Implement missing strategies
3. Test with small profile subset

### Long-term (Next 1-2 Months)
1. Full 180-profile optimization run
2. Dashboard deployment
3. Paper trading integration

---

## 12. Notes

### Key Insight
The **multi-strategy system is production-ready**. The main work is:
1. Creating the integration layer (ProfileStrategyMapper)
2. Adding batch processing capability
3. Implementing 3 missing strategies

### Architecture Decision
**LEVERAGE existing MultiStrategyBacktester** rather than rebuilding:
- Extends via composition, not modification
- Maintains backward compatibility
- Reduces development time significantly

### Risk Reduction
By using existing multi-strategy infrastructure:
- Lower risk of bugs (battle-tested code)
- Faster time to market
- Easier maintenance

---

**Document Status**: Updated V2 - Multi-Strategy Analysis Complete
**Key Change**: ~70% → ~80% existing infrastructure
**Next Action**: Start Phase 1 (ProfileStrategyMapper)
