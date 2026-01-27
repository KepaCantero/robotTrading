# Priority Recommendations - Quick Reference Guide

## Overview
This guide shows how to use the three critical improvements for robust backtesting:
1. **Multiple Testing Correction** - Prevent false discoveries
2. **Survivorship Bias Adjustment** - Get realistic performance estimates
3. **Expectancy Calculation** - Measure true profitability per trade

---

## 1. Multiple Testing Correction

### Why You Need It
When testing multiple parameter combinations, some will appear profitable by pure chance. For example:
- Testing 20 parameters at 95% confidence
- Probability of at least one false positive: 1 - (0.95)^20 = 64%
- **Solution**: Apply Bonferroni correction → 4.75% adjusted confidence

### Basic Usage

```python
from app.backtesting.data_split import MultipleTestingCorrector

# Initialize with number of tests
corrector = MultipleTestingCorrector(num_tests=20, base_confidence=0.95)

# Apply Bonferroni correction
adjusted_confidence = corrector.bonferroni_correction()
print(f"Adjusted confidence: {adjusted_confidence:.4f}")  # 0.0475

# Alternative: Benjamini-Hochberg (less conservative)
p_values = [0.01, 0.03, 0.05, 0.10, 0.20]
significant = corrector.benjamini_hochberg_correction(p_values)
```

### Integration with Parameter Optimization

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

runner = ComprehensiveBacktestRunner("config/backtesting/config.yaml")

# Define parameter grid
param_grid = [
    {"buy_threshold": 0.7, "sell_threshold": 0.3},
    {"buy_threshold": 0.8, "sell_threshold": 0.2},
    # ... more combinations
]

# Optimize with automatic multiple testing correction
results = runner.optimize_with_validation(
    param_grid=param_grid,
    strategy_class=ModularMomentumStrategy,
)

# Check if results are statistically valid
if results['oos_valid']:
    print(f"Best parameters: {results['best_params']}")
    print(f"Adjusted confidence: {results['adjusted_confidence']:.4f}")
else:
    print("WARNING: Parameters overfit! Do not use.")
```

---

## 2. Survivorship Bias Adjustment

### Why You Need It
Backtesting only currently active companies inflates returns:
- **Example**: S&P 500 average excludes bankrupt companies
- **Typical bias**: 10-30% overestimation of returns
- **Solution**: Include delisted, acquired, and failed companies

### Basic Usage

```python
from app.backtesting.universe_manager import UniverseManager
from datetime import datetime

manager = UniverseManager()

# Get universe for your backtesting period
symbols = manager.get_universe(
    start_date=datetime(2010, 1, 1),
    end_date=datetime(2024, 12, 31),
    include_delisted=True,      # Include bankrupt companies
    include_spun_off=True,      # Include acquired companies
    include_penny_stocks=False, # Exclude penny stock periods
)

print(f"Universe size: {len(symbols)} symbols")

# Filter by market cap
large_caps = manager.filter_by_market_cap(
    symbols=symbols,
    min_market_cap=Decimal("200"),  # $200B+
)

# Get sector breakdown
sectors = manager.get_sector_diversification(symbols)
for sector, tickers in sectors.items():
    print(f"{sector}: {len(tickers)} symbols")
```

### Quantify Survivorship Bias

```python
# Calculate bias impact
bias_metrics = manager.calculate_survivorship_bias(
    survivor_returns=[0.01, 0.02, 0.015, 0.025, 0.03],  # Your backtest returns
    full_universe_returns=[0.005, 0.01, 0.008, -0.02, 0.012],  # With failed companies
)

if bias_metrics['bias_detected']:
    print(f"WARNING: Survivorship bias detected!")
    print(f"Survivor CAGR: {bias_metrics['survivor_cagr']:.2%}")
    print(f"Full Universe CAGR: {bias_metrics['full_universe_cagr']:.2%}")
    print(f"Bias: {bias_metrics['bias_percentage']:.1f}% overestimation")
```

### What's Included

**Delisted Companies** (bankruptcies, failures):
- ENRN - Enron Corporation (2001)
- LEH - Lehman Brothers (2008)
- WCOM - WorldCom (2002)
- KM - Kmart (2002)
- TWXQ - Toys R Us (2017)
- THMRQ - Theranos (2018)

**Acquired Companies** (no longer independent):
- YHOO - Yahoo (2017)
- MW - Monsanto (2018)
- FT - First Republic Bank (2023)

**Penny Stock Periods** (during crises):
- GE, F, C, AIG during 2008-2009

---

## 3. Expectancy Calculation

### Why You Need It
Win rate alone doesn't tell the full story:
- **Strategy A**: 60% win rate, $100 avg win, $400 avg loss → **-$100 per trade**
- **Strategy B**: 40% win rate, $500 avg win, $300 avg loss → **+$20 per trade**

**Expectancy reveals the truth**: Strategy B is profitable despite lower win rate!

### Formula

```
Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
```

### Basic Usage

```python
from app.backtesting.metrics import calculate_expectancy

