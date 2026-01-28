# Ernest Chan - Algorithmic Trading Quick Reference

Quick reference guide for Ernest Chan's methodologies implementation.

---

## Stationarity & Cointegration

### Test Stationarity

```python
from app.services.stationarity_analyzer import StationarityAnalyzer

analyzer = StationarityAnalyzer()
result = analyzer.test_stationarity(prices)

# Key outputs:
result.is_stationary      # bool
result.p_value            # float
result.half_life          # float (days)
result.hurst_exponent     # float (< 0.5 = mean reverting)
```

### Find Cointegrated Pairs

```python
from app.services.stationarity_analyzer import find_cointegrated_pairs

pairs = find_cointegrated_pairs(price_data)

for asset1, asset2, result in pairs:
    if result.spread_half_life < 30:  # Fast mean reversion
        # Trade this pair
        pass
```

---

## Risk Management

### ATR-Based Stop Loss

```python
from app.services.risk_management_chan import calculate_optimal_stop_loss

stop = calculate_optimal_stop_loss(
    entry_price=100.0,
    atr=2.5,
    direction="long",
    method="atr",  # or "fixed", "trailing"
)
# stop.stop_loss_price = 95.0 (100 - 2.5*2)
```

### Kelly Criterion Position Size

```python
from app.services.risk_management_chan import calculate_optimal_position_size

size = calculate_optimal_position_size(
    capital=100000,
    entry_price=100.0,
    stop_loss_price=95.0,
    method="kelly",
    win_rate=0.55,
    avg_win=5.0,
    avg_loss=3.0,
)
# size.shares = optimal share count
# size.kelly_fraction = Kelly fraction used
```

### Drawdown Control

```python
from app.services.risk_management_chan import ChanDrawdownController

controller = ChanDrawdownController(max_drawdown=0.25)
controller.update_equity(current_equity)

if controller.should_halt_trading():
    # Stop trading
    pass

multiplier = controller.get_position_size_multiplier()
# Reduce position sizes by this multiplier
```

---

## Performance Metrics

### Sharpe Ratio with CI

```python
from app.backtesting.chan_metrics import ChanSharpeRatioCalculator

calc = ChanSharpeRatioCalculator()
result = calc.calculate_sharpe_ratio(returns)

# Key outputs:
result.annualized_sharpe              # float
result.confidence_interval_low        # float
result.confidence_interval_high       # float
result.is_statistically_significant   # bool
```

### Max Drawdown Analysis

```python
from app.backtesting.chan_metrics import ChanDrawdownAnalyzer

analyzer = ChanDrawdownAnalyzer()
result = analyzer.analyze_drawdown(equity_curve)

# Key outputs:
result.max_drawdown_percentage     # float (negative)
result.max_drawdown_duration_days  # int
result.recovery_factor             # float
```

### Calmar Ratio

```python
from app.backtesting.chan_metrics import calculate_calmar_ratio

calmar = calculate_calmar_ratio(returns)
# > 3 = Excellent, > 1 = Good, < 0.5 = Poor
```

---

## Bias Correction

### Remove Look-Ahead Bias

```python
from app.backtesting.bias_correctors import LookAheadBiasCorrector

corrector = LookAheadBiasCorrector()
result = corrector.validate_no_lookahead(
    signals=signals_df,
    market_data=market_df,
)

if result.has_lookahead_bias:
    # Fix issues in result.recommendations
    pass
```

### Apply Corporate Actions

```python
from app.backtesting.bias_correctors import create_bias_correction_pipeline

clean_data = create_bias_correction_pipeline(
    raw_data=prices_df,
    dividend_data=dividends_df,
    split_data=splits_df,
)
```

---

## Common Patterns

### Mean Reversion Strategy Setup

```python
# 1. Test for stationarity
analyzer = StationarityAnalyzer()
result = analyzer.test_stationarity(prices)

if result.is_stationary and result.half_life < 20:
    # 2. Calculate position size
    sizer = ChanPositionSizer()
    size = sizer.calculate_risk_based_position(
        capital=100000,
        entry_price=price,
        stop_loss_price=price * 0.95,
    )

    # 3. Set stop loss
    stop = calculate_optimal_stop_loss(
        entry_price=price,
        atr=atr_value,
        direction="long",
    )

    # 4. Execute trade
    # execute_trade(symbol, size.shares, stop.stop_loss_price)
```

### Pairs Trading Setup

```python
# 1. Find cointegrated pairs
pairs = find_cointegrated_pairs(price_data)

# 2. Filter by half-life
for asset1, asset2, result in pairs:
    if 10 < result.spread_half_life < 40:
        # 3. Calculate position sizes
        size1 = capital * 0.02 / abs(price1 - result.hedge_ratio * price1)
        size2 = size1 * result.hedge_ratio

        # 4. Enter pair trade
        # enter_pair_trade(asset1, size1, asset2, size2)
```

---

## Key Formulas

### Half-Life of Mean Reversion
```
half_life = -ln(2) / theta
where theta = coefficient from OU process regression
```

### Kelly Criterion
```
f* = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
Use half-Kelly: f = f* / 2
```

### Sharpe Ratio (Annualized)
```
Sharpe = (mean_return - risk_free) / std_return * sqrt(252)
```

### Calmar Ratio
```
Calmar = annual_return / abs(max_drawdown)
```

---

## Quick Rules of Thumb

| Metric | Good | Excellent |
|--------|------|-----------|
| Half-Life | < 20 days | < 10 days |
| Hurst Exponent | < 0.5 | < 0.4 |
| Sharpe Ratio | > 1 | > 2 |
| Calmar Ratio | > 1 | > 3 |
| Max Drawdown | < 20% | < 15% |

---

## File Locations

| Module | Path |
|--------|------|
| Stationarity | `app/services/stationarity_analyzer.py` |
| Bias Correction | `app/backtesting/bias_correctors.py` |
| Risk Management | `app/services/risk_management_chan.py` |
| Performance Metrics | `app/backtesting/chan_metrics.py` |

---

For detailed documentation, see `ERNEST_CHAN_IMPLEMENTATION_REPORT.md`
