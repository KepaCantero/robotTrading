# Harris "Trading and Exchanges" Implementation Guide

## Overview

This document describes the implementation of Larry Harris's market microstructure theories from "Trading and Exchanges" (2003). The implementation covers order book simulation, market mechanics, trading costs, and exchange behavior.

**Compliance Target: 95%**

---

## 1. Order Book Simulation (`app/simulation/order_book.py`)

### Key Concepts from Harris Chapter 3-4

- **Price-Time Priority**: Orders matched FIFO at each price level
- **Limit Order Book**: Continuous double auction mechanism
- **Depth and Liquidity**: Track available quantity at each price level

### Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `Order` | Represents a trading order | `fill()`, `cancel()`, `is_marketable` |
| `PriceLevel` | Orders at a single price | `add_order()`, `remove_order()`, `get_quantity()` |
| `LimitOrderBook` | Complete order book | `submit_order()`, `cancel_order()`, `get_snapshot()` |
| `Trade` | Executed trade record | N/A |

### Usage Example

```python
from app.simulation.order_book import create_limit_order_book, Order, OrderSide, OrderType
from decimal import Decimal

# Create order book
book = create_limit_order_book("AAPL", tick_size=0.01)

# Submit limit orders
buy_order = Order(
    order_id="buy_001",
    symbol="AAPL",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=Decimal("100"),
    price=Decimal("150.00"),
)
trades = book.submit_order(buy_order)

# Get snapshot
snapshot = book.get_snapshot(depth=10)
print(f"Best bid: {snapshot.best_bid}, Best ask: {snapshot.best_ask}")
print(f"Spread: {snapshot.spread}, Mid: {snapshot.mid_price}")
```

---

## 2. Market Mechanics (`app/simulation/market_mechanics.py`)

### Key Concepts from Harris Chapter 4-5

- **Call Auctions**: Opening/closing auctions with volume maximization
- **Continuous Trading**: Immediate order matching during regular hours
- **Trading Sessions**: Pre-market, regular, post-market periods
- **Market Phases**: State transitions throughout trading day

### Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `AuctionMechanism` | Call auction execution | `submit_order()`, `execute_auction()` |
| `ContinuousTrading` | Continuous double auction | `submit_order()`, `calculate_vwap()` |
| `MarketMechanicsEngine` | Complete session management | `transition_to()`, `submit_order()` |

### Usage Example

```python
from app.simulation.market_mechanics import create_market_mechanics_engine
from app.simulation.order_book import Order, OrderSide, OrderType
from decimal import Decimal

# Create engine
engine = create_market_mechanics_engine("AAPL", open_time=(9, 30), close_time=(16, 0))

# Transition to opening auction
engine.transition_to(MarketPhase.OPENING_AUCTION)

# Submit auction orders
for i in range(5):
    buy = Order(
        order_id=f"buy_{i}",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("100"),
        price=Decimal(f"150.{i:02d}"),
    )
    engine.submit_order(buy)

# Execute auction
result = engine.execute_opening_auction()
print(f"Auction price: {result.auction_price}, Volume: {result.total_volume}")

# Transition to continuous trading
engine.transition_to(MarketPhase.CONTINUOUS_TRADING)
```

---

## 3. Exchange Simulation (`app/simulation/exchange.py`)

### Key Concepts from Harris Chapter 4-6

- **Order Matching Engine**: Price-time priority matching
- **Market Makers**: Liquidity provision with inventory management
- **Execution Quality**: Metrics for evaluating trade execution
- **Spread Strategies**: Fixed, adaptive, inventory-based quoting

### Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `OrderMatchingEngine` | Core matching logic | `submit_order()`, `get_execution_quality()` |
| `MarketMakerStrategy` | Simulated market maker | `calculate_spread()`, `should_quote()` |
| `Exchange` | Complete exchange | `submit_order()`, `get_market_maker_quotes()` |

### Usage Example

