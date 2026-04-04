# Dashboard Backtesting Integration - Profitability Dashboard

## Context

Build a unified backtesting dashboard that allows the user to:
1. **Execute backtests** from the dashboard with configurable parameters
2. **Save results** and compare across runs to detect improvements/regressions
3. **View central config parameters** affecting the backtest
4. **Answer the key question**: Is this strategy/multi-strategy + investor profile + time window **profitable**?

## Current State

### Existing Dashboards (3 separate systems - need unification)
1. **Streamlit**: `app/presentation/dashboard/main.py` (~1340 lines) + `advanced_dashboard.py` (~2620 lines)
2. **Production Web**: `app/presentation/dashboard/frontend/` (FastAPI + HTML/JS + Chart.js + WebSocket)
3. **Stubs**: `app/presentation/controllers/dashboard_controller.py`, `portfolio_controller.py`, `strategy_controller.py`

### Central Config
- `app/shared/config/centralized_config.py` (~861 lines) - Facade with Pydantic BaseSettings
- Sub-configs: `trading`, `backtesting`, `database`, `redis`, `api`, `logging`, `monitoring`, `strategies`, etc.
- Strategy configs loaded from `config/strategies/*.yaml`
- Global access: `get_config()`, `get_strategy_config()`, `reload_config()`

### Backtesting Results Storage
- JSON files in `reports/comprehensive_backtest/`
- `app/presentation/dashboard/comprehensive_data_loader.py` - loads JSON results
- File patterns: `comprehensive_backtest_results_*.json`, `grid_search_*.json`, `monte_carlo_*.json`, etc.
- No historical comparison / run tracking system exists yet

### Investor Profiles (5 objectives)
- `app/domain/models/input_profile.py`: `ObjectivoInversion` enum
- `app/domain/models/investment_profile.py`: `CapitalTier`, `InvestmentProfile`
- `app/services/profile_driven_trading/profile_strategy_mapper.py`: maps profile -> strategies
- Config: `config/portfolio/investment_profiles.yaml`, `config/portfolio/profile_batch_backtest.yaml`

## Requirements

### 1. Backtest Execution from Dashboard
- Select: strategy/multi-strategy, investor profile (objective + tier + risk), time window (1mo-5yr)
- Run backtest and display results in real-time
- Show progress indicator during execution
- Support for all 5 investor profiles with special focus on `maximizar_dividendos`

### 2. Result Persistence & Historical Comparison
- Save each backtest run with: timestamp, parameters, results, config snapshot
- Compare current run vs previous runs (improvement/regression indicators)
- Historical trend chart: key metrics over time (Sharpe, return, max drawdown)
- Run metadata: git commit hash, config version, strategy version

### 3. Central Config Viewer
- Display current values of all config parameters affecting backtesting
- Highlight which parameters changed between runs
- Show strategy-specific parameters from `config/strategies/*.yaml`
- Allow parameter override for "what-if" scenarios

### 4. Profitability Verdict
- Clear PASS/FAIL indicator for: strategy + profile + time window combination
- Key metrics: total return, Sharpe, Sortino, max drawdown, win rate, profit factor
- Dividend-specific: DRIP return, yield on cost, dividend income vs capital gains
- Compare against minimum thresholds per profile (from `profile_batch_backtest.yaml`)
- Risk-adjusted profitability: is the return worth the risk taken?

## Technical Constraints
- Extend existing Streamlit dashboards (don't rebuild)
- Use existing `CentralizedConfig` facade
- Store results in SQLite for efficient querying (not just JSON files)
- All code must pass QA gates: black, isort, ruff
- Unit tests for all new services
- Commit after each major component

## Key Files to Modify/Extend
- `app/presentation/dashboard/main.py` - add backtest execution tab
- `app/presentation/dashboard/advanced_dashboard.py` - add comparison tab
- `app/shared/config/centralized_config.py` - add config viewer methods
- `app/presentation/dashboard/comprehensive_data_loader.py` - add historical loading
- New: `app/infrastructure/persistence/backtest_result_store.py` - SQLite persistence
- New: `app/presentation/dashboard/profitability_engine.py` - profitability verdict logic
- New: `app/presentation/dashboard/config_viewer.py` - config parameter display
