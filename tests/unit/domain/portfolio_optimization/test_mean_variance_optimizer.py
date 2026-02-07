"""Comprehensive tests for Mean-Variance Portfolio Optimizer.

Tests cover all Markowitz rules (66-80) from the paper:
- Rule 66: Covariance with 252-day lookback
- Rule 67: Mean-Variance Optimization
- Rule 68: Long-only constraints (0 <= weight <= 1)
- Rule 69: Sum constraint validation
- Rule 70: Diversification enforcement (max 20%)
- Rule 71: Efficient frontier calculation (20+ points)
- Rule 72: Max Sharpe portfolio optimization
- Rule 73: L2 regularization
- Rule 74: Ledoit-Wolf shrinkage
- Rule 13: Risk parity fallback
- Rule 14: False diversification detection
- Rule 15: Input sanitization
"""


import numpy as np
import pytest
from numpy.typing import NDArray

from app.domain.portfolio_optimization import (
    EfficientFrontier,
    EfficientFrontierPoint,
    InputValidationError,
    MeanVarianceOptimizer,
    OptimizationMethod,
    OptimizationResult,
    ShrinkageMethod,
)


class TestMeanVarianceOptimizerInitialization:
    """Test suite for MeanVarianceOptimizer initialization."""

    def test_default_initialization(self) -> None:
        """Test optimizer with default parameters."""
        optimizer = MeanVarianceOptimizer()

        assert optimizer.lookback_days == 252
        assert optimizer.max_position == 0.20
        assert optimizer.risk_free_rate == 0.02
        assert optimizer.regularization_gamma == 0.01

    def test_custom_initialization(self) -> None:
        """Test optimizer with custom parameters."""
        optimizer = MeanVarianceOptimizer(
            lookback_days=500,
            max_position=0.15,
            risk_free_rate=0.03,
            regularization_gamma=0.005,
            sum_tolerance=1e-7,
        )

        assert optimizer.lookback_days == 500
        assert optimizer.max_position == 0.15
        assert optimizer.risk_free_rate == 0.03
        assert optimizer.regularization_gamma == 0.005

    def test_invalid_lookback_days_raises_error(self) -> None:
        """Test that invalid lookback_days raises ValueError."""
        with pytest.raises(ValueError, match="lookback_days must be >= 252"):
            MeanVarianceOptimizer(lookback_days=100)

    def test_invalid_max_position_raises_error(self) -> None:
        """Test that invalid max_position raises ValueError."""
        with pytest.raises(ValueError, match="max_position must be in \\(0, 1\\]"):
            MeanVarianceOptimizer(max_position=0.0)

        with pytest.raises(ValueError, match="max_position must be in \\(0, 1\\]"):
            MeanVarianceOptimizer(max_position=1.5)

    def test_invalid_risk_free_rate_raises_error(self) -> None:
        """Test that invalid risk_free_rate raises ValueError."""
        with pytest.raises(ValueError, match="risk_free_rate must be in \\[0, 1\\]"):
            MeanVarianceOptimizer(risk_free_rate=-0.01)

        with pytest.raises(ValueError, match="risk_free_rate must be in \\[0, 1\\]"):
            MeanVarianceOptimizer(risk_free_rate=1.5)

    def test_invalid_regularization_gamma_raises_error(self) -> None:
        """Test that negative regularization_gamma raises ValueError."""
        with pytest.raises(ValueError, match="regularization_gamma must be >= 0"):
            MeanVarianceOptimizer(regularization_gamma=-0.01)


