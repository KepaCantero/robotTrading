#!/usr/bin/env python
"""
Crypto Momentum Strategy Example

This example demonstrates how to use the CryptoMomentumStrategy:
1. Initialize the strategy with configuration
2. Create a universe of crypto assets
3. Screen assets for eligibility
4. Calculate momentum scores
5. Construct a portfolio
6. Generate trading signals
"""

from decimal import Decimal
from datetime import datetime

import pandas as pd
import numpy as np

from app.strategies.crypto_momentum import (
    CryptoMomentumStrategy,
    CryptoAsset,
    CryptoAssetType,
    CryptoExchange,
)
from app.strategies.registry import StrategyRegistry
from app.models.market_data import Quote


def create_sample_universe():
    """Create a sample universe of crypto assets."""
    assets = [
        # Bitcoin
        CryptoAsset(
            symbol="BTC",
            name="Bitcoin",
            asset_type=CryptoAssetType.BITCOIN,
            market_cap=Decimal("500000000000"),  # $500B
            liquidity_score=Decimal("95"),
            volatility_90d=Decimal("65"),
            avg_daily_volume=Decimal("20000000000"),  # $20B
            exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE, CryptoExchange.KRAKEN],
            btc_correlation=1.0,
            current_price=Decimal("45000"),
            is_eligible=True,
        ),
        # Ethereum
        CryptoAsset(
            symbol="ETH",
            name="Ethereum",
            asset_type=CryptoAssetType.ETHEREUM,
            market_cap=Decimal("200000000000"),  # $200B
            liquidity_score=Decimal("90"),
            volatility_90d=Decimal("85"),
            avg_daily_volume=Decimal("10000000000"),  # $10B
            exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
            btc_correlation=0.75,
            current_price=Decimal("3000"),
            is_eligible=True,
        ),
        # Solana
        CryptoAsset(
            symbol="SOL",
            name="Solana",
            asset_type=CryptoAssetType.L1_BLOCKCHAIN,
            market_cap=Decimal("10000000000"),  # $10B
            liquidity_score=Decimal("75"),
            volatility_90d=Decimal("120"),
            avg_daily_volume=Decimal("500000000"),  # $500M
            exchanges=[CryptoExchange.BINANCE, CryptoExchange.KRAKEN],
            btc_correlation=0.65,
            current_price=Decimal("100"),
            is_eligible=True,
        ),
        # Cardano
        CryptoAsset(
            symbol="ADA",
            name="Cardano",
            asset_type=CryptoAssetType.L1_BLOCKCHAIN,
            market_cap=Decimal("15000000000"),  # $15B
            liquidity_score=Decimal("70"),
            volatility_90d=Decimal("110"),
            avg_daily_volume=Decimal("400000000"),  # $400M
            exchanges=[CryptoExchange.BINANCE],
            btc_correlation=0.70,
            current_price=Decimal("0.50"),
            is_eligible=True,
        ),
        # Polygon
        CryptoAsset(
            symbol="MATIC",
            name="Polygon",
            asset_type=CryptoAssetType.L2_SCALING,
            market_cap=Decimal("8000000000"),  # $8B
            liquidity_score=Decimal("65"),
            volatility_90d=Decimal("130"),
            avg_daily_volume=Decimal("300000000"),  # $300M
            exchanges=[CryptoExchange.BINANCE],
            btc_correlation=0.75,
            current_price=Decimal("0.85"),
            is_eligible=True,
        ),
        # Uniswap
        CryptoAsset(
            symbol="UNI",
            name="Uniswap",
            asset_type=CryptoAssetType.DEFI,
            market_cap=Decimal("5000000000"),  # $5B
            liquidity_score=Decimal("60"),
            volatility_90d=Decimal("125"),
            avg_daily_volume=Decimal("200000000"),  # $200M
            exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
            btc_correlation=0.60,
            current_price=Decimal("6.50"),
            is_eligible=True,
        ),
    ]

    return assets


def generate_sample_prices(initial_price: float, days: int = 100, trend: float = 0.001) -> pd.Series:
    """Generate sample price data for testing."""
    np.random.seed(42)

    # Generate returns with trend
    returns = np.random.normal(trend, 0.05, days)

    # Calculate prices
    log_prices = np.log(initial_price) + np.cumsum(returns)
    prices = np.exp(log_prices)

    # Create date range
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    return pd.Series(prices, index=dates)


