"""
Tests for Portfolio Construction - Narang "Inside the Black Box" Chapter 6
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

from app.services.portfolio_construction_narang import (
    OptimizationMethod,
    RebalanceTrigger,
    AlphaView,
    PortfolioConstraints,
    PortfolioWeights,
    RebalanceRecommendation,
    PortfolioConstructor,
    get_portfolio_constructor,
)
from app.strategies.alpha_models import AlphaType


@pytest.fixture
def sample_returns():
    """Create sample returns data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")

    # Create returns for 10 assets
    n_assets = 10
    symbols = [f"STOCK{i}" for i in range(n_assets)]

    # Generate correlated returns
    means = np.random.uniform(0.0001, 0.001, n_assets)
    cov = np.eye(n_assets) * 0.0002  # 20% annual vol

    returns = np.random.multivariate_normal(means, cov, size=100)
    returns_df = pd.DataFrame(returns, index=dates, columns=symbols)

    return returns_df


@pytest.fixture
def sample_alpha_views():
    """Create sample alpha views."""
    views = [
        AlphaView(
            symbol="STOCK0",
            expected_return=0.05,  # 5%
            confidence=0.8,
            alpha_source="momentum",
            holding_period=10,
        ),
        AlphaView(
            symbol="STOCK1",
            expected_return=0.03,
            confidence=0.7,
            alpha_source="mean_reversion",
            holding_period=5,
        ),
        AlphaView(
            symbol="STOCK2",
            expected_return=0.04,
            confidence=0.75,
            alpha_source="momentum",
            holding_period=7,
        ),
        AlphaView(
            symbol="STOCK3",
            expected_return=0.02,
            confidence=0.6,
            alpha_source="value",
            holding_period=14,
        ),
        AlphaView(
            symbol="STOCK4",
            expected_return=0.035,
            confidence=0.65,
            alpha_source="quality",
            holding_period=21,
        ),
    ]
    return views


@pytest.fixture
def portfolio_constructor_config():
    """Portfolio constructor configuration."""
    return {
        "name": "test_constructor",
        "optimization_method": "mean_variance",
        "constraints": {
            "max_position_size": 0.30,
            "min_position_size": 0.05,
            "max_leverage": 1.0,
            "max_turnover": 0.20,
            "max_new_positions": 10,
        },
        "rebalance_frequency": "weekly",
        "drift_threshold": 0.05,
        "risk_aversion": 1.0,
    }


class TestAlphaView:
    """Tests for AlphaView dataclass."""

    def test_alpha_view_creation(self):
        """Test creating an alpha view."""
        view = AlphaView(
            symbol="AAPL",
            expected_return=0.05,
            confidence=0.8,
            alpha_source="momentum",
            holding_period=10,
        )

        assert view.symbol == "AAPL"
        assert view.expected_return == 0.05
        assert view.confidence == 0.8
        assert view.alpha_source == "momentum"
        assert view.holding_period == 10


class TestPortfolioConstraints:
    """Tests for PortfolioConstraints dataclass."""

    def test_default_constraints(self):
        """Test default constraint values."""
        constraints = PortfolioConstraints()

        assert constraints.max_position_size == Decimal("0.10")
        assert constraints.max_leverage == Decimal("1.0")
        assert constraints.max_sector_exposure == Decimal("0.30")


class TestPortfolioWeights:
    """Tests for PortfolioWeights dataclass."""

    def test_portfolio_weights_properties(self):
        """Test portfolio weights calculated properties."""
        weights = PortfolioWeights(
            weights={
                "STOCK0": Decimal("0.30"),
                "STOCK1": Decimal("0.25"),
                "STOCK2": Decimal("0.20"),
                "STOCK3": Decimal("0.15"),
                "STOCK4": Decimal("0.10"),
            },
            optimization_method=OptimizationMethod.MEAN_VARIANCE,
        )

        assert weights.long_exposure == Decimal("1.00")  # All long
        assert weights.short_exposure == Decimal("0.00")
        assert weights.gross_exposure == Decimal("1.00")
        assert weights.net_exposure == Decimal("1.00")

    def test_portfolio_weights_with_shorts(self):
        """Test portfolio weights with short positions."""
        weights = PortfolioWeights(
            weights={
                "STOCK0": Decimal("0.50"),
                "STOCK1": Decimal("0.30"),
                "STOCK2": Decimal("-0.20"),
                "STOCK3": Decimal("-0.10"),
            },
            optimization_method=OptimizationMethod.MEAN_VARIANCE,
        )

        assert weights.long_exposure == Decimal("0.80")
        assert weights.short_exposure == Decimal("0.30")
        assert weights.gross_exposure == Decimal("1.10")
        assert weights.net_exposure == Decimal("0.50")


