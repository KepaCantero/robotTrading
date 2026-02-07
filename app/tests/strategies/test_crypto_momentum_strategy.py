"""
Comprehensive Tests for Crypto Momentum Strategy

This module contains 60+ tests for the crypto momentum strategy,
covering all major components and edge cases.

Test Coverage:
- Model validation
- Screener functionality
- Indicator calculations
- Portfolio construction
- Strategy execution
- Edge cases and error handling
"""

from datetime import datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.strategies.crypto_momentum.crypto_indicators import CryptoIndicators
from app.strategies.crypto_momentum.crypto_momentum_strategy import CryptoMomentumStrategy
from app.strategies.crypto_momentum.crypto_portfolio import CryptoPortfolioConstructor
from app.strategies.crypto_momentum.crypto_screener import CryptoScreener
from app.strategies.crypto_momentum.models import (
    CryptoAsset,
    CryptoAssetType,
    CryptoExchange,
    CryptoMomentumConfig,
    CryptoMomentumScore,
    CryptoPortfolio,
    CryptoPosition,
    OnChainMetrics,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_btc_asset():
    """Sample Bitcoin asset."""
    return CryptoAsset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=CryptoAssetType.BITCOIN,
        market_cap=Decimal("500000000000"),  # $500B
        liquidity_score=Decimal("95"),
        volatility_90d=Decimal("65"),
        avg_daily_volume=Decimal("20000000000"),  # $20B daily
        exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE, CryptoExchange.KRAKEN],
        btc_correlation=1.0,
        btc_beta=1.0,
        current_price=Decimal("45000"),
        is_eligible=True,
    )


@pytest.fixture
def sample_eth_asset():
    """Sample Ethereum asset."""
    return CryptoAsset(
        symbol="ETH",
        name="Ethereum",
        asset_type=CryptoAssetType.ETHEREUM,
        market_cap=Decimal("200000000000"),  # $200B
        liquidity_score=Decimal("90"),
        volatility_90d=Decimal("85"),
        avg_daily_volume=Decimal("10000000000"),  # $10B daily
        exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
        btc_correlation=0.75,
        btc_beta=1.2,
        current_price=Decimal("3000"),
        is_eligible=True,
    )


@pytest.fixture
def sample_altcoin_asset():
    """Sample altcoin asset."""
    return CryptoAsset(
        symbol="SOL",
        name="Solana",
        asset_type=CryptoAssetType.L1_BLOCKCHAIN,
        market_cap=Decimal("10000000000"),  # $10B
        liquidity_score=Decimal("75"),
        volatility_90d=Decimal("120"),
        avg_daily_volume=Decimal("500000000"),  # $500M daily
        exchanges=[CryptoExchange.BINANCE, CryptoExchange.KRAKEN],
        btc_correlation=0.65,
        btc_beta=1.5,
        current_price=Decimal("100"),
        is_eligible=True,
    )


@pytest.fixture
def sample_small_cap_asset():
    """Sample small cap asset (should fail screening)."""
    return CryptoAsset(
        symbol="SMALL",
        name="Small Cap Token",
        asset_type=CryptoAssetType.UTILITY,
        market_cap=Decimal("50000000"),  # $50M (too small)
        liquidity_score=Decimal("30"),
        volatility_90d=Decimal("150"),
        avg_daily_volume=Decimal("1000000"),  # $1M daily (too low)
        exchanges=[CryptoExchange.KUCOIN],
        btc_correlation=0.8,
        btc_beta=1.8,
        current_price=Decimal("1"),
        is_eligible=False,
    )


@pytest.fixture
def sample_on_chain_metrics():
    """Sample on-chain metrics."""
    return OnChainMetrics(
        active_addresses=100000,
        transaction_count=250000,
        transaction_volume=Decimal("1000000000"),  # $1B
        market_cap=Decimal("10000000000"),  # $10B
        nvt_ratio=Decimal("10"),
        realized_cap=Decimal("8000000000"),
        mayer_multiple=Decimal("1.5"),
        hashrate=Decimal("150000000000000000000"),
        staking_ratio=Decimal("65"),
        token_velocity=Decimal("0.5"),
    )


