# Backtest Results Summary

## Overview

This table tracks all backtest executions performed on the AlgoTrading system.

| Módulo                      | Configuración | Periodo | Total Trades | Win Rate | Total PnL | Sharpe | Max Drawdown | Capital Final | Fecha | Reporte |
| --------------------------- | ------------- | ------- | ------------ | -------- | --------- | ------ | ------------ | ------------- | ----- | ------- |
| _No backtests executed yet_ |               |         |              |          |           |        |              |               |       |         |

## Adding New Results

Results are automatically added when backtests are executed via the dashboard.

Each entry includes:

- Module name
- Configuration used
- Date range
- Performance metrics
- Link to detailed report

## Legend

- **Módulo**: Trading module used
- **Configuración**: Preset configuration (Conservative/Moderate/Aggressive)
- **Periodo**: Date range of backtest
- **Total Trades**: Number of trades executed
- **Win Rate**: Percentage of profitable trades
- **Total PnL**: Total profit/loss in dollars
- **Sharpe**: Sharpe ratio (risk-adjusted return)
- **Max Drawdown**: Maximum peak-to-trough decline
- **Capital Final**: Final portfolio value
- **Fecha**: Execution timestamp
- **Reporte**: Link to detailed report

## Notes

- Backtest results are automatically saved to `docs/BACKTEST_RESULTS/`
- Each module gets its own subdirectory
- Reports are generated in Markdown format
- Trade logs and metrics are exported as CSV/JSON
