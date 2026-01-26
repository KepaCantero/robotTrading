# Vulture whitelist file for dead code detection
# Format: variable_name  # optional comment

# Exception handling parameters that are intentionally unused
exc_tb  # Exception traceback in except clauses
exc_val  # Exception value in except clauses

# Database connection records
connection_record
connection_proxy

# Various unused variables in business logic
baseline_period
new_scores
is_oversold
fastapi_app
historical_mean
historical_std
model_data
feature_engineering_config
file_level
invariants

# Additional variables detected by Vulture
backtest_start
backtest_end
strategy_func
target_diversification
max_total_hours
wkhtmltopdf_path
live_sharpe
resolution_note
price_correlation
gamma
input
expected_multiplier
circuit_manager
mock_file
caplog
capsys
tqdm  # Import used conditionally
