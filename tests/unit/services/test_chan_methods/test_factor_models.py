"""
Tests for Ernest Chan Factor Models Implementation
"""

import pytest
import numpy as np
import pandas as pd
from app.services.factor_models import (
    FamaFrenchFactorModel,
    APTModel,
    StatisticalArbitrage,
    calculate_factor_exposure,
    create_factor_portfolio,
)


class TestFamaFrenchFactorModel:
    """Test Fama-French factor model."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        n = 252  # 1 year of daily data

        asset_returns = pd.Series(
            np.random.normal(0.0005, 0.02, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D')
        )

        market_returns = pd.Series(
            np.random.normal(0.0003, 0.015, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D')
        )

        smb_returns = pd.Series(
            np.random.normal(0.0001, 0.01, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D')
        )

        hml_returns = pd.Series(
            np.random.normal(0.0002, 0.008, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D')
        )

        return {
            'asset_returns': asset_returns,
            'market_returns': market_returns,
            'smb_returns': smb_returns,
            'hml_returns': hml_returns,
        }

    def test_initialization(self):
        """Test model initialization."""
        model = FamaFrenchFactorModel(model_type="three_factor")
        assert model.model_type == "three_factor"
        assert not model.fitted
        assert model.last_result is None

    def test_fit_three_factor_model(self, sample_data):
        """Test fitting 3-factor model."""
        model = FamaFrenchFactorModel(model_type="three_factor")

        result = model.fit(
            asset_returns=sample_data['asset_returns'],
            market_returns=sample_data['market_returns'],
            smb_returns=sample_data['smb_returns'],
            hml_returns=sample_data['hml_returns'],
        )

        assert model.fitted
        assert result is not None
        assert result.factor_loadings is not None
        assert result.beta_market is not None
        assert result.beta_smb is not None
        assert result.beta_hml is not None
        assert 0 <= result.r_squared <= 1

    def test_fit_insufficient_data(self):
        """Test fitting with insufficient data."""
        model = FamaFrenchFactorModel()

        short_returns = pd.Series([0.01, 0.02, -0.01])

        with pytest.raises(ValueError):
            model.fit(
                asset_returns=short_returns,
                market_returns=short_returns,
                smb_returns=short_returns,
                hml_returns=short_returns,
            )

    def test_prediction(self, sample_data):
        """Test prediction with fitted model."""
        model = FamaFrenchFactorModel()

        model.fit(
            asset_returns=sample_data['asset_returns'],
            market_returns=sample_data['market_returns'],
            smb_returns=sample_data['smb_returns'],
            hml_returns=sample_data['hml_returns'],
        )

        from app.services.factor_models import FactorReturns

        factor_returns = FactorReturns(
            market_return=0.001,
            smb_return=0.0005,
            hml_return=0.0003,
            rmw_return=0.0,
            cma_return=0.0,
            momentum_return=0.0,
        )

        predicted = model.predict(factor_returns)

        assert isinstance(predicted, float)
        assert predicted is not None


class TestAPTModel:
    """Test APT model."""

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns data."""
        np.random.seed(42)
        n = 252
        n_assets = 10

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            index=pd.date_range('2023-01-01', periods=n, freq='D'),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        return returns

    def test_initialization(self):
        """Test APT initialization."""
        model = APTModel(n_factors=5)
        assert model.n_factors == 5
        assert not model.fitted

    def test_fit(self, sample_returns):
        """Test fitting APT model."""
        model = APTModel(n_factors=5)
        model.fit(sample_returns)

        assert model.fitted
        assert model.factor_loadings is not None
        assert model.factor_returns is not None
        assert model.factor_loadings.shape == (10, 5)

    def test_get_factor_loadings(self, sample_returns):
        """Test getting factor loadings."""
        model = APTModel(n_factors=3)
        model.fit(sample_returns)

        loadings = model.get_factor_loadings()

        assert isinstance(loadings, pd.DataFrame)
        assert loadings.shape == (10, 3)
        assert list(loadings.columns) == ['factor_1', 'factor_2', 'factor_3']

    def test_get_explained_variance_ratio(self, sample_returns):
        """Test explained variance ratio."""
        model = APTModel(n_factors=3)
        model.fit(sample_returns)

        ratios = model.get_explained_variance_ratio()

        assert isinstance(ratios, np.ndarray)
        assert len(ratios) == 3
        assert all(r >= 0 for r in ratios)
        assert sum(ratios) <= 1.0  # Should explain less than 100% variance

    def test_predict_portfolio_risk(self, sample_returns):
        """Test portfolio risk prediction."""
        model = APTModel(n_factors=5)
        model.fit(sample_returns)

        weights = np.ones(10) / 10

        risk = model.predict_portfolio_risk(weights)

        assert isinstance(risk, float)
        assert risk > 0


