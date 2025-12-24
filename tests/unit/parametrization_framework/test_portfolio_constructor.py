"""
T7.1: Unit Tests for PortfolioConstructor

Tests cover:
- Equal-weight allocation
- Mean-variance optimization
- Risk parity allocation
- Maximum Sharpe ratio optimization
- Covariance matrix building
- Portfolio volatility calculations
"""

import pytest
from app.services.portfolio_construction import (
    PortfolioConstructor,
    OptimizationMethod,
)


@pytest.fixture
def constructor():
    """Create PortfolioConstructor instance."""
    return PortfolioConstructor()


@pytest.fixture
def sample_assets():
    """Sample asset list."""
    return ["AAPL", "MSFT", "GOOGL", "AMZN"]


@pytest.fixture
def sample_returns():
    """Sample expected returns."""
    return {
        "AAPL": 0.12,
        "MSFT": 0.14,
        "GOOGL": 0.16,
        "AMZN": 0.18,
    }


@pytest.fixture
def sample_volatilities():
    """Sample volatilities."""
    return {
        "AAPL": 0.20,
        "MSFT": 0.18,
        "GOOGL": 0.22,
        "AMZN": 0.25,
    }


@pytest.fixture
def sample_correlation_matrix():
    """Sample correlation matrix."""
    return {
        "AAPL": {"AAPL": 1.0, "MSFT": 0.65, "GOOGL": 0.60, "AMZN": 0.55},
        "MSFT": {"AAPL": 0.65, "MSFT": 1.0, "GOOGL": 0.70, "AMZN": 0.60},
        "GOOGL": {"AAPL": 0.60, "MSFT": 0.70, "GOOGL": 1.0, "AMZN": 0.65},
        "AMZN": {"AAPL": 0.55, "MSFT": 0.60, "GOOGL": 0.65, "AMZN": 1.0},
    }


# =============================================================================
# Test Equal-Weight Allocation
# =============================================================================

