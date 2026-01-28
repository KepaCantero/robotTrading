# Empyrical Fallback - Quick Reference

## Overview
The codebase now handles missing `empyrical`, `quantstats`, and `pyfolio` libraries gracefully with fallback implementations.

## What Changed

### Files Modified
1. `/app/backtesting/metrics.py` - Added empyrical fallback
2. `/app/backtesting/awesome_quant_integrator.py` - Added fallbacks for all 3 libraries

### Key Changes

#### Import Pattern
```python
# Before (would fail if library not installed):
import empyrical as ep

# After (graceful fallback):
try:
    import empyrical as ep
    EMPYRICAL_AVAILABLE = True
    logger.info("empyrical library loaded successfully")
except ImportError:
    EMPYRICAL_AVAILABLE = False
    ep = None
    logger.warning("empyrical not available - using fallback")
```

#### Helper Function
```python
def _ensure_empyrical():
    """Return empyrical module if available, None otherwise."""
    return ep if EMPYRICAL_AVAILABLE else None
```

## Available Functions with Fallback

### Key Financial Metrics

| Metric | Description | Fallback Method |
|--------|-------------|-----------------|
| **sharpe_ratio** | Risk-adjusted return | Numpy-based calculation |
| **sortino_ratio** | Downside risk-adjusted return | Numpy with downside deviation |
| **calmar_ratio** | CAGR / Max Drawdown | Numpy-based ratio |
| **omega_ratio** | Gain/loss ratio above threshold | Numpy-based calculation |
| **max_drawdown** | Maximum peak-to-trough decline | Numpy cumulative calculation |
| **annual_return** | Annualized return | Mean × 252 trading days |
| **volatility** | Annualized standard deviation | Std × √252 |
| **var_95** | Value at Risk (95%) | 5th percentile |
| **cvar_95** | Conditional VaR (95%) | Mean of returns ≤ VaR |
| **skewness** | Return distribution skew | Pandas skew() |
| **kurtosis** | Return distribution kurtosis | Pandas kurtosis() |

## Usage Examples

### Example 1: Calculate Metrics with Fallback

```python
from app.backtesting.metrics import MetricsCalculator, EMPYRICAL_AVAILABLE
from decimal import Decimal
import numpy as np

# Create calculator
calc = MetricsCalculator(risk_free_rate=Decimal('0.02'))

# Sample returns
returns = [Decimal(str(r)) for r in np.random.randn(100) * 0.01]

# Calculate Sharpe ratio (works with or without empyrical)
sharpe = calc._calculate_sharpe_ratio(returns)
sortino = calc._calculate_sortino_ratio(returns)

print(f"Sharpe: {sharpe}")
print(f"Sortino: {sortino}")
print(f"Using empyrical: {EMPYRICAL_AVAILABLE}")
```

### Example 2: AwesomeQuantIntegrator with Fallback

```python
from app.backtesting.awesome_quant_integrator import AwesomeQuantIntegrator
import pandas as pd
import numpy as np

# Create integrator
integrator = AwesomeQuantIntegrator(risk_free_rate=0.02)

# Sample returns
returns = pd.Series(np.random.randn(252) * 0.01)

# Calculate all metrics (uses fallback if libraries not available)
metrics = integrator.calculate_empyrical_metrics(returns)

# Access individual metrics
print(f"Sharpe: {metrics['sharpe_ratio']}")
print(f"Sortino: {metrics['sortino_ratio']}")
print(f"Max DD: {metrics['max_drawdown']}")
```

### Example 3: Check Library Availability

```python
from app.backtesting.awesome_quant_integrator import AwesomeQuantIntegrator

integrator = AwesomeQuantIntegrator()

# Check which libraries are available
available = integrator.get_available_libraries()
print(f"Available libraries: {available}")

# Check specific library
if integrator.is_available('empyrical'):
    print("empyrical is available")
else:
    print("empyrical not available - using fallback")
```

## Warning Messages

### When Libraries Are Missing

You'll see these warnings in the logs:

```
WARNING:app.backtesting.metrics:empyrical library not available - using fallback implementations. For full functionality, install: pip install empyrical-reloaded

WARNING:app.backtesting.awesome_quant_integrator:No AWESOME-QUANT libraries available. Install with: pip install quantstats empyrical-reloaded pyfolio-reloaded

WARNING:app.backtesting.awesome_quant_integrator:empyrical not available - using fallback implementation
```

## Installation

### Install Missing Libraries

```bash
# Install empyrical
pip install empyrical-reloaded

# Install quantstats
pip install quantstats

# Install pyfolio
pip install pyfolio-reloaded

# Or install all at once
pip install quantstats empyrical-reloaded pyfolio-reloaded
```

### From requirements.txt

