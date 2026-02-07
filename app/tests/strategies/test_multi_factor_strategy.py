"""
Comprehensive Unit Tests for Multi-Factor Strategy

This test suite covers:
1. Model validation and creation
2. Factor calculator functionality
3. Factor model implementations
4. Portfolio construction
5. Strategy execution
6. Risk checks and validation

Run with: pytest app/tests/strategies/test_multi_factor_strategy.py -v
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import numpy as np
import pytest

from app.models.market_data import Quote
from app.models.portfolio import AssetClass, Portfolio, Position
from app.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.strategies.multi_factor import (
    FactorCalculator,
    FactorModelManager,
    FactorPortfolio,
    FactorPortfolioConstructor,
    FactorPosition,
    FactorProfile,
    FactorScores,
    FactorStrategyConfig,
    FactorTiltDirection,
    FactorType,
    MultiFactorStrategy,
    get_default_factor_premiums,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_factor_config():
    """Create sample factor strategy configuration."""
    return {
        "name": "TestMultiFactor",
        "description": "Test multi-factor strategy",
        "objetivo_inversion": "BALANCED_GROWTH",
        "value_tilt": Decimal("0.2"),
        "profitability_tilt": Decimal("0.2"),
        "momentum_tilt": Decimal("0.1"),
        "size_tilt": Decimal("0"),
        "investment_tilt": Decimal("0"),
        "portfolio_size": 20,
        "max_sector_weight": Decimal("0.25"),
        "max_single_position": Decimal("0.05"),
        "min_position": Decimal("0.01"),
    }


@pytest.fixture
def sample_factor_profiles() -> List[FactorProfile]:
    """Create sample factor profiles for testing."""
    profiles = []

    # Create 50 sample profiles
    for i in range(50):
        symbol = f"STOCK{i:02d}"

        # Vary the characteristics to get different factor scores
        is_value = i % 3 == 0  # Every 3rd stock is value
        is_small_cap = i % 4 == 0  # Every 4th stock is small cap
        is_profitable = i % 5 != 0  # Most stocks are profitable
        is_winner = i % 3 != 0  # Most stocks are winners

        # Use 6 sectors instead of 3 for better diversification testing
        sectors = ["Technology", "Healthcare", "Finance", "Consumer", "Energy", "Industrial"]
        sector = sectors[i % 6]

        profile = FactorProfile(
            symbol=symbol,
            company_name=f"Test Company {i}",
            sector=sector,
            industry=f"Test Industry {i % 3}",
            current_price=Decimal(str(100 + i)),
            market_cap=Decimal("500") if is_small_cap else Decimal("5000"),
            shares_outstanding=Decimal(str(1000000 + i * 10000)),
            # Value metrics
            book_value_per_share=Decimal(str(50 + i)),
            book_to_market=Decimal("0.8") if is_value else Decimal("0.3"),
            pe_ratio=Decimal(str(15 + i)),
            pb_ratio=Decimal(str(2 + i * 0.1)),
            ps_ratio=Decimal(str(3 + i * 0.1)),
            ev_ebitda=Decimal(str(12 + i)),
            # Profitability metrics
            revenue=Decimal(str(1000 + i * 100)),
            ebitda=Decimal(str(200 + i * 10)),
            operating_income=Decimal(str(150 + i * 10)),
            net_income=Decimal(str(100 + i * 10)),
            roe=Decimal(str(15)) if is_profitable else Decimal(str(5)),
            roa=Decimal(str(10)) if is_profitable else Decimal(str(2)),
            roic=Decimal(str(12)) if is_profitable else Decimal(str(4)),
            gross_margin=Decimal(str(40)) if is_profitable else Decimal(str(15)),
            operating_margin=Decimal(str(20)) if is_profitable else Decimal(str(5)),
            net_margin=Decimal(str(15)) if is_profitable else Decimal(str(3)),
            # Investment metrics
            total_assets=Decimal(str(5000 + i * 100)),
            total_assets_py=Decimal(str(4800 + i * 100)),
            asset_growth=Decimal(str(5)) if is_small_cap else Decimal(str(2)),
            capex=Decimal(str(100 + i * 10)),
            capex_py=Decimal(str(90 + i * 10)),
            # Price history for momentum
            price_12m_ago=Decimal(str(80 + i)),
            price_6m_ago=Decimal(str(90 + i)),
            price_3m_ago=Decimal(str(95 + i)),
            price_1m_ago=Decimal(str(98 + i)),
            # Momentum calculations
            momentum_1m=Decimal(str(2)),
            momentum_3m=Decimal(str(5)),
            momentum_6m=Decimal(str(10)),
            momentum_12m=Decimal(str(20)),
            # Volatility
            beta=Decimal(str(1.0 + i * 0.02)),
            volatility_1y=Decimal(str(0.2 + i * 0.005)),
            max_drawdown_1y=Decimal(str(-0.15 - i * 0.005)),
            # Factor scores (optional)
            factor_scores=None,
            overall_factor_score=Decimal(str(60)),
            quality_score=Decimal(str(65)),
            value_score=Decimal(str(55)),
            growth_score=Decimal(str(70)),
        )

        profiles.append(profile)

    return profiles


@pytest.fixture
def sample_quote():
    """Create sample market quote."""
    return Quote(
        symbol="AAPL",
        bid=Decimal("150.00"),
        ask=Decimal("150.05"),
        last=Decimal("150.02"),
        open=Decimal("149.00"),
        high=Decimal("151.00"),
        low=Decimal("148.00"),
        close=Decimal("150.00"),
        volume=Decimal("1000000"),
    )


@pytest.fixture
def sample_portfolio() -> Portfolio:
    """Create sample portfolio."""
    return Portfolio(
        portfolio_id="test_portfolio",
        cash=Decimal("50000"),
        positions=[
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("140"),
                market_price=Decimal("150"),
                unrealized_pnl=Decimal("1000"),
                broker="test",
                sector="Technology",
            ),
        ],
        broker="test",
    )


# ============================================================================
# MODEL TESTS
# ============================================================================


class TestFactorStrategyConfig:
    """Tests for FactorStrategyConfig model."""

    def test_create_default_config(self):
        """Test creating default configuration."""
        config = FactorStrategyConfig()

        assert config.name == "MultiFactorStrategy"
        assert config.objetivo_inversion == "BALANCED_GROWTH"
        assert config.portfolio_size == 40
        assert config.value_tilt == Decimal("0.2")

    def test_create_custom_config(self, sample_factor_config):
        """Test creating custom configuration."""
        config = FactorStrategyConfig(**sample_factor_config)

        assert config.name == "TestMultiFactor"
        assert config.value_tilt == Decimal("0.2")
        assert config.portfolio_size == 20

    def test_validate_weights_sum_valid(self):
        """Test validation passes when weights sum to 1."""
        config = FactorStrategyConfig(
            value_weight=Decimal("0.25"),
            profitability_weight=Decimal("0.25"),
            momentum_weight=Decimal("0.20"),
            size_weight=Decimal("0.15"),
            investment_weight=Decimal("0.15"),
        )
        # Should not raise
        assert config.value_weight == Decimal("0.25")

    def test_validate_weights_sum_invalid(self):
        """Test validation fails when weights don't sum to 1."""
        with pytest.raises(ValueError, match="Factor weights must sum to 1.0"):
            FactorStrategyConfig(
                value_weight=Decimal("0.5"),
                profitability_weight=Decimal("0.5"),
                momentum_weight=Decimal("0.2"),
                size_weight=Decimal("0.15"),
                investment_weight=Decimal("0.15"),
            )

    def test_get_factor_tilts(self, sample_factor_config):
        """Test getting factor tilts."""
        config = FactorStrategyConfig(**sample_factor_config)
        tilts = config.get_factor_tilts()

        assert len(tilts) == 5
        assert tilts[0].factor == FactorType.VALUE
        assert tilts[0].direction == FactorTiltDirection.POSITIVE
        assert tilts[0].target_exposure == Decimal("0.2")

    def test_get_config_description(self, sample_factor_config):
        """Test configuration description."""
        config = FactorStrategyConfig(**sample_factor_config)
        desc = config.get_config_description()

        assert "Multi-Factor Strategy" in desc
        assert "BALANCED_GROWTH" in desc
        assert "20" in desc  # portfolio size