class TestEqualWeightAllocation:
    """Test equal-weight portfolio allocation."""

    @pytest.mark.asyncio
    async def test_equal_weight_four_assets(self, constructor, sample_assets):
        """Test equal-weight allocation for four assets."""
        allocation = await constructor._equal_weight_allocation(sample_assets)

        assert allocation.allocation["AAPL"] == 0.25
        assert allocation.allocation["MSFT"] == 0.25
        assert allocation.allocation["GOOGL"] == 0.25
        assert allocation.allocation["AMZN"] == 0.25
        assert allocation.method == OptimizationMethod.EQUAL_WEIGHT.value
        assert allocation.num_assets == 4

    @pytest.mark.asyncio
    async def test_equal_weight_allocation_sums_to_one(self, constructor, sample_assets):
        """Test that allocation weights sum to 1.0."""
        allocation = await constructor._equal_weight_allocation(sample_assets)
        total_weight = sum(allocation.allocation.values())
        assert abs(total_weight - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_equal_weight_single_asset(self, constructor):
        """Test equal-weight with single asset."""
        allocation = await constructor._equal_weight_allocation(["SPY"])
        assert allocation.allocation["SPY"] == 1.0
        assert allocation.num_assets == 1

    @pytest.mark.asyncio
    async def test_equal_weight_not_optimized_flag(self, constructor, sample_assets):
        """Test that equal-weight allocation is marked as not optimized."""
        allocation = await constructor._equal_weight_allocation(sample_assets)
        assert allocation.is_optimized is False


# =============================================================================
# Test Mean-Variance Optimization
# =============================================================================

class TestMeanVarianceOptimization:
    """Test mean-variance optimization."""

    @pytest.mark.asyncio
    async def test_mean_variance_basic(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test basic mean-variance optimization."""
        allocation = await constructor._mean_variance_optimization(
            sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
        )

        assert allocation.method == OptimizationMethod.MEAN_VARIANCE.value
        assert allocation.is_optimized is True
        assert allocation.expected_return > 0
        assert allocation.expected_volatility > 0
        assert allocation.sharpe_ratio > 0

    @pytest.mark.asyncio
    async def test_mean_variance_allocation_valid(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test that mean-variance allocation is valid (sums to 1)."""
        allocation = await constructor._mean_variance_optimization(
            sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
        )

        total_weight = sum(allocation.allocation.values())
        assert abs(total_weight - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_mean_variance_without_correlation(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test mean-variance falls back to equal-weight without correlation matrix."""
        allocation = await constructor._mean_variance_optimization(
            sample_assets, sample_returns, sample_volatilities, None
        )

        # Should fall back to equal-weight
        assert abs(allocation.allocation[sample_assets[0]] - 0.25) < 0.01

    @pytest.mark.asyncio
    async def test_mean_variance_positive_sharpe(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test that Sharpe ratio is positive for positive returns."""
        allocation = await constructor._mean_variance_optimization(
            sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
        )

        assert allocation.sharpe_ratio > 0


# =============================================================================
# Test Risk Parity Allocation
# =============================================================================

class TestRiskParityAllocation:
    """Test risk parity allocation."""

    @pytest.mark.asyncio
    async def test_risk_parity_basic(self, constructor, sample_assets, sample_volatilities):
        """Test basic risk parity allocation."""
        allocation = await constructor._risk_parity_allocation(sample_assets, sample_volatilities)

        assert allocation.method == OptimizationMethod.RISK_PARITY.value
        assert allocation.is_optimized is True
        assert allocation.num_assets == 4

    @pytest.mark.asyncio
    async def test_risk_parity_weights_sum_to_one(self, constructor, sample_assets, sample_volatilities):
        """Test that risk parity weights sum to 1.0."""
        allocation = await constructor._risk_parity_allocation(sample_assets, sample_volatilities)
        total_weight = sum(allocation.allocation.values())
        assert abs(total_weight - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_risk_parity_inverse_volatility(self, constructor, sample_assets, sample_volatilities):
        """Test that higher volatility assets get lower weights."""
        allocation = await constructor._risk_parity_allocation(sample_assets, sample_volatilities)

        # AMZN has highest volatility (0.25), should have lowest weight
        # MSFT has lowest volatility (0.18), should have highest weight
        assert allocation.allocation["MSFT"] > allocation.allocation["AMZN"]
        assert allocation.allocation["MSFT"] > allocation.allocation["GOOGL"]

    @pytest.mark.asyncio
    async def test_risk_parity_single_asset(self, constructor):
        """Test risk parity with single asset."""
        allocation = await constructor._risk_parity_allocation(["SPY"], {"SPY": 0.15})
        assert allocation.allocation["SPY"] == 1.0


# =============================================================================
# Test Maximum Sharpe Ratio Optimization
# =============================================================================

class TestMaxSharpeOptimization:
    """Test maximum Sharpe ratio optimization."""

    @pytest.mark.asyncio
    async def test_max_sharpe_basic(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test basic maximum Sharpe optimization."""
        allocation = await constructor._max_sharpe_optimization(
            sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
        )

        assert allocation.method == OptimizationMethod.MAX_SHARPE.value
        assert allocation.is_optimized is True
        assert allocation.sharpe_ratio > 0

    @pytest.mark.asyncio
    async def test_max_sharpe_allocation_valid(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test that max Sharpe allocation is valid."""
        allocation = await constructor._max_sharpe_optimization(
            sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
        )

        total_weight = sum(allocation.allocation.values())
        assert abs(total_weight - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_max_sharpe_without_correlation(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test max Sharpe falls back without correlation matrix."""
        allocation = await constructor._max_sharpe_optimization(
            sample_assets, sample_returns, sample_volatilities, None
        )

        assert allocation.allocation[sample_assets[0]] > 0


# =============================================================================
# Test Covariance Matrix Building
# =============================================================================

class TestCovarianceMatrix:
    """Test covariance matrix construction."""

    @pytest.mark.asyncio
    async def test_covariance_matrix_diagonal(
        self, constructor, sample_assets, sample_volatilities, sample_correlation_matrix
    ):
        """Test that covariance matrix diagonal equals variance."""
        cov = await constructor._build_covariance_matrix(
            sample_assets, sample_volatilities, sample_correlation_matrix
        )

        for asset in sample_assets:
            # Variance = volatility^2
            expected_var = sample_volatilities[asset] ** 2
            actual_var = cov[asset][asset]
            assert abs(actual_var - expected_var) < 1e-6

    @pytest.mark.asyncio
    async def test_covariance_matrix_symmetric(
        self, constructor, sample_assets, sample_volatilities, sample_correlation_matrix
    ):
        """Test that covariance matrix is symmetric."""
        cov = await constructor._build_covariance_matrix(
            sample_assets, sample_volatilities, sample_correlation_matrix
        )

        for asset1 in sample_assets:
            for asset2 in sample_assets:
                assert abs(cov[asset1][asset2] - cov[asset2][asset1]) < 1e-6

    @pytest.mark.asyncio
    async def test_covariance_matrix_off_diagonal(
        self, constructor, sample_assets, sample_volatilities, sample_correlation_matrix
    ):
        """Test that off-diagonal elements use correlation correctly."""
        cov = await constructor._build_covariance_matrix(
            sample_assets, sample_volatilities, sample_correlation_matrix
        )

        # Cov(A,B) = Corr(A,B) * Vol(A) * Vol(B)
        expected_cov = (
            sample_correlation_matrix["AAPL"]["MSFT"] *
            sample_volatilities["AAPL"] *
            sample_volatilities["MSFT"]
        )
        actual_cov = cov["AAPL"]["MSFT"]
        assert abs(actual_cov - expected_cov) < 1e-6


# =============================================================================
# Test Portfolio Volatility Calculation
# =============================================================================

class TestPortfolioVolatility:
    """Test portfolio volatility calculation."""

    @pytest.mark.asyncio
    async def test_portfolio_volatility_single_asset(
        self, constructor, sample_volatilities, sample_correlation_matrix
    ):
        """Test portfolio volatility for single asset equals asset volatility."""
        cov = await constructor._build_covariance_matrix(
            ["AAPL"], {"AAPL": sample_volatilities["AAPL"]}, sample_correlation_matrix
        )

        allocation = {"AAPL": 1.0}
        vol = await constructor._calculate_portfolio_volatility(allocation, cov)

        assert abs(vol - sample_volatilities["AAPL"]) < 1e-6

    @pytest.mark.asyncio
    async def test_portfolio_volatility_equal_weight(
        self, constructor, sample_assets, sample_volatilities, sample_correlation_matrix
    ):
        """Test portfolio volatility for equal-weight allocation."""
        cov = await constructor._build_covariance_matrix(
            sample_assets, sample_volatilities, sample_correlation_matrix
        )

        allocation = {asset: 0.25 for asset in sample_assets}
        vol = await constructor._calculate_portfolio_volatility(allocation, cov)

        # Should be less than average volatility due to diversification
        avg_vol = sum(sample_volatilities.values()) / len(sample_assets)
        assert vol < avg_vol

    @pytest.mark.asyncio
    async def test_portfolio_volatility_positive(
        self, constructor, sample_assets, sample_volatilities, sample_correlation_matrix
    ):
        """Test that portfolio volatility is always positive."""
        cov = await constructor._build_covariance_matrix(
            sample_assets, sample_volatilities, sample_correlation_matrix
        )

        allocation = {asset: 0.25 for asset in sample_assets}
        vol = await constructor._calculate_portfolio_volatility(allocation, cov)

        assert vol > 0


# =============================================================================
# Test Main Construct Portfolio Method
# =============================================================================

class TestConstructPortfolio:
    """Test main construct_portfolio method."""

    @pytest.mark.asyncio
    async def test_construct_equal_weight_method(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test constructing portfolio with equal-weight method."""
        allocation = await constructor.construct_portfolio(
            sample_assets, sample_returns, sample_volatilities,
            method=OptimizationMethod.EQUAL_WEIGHT.value
        )

        assert allocation.method == OptimizationMethod.EQUAL_WEIGHT.value
        assert all(abs(w - 0.25) < 1e-6 for w in allocation.allocation.values())

    @pytest.mark.asyncio
    async def test_construct_risk_parity_method(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test constructing portfolio with risk parity method."""
        allocation = await constructor.construct_portfolio(
            sample_assets, sample_returns, sample_volatilities,
            method=OptimizationMethod.RISK_PARITY.value
        )

        assert allocation.method == OptimizationMethod.RISK_PARITY.value
        assert allocation.is_optimized is True

    @pytest.mark.asyncio
    async def test_construct_mean_variance_method(
        self, constructor, sample_assets, sample_returns, sample_volatilities, sample_correlation_matrix
    ):
        """Test constructing portfolio with mean-variance method."""
        allocation = await constructor.construct_portfolio(
            sample_assets, sample_returns, sample_volatilities,
            correlation_matrix=sample_correlation_matrix,
            method=OptimizationMethod.MEAN_VARIANCE.value
        )

        assert allocation.method == OptimizationMethod.MEAN_VARIANCE.value
        assert allocation.sharpe_ratio > 0

    @pytest.mark.asyncio
    async def test_construct_unknown_method_fallback(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test that unknown method falls back to equal-weight."""
        allocation = await constructor.construct_portfolio(
            sample_assets, sample_returns, sample_volatilities,
            method="unknown_method"
        )

        assert allocation.method == OptimizationMethod.EQUAL_WEIGHT.value

    @pytest.mark.asyncio
    async def test_construct_error_handling(
        self, constructor, sample_assets, sample_returns, sample_volatilities
    ):
        """Test that errors are handled gracefully with fallback."""
        # Call with minimal data should still succeed with fallback
        allocation = await constructor.construct_portfolio(
            sample_assets, {}, {},
            method=OptimizationMethod.MEAN_VARIANCE.value
        )

        # Should fall back to equal-weight
        assert allocation.allocation[sample_assets[0]] > 0


# =============================================================================
# Test Allocation Validation
# =============================================================================

class TestAllocationValidation:
    """Test allocation validation."""

    def test_validate_allocation_valid(self, constructor):
        """Test validation of valid allocation."""
        allocation = {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.25}
        assert constructor.validate_allocation(allocation) is True

    def test_validate_allocation_small_error(self, constructor):
        """Test validation allows small floating-point errors."""
        allocation = {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.2500000001}
        assert constructor.validate_allocation(allocation) is True

    def test_validate_allocation_invalid_sum(self, constructor):
        """Test validation rejects invalid sums."""
        allocation = {"AAPL": 0.30, "MSFT": 0.30, "GOOGL": 0.30, "AMZN": 0.30}
        assert constructor.validate_allocation(allocation) is False
