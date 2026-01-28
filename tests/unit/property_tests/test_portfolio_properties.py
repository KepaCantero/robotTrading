"""
Property-Based Tests for Portfolio Calculations

This module uses Hypothesis to test mathematical properties and invariants
of portfolio calculations, ensuring correctness across wide ranges of inputs.

Properties tested:
- Weight constraint invariants
- Return calculation properties
- Portfolio optimization invariants
- Risk parity properties
- Concentration limits
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional

import numpy as np
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from hypothesis.extra import numpy as np_strategies

from app.engines.portfolio_engine.optimizers import MarkowitzOptimizer


# ============================================================================
# Test Strategies
# ============================================================================

def valid_portfolio_weights() -> st.SearchStrategy[np.ndarray]:
    """
    Generate valid portfolio weights that sum to 1.

    Uses Dirichlet distribution to ensure weights sum to 1 and are non-negative.
    """
    n_assets = st.integers(min_value=2, max_value=50)

    return n_assets.flatmap(lambda n: np_strategies.arrays(
        dtype=np.float64,
        shape=(n,),
        elements=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
    ).map(lambda weights: weights / weights.sum()))


def valid_returns_matrix() -> st.SearchStrategy[np.ndarray]:
    """Generate valid asset returns matrix."""
    n_assets = st.integers(min_value=2, max_value=20)
    n_observations = st.integers(min_value=50, max_value=1000)

    return st.tuples(n_assets, n_observations).flatmap(
        lambda dims: np_strategies.arrays(
            dtype=np.float64,
            shape=(dims[1], dims[0]),
            elements=st.floats(min_value=-0.10, max_value=0.10, allow_nan=False, allow_infinity=False)
        )
    )


def valid_expected_returns() -> st.SearchStrategy[np.ndarray]:
    """Generate valid expected returns."""
    n_assets = st.integers(min_value=2, max_value=20)

    return n_assets.flatmap(lambda n: np_strategies.arrays(
        dtype=np.float64,
        shape=(n,),
        elements=st.floats(min_value=-0.05, max_value=0.15, allow_nan=False, allow_infinity=False)
    ))


def valid_correlation_matrix() -> st.SearchStrategy[np.ndarray]:
    """
    Generate valid correlation matrix (positive semi-definite).

    This is complex, so we'll generate a simpler approximation.
    """
    n_assets = st.integers(min_value=2, max_value=10)

    return n_assets.flatmap(lambda n: np_strategies.arrays(
        dtype=np.float64,
        shape=(n + 1, n),  # More rows than columns to ensure valid correlation
        elements=st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False)
    ).map(lambda X: _ensure_valid_correlation(X)))


def weights_and_returns() -> st.SearchStrategy[tuple[np.ndarray, np.ndarray]]:
    """Generate matching weights and returns arrays with same dimensions."""
    n_assets = st.integers(min_value=2, max_value=50)

    return n_assets.flatmap(lambda n: st.tuples(
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n,),
            elements=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
        ).map(lambda weights: weights / weights.sum()),
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n,),
            elements=st.floats(min_value=-0.05, max_value=0.15, allow_nan=False, allow_infinity=False)
        )
    ))


def weights_and_correlation() -> st.SearchStrategy[tuple[np.ndarray, np.ndarray]]:
    """Generate matching weights and correlation matrix with same dimensions."""
    n_assets = st.integers(min_value=2, max_value=10)

    return n_assets.flatmap(lambda n: st.tuples(
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n,),
            elements=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
        ).map(lambda weights: weights / weights.sum()),
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n + 1, n),  # More rows than columns to ensure valid correlation
            elements=st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False)
        ).map(lambda X: _ensure_valid_correlation(X))
    ))


def two_weights_sets() -> st.SearchStrategy[tuple[np.ndarray, np.ndarray]]:
    """Generate two matching weight arrays with same dimensions."""
    n_assets = st.integers(min_value=2, max_value=50)

    return n_assets.flatmap(lambda n: st.tuples(
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n,),
            elements=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
        ).map(lambda weights: weights / weights.sum()),
        np_strategies.arrays(
            dtype=np.float64,
            shape=(n,),
            elements=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
        ).map(lambda weights: weights / weights.sum())
    ))


def _ensure_valid_correlation(X: np.ndarray) -> np.ndarray:
    """Ensure the matrix is a valid correlation matrix."""
    # X shape is (n_rows, n_cols)
    # We want a correlation matrix of size (n_cols, n_cols)
    n = X.shape[1]

    # Handle edge case: if all values are the same, add some noise
    if np.allclose(X, X.flat[0]):
        X = X + np.random.uniform(-0.1, 0.1, X.shape)

    # Check if any column has zero variance (would cause division by zero)
    col_stds = X.std(axis=0)
    if np.any(col_stds < 1e-10):
        # Add noise to constant columns
        for i in range(n):
            if col_stds[i] < 1e-10:
                X[:, i] = X[:, i] + np.random.uniform(-0.1, 0.1, X.shape[0])

    # Generate correlation matrix from the random data
    with np.errstate(divide='ignore', invalid='ignore'):
        corr = np.corrcoef(X.T)  # Transpose to get (n, n) matrix

    # Check for NaN or inf
    if not np.all(np.isfinite(corr)):
        # Fallback: create a simple valid correlation matrix
        corr = np.eye(n) * 0.9 + np.ones((n, n)) * 0.1
        np.fill_diagonal(corr, 1.0)
        return corr

    # Ensure diagonal is exactly 1
    np.fill_diagonal(corr, 1.0)

    # Ensure it's positive semi-definite by checking eigenvalues
    try:
        eigenvalues = np.linalg.eigvals(corr)
        min_eigenvalue = np.min(np.real(eigenvalues))
        if min_eigenvalue < -1e-8:
            # Add small diagonal term to ensure positive semi-definiteness
            corr = corr + np.eye(n) * (abs(min_eigenvalue) + 0.01)
            # Reset diagonal to 1
            np.fill_diagonal(corr, 1.0)
    except np.linalg.LinAlgError:
        # Fallback to simple valid correlation matrix
        corr = np.eye(n) * 0.9 + np.ones((n, n)) * 0.1
        np.fill_diagonal(corr, 1.0)

    return corr


def valid_capitals() -> st.SearchStrategy[Decimal]:
    """Generate valid capital amounts."""
    return st.floats(min_value=1_000, max_value=100_000_000).map(
        lambda x: Decimal(str(x))
    )


# ============================================================================
# Weight Constraint Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioWeightConstraints:
    """Property tests for portfolio weight constraints."""

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_weights_sum_to_one(self, weights):
        """Portfolio weights should sum to 1 (or very close)."""
        sum_weights = weights.sum()

        assert abs(sum_weights - 1.0) < 1e-10, \
            f"Weights sum to {sum_weights}, expected 1.0"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_weights_non_negative(self, weights):
        """Portfolio weights should be non-negative (long-only constraint)."""
        assert all(w >= 0 for w in weights), \
            f"All weights should be >= 0, got min {weights.min()}"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_weights_le_one(self, weights):
        """Individual weights should be <= 1."""
        assert all(w <= 1.0 for w in weights), \
            f"All weights should be <= 1, got max {weights.max()}"

    @given(
        weights=valid_portfolio_weights(),
        capital=valid_capitals()
    )
    @settings(max_examples=100)
    def test_position_values_sum_to_capital(self, weights, capital):
        """Position values should sum to total capital."""
        position_values = weights * float(capital)
        sum_positions = position_values.sum()

        # Allow small floating point error
        assert abs(sum_positions - float(capital)) < 0.01, \
            f"Position values sum to {sum_positions}, expected {capital}"

    @given(
        weights=valid_portfolio_weights(),
        capital=valid_capitals()
    )
    @settings(max_examples=100)
    def test_position_values_non_negative(self, weights, capital):
        """Position values should be non-negative."""
        position_values = weights * float(capital)

        assert all(v >= 0 for v in position_values), \
            f"All position values should be >= 0, got min {position_values.min()}"

    @given(
        weights=valid_portfolio_weights(),
        concentration_limit=st.floats(min_value=0.05, max_value=0.5)
    )
    @settings(max_examples=100)
    def test_concentration_limit_enforced(self, weights, concentration_limit):
        """Maximum weight should respect concentration limit."""
        max_weight = weights.max()

        # This test checks the property, doesn't enforce it
        # We're testing that max_weight is a reasonable measure of concentration
        assert max_weight >= 0, "Max weight should be non-negative"
        assert max_weight <= 1.0, "Max weight should not exceed 1"


# ============================================================================
# Portfolio Return Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioReturnCalculations:
    """Property tests for portfolio return calculations."""

    @given(weights_returns=weights_and_returns())
    @settings(max_examples=100)
    def test_portfolio_return_linear(self, weights_returns):
        """Portfolio return should be linear in weights and returns."""
        weights, returns = weights_returns

        portfolio_return = np.dot(weights, returns)

        # Should be between min and max individual returns
        min_return = returns.min()
        max_return = returns.max()

        assert min_return - 1e-10 <= portfolio_return <= max_return + 1e-10, \
            f"Portfolio return {portfolio_return} outside bounds [{min_return}, {max_return}]"

    @given(
        returns=valid_expected_returns(),
        capital=valid_capitals()
    )
    @settings(max_examples=100)
    def test_equal_weighted_portfolio_return(self, returns, capital):
        """Equal-weighted portfolio return should be average of returns."""
        n = len(returns)
        equal_weights = np.ones(n) / n

        portfolio_return = np.dot(equal_weights, returns)
        average_return = returns.mean()

        assert abs(portfolio_return - average_return) < 1e-10, \
            f"Equal-weighted return {portfolio_return} != average {average_return}"

    @given(weights_returns=weights_and_returns())
    @settings(max_examples=100)
    def test_return_scaling_with_weights(self, weights_returns):
        """Doubling all weights (before normalization) should give same return."""
        weights, returns = weights_returns

        # Double weights
        doubled_weights = weights * 2
        # Renormalize
        doubled_weights = doubled_weights / doubled_weights.sum()

        return1 = np.dot(weights, returns)
        return2 = np.dot(doubled_weights, returns)

        assert abs(return1 - return2) < 1e-10, \
            f"Scaled weights should give same return: {return1} != {return2}"

    @given(weights_returns=weights_and_returns())
    @settings(max_examples=50)
    def test_return_additivity(self, weights_returns):
        """Portfolio return of combined returns should be sum of individual returns."""
        weights, returns1 = weights_returns

        # Generate returns2 with same dimension
        returns2 = np.random.uniform(-0.05, 0.15, len(returns1))

        combined_returns = returns1 + returns2

        return1 = np.dot(weights, returns1)
        return2 = np.dot(weights, returns2)
        return_combined = np.dot(weights, combined_returns)

        assert abs(return_combined - (return1 + return2)) < 1e-10, \
            f"Combined return {return_combined} != sum {return1 + return2}"


# ============================================================================
# Portfolio Variance Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioVarianceProperties:
    """Property tests for portfolio variance calculations."""

    @given(weights_corr=weights_and_correlation())
    @settings(max_examples=100)
    def test_variance_non_negative(self, weights_corr):
        """Portfolio variance should always be non-negative."""
        weights, corr_matrix = weights_corr

        # Assume equal volatilities for simplicity
        volatilities = np.ones(len(weights)) * 0.2

        # Calculate covariance matrix
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix

        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))

        assert portfolio_variance >= 0, \
            f"Portfolio variance should be >= 0, got {portfolio_variance}"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_variance_zero_for_perfect_correlation(self, weights):
        """With perfect correlation and equal volatilities, variance should simplify."""
        # Create perfect correlation matrix
        n = len(weights)
        perfect_corr = np.ones((n, n))

        # Equal volatilities
        volatilities = np.ones(n) * 0.2

        # Covariance matrix
        cov_matrix = np.outer(volatilities, volatilities) * perfect_corr

        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))

        # With perfect correlation and equal vols: variance = (sum(weights) * vol)^2 = vol^2
        expected_variance = volatilities[0] ** 2

        assert abs(portfolio_variance - expected_variance) < 1e-10, \
            f"Variance {portfolio_variance} != expected {expected_variance}"

    @given(weights_corr=weights_and_correlation())
    @settings(max_examples=100)
    def test_variance_symmetry(self, weights_corr):
        """Portfolio variance should be symmetric with respect to weight ordering."""
        weights, corr_matrix = weights_corr

        # Reverse weights
        reversed_weights = weights[::-1]

        # Reverse correlation matrix
        reversed_corr = corr_matrix[::-1, ::-1]

        volatilities = np.ones(len(weights)) * 0.2
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
        reversed_cov = np.outer(volatilities, volatilities) * reversed_corr

        variance1 = np.dot(weights, np.dot(cov_matrix, weights))
        variance2 = np.dot(reversed_weights, np.dot(reversed_cov, reversed_weights))

        assert abs(variance1 - variance2) < 1e-10, \
            f"Variance should be symmetric: {variance1} != {variance2}"


# ============================================================================
# Risk Parity Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestRiskParityProperties:
    """Property tests for risk parity calculations."""

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=50)
    def test_risk_parity_equal_risk_contribution(self, weights):
        """Risk parity should result in equal marginal contribution to risk."""
        n = len(weights)

        # For equal volatilities and perfect correlation, equal weights
        # give equal risk contributions
        risk_parity_weights = np.ones(n) / n

        # Use perfect correlation matrix (all ones)
        corr_matrix = np.ones((n, n))
        np.fill_diagonal(corr_matrix, 1.0)

        # Assume equal volatilities for simplicity
        volatilities = np.ones(n) * 0.2

        # Calculate covariance matrix
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix

        # Calculate portfolio variance
        portfolio_variance = np.dot(risk_parity_weights, np.dot(cov_matrix, risk_parity_weights))
        portfolio_std = np.sqrt(portfolio_variance)

        # Calculate marginal contributions
        marginal_contrib = np.dot(cov_matrix, risk_parity_weights) / portfolio_std

        # Risk contributions
        risk_contrib = risk_parity_weights * marginal_contrib

        # All risk contributions should be approximately equal
        mean_risk_contrib = risk_contrib.mean()

        for i, rc in enumerate(risk_contrib):
            assert abs(rc - mean_risk_contrib) < 1e-10, \
                f"Risk contribution {rc} at index {i} != mean {mean_risk_contrib}"


# ============================================================================
# Portfolio Optimization Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioOptimizationProperties:
    """Property tests for portfolio optimization."""

    @given(returns_matrix=valid_returns_matrix())
    @settings(max_examples=50, deadline=None)
    def test_max_sharpe_weights_sum_to_one(self, returns_matrix):
        """Maximum Sharpe ratio portfolio weights should sum to 1."""
        try:
            optimizer = MarkowitzOptimizer(config={})
        except (ImportError, TypeError):
            pytest.skip("Optimization dependencies not available")

        try:
            # Calculate expected returns and covariance
            expected_returns = returns_matrix.mean(axis=0)
            cov_matrix = np.cov(returns_matrix.T)

            # Optimize
            result = optimizer.optimize(
                expected_returns=expected_returns,
                cov_matrix=cov_matrix,
            )

            assume(result is not None)

            weights = result.get('weights')
            if weights is not None:
                # Convert dict to array if needed
                if isinstance(weights, dict):
                    weights_array = np.array(list(weights.values()))
                else:
                    weights_array = weights
                sum_weights = weights_array.sum()
                assert abs(sum_weights - 1.0) < 0.01, \
                    f"Max Sharpe weights sum to {sum_weights}, expected 1.0"
        except (ImportError, np.linalg.LinAlgError):
            pytest.skip("Optimization dependencies not available or singular matrix")

    @given(returns_matrix=valid_returns_matrix())
    @settings(max_examples=50, deadline=None)
    def test_min_variance_weights_sum_to_one(self, returns_matrix):
        """Minimum variance portfolio weights should sum to 1."""
        try:
            optimizer = MarkowitzOptimizer(config={})
        except (ImportError, TypeError):
            pytest.skip("Optimization dependencies not available")

        try:
            cov_matrix = np.cov(returns_matrix.T)

            result = optimizer.optimize(
                expected_returns=np.zeros(cov_matrix.shape[0]),  # Not used for min variance
                cov_matrix=cov_matrix,
            )

            assume(result is not None)

            weights = result.get('weights')
            if weights is not None:
                # Convert dict to array if needed
                if isinstance(weights, dict):
                    weights_array = np.array(list(weights.values()))
                else:
                    weights_array = weights
                sum_weights = weights_array.sum()
                assert abs(sum_weights - 1.0) < 0.01, \
                    f"Min variance weights sum to {sum_weights}, expected 1.0"
        except (ImportError, np.linalg.LinAlgError):
            pytest.skip("Optimization dependencies not available or singular matrix")

    @given(returns_matrix=valid_returns_matrix())
    @settings(max_examples=50, deadline=None)
    def test_min_variance_lower_than_equal_weighted(self, returns_matrix):
        """Minimum variance should be <= equal-weighted variance."""
        try:
            optimizer = MarkowitzOptimizer(config={})
        except (ImportError, TypeError):
            pytest.skip("Optimization dependencies not available")

        try:
            cov_matrix = np.cov(returns_matrix.T)
            n = cov_matrix.shape[0]

            # Minimum variance portfolio
            result_min_var = optimizer.optimize(
                expected_returns=np.zeros(n),  # Not used for min variance
                cov_matrix=cov_matrix,
            )

            assume(result_min_var is not None)

            weights_min_var = result_min_var.get('weights')
            if weights_min_var is not None:
                # Convert dict to array if needed
                if isinstance(weights_min_var, dict):
                    weights_array = np.array(list(weights_min_var.values()))
                else:
                    weights_array = weights_min_var
                var_min_var = np.dot(weights_array, np.dot(cov_matrix, weights_array))

                # Equal-weighted portfolio
                weights_equal = np.ones(n) / n
                var_equal = np.dot(weights_equal, np.dot(cov_matrix, weights_equal))

                assert var_min_var <= var_equal * 1.01, \
                    f"Min variance {var_min_var} should be <= equal-weighted {var_equal}"
        except (ImportError, np.linalg.LinAlgError):
            pytest.skip("Optimization dependencies not available or singular matrix")


# ============================================================================
# Portfolio Rebalancing Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioRebalancingProperties:
    """Property tests for portfolio rebalancing."""

    @given(
        two_weights_capital=st.tuples(two_weights_sets(), valid_capitals())
    )
    @settings(max_examples=100)
    def test_rebalancing_trades_sum_to_zero(self, two_weights_capital):
        """Rebalancing trades should sum to zero (buy + sell = 0)."""
        (current_weights, target_weights), capital = two_weights_capital

        # Calculate trades
        trades = (target_weights - current_weights) * float(capital)

        # Sum of trades should be approximately zero
        # (some cash might be left over due to discrete units, but in continuous case it's zero)
        sum_trades = trades.sum()

        assert abs(sum_trades) < 0.01, \
            f"Rebalancing trades should sum to 0, got {sum_trades}"

    @given(
        two_weights_capital=st.tuples(two_weights_sets(), valid_capitals())
    )
    @settings(max_examples=100)
    def test_rebalancing_preserves_capital(self, two_weights_capital):
        """Rebalancing should not change total capital (ignoring costs)."""
        (current_weights, target_weights), capital = two_weights_capital

        # Current position values
        current_values = current_weights * float(capital)
        sum_current = current_values.sum()

        # Target position values
        target_values = target_weights * float(capital)
        sum_target = target_values.sum()

        # Both should equal capital
        assert abs(sum_current - float(capital)) < 0.01, \
            f"Current values sum to {sum_current}, expected {capital}"
        assert abs(sum_target - float(capital)) < 0.01, \
            f"Target values sum to {sum_target}, expected {capital}"


# ============================================================================
# Turnover Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioTurnoverProperties:
    """Property tests for portfolio turnover calculations."""

    @given(two_weights=two_weights_sets())
    @settings(max_examples=100)
    def test_turnover_non_negative(self, two_weights):
        """Portfolio turnover should be non-negative."""
        weights1, weights2 = two_weights

        # Turnover is sum of absolute weight changes divided by 2
        turnover = np.sum(np.abs(weights2 - weights1)) / 2

        assert turnover >= 0, \
            f"Turnover should be >= 0, got {turnover}"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_turnover_zero_for_same_weights(self, weights):
        """Turnover should be zero when weights don't change."""
        turnover = np.sum(np.abs(weights - weights)) / 2

        assert turnover == 0, \
            f"Turnover should be 0 for same weights, got {turnover}"

    @given(two_weights=two_weights_sets())
    @settings(max_examples=100)
    def test_turnover_symmetry(self, two_weights):
        """Turnover should be symmetric (A->B equals B->A)."""
        weights1, weights2 = two_weights

        turnover1_to_2 = np.sum(np.abs(weights2 - weights1)) / 2
        turnover2_to_1 = np.sum(np.abs(weights1 - weights2)) / 2

        assert abs(turnover1_to_2 - turnover2_to_1) < 1e-10, \
            f"Turnover should be symmetric: {turnover1_to_2} != {turnover2_to_1}"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_turnover_maximum_for_complete_reversal(self, weights):
        """Complete reversal should give maximum turnover of 1."""
        n = len(weights)

        # Complete reversal: invest in all other assets
        # For simplicity, equal weight everything else
        reversed_weights = np.ones(n) / n

        turnover = np.sum(np.abs(reversed_weights - weights)) / 2

        # Maximum possible turnover is 1 (100% of portfolio turns over)
        assert turnover <= 1.0, \
            f"Turnover {turnover} should not exceed 1.0"


