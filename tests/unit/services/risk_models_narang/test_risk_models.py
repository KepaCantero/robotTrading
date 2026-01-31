"""
Tests for Risk Models - Narang "Inside the Black Box" Chapter 4
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal

from app.services.risk_models_narang import (
    RiskFactorType,
    RiskModelType,
    RiskFactor,
    RiskBudget,
    RiskMetrics,
    RiskConstraint,
    RiskModel,
    FactorRiskModel,
    CovarianceRiskModel,
    get_risk_model,
)


@pytest.fixture
def sample_returns():
    """Create sample returns data for testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")

    # Create correlated returns
    n_assets = 5
    symbols = [f"STOCK{i}" for i in range(n_assets)]

    # Generate correlated returns using Cholesky decomposition
    cov = np.array(
        [
            [0.0004, 0.0002, 0.0001, 0.00005, 0.00003],
            [0.0002, 0.0003, 0.00015, 0.00008, 0.00004],
            [0.0001, 0.00015, 0.00025, 0.0001, 0.00005],
            [0.00005, 0.00008, 0.0001, 0.0002, 0.00006],
            [0.00003, 0.00004, 0.00005, 0.00006, 0.00015],
        ]
    )

    L = np.linalg.cholesky(cov)
    random_returns = np.random.randn(100, n_assets)
    correlated_returns = random_returns @ L.T

    returns = pd.DataFrame(correlated_returns, index=dates, columns=symbols)

    return returns


@pytest.fixture
def sample_factor_loadings():
    """Create sample factor loadings for testing."""
    symbols = [f"STOCK{i}" for i in range(5)]
    factors = ["Value", "Growth", "Momentum", "Size", "Quality"]

    np.random.seed(42)
    loadings = np.random.randn(len(symbols), len(factors)) * 0.3

    return pd.DataFrame(loadings, index=symbols, columns=factors)


@pytest.fixture
def sample_portfolio_weights():
    """Create sample portfolio weights."""
    symbols = [f"STOCK{i}" for i in range(5)]
    weights = np.array([0.25, 0.25, 0.20, 0.15, 0.15])
    return dict(zip(symbols, weights))


class TestRiskModel:
    """Tests for base RiskModel class."""

    def test_initialization(self):
        """Test risk model initialization."""
        config = {"name": "test_risk_model", "lookup_days": 252}
        model = RiskModel(config)

        assert model.name == "test_risk_model"
        assert model.lookup_days == 252

    def test_add_risk_factor(self):
        """Test adding a risk factor."""
        model = RiskModel({})

        factor = RiskFactor(
            name="Value",
            factor_type=RiskFactorType.STYLE,
            exposures={"STOCK0": 0.5, "STOCK1": -0.3},
            returns=pd.Series([0.01, 0.02, -0.01]),
        )

        model.add_risk_factor(factor)

        assert "Value" in model.risk_factors
        assert model.risk_factors["Value"].factor_type == RiskFactorType.STYLE

    def test_add_constraint(self):
        """Test adding a risk constraint."""
        model = RiskModel({})

        constraint = RiskConstraint(
            name="max_beta",
            constraint_type="max_beta",
            max_value=Decimal("1.5"),
        )

        model.add_constraint(constraint)

        assert len(model.risk_constraints) == 1
        assert model.risk_constraints[0].name == "max_beta"

    def test_estimate_covariance_matrix_sample(self, sample_returns):
        """Test sample covariance estimation."""
        model = RiskModel({})
        cov = model.estimate_covariance_matrix(sample_returns, method="sample")

        assert cov.shape == (5, 5)
        assert np.allclose(cov.values, cov.values.T)  # Symmetric

    def test_estimate_covariance_matrix_shrinkage(self, sample_returns):
        """Test shrinkage covariance estimation."""
        model = RiskModel({})
        cov = model.estimate_covariance_matrix(sample_returns, method="shrinkage")

        assert cov.shape == (5, 5)
        assert np.allclose(cov.values, cov.values.T)  # Symmetric

    def test_calculate_factor_exposures(self, sample_portfolio_weights, sample_factor_loadings):
        """Test factor exposure calculation."""
        model = RiskModel({})
        exposures = model.calculate_factor_exposures(
            sample_portfolio_weights, sample_factor_loadings
        )

        assert len(exposures) == len(sample_factor_loadings.columns)
        assert all(isinstance(v, float) for v in exposures.values())

    def test_forecast_risk(self, sample_portfolio_weights, sample_returns):
        """Test risk forecasting."""
        model = RiskModel({})
        risk_metrics = model.forecast_risk(sample_portfolio_weights, sample_returns)

        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.total_risk > 0
        assert risk_metrics.var_95 < 0  # VaR should be negative
        assert risk_metrics.beta > 0

    def test_apply_factor_constraints(self, sample_portfolio_weights, sample_factor_loadings):
        """Test applying factor constraints."""
        model = RiskModel({})

        weights_series = pd.Series(sample_portfolio_weights)
        constrained = model.apply_factor_constraints(
            weights_series,
            sample_factor_loadings,
            max_factor_exposure=0.15,
        )

        # Check that weights sum to 1
        assert abs(constrained.sum() - 1.0) < 0.01

        # Check that factor exposures are within limits
        exposures = model.calculate_factor_exposures(constrained.to_dict(), sample_factor_loadings)
        for exposure in exposures.values():
            assert abs(exposure) <= 0.2  # Allow small tolerance

    def test_validate_portfolio_risk(self, sample_portfolio_weights, sample_returns):
        """Test portfolio risk validation."""
        config = {
            "max_portfolio_risk": 0.30,  # 30% vol
            "max_var_95": -0.10,  # -10% daily VaR
            "max_beta": 2.0,
            "min_beta": 0.3,
        }
        model = RiskModel(config)

        is_valid, issues = model.validate_portfolio_risk(sample_portfolio_weights, sample_returns)

        # Check that validation returns a tuple
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)