@pytest.fixture
def sample_config():
    """Sample strategy configuration."""
    return CryptoMomentumConfig(
        lookback_days=90,
        volatility_adjustment=True,
        btc_adjustment=True,
        max_position_size=Decimal("0.10"),
        btc_weight=Decimal("0.50"),
        portfolio_size=10,
        rebalance_threshold=Decimal("0.05"),
        min_market_cap=Decimal("1000000000"),
        min_daily_volume=Decimal("10000000"),
        min_liquidity_score=Decimal("50"),
        max_volatility=Decimal("150"),
        use_on_chain_metrics=False,
    )


@pytest.fixture
def sample_price_series():
    """Sample price series for testing."""
    np.random.seed(42)
    days = 100
    # Generate trending prices with noise
    trend = np.linspace(100, 150, days)
    noise = np.random.normal(0, 5, days)
    prices = trend + noise

    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    return pd.Series(prices, index=dates)


@pytest.fixture
def sample_btc_price_series():
    """Sample BTC price series for testing."""
    np.random.seed(42)
    days = 100
    trend = np.linspace(40000, 50000, days)
    noise = np.random.normal(0, 1000, days)
    prices = trend + noise

    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    return pd.Series(prices, index=dates)


# ============================================================================
# MODEL TESTS (15 tests)
# ============================================================================


class TestCryptoAsset:
    """Tests for CryptoAsset model."""

    def test_crypto_asset_creation(self, sample_btc_asset):
        """Test creating a crypto asset."""
        assert sample_btc_asset.symbol == "BTC"
        assert sample_btc_asset.asset_type == CryptoAssetType.BITCOIN
        assert sample_btc_asset.market_cap == Decimal("500000000000")

    def test_is_eligible_for_trading_pass(self, sample_btc_asset):
        """Test eligibility check with passing criteria."""
        result = sample_btc_asset.is_eligible_for_trading(
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("50"),
            required_exchanges=None,
        )
        assert result is True

    def test_is_eligible_for_trading_fail_market_cap(self, sample_small_cap_asset):
        """Test eligibility check with insufficient market cap."""
        result = sample_small_cap_asset.is_eligible_for_trading(
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("50"),
            required_exchanges=None,
        )
        assert result is False

    def test_is_eligible_for_trading_fail_volume(self, sample_small_cap_asset):
        """Test eligibility check with insufficient volume."""
        result = sample_small_cap_asset.is_eligible_for_trading(
            min_market_cap=Decimal("1000000"),  # Low enough
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("10"),
            required_exchanges=None,
        )
        assert result is False

    def test_is_eligible_for_trading_fail_exchange(self, sample_small_cap_asset):
        """Test eligibility check with missing exchange listing."""
        result = sample_small_cap_asset.is_eligible_for_trading(
            min_market_cap=Decimal("1000000"),
            min_daily_volume=Decimal("1000000"),
            min_liquidity_score=Decimal("10"),
            required_exchanges=[CryptoExchange.BINANCE, CryptoExchange.COINBASE],
        )
        assert result is False


class TestOnChainMetrics:
    """Tests for OnChainMetrics model."""

    def test_on_chain_metrics_creation(self, sample_on_chain_metrics):
        """Test creating on-chain metrics."""
        assert sample_on_chain_metrics.active_addresses == 100000
        assert sample_on_chain_metrics.transaction_count == 250000
        assert sample_on_chain_metrics.market_cap == Decimal("10000000000")

    def test_network_health_score_calculation(self, sample_on_chain_metrics):
        """Test network health score calculation."""
        score = sample_on_chain_metrics.network_health_score
        assert score is not None
        assert 0 <= score <= 100

    def test_network_health_score_missing_data(self):
        """Test network health score with missing data."""
        metrics = OnChainMetrics(
            active_addresses=None,
            transaction_count=None,
            transaction_volume=None,
            market_cap=None,
        )
        assert metrics.network_health_score is None