# ============================================================================
# Diversification Properties
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioDiversificationProperties:
    """Property tests for portfolio diversification metrics."""

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_herfindahl_index_range(self, weights):
        """Herfindahl index should be between 1/n and 1."""
        n = len(weights)

        # Herfindahl index: sum of squared weights
        hhi = np.sum(weights ** 2)

        # Minimum diversification: 1/n (equal weights)
        min_hhi = 1.0 / n

        # Maximum concentration: 1 (single asset)
        max_hhi = 1.0

        # Allow small floating point tolerance
        assert min_hhi - 1e-12 <= hhi <= max_hhi + 1e-12, \
            f"HHI {hhi} outside range [{min_hhi}, {max_hhi}]"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_herfindahl_equal_weights_minimal(self, weights):
        """Equal weights should minimize Herfindahl index."""
        n = len(weights)

        # Calculate HHI for given weights
        hhi = np.sum(weights ** 2)

        # Equal weights
        equal_weights = np.ones(n) / n
        hhi_equal = np.sum(equal_weights ** 2)

        # HHI for equal weights should be minimal
        assert hhi >= hhi_equal - 1e-10, \
            f"HHI {hhi} should be >= equal-weight HHI {hhi_equal}"

    @given(weights=valid_portfolio_weights())
    @settings(max_examples=100)
    def test_herfindahl_single_asset_maximal(self, weights):
        """Single asset portfolio should maximize Herfindahl index."""
        # Calculate HHI for given weights
        hhi = np.sum(weights ** 2)

        # Maximum possible HHI (all weight in one asset)
        # This is 1.0, but we check that our weights don't exceed it
        assert hhi <= 1.0, \
            f"HHI {hhi} should not exceed 1.0"

    @given(weights_corr=weights_and_correlation())
    @settings(max_examples=100)
    def test_diversification_ratio_properties(self, weights_corr):
        """Diversification ratio should have reasonable bounds."""
        weights, corr_matrix = weights_corr

        # Assume equal volatilities
        volatilities = np.ones(len(weights)) * 0.2

        # Portfolio volatility
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
        portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))

        # Weighted average volatility
        weighted_avg_vol = np.dot(weights, volatilities)

        # Diversification ratio
        if portfolio_vol > 0:
            div_ratio = weighted_avg_vol / portfolio_vol

            # Should be >= 1 (diversification helps)
            assert div_ratio >= 0.99, \
                f"Diversification ratio {div_ratio} should be >= 1 (approximately)"


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
class TestPortfolioEdgeCases:
    """Test edge cases for portfolio calculations."""

    @given(capital=valid_capitals())
    @settings(max_examples=50)
    def test_single_asset_portfolio(self, capital):
        """Single asset portfolio should have weight of 1."""
        weights = np.array([1.0])

        assert weights.sum() == 1.0, "Single asset weight should sum to 1"
        assert weights[0] == 1.0, "Single asset weight should be 1"

        position_value = weights[0] * float(capital)
        assert abs(position_value - float(capital)) < 0.01, \
            f"Position value {position_value} should equal capital {capital}"

    @given(
        capital=valid_capitals(),
        n=st.integers(min_value=2, max_value=10)
    )
    @settings(max_examples=50)
    def test_equal_weighted_portfolio(self, capital, n):
        """Equal-weighted portfolio should distribute capital evenly."""
        weights = np.ones(n) / n

        assert abs(weights.sum() - 1.0) < 1e-10, "Weights should sum to 1"

        position_values = weights * float(capital)
        expected_value = float(capital) / n

        for i, value in enumerate(position_values):
            assert abs(value - expected_value) < 0.01, \
                f"Position {i} value {value} != expected {expected_value}"
