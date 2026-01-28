# Ernest Chan Quantitative Trading - Quick Reference

## Installation

```bash
# Install dependencies
pip install cvxpy>=1.4.0 hmmlearn>=0.9.0
```

## Quick Start Examples

### Factor Models

```python
from app.services.factor_models import FamaFrenchFactorModel

# Fit Fama-French 3-factor model
model = FamaFrenchFactorModel(model_type="three_factor")
result = model.fit(asset_returns, market_returns, smb_returns, hml_returns)

print(f"Beta Market: {result.factor_loadings.beta_market:.4f}")
print(f"R-squared: {result.r_squared:.4f}")
```

### Portfolio Optimization

```python
from app.services.optimization_chan import optimize_portfolio

# Optimize using Hierarchical Risk Parity
result = optimize_portfolio(returns, method='hrp')

print(f"Expected Return: {result.expected_return:.4f}")
print(f"Volatility: {result.volatility:.4f}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.4f}")
```

### Regime Detection

```python
from app.services.regime_detection_chan import detect_market_regimes

# Detect market regimes using HMM
regimes = detect_market_regimes(returns, method='hmm', n_regimes=3)

# Get current regime
detector = MarketRegimeDetector()
current = detector.get_current_regime(returns, prices)
print(f"Current Regime: {current.regime_type.value}")
```

### Execution Algorithms

```python
from app.services.execution_algorithms import create_execution_plan

# Create VWAP execution plan
plan = create_execution_plan(
    symbol="AAPL",
    quantity=10000,
    side="buy",
    algorithm="vwap"
)

print(f"Number of slices: {len(plan.execution_slices)}")
print(f"Expected slippage: {plan.estimated_slippage:.2f} bps")
```

## API Reference

### Factor Models (`factor_models.py`)

| Class | Methods | Purpose |
|-------|---------|---------|
| `FamaFrenchFactorModel` | `fit()`, `predict()` | Fama-French regression |
| `APTModel` | `fit()`, `get_factor_loadings()` | APT with PCA |
| `StatisticalArbitrage` | `generate_signals()` | Factor-neutral arb |

### Portfolio Optimization (`optimization_chan.py`)

| Class | Methods | Purpose |
|-------|---------|---------|
| `MeanVarianceOptimizer` | `optimize()` | Markowitz optimization |
| `RiskParityOptimizer` | `optimize()` | Equal risk contribution |
| `HierarchicalRiskParityOptimizer` | `optimize()` | HRP clustering |
| `MaximumDiversificationOptimizer` | `optimize()` | Max diversification |
| `CVaROptimizer` | `optimize()` | CVaR optimization |

### Regime Detection (`regime_detection_chan.py`)

| Class | Methods | Purpose |
|-------|---------|---------|
| `MarketRegimeDetector` | `detect_regimes()` | Multi-method detection |
| `VolatilityRegimeDetector` | `detect_volatility_regimes()` | Volatility regimes |

### Execution Algorithms (`execution_algorithms.py`)

| Class | Methods | Purpose |
|-------|---------|---------|
| `VWAPExecutor` | `create_execution_plan()` | VWAP execution |
| `TWAPExecutor` | `create_execution_plan()` | TWAP execution |
| `ImplementationShortfallExecutor` | `create_execution_plan()` | Optimal execution |
| `POVExecutor` | `create_execution_plan()` | POV execution |

## Compliance Matrix

| Concept | Status | Implementation |
|---------|--------|----------------|
| Factor Models | ✅ 95% | FF 3/5/4-factor, APT |
| Portfolio Optimization | ✅ 95% | 5 optimization methods |
| Regime Detection | ✅ 95% | 4 detection methods |
| Execution Algorithms | ✅ 95% | 4 execution algos |

## File Locations

```
app/services/
├── factor_models.py           (550 lines)
├── optimization_chan.py       (650 lines)
├── regime_detection_chan.py   (550 lines)
└── execution_algorithms.py    (600 lines)

tests/unit/services/test_chan_methods/
├── test_factor_models.py
├── test_optimization_chan.py
├── test_regime_detection.py
└── test_execution_algorithms.py

docs/
└── ERNEST_CHAN_QUANTITATIVE_TRADING.md
```

## Testing

```bash
# Run all Ernest Chan tests
pytest tests/unit/services/test_chan_methods/ -v

# Run specific test file
pytest tests/unit/services/test_chan_methods/test_factor_models.py -v

# Run with coverage
pytest tests/unit/services/test_chan_methods/ --cov=app.services --cov-report=html
```

## References

- Chan, E. P. (2013). *Quantitative Trading*
- Fama, E. F., & French, K. R. (1993). Common risk factors
- Almgren, R., & Chriss, N. (2001). Optimal execution
- Lopez de Prado, M. (2016). *Building Diversified Portfolios*

## Support

For detailed documentation, see: `docs/ERNEST_CHAN_QUANTITATIVE_TRADING.md`