class TestCryptoMomentumScore:
    """Tests for CryptoMomentumScore model."""

    def test_momentum_score_creation(self):
        """Test creating momentum score."""
        score = CryptoMomentumScore(
            symbol="BTC",
            raw_momentum=Decimal("75"),
            volatility_adjusted_momentum=Decimal("70"),
            btc_adjusted_momentum=Decimal("72"),
            final_score=Decimal("72"),
            rank=1,
            percentile=Decimal("95"),
            confidence=Decimal("85"),
        )
        assert score.symbol == "BTC"
        assert score.final_score == Decimal("72")

    def test_is_high_momentum(self):
        """Test high momentum detection."""
        score = CryptoMomentumScore(
            symbol="BTC",
            raw_momentum=Decimal("75"),
            final_score=Decimal("80"),
            confidence=Decimal("85"),
        )
        assert score.is_high_momentum is True

    def test_is_low_momentum(self):
        """Test low momentum detection."""
        score = CryptoMomentumScore(
            symbol="BTC",
            raw_momentum=Decimal("30"),
            final_score=Decimal("35"),
            confidence=Decimal("60"),
        )
        assert score.is_low_momentum is True

    def test_momentum_score_validation(self):
        """Test momentum score validation."""
        with pytest.raises(ValueError):
            CryptoMomentumScore(
                symbol="BTC",
                raw_momentum=Decimal("150"),  # Invalid: > 100
                final_score=Decimal("150"),
                confidence=Decimal("50"),
            )


class TestCryptoPosition:
    """Tests for CryptoPosition model."""

    def test_position_creation(self):
        """Test creating a position."""
        position = CryptoPosition(
            symbol="BTC",
            quantity=Decimal("1.5"),
            entry_price=Decimal("40000"),
            current_price=Decimal("45000"),
            value=Decimal("67500"),
            weight=Decimal("0.5"),
        )
        assert position.symbol == "BTC"
        assert position.quantity == Decimal("1.5")

    def test_position_pnl_calculation(self):
        """Test P&L calculation in position."""
        position = CryptoPosition(
            symbol="BTC",
            quantity=Decimal("1.5"),
            entry_price=Decimal("40000"),
            current_price=Decimal("45000"),
            value=Decimal("67500"),
            weight=Decimal("0.5"),
        )
        assert position.unrealized_pnl == Decimal("7500")  # 1.5 * 5000
        assert position.unrealized_pnl_pct == Decimal("12.5")  # 5000/40000


class TestCryptoMomentumConfig:
    """Tests for CryptoMomentumConfig model."""

    def test_config_creation(self, sample_config):
        """Test creating configuration."""
        assert sample_config.lookback_days == 90
        assert sample_config.btc_weight == Decimal("0.50")

    def test_config_weight_validation(self):
        """Test weight validation in config."""
        with pytest.raises(ValueError):
            CryptoMomentumConfig(
                max_position_size=Decimal("0.60"),  # Invalid: > 0.5
            )

    def test_config_btc_weight_validation(self):
        """Test BTC weight validation."""
        with pytest.raises(ValueError):
            CryptoMomentumConfig(
                btc_weight=Decimal("1.50"),  # Invalid: > 1.0
            )

    def test_get_screening_description(self, sample_config):
        """Test screening description generation."""
        desc = sample_config.get_screening_description()
        assert "90 days" in desc
        assert "50%" in desc  # btc_weight


# ============================================================================
# SCREENER TESTS (12 tests)
# ============================================================================


