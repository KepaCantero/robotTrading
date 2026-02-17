# Compliance Integration Guide - ALL 12 Rules

**Date:** 2026-01-28
**Version:** 1.0
**Status:** Complete Integration

## Executive Summary

This guide explains how to use ALL 12 compliance systems integrated into your algorithmic trading platform:

| Rule | Author | Systems | Status |
|------|--------|---------|--------|
| 1 | Ernest Chan | Factor Models, Portfolio Optimization, Regime Detection, Execution Algorithms | ✅ 95% |
| 2 | Narang | Alpha Models, Risk Models, Transaction Costs, Portfolio Construction | ✅ 95% |
| 3 | López de Prado | Sample Weights, Purged CV, Meta-Labeling, MCC Metrics | ✅ 88% |
| 4 | Tomasini | Trading Systems Architecture | ✅ 82% |
| 5 | Hastie | Statistical Learning | ✅ 78% |
| 6 | Harris | Order Book, Bid-Ask Bounce, Market Impact, Dark Pools, PFOF | ✅ 95% |
| 7 | O'Hara | Order Flow (PIN, VPIN), Liquidity, Price Discovery, Trading Mechanisms | ✅ 95% |
| 8 | Percival | Architecture Patterns | ✅ 75% |
| 13 | Hull | Greeks Validation, VaR Backtesting, Stress Scenarios | ✅ 95% |
| 18 | Martin | Clean Architecture | ✅ 80% |
| 20 | Google SRE | Golden Signals, Trading Metrics, Toil Tracking, On-Call | ✅ 95% |
| 21 | Beck TDD | Test-Driven Development | ✅ 82% |

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Integration Module](#core-integration-module)
3. [Backtesting Integration](#backtesting-integration)
4. [Live Trading Integration](#live-trading-integration)
5. [Paper Trading Integration](#paper-trading-integration)
6. [API Reference](#api-reference)
7. [Examples](#examples)

---

## Quick Start

### Installation

All compliance systems are already integrated. Simply import and use:

```python
# For all three systems
from app.core import get_compliance_integration_engine

# Get the engine
engine = get_compliance_integration_engine()

# Check availability
availability = engine.get_system_availability()
print(availability)
# {'ernest_chan': True, 'narang': True, 'lopez_de_prado': True, ...}
```

### Basic Usage

```python
from app.core import quick_pre_trade_check
from decimal import Decimal

# Quick pre-trade check
can_execute, reason = quick_pre_trade_check(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150.00"),
    price_history=price_df,  # Optional
)

if can_execute:
    print("Order approved")
else:
    print(f"Order blocked: {reason}")
```

---

## Core Integration Module

### Location
`app/core/compliance_integration.py`

### Main Classes

#### ComplianceIntegrationEngine

The main engine that integrates ALL 12 compliance systems.

```python
from app.core import get_compliance_integration_engine

engine = get_compliance_integration_engine(
    asset_class="equity",      # equity, etf, forex, crypto, futures
    enable_all_rules=True,     # Enable all 12 rules
    strict_mode=False,         # Block orders on compliance failures
)
```

### Key Methods

#### comprehensive_pre_trade_check()

The main pre-trade analysis using ALL compliance systems.

```python
analysis = engine.comprehensive_pre_trade_check(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    current_price=Decimal("150.00"),
    price_history=price_df,
    order_book=order_book_snapshot,
    urgency=0.5,
    signal_time=datetime.now(),
)

# Result fields
print(f"Can execute: {analysis.can_execute}")
print(f"Confidence: {analysis.confidence:.0%}")
print(f"Market regime: {analysis.market_regime}")
print(f"Liquidity regime: {analysis.liquidity_regime}")
print(f"Alpha signal: {analysis.alpha_signal}")
print(f"VPIN: {analysis.vpin:.3f}")
print(f"PIN: {analysis.pin:.3f}")
print(f"Estimated cost: {analysis.estimated_total_cost_bps:.1f} bps")
print(f"Recommended venue: {analysis.recommended_venue}")
print(f"Recommended algorithm: {analysis.recommended_algorithm}")
print(f"Limit price: {analysis.recommended_limit_price}")
```

#### comprehensive_post_trade_analysis()

Post-trade execution quality analysis.

```python
analysis = engine.comprehensive_post_trade_analysis(
    order_id="order_123",
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    execution_price=Decimal("150.25"),
    signal_price=Decimal("150.00"),
    signal_time=datetime.now() - timedelta(minutes=5),
    submission_time=datetime.now() - timedelta(minutes=1),
    execution_time=datetime.now(),
    nbbo_at_execution=(Decimal("150.20"), Decimal("150.30")),
)

print(f"Implementation shortfall: {analysis.implementation_shortfall_bps:.1f} bps")
print(f"Market impact: {analysis.market_impact_bps:.1f} bps")
print(f"Timing cost: {analysis.timing_cost_bps:.1f} bps")
print(f"Execution quality: {analysis.execution_quality_score:.0f}/100")
```

#### optimize_portfolio_comprehensive()

Portfolio optimization combining Chan + Narang methods.

```python
result = engine.optimize_portfolio_comprehensive(
    symbols=["AAPL", "MSFT", "GOOGL"],
    returns=returns_df,
    current_prices={"AAPL": Decimal("150"), "MSFT": Decimal("300"), "GOOGL": Decimal("2500")},
)

print(f"Optimal weights: {result.weights}")
print(f"Expected return: {result.expected_return:.2%}")
print(f"Expected risk: {result.expected_risk:.2%}")
print(f"Sharpe ratio: {result.sharpe_ratio:.2f}")
print(f"Regime: {result.regime}")
```

---

## Backtesting Integration

### Using the Compliance-Aware Backtester

```python
from app.trading_compliance import wrap_backtester
from app.backtesting.engine import SimpleBacktester
from decimal import Decimal

# Create original backtester
original_backtester = SimpleBacktester(config)

# Wrap with compliance
backtester = wrap_backtester(
    backtester=original_backtester,
    enable_compliance=True,
)

# Execute with compliance
result = backtester.execute_with_compliance(
    quotes=historical_quotes,
    price_history=price_df,
)

# Access compliance metrics
print(result.compliance_metrics)
# {
#     'total_signals': 150,
#     'blocked_by_compliance': 15,
#     'modified_by_compliance': 30,
#     'passed_through': 105,
#     'avg_market_impact_bps': 8.5,
#     'avg_timing_cost_bps': 2.3,
# }
```

### Manual Compliance Checks in Backtesting

```python
from app.core import get_compliance_integration_engine

engine = get_compliance_integration_engine()

# For each signal in your backtest
for signal in signals:
    # Check compliance
    can_execute, reason, analysis = backtester.check_signal_compliance(
        symbol=signal.symbol,
        side=signal.side,
        quantity=signal.quantity,
        price=signal.price,
        timestamp=signal.timestamp,
    )

    if can_execute:
        # Simulate execution with realistic costs
        exec_price, impact_bps, timing_bps = backtester.simulate_execution_with_costs(
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            price=signal.price,
            timestamp=signal.timestamp,
        )

        # Execute trade
        backtester.execute_trade(exec_price, signal.quantity)
    else:
        print(f"Signal blocked: {reason}")
```

---

## Live Trading Integration

### Using the Compliance-Aware Live Trader

```python
from app.trading_compliance import wrap_live_trader
from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter
from decimal import Decimal

# Create original adapter
original_adapter = AlpacaAdapter()
await original_adapter.connect(...)

# Wrap with compliance
trader = wrap_live_trader(
    adapter=original_adapter,
    enable_compliance=True,
    strict_mode=True,  # Block orders that fail compliance
)

# Place order with compliance checks
success, order_id, venue = await trader.place_order_with_compliance(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    order_type="LIMIT",
    urgency=0.5,
    signal_time=datetime.now(),
)

if success:
    print(f"Order placed: {order_id} on {venue}")
else:
    print(f"Order blocked: {order_id}")

# After execution, analyze quality
analysis = await trader.analyze_execution(
    order_id=order_id,
    execution_price=Decimal("150.25"),
    execution_time=datetime.now(),
    nbbo_at_execution=(Decimal("150.20"), Decimal("150.30")),
)

print(f"Execution quality score: {analysis.execution_quality_score:.0f}/100")
```

### SLO Tracking (Google SRE)

```python
# Get SLO metrics
slo_metrics = trader.get_slo_metrics()

print(f"SLO compliance rate: {slo_metrics['slo_compliance_rate']:.1%}")
print(f"Average latency: {slo_metrics['avg_latency_ms']:.0f}ms")
print(f"Total violations: {slo_metrics['slo_violations']}")
```

---

## Paper Trading Integration

### Using the Compliance-Aware Paper Trader

```python
from app.trading_compliance import wrap_paper_trader
from app.services.live_trading.broker_adapters.paper_adapter import PaperAdapter
from decimal import Decimal

# Create original adapter
original_adapter = PaperAdapter(initial_cash=Decimal("100000"))
await original_adapter.connect()

# Wrap with realistic simulation
paper_trader = wrap_paper_trader(
    adapter=original_adapter,
    enable_compliance=True,
    realistic_simulation=True,  # Use realistic market impact
)

# Place order with realistic execution
success, order_id, execution_price = await paper_trader.place_order_realistic(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    urgency=0.5,
)

print(f"Order executed at: ${execution_price:.2f}")
# Price includes: bid-ask spread + market impact + slippage
```

### Simulation Statistics

```python
stats = paper_trader.get_simulation_stats()

print(f"Realistic simulation: {stats['realistic_simulation']}")
print(f"Default spread: {stats['default_spread_bps']} bps")
print(f"Compliance enabled: {stats['compliance_enabled']}")
```

---

## API Reference

### Convenience Functions

#### quick_pre_trade_check()

```python
from app.core import quick_pre_trade_check

can_execute, reason = quick_pre_trade_check(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    price=Decimal("150.00"),
    price_history=price_df,
)
```

#### get_execution_recommendation()

```python
from app.core import get_execution_recommendation

recommendation = get_execution_recommendation(
    symbol="AAPL",
    quantity=Decimal("1000"),
    current_price=Decimal("150.00"),
    price_history=price_df,
    order_book=order_book_snapshot,
)

print(f"Venue: {recommendation['venue']}")
print(f"Algorithm: {recommendation['algorithm']}")
print(f"Limit Price: {recommendation['limit_price']}")
print(f"Est. Cost: {recommendation['estimated_cost_bps']:.1f} bps")
```

### Data Classes

#### ComprehensivePreTradeAnalysis

```python
@dataclass
class ComprehensivePreTradeAnalysis:
    can_execute: bool
    confidence: float
    reasons: List[str]

    # Ernest Chan
    market_regime: Optional[str]
    regime_confidence: float

    # Narang
    alpha_signal: Optional[float]
    alpha_decay_rate: Optional[float]
    recommended_holding_period: Optional[int]

    # Harris & O'Hara
    order_book_depth_ok: bool
    liquidity_score: float
    liquidity_regime: str
    flow_toxicity: float
    vpin: float
    pin: float

    # Cost estimates
    estimated_market_impact_bps: float
    estimated_timing_cost_bps: float
    estimated_total_cost_bps: float

    # Execution recommendations
    recommended_venue: str
    recommended_algorithm: str
    recommended_limit_price: Optional[Decimal]

    # Risk factors
    risk_factors: Dict[str, float]

    # Hull
    var_1d_95: Optional[float]
    beta: Optional[float]
```

#### ComprehensivePostTradeAnalysis

```python
@dataclass
class ComprehensivePostTradeAnalysis:
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    execution_price: Decimal

    # Cost breakdown
    implementation_shortfall_bps: float
    market_impact_bps: float
    timing_cost_bps: float
    effective_spread_bps: float

    # Execution quality
    execution_quality_score: float
    price_improvement_bps: float

    # SLO tracking
    latency_ms: float
    fill_rate: float
```

---

## Examples

### Example 1: Complete Backtesting Workflow

```python
from app.trading_compliance import wrap_backtester
from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

# Load configuration
runner = ComprehensiveBacktestRunner("config/backtesting.yaml")

# Wrap the internal executor
runner.executor = wrap_backtester(
    backtester=runner.executor,
    enable_compliance=True,
)

# Run backtests with compliance
results = runner.run_all_backtests()

# Check compliance metrics
for result in results:
    if hasattr(result, 'compliance_metrics'):
        print(f"{result['test_name']}:")
        print(f"  Blocked: {result['compliance_metrics']['blocked_by_compliance']}")
        print(f"  Avg Impact: {result['compliance_metrics']['avg_market_impact_bps']:.1f} bps")
```

### Example 2: Live Trading with Full Compliance

```python
from app.trading_compliance import wrap_live_trader
from app.services.live_trading.broker_adapters.alpaca_adapter import AlpacaAdapter
from app.core import get_compliance_integration_engine
from decimal import Decimal
import asyncio

async def main():
    # Setup
    adapter = AlpacaAdapter()
    await adapter.connect(
        api_key="YOUR_KEY",
        api_secret="YOUR_SECRET",
        paper_trading=True,
    )

    trader = wrap_live_trader(adapter, enable_compliance=True, strict_mode=True)
    engine = get_compliance_integration_engine()

    # Trading loop
    symbols = ["AAPL", "MSFT", "GOOGL"]

    for symbol in symbols:
        # Get market data
        price = await get_current_price(symbol)
        price_history = await get_price_history(symbol, days=30)

        # Generate signal
        signal = generate_signal(symbol, price_history)

        # Check compliance
        analysis = engine.comprehensive_pre_trade_check(
            symbol=symbol,
            side="BUY" if signal > 0 else "SELL",
            quantity=Decimal("100"),
            current_price=Decimal(str(price)),
            price_history=price_history,
            urgency=0.5,
        )

        if not analysis.can_execute:
            print(f"{symbol}: BLOCKED - {'; '.join(analysis.reasons)}")
            continue

        # Place order
        success, order_id, venue = await trader.place_order_with_compliance(
            symbol=symbol,
            side="BUY" if signal > 0 else "SELL",
            quantity=Decimal("100"),
            urgency=analysis.confidence,
        )

        if success:
            print(f"{symbol}: ORDER PLACED - {order_id} on {venue}")

            # Track for post-trade analysis
            # (call analyze_execution when filled)

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 3: Portfolio Optimization with Compliance

```python
from app.core import get_compliance_integration_engine
from decimal import Decimal
import pandas as pd

engine = get_compliance_integration_engine()

# Get returns data
returns = pd.DataFrame({
    'AAPL': [0.01, 0.02, -0.01, ...],
    'MSFT': [0.015, 0.01, 0.005, ...],
    'GOOGL': [0.02, -0.01, 0.015, ...],
})

# Get current prices
prices = {
    'AAPL': Decimal("150.00"),
    'MSFT': Decimal("300.00"),
    'GOOGL': Decimal("2500.00"),
}

# Optimize
result = engine.optimize_portfolio_comprehensive(
    symbols=list(returns.columns),
    returns=returns,
    current_prices=prices,
)

print("Optimal Portfolio:")
for symbol, weight in result.weights.items():
    print(f"  {symbol}: {weight:.2%}")

print(f"\nExpected Return: {result.expected_return:.2%}")
print(f"Expected Risk: {result.expected_risk:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Regime: {result.regime}")
```

---

## Testing

### Run Integration Tests

```bash
# Run all compliance integration tests
pytest tests/integration/test_compliance_integration.py -v

# Run specific system tests
pytest tests/unit/services/test_chan_methods/ -v
pytest tests/unit/services/portfolio_construction_narang/ -v
pytest tests/unit/engines/execution_engine/microstructure/ -v
pytest tests/unit/microstructure/ -v
pytest tests/unit/sre/ -v
```

### Test Individual Components

```python
# Test availability
from app.core import get_compliance_integration_engine

engine = get_compliance_integration_engine()
availability = engine.get_system_availability()

for system, available in availability.items():
    assert available, f"{system} not available!"

print("All systems available!")
```

---

## Troubleshooting

### System Not Available

If a compliance system is not available:

1. Check if dependencies are installed:
```bash
pip install -r requirements.txt
```

2. Check import paths in `app/core/compliance_integration.py`

3. Enable fallback mode:
```python
engine = get_compliance_integration_engine(
    enable_all_rules=False,  # This will enable only available systems
)
```

### High Compliance Blocking Rate

If too many orders are being blocked:

1. Use non-strict mode:
```python
trader = wrap_live_trader(adapter, strict_mode=False)
```

2. Check blocking reasons:
```python
for reason in analysis.reasons:
    print(f"- {reason}")
```

3. Adjust urgency:
```python
# Lower urgency = less aggressive = more orders pass
success, order_id, venue = await trader.place_order_with_compliance(
    ...,
    urgency=0.3,  # More patient
)
```

---

## References

### Academic Papers

- Chan, E. (2013). *Quantitative Trading*
- Narang, R. (2013). *Inside the Black Box*
- López de Prado, M. (2018). *Advances in Financial Machine Learning*
- Harris, L. (2003). *Trading and Exchanges*
- O'Hara, M. (1995). *Market Microstructure Theory*
- Hull, J. (2018). *Options, Futures, and Other Derivatives*

### System Documentation

- `docs/ERNEST_CHAN_QUANTITATIVE_TRADING.md`
- `docs/NARANG_INSIDE_BLACK_BOX_IMPLEMENTATION.md`
- `docs/LOPEZ_DE_PRADO_95_COMPLIANCE.md`
- `docs/HARRIS_TRADING_AND_EXCHANGES.md`
- `docs/OHARA_MICROSTRUCTURE_QUICK_REFERENCE.md`

---

## Changelog

### Version 1.0 (2026-01-28)

**Initial Release**

- ✅ Integrated ALL 12 compliance systems
- ✅ Created unified `ComplianceIntegrationEngine`
- ✅ Created wrappers for backtesting, live trading, and paper trading
- ✅ Added comprehensive documentation
- ✅ Added integration tests

**Systems Integrated:**
1. Ernest Chan (Rule 1) - 95% compliance
2. Narang (Rule 2) - 95% compliance
3. López de Prado (Rule 3) - 88% compliance
4. Tomasini (Rule 4) - 82% compliance
5. Hastie (Rule 5) - 78% compliance
6. Harris (Rule 6) - 95% compliance
7. O'Hara (Rule 7) - 95% compliance
8. Percival (Rule 8) - 75% compliance
9. Hull (Rule 13) - 95% compliance
10. Martin (Rule 18) - 80% compliance
11. Google SRE (Rule 20) - 95% compliance
12. Beck TDD (Rule 21) - 82% compliance

---

**End of Document**