class TestPortfolioConstructor:
    """Tests for PortfolioConstructor class."""

    def test_initialization(self, portfolio_constructor_config):
        """Test portfolio constructor initialization."""
        constructor = PortfolioConstructor(portfolio_constructor_config)

        assert constructor.name == "test_constructor"
        assert constructor.optimization_method == OptimizationMethod.MEAN_VARIANCE
        assert constructor.drift_threshold == Decimal("0.05")

    def test_construct_portfolio_equal_weight(self, sample_alpha_views):
        """Test equal-weight portfolio construction."""
        config = {"optimization_method": "equal_weight"}
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views)

        assert isinstance(weights, PortfolioWeights)
        assert len(weights.weights) == len(sample_alpha_views)
        assert weights.optimization_method == OptimizationMethod.EQUAL_WEIGHT

        # All weights should be approximately equal
        weight_values = list(weights.weights.values())
        expected_weight = Decimal("1.0") / Decimal(str(len(sample_alpha_views)))
        for w in weight_values:
            assert abs(w - expected_weight) < Decimal("0.01")

    def test_construct_portfolio_alpha_rank(self, sample_alpha_views):
        """Test alpha-rank portfolio construction."""
        config = {"optimization_method": "alpha_rank"}
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views)

        assert isinstance(weights, PortfolioWeights)
        assert len(weights.weights) > 0

        # Higher alpha * confidence should get higher weight
        best_stock = max(sample_alpha_views, key=lambda v: v.expected_return * v.confidence)
        assert best_stock.symbol in weights.weights

    def test_construct_portfolio_mean_variance(self, sample_alpha_views, sample_returns):
        """Test mean-variance portfolio construction."""
        config = {"optimization_method": "mean_variance", "risk_aversion": 1.0}
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views, returns=sample_returns)

        assert isinstance(weights, PortfolioWeights)
        assert weights.optimization_method == OptimizationMethod.MEAN_VARIANCE

        # Weights should sum to approximately 1
        total_weight = sum(weights.weights.values())
        assert abs(total_weight - Decimal("1.0")) < Decimal("0.05")

    def test_filter_by_constraints(self, portfolio_constructor_config, sample_alpha_views):
        """Test filtering alpha views by constraints."""
        constructor = PortfolioConstructor(portfolio_constructor_config)

        # Add some low-confidence views
        all_views = sample_alpha_views + [
            AlphaView(
                symbol="STOCK5",
                expected_return=0.01,  # Low return
                confidence=0.4,  # Low confidence
                alpha_source="momentum",
                holding_period=5,
            ),
        ]

        filtered = constructor._filter_by_constraints(all_views)

        # Low-confidence view should be filtered out
        assert "STOCK5" not in [v.symbol for v in filtered]

    def test_should_rebalance_no_drift(self, portfolio_constructor_config):
        """Test rebalancing decision when there's no drift."""
        constructor = PortfolioConstructor(portfolio_constructor_config)

        current_weights = {"STOCK0": Decimal("0.25"), "STOCK1": Decimal("0.25")}
        target_weights = {"STOCK0": Decimal("0.26"), "STOCK1": Decimal("0.24")}

        recommendation = constructor.should_rebalance(
            current_weights, target_weights, Decimal("1000000")
        )

        assert isinstance(recommendation, RebalanceRecommendation)
        # Small drift should not trigger rebalance
        assert recommendation.should_rebalance is False

    def test_should_rebalance_with_drift(self, portfolio_constructor_config):
        """Test rebalancing decision when there's significant drift."""
        constructor = PortfolioConstructor(portfolio_constructor_config)

        current_weights = {"STOCK0": Decimal("0.30"), "STOCK1": Decimal("0.20")}
        target_weights = {"STOCK0": Decimal("0.15"), "STOCK1": Decimal("0.35")}

        recommendation = constructor.should_rebalance(
            current_weights, target_weights, Decimal("1000000")
        )

        assert isinstance(recommendation, RebalanceRecommendation)
        # Large drift should trigger rebalance
        assert recommendation.should_rebalance is True
        assert recommendation.trigger == RebalanceTrigger.DRIFT

    def test_construct_portfolio_with_no_views(self):
        """Test portfolio construction with no alpha views."""
        constructor = PortfolioConstructor({})

        weights = constructor.construct_portfolio([])

        assert isinstance(weights, PortfolioWeights)
        assert len(weights.weights) == 0