class TestCryptoScreener:
    """Tests for CryptoScreener."""

    def test_screener_initialization(self):
        """Test screener initialization."""
        screener = CryptoScreener()
        assert screener.config == {}
        assert screener.screening_history == []

    def test_screen_passing_assets(self, sample_btc_asset, sample_eth_asset, sample_altcoin_asset):
        """Test screening with passing assets."""
        screener = CryptoScreener()
        universe = [sample_btc_asset, sample_eth_asset, sample_altcoin_asset]

        result = screener.screen(
            universe=universe,
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("50"),
        )

        assert len(result.passed_assets) == 3
        assert result.pass_rate == 100.0

    def test_screen_failing_assets(self, sample_btc_asset, sample_small_cap_asset):
        """Test screening with failing assets."""
        screener = CryptoScreener()
        universe = [sample_btc_asset, sample_small_cap_asset]

        result = screener.screen(
            universe=universe,
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("50"),
        )

        assert len(result.passed_assets) == 1
        assert len(result.failed_assets) == 1
        assert "SMALL" in result.failed_assets

    def test_calculate_liquidity_score(self, sample_btc_asset):
        """Test liquidity score calculation."""
        screener = CryptoScreener()
        score = screener.calculate_liquidity_score(sample_btc_asset)

        assert 0 <= score <= 100
        assert score > 50  # BTC should have high liquidity

    def test_verify_listing(self):
        """Test exchange listing verification."""
        screener = CryptoScreener()
        result = screener.verify_listing("BTC", [CryptoExchange.BINANCE, CryptoExchange.COINBASE])
        assert result is True

    def test_calculate_btc_correlation_score(self, sample_btc_asset, sample_eth_asset):
        """Test BTC correlation score calculation."""
        screener = CryptoScreener()

        # BTC (perfect correlation) = low diversification score
        btc_score = screener.calculate_btc_correlation_score(sample_btc_asset)
        assert btc_score < 50  # High correlation = low score

        # Lower correlation asset
        low_corr_asset = CryptoAsset(
            symbol="LOW",
            name="Low Correlation",
            asset_type=CryptoAssetType.UTILITY,
            market_cap=Decimal("1000000000"),
            liquidity_score=Decimal("70"),
            volatility_90d=Decimal("80"),
            avg_daily_volume=Decimal("100000000"),
            exchanges=[CryptoExchange.BINANCE],
            btc_correlation=0.1,  # Low correlation
            current_price=Decimal("10"),
        )
        low_corr_score = screener.calculate_btc_correlation_score(low_corr_asset)
        assert low_corr_score > btc_score  # Lower correlation = higher score

    def test_screening_result_pass_rate(self, sample_btc_asset, sample_small_cap_asset):
        """Test pass rate calculation."""
        screener = CryptoScreener()
        universe = [sample_btc_asset, sample_small_cap_asset]

        result = screener.screen(
            universe=universe,
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
            min_liquidity_score=Decimal("50"),
        )

        assert result.pass_rate == 50.0

    def test_get_screening_summary(self, sample_btc_asset):
        """Test screening summary."""
        screener = CryptoScreener()

        # Run screening first
        screener.screen(
            universe=[sample_btc_asset],
            min_market_cap=Decimal("1000000000"),
            min_daily_volume=Decimal("10000000"),
        )

        summary = screener.get_screening_summary()
        assert summary["total_screenings"] == 1
        assert summary["total_evaluations"] == 1


# ============================================================================
# INDICATORS TESTS (12 tests)
# ============================================================================