class TestStatisticalArbitrage:
    """Test statistical arbitrage strategies."""

    @pytest.fixture
    def setup_data(self):
        """Create test data."""
        np.random.seed(42)
        n = 252

        asset_returns = pd.Series(
            np.random.normal(0.0005, 0.02, n),
            index=pd.date_range('2023-01-01', periods=n, freq='D')
        )

        factor_returns = pd.DataFrame({
            'market': np.random.normal(0.0003, 0.015, n),
            'smb': np.random.normal(0.0001, 0.01, n),
            'hml': np.random.normal(0.0002, 0.008, n),
        }, index=pd.date_range('2023-01-01', periods=n, freq='D'))

        return {'asset_returns': asset_returns, 'factor_returns': factor_returns}

    def test_initialization(self, setup_data):
        """Test initialization."""
        factor_model = FamaFrenchFactorModel()
        factor_model.fit(
            setup_data['asset_returns'],
            setup_data['factor_returns']['market'],
            setup_data['factor_returns']['smb'],
            setup_data['factor_returns']['hml'],
        )

        arb = StatisticalArbitrage(factor_model)

        assert arb.factor_model == factor_model
        assert arb.z_score_threshold == 2.0

    def test_calculate_residuals(self, setup_data):
        """Test residual calculation."""
        factor_model = FamaFrenchFactorModel()
        factor_model.fit(
            setup_data['asset_returns'],
            setup_data['factor_returns']['market'],
            setup_data['factor_returns']['smb'],
            setup_data['factor_returns']['hml'],
        )

        arb = StatisticalArbitrage(factor_model)

        residuals = arb.calculate_residuals(
            setup_data['asset_returns'],
            setup_data['factor_returns']
        )

        assert isinstance(residuals, pd.Series)
        assert len(residuals) == len(setup_data['asset_returns'])

    def test_generate_signals(self, setup_data):
        """Test signal generation."""
        factor_model = FamaFrenchFactorModel()
        factor_model.fit(
            setup_data['asset_returns'],
            setup_data['factor_returns']['market'],
            setup_data['factor_returns']['smb'],
            setup_data['factor_returns']['hml'],
        )

        arb = StatisticalArbitrage(factor_model, z_score_threshold=1.5)

        signals = arb.generate_signals(
            setup_data['asset_returns'],
            setup_data['factor_returns']
        )

        assert isinstance(signals, pd.Series)
        assert set(signals.unique()).issubset({-1, 0, 1})


class TestUtilityFunctions:
    """Test utility functions."""

    def test_calculate_factor_exposure(self):
        """Test factor exposure calculation."""
        np.random.seed(42)
        n = 100

        asset_returns = pd.Series(np.random.normal(0, 0.02, n))
        factor_returns = pd.DataFrame({
            'factor1': np.random.normal(0, 0.01, n),
            'factor2': np.random.normal(0, 0.015, n),
            'factor3': np.random.normal(0, 0.008, n),
        })

        exposure = calculate_factor_exposure(asset_returns, factor_returns)

        assert isinstance(exposure, pd.Series)
        assert len(exposure) == 3
        assert list(exposure.index) == ['factor1', 'factor2', 'factor3']

    def test_create_factor_portfolio(self):
        """Test factor portfolio creation."""
        np.random.seed(42)
        n = 252
        n_assets = 20

        returns = pd.DataFrame(
            np.random.normal(0.0005, 0.02, (n, n_assets)),
            columns=[f'asset_{i}' for i in range(n_assets)]
        )

        factor_returns, weights = create_factor_portfolio(returns, n_factors=5)

        assert factor_returns.shape[1] == 5
        assert weights.shape == (n_assets, 5)