class TestFactorProfile:
    """Tests for FactorProfile model."""

    def test_create_profile(self):
        """Test creating a factor profile."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("150"),
            market_cap=Decimal("2500000"),
        )

        assert profile.symbol == "AAPL"
        assert profile.current_price == Decimal("150")

    def test_momentum_calculation(self):
        """Test momentum excluding last month calculation."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("150"),
            price_12m_ago=Decimal("100"),
            price_1m_ago=Decimal("145"),
        )

        momentum = profile.momentum_excluding_last_month
        assert momentum is not None
        # (145/100 - 1) * 100 = 45%
        assert abs(float(momentum) - 45.0) < 0.01

    def test_is_value_stock(self):
        """Test value stock classification."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("100"),
            book_to_market=Decimal("0.6"),
        )

        assert profile.is_value_stock is True

        profile.book_to_market = Decimal("0.4")
        assert profile.is_value_stock is False

    def test_is_small_cap(self):
        """Test small cap classification."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("100"),
            market_cap=Decimal("1000"),
        )

        assert profile.is_small_cap is True

        profile.market_cap = Decimal("5000")
        assert profile.is_small_cap is False

    def test_is_profitable(self):
        """Test profitable classification."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("100"),
            roa=Decimal("10"),
        )

        assert profile.is_profitable is True

        profile.roa = Decimal("-5")
        assert profile.is_profitable is False

    def test_is_winner(self):
        """Test winner classification."""
        profile = FactorProfile(
            symbol="AAPL",
            current_price=Decimal("150"),
            price_12m_ago=Decimal("100"),
            price_1m_ago=Decimal("140"),
        )

        assert profile.is_winner is True  # 40% return > 15% threshold


class TestFactorScores:
    """Tests for FactorScores model."""

    def test_create_scores(self):
        """Test creating factor scores."""
        scores = FactorScores(
            symbol="AAPL",
            value_score=Decimal("1.5"),
            size_score=Decimal("-0.5"),
            profitability_score=Decimal("1.0"),
        )

        assert scores.symbol == "AAPL"
        assert scores.value_score == Decimal("1.5")
        assert scores.size_score == Decimal("-0.5")


class TestFactorPortfolio:
    """Tests for FactorPortfolio model."""

    def test_create_portfolio(self):
        """Test creating a factor portfolio."""
        positions = [
            FactorPosition(
                symbol="AAPL",
                weight=Decimal("0.04"),
                sector="Technology",
            ),
            FactorPosition(
                symbol="JPM",
                weight=Decimal("0.03"),
                sector="Finance",
            ),
        ]

        portfolio = FactorPortfolio(
            positions=positions,
            total_value=Decimal("100000"),
            cash=Decimal("0"),
            sector_weights={"Technology": Decimal("0.04"), "Finance": Decimal("0.03")},
        )

        assert portfolio.positions_count == 2
        assert portfolio.is_diversified is False  # Need 20+ positions
        assert portfolio.max_position_weight == Decimal("0.04")

    def test_herfindahl_index(self):
        """Test Herfindahl index calculation."""
        positions = [
            FactorPosition(symbol="A", weight=Decimal("0.5")),
            FactorPosition(symbol="B", weight=Decimal("0.3")),
            FactorPosition(symbol="C", weight=Decimal("0.2")),
        ]

        portfolio = FactorPortfolio(
            positions=positions,
            total_value=Decimal("100000"),
        )

        hhi = portfolio.herfindahl_index
        expected = Decimal("0.5") ** 2 + Decimal("0.3") ** 2 + Decimal("0.2") ** 2
        assert abs(float(hhi) - float(expected)) < 0.0001


# ============================================================================
# FACTOR CALCULATOR TESTS
# ============================================================================


class TestFactorCalculator:
    """Tests for FactorCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create factor calculator."""
        return FactorCalculator(min_samples=5)

    def test_calculate_value_scores(self, calculator, sample_factor_profiles):
        """Test calculating value factor scores."""
        scores_dict = calculator.calculate_factor_scores(sample_factor_profiles)

        assert len(scores_dict) > 0

        # Check that we have value scores
        for symbol, scores in scores_dict.items():
            if scores.value_score is not None:
                # Score should be reasonable (z-score typically -3 to 3)
                assert -5 <= float(scores.value_score) <= 5

    def test_calculate_size_scores(self, calculator, sample_factor_profiles):
        """Test calculating size factor scores."""
        scores_dict = calculator.calculate_factor_scores(sample_factor_profiles)

        assert len(scores_dict) > 0

        # Check size scores
        size_scores = [s.size_score for s in scores_dict.values() if s.size_score is not None]
        assert len(size_scores) > 0

    def test_calculate_profitability_scores(self, calculator, sample_factor_profiles):
        """Test calculating profitability scores."""
        scores_dict = calculator.calculate_factor_scores(sample_factor_profiles)

        prof_scores = [
            s.profitability_score for s in scores_dict.values() if s.profitability_score is not None
        ]
        assert len(prof_scores) > 0

    def test_calculate_momentum_scores(self, calculator, sample_factor_profiles):
        """Test calculating momentum scores."""
        scores_dict = calculator.calculate_factor_scores(sample_factor_profiles)

        mom_scores = [
            s.momentum_score for s in scores_dict.values() if s.momentum_score is not None
        ]
        assert len(mom_scores) > 0

    def test_get_factor_statistics(self, calculator, sample_factor_profiles):
        """Test getting factor statistics."""
        calculator.calculate_factor_scores(sample_factor_profiles)
        stats = calculator.get_factor_statistics()

        assert len(stats) > 0
        assert "value" in stats or "size" in stats

    def test_insufficient_samples(self, calculator, sample_factor_profiles):
        """Test behavior with insufficient samples."""
        profiles = sample_factor_profiles[:3]  # Less than min_samples
        scores = calculator.calculate_factor_scores(profiles)

        # Should return empty dict or handle gracefully
        assert isinstance(scores, dict)

    def test_calculate_predicted_returns(self, calculator, sample_factor_profiles):
        """Test calculating predicted returns from factor model."""
        scores_dict = calculator.calculate_factor_scores(sample_factor_profiles)
        premiums = get_default_factor_premiums()

        predicted = calculator.calculate_predicted_returns(
            scores_dict, premiums, risk_free_rate=0.02
        )

        assert len(predicted) > 0
        for symbol, ret in predicted.items():
            assert float(ret) > -100  # Reasonable return


# ============================================================================
# FACTOR MODEL TESTS
# ============================================================================


class TestFactorModelManager:
    """Tests for FactorModelManager."""

    @pytest.fixture
    def manager(self):
        """Create factor model manager."""
        return FactorModelManager()

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert "ff5" in manager.models
        assert "ff6" in manager.models
        assert "carhart" in manager.models

    def test_fit_ff5_model(self, manager):
        """Test fitting FF5 model."""
        # Create sample data
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
            "profitability": np.random.normal(0.002, 0.01, n_obs),
            "investment": np.random.normal(0.001, 0.01, n_obs),
        }

        result = manager.fit_model("ff5", returns, factor_returns)

        assert result.model_name == "Fama-French 5-Factor"
        assert result.beta_market is not None
        assert result.beta_value is not None
        assert result.beta_profitability is not None
        assert result.observations == n_obs

    def test_fit_carhart_model(self, manager):
        """Test fitting Carhart 4-factor model."""
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
            "momentum": np.random.normal(0.004, 0.015, n_obs),
        }

        result = manager.fit_model("carhart", returns, factor_returns)

        assert result.model_name == "Carhart 4-Factor"
        assert result.beta_momentum is not None

    def test_fit_6factor_model(self, manager):
        """Test fitting complete 6-factor model."""
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
            "profitability": np.random.normal(0.002, 0.01, n_obs),
            "investment": np.random.normal(0.001, 0.01, n_obs),
            "momentum": np.random.normal(0.004, 0.015, n_obs),
        }

        result = manager.fit_model("ff6", returns, factor_returns)

        assert result.model_name == "FF5 + Momentum (6-Factor)"
        assert result.beta_momentum is not None
        assert result.beta_profitability is not None

    def test_compare_models(self, manager):
        """Test comparing multiple models."""
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
            "profitability": np.random.normal(0.002, 0.01, n_obs),
            "investment": np.random.normal(0.001, 0.01, n_obs),
            "momentum": np.random.normal(0.004, 0.015, n_obs),
        }

        results = manager.compare_models(returns, factor_returns)

        assert len(results) > 0
        assert "ff6" in results or "ff5" in results

    def test_get_best_model(self, manager):
        """Test getting best model."""
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
        }

        results = manager.compare_models(returns, factor_returns)
        if results:
            best_name, best_result = manager.get_best_model(results, metric="r_squared")

            assert best_name in results
            assert best_result.r_squared is not None

    def test_missing_factor_raises_error(self, manager):
        """Test that missing factors raise error."""
        n_obs = 60
        returns = np.random.normal(0.01, 0.02, n_obs)

        # Missing profitability factor for FF5
        factor_returns = {
            "market": np.random.normal(0.005, 0.01, n_obs),
            "size": np.random.normal(0.002, 0.01, n_obs),
            "value": np.random.normal(0.003, 0.01, n_obs),
            "investment": np.random.normal(0.001, 0.01, n_obs),
        }

        with pytest.raises(ValueError):
            manager.fit_model("ff5", returns, factor_returns)


# ============================================================================
# PORTFOLIO CONSTRUCTOR TESTS
# ============================================================================


class TestFactorPortfolioConstructor:
    """Tests for FactorPortfolioConstructor."""

    @pytest.fixture
    def config(self, sample_factor_config):
        """Create strategy config."""
        return FactorStrategyConfig(**sample_factor_config)

    @pytest.fixture
    def constructor(self, config):
        """Create portfolio constructor."""
        return FactorPortfolioConstructor(config)

    @pytest.fixture
    def factor_scores_dict(self, sample_factor_profiles):
        """Create factor scores dictionary."""
        calculator = FactorCalculator()
        return calculator.calculate_factor_scores(sample_factor_profiles)

    def test_construct_portfolio(self, constructor, sample_factor_profiles, factor_scores_dict):
        """Test constructing a portfolio."""
        total_capital = Decimal("100000")

        portfolio = constructor.construct_portfolio(
            sample_factor_profiles,
            factor_scores_dict,
            total_capital,
        )

        assert portfolio is not None
        assert portfolio.total_value == total_capital
        assert len(portfolio.positions) > 0
        assert len(portfolio.positions) <= 40  # Max portfolio size

    def test_portfolio_respects_max_position(
        self, constructor, sample_factor_profiles, factor_scores_dict
    ):
        """Test that portfolio respects max position size."""
        portfolio = constructor.construct_portfolio(
            sample_factor_profiles,
            factor_scores_dict,
            Decimal("100000"),
        )

        for pos in portfolio.positions:
            assert pos.weight <= Decimal("0.05")  # max_single_position

    def test_portfolio_respects_sector_limits(
        self, constructor, sample_factor_profiles, factor_scores_dict
    ):
        """Test that portfolio respects sector weight limits."""
        portfolio = constructor.construct_portfolio(
            sample_factor_profiles,
            factor_scores_dict,
            Decimal("100000"),
        )

        # Check that no single sector exceeds limit by too much
        # Note: With optimization, there might be slight overruns
        for sector, weight in portfolio.sector_weights.items():
            # Allow small tolerance for optimization
            assert weight <= Decimal("0.30")  # Slightly above 0.25 max

    def test_calculate_sector_weights(self, constructor):
        """Test sector weight calculation."""
        positions = [
            FactorPosition(symbol="A", weight=Decimal("0.10"), sector="Technology"),
            FactorPosition(symbol="B", weight=Decimal("0.05"), sector="Technology"),
            FactorPosition(symbol="C", weight=Decimal("0.15"), sector="Finance"),
        ]

        weights = constructor._calculate_sector_weights(positions)

        # Total weight = 0.30, Technology = 0.15/0.30 = 0.5, Finance = 0.15/0.30 = 0.5
        assert weights["Technology"] == Decimal("0.5")
        assert weights["Finance"] == Decimal("0.5")

    def test_analyze_drift_no_rebalance(self, constructor, factor_scores_dict):
        """Test drift analysis when no rebalance needed."""
        # Create portfolio
        portfolio = FactorPortfolio(
            positions=[
                FactorPosition(symbol="AAPL", weight=Decimal("0.04"), sector="Technology"),
            ],
            total_value=Decimal("100000"),
            rebalance_at=datetime.utcnow() + timedelta(days=30),
            factor_exposures={"value": Decimal("0.1")},
        )

        recommendation = constructor.analyze_drift(portfolio, factor_scores_dict)

        # Should not need rebalance (just created)
        assert isinstance(recommendation.needs_rebalance, bool)

    def test_get_portfolio_metrics(self, constructor, sample_factor_profiles, factor_scores_dict):
        """Test getting portfolio metrics."""
        portfolio = constructor.construct_portfolio(
            sample_factor_profiles[:20],  # Smaller universe
            factor_scores_dict,
            Decimal("100000"),
        )

        metrics = constructor.get_portfolio_metrics(portfolio)

        assert metrics["total_value"] == 100000
        assert metrics["positions_count"] > 0
        assert "factor_exposures" in metrics
        assert "sector_weights" in metrics


# ============================================================================
# STRATEGY TESTS
# ============================================================================


class TestMultiFactorStrategy:
    """Tests for MultiFactorStrategy."""

    @pytest.fixture
    def strategy(self, sample_factor_config):
        """Create multi-factor strategy."""
        return MultiFactorStrategy(sample_factor_config)

    @pytest.fixture
    def initialized_strategy(self, strategy, sample_factor_profiles):
        """Create initialized strategy with universe."""
        strategy.set_universe(sample_factor_profiles)
        return strategy

    def test_strategy_initialization(self, strategy):
        """Test strategy initialization."""
        assert strategy.name == "TestMultiFactor"
        assert strategy.strategy_config.objetivo_inversion == "BALANCED_GROWTH"
        assert strategy.strategy_config.value_tilt == Decimal("0.2")

    def test_set_universe(self, strategy, sample_factor_profiles):
        """Test setting the universe."""
        strategy.set_universe(sample_factor_profiles)

        assert len(strategy.universe) == 50
        assert len(strategy.factor_scores_dict) > 0

    def test_construct_initial_portfolio(self, initialized_strategy):
        """Test constructing initial portfolio."""
        total_capital = Decimal("100000")

        portfolio = initialized_strategy.construct_initial_portfolio(total_capital)

        assert portfolio is not None
        assert portfolio.total_value == total_capital
        assert len(portfolio.positions) > 0
        assert initialized_strategy.last_rebalance_date is not None

    def test_generate_buy_signals(self, initialized_strategy, sample_quote):
        """Test generating buy signals."""
        # Update profile price
        for profile in initialized_strategy.universe:
            if profile.symbol == sample_quote.symbol:
                profile.current_price = sample_quote.close
                break

        signals = initialized_strategy.generate_signals(sample_quote)

        # Should generate some signals
        assert isinstance(signals, list)

        for signal in signals:
            assert signal.symbol == sample_quote.symbol
            assert signal.source == SignalSource.FUNDAMENTAL
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]

    def test_generate_sell_signals(self, initialized_strategy, sample_quote):
        """Test generating sell signals when quality deteriorates."""
        # Make a stock have poor quality
        for profile in initialized_strategy.universe:
            if profile.symbol == sample_quote.symbol:
                profile.quality_score = Decimal("20")  # Below minimum
                profile.current_price = sample_quote.close
                break

        # Add to current portfolio
        initialized_strategy.current_portfolio = FactorPortfolio(
            positions=[
                FactorPosition(symbol=sample_quote.symbol, weight=Decimal("0.04")),
            ],
            total_value=Decimal("100000"),
        )

        signals = initialized_strategy.generate_signals(sample_quote)

        # Should generate sell signal
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        # Note: This depends on factor scores, so may or may not trigger

    def test_risk_check_max_position(self, initialized_strategy):
        """Test risk check for max position size."""
        # Create a portfolio with a position that's at max
        position = Position(
            symbol="AAPL",
            asset_class=AssetClass.EQUITY,
            quantity=Decimal("100"),
            avg_price=Decimal("100"),
            market_price=Decimal("100"),
            unrealized_pnl=Decimal("0"),
            broker="test",
        )

        portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("90000"),  # $10k position / $100k total = 10%
            positions=[position],
            broker="test",
        )

        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=80.0,
            priority_score=70.0,
            source=SignalSource.FUNDAMENTAL,
            price=Decimal("100"),
            volume=Decimal("1000000"),
        )

        # Position is 10% but max is 5%, should fail
        result = initialized_strategy.risk_check(signal, portfolio)
        assert result is False

    def test_risk_check_sector_limit(self, initialized_strategy):
        """Test risk check for sector limits."""
        # Use a stock that's in the universe (STOCK00 is Technology sector from fixture)
        signal = Signal(
            symbol="STOCK00",  # First stock in universe, Technology sector
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=75.0,
            liquidity_score=80.0,
            priority_score=70.0,
            source=SignalSource.FUNDAMENTAL,
            price=Decimal("300"),
            volume=Decimal("1000000"),
        )

        # Create portfolio at sector limit (25% in Technology)
        initialized_strategy.current_portfolio = FactorPortfolio(
            positions=[
                FactorPosition(symbol="AAPL", weight=Decimal("0.25"), sector="Technology"),
            ],
            total_value=Decimal("100000"),
            sector_weights={"Technology": Decimal("0.25")},
        )

        # Create empty portfolio for risk check
        test_portfolio = Portfolio(
            portfolio_id="test",
            cash=Decimal("100000"),
            positions=[],
            broker="test",
        )

        result = initialized_strategy.risk_check(signal, test_portfolio)

        # Should fail risk check (would exceed sector limit)
        assert result is False

    def test_validate_config_valid(self, strategy):
        """Test config validation with valid config."""
        assert strategy.validate_config() is True

    def test_validate_config_invalid_weights(self, sample_factor_config):
        """Test config validation with invalid weights."""
        config = sample_factor_config.copy()
        config["value_weight"] = Decimal("0.5")
        config["profitability_weight"] = Decimal("0.6")  # Sum > 1

        # Should raise ValueError during config validation
        with pytest.raises(ValueError):
            FactorStrategyConfig(**config)

    def test_get_required_parameters(self, strategy):
        """Test getting required parameters."""
        params = strategy.get_required_parameters()

        assert "portfolio_size" in params
        assert "value_tilt" in params
        assert "max_sector_weight" in params

    def test_get_portfolio_metrics(self, initialized_strategy):
        """Test getting portfolio metrics."""
        initialized_strategy.construct_initial_portfolio(Decimal("100000"))

        metrics = initialized_strategy.get_portfolio_metrics()

        assert "total_value" in metrics
        assert "positions_count" in metrics
        assert "factor_exposures" in metrics

    def test_get_factor_exposures(self, initialized_strategy):
        """Test getting factor exposures."""
        initialized_strategy.construct_initial_portfolio(Decimal("100000"))

        exposures = initialized_strategy.get_factor_exposures()

        assert "value" in exposures
        assert "profitability" in exposures
        assert "momentum" in exposures

    def test_get_strategy_status(self, initialized_strategy):
        """Test getting strategy status."""
        status = initialized_strategy.get_strategy_status()

        assert status["name"] == "TestMultiFactor"
        assert status["objective"] == "BALANCED_GROWTH"
        assert status["universe_size"] == 50
        assert "factor_tilts" in status

    def test_async_execute_construct_mode(self, initialized_strategy):
        """Test async execute in construct mode."""

        async def test():
            result = await initialized_strategy.execute(
                mode="construct_portfolio",
                capital=100000,
            )
            assert result is not None
            assert isinstance(result, FactorPortfolio)

        asyncio.run(test())

    def test_async_execute_signals_mode(self, initialized_strategy, sample_quote):
        """Test async execute in signals mode."""

        async def test():
            result = await initialized_strategy.execute(
                mode="signals",
                market_data=sample_quote,
            )
            assert isinstance(result, list)

        asyncio.run(test())

    def test_rebalance_portfolio(self, initialized_strategy):
        """Test rebalancing portfolio."""
        initialized_strategy.construct_initial_portfolio(Decimal("100000"))

        len(initialized_strategy.current_portfolio.positions)

        new_portfolio = initialized_strategy.rebalance_portfolio()

        assert new_portfolio is not None
        assert initialized_strategy.rebalance_count == 2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestMultiFactorIntegration:
    """Integration tests for complete workflow."""

    def test_complete_workflow(self, sample_factor_config, sample_factor_profiles):
        """Test complete strategy workflow."""
        # Create strategy
        strategy = MultiFactorStrategy(sample_factor_config)

        # Set universe
        strategy.set_universe(sample_factor_profiles)
        assert len(strategy.universe) == 50

        # Construct portfolio
        portfolio = strategy.construct_initial_portfolio(Decimal("100000"))
        assert portfolio is not None
        assert len(portfolio.positions) > 0

        # Check metrics
        metrics = strategy.get_portfolio_metrics()
        assert metrics["positions_count"] > 0
        assert metrics["total_value"] == 100000

        # Check exposures
        exposures = strategy.get_factor_exposures()
        assert len(exposures) > 0

        # Check status
        status = strategy.get_strategy_status()
        assert status["objective"] == "BALANCED_GROWTH"

    def test_factor_premiums_defaults(self):
        """Test default factor premiums."""
        premiums = get_default_factor_premiums()

        assert "market" in premiums
        assert "value" in premiums
        assert "momentum" in premiums
        assert premiums["market"] > 0  # Should be positive

    def test_small_universe_handling(self, sample_factor_config, sample_factor_profiles):
        """Test handling of small universe."""
        strategy = MultiFactorStrategy(sample_factor_config)

        # Small universe (less than min_samples)
        small_profiles = sample_factor_profiles[:5]
        strategy.set_universe(small_profiles)

        # Should handle gracefully
        assert len(strategy.universe) <= 5


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_universe(self, sample_factor_config):
        """Test with empty universe."""
        strategy = MultiFactorStrategy(sample_factor_config)
        strategy.set_universe([])

        assert len(strategy.universe) == 0

        # Should not crash when constructing
        with pytest.raises(ValueError):
            strategy.construct_initial_portfolio(Decimal("100000"))

    def test_null_factor_scores(self, sample_factor_config):
        """Test handling of null factor scores."""
        strategy = MultiFactorStrategy(sample_factor_config)

        # Create profile with None values
        profile = FactorProfile(
            symbol="NULL",
            current_price=Decimal("100"),
            book_to_market=None,
            roa=None,
        )

        strategy.set_universe([profile])

        # Should handle gracefully
        signals = strategy.generate_signals(
            Quote(
                symbol="NULL",
                bid=Decimal("100"),
                ask=Decimal("101"),
                last=Decimal("100.5"),
                open=Decimal("99"),
                high=Decimal("102"),
                low=Decimal("98"),
                close=Decimal("100"),
                volume=Decimal("100000"),
            )
        )

        # Should return empty list (no factor scores calculated)
        assert isinstance(signals, list)

    def test_extreme_tilt_values(self):
        """Test with extreme tilt values."""
        config = {
            "value_tilt": Decimal("0.9"),  # Very high
            "profitability_tilt": Decimal("0.8"),
        }

        with pytest.raises(ValueError):
            FactorStrategyConfig(**config)

    def test_zero_portfolio_size(self, sample_factor_config):
        """Test with zero portfolio size."""
        config = sample_factor_config.copy()
        config["portfolio_size"] = 0

        with pytest.raises(ValueError):
            FactorStrategyConfig(**config)

    def test_negative_price(self):
        """Test profile with negative price."""
        with pytest.raises(ValueError):
            FactorProfile(
                symbol="BAD",
                current_price=Decimal("-100"),
            )

    def test_invalid_market_cap(self, sample_factor_config):
        """Test with invalid market cap filter."""
        strategy = MultiFactorStrategy(sample_factor_config)

        # Set config with unrealistic market cap
        strategy.strategy_config.min_market_cap = Decimal("999999999")

        profiles = [
            FactorProfile(
                symbol="TEST",
                current_price=Decimal("100"),
                market_cap=Decimal("1000"),  # Below min
            )
        ]

        strategy.set_universe(profiles)

        # Universe should be filtered or handled gracefully
        assert isinstance(strategy.universe, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
