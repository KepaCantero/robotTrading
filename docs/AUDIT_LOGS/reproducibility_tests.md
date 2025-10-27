# Reproducibility Tests

## Purpose

This document enables external auditors to replicate backtest results with 100% accuracy.

## How to Reproduce Results

### 1. Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd algoTrading

# Checkout specific commit
git checkout <commit_sha>

# Install dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should match audit report
```

### 2. Load Same Data

```bash
# Data source: data/historical/AAPL.csv
# Verify hash matches audit report
sha256sum data/historical/AAPL.csv
```

### 3. Configure Identical Settings

```python
# Use exact parameters from config_{name}_report.md
strategy_config = {
    "name": "momentum",
    "rsi_threshold": 40,
    "momentum_threshold": 0.005,
    "stop_loss": 3.0,
    "take_profit": 7.0,
}

backtest_config = {
    "initial_capital": Decimal("100000"),
    "commission_per_trade": Decimal("1.0"),
    "slippage_percentage": Decimal("0.05"),
    "stop_loss_percentage": Decimal("3.0"),
    "take_profit_percentage": Decimal("7.0"),
    "max_position_size": Decimal("0.05"),
}
```

### 4. Execute Backtest

```python
from app.backtesting.engine import SimpleBacktester
from app.backtesting.data_loader import DataLoader

# Load data
loader = DataLoader()
quotes = loader.load_market_data(
    symbol="AAPL",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Run backtest
backtester = SimpleBacktester(backtest_config)
result = backtester.run_backtest(quotes, signals)
```

### 5. Verify Results

**Compare hashes:**

```bash
# Generate hash of metrics
sha256sum docs/BACKTEST_RESULTS/momentum/metrics_moderate.json

# Should match audit report hash
```

**Compare metrics:**

- Total trades must match exactly
- Win rate within 0.01% tolerance
- Sharpe ratio within 0.001 tolerance
- Final capital within 0.01% tolerance

## Tolerances

**Exact Matches Required:**

- Total trades (must be identical)
- Trade entry/exit times (must be identical)
- Signals generated (must be identical)

**Allowable Tolerances:**

- Win rate: <0.01% difference
- Total PnL: <$0.01 difference
- Sharpe ratio: <0.001 difference
- Floating point operations: IEEE 754 compatible

## Cross-Environment Tests

### Local vs AWS

**Differences:**

- Platform: macOS vs Linux
- Python minor version: 3.9.x vs 3.9.y (acceptable if y >= x)
- File paths: relative paths maintained

**Verification:**

- Same commit SHA
- Same dependency versions
- Same data hash
- Same result hash

### Reproducibility Checklist

- [ ] Same commit SHA (`git rev-parse HEAD`)
- [ ] Same Python version
- [ ] Same dependency versions (`pip freeze`)
- [ ] Same data file (verify hash)
- [ ] Same configuration parameters
- [ ] Same result hash (verify metrics.json)
- [ ] Same number of trades
- [ ] Same win rate (within tolerance)
- [ ] Same final capital (within tolerance)

## Troubleshooting

### Results Don't Match

1. **Check Commit SHA:**

   ```bash
   git rev-parse HEAD
   git log --oneline -5
   ```

2. **Check Data File:**

   ```bash
   sha256sum data/historical/AAPL.csv
   ```

3. **Check Configuration:**

   - Verify all parameters match
   - Check for environment variables
   - Verify random seeds (if any)

4. **Check Dependencies:**
   ```bash
   pip freeze > current_requirements.txt
   diff requirements.txt current_requirements.txt
   ```

### Common Issues

**Issue:** Floating point precision  
**Solution:** Use Decimal for all financial calculations (already implemented)

**Issue:** Different platform behavior  
**Solution:** Ensure same Python version and dependencies

**Issue:** Data file differences  
**Solution:** Verify data source and hash before backtest

## Contact

For reproducibility questions, see audit logs and commit history.