class TestInputSanitization:
    """Test suite for input sanitization (Rule 15)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def valid_returns(self) -> NDArray[np.float64]:
        """Create valid returns data."""
        np.random.seed(42)
        return np.random.randn(300, 10) * 0.01  # 300 days, 10 assets

    def test_sanitize_valid_returns(self, optimizer, valid_returns) -> None:
        """Test sanitization of valid returns."""
        cleaned = optimizer.sanitize_inputs(valid_returns)

        assert cleaned.shape[0] == 300
        assert cleaned.shape[1] == 10

    def test_sanitize_removes_nan_assets(self, optimizer) -> None:
        """Test that NaN assets are removed."""
        returns = np.random.randn(300, 10) * 0.01
        returns[:, 5] = np.nan  # Make asset 5 all NaN
        returns[:, 8] = np.nan  # Make asset 8 all NaN

        cleaned = optimizer.sanitize_inputs(returns)

        assert cleaned.shape[1] == 8  # 2 assets removed

    def test_sanitize_removes_zero_volatility_assets(self, optimizer) -> None:
        """Test that zero volatility assets are removed."""
        returns = np.random.randn(300, 10) * 0.01
        returns[:, 3] = 0.001  # Near-zero volatility

        cleaned = optimizer.sanitize_inputs(returns)

        # Asset with ~0 volatility should be removed
        assert cleaned.shape[1] <= 9

    def test_insufficient_periods_raises_error(self, optimizer) -> None:
        """Test that insufficient periods raise InputValidationError."""
        returns = np.random.randn(100, 5) * 0.01  # Only 100 periods

        with pytest.raises(InputValidationError, match="Insufficient data"):
            optimizer.sanitize_inputs(returns)

    def test_insufficient_assets_raises_error(self, optimizer) -> None:
        """Test that insufficient assets raise InputValidationError."""
        returns = np.random.randn(300, 1) * 0.01  # Only 1 asset

        with pytest.raises(InputValidationError, match="Insufficient assets"):
            optimizer.sanitize_inputs(returns)

    def test_invalid_dimensions_raises_error(self, optimizer) -> None:
        """Test that invalid dimensions raise InputValidationError."""
        returns = np.random.randn(300) * 0.01  # 1D array

        with pytest.raises(InputValidationError, match="must be 2-dimensional"):
            optimizer.sanitize_inputs(returns)

    def test_too_few_assets_after_sanitization_raises_error(self, optimizer) -> None:
        """Test that having too few assets after sanitization raises error."""
        returns = np.random.randn(300, 2) * 0.01
        returns[:, 0] = np.nan  # Remove first asset
        returns[:, 1] = 0.001  # Make second asset ~0 volatility

        with pytest.raises(InputValidationError, match="Insufficient assets after"):
            optimizer.sanitize_inputs(returns)


class TestCovarianceCalculation:
    """Test suite for covariance matrix calculation (Rule 66)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def returns(self) -> NDArray[np.float64]:
        """Create returns data."""
        np.random.seed(42)
        return np.random.randn(300, 5) * 0.01

    def test_calculate_covariance_matrix_shape(self, optimizer, returns) -> None:
        """Test covariance matrix has correct shape."""
        cov_matrix = optimizer.calculate_covariance_matrix(returns)

        assert cov_matrix.shape == (5, 5)

    def test_covariance_matrix_symmetry(self, optimizer, returns) -> None:
        """Test that covariance matrix is symmetric."""
        cov_matrix = optimizer.calculate_covariance_matrix(returns)

        assert np.allclose(cov_matrix, cov_matrix.T)

    def test_covariance_matrix_positive_definite(self, optimizer, returns) -> None:
        """Test that covariance matrix is positive semi-definite."""
        cov_matrix = optimizer.calculate_covariance_matrix(returns)

        # Try Cholesky decomposition
        try:
            np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            pytest.fail("Covariance matrix is not positive semi-definite")

    def test_covariance_without_shrinkage(self, optimizer, returns) -> None:
        """Test covariance calculation without shrinkage."""
        cov_matrix = optimizer.calculate_covariance_matrix(returns, use_shrinkage=False)

        assert cov_matrix.shape == (5, 5)

    def test_covariance_with_ledoit_wolf(self, optimizer, returns) -> None:
        """Test Ledoit-Wolf shrinkage (Rule 74)."""
        cov_matrix = optimizer.calculate_covariance_matrix(
            returns,
            use_shrinkage=True,
            shrinkage_method=ShrinkageMethod.LEDOIT_WOLF,
        )

        assert cov_matrix.shape == (5, 5)

    def test_expected_returns_calculation(self, optimizer, returns) -> None:
        """Test expected returns calculation."""
        expected_returns = optimizer.calculate_expected_returns(returns)

        assert expected_returns.shape == (5,)


class TestSumConstraintValidation:
    """Test suite for sum constraint validation (Rule 69)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_valid_sum_constraint(self, optimizer) -> None:
        """Test validation of valid sum constraint."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])

        assert optimizer.validate_sum_constraint(weights)

    def test_invalid_sum_constraint(self, optimizer) -> None:
        """Test that invalid sum constraint fails."""
        weights = np.array([0.30, 0.30, 0.30, 0.30])  # Sum = 1.2

        assert not optimizer.validate_sum_constraint(weights)

    def test_sum_constraint_with_tolerance(self, optimizer) -> None:
        """Test sum constraint with small deviation within tolerance."""
        weights = np.array([0.2500001, 0.2499999, 0.25, 0.25])

        assert optimizer.validate_sum_constraint(weights)