```python
from app.simulation.exchange import create_exchange
from app.simulation.order_book import Order, OrderSide, OrderType
from decimal import Decimal

# Create exchange with market makers
exchange = create_exchange("NYSE", "AAPL", num_market_makers=3)

# Submit order
order = Order(
    order_id="order_001",
    symbol="AAPL",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=Decimal("1000"),
    price=Decimal("150.00"),
)
executions = exchange.submit_order(order)

# Get market maker quotes
quotes = exchange.get_market_maker_quotes()
for bid, ask, size in quotes:
    print(f"Quote: {bid} - {ask} ({size} shares)")

# Get statistics
stats = exchange.get_execution_statistics()
print(f"Total trades: {stats['total_trades']}, VWAP: {stats['vwap']}")
```

---

## 4. Trading Costs Analysis (`app/simulation/trading_costs.py`)

### Key Concepts from Harris Chapter 8-9

- **Bid-Ask Spread**: Explicit cost of crossing spread
- **Market Impact**: Price movement from order size
- **Timing Risk**: Uncertainty from execution delay
- **Implementation Shortfall**: Total execution cost metric

### Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `MarketImpactModel` | Impact calculation | `calculate_impact()` |
| `BidAskSpreadAnalyzer` | Spread analysis | `get_spread_statistics()` |
| `TimingRiskCalculator` | Timing risk | `calculate_timing_risk()` |
| `TradingCostAnalyzer` | Comprehensive analysis | `analyze_execution()`, `evaluate_execution_quality()` |

### Usage Example

```python
from app.simulation.trading_costs import create_trading_cost_analyzer, ImpactModel
from decimal import Decimal

# Create analyzer
analyzer = create_trading_cost_analyzer(
    impact_model=ImpactModel.SQUARE_ROOT,
    daily_volume=1_000_000,
)

# Analyze execution
cost = analyzer.analyze_execution(
    symbol="AAPL",
    side="BUY",
    quantity=Decimal("5000"),
    execution_price=Decimal("150.50"),
    benchmark_price=Decimal("150.00"),
    commission=Decimal("10.00"),
    bid_at_arrival=Decimal("149.90"),
    ask_at_arrival=Decimal("150.10"),
    adv=1_000_000,
    volatility=0.2,
)

print(f"Total cost: {cost.total_cost_bps:.2f} bps")
print(f"Components: {cost.components}")
print(f"Implementation shortfall: {cost.implementation_shortfall:.2f} bps")

# Evaluate quality
quality = analyzer.evaluate_execution_quality(cost, fill_rate=Decimal("100"))
print(f"Execution score: {quality.execution_score:.1f}/100")
```

---

## 5. Market Microstructure (`app/simulation/microstructure.py`)

### Key Concepts from Harris Chapter 10-11

- **Order Flow Analysis**: Predicting price movements from flow
- **Market Depth**: Liquidity at multiple price levels
- **Liquidity Provision**: Market maker strategies
- **Order Imbalance**: Short-term price indicator

### Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `OrderFlowAnalyzer` | Flow analysis | `calculate_order_imbalance()`, `calculate_flow_toxicity()` |
| `MarketDepthAnalyzer` | Depth analysis | `analyze_depth()`, `estimate_price_impact()` |
| `LiquidityProvider` | LP strategy | `calculate_quotes()`, `should_provide_liquidity()` |
| `MarketMicrostructureAnalyzer` | Complete analysis | `get_comprehensive_metrics()` |

### Usage Example

```python
from app.simulation.microstructure import create_market_microstructure_analyzer
from app.simulation.order_book import create_limit_order_book

# Create analyzer
book = create_limit_order_book("AAPL")
analyzer = create_market_microstructure_analyzer("AAPL", book)

# Update with market data
# ... add orders and trades ...

# Get comprehensive metrics
metrics = analyzer.get_comprehensive_metrics()

print(f"Liquidity regime: {metrics.liquidity_regime.value}")
print(f"Flow toxicity: {metrics.flow_toxicity:.2f}")
print(f"Order imbalance: {metrics.order_imbalance.normalized_imbalance:.2f}")
print(f"Depth: {metrics.market_depth['total_depth']:.0f} shares")

# Check if conditions are favorable
if metrics.liquidity_regime == LiquidityRegime.HIGH and not metrics.is_toxic:
    print("Favorable conditions for trading")
```

---

