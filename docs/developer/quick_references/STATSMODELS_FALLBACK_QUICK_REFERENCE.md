# Statsmodels Fallback Quick Reference

## Overview

The codebase now includes fallback implementations for statsmodels functions. When statsmodels is not available, the system automatically uses scipy/numpy-based alternatives with appropriate warnings.

## Available Fallback Functions

### Time Series Analysis
```python
from app.core.statsmodels_fallback import adfuller, coint

# Augmented Dickey-Fuller test
result = adfuller(time_series, maxlag=1)
# Returns: (adf_statistic, pvalue, usedlag, critical_values, icbest)

# Cointegration test
stat, pvalue, crit_values = coint(series1, series2)
```

### Seasonal Decomposition
```python
from app.core.statsmodels_fallback import seasonal_decompose

# Decompose time series
result = seasonal_decompose(series, model='additive', period=12)
# Returns: DecomposeResult with observed, trend, seasonal, resid
```

### Regression Analysis
```python
from app.core.statsmodels_fallback import OLS

# Fit linear model
model = OLS(y, X).fit()
print(model.summary())
print(f"R-squared: {model.rsquared}")
print(f"Parameters: {model.params}")
```

### Autocorrelation Tests
```python
from app.core.statsmodels_fallback import acorr_ljungbox, pacf

# Ljung-Box test
result = acorr_ljungbox(x, lags=10)

# Partial autocorrelation
pacf_values = pacf(x, nlags=40)
```

### Autoregressive Models
```python
from app.core.statsmodels_fallback import AutoReg

# Fit AR model
model = AutoReg(series, lags=5)
results = model.fit()
print(results.summary())
```

## Usage Pattern

### In Your Code

```python
# Option 1: Use fallback directly
from app.core.statsmodels_fallback import adfuller
result = adfuller(series)

# Option 2: Try statsmodels first, fallback if unavailable
try:
    from statsmodels.tsa.stattools import adfuller as sm_adfuller
    def adfuller(*args, **kwargs):
        return sm_adfuller(*args, **kwargs)
    STATSMODELS_AVAILABLE = True
except ImportError:
    from app.core.statsmodels_fallback import adfuller
    STATSMODELS_AVAILABLE = False
```

### Checking Availability

```python
from app.core.statsmodels_fallback import USING_FALLBACK

if USING_FALLBACK:
    print("Using fallback implementations")
    print("Install statsmodels for full functionality:")
    print("  pip install statsmodels>=0.14.0,<1.0.0")
```

## Warning Messages

When using fallback, you'll see warnings like:

```
WARNING:app.core.statsmodels_fallback:Using fallback implementation for adfuller.
Results may differ from statsmodels. For full ADF test functionality,
install statsmodels: pip install statsmodels
```

## When to Use Fallback vs. Statsmodels

### Use Fallback For:
- Development and testing
- Quick prototyping
- Systems with minimal dependencies
- Basic statistical analysis

### Use Statsmodels For:
- Production trading systems
- Published research
- Backtesting for live trading
- When statistical accuracy is critical

## Installation

### Minimal Dependencies (Fallback)
```bash
pip install numpy>=1.20.0 scipy>=1.7.0 pandas>=1.3.0
```

### Full Functionality (Recommended for Production)
```bash
pip install statsmodels>=0.14.0,<1.0.0
```

## Example: Stationarity Test

```python
import numpy as np
import pandas as pd
from app.core.statsmodels_fallback import adfuller

# Generate random walk
np.random.seed(42)
series = np.random.randn(100).cumsum()

# Test for stationarity
result = adfuller(series, maxlag=1)

print(f"ADF Statistic: {result[0]:.4f}")
print(f"p-value: {result[1]:.4f}")
print(f"Critical Values:")
for key, value in result[3].items():
    print(f"  {key}: {value:.4f}")

if result[1] < 0.05:
    print("Series is stationary (reject null hypothesis)")
else:
    print("Series is non-stationary (fail to reject null hypothesis)")
```

## Example: Pairs Trading Cointegration Test

```python
from app.core.statsmodels_fallback import coint
import numpy as np

# Two price series
prices_a = np.random.randn(100).cumsum() + 100
prices_b = prices_a * 0.8 + np.random.randn(100) * 2

# Test for cointegration
stat, pvalue, crit_values = coint(prices_a, prices_b)

print(f"Cointegration Statistic: {stat:.4f}")
print(f"p-value: {pvalue:.4f}")

if pvalue < 0.05:
    print("Series are cointegrated (suitable for pairs trading)")
else:
    print("Series are not cointegrated")
```

## Troubleshooting

### Import Error
If you get `ModuleNotFoundError: No module named 'app'`:
```bash
export PYTHONPATH="/path/to/algoTrading:$PYTHONPATH"
```

### Numpy Compatibility Warning
If you see numpy version warnings:
```bash
pip install numpy>=2.0.0
# or downgrade if needed:
pip install "numpy<2"
```

### Always Getting Fallback Warnings
If statsmodels is installed but you still see warnings:
```python
# Verify installation
python -c "import statsmodels; print(statsmodels.__version__)"

# Reinstall if needed
pip install --force-reinstall statsmodels>=0.14.0
```

## Performance Considerations

- **Fallback implementations are generally faster** for small datasets
- **Statsmodels is more accurate** for statistical inference
- **For large datasets**, consider installing statsmodels for better numerical stability

## API Compatibility

All fallback functions maintain the same API as statsmodels:
- Same function signatures
- Same return value formats
- Same parameter names and defaults
- Compatible with existing code

## Files Using Fallback

The following files have been updated with fallback patterns:

1. `app/backtesting/feature_engineering/fractional_differentiation.py`
2. `app/microstructure/price_discovery.py`
3. `app/backtesting/seasonality_analyzer.py`
4. `app/services/stationarity_analyzer.py`
5. `app/services/half_life_calculator.py`
6. `app/services/strategy_stock_allocator.py`
7. `app/engines/risk_engine/__init__.py`
8. `app/backtesting/comprehensive_backtest_runner.py`
9. `app/backtesting/feature_engineering/fracdiff_visualizations.py`
10. `app/engines/strategy_engines/pairs_engine.py`

## Additional Resources

- **Full Implementation Report:** See `STATSMODELS_FALLBACK_IMPLEMENTATION_REPORT.md`
- **Fallback Source Code:** See `app/core/statsmodels_fallback.py`
- **Statsmodels Documentation:** https://www.statsmodels.org/

## Contributing

When adding new statsmodels dependencies, always:
1. Implement a fallback in `app/core/statsmodels_fallback.py`
2. Use try/except pattern in importing code
3. Add appropriate warning messages
4. Test both with and without statsmodels installed
5. Document the fallback behavior

---

**Last Updated:** 2026-01-28
**Maintained By:** Legacy Modernizer Team