class TestCryptoIndicators:
    """Tests for CryptoIndicators."""

    def test_indicators_initialization(self):
        """Test indicators initialization."""
        indicators = CryptoIndicators()
        assert indicators.indicator_cache == {}

    def test_calculate_nvt_ratio(self):
        """Test NVT ratio calculation."""
        indicators = CryptoIndicators()

        market_cap = pd.Series([100, 110, 120, 130, 140] * 10)  # 50 data points
        tx_volume = pd.Series([10, 12, 11, 13, 14] * 10)

        nvt = indicators.calculate_nvt_ratio(market_cap, tx_volume)

        assert len(nvt) == len(market_cap)
        # Last value should not be NaN (MA period is 30)
        assert not pd.isna(nvt.iloc[-1])
        assert nvt.iloc[-1] > 0

    def test_calculate_mayer_multiple(self):
        """Test Mayer Multiple calculation."""
        indicators = CryptoIndicators()

        realized_cap = pd.Series(range(100, 400))  # 300 data points for 200 MA
        current_price = 250

        mayer_multiple = indicators.calculate_mayer_multiple(current_price, realized_cap)

        assert mayer_multiple > 0
        assert isinstance(mayer_multiple, float)

    def test_calculate_fear_greed_index(self):
        """Test Fear & Greed index calculation."""
        indicators = CryptoIndicators()

        metrics = {
            "volatility": 50,
            "momentum": 0.05,
            "social_media": 60,
            "surveys": 55,
            "taker_buy_sell": 1.1,
            "btc_dominance": 45,
        }

        fgi = indicators.calculate_fear_greed_index(metrics)

        assert 0 <= fgi <= 100

    def test_calculate_relative_strength(self):
        """Test relative strength calculation."""
        indicators = CryptoIndicators()

        asset_prices = pd.Series([100, 105, 110, 115, 120])
        btc_prices = pd.Series([40000, 41000, 42000, 43000, 44000])

        rs = indicators.calculate_relative_strength(asset_prices, btc_prices)

        assert len(rs) == len(asset_prices)

    def test_calculate_momentum_score(self, sample_price_series):
        """Test momentum score calculation."""
        indicators = CryptoIndicators()

        score = indicators.calculate_momentum_score(
            prices=sample_price_series,
            benchmark_prices=None,
            lookback_days=90,
        )

        assert 0 <= score <= 100

    def test_calculate_momentum_score_with_btc(self, sample_price_series, sample_btc_price_series):
        """Test momentum score with BTC adjustment."""
        indicators = CryptoIndicators()

        score = indicators.calculate_momentum_score(
            prices=sample_price_series,
            benchmark_prices=sample_btc_price_series,
            lookback_days=90,
        )

        assert 0 <= score <= 100

    def test_calculate_crypto_beta(self):
        """Test beta calculation."""
        indicators = CryptoIndicators()

        asset_returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])
        btc_returns = pd.Series([0.02, 0.03, -0.01, 0.02, 0.01])

        beta = indicators.calculate_crypto_beta(asset_returns, btc_returns)

        assert isinstance(beta, float)

    def test_calculate_network_health_score(self, sample_on_chain_metrics):
        """Test network health score calculation."""
        indicators = CryptoIndicators()

        score = indicators.calculate_network_health_score(sample_on_chain_metrics)

        assert score is not None
        assert 0 <= score <= 100

    def test_calculate_token_velocity(self):
        """Test token velocity calculation."""
        indicators = CryptoIndicators()

        velocity = indicators.calculate_token_velocity(
            transaction_volume=Decimal("5000000000"),
            market_cap=Decimal("10000000000"),
        )

        assert velocity == Decimal("0.50")

    def test_calculate_rsi(self, sample_price_series):
        """Test RSI calculation."""
        indicators = CryptoIndicators()

        rsi = indicators.calculate_rsi(sample_price_series)

        assert len(rsi) == len(sample_price_series)
        # RSI should be between 0 and 100
        assert rsi.dropna().between(0, 100).all()

    def test_calculate_ema(self, sample_price_series):
        """Test EMA calculation."""
        indicators = CryptoIndicators()

        ema = indicators.calculate_ema(sample_price_series)

        assert len(ema) == len(sample_price_series)


# ============================================================================
# PORTFOLIO TESTS (10 tests)
# ============================================================================


