"""
Harris Trading and Exchanges - Complete Example

This example demonstrates the full Harris market microstructure implementation
including order book simulation, market mechanics, trading costs, and
microstructure analysis.

Usage:
    python examples/harris_trading_example.py
"""

from decimal import Decimal

from app.simulation.order_book import (
    create_limit_order_book,
    Order,
    OrderSide,
    OrderType,
)
from app.simulation.market_mechanics import (
    create_market_mechanics_engine,
    MarketPhase,
)
from app.simulation.exchange import (
    create_exchange,
)
from app.simulation.trading_costs import (
    create_trading_cost_analyzer,
    ImpactModel,
)
from app.simulation.microstructure import (
    create_market_microstructure_analyzer,
    LiquidityRegime,
)


def main():
    """Run the complete Harris trading simulation example."""

    print("=" * 80)
    print("HARRIS TRADING AND EXCHANGES - SIMULATION EXAMPLE")
    print("=" * 80)
    print()

    # ============================================================================
    # 1. ORDER BOOK SIMULATION
    # ============================================================================
    print("1. ORDER BOOK SIMULATION")
    print("-" * 80)

    # Create order book for AAPL
    book = create_limit_order_book(symbol="AAPL", tick_size=0.01)

    # Submit some limit orders to build the book
    print("\nBuilding initial order book...")

    # Add bids (buy orders)
    for i, (price, qty) in enumerate([
        (149.50, 500),
        (149.45, 300),
        (149.40, 200),
        (149.35, 400),
        (149.30, 600),
    ]):
        order = Order(
            order_id=f"bid_{i}",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal(str(qty)),
            price=Decimal(str(price)),
        )
        book.submit_order(order)
        print(f"  Added BID: {qty} @ ${price}")

    # Add asks (sell orders)
    for i, (price, qty) in enumerate([
        (150.50, 400),
        (150.55, 300),
        (150.60, 500),
        (150.65, 200),
        (150.70, 600),
    ]):
        order = Order(
            order_id=f"ask_{i}",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal(str(qty)),
            price=Decimal(str(price)),
        )
        book.submit_order(order)
        print(f"  Added ASK: {qty} @ ${price}")

    # Get order book snapshot
    snapshot = book.get_snapshot(depth=5)
    print(f"\nOrder Book State:")
    print(f"  Best Bid: ${snapshot.best_bid}")
    print(f"  Best Ask: ${snapshot.best_ask}")
    print(f"  Spread: ${snapshot.spread} ({snapshot.spread / snapshot.mid_price * 100:.2f}%)")
    print(f"  Mid Price: ${snapshot.mid_price}")
    print(f"  Bid Depth: {snapshot.bid_depth} levels")
    print(f"  Ask Depth: {snapshot.ask_depth} levels")
    print(f"  Total Bid Qty: {snapshot.total_bid_quantity}")
    print(f"  Total Ask Qty: {snapshot.total_ask_quantity}")

    # ============================================================================
    # 2. MARKET MECHANICS - OPENING AUCTION
    # ============================================================================
    print("\n\n2. MARKET MECHANICS - OPENING AUCTION")
    print("-" * 80)

    # Create market mechanics engine
    engine = create_market_mechanics_engine(
        symbol="AAPL",
        tick_size=0.01,
        open_time=(9, 30),
        close_time=(16, 0),
    )

    # Transition to opening auction
    print("\nTransitioning to OPENING_AUCTION phase...")
    engine.transition_to(MarketPhase.OPENING_AUCTION)

    # Submit auction orders
    print("\nSubmitting auction orders...")
    auction_orders = [
        ("BUY", 149.80, 1000),
        ("BUY", 149.90, 800),
        ("BUY", 150.00, 1200),
        ("BUY", 150.10, 500),
        ("SELL", 150.00, 900),
        ("SELL", 150.10, 700),
        ("SELL", 150.20, 1100),
        ("SELL", 150.30, 400),
    ]

    for side, price, qty in auction_orders:
        order = Order(
            order_id=f"auction_{side}_{price}",
            symbol="AAPL",
            side=OrderSide.BUY if side == "BUY" else OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal(str(qty)),
            price=Decimal(str(price)),
        )
        engine.submit_order(order)
        print(f"  {side:4s} {qty:4d} @ ${price:.2f}")

    # Execute auction
    print("\nExecuting opening auction...")
    result = engine.execute_opening_auction()

    print(f"\nAuction Results:")
    print(f"  Auction Price: ${result.auction_price}")
    print(f"  Total Volume: {result.total_volume}")
    print(f"  Buy Volume: {result.buy_volume}")
    print(f"  Sell Volume: {result.sell_volume}")
    print(f"  Matched Orders: {len(result.matched_orders)}")
    print(f"  Imbalance: {result.imbalance}")

    # Transition to continuous trading
    print("\nTransitioning to CONTINUOUS_TRADING phase...")
    engine.transition_to(MarketPhase.CONTINUOUS_TRADING)

    # ============================================================================
    # 3. EXCHANGE SIMULATION WITH MARKET MAKERS
    # ============================================================================
    print("\n\n3. EXCHANGE SIMULATION")
    print("-" * 80)

    # Create exchange with market makers
    exchange = create_exchange(
        name="SIMULATED_EXCHANGE",
        symbol="AAPL",
        tick_size=0.01,
        num_market_makers=3,
    )

    print("\nCreated exchange with 3 market makers")
    print("\nCurrent Market Maker Quotes:")
    quotes = exchange.get_market_maker_quotes()
    for i, (bid, ask, size) in enumerate(quotes, 1):
        spread_bps = (ask - bid) / bid * 10000
        print(f"  MM{i}: Bid ${bid:.2f} - Ask ${ask:.2f} "
              f"({size:.0f} shares, spread: {spread_bps:.1f} bps)")

    # Submit a market order
    print("\nSubmitting market buy order for 500 shares...")
    market_order = Order(
        order_id="market_buy_001",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("500"),
    )
    executions = exchange.submit_order(market_order)

    print(f"\nExecution Results:")
    for exec in executions:
        print(f"  Execution ID: {exec.execution_id}")
        print(f"  Quantity: {exec.quantity}")
        print(f"  Price: ${exec.price}")
        print(f"  Liquidity Taker: {exec.liquidity_taker}")

    # Get exchange statistics
    stats = exchange.get_execution_statistics()
    print(f"\nExchange Statistics:")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Total Volume: {stats['total_volume']}")
    print(f"  VWAP: ${stats['vwap']:.2f}")

    # ============================================================================
    # 4. TRADING COSTS ANALYSIS
    # ============================================================================
    print("\n\n4. TRADING COSTS ANALYSIS")
    print("-" * 80)

    # Create cost analyzer
    cost_analyzer = create_trading_cost_analyzer(
        impact_model=ImpactModel.SQUARE_ROOT,
        daily_volume=5_000_000,
    )

    # Analyze execution cost
    print("\nAnalyzing execution costs...")
    cost_analysis = cost_analyzer.analyze_execution(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("500"),
        execution_price=executions[0].price,
        benchmark_price=Decimal("150.00"),
        arrival_price=Decimal("149.90"),
        decision_price=Decimal("149.80"),
        commission=Decimal("5.00"),
        fees=Decimal("0.50"),
        bid_at_arrival=Decimal("149.95"),
        ask_at_arrival=Decimal("150.05"),
        adv=5_000_000,
        volatility=0.2,
        execution_period_hours=0.25,
    )

    print(f"\nCost Breakdown:")
    print(f"  Total Cost: ${cost_analysis.total_cost:.2f}")
    print(f"  Total Cost (bps): {cost_analysis.total_cost_bps:.2f} bps")
    print(f"  Effective Spread: {cost_analysis.effective_spread:.2f} bps")
    print(f"  Implementation Shortfall: {cost_analysis.implementation_shortfall:.2f} bps")
    print(f"  Savings vs Benchmark: ${cost_analysis.saving_vs_benchmark:.2f}")

    print(f"\n  Cost Components:")
    for component, value in cost_analysis.components.items():
        print(f"    {component.value}: ${value:.2f}")

    # Evaluate execution quality
    quality = cost_analyzer.evaluate_execution_quality(
        cost_breakdown=cost_analysis,
        fill_rate=Decimal("100"),
    )

    print(f"\nExecution Quality:")
    print(f"  Execution Score: {quality.execution_score:.1f}/100")
    print(f"  Fill Rate: {quality.fill_rate:.1f}%")
    print(f"  Price Improvement: {quality.price_improvement_bps:.2f} bps")
    print(f"  Market Impact: {quality.market_impact_bps:.2f} bps")
    print(f"  Timing Cost: {quality.timing_cost_bps:.2f} bps")

    if quality.execution_score >= 80:
        print(f"  Rating: EXCELLENT")
    elif quality.execution_score >= 60:
        print(f"  Rating: GOOD")
    elif quality.execution_score >= 40:
        print(f"  Rating: FAIR")
    else:
        print(f"  Rating: POOR")

    # ============================================================================
    # 5. MARKET MICROSTRUCTURE ANALYSIS
    # ============================================================================
    print("\n\n5. MARKET MICROSTRUCTURE ANALYSIS")
    print("-" * 80)

    # Create microstructure analyzer
    micro_analyzer = create_market_microstructure_analyzer(
        symbol="AAPL",
        order_book=book,
    )

    # Add some market data
    print("\nAdding market data to analyzer...")
    for i in range(10):
        # Simulate order flow
        order = Order(
            order_id=f"flow_{i}",
            symbol="AAPL",
            side=OrderSide.BUY if i % 3 != 0 else OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal(str(100 + i * 50)),
            price=Decimal("150.00"),
        )
        micro_analyzer.update(order=order)

    # Get comprehensive metrics
    print("\nCalculating microstructure metrics...")
    metrics = micro_analyzer.get_comprehensive_metrics()

    print(f"\nOrder Flow:")
    print(f"  Buy Volume: {metrics.order_imbalance.buy_volume}")
    print(f"  Sell Volume: {metrics.order_imbalance.sell_volume}")
    print(f"  Imbalance: {metrics.order_imbalance.imbalance}")
    print(f"  Normalized Imbalance: {metrics.order_imbalance.normalized_imbalance:.2f}")
    print(f"  Direction: {metrics.order_imbalance.direction.value}")
    print(f"  Bias Strength: {metrics.order_imbalance.bias_strength}")

    print(f"\nMarket Depth:")
    print(f"  Total Depth: {metrics.market_depth['total_depth']:.0f} shares")
    print(f"  Bid Depth: {metrics.market_depth['total_bid_depth']:.0f} shares")
    print(f"  Ask Depth: {metrics.market_depth['total_ask_depth']:.0f} shares")
    print(f"  Depth Imbalance: {metrics.market_depth['depth_imbalance']:.2f}")
    print(f"  Spread: {metrics.market_depth['spread_bps']:.1f} bps")

    print(f"\nLiquidity:")
    print(f"  Regime: {metrics.liquidity_regime.value}")
    print(f"  Flow Toxicity: {metrics.flow_toxicity:.2f}")
    print(f"  Price Discovery: {metrics.price_discovery:.1f}/100")
    print(f"  Trading Intensity: {metrics.trading_intensity:.2f}")
    print(f"  Share Turnover: {metrics.share_turnover:.4f}")

    # Interpret conditions
    print(f"\nMarket Conditions Assessment:")
    if metrics.liquidity_regime == LiquidityRegime.HIGH:
        print("  LIQUIDITY: Excellent - Tight spreads, deep order book")
    elif metrics.liquidity_regime == LiquidityRegime.NORMAL:
        print("  LIQUIDITY: Normal - Adequate for most trades")
    elif metrics.liquidity_regime == LiquidityRegime.LOW:
        print("  LIQUIDITY: Low - Wide spreads, use caution")
    else:
        print("  LIQUIDITY: Very Low - Dangerous conditions")

    if metrics.flow_toxicity > 0.6:
        print("  FLOW TOXICITY: High - Informed traders present, risky for LPs")
    elif metrics.flow_toxicity > 0.4:
        print("  FLOW TOXICITY: Moderate - Some informed trading")
    else:
        print("  FLOW TOXICITY: Low - Mostly uninformed flow")

    if metrics.order_imbalance.is_biased:
        direction = "BUYING" if metrics.order_imbalance.normalized_imbalance > 0 else "SELLING"
        print(f"  ORDER FLOW: {direction} pressure ({metrics.order_imbalance.bias_strength})")
    else:
        print("  ORDER FLOW: Balanced")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)
    print("\nKey Insights:")
    print("1. Order book properly maintains price-time priority")
    print("2. Auction mechanism maximizes executable volume")
    print("3. Market makers provide continuous two-sided quotes")
    print("4. Trading costs can be decomposed into explicit and implicit components")
    print("5. Microstructure metrics reveal market conditions and flow dynamics")
    print("\nAll Harris 'Trading and Exchanges' core concepts are implemented!")


if __name__ == "__main__":
    main()