## Key Metrics Reference

### Market Quality Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Bid-Ask Spread** | Ask - Bid | Lower = more liquid |
| **Relative Spread** | (Ask - Bid) / Mid | As % of mid price |
| **Order Imbalance** | (BuyVol - SellVol) / Total | +1 = all buys, -1 = all sells |
| **Flow Toxicity** | Correlation(flow, future price) | >0.6 = informed trading |
| **Market Depth** | Sum(quantity at all levels) | Higher = more liquid |
| **Price Impact** | ΔPrice / Price due to trade | Higher = less liquid |

### Execution Quality Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Effective Spread** | 2 \* \|Exec - Mid\| / Mid | Actual spread paid |
| **Implementation Shortfall** | (DecisionPrice - ExecPrice) / DecisionPrice | Total cost |
| **Price Improvement** | LimitPrice - ExecPrice | Positive = got better price |
| **Fill Rate** | FilledQty / OrderQty | 100% = complete fill |

---

## Testing

All modules include comprehensive unit tests:

```bash
# Run all Harris-related tests
pytest tests/unit/simulation/ -v

# Run specific module tests
pytest tests/unit/simulation/test_order_book.py -v
pytest tests/unit/simulation/test_market_mechanics.py -v
pytest tests/unit/simulation/test_trading_costs.py -v
pytest tests/unit/simulation/test_microstructure.py -v
```

---

## Integration Example

```python
from app.simulation import (
    create_limit_order_book,
    create_market_mechanics_engine,
    create_trading_cost_analyzer,
    create_market_microstructure_analyzer,
    create_exchange,
)
from app.simulation.order_book import Order, OrderSide, OrderType
from decimal import Decimal

# Setup
symbol = "AAPL"
book = create_limit_order_book(symbol, tick_size=0.01)
engine = create_market_mechanics_engine(symbol)
cost_analyzer = create_trading_cost_analyzer(ImpactModel.SQUARE_ROOT, 1_000_000)
micro_analyzer = create_market_microstructure_analyzer(symbol, book)
exchange = create_exchange("SIMULATED", symbol)

# Trading day simulation
engine.transition_to(MarketPhase.OPENING_AUCTION)
# ... submit auction orders ...
result = engine.execute_opening_auction()
print(f"Opening: {result.auction_price}")

engine.transition_to(MarketPhase.CONTINUOUS_TRADING)

# Execute a trade
order = Order(
    order_id="trade_001",
    symbol=symbol,
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=Decimal("1000"),
)
executions = exchange.submit_order(order)

# Analyze cost
cost = cost_analyzer.analyze_execution(
    symbol=symbol,
    side="BUY",
    quantity=Decimal("1000"),
    execution_price=executions[0].price,
    benchmark_price=book.mid_price or Decimal("150.00"),
)
print(f"Cost: {cost.total_cost_bps:.2f} bps")

# Check microstructure
metrics = micro_analyzer.get_comprehensive_metrics()
print(f"Regime: {metrics.liquidity_regime.value}, Toxicity: {metrics.flow_toxicity:.2f}")
```

---

## References

- Harris, L. (2003). *Trading and Exchanges: Market Microstructure for Practitioners*. Oxford University Press.
  - Chapter 3: Orders and Order Properties
  - Chapter 4: Market Structure
  - Chapter 5: Market Quality
  - Chapter 6: Dealer Markets
  - Chapter 8: Trading Costs
  - Chapter 9: Trading Cost Evaluation
  - Chapter 10: Market Information and Price Discovery
  - Chapter 11: Liquidity and Liquidity Risk

---

## Quick Reference Factory Functions

| Function | Returns | Purpose |
|----------|---------|---------|
| `create_limit_order_book()` | `LimitOrderBook` | Create order book |
| `create_market_mechanics_engine()` | `MarketMechanicsEngine` | Create session manager |
| `create_exchange()` | `Exchange` | Create simulated exchange |
| `create_trading_cost_analyzer()` | `TradingCostAnalyzer` | Create cost analyzer |
| `create_market_microstructure_analyzer()` | `MarketMicrostructureAnalyzer` | Create micro analyzer |