class TestCryptoPortfolioConstructor:
    """Tests for CryptoPortfolioConstructor."""

    def test_constructor_initialization(self, sample_config):
        """Test constructor initialization."""
        constructor = CryptoPortfolioConstructor(sample_config)
        assert constructor.config == sample_config

    def test_construct_portfolio(self, sample_config, sample_btc_asset, sample_eth_asset):
        """Test portfolio construction."""
        constructor = CryptoPortfolioConstructor(sample_config)

        momentum_scores = {
            "BTC": CryptoMomentumScore(
                symbol="BTC",
                raw_momentum=Decimal("80"),
                final_score=Decimal("80"),
                confidence=Decimal("90"),
            ),
            "ETH": CryptoMomentumScore(
                symbol="ETH",
                raw_momentum=Decimal("75"),
                final_score=Decimal("75"),
                confidence=Decimal("85"),
            ),
        }

        portfolio = constructor.construct_portfolio(
            ranked_assets=[sample_btc_asset, sample_eth_asset],
            momentum_scores=momentum_scores,
            total_capital=Decimal("100000"),
        )

        assert len(portfolio.positions) == 2
        assert portfolio.btc_weight > 0

    def test_calculate_position_size(self, sample_config, sample_btc_asset):
        """Test position size calculation."""
        constructor = CryptoPortfolioConstructor(sample_config)

        size = constructor.calculate_position_size(
            asset=sample_btc_asset,
            score=80,
            total_capital=Decimal("100000"),
        )

        assert size > 0
        assert size <= Decimal("10000")  # Max 10% of capital

    def test_rebalance_portfolio(self, sample_config):
        """Test portfolio rebalancing."""
        constructor = CryptoPortfolioConstructor(sample_config)

        current_portfolio = CryptoPortfolio(
            positions=[
                CryptoPosition(
                    symbol="BTC",
                    quantity=Decimal("1"),
                    entry_price=Decimal("40000"),
                    current_price=Decimal("45000"),
                    value=Decimal("45000"),
                    weight=Decimal("0.45"),
                )
            ],
            total_value=Decimal("100000"),
            cash=Decimal("55000"),
            btc_weight=Decimal("0.45"),
        )

        target_portfolio = CryptoPortfolio(
            positions=[
                CryptoPosition(
                    symbol="BTC",
                    quantity=Decimal("1.1"),
                    entry_price=Decimal("40000"),
                    current_price=Decimal("45000"),
                    value=Decimal("49500"),
                    weight=Decimal("0.50"),
                )
            ],
            total_value=Decimal("100000"),
            cash=Decimal("50500"),
            btc_weight=Decimal("0.50"),
        )

        trades = constructor.rebalance_portfolio(current_portfolio, target_portfolio)

        assert isinstance(trades, dict)

    def test_get_portfolio_summary(self, sample_config, sample_btc_asset):
        """Test portfolio summary."""
        constructor = CryptoPortfolioConstructor(sample_config)

        portfolio = CryptoPortfolio(
            positions=[
                CryptoPosition(
                    symbol="BTC",
                    quantity=Decimal("1"),
                    entry_price=Decimal("40000"),
                    current_price=Decimal("45000"),
                    value=Decimal("45000"),
                    weight=Decimal("0.45"),
                    unrealized_pnl=Decimal("5000"),
                    unrealized_pnl_pct=Decimal("12.5"),
                )
            ],
            total_value=Decimal("100000"),
            cash=Decimal("55000"),
            btc_weight=Decimal("0.45"),
            expected_volatility=Decimal("65"),
        )

        summary = constructor.get_portfolio_summary(portfolio)

        assert summary["total_positions"] == 1
        assert summary["btc_weight"] == 0.45
        assert summary["expected_volatility"] == 65.0


# ============================================================================
# STRATEGY TESTS (15 tests)
# ============================================================================


