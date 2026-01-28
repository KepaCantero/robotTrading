# Harris Rule 6 Integration - Quick Start

## Overview

The `HarrisMicrostructureIntegrator` provides a unified interface for all 10 Harris "Trading and Exchanges" rules. It combines order book analysis, market impact estimation, dark pool routing, and execution quality evaluation into a single, easy-to-use API.

## Quick Start

### 1. Get the Integrator

```python
from app.engines.execution_engine.microstructure.harris_integration import get_harris_integrator

integrator = get_harris_integrator()
```

### 2. Pre-Trade Check

```python
from decimal import Decimal
from app.engines.execution_engine.microstructure.order_book_analyzer import OrderBookSnapshot, OrderBookLevel

# Create order book snapshot
order_book = OrderBookSnapshot(
    symbol="AAPL",
    timestamp=pd.Timestamp.now(),
    bids=[
        OrderBookLevel(price=Decimal("150.00"), size=Decimal("1000")),
        # ... more levels
    ],
    asks=[
        OrderBookLevel(price=Decimal("150.01"), size=Decimal("1000")),
        # ... more levels
    ],
)

# Run pre-trade check
result = integrator.pre_trade_check(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    current_price=Decimal("150.00"),
    order_book=order_book,
    adv=Decimal("1000000"),  # Average daily volume
)

# Check results
if result.can_execute:
    print(f"Execute at {result.recommended_venue}")
    print(f"Use {result.recommended_order_type} order")
    print(f"Limit price: {result.recommended_limit_price}")
    print(f"Estimated cost: {result.estimated_cost_bps:.2f} bps")
else:
    print(f"Cannot execute: {result.reasons}")
```

### 3. Post-Trade Analysis

```python
from datetime import datetime, timedelta

analysis = integrator.analyze_execution(
    order_id="order_001",
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("100"),
    execution_price=Decimal("150.25"),
    signal_price=Decimal("150.00"),
    signal_time=datetime.now() - timedelta(minutes=10),
    submission_time=datetime.now() - timedelta(minutes=5),
    execution_time=datetime.now(),
    arrival_price=Decimal("150.10"),
    decision_price=Decimal("150.00"),
    nbbo_at_execution=(Decimal("150.20"), Decimal("150.30")),
)

print(f"Implementation shortfall: {analysis.implementation_shortfall_bps:.2f} bps")
print(f"Execution quality: {analysis.execution_quality_score:.1f}/100")
print(f"Price improvement: {analysis.price_improvement_bps:.2f} bps")
```

## Individual Rules

### Rule 6.1: Order Book Depth

```python
analysis = integrator.analyze_order_book_depth(
    order_book=order_book,
    order_size=Decimal("100"),
)

print(f"Liquidity score: {analysis['liquidity_score']:.1f}/100")
print(f"Spread: {analysis['spread_bps']:.2f} bps")
print(f"Can execute immediately: {analysis['can_execute_immediately']}")
```

### Rule 6.2: Bid-Ask Bounce Removal

```python
import pandas as pd

# df has 'bid', 'ask', 'close' columns
cleaned_prices = integrator.remove_bid_ask_bounce(
    df=df,
    bid_col="bid",
    ask_col="ask",
    last_col="close",
)
```

### Rule 6.3: Timing Cost

```python
# Record signal time
integrator.record_signal_time("order_001", datetime.now())

# Calculate timing cost later
timing_cost = integrator.calculate_timing_cost(
    order_id="order_001",
    execution_price=Decimal("150.25"),
    signal_price=Decimal("150.00"),
    execution_time=datetime.now(),
)
```

### Rule 6.4: Market Impact

```python
impact = integrator.estimate_market_impact(
    symbol="AAPL",
    order_size=Decimal("10000"),
    adv=Decimal("1000000"),
    volatility=0.2,
    price=Decimal("150.00"),
)

print(f"Permanent impact: {impact.permanent_impact_bps:.2f} bps")
print(f"Temporary impact: {impact.temporary_impact_bps:.2f} bps")
print(f"Total impact: {impact.total_impact_bps:.2f} bps")
```

### Rule 6.5: Quote Stuffing Detection

```python
is_stuffing = integrator.detect_quote_stuffing(
    symbol="AAPL",
    current_time=datetime.now(),
    window_seconds=10,
    threshold_quotes_per_second=100.0,
)

if is_stuffing:
    print("Quote stuffing detected - DO NOT TRADE")
```

### Rule 6.6: Limit Price Optimization

```python
optimal_price = integrator.calculate_optimal_limit_price(
    side="BUY",
    current_bid=Decimal("150.00"),
    current_ask=Decimal("150.01"),
    urgency=0.5,  # 0 = patient, 1 = urgent
)
```

### Rule 6.7: Dark Pool Routing

```python
decision = integrator.should_use_dark_pool(
    order_size=Decimal("200000"),
    adv=Decimal("1000000"),
    order_value_usd=Decimal("30000000"),
    information_leakage_risk="HIGH",
)

if decision.use_dark_pool:
    print(f"Use dark pool: {decision.reason}")
    print(f"Venue allocation: {decision.venue_allocation}")
```

### Rule 6.8: Liquidity Validation

```python
validation = integrator.validate_liquidity_assumption(
    order_size=Decimal("10000"),
    adv=Decimal("1000000"),
    max_participation=0.20,
)

if validation["valid"]:
    print(f"Participation rate: {validation['participation_rate']:.1%}")
else:
    print(f"Warning: {validation['warnings']}")
```

### Rule 6.10: Execution Quality

```python
quality = integrator.evaluate_execution_quality(
    executions=executions_list,
    nbbo_snapshot={"AAPL": (Decimal("150.20"), Decimal("150.30"))},
)

print(f"Average improvement vs NBBO: {quality['avg_improvement_bps']:.2f} bps")
print(f"Percentage improved: {quality['pct_improved']:.1%}")
```

## Test Coverage

Run the comprehensive test suite:

```bash
source .venv/bin/activate
python -m pytest tests/unit/engines/execution_engine/microstructure/test_harris_integration.py -v
```

All 20 tests should pass, covering:
- Integrator initialization and singleton pattern
- All 10 Harris rules individually
- Comprehensive pre-trade checks
- Post-trade execution analysis

## Files

- **Implementation**: `/app/engines/execution_engine/microstructure/harris_integration.py`
- **Tests**: `/tests/unit/engines/execution_engine/microstructure/test_harris_integration.py`
- **Report**: `/HARRIS_INTEGRATION_FIX_REPORT.md`
- **Quick Reference**: `/HARRIS_QUICK_REFERENCE.md`