class TestFactorRiskModel:
    """Tests for FactorRiskModel."""

    def test_initialization(self):
        """Test factor risk model initialization."""
        config = {"name": "test_factor_model"}
        model = FactorRiskModel(config)

        assert model.model_type == RiskModelType.FACTOR_MODEL

    def test_estimate_factor_returns(self, sample_returns, sample_factor_loadings):
        """Test factor return estimation."""
        model = FactorRiskModel({})

        # Single period returns
        single_period_returns = sample_returns.iloc[-1]

        factor_returns = model.estimate_factor_returns(
            single_period_returns, sample_factor_loadings
        )

        if factor_returns:
            # Should return estimates for some factors
            assert all(isinstance(v, float) for v in factor_returns.values())

    def test_calculate_specific_risk(self, sample_returns, sample_factor_loadings):
        """Test specific risk calculation."""
        model = FactorRiskModel({})

        specific_risk = model.calculate_specific_risk(sample_returns, sample_factor_loadings)

        # Should return risk estimates for assets
        assert len(specific_risk) > 0
        assert all(v >= 0 for v in specific_risk.values())


class TestCovarianceRiskModel:
    """Tests for CovarianceRiskModel."""

    def test_initialization(self):
        """Test covariance risk model initialization."""
        config = {"name": "test_cov_model"}
        model = CovarianceRiskModel(config)

        assert model.model_type == RiskModelType.COVARIANCE_MATRIX

    def test_forecast_risk(self, sample_portfolio_weights, sample_returns):
        """Test risk forecasting with covariance model."""
        model = CovarianceRiskModel({})
        risk_metrics = model.forecast_risk(sample_portfolio_weights, sample_returns)

        assert isinstance(risk_metrics, RiskMetrics)
        assert risk_metrics.total_risk > 0


class TestRiskBudget:
    """Tests for risk budgeting functionality."""

    def test_calculate_risk_budget(self, sample_portfolio_weights, sample_factor_loadings):
        """Test risk budget calculation."""
        model = RiskModel({})

        # Add a constraint for a factor
        constraint = RiskConstraint(
            name="max_value_exposure",
            constraint_type="max_exposure",
            factor="Value",
            max_value=Decimal("0.15"),
        )
        model.add_constraint(constraint)

        budgets = model.calculate_risk_budget(sample_portfolio_weights, sample_factor_loadings)

        assert len(budgets) > 0
        for budget in budgets:
            assert isinstance(budget, RiskBudget)
            assert budget.max_exposure > 0
            # Utilization can be > 1 if exposure exceeds constraint
            assert budget.utilization >= 0


class TestRiskModelFactory:
    """Tests for the risk model factory function."""

    def test_get_factor_model(self):
        """Test factory creates factor model."""
        config = {"model_type": "factor"}
        model = get_risk_model(config)

        assert isinstance(model, FactorRiskModel)

    def test_get_covariance_model(self):
        """Test factory creates covariance model."""
        config = {"model_type": "covariance"}
        model = get_risk_model(config)

        assert isinstance(model, CovarianceRiskModel)

    def test_default_model(self):
        """Test factory returns default model for unknown type."""
        config = {"model_type": "unknown"}
        model = get_risk_model(config)

        assert isinstance(model, RiskModel)


class TestRiskConstraint:
    """Tests for RiskConstraint dataclass."""

    def test_constraint_creation(self):
        """Test creating a risk constraint."""
        constraint = RiskConstraint(
            name="max_sector_tech",
            constraint_type="max_exposure",
            factor="Technology",
            max_value=Decimal("0.25"),
            penalty_weight=Decimal("2.0"),
        )

        assert constraint.name == "max_sector_tech"
        assert constraint.constraint_type == "max_exposure"
        assert constraint.max_value == Decimal("0.25")


class TestRiskMetrics:
    """Tests for RiskMetrics dataclass."""

    def test_risk_metrics_creation(self):
        """Test creating risk metrics."""
        metrics = RiskMetrics(
            total_risk=Decimal("0.15"),
            systematic_risk=Decimal("0.12"),
            idiosyncratic_risk=Decimal("0.03"),
            factor_exposures={"Value": Decimal("0.1"), "Momentum": Decimal("0.2")},
            var_95=Decimal("-0.02"),
            cvar_95=Decimal("-0.03"),
            max_drawdown=Decimal("-0.10"),
            beta=Decimal("1.1"),
            correlation_to_market=Decimal("0.85"),
        )

        assert metrics.total_risk == Decimal("0.15")
        assert metrics.systematic_risk + metrics.idiosyncratic_risk == metrics.total_risk
        assert metrics.beta > 1  # High beta
        assert metrics.var_95 < 0  # Negative VaR