# From your backtest results
expectancy = calculate_expectancy(winning_trades, losing_trades)

print(f"Expectancy: ${expectancy:.2f} per trade")

if expectancy > 0:
    print("Strategy has positive expectancy - PROFITABLE")
else:
    print("Strategy has negative expectancy - UNPROFITABLE")
```

### With Confidence Intervals

```python
from app.backtesting.metrics import calculate_expectancy_with_confidence

# Calculate expectancy with 95% confidence interval
result = calculate_expectancy_with_confidence(
    winning_trades,
    losing_trades,
    confidence_level=0.95,
)

print(f"Expectancy: ${result['expectancy']:.2f} per trade")
print(f"95% CI: [${result['lower_bound']:.2f}, ${result['upper_bound']:.2f}]")
print(f"Std Error: ${result['std_error']:.2f}")
```

### Automatic Integration

Expectancy is automatically calculated in all backtests:

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

runner = ComprehensiveBacktestRunner("config/backtesting/config.yaml")
results = runner.run_baseline_backtest()

# Access expectancy from results
for result in results:
    print(f"Expectancy: ${result.get('expectancy', 0):.2f} per trade")
```

### Interpretation Guide

| Expectancy | Interpretation | Action |
|------------|---------------|---------|
| > $100 | Excellent | Strong candidate for live trading |
| $50 - $100 | Good | Consider with proper risk management |
| $0 - $50 | Marginal | Needs improvement before trading |
| $0 | Break-even | Not worth trading (costs will make it negative) |
| < $0 | Losing | **DO NOT TRADE** |

---

## Complete Workflow Example

```python
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.universe_manager import UniverseManager
from app.backtesting.metrics import calculate_expectancy
from datetime import datetime

# Step 1: Get survivorship-bias-adjusted universe
manager = UniverseManager()
symbols = manager.get_universe(
    start_date=datetime(2010, 1, 1),
    end_date=datetime(2024, 12, 31),
    include_delisted=True,
    include_spun_off=True,
)

print(f"Testing with {len(symbols)} symbols (including failed companies)")

# Step 2: Optimize parameters with multiple testing correction
runner = ComprehensiveBacktestRunner("config/backtesting/config.yaml")

param_grid = [
    {"buy_threshold": 0.7, "sell_threshold": 0.3},
    {"buy_threshold": 0.75, "sell_threshold": 0.25},
    {"buy_threshold": 0.8, "sell_threshold": 0.2},
]

results = runner.optimize_with_validation(
    param_grid=param_grid,
    strategy_class=ModularMomentumStrategy,
)

# Step 3: Validate results
if not results['oos_valid']:
    print("FAILED: Out-of-sample validation failed")
    exit()

print(f"Best parameters: {results['best_params']}")
print(f"Adjusted confidence: {results['adjusted_confidence']:.4f}")

# Step 4: Calculate expectancy
# (from the trades in results)
expectancy = calculate_expectancy(winning_trades, losing_trades)

print(f"Expectancy: ${expectancy:.2f} per trade")

# Step 5: Make decision
if expectancy > 0 and results['oos_valid']:
    print("READY FOR LIVE TRADING")
else:
    print("NOT READY - Needs more work")
```

---

## Common Pitfalls

### Don't Ignore Multiple Testing
❌ **Wrong**: "I tested 50 combinations and found one with Sharpe 2.0!"
✅ **Right**: "After Bonferroni correction for 50 tests, none are significant."

### Don't Use Survivor-Biased Data
❌ **Wrong**: Backtesting with only S&P 500 companies from 2024
✅ **Right**: Include companies that existed during the period, even if they failed

### Don't Focus Only on Win Rate
❌ **Wrong**: "90% win rate, must be good!"
✅ **Right**: "90% win rate but avg loss 10x avg win → negative expectancy"

---

## Performance Tips

1. **Cache Universe Calculations**
   ```python
   # Calculate once, reuse
   universe = manager.get_universe(start_date, end_date)
   # Don't recalculate for each backtest
   ```

2. **Use Appropriate Correction Method**
   - Bonferroni: Small number of tests (<10)
   - Benjamini-Hochberg: Large number of tests (>20)
   - Holm-Bonferroni: Moderate number (10-20)

3. **Interpret Expectancy in Context**
   - Consider transaction costs
   - Consider position sizing
   - Consider market conditions

---

## References

- **Multiple Testing**: [Bonferroni Correction](https://en.wikipedia.org/wiki/Bonferroni_correction)
- **Survivorship Bias**: [Survivorship Bias in Backtesting](https://www.investopedia.com/terms/s/survivorshipbias.asp)
- **Expectancy**: [Expected Value in Trading](https://www.investopedia.com/terms/e/expectedvalue.asp)

---

**Last Updated**: 2026-01-27
**Version**: 1.0.0
**Status**: Production Ready ✅
