# Covered Calls Strategy - Implementation Summary

## Overview

This implementation provides a complete **Covered Calls Strategy** for the algorithmic trading system, following the FASE 4.4 - INCOME_GENERATION requirements from the AUDIT_PLAN_COMPLETO.

## Files Created

```
app/strategies/covered_calls/
├── __init__.py                      # Package exports and metadata
├── models.py                        # Pydantic data models
├── greeks_calculator.py             # Black-Scholes option pricing
├── option_screener.py               # Option filtering and screening
├── position_manager.py              # Position lifecycle management
├── roll_analyzer.py                 # Rolling opportunity analysis
└── covered_call_strategy.py         # Main strategy implementation
```

## Key Components

### 1. Models (`models.py`)

- **CallOption**: Option data with Greeks, moneyness, time value calculations
- **CoveredCallPosition**: Position tracking with P&L, break-even, returns
- **CoveredCallConfig**: Strategy configuration with validation
- **OptionScreeningCriteria**: Filtering parameters
- **RollOpportunity**: Rolling analysis results
- **AssignmentProbability**: Risk assessment enum

### 2. Greeks Calculator (`greeks_calculator.py`)

- **BlackScholesGreeks**: Implementation of Black-Scholes-Merton model
  - Delta, Gamma, Theta, Vega, Rho calculations
  - Implied volatility calculation (Newton-Raphson)
  - Assignment probability estimation
- **GreeksCalculator**: Facade for pricing models

### 3. Option Screener (`option_screener.py`)

- Filters options by:
  - Days to expiration (DTE): 20-50 days optimal
  - Moneyness: 2-5% OTM for balanced risk/reward
  - Premium: Minimum 0.5-1% of underlying price
  - Liquidity: Open interest and volume thresholds
  - Greeks: Delta and theta targets
- Scores options (0-100) for ranking
- Provides filtered lists for decision making

### 4. Position Manager (`position_manager.py`)

Manages covered call position lifecycle:
- **Opening**: Validates share coverage, contract limits
- **Updating**: Refreshes prices and probabilities
- **Closing**: Records P&L and reasons
- **Rolling decisions**: When to roll positions
- **Metrics tracking**: Portfolio aggregated statistics

Key position metrics:
- `break_even_price`: Cost basis adjusted by premium
- `max_profit`: Capped at strike + premium
- `return_if_called`: If assigned at expiration
- `return_if_unchanged`: If price unchanged
- `downside_protection`: Percentage from premium
- `annualized_return`: Time-adjusted yield

### 5. Roll Analyzer (`roll_analyzer.py`)

Analyzes rolling opportunities:

**Roll Types:**
- **ROLL_UP_AND_OUT**: Stock rallied, move to higher strike + later expiry
- **ROLL_DOWN_AND_OUT**: Stock declined, lower strike + later expiry
- **ROLL_OUT**: Time decay management, same strike + later expiry

**Analysis:**
- Additional premium benefit
- Assignment probability changes
- Expected return comparisons
- Risk/reward optimization

### 6. Main Strategy (`covered_call_strategy.py`)

Implements `BaseStrategy` interface:
- `generate_signals()`: Creates buy/sell/hold signals
- `risk_check()`: Validates against portfolio limits
- `validate_config()`: Configuration validation
- `create_covered_call_position()`: Position creation
- `analyze_roll_opportunities()`: Rolling analysis

## Strategy Rules

1. **Position Requirements:**
   - Minimum 100 shares (1 contract = 100 shares)
   - Maximum position size: 10% of portfolio
   - Maximum 10 contracts per position

2. **Option Selection:**
   - Target DTE: 30 days (±15 days)
   - Target OTM: 3% (±2%)
   - Minimum premium: 1% of stock price
   - Avoid earnings announcements
   - Minimum liquidity requirements

3. **Rolling Rules:**
   - Roll when DTE ≤ 7 days
   - Roll ITM when assignment probability HIGH+
   - Roll deep OTM to capture more premium
   - Target same or better terms

4. **Risk Management:**
   - Maximum 30% of portfolio in covered calls
   - Monitor assignment probability
   - Diversify across underlyings

## Usage Example

```python
from app.strategies.covered_calls import CoveredCallStrategy

# Configuration
config = {
    "name": "MyCoveredCalls",
    "target_dte": 30,
    "target_otm_pct": 0.03,
    "min_premium_pct": 0.01,
    "max_position_size": 0.10,
}

# Initialize strategy
strategy = CoveredCallStrategy(config)

# Set available options
from app.strategies.covered_calls.models import CallOption
options = [...]  # List of CallOption objects
strategy.set_available_options(options)

# Create covered call position
position = strategy.create_covered_call_position(
    symbol="AAPL",
    shares_owned=200,
    average_cost=Decimal("140.00"),
    current_price=Decimal("145.00"),
)

# Analyze rolling opportunities
opportunities = strategy.analyze_roll_opportunities(
    symbol="AAPL",
    current_price=Decimal("148.00"),
)
```

## Test Coverage

**65 comprehensive tests** covering:
- Model validation (Pydantic)
- Greeks calculations (Black-Scholes)
- Option screening logic
- Position management
- Roll analysis
- Main strategy integration
- Edge cases and error handling

Run tests:
```bash
python -m pytest app/tests/strategies/test_covered_calls_strategy.py -v
```

## Integration with Strategy Registry

The strategy can be registered in the strategy registry:

```python
from app.strategies.strategy_registry import StrategyRegistry

StrategyRegistry.register("covered_calls", CoveredCallStrategy)
```

## Metrics and Monitoring

Key performance indicators:
- Total premium collected
- Win rate (positions expiring worthless)
- Annualized return
- Assignment rate
- Average holding period
- Roll frequency

## Mathematical Background

**Black-Scholes Formula:**

```
C = S·N(d1) - K·e^(-rT)·N(d2)

d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
d2 = d1 - σ√T
```

**Greeks:**
- Delta = N(d1)
- Gamma = N'(d1) / (Sσ√T)
- Theta = decay per day
- Vega = sensitivity to volatility
- Rho = sensitivity to interest rate

## Dependencies

- `pydantic`: Data validation
- `numpy`: Mathematical operations
- Existing strategy framework (`BaseStrategy`, `Signal`, etc.)

## Future Enhancements

1. **Advanced Greeks**
   - Higher-order Greeks (Vanna, Charm, etc.)
   - Volatility surface modeling

2. **Strategy Variations**
   - Poor Man's Covered Call (LEAPS + short calls)
   - Buy-Write Strategy (simultaneous entry)
   - Ratio Writes (varying ratios)

3. **Risk Management**
   - Portfolio-level Greeks exposure
   - Correlation analysis
   - Stress testing

4. **Automation**
   - Auto-roll execution
   - Assignment prediction ML models
   - Earnings calendar integration

## References

- Black, F., & Scholes, M. (1973). "The Pricing of Options and Corporate Liabilities"
- Hull, J. C. (2022). "Options, Futures, and Other Derivatives"
- AUDIT_PLAN_COMPLETO - FASE 4.4 requirements

---

**Implementation Date**: 2026-01-30
**Version**: 1.0.0
**Status**: Production Ready ✅