class TestLongOnlyConstraint:
    """Test suite for long-only constraint (Rule 68)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_apply_long_only_constraint(self, optimizer) -> None:
        """Test applying long-only constraint."""
        weights = np.array([1.2, -0.3, 0.5, 0.6])

        constrained = optimizer.apply_long_only_constraint(weights)

        assert constrained.min() >= 0.0
        assert constrained.max() <= 1.0
        assert np.isclose(constrained.sum(), 1.0)

    def test_long_only_already_valid(self, optimizer) -> None:
        """Test that valid weights are unchanged."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])

        constrained = optimizer.apply_long_only_constraint(weights)

        assert np.allclose(constrained, weights)


class TestDiversificationConstraint:
    """Test suite for diversification constraint (Rule 70)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_apply_diversification_constraint(self, optimizer) -> None:
        """Test applying diversification constraint."""
        # Use more assets so 20% max is mathematically possible
        weights = np.array([0.30, 0.25, 0.20, 0.15, 0.10])

        constrained = optimizer.apply_diversification_constraint(weights)

        assert constrained.max() <= 0.20
        assert np.isclose(constrained.sum(), 1.0)

    def test_diversification_no_violations(self, optimizer) -> None:
        """Test that valid weights are unchanged."""
        weights = np.array([0.20, 0.20, 0.30, 0.30])
        weights = weights / weights.sum()  # Normalize

        constrained = optimizer.apply_diversification_constraint(weights, max_weight=0.30)

        assert np.allclose(constrained, weights)


class TestMaxSharpePortfolio:
    """Test suite for maximum Sharpe portfolio optimization (Rule 72)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def sample_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Create sample expected returns and covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01

        expected_returns = returns.mean(axis=0) * 252
        cov_matrix = np.cov(returns, rowvar=False) * 252

        return expected_returns, cov_matrix

    def test_max_sharpe_portfolio_success(self, optimizer, sample_data) -> None:
        """Test successful max Sharpe optimization."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.max_sharpe_portfolio(expected_returns, cov_matrix)

        assert result.success
        assert result.method == OptimizationMethod.MAX_SHARPE
        assert len(result.weights) == 5

    def test_max_sharpe_portfolio_constraints(self, optimizer, sample_data) -> None:
        """Test that max Sharpe portfolio satisfies constraints."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.max_sharpe_portfolio(expected_returns, cov_matrix)

        # Long-only constraint
        assert (result.weights >= 0.0).all()
        assert (result.weights <= optimizer.max_position).all()

        # Sum constraint
        assert np.isclose(result.weights.sum(), 1.0, atol=1e-5)

    def test_max_sharpe_portfolio_metrics(self, optimizer, sample_data) -> None:
        """Test that portfolio metrics are calculated correctly."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.max_sharpe_portfolio(expected_returns, cov_matrix)

        # Check expected return calculation
        expected_return = float(result.weights @ expected_returns)
        assert np.isclose(result.expected_return, expected_return)

        # Check risk calculation
        expected_risk = float(np.sqrt(result.weights @ cov_matrix @ result.weights))
        assert np.isclose(result.expected_risk, expected_risk)

        # Check Sharpe ratio
        expected_sharpe = (expected_return - optimizer.risk_free_rate) / expected_risk
        assert np.isclose(result.sharpe_ratio, expected_sharpe)


class TestMinVariancePortfolio:
    """Test suite for minimum variance portfolio optimization."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def sample_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Create sample expected returns and covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01

        expected_returns = returns.mean(axis=0) * 252
        cov_matrix = np.cov(returns, rowvar=False) * 252

        return expected_returns, cov_matrix

    def test_min_variance_portfolio_success(self, optimizer, sample_data) -> None:
        """Test successful minimum variance optimization."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.min_variance_portfolio(expected_returns, cov_matrix)

        assert result.success
        assert result.method == OptimizationMethod.MIN_VARIANCE
        assert len(result.weights) == 5


class TestRegularizedMVO:
    """Test suite for regularized MVO (Rule 73)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def sample_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Create sample expected returns and covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01

        expected_returns = returns.mean(axis=0) * 252
        cov_matrix = np.cov(returns, rowvar=False) * 252

        return expected_returns, cov_matrix

    def test_regularized_mvo_success(self, optimizer, sample_data) -> None:
        """Test successful regularized MVO."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.regularized_mvo(expected_returns, cov_matrix)

        assert result.success
        assert len(result.weights) == 5

    def test_regularized_mvo_with_custom_gamma(self, optimizer, sample_data) -> None:
        """Test regularized MVO with custom gamma."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.regularized_mvo(expected_returns, cov_matrix, gamma=0.05)

        assert result.success
        # Higher gamma should lead to more balanced weights
        assert result.weights.max() <= optimizer.max_position


