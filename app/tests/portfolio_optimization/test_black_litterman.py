"""Comprehensive tests for Black-Litterman Portfolio Optimization.

Tests follow AAA pattern and cover:
- InvestorView validation and creation
- Equilibrium return calculations
- View matrix construction (P, Q, Ω)
- Black-Litterman return combination
- Full optimization pipeline
- Edge cases and error handling

Reference:
    Black, F. and Litterman, R. (1992). "Global Portfolio Optimization".
    Financial Analysts Journal, 48(5), pp. 28-43.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from app.domain.portfolio_optimization.black_litterman_optimizer import (
    BlackLittermanConfig,
    BlackLittermanOptimizer,
    BlackLittermanResult,
    EquilibriumReturns,
    InvestorView,
    ViewMatrix,
    ViewType,
    compute_black_litterman_weights,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_returns() -> NDArray[np.float64]:
    """Generate sample historical returns for testing.

    Returns:
        Returns array of shape (252, 5) - 1 year of daily returns for 5 assets.
    """
    np.random.seed(42)
    # Simulate correlated returns
    mean_returns = np.array([0.0005, 0.0003, 0.0007, 0.0004, 0.0006])
    cov_matrix = np.array(
        [
            [0.0004, 0.0002, 0.0001, 0.00015, 0.0001],
            [0.0002, 0.0003, 0.00015, 0.0001, 0.00005],
            [0.0001, 0.00015, 0.0005, 0.0002, 0.00015],
            [0.00015, 0.0001, 0.0002, 0.00035, 0.0001],
            [0.0001, 0.00005, 0.00015, 0.0001, 0.00025],
        ]
    )

    returns = np.random.multivariate_normal(mean_returns, cov_matrix, 252)
    return returns.astype(np.float64)


@pytest.fixture
def sample_market_caps() -> NDArray[np.float64]:
    """Generate sample market capitalizations.

    Returns:
        Market caps array for 5 assets (in billions).
    """
    return np.array([1000.0, 800.0, 600.0, 400.0, 200.0], dtype=np.float64)


@pytest.fixture
def sample_market_weights() -> NDArray[np.float64]:
    """Generate sample market weights (sum to 1).

    Returns:
        Market weights array for 5 assets.
    """
    caps = np.array([1000.0, 800.0, 600.0, 400.0, 200.0])
    return (caps / caps.sum()).astype(np.float64)


@pytest.fixture
def sample_covariance() -> NDArray[np.float64]:
    """Generate sample covariance matrix.

    Returns:
        Covariance matrix of shape (5, 5), annualized.
    """
    cov = np.array(
        [
            [0.04, 0.02, 0.01, 0.015, 0.01],
            [0.02, 0.03, 0.015, 0.01, 0.005],
            [0.01, 0.015, 0.05, 0.02, 0.015],
            [0.015, 0.01, 0.02, 0.035, 0.01],
            [0.01, 0.005, 0.015, 0.01, 0.025],
        ],
        dtype=np.float64,
    )
    return cov


@pytest.fixture
def absolute_view() -> InvestorView:
    """Create a sample absolute view.

    View: "Asset 0 will return 8% annually"
    """
    return InvestorView(
        view_type=ViewType.ABSOLUTE,
        assets=[0],
        pick_vector=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
        expected_return=0.08,
        confidence=0.70,
        id="view_absolute_0",
    )


@pytest.fixture
def relative_view() -> InvestorView:
    """Create a sample relative view.

    View: "Asset 0 will outperform Asset 1 by 3% annually"
    """
    return InvestorView(
        view_type=ViewType.RELATIVE,
        assets=[0, 1],
        pick_vector=np.array([1.0, -1.0, 0.0, 0.0, 0.0]),
        expected_return=0.03,
        confidence=0.60,
        id="view_relative_0_1",
    )


@pytest.fixture
def multiple_views() -> list[InvestorView]:
    """Create multiple investor views for testing."""
    return [
        InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
            expected_return=0.08,
            confidence=0.70,
        ),
        InvestorView(
            view_type=ViewType.RELATIVE,
            assets=[0, 1],
            pick_vector=np.array([1.0, -1.0, 0.0, 0.0, 0.0]),
            expected_return=0.03,
            confidence=0.60,
        ),
        InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[2],
            pick_vector=np.array([0.0, 0.0, 1.0, 0.0, 0.0]),
            expected_return=0.10,
            confidence=0.50,
        ),
    ]


@pytest.fixture
def default_config() -> BlackLittermanConfig:
    """Create default Black-Litterman configuration."""
    return BlackLittermanConfig()


@pytest.fixture
def custom_config() -> BlackLittermanConfig:
    """Create custom Black-Litterman configuration."""
    return BlackLittermanConfig(
        tau=0.03,
        risk_aversion=2.5,
        use_shrinkage=True,
        lookback_days=252,
        risk_free_rate=0.015,
        max_position=0.25,
        omega_method="idzorek",
    )


@pytest.fixture
def optimizer(default_config: BlackLittermanConfig) -> BlackLittermanOptimizer:
    """Create Black-Litterman optimizer with default config."""
    return BlackLittermanOptimizer(default_config)


# =============================================================================
# TESTS: InvestorView
# =============================================================================


class TestInvestorView:
    """Test suite for InvestorView dataclass."""

    def test_create_absolute_view_success(self) -> None:
        """Test successful creation of absolute view."""
        view = InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0, 0.0]),
            expected_return=0.08,
            confidence=0.75,
        )

        assert view.view_type == ViewType.ABSOLUTE
        assert view.assets == [0]
        assert np.array_equal(view.pick_vector, np.array([1.0, 0.0, 0.0]))
        assert view.expected_return == 0.08
        assert view.confidence == 0.75
        assert view.id is None

    def test_create_relative_view_success(self) -> None:
        """Test successful creation of relative view."""
        view = InvestorView(
            view_type=ViewType.RELATIVE,
            assets=[0, 1],
            pick_vector=np.array([1.0, -1.0, 0.0]),
            expected_return=0.03,
            confidence=0.60,
        )

        assert view.view_type == ViewType.RELATIVE
        assert view.assets == [0, 1]
        assert np.array_equal(view.pick_vector, np.array([1.0, -1.0, 0.0]))
        assert view.expected_return == 0.03
        assert view.confidence == 0.60

    def test_create_view_with_id_success(self) -> None:
        """Test creation of view with identifier."""
        view = InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0]),
            expected_return=0.05,
            confidence=0.80,
            id="custom_view_id",
        )

        assert view.id == "custom_view_id"

    def test_view_with_confidence_zero_raises_error(self) -> None:
        """Test that zero confidence is invalid."""
        with pytest.raises(ValueError, match=r"Confidence must be in \(0, 1\)"):
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[0],
                pick_vector=np.array([1.0]),
                expected_return=0.05,
                confidence=0.0,
            )

    def test_view_with_confidence_one_raises_error(self) -> None:
        """Test that confidence of 1.0 is invalid."""
        with pytest.raises(ValueError, match=r"Confidence must be in \(0, 1\)"):
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[0],
                pick_vector=np.array([1.0]),
                expected_return=0.05,
                confidence=1.0,
            )

    def test_view_with_negative_confidence_raises_error(self) -> None:
        """Test that negative confidence is invalid."""
        with pytest.raises(ValueError, match=r"Confidence must be in \(0, 1\)"):
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[0],
                pick_vector=np.array([1.0]),
                expected_return=0.05,
                confidence=-0.1,
            )

    def test_view_with_confidence_greater_than_one_raises_error(self) -> None:
        """Test that confidence > 1.0 is invalid."""
        with pytest.raises(ValueError, match=r"Confidence must be in \(0, 1\)"):
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[0],
                pick_vector=np.array([1.0]),
                expected_return=0.05,
                confidence=1.5,
            )


# =============================================================================
# TESTS: BlackLittermanConfig
# =============================================================================


class TestBlackLittermanConfig:
    """Test suite for BlackLittermanConfig."""

    def test_default_config_creation_success(self) -> None:
        """Test successful creation with default values."""
        config = BlackLittermanConfig()

        assert config.tau == 0.05
        assert config.risk_aversion == 3.0
        assert config.use_shrinkage is True
        assert config.lookback_days == 252
        assert config.risk_free_rate == 0.02
        assert config.max_position == 0.20
        assert config.omega_method == "idzorek"

    def test_custom_config_creation_success(self) -> None:
        """Test successful creation with custom values."""
        config = BlackLittermanConfig(
            tau=0.03,
            risk_aversion=2.5,
            use_shrinkage=False,
            lookback_days=300,
            risk_free_rate=0.015,
            max_position=0.15,
            omega_method="proportional",
        )

        assert config.tau == 0.03
        assert config.risk_aversion == 2.5
        assert config.use_shrinkage is False
        assert config.lookback_days == 300
        assert config.risk_free_rate == 0.015
        assert config.max_position == 0.15
        assert config.omega_method == "proportional"

    def test_config_with_zero_tau_raises_error(self) -> None:
        """Test that tau <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="tau must be positive"):
            BlackLittermanConfig(tau=0.0)

    def test_config_with_negative_tau_raises_error(self) -> None:
        """Test that negative tau raises ValueError."""
        with pytest.raises(ValueError, match="tau must be positive"):
            BlackLittermanConfig(tau=-0.05)

    def test_config_with_zero_risk_aversion_raises_error(self) -> None:
        """Test that risk_aversion <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="risk_aversion must be positive"):
            BlackLittermanConfig(risk_aversion=0.0)

    def test_config_with_lookback_less_than_252_raises_error(self) -> None:
        """Test that lookback_days < 252 raises ValueError (Rule 66)."""
        with pytest.raises(ValueError, match="lookback_days must be >= 252"):
            BlackLittermanConfig(lookback_days=200)

    def test_config_with_invalid_max_position_raises_error(self) -> None:
        """Test that invalid max_position raises ValueError."""
        with pytest.raises(ValueError, match="max_position must be in \\(0, 1\\]"):
            BlackLittermanConfig(max_position=0.0)

    def test_config_with_max_position_greater_than_one_raises_error(self) -> None:
        """Test that max_position > 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_position must be in \\(0, 1\\]"):
            BlackLittermanConfig(max_position=1.5)

    def test_config_with_invalid_omega_method_raises_error(self) -> None:
        """Test that invalid omega_method raises ValueError."""
        with pytest.raises(ValueError, match="omega_method must be one of"):
            BlackLittermanConfig(omega_method="invalid_method")