class TestOptimizationMethods:
    """Tests for different optimization methods."""

    def test_min_variance_optimization(self, sample_alpha_views, sample_returns):
        """Test minimum variance optimization."""
        config = {"optimization_method": "min_variance"}
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views, returns=sample_returns)

        assert weights.optimization_method == OptimizationMethod.MIN_VARIANCE
        assert len(weights.weights) > 0

    def test_risk_parity_optimization(self, sample_alpha_views, sample_returns):
        """Test risk parity optimization."""
        config = {"optimization_method": "risk_parity"}
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views, returns=sample_returns)

        assert weights.optimization_method == OptimizationMethod.RISK_PARITY
        assert len(weights.weights) > 0

    def test_max_sharpe_optimization(self, sample_alpha_views, sample_returns):
        """Test maximum Sharpe ratio optimization."""
        config = {
            "optimization_method": "max_sharpe",
            "risk_free_rate": 0.02,
        }
        constructor = PortfolioConstructor(config)

        weights = constructor.construct_portfolio(sample_alpha_views, returns=sample_returns)

        assert weights.optimization_method == OptimizationMethod.MAX_SHARPE
        assert len(weights.weights) > 0


class TestPortfolioConstructorFactory:
    """Tests for the portfolio constructor factory function."""

    def test_get_portfolio_constructor(self):
        """Test factory creates portfolio constructor."""
        config = {
            "optimization_method": "mean_variance",
            "constraints": {"max_position_size": 0.20},
        }

        constructor = get_portfolio_constructor(config)

        assert isinstance(constructor, PortfolioConstructor)
        assert constructor.optimization_method == OptimizationMethod.MEAN_VARIANCE

    def test_constructor_with_risk_model(self):
        """Test constructor with risk model."""
        config = {
            "risk_model": {"model_type": "covariance"},
        }

        constructor = get_portfolio_constructor(config)

        assert constructor.risk_model is not None

    def test_constructor_with_cost_model(self):
        """Test constructor with cost model."""
        config = {
            "cost_model": {"model_type": "commission"},
        }

        constructor = get_portfolio_constructor(config)

        assert constructor.cost_model is not None


class TestRebalanceRecommendation:
    """Tests for RebalanceRecommendation dataclass."""

    def test_rebalance_recommendation_creation(self):
        """Test creating a rebalance recommendation."""
        recommendation = RebalanceRecommendation(
            should_rebalance=True,
            trigger=RebalanceTrigger.DRIFT,
            reason="Weight drift exceeds threshold",
            trades=[("STOCK0", Decimal("0.30"), Decimal("0.20"))],
            estimated_cost=Decimal("1000"),
            expected_benefit=Decimal("5000"),
        )

        assert recommendation.should_rebalance is True
        assert recommendation.trigger == RebalanceTrigger.DRIFT
        assert len(recommendation.trades) == 1
        assert recommendation.estimated_benefit > recommendation.estimated_cost