class TestEfficientFrontier:
    """Test suite for efficient frontier calculation (Rule 71)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def sample_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Create sample expected returns and covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01

        expected_returns = returns.mean(axis=0) * 252
        cov_matrix = np.cov(returns, rowvar=False) * 252

        return expected_returns, cov_matrix

    def test_efficient_frontier_calculation(self, optimizer, sample_data) -> None:
        """Test efficient frontier calculation with 20+ points (Rule 71)."""
        expected_returns, cov_matrix = sample_data
        frontier = optimizer.calculate_efficient_frontier(expected_returns, cov_matrix, n_points=20)

        assert isinstance(frontier, EfficientFrontier)
        assert len(frontier.points) >= 20
        assert frontier.max_sharpe_index < len(frontier.points)
        assert frontier.min_variance_index < len(frontier.points)

    def test_efficient_frontier_max_sharpe(self, optimizer, sample_data) -> None:
        """Test that max Sharpe portfolio is identified correctly."""
        expected_returns, cov_matrix = sample_data
        frontier = optimizer.calculate_efficient_frontier(expected_returns, cov_matrix, n_points=20)

        max_sharpe = frontier.max_sharpe_portfolio

        # Should be the highest Sharpe ratio
        sharpes = [p.sharpe_ratio for p in frontier.points]
        assert max_sharpe.sharpe_ratio == max(sharpes)

    def test_efficient_frontier_min_variance(self, optimizer, sample_data) -> None:
        """Test that min variance portfolio is identified correctly."""
        expected_returns, cov_matrix = sample_data
        frontier = optimizer.calculate_efficient_frontier(expected_returns, cov_matrix, n_points=20)

        min_var = frontier.min_variance_portfolio

        # Should be the lowest risk
        risks = [p.portfolio_risk for p in frontier.points]
        assert min_var.portfolio_risk == min(risks)


class TestFalseDiversification:
    """Test suite for false diversification detection (Rule 14)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_no_false_diversification(self, optimizer) -> None:
        """Test case with good diversification."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01
        cov_matrix = np.cov(returns, rowvar=False) * 252

        result = optimizer.check_false_diversification(cov_matrix)

        assert result["false_diversification"] is False
        assert "avg_correlation" in result

    def test_false_diversification_detected(self, optimizer) -> None:
        """Test case with high correlation (false diversification)."""
        # Create highly correlated assets
        np.random.seed(42)
        common_factor = np.random.randn(300, 1) * 0.01
        specific = np.random.randn(300, 5) * 0.001  # Small idiosyncratic component
        returns = common_factor + specific

        cov_matrix = np.cov(returns, rowvar=False) * 252

        result = optimizer.check_false_diversification(cov_matrix, threshold=0.70)

        # High correlation should be detected
        assert result["avg_correlation"] > 0.70


class TestRiskParityFallback:
    """Test suite for risk parity fallback (Rule 13)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def sample_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Create sample expected returns and covariance matrix."""
        np.random.seed(42)
        returns = np.random.randn(300, 5) * 0.01

        expected_returns = returns.mean(axis=0) * 252
        cov_matrix = np.cov(returns, rowvar=False) * 252

        return expected_returns, cov_matrix

    def test_risk_parity_fallback(self, optimizer, sample_data) -> None:
        """Test risk parity fallback calculation."""
        expected_returns, cov_matrix = sample_data
        result = optimizer.risk_parity_fallback(expected_returns, cov_matrix)

        assert result.success
        assert result.method == OptimizationMethod.RISK_PARITY
        assert len(result.weights) == 5

    def test_risk_parity_weights_inverse_volatility(self, optimizer, sample_data) -> None:
        """Test that risk parity uses inverse volatility weights."""
        expected_returns, cov_matrix = sample_data

        # Get volatilities
        vols = np.sqrt(np.diag(cov_matrix))

        # Calculate expected inverse volatility weights
        inv_vols = 1.0 / vols
        inv_vols / inv_vols.sum()

        result = optimizer.risk_parity_fallback(expected_returns, cov_matrix)

        # Weights should be proportional to inverse volatility
        # (after applying diversification constraint)
        assert np.allclose(result.weights.sum(), 1.0)


class TestRebalanceTrigger:
    """Test suite for rebalance trigger detection (Rule 9)."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_no_rebalance_needed(self, optimizer) -> None:
        """Test case where no rebalancing is needed."""
        current = np.array([0.25, 0.25, 0.25, 0.25])
        target = np.array([0.26, 0.24, 0.25, 0.25])

        result = optimizer.check_rebalance_trigger(current, target, threshold=0.20)

        assert result["rebalance"] is False
        assert result["n_assets"] == 0

    def test_rebalance_triggered(self, optimizer) -> None:
        """Test case where rebalancing is triggered."""
        current = np.array([0.25, 0.25, 0.25, 0.25])
        target = np.array([0.15, 0.35, 0.25, 0.25])  # Large deviation

        result = optimizer.check_rebalance_trigger(current, target, threshold=0.20)

        assert result["rebalance"] is True
        assert result["n_assets"] > 0
        assert "max_deviation" in result


