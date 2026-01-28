# Crypto Momentum Strategy

A momentum strategy optimized for cryptocurrency assets, accounting for their unique characteristics.

## Overview

Crypto markets differ significantly from traditional markets:

- **24/7 trading** - No market close, continuous price discovery
- **High volatility** - Much larger swings than stocks (60-120% annual)
- **Lower liquidity** - Especially in smaller cap tokens
- **Bitcoin correlation** - Most crypto assets follow BTC price movements
- **Social sentiment impact** - Retail and social media drive prices

## Strategy Components

### 1. CryptoMomentumStrategy
Main strategy implementation that:
- Generates momentum signals for crypto assets
- Adjusts for volatility and BTC correlation
- Implements position sizing limits
- Provides 24/7 trading awareness

### 2. CryptoScreener
Screens crypto assets based on:
- **Market cap** - Minimum market cap to avoid micro-cap scams
- **Liquidity** - Volume/market cap ratio and exchange listings
- **Exchange listing** - Must trade on major exchanges (Binance, Coinbase, etc.)
- **Volatility** - Configurable maximum volatility threshold

### 3. CryptoIndicators
Crypto-specific technical indicators:
- **NVT Ratio** - Network Value to Transactions ratio
- **Mayer Multiple** - For Bitcoin valuation
- **Fear & Greed Index** - Market sentiment indicator
- **Relative Strength** - Asset performance vs BTC
- **Network Health Score** - On-chain metrics

### 4. CryptoPortfolioConstructor
Builds crypto momentum portfolios with:
- **BTC core holding** - 40-60% fixed allocation
- **Altcoin selection** - Remaining capital by momentum score
- **Position sizing** - Based on liquidity and volatility
- **Rebalancing** - Threshold-based to minimize fees

## Configuration

```python
from app.strategies.crypto_momentum import CryptoMomentumStrategy

config = {
    "name": "CryptoMomentumStrategy",
    "description": "Crypto momentum strategy with BTC adjustment",
    "version": "1.0.0",

    # Momentum parameters
    "lookback_days": 90,
    "volatility_adjustment": True,
    "btc_adjustment": True,

    # Portfolio parameters
    "max_position_size": 0.10,  # 10% max per position
    "btc_weight": 0.50,  # 50% BTC allocation
    "portfolio_size": 10,  # Max 10 positions
    "rebalance_threshold": 0.05,  # 5% deviation triggers rebalance

    # Screening parameters
    "min_market_cap": 1000000000,  # $1B minimum
    "min_daily_volume": 10000000,  # $10M minimum daily volume
    "min_liquidity_score": 50,  # Minimum liquidity score
    "max_volatility": 150,  # Maximum 150% annual volatility

    # Exchange requirements
    "required_exchanges": ["binance", "coinbase"],

    # Advanced features
    "use_on_chain_metrics": False,
    "social_sentiment_weight": 0.0,
}

strategy = CryptoMomentumStrategy(config)
```

## Usage Example

```python
from decimal import Decimal
from app.strategies.crypto_momentum import (
    CryptoMomentumStrategy,
    CryptoAsset,
    CryptoAssetType,
    CryptoExchange,
)
from app.models.market_data import Quote

# Initialize strategy
strategy = CryptoMomentumStrategy({
    "lookback_days": 90,
    "btc_weight": "0.50",
    "portfolio_size": 10,
})

# Create crypto assets
btc = CryptoAsset(
    symbol="BTC",
    name="Bitcoin",
    asset_type=CryptoAssetType.BITCOIN,
    market_cap=Decimal("500000000000"),
    liquidity_score=Decimal("95"),
    volatility_90d=Decimal("65"),
    avg_daily_volume=Decimal("20000000000"),
    exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
    current_price=Decimal("45000"),
)

eth = CryptoAsset(
    symbol="ETH",
    name="Ethereum",
    asset_type=CryptoAssetType.ETHEREUM,
    market_cap=Decimal("200000000000"),
    liquidity_score=Decimal("90"),
    volatility_90d=Decimal("85"),
    avg_daily_volume=Decimal("10000000000"),
    exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
    current_price=Decimal("3000"),
)

# Set universe
strategy.set_universe([btc, eth])

# Update momentum scores
strategy.update_momentum_scores()

# Construct portfolio
portfolio = strategy.construct_portfolio(
    total_capital=Decimal("100000")
)

# Generate signals from market data
quote = Quote(
    symbol="BTC",
    timestamp=datetime.utcnow(),
    bid=Decimal("44990"),
    ask=Decimal("45010"),
    last=Decimal("45000"),
    volume=Decimal("1000000"),
)

signals = strategy.generate_signals(quote)
```

## Key Features

### 1. Volatility-Adjusted Momentum
```python
# Calculate volatility-adjusted momentum score
score = strategy.calculate_momentum_score(
    prices=price_series,
    benchmark_prices=btc_prices,  # Optional
)
```

### 2. BTC Correlation Adjustment
```python
# Calculate beta to Bitcoin
beta = strategy.calculate_crypto_beta(
    asset_returns=asset_returns,
    btc_returns=btc_returns,
)
```

### 3. Liquidity-Based Position Sizing
```python
# Position size adjusted for liquidity
size = constructor.calculate_position_size(
    asset=asset,
    score=80,
    total_capital=Decimal("100000"),
)
```

### 4. Portfolio Rebalancing
```python
# Calculate rebalance trades
trades = constructor.rebalance_portfolio(
    current_portfolio=current,
    target_portfolio=target,
)
```

## Testing

Run tests with:

```bash
# Run all crypto momentum tests
pytest app/tests/strategies/test_crypto_momentum_strategy.py -v

# Run specific test class
pytest app/tests/strategies/test_crypto_momentum_strategy.py::TestCryptoScreener -v

# Run with coverage
pytest app/tests/strategies/test_crypto_momentum_strategy.py --cov=app/strategies/crypto_momentum -v
```

## Risk Management

The strategy implements several risk management features:

1. **Position size limits** - Max 10% per position (configurable)
2. **Volatility caps** - Maximum volatility threshold
3. **Stop loss** - 15% stop loss on positions
4. **Liquidity requirements** - Minimum daily volume and market cap
5. **Exchange listing verification** - Must trade on major exchanges
6. **BTC correlation penalty** - Reduces positions highly correlated with BTC

## Performance Considerations

- **24/7 Trading**: The strategy is designed for continuous monitoring
- **High Volatility**: Position sizes are reduced for high-volatility assets
- **Low Liquidity**: Small-cap tokens have smaller allocations
- **Fees**: Rebalancing threshold minimizes trading fees

## Future Enhancements

Potential improvements:
1. Social sentiment integration (Twitter, Reddit, etc.)
2. On-chain metrics integration (active addresses, transaction counts)
3. Staking yield optimization for PoS tokens
4. DeFi protocol yield farming
5. Options strategies for crypto
6. Cross-exchange arbitrage
7. Machine learning for price prediction

## References

- [Momentum Effect in Crypto Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3194565)
- [Bitcoin Mayer Multiple](https://mayermultiple.info/)
- [NVT Ratio - Willy Woo](https://woobull.com/introducing-nvt-ratio/)
- [Crypto Fear & Greed Index](https://alternative.me/crypto/fear-and-greed-index/)