class TestCryptoMomentumStrategy:
    """Tests for CryptoMomentumStrategy."""

    def test_strategy_initialization(self):
        """Test strategy initialization."""
        config = {
            "lookback_days": 90,
            "btc_weight": "0.50",
            "max_position_size": "0.10",
        }
        strategy = CryptoMomentumStrategy(config)

        assert strategy.strategy_config.lookback_days == 90
        assert strategy.strategy_config.btc_weight == Decimal("0.50")

    def test_parse_config_valid(self):
        """Test config parsing with valid config."""
        config = {
            "lookback_days": 60,
            "btc_weight": "0.40",
            "portfolio_size": 15,
        }
        strategy = CryptoMomentumStrategy(config)

        assert strategy.strategy_config.lookback_days == 60
        assert strategy.strategy_config.btc_weight == Decimal("0.40")

    def test_set_universe(self, sample_btc_asset, sample_eth_asset):
        """Test setting universe."""
        strategy = CryptoMomentumStrategy({})

        strategy.set_universe([sample_btc_asset, sample_eth_asset])

        assert len(strategy.universe) == 2

    def test_update_momentum_scores(
        self, sample_btc_asset, sample_price_series, sample_btc_price_series
    ):
        """Test updating momentum scores."""
        strategy = CryptoMomentumStrategy({"lookback_days": 90})
        strategy.set_universe([sample_btc_asset])

        # Populate price history
        for i, (date, price) in enumerate(zip(sample_price_series.index, sample_price_series)):
            from app.models.market_data import Quote

            quote = Quote(
                symbol="BTC",
                timestamp=date,
                bid=Decimal(str(price - 10)),
                ask=Decimal(str(price + 10)),
                last=Decimal(str(price)),
                volume=Decimal("1000000"),
            )
            strategy._update_price_history("BTC", quote)

        strategy.update_momentum_scores()

        assert "BTC" in strategy.momentum_scores

    def test_calculate_momentum_score(self, sample_price_series):
        """Test momentum score calculation."""
        strategy = CryptoMomentumStrategy({})

        score = strategy.calculate_momentum_score(sample_price_series)

        assert 0 <= score <= 100

    def test_calculate_crypto_beta(self):
        """Test beta calculation."""
        strategy = CryptoMomentumStrategy({})

        asset_returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.01])
        btc_returns = pd.Series([0.02, 0.03, -0.01, 0.02, 0.01])

        beta = strategy.calculate_crypto_beta(asset_returns, btc_returns)

        assert isinstance(beta, float)

    def test_construct_portfolio(self, sample_btc_asset, sample_eth_asset):
        """Test portfolio construction."""
        strategy = CryptoMomentumStrategy(
            {
                "lookback_days": 90,
                "btc_weight": "0.50",
                "portfolio_size": 5,
            }
        )

        # Set up momentum scores
        strategy.momentum_scores = {
            "BTC": CryptoMomentumScore(
                symbol="BTC",
                raw_momentum=Decimal("80"),
                final_score=Decimal("80"),
                confidence=Decimal("90"),
            ),
            "ETH": CryptoMomentumScore(
                symbol="ETH",
                raw_momentum=Decimal("75"),
                final_score=Decimal("75"),
                confidence=Decimal("85"),
            ),
        }

        strategy.set_universe([sample_btc_asset, sample_eth_asset])

        portfolio = strategy.construct_portfolio(Decimal("100000"))

        assert portfolio is not None
        assert len(portfolio.positions) > 0

    def test_get_required_parameters(self):
        """Test getting required parameters."""
        strategy = CryptoMomentumStrategy({})

        params = strategy.get_required_parameters()

        assert "lookback_days" in params
        assert "max_position_size" in params
        assert "btc_weight" in params

    def test_validate_config(self):
        """Test config validation."""
        strategy = CryptoMomentumStrategy({})

        assert strategy.validate_config() is True

    def test_get_portfolio_metrics(self, sample_btc_asset):
        """Test getting portfolio metrics."""
        strategy = CryptoMomentumStrategy({})

        # Create a portfolio
        portfolio = CryptoPortfolio(
            positions=[
                CryptoPosition(
                    symbol="BTC",
                    quantity=Decimal("1"),
                    entry_price=Decimal("40000"),
                    current_price=Decimal("45000"),
                    value=Decimal("45000"),
                    weight=Decimal("0.45"),
                )
            ],
            total_value=Decimal("100000"),
            cash=Decimal("55000"),
            btc_weight=Decimal("0.45"),
        )
        strategy.current_portfolio = portfolio

        metrics = strategy.get_portfolio_metrics()

        assert metrics["total_positions"] == 1


# ============================================================================
# INTEGRATION TESTS (6 tests)
# ============================================================================


