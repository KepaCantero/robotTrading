"""
Backtest engine services.

Execution-machinery services used by app.backtesting.engine.BacktestEngine
(the single motor): signal processing, trade execution, PnL/costs, equity
tracking, position management, exit monitoring and performance metrics.

(The former profile-batch family — configuration/profile-generation/
database/reporting services extracted from ProfileBatchBacktester — was
removed together with the parametrization-framework twin.)
"""