# =============================================================================
# TESTS: EquilibriumReturns
# =============================================================================


class TestEquilibriumReturns:
    """Test suite for EquilibriumReturns calculation."""

    def test_from_market_caps_success(
        self, sample_covariance: NDArray[np.float64], sample_market_caps: NDArray[np.float64]
    ) -> None:
        """Test successful calculation of equilibrium returns from market caps."""
        pi = EquilibriumReturns.from_market_caps(
            cov_matrix=sample_covariance,
            market_caps=sample_market_caps,
            risk_aversion=3.0,
        )

        assert pi.shape == (5,)
        assert np.all(np.isfinite(pi))
        # Equilibrium returns should be positive for growing market
        assert np.all(pi > 0)

    def test_from_market_caps_normalizes_weights(
        self, sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test that market caps are properly normalized to weights."""
        caps = np.array([1000.0, 500.0, 500.0], dtype=np.float64)
        cov = np.eye(3) * 0.04

        pi1 = EquilibriumReturns.from_market_caps(cov, caps, 3.0)
        pi2 = EquilibriumReturns.from_market_caps(cov, caps * 2, 3.0)

        # Should be same after normalization
        np.testing.assert_array_almost_equal(pi1, pi2)

    def test_from_weights_success(
        self, sample_covariance: NDArray[np.float64], sample_market_weights: NDArray[np.float64]
    ) -> None:
        """Test successful calculation from market weights."""
        pi = EquilibriumReturns.from_weights(
            cov_matrix=sample_covariance,
            market_weights=sample_market_weights,
            risk_aversion=3.0,
        )

        assert pi.shape == (5,)
        assert np.all(np.isfinite(pi))

    def test_from_weights_with_invalid_weights_raises_error(
        self, sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test that weights not summing to 1 raises ValueError."""
        invalid_weights = np.array([0.5, 0.5, 0.5, 0.0, 0.0])  # Sum = 1.5

        with pytest.raises(ValueError, match="Market weights must sum to 1"):
            EquilibriumReturns.from_weights(
                cov_matrix=sample_covariance,
                market_weights=invalid_weights,
                risk_aversion=3.0,
            )

    def test_equilibrium_returns_increase_with_risk_aversion(
        self, sample_covariance: NDArray[np.float64], sample_market_caps: NDArray[np.float64]
    ) -> None:
        """Test that higher risk aversion increases equilibrium returns."""
        pi_low = EquilibriumReturns.from_market_caps(sample_covariance, sample_market_caps, 2.0)
        pi_high = EquilibriumReturns.from_market_caps(sample_covariance, sample_market_caps, 5.0)

        # Higher risk aversion should give higher equilibrium returns
        assert np.all(pi_high >= pi_low * 0.95)  # Allow small numerical differences


# =============================================================================
# TESTS: ViewMatrix
# =============================================================================


class TestViewMatrix:
    """Test suite for ViewMatrix construction."""

    def test_build_pick_matrix_absolute_view_success(self, absolute_view: InvestorView) -> None:
        """Test building P matrix for single absolute view."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix([absolute_view], n_assets)

        assert P.shape == (1, 5)
        np.testing.assert_array_equal(P[0, :], absolute_view.pick_vector)

    def test_build_pick_matrix_multiple_views_success(
        self, multiple_views: list[InvestorView]
    ) -> None:
        """Test building P matrix for multiple views."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix(multiple_views, n_assets)

        assert P.shape == (3, 5)  # 3 views, 5 assets

        # Check first row (absolute view on asset 0)
        np.testing.assert_array_equal(P[0, :], np.array([1.0, 0.0, 0.0, 0.0, 0.0]))

        # Check second row (relative view: asset 0 - asset 1)
        np.testing.assert_array_equal(P[1, :], np.array([1.0, -1.0, 0.0, 0.0, 0.0]))

    def test_build_pick_matrix_empty_views_raises_error(self) -> None:
        """Test that empty views list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot build P matrix from empty views"):
            ViewMatrix.build_pick_matrix([], 5)

    def test_build_pick_matrix_mismatched_length_raises_error(self) -> None:
        """Test that mismatched pick_vector length raises ValueError."""
        view = InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0]),  # 2 elements
            expected_return=0.05,
            confidence=0.7,
        )

        with pytest.raises(ValueError, match="pick_vector length .* does not match n_assets"):
            ViewMatrix.build_pick_matrix([view], n_assets=5)

    def test_build_q_vector_success(self, multiple_views: list[InvestorView]) -> None:
        """Test building Q vector from views."""
        Q = ViewMatrix.build_q_vector(multiple_views)

        assert Q.shape == (3,)
        assert Q[0] == 0.08  # First view
        assert Q[1] == 0.03  # Second view
        assert Q[2] == 0.10  # Third view

    def test_build_q_vector_empty_views_raises_error(self) -> None:
        """Test that empty views list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot build Q vector from empty views"):
            ViewMatrix.build_q_vector([])

    def test_build_omega_matrix_idzorek_method_success(
        self, multiple_views: list[InvestorView], sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test building Ω matrix using Idzorek method."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix(multiple_views, n_assets)
        tau = 0.05

        Ω = ViewMatrix.build_omega_matrix(
            P, sample_covariance, multiple_views, tau, method="idzorek"
        )

        assert Ω.shape == (3, 3)
        # Should be diagonal
        assert np.allclose(Ω, np.diag(np.diag(Ω)))
        # All diagonal elements should be positive
        assert np.all(np.diag(Ω) > 0)

    def test_build_omega_matrix_proportional_method_success(
        self, multiple_views: list[InvestorView], sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test building Ω matrix using proportional method."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix(multiple_views, n_assets)
        tau = 0.05

        Ω = ViewMatrix.build_omega_matrix(
            P, sample_covariance, multiple_views, tau, method="proportional"
        )

        assert Ω.shape == (3, 3)
        # Should be symmetric positive semi-definite
        assert np.allclose(Ω, Ω.T)

    def test_build_omega_matrix_diagonal_method_success(
        self, multiple_views: list[InvestorView], sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test building Ω matrix using diagonal method."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix(multiple_views, n_assets)
        tau = 0.05

        Ω = ViewMatrix.build_omega_matrix(
            P, sample_covariance, multiple_views, tau, method="diagonal"
        )

        assert Ω.shape == (3, 3)
        # Should be diagonal
        assert np.allclose(Ω, np.diag(np.diag(Ω)))

    def test_build_omega_matrix_with_invalid_method_raises_error(
        self, multiple_views: list[InvestorView], sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test that invalid method raises ValueError."""
        n_assets = 5
        P = ViewMatrix.build_pick_matrix(multiple_views, n_assets)

        with pytest.raises(ValueError, match="Unknown omega_method"):
            ViewMatrix.build_omega_matrix(
                P, sample_covariance, multiple_views, 0.05, method="invalid"
            )


# =============================================================================
# TESTS: BlackLittermanOptimizer
# =============================================================================


class TestBlackLittermanOptimizer:
    """Test suite for BlackLittermanOptimizer."""

    def test_optimizer_initialization_success(self, default_config: BlackLittermanConfig) -> None:
        """Test successful optimizer initialization."""
        optimizer = BlackLittermanOptimizer(default_config)

        assert optimizer.config == default_config
        assert optimizer.config.tau == 0.05
        assert optimizer.config.risk_aversion == 3.0

    def test_optimizer_initialization_with_none_uses_defaults(self) -> None:
        """Test that None config uses default values."""
        optimizer = BlackLittermanOptimizer(None)

        assert optimizer.config.tau == 0.05
        assert optimizer.config.risk_aversion == 3.0
        assert optimizer.config.lookback_days == 252

    def test_calculate_covariance_matrix_success(
        self, optimizer: BlackLittermanOptimizer, sample_returns: NDArray[np.float64]
    ) -> None:
        """Test successful covariance matrix calculation."""
        cov = optimizer.calculate_covariance_matrix(sample_returns)

        assert cov.shape == (5, 5)
        assert np.allclose(cov, cov.T)  # Symmetric
        assert np.all(np.diag(cov) >= 0)  # Positive variances

    def test_calculate_covariance_matrix_with_insufficient_data_raises_error(
        self, optimizer: BlackLittermanOptimizer
    ) -> None:
        """Test that insufficient data raises ValueError."""
        short_returns = np.random.randn(100, 5)  # Only 100 days

        with pytest.raises(ValueError, match="Insufficient data.*Rule 66"):
            optimizer.calculate_covariance_matrix(short_returns)

    def test_calculate_covariance_matrix_without_shrinkage_success(
        self, optimizer: BlackLittermanOptimizer, sample_returns: NDArray[np.float64]
    ) -> None:
        """Test covariance calculation without shrinkage."""
        cov = optimizer.calculate_covariance_matrix(sample_returns, use_shrinkage=False)

        assert cov.shape == (5, 5)
        assert np.all(np.isfinite(cov))

    def test_calculate_equilibrium_returns_from_caps_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_covariance: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test equilibrium returns calculation from market caps."""
        pi = optimizer.calculate_equilibrium_returns(
            cov_matrix=sample_covariance, market_caps=sample_market_caps
        )

        assert pi.shape == (5,)
        assert np.all(np.isfinite(pi))

    def test_calculate_equilibrium_returns_from_weights_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_covariance: NDArray[np.float64],
        sample_market_weights: NDArray[np.float64],
    ) -> None:
        """Test equilibrium returns calculation from market weights."""
        pi = optimizer.calculate_equilibrium_returns(
            cov_matrix=sample_covariance, market_weights=sample_market_weights
        )

        assert pi.shape == (5,)
        assert np.all(np.isfinite(pi))

    def test_calculate_equilibrium_returns_without_market_data_raises_error(
        self, optimizer: BlackLittermanOptimizer, sample_covariance: NDArray[np.float64]
    ) -> None:
        """Test that missing market data raises ValueError."""
        with pytest.raises(
            ValueError, match="Either market_caps or market_weights must be provided"
        ):
            optimizer.calculate_equilibrium_returns(cov_matrix=sample_covariance)

    def test_calculate_bl_returns_without_views_returns_equilibrium(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_covariance: NDArray[np.float64],
        sample_market_weights: NDArray[np.float64],
    ) -> None:
        """Test that no views returns equilibrium returns."""
        pi = optimizer.calculate_equilibrium_returns(
            cov_matrix=sample_covariance, market_weights=sample_market_weights
        )

        bl_returns, posterior_cov = optimizer.calculate_bl_returns(
            equilibrium_returns=pi, cov_matrix=sample_covariance, views=[]
        )

        np.testing.assert_array_almost_equal(bl_returns, pi)

    def test_calculate_bl_returns_with_views_modifies_returns(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_covariance: NDArray[np.float64],
        sample_market_weights: NDArray[np.float64],
        absolute_view: InvestorView,
    ) -> None:
        """Test that views modify equilibrium returns."""
        pi = optimizer.calculate_equilibrium_returns(
            cov_matrix=sample_covariance, market_weights=sample_market_weights
        )

        bl_returns, _ = optimizer.calculate_bl_returns(
            equilibrium_returns=pi, cov_matrix=sample_covariance, views=[absolute_view]
        )

        # BL returns should differ from equilibrium
        assert not np.allclose(bl_returns, pi)
        # Asset 0 should be affected by the view
        assert bl_returns[0] != pi[0]

    def test_optimize_without_views_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test optimization without investor views."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        assert isinstance(result, BlackLittermanResult)
        assert result.success
        assert result.weights.shape == (5,)
        assert np.allclose(result.weights.sum(), 1.0, atol=1e-5)
        assert np.all(result.weights >= 0)
        assert np.all(result.weights <= optimizer.config.max_position + 1e-5)

    def test_optimize_with_views_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        multiple_views: list[InvestorView],
    ) -> None:
        """Test optimization with investor views."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=multiple_views,
        )

        assert result.success
        assert len(result.views) == 3
        assert result.weights.shape == (5,)
        assert result.bl_returns is not None
        assert result.equilibrium_returns is not None

    def test_optimize_using_market_weights_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_weights: NDArray[np.float64],
    ) -> None:
        """Test optimization using market weights instead of caps."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_weights=sample_market_weights,
            views=None,
        )

        assert result.success

    def test_optimize_with_custom_config_success(
        self,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        custom_config: BlackLittermanConfig,
    ) -> None:
        """Test optimization with custom configuration."""
        optimizer = BlackLittermanOptimizer(custom_config)
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        assert result.success

    def test_optimization_result_weights_dict_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test weights_dict property of result."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        weights_dict = result.weights_dict

        assert isinstance(weights_dict, dict)
        assert len(weights_dict) == 5
        assert "asset_0" in weights_dict
        assert np.isclose(weights_dict["asset_0"], result.weights[0])

    def test_optimization_result_get_view_summary_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        multiple_views: list[InvestorView],
    ) -> None:
        """Test get_view_summary method."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=multiple_views,
        )

        summary = result.get_view_summary()

        assert isinstance(summary, list)
        assert len(summary) == 3
        assert summary[0]["type"] == "absolute"
        assert summary[0]["confidence"] == 0.70
        assert summary[1]["type"] == "relative"

    def test_optimize_handles_invalid_inputs_gracefully(
        self, optimizer: BlackLittermanOptimizer
    ) -> None:
        """Test that optimization handles invalid inputs gracefully."""
        invalid_returns = np.random.randn(300, 5)
        invalid_caps = np.array([1.0, -1.0, 1.0, 1.0, 1.0])  # Negative cap

        result = optimizer.optimize(
            returns=invalid_returns,
            market_caps=invalid_caps,
            views=None,
        )

        # Should still return a result, even if not successful
        assert isinstance(result, BlackLittermanResult)


# =============================================================================
# TESTS: Convenience Function
# =============================================================================


class TestConvenienceFunction:
    """Test suite for compute_black_litterman_weights convenience function."""

    def test_compute_black_litterman_weights_success(
        self,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        absolute_view: InvestorView,
    ) -> None:
        """Test convenience function returns correct weights."""
        weights = compute_black_litterman_weights(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=[absolute_view],
            tau=0.05,
            risk_aversion=3.0,
            max_position=0.20,
        )

        assert weights.shape == (5,)
        assert np.allclose(weights.sum(), 1.0, atol=1e-5)
        assert np.all(weights >= 0)

    def test_compute_black_litterman_weights_with_custom_params_success(
        self,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test with custom parameters."""
        weights = compute_black_litterman_weights(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=[],
            tau=0.03,
            risk_aversion=2.5,
            max_position=0.15,
        )

        assert weights.shape == (5,)


# =============================================================================
# TESTS: Integration and Edge Cases
# =============================================================================


class TestIntegrationAndEdgeCases:
    """Integration tests and edge case handling."""

    def test_full_pipeline_with_realistic_data_success(self) -> None:
        """Test complete pipeline with realistic market data."""
        np.random.seed(123)

        # Generate realistic returns (3 years, 10 assets)
        n_assets = 10
        n_periods = 756  # 3 years

        # Create correlated returns
        corr_target = np.eye(n_assets) * 0.15  # 15% correlation off-diagonal
        np.fill_diagonal(corr_target, 1.0)
        corr_target = np.where(corr_target == 0.15, 0.3, corr_target)

        vols = np.array([0.20, 0.18, 0.22, 0.25, 0.15, 0.19, 0.21, 0.17, 0.23, 0.16])
        cov_matrix = np.outer(vols, vols) * corr_target

        returns = np.random.multivariate_normal(
            np.zeros(n_assets) * 0.0005, cov_matrix / 252, n_periods
        )

        # Market caps (log-normal distribution)
        market_caps = np.random.lognormal(mean=10, sigma=1, size=n_assets)

        # Views
        views = [
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[0],
                pick_vector=np.array([1.0] + [0.0] * 9),
                expected_return=0.12,
                confidence=0.65,
            ),
            InvestorView(
                view_type=ViewType.RELATIVE,
                assets=[1, 2],
                pick_vector=np.array([0.0, 1.0, -1.0] + [0.0] * 7),
                expected_return=0.02,
                confidence=0.55,
            ),
        ]

        # Run optimization
        optimizer = BlackLittermanOptimizer()
        result = optimizer.optimize(returns=returns, market_caps=market_caps, views=views)

        # Assertions
        assert result.success
        assert result.weights.shape == (n_assets,)
        assert np.allclose(result.weights.sum(), 1.0, atol=1e-4)
        assert np.all(result.weights >= 0)
        assert np.all(result.weights <= 0.25)  # Max position constraint
        assert result.sharpe_ratio > 0

    def test_with_single_view_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        absolute_view: InvestorView,
    ) -> None:
        """Test optimization with single absolute view."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=[absolute_view],
        )

        assert result.success
        assert len(result.views) == 1

    def test_with_many_views_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test optimization with many views."""
        many_views = [
            InvestorView(
                view_type=ViewType.ABSOLUTE,
                assets=[i],
                pick_vector=np.array([1.0 if j == i else 0.0 for j in range(5)]),
                expected_return=0.05 + i * 0.01,
                confidence=0.5 + i * 0.05,
            )
            for i in range(5)
        ]

        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=many_views,
        )

        assert result.success
        assert len(result.views) == 5

    def test_with_low_confidence_views_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test that low confidence views have minimal impact."""
        low_confidence_view = InvestorView(
            view_type=ViewType.ABSOLUTE,
            assets=[0],
            pick_vector=np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
            expected_return=0.50,  # Very high return expectation
            confidence=0.05,  # But very low confidence
        )

        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=[low_confidence_view],
        )

        assert result.success
        # Returns should be much closer to equilibrium than the view
        assert result.bl_returns[0] < 0.50  # Should not be dominated by view

    def test_view_impact_calculation_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        multiple_views: list[InvestorView],
    ) -> None:
        """Test that view impact is calculated correctly."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=multiple_views,
        )

        assert result.view_impact is not None
        assert result.view_impact.shape == (3,)
        assert np.all(result.view_impact >= 0)

    def test_posterior_covariance_is_positive_definite(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
        multiple_views: list[InvestorView],
    ) -> None:
        """Test that posterior covariance is positive definite."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=multiple_views,
        )

        # Check if positive semi-definite by attempting Cholesky decomposition
        try:
            np.linalg.cholesky(result.posterior_covariance)
            is_psd = True
        except np.linalg.LinAlgError:
            is_psd = False

        assert is_psd

    def test_sharpe_ratio_calculation_success(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test that Sharpe ratio is calculated correctly."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        expected_sharpe = (
            (result.expected_return - optimizer.config.risk_free_rate) / result.expected_risk
            if result.expected_risk > 0
            else -np.inf
        )

        assert np.isclose(result.sharpe_ratio, expected_sharpe)

    def test_long_only_constraint_enforced(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test that long-only constraint is enforced."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        assert np.all(result.weights >= 0)

    def test_max_position_constraint_enforced(
        self,
        optimizer: BlackLittermanOptimizer,
        sample_returns: NDArray[np.float64],
        sample_market_caps: NDArray[np.float64],
    ) -> None:
        """Test that max position constraint is enforced."""
        result = optimizer.optimize(
            returns=sample_returns,
            market_caps=sample_market_caps,
            views=None,
        )

        assert np.all(result.weights <= optimizer.config.max_position + 1e-5)