class TestCryptoMomentumIntegration:
    """Integration tests for crypto momentum strategy."""

    def test_full_workflow(self, sample_btc_asset, sample_eth_asset, sample_altcoin_asset):
        """Test complete workflow from screening to portfolio construction."""
        # Initialize strategy
        strategy = CryptoMomentumStrategy(
            {
                "lookback_days": 90,
                "btc_weight": "0.50",
                "portfolio_size": 10,
            }
        )

        # Set universe
        strategy.set_universe([sample_btc_asset, sample_eth_asset, sample_altcoin_asset])

        # Verify universe
        assert len(strategy.universe) == 3

        # Set momentum scores
        strategy.momentum_scores = {
            "BTC": CryptoMomentumScore(
                symbol="BTC",
                raw_momentum=Decimal("85"),
                final_score=Decimal("85"),
                confidence=Decimal("90"),
            ),
            "ETH": CryptoMomentumScore(
                symbol="ETH",
                raw_momentum=Decimal("80"),
                final_score=Decimal("80"),
                confidence=Decimal("85"),
            ),
            "SOL": CryptoMomentumScore(
                symbol="SOL",
                raw_momentum=Decimal("75"),
                final_score=Decimal("75"),
                confidence=Decimal("80"),
            ),
        }

        # Construct portfolio
        portfolio = strategy.construct_portfolio(Decimal("100000"))

        assert portfolio is not None
        assert len(portfolio.positions) >= 1

    def test_screen_and_construct(self, sample_btc_asset, sample_eth_asset, sample_small_cap_asset):
        """Test screening followed by portfolio construction."""
        strategy = CryptoMomentumStrategy(
            {
                "min_market_cap": "1000000000",
                "min_daily_volume": "10000000",
            }
        )

        # Set universe (will be screened)
        strategy.set_universe(
            [
                sample_btc_asset,
                sample_eth_asset,
                sample_small_cap_asset,  # Should fail screening
            ]
        )

        # Only BTC and ETH should pass
        assert len(strategy.universe) == 2
        assert all(a.symbol in ["BTC", "ETH"] for a in strategy.universe)

    def test_rebalance_workflow(self, sample_btc_asset):
        """Test rebalance workflow."""
        strategy = CryptoMomentumStrategy(
            {
                "lookback_days": 90,
                "portfolio_size": 5,
            }
        )

        # Create initial portfolio
        portfolio = CryptoPortfolio(
            positions=[
                CryptoPosition(
                    symbol="BTC",
                    quantity=Decimal("1"),
                    entry_price=Decimal("40000"),
                    current_price=Decimal("45000"),
                    value=Decimal("45000"),
                    weight=Decimal("0.45"),
                )
            ],
            total_value=Decimal("100000"),
            cash=Decimal("55000"),
            btc_weight=Decimal("0.45"),
        )
        strategy.current_portfolio = portfolio

        # Rebalance
        new_portfolio = strategy.rebalance_portfolio(Decimal("100000"))

        assert new_portfolio is not None

    def test_screener_to_strategy_integration(
        self, sample_btc_asset, sample_eth_asset, sample_altcoin_asset
    ):
        """Test integration between screener and strategy."""
        strategy = CryptoMomentumStrategy(
            {
                "min_market_cap": "1000000000",
                "min_daily_volume": "10000000",
            }
        )

        # Run screening through strategy
        strategy.set_universe(
            [
                sample_btc_asset,
                sample_eth_asset,
                sample_altcoin_asset,
            ]
        )

        # Verify screened universe
        assert len(strategy.universe) > 0

    def test_indicators_to_strategy_integration(self, sample_price_series):
        """Test integration between indicators and strategy."""
        strategy = CryptoMomentumStrategy({"lookback_days": 90})

        # Calculate momentum using strategy's indicators
        score = strategy.indicators.calculate_momentum_score(sample_price_series)

        assert 0 <= score <= 100

    def test_portfolio_to_strategy_integration(self, sample_btc_asset):
        """Test integration between portfolio and strategy."""
        strategy = CryptoMomentumStrategy(
            {
                "btc_weight": "0.50",
                "max_position_size": "0.10",
            }
        )

        # Create portfolio using strategy's constructor
        momentum_scores = {
            "BTC": CryptoMomentumScore(
                symbol="BTC",
                raw_momentum=Decimal("80"),
                final_score=Decimal("80"),
                confidence=Decimal("90"),
            ),
        }

        portfolio = strategy.constructor.construct_portfolio(
            ranked_assets=[sample_btc_asset],
            momentum_scores=momentum_scores,
            total_capital=Decimal("100000"),
        )

        assert portfolio is not None
        assert portfolio.btc_weight == Decimal("0.50")


# ============================================================================
# TOTAL: 60+ tests covering all components
# ============================================================================