def main():
    """Main example function."""
    print("=" * 80)
    print("Crypto Momentum Strategy Example")
    print("=" * 80)
    print()

    # ============================================================================
    # 1. Initialize Strategy
    # ============================================================================
    print("1. Initializing Crypto Momentum Strategy...")
    print("-" * 40)

    config = {
        "name": "CryptoMomentumStrategy",
        "description": "Crypto momentum strategy with BTC adjustment",
        "version": "1.0.0",
        "lookback_days": 90,
        "volatility_adjustment": True,
        "btc_adjustment": True,
        "max_position_size": Decimal("0.10"),
        "btc_weight": Decimal("0.50"),
        "portfolio_size": 10,
        "rebalance_threshold": Decimal("0.05"),
        "min_market_cap": Decimal("1000000000"),
        "min_daily_volume": Decimal("10000000"),
        "min_liquidity_score": Decimal("50"),
        "max_volatility": Decimal("150"),
    }

    strategy = CryptoMomentumStrategy(config)

    print(f"  Strategy: {strategy.name}")
    print(f"  Lookback: {strategy.strategy_config.lookback_days} days")
    print(f"  BTC Weight: {strategy.strategy_config.btc_weight:.1%}")
    print(f"  Max Position: {strategy.strategy_config.max_position_size:.1%}")
    print()

    # ============================================================================
    # 2. Create and Screen Universe
    # ============================================================================
    print("2. Creating and Screening Universe...")
    print("-" * 40)

    universe = create_sample_universe()
    print(f"  Initial universe: {len(universe)} assets")

    strategy.set_universe(universe)

    print(f"  Screened universe: {len(strategy.universe)} assets")
    print(f"  Pass rate: {len(strategy.universe) / len(universe) * 100:.1f}%")
    print()

    # ============================================================================
    # 3. Populate Price History and Calculate Momentum Scores
    # ============================================================================
    print("3. Calculating Momentum Scores...")
    print("-" * 40)

    # Generate price data for each asset
    price_data = {
        "BTC": generate_sample_prices(45000, days=100, trend=0.0005),
        "ETH": generate_sample_prices(3000, days=100, trend=0.0008),
        "SOL": generate_sample_prices(100, days=100, trend=0.0012),
        "ADA": generate_sample_prices(0.50, days=100, trend=0.0006),
        "MATIC": generate_sample_prices(0.85, days=100, trend=0.0010),
        "UNI": generate_sample_prices(6.50, days=100, trend=0.0007),
    }

    # Populate price history
    for asset in strategy.universe:
        if asset.symbol in price_data:
            prices = price_data[asset.symbol]

            for i, (date, price) in enumerate(zip(prices.index, prices)):
                quote = Quote(
                    symbol=asset.symbol,
                    timestamp=date,
                    bid=Decimal(str(price * 0.999)),
                    ask=Decimal(str(price * 1.001)),
                    last=Decimal(str(price)),
                    volume=Decimal("1000000"),
                )
                strategy._update_price_history(asset.symbol, quote)

    # Update momentum scores
    strategy.update_momentum_scores()

    # Display scores
    print("  Momentum Scores:")
    for symbol, score in sorted(
        strategy.momentum_scores.items(),
        key=lambda x: float(x[1].final_score),
        reverse=True,
    ):
        print(f"    {symbol}: {score.final_score:.1f} (confidence: {score.confidence:.1f}%)")
    print()

    # ============================================================================
    # 4. Construct Portfolio
    # ============================================================================
    print("4. Constructing Portfolio...")
    print("-" * 40)

    total_capital = Decimal("100000")
    portfolio = strategy.construct_portfolio(total_capital)

    print(f"  Total Value: ${portfolio.total_value:,.2f}")
    print(f"  Invested: ${portfolio.invested_value:,.2f}")
    print(f"  Cash: ${portfolio.cash:,.2f}")
    print(f"  BTC Weight: {portfolio.btc_weight:.1%}")
    print(f"  Altcoin Weight: {portfolio.altcoin_weight:.1%}")
    print(f"  Expected Volatility: {portfolio.expected_volatility:.1f}%")
    print()

    print("  Positions:")
    for pos in portfolio.positions:
        print(f"    {pos.symbol}: ${pos.value:,.2f} ({pos.weight:.1%}) - {pos.quantity:.4f} units @ ${pos.entry_price:.2f}")
    print()

    # ============================================================================
    # 5. Generate Trading Signals
    # ============================================================================
    print("5. Generating Trading Signals...")
    print("-" * 40)

    # Activate strategy
    strategy.is_active = True

    # Generate signals for each asset
    all_signals = []
    for asset in strategy.universe:
        quote = Quote(
            symbol=asset.symbol,
            timestamp=datetime.utcnow(),
            bid=Decimal(str(asset.current_price * 0.999)),
            ask=Decimal(str(asset.current_price * 1.001)),
            last=asset.current_price,
            volume=asset.avg_daily_volume / 24,  # Hourly volume
        )

        signals = strategy.generate_signals(quote)
        all_signals.extend(signals)

    if all_signals:
        print(f"  Generated {len(all_signals)} signals:")
        for signal in all_signals:
            print(f"    {signal.signal_type.value.upper()} {signal.symbol}")
            print(f"      Strength: {signal.strength.value}")
            print(f"      Confidence: {signal.confidence:.1f}%")
            print(f"      Priority: {signal.priority_score:.1f}")
            print(f"      Price: ${signal.price:.2f}")
    else:
        print("  No signals generated")
    print()

    # ============================================================================
    # 6. Display Portfolio Metrics
    # ============================================================================
    print("6. Portfolio Metrics...")
    print("-" * 40)

    metrics = strategy.get_portfolio_metrics()

    print(f"  Total Positions: {metrics.get('total_positions', 0)}")
    print(f"  Invested Value: ${metrics.get('invested_value', 0):,.2f}")
    print(f"  Cash: ${metrics.get('cash', 0):,.2f}")
    print(f"  Unrealized P&L: ${metrics.get('unrealized_pnl', 0):,.2f}")
    print(f"  Unrealized P&L %: {metrics.get('unrealized_pnl_pct', 0):.2f}%")
    print()

    # ============================================================================
    # 7. Using Strategy Registry
    # ============================================================================
    print("7. Using Strategy Registry...")
    print("-" * 40)

    registry = StrategyRegistry()

    # Load strategy
    loaded_strategy = registry.load_strategy("crypto_momentum", config)
    print(f"  Loaded strategy: {loaded_strategy.name}")

    # Set as active
    registry.set_active_strategy("crypto_momentum")
    print(f"  Active strategy: {registry.get_active_strategy().name}")

    # List available strategies
    available = registry.list_available_strategies()
    print(f"  Available strategies: {len(available)}")
    print()

    print("=" * 80)
    print("Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