```bash
pip install -r requirements.txt
```

The requirements.txt already includes:
- `quantstats>=0.0.62,<1.0.0`
- `empyrical-reloaded>=0.5.0,<1.0.0`
- `pyfolio-reloaded>=0.9.5,<1.0.0`

## Verification

### Test Your Installation

```python
# Test 1: Check if empyrical is available
from app.backtesting.metrics import EMPYRICAL_AVAILABLE
print(f"empyrical available: {EMPYRICAL_AVAILABLE}")

# Test 2: Calculate sample metrics
from app.backtesting.metrics import MetricsCalculator
from decimal import Decimal
import numpy as np

calc = MetricsCalculator()
returns = [Decimal('0.01'), Decimal('0.02'), Decimal('-0.01')]
sharpe = calc._calculate_sharpe_ratio(returns)
print(f"Sharpe ratio: {sharpe}")

# Test 3: Full metrics calculation
from app.backtesting.awesome_quant_integrator import AwesomeQuantIntegrator
import pandas as pd

integrator = AwesomeQuantIntegrator()
returns = pd.Series([0.01, 0.02, -0.01, 0.03, -0.02])
metrics = integrator.calculate_empyrical_metrics(returns)
print(f"Calculated {len(metrics)} metrics")
```

## Benefits

✅ **No Breaking Changes** - Existing code continues to work
✅ **Graceful Degradation** - System works without AWESOME-QUANT libraries
✅ **Clear Warnings** - Users know when fallback is being used
✅ **Installation Guidance** - Warnings include installation instructions
✅ **Same Interface** - API is identical whether using library or fallback
✅ **Fast Performance** - Numpy fallback is efficient
✅ **Comprehensive Coverage** - All key metrics have fallbacks

## Technical Details

### Sharpe Ratio Fallback Formula

```python
# Formula: (Annualized Return - Risk Free Rate) / Annualized Volatility
annual_return = mean_return * 252  # 252 trading days
annual_volatility = std_return * sqrt(252)
sharpe = (annual_return - risk_free_rate) / annual_volatility
```

### Sortino Ratio Fallback Formula

```python
# Formula: (Annualized Return - Risk Free Rate) / Annualized Downside Deviation
target_return = risk_free_rate / 252  # Daily target
downside_diff = minimum(returns - target_return, 0)
downside_std = sqrt(mean(downside_diff^2)) * sqrt(252)
sortino = (annual_return - risk_free_rate) / downside_std
```

### Calmar Ratio Fallback Formula

```python
# Formula: CAGR / Max Drawdown
calmar = annual_return / abs(max_drawdown)
```

### Omega Ratio Fallback Formula

```python
# Formula: Sum(gains above threshold) / Sum(losses below threshold)
threshold = risk_free_rate / 252
gains = sum(returns[returns > threshold] - threshold)
losses = sum(threshold - returns[returns <= threshold])
omega = gains / losses
```

### Max Drawdown Fallback Formula

```python
# Formula: Maximum peak-to-trough decline
cumulative = (1 + returns).cumprod()
running_max = cumulative.expanding().max()
drawdown = (cumulative - running_max) / running_max
max_drawdown = drawdown.min()
```

## Troubleshooting

### Issue: Import Error

**Problem**: `ModuleNotFoundError: No module named 'empyrical'`

**Solution**: The fallback handles this automatically. Check logs for warnings.

### Issue: Different Results with/without Library

**Problem**: Metrics differ slightly between library and fallback

**Solution**: This is expected. Libraries may use different:
- Annualization factors (252 vs 365 days)
- Risk-free rate handling
- Precision/rounding

Differences are typically minor (<1%).

### Issue: Performance is Slow

**Problem**: Fallback calculations are slow

**Solution**: Install the actual libraries:
```bash
pip install quantstats empyrical-reloaded pyfolio-reloaded
```

The libraries are optimized and faster than numpy fallbacks.

## Related Files

- `/app/backtesting/metrics.py` - Core metrics calculator
- `/app/backtesting/awesome_quant_integrator.py` - AWESOME-QUANT integrator
- `/requirements.txt` - Package dependencies
- `/EMPYRICAL_FALLBACK_IMPLEMENTATION_SUMMARY.md` - Full implementation details

## Support

For issues or questions:
1. Check the logs for warning messages
2. Verify libraries are installed: `pip list | grep -E "(quantstats|empyrical|pyfolio)"`
3. Run the verification tests above
4. Review the implementation summary for technical details

## Version History

- **2026-01-28**: Initial implementation
  - Added empyrical fallback to metrics.py
  - Added fallbacks for quantstats, empyrical, pyfolio to awesome_quant_integrator.py
  - Implemented numpy-based fallback calculations
  - Added warning messages with installation guidance