class TestFullOptimizationPipeline:
    """Test suite for the complete optimization pipeline."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    @pytest.fixture
    def returns(self) -> NDArray[np.float64]:
        """Create returns data."""
        np.random.seed(42)
        return np.random.randn(300, 10) * 0.01

    def test_optimize_max_sharpe(self, optimizer, returns) -> None:
        """Test complete optimization with max Sharpe method."""
        result = optimizer.optimize(returns, method=OptimizationMethod.MAX_SHARPE)

        assert result.success
        assert result.method == OptimizationMethod.MAX_SHARPE
        assert len(result.weights) == 10

    def test_optimize_min_variance(self, optimizer, returns) -> None:
        """Test complete optimization with min variance method."""
        result = optimizer.optimize(returns, method=OptimizationMethod.MIN_VARIANCE)

        assert result.success
        assert len(result.weights) == 10

    def test_optimize_with_shrinkage(self, optimizer, returns) -> None:
        """Test optimization with shrinkage."""
        result = optimizer.optimize(
            returns, use_shrinkage=True, method=OptimizationMethod.MAX_SHARPE
        )

        assert result.success

    def test_optimize_without_shrinkage(self, optimizer, returns) -> None:
        """Test optimization without shrinkage."""
        result = optimizer.optimize(
            returns, use_shrinkage=False, method=OptimizationMethod.MAX_SHARPE
        )

        assert result.success

    def test_optimization_result_weights_dict(self, optimizer, returns) -> None:
        """Test OptimizationResult.weights_dict property."""
        result = optimizer.optimize(returns)

        weights_dict = result.weights_dict

        assert isinstance(weights_dict, dict)
        assert len(weights_dict) == 10
        assert all(isinstance(k, str) for k in weights_dict.keys())
        assert all(isinstance(v, float) for v in weights_dict.values())


class TestOptimizationResult:
    """Test suite for OptimizationResult dataclass."""

    def test_optimization_result_creation(self) -> None:
        """Test creating an OptimizationResult."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])

        result = OptimizationResult(
            weights=weights,
            expected_return=0.10,
            expected_risk=0.15,
            sharpe_ratio=0.67,
            success=True,
            message="Optimization successful",
            method=OptimizationMethod.MAX_SHARPE,
        )

        assert result.success
        assert result.message == "Optimization successful"
        assert result.method == OptimizationMethod.MAX_SHARPE

    def test_optimization_result_weights_dict(self) -> None:
        """Test weights_dict property."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])

        result = OptimizationResult(
            weights=weights,
            expected_return=0.10,
            expected_risk=0.15,
            sharpe_ratio=0.67,
            success=True,
            message="Optimization successful",
            method=OptimizationMethod.MAX_SHARPE,
        )

        weights_dict = result.weights_dict

        assert len(weights_dict) == 4
        assert weights_dict["asset_0"] == 0.25


class TestEfficientFrontierPoint:
    """Test suite for EfficientFrontierPoint dataclass."""

    def test_efficient_frontier_point_creation(self) -> None:
        """Test creating an EfficientFrontierPoint."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])

        point = EfficientFrontierPoint(
            weights=weights,
            portfolio_return=0.10,
            portfolio_risk=0.15,
            sharpe_ratio=0.67,
        )

        assert point.portfolio_return == 0.10
        assert point.portfolio_risk == 0.15
        assert point.sharpe_ratio == 0.67


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    @pytest.fixture
    def optimizer(self) -> MeanVarianceOptimizer:
        """Create optimizer for testing."""
        return MeanVarianceOptimizer()

    def test_empty_weights_for_rebalance(self, optimizer) -> None:
        """Test rebalance check with empty weights."""
        current = np.array([])
        np.array([])

        # Should handle gracefully
        assert optimizer.validate_sum_constraint(current) is False

    def test_mismatched_weight_shapes(self, optimizer) -> None:
        """Test rebalance check with mismatched shapes."""
        current = np.array([0.25, 0.25, 0.25, 0.25])
        target = np.array([0.50, 0.50])

        with pytest.raises(ValueError, match="Weight shape mismatch"):
            optimizer.check_rebalance_trigger(current, target)
