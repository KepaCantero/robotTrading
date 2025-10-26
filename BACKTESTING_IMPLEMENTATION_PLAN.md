# Backtesting Infrastructure Implementation Plan

## ✅ Current Progress: 2/6 Components Complete

### 1. ✅ Data Loader (`app/backtesting/data_loader.py`)
- CSV file support from `data/historical/`
- Yahoo Finance integration
- Fallback mechanism
- Cache support

### 2. ✅ Metrics Calculator (`app/backtesting/metrics.py`)
- CAGR calculation
- Sharpe ratio
- Sortino ratio
- Max drawdown
- Win rate
- Profit factor
- Trade statistics

### 3. Requirements Updated
- Added: pandas, numpy, yfinance, matplotlib, scipy, rich

## 📋 Remaining Tasks

### 3. Backtesting Runner (`app/backtesting/runner.py`)
- Implement BacktestRunner class
- Accept strategy, date range, initial balance, data source
- Execute step-by-step simulation
- Track positions, PnL, drawdown

### 4. CLI Entry Point
- Create `scripts/run_backtest.sh`
- Add CLI commands to Makefile
- Arguments: --strategy, --start, --end, --capital

### 5. Visualization
- Generate equity curve PNG
- Create reports in `reports/backtesting/`

### 6. Tests
- Unit tests in `tests/backtesting/`
- Target: 95% coverage
- Integration tests

## 🎯 Expected Output

```bash
# Command
python -m app.backtesting.runner --strategy momentum --start 2024-01-01 --end 2025-01-01 --capital 100000

# Output
🚀 Backtesting MomentumStrategy
Periodo: 2024-01-01 → 2025-01-01
Capital inicial: 100,000.00
Beneficio neto: 17,300.50 (+17.3%)
Sharpe: 1.84 | Sortino: 2.30 | MaxDD: -6.2%
Report guardado en reports/backtesting/results_momentum.json
✅ Ejecución completada sin errores
```

## 📊 Current Status
- Files Created: 2
- Remaining: 4 major components
- Estimated Time: Significant implementation ahead

