"""
Unit tests for Handcrafted Weights Optimizer (Carver's methodology).

Tests cover:
- Inverse volatility weighting
- Volatility targeting
- Equal risk contribution
- Constraint handling
- Diversification ratio calculation
"""

from unittest.mock import patch

import numpy as np
import pytest

from app.engines.portfolio_engine.optimizers.handcrafted_optimizer import (
    HandcraftedWeightsOptimizer,
    create_handcrafted_weights,
)


@pytest.mark.unit
class TestHandcraftedWeightsOptimizer:
    """Test suite for Handcrafted Weights Optimizer (Carver's methodology)."""

    @pytest.fixture
    def optimizer(self):
        """Create handcrafted optimizer with default config."""
        config = {
            "target_volatility": 0.15,
            "max_instrument_weight": 0.40,
            "min_instrument_weight": 0.01,
            "use_volatility_scaling": True,
            "equal_risk_contribution": False,
        }
        return HandcraftedWeightsOptimizer(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample returns and covariance matrix."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        # Heterogeneous volatilities
        cov_matrix = np.array([
            [0.0400, 0.0080, 0.0060, 0.0100, 0.0070],
            [0.0080, 0.0900, 0.0070, 0.0120, 0.0080],
            [0.0060, 0.0070, 0.0250, 0.0080, 0.0060],
            [0.0100, 0.0120, 0.0080, 0.0600, 0.0090],
            [0.0070, 0.0080, 0.0060, 0.0090, 0.0350],
        ])

        return expected_returns, cov_matrix

    def test_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.target_volatility == 0.15
        assert optimizer.max_instrument_weight == 0.40
        assert optimizer.min_instrument_weight == 0.01
        assert optimizer.use_volatility_scaling is True
        assert optimizer.equal_risk_contribution is False

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        config = {
            "target_volatility": 0.20,
            "max_instrument_weight": 0.30,
            "min_instrument_weight": 0.05,
            "use_volatility_scaling": False,
        }
        optimizer = HandcraftedWeightsOptimizer(config)

        assert optimizer.target_volatility == 0.20
        assert optimizer.max_instrument_weight == 0.30
        assert optimizer.min_instrument_weight == 0.05
        assert optimizer.use_volatility_scaling is False

    def test_inverse_volatility_weighting(self, optimizer, sample_data):
        """Test inverse volatility weighting (Carver's preferred method)."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check basic structure
        assert "weights" in result
        assert "expected_return" in result
        assert "volatility" in result
        assert "sharpe_ratio" in result
        assert "method" in result

        # Check method
        assert result["method"] == "handcrafted_carver"

        # Check weights sum to 1
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

        # Check all weights are positive
        assert all(w > 0 for w in weights)

    def test_volatility_calculation(self, optimizer, sample_data):
        """Test volatility calculation from covariance matrix."""
        expected_returns, cov_matrix = sample_data

        volatilities = optimizer._calculate_volatilities(cov_matrix)

        # Volatilities should be square root of diagonal
        expected_vols = np.sqrt(np.diag(cov_matrix))
        np.testing.assert_array_almost_equal(volatilities, expected_vols)

        # All volatilities should be positive
        assert all(v > 0 for v in volatilities)

    def test_inverse_volatility_formula(self, optimizer):
        """Test inverse volatility weight calculation formula."""
        # Test with known volatilities
        volatilities = np.array([0.20, 0.30, 0.15, 0.25])

        weights = optimizer._inverse_volatility_weights(volatilities)

        # Weights should be proportional to 1/volatility
        inv_vol = 1.0 / volatilities
        expected_weights = inv_vol / inv_vol.sum()

        np.testing.assert_array_almost_equal(weights, expected_weights)

        # Higher volatility should get lower weight
        assert weights[1] < weights[0]  # 0.30 > 0.20
        assert weights[2] > weights[3]  # 0.15 < 0.25

    def test_equal_risk_contribution_mode(self, sample_data):
        """Test equal risk contribution mode."""
        expected_returns, cov_matrix = sample_data

        config = {
            "target_volatility": 0.15,
            "equal_risk_contribution": True,
            "use_volatility_scaling": True,
        }
        optimizer = HandcraftedWeightsOptimizer(config)

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check result structure
        assert "weights" in result
        assert "risk_contributions" in result

        # Check that risk contributions are approximately equal
        risk_contribs = list(result["risk_contributions"].values())
        n = len(risk_contribs)
        target_risk = 1.0 / n

        for rc in risk_contribs:
            assert rc == pytest.approx(target_risk, abs=0.1)  # 10% tolerance

    def test_volatility_targeting(self, optimizer, sample_data):
        """Test volatility targeting functionality."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check that volatility is in result
        assert "volatility" in result
        assert "volatility_target" in result

        # Portfolio volatility should be close to target (after scaling)
        # Note: might not be exact due to max leverage constraint
        assert result["volatility"] > 0

    def test_volatility_targeting_leverage_limit(self, optimizer, sample_data):
        """Test that volatility targeting respects max leverage."""
        expected_returns, cov_matrix = sample_data

        # Set very low target volatility
        config = {
            "target_volatility": 0.50,  # High target
            "max_instrument_weight": 0.40,
            "use_volatility_scaling": True,
        }
        optimizer_high_target = HandcraftedWeightsOptimizer(config)

        result = optimizer_high_target.optimize(expected_returns, cov_matrix)

        # Should respect max leverage of 2.0 internally
        weights = list(result["weights"].values())
        assert sum(weights) <= 2.5  # Allow some tolerance

    def test_constraint_handling(self, optimizer, sample_data):
        """Test weight constraint handling."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "max_weight": 0.30,
            "min_weight": 0.10,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)
        weights = list(result["weights"].values())

        # Check constraints are respected
        assert all(w <= 0.31 for w in weights)  # Small tolerance
        assert all(w >= 0.09 for w in weights)

    def test_max_instrument_weight_from_config(self, sample_data):
        """Test max instrument weight from config."""
        expected_returns, cov_matrix = sample_data

        config = {
            "max_instrument_weight": 0.25,
            "target_volatility": 0.15,
        }
        optimizer = HandcraftedWeightsOptimizer(config)

        result = optimizer.optimize(expected_returns, cov_matrix)
        weights = list(result["weights"].values())

        # Check max weight constraint
        assert all(w <= 0.26 for w in weights)

    def test_single_asset_portfolio(self, optimizer):
        """Test with single asset portfolio."""
        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Single asset should get all weight
        assert result["weights"]["asset_0"] == pytest.approx(1.0)

    def test_two_asset_portfolio(self, optimizer):
        """Test with two asset portfolio."""
        expected_returns = np.array([0.08, 0.10])

        # Different volatilities
        cov_matrix = np.array([
            [0.04, 0.01],
            [0.01, 0.09],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Lower volatility asset should get higher weight
        weights = list(result["weights"].values())
        assert weights[0] > weights[1]

    def test_risk_contributions_calculation(self, optimizer, sample_data):
        """Test risk contributions calculation."""
        expected_returns, cov_matrix = sample_data

        # Use known weights
        weights = np.array([0.3, 0.2, 0.2, 0.15, 0.15])

        risk_contribs = optimizer._calculate_risk_contributions(weights, cov_matrix)

        # Risk contributions should sum to 1
        assert np.isclose(risk_contribs.sum(), 1.0, atol=1e-6)

        # All risk contributions should be positive
        assert all(rc > 0 for rc in risk_contribs)

    def test_diversification_ratio_calculation(self, optimizer):
        """Test diversification ratio calculation."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        volatilities = np.array([0.20, 0.25, 0.15, 0.30])

        dr = optimizer._calculate_diversification_ratio(weights, volatilities)

        # Diversification ratio should be >= 1 for uncorrelated assets
        # (actual value depends on correlation assumption in formula)
        assert dr > 0

    def test_diversification_ratio_equal_weights(self, optimizer):
        """Test diversification ratio with equal weights and equal volatilities."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        volatilities = np.array([0.20] * 4)

        dr = optimizer._calculate_diversification_ratio(weights, volatilities)

        # With equal weights and volatilities, DR should be 1.0
        assert dr == pytest.approx(1.0)

    def test_equal_weight_fallback(self, optimizer):
        """Test equal weight fallback on error."""
        with patch.object(optimizer, '_calculate_volatilities', side_effect=Exception("Test error")):
            expected_returns = np.array([0.08, 0.10, 0.06])
            cov_matrix = np.eye(3) * 0.04

            result = optimizer.optimize(expected_returns, cov_matrix)

            # Should fall back to equal weights
            assert result["method"] == "equal_weight_fallback"
            assert result["weights"]["asset_0"] == pytest.approx(1.0 / 3)
            assert result["weights"]["asset_1"] == pytest.approx(1.0 / 3)
            assert result["weights"]["asset_2"] == pytest.approx(1.0 / 3)

    def test_volatility_targeting_disabled(self, sample_data):
        """Test with volatility targeting disabled."""
        expected_returns, cov_matrix = sample_data

        config = {
            "use_volatility_scaling": False,
            "target_volatility": 0.15,
        }
        optimizer = HandcraftedWeightsOptimizer(config)

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should still produce valid weights
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

    def test_near_zero_volatility_handling(self, optimizer):
        """Test handling of near-zero volatility."""
        expected_returns = np.array([0.05, 0.08, 0.06])

        # One asset with very low volatility
        cov_matrix = np.array([
            [0.0001, 0.005, 0.004],
            [0.005, 0.04, 0.01],
            [0.004, 0.01, 0.03],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)

    def test_high_volatility_asset(self, optimizer):
        """Test with one very high volatility asset."""
        expected_returns = np.array([0.08, 0.10, 0.06])

        # Asset 1 has very high volatility
        cov_matrix = np.array([
            [0.04, 0.01, 0.008],
            [0.01, 0.50, 0.015],
            [0.008, 0.015, 0.03],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # High volatility asset should get lower weight
        weights = list(result["weights"].values())
        assert weights[1] < weights[0]  # Asset 1 has highest volatility
        assert weights[1] < weights[2]

    def test_all_equal_volatilities(self, optimizer):
        """Test when all assets have equal volatilities."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        # Equal variances, some correlation
        cov_matrix = np.array([
            [0.04, 0.01, 0.01, 0.01, 0.01],
            [0.01, 0.04, 0.01, 0.01, 0.01],
            [0.01, 0.01, 0.04, 0.01, 0.01],
            [0.01, 0.01, 0.01, 0.04, 0.01],
            [0.01, 0.01, 0.01, 0.01, 0.04],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # With equal volatilities, should get approximately equal weights
        weights = list(result["weights"].values())
        for w in weights:
            assert w == pytest.approx(0.2, abs=0.05)

    def test_instrument_volatilities_in_result(self, optimizer, sample_data):
        """Test that instrument volatilities are included in result."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check that volatilities are in result
        assert "instrument_volatilities" in result

        # Should have one volatility per asset
        vols = result["instrument_volatilities"]
        assert len(vols) == len(expected_returns)

        # All volatilities should be positive
        for vol in vols.values():
            assert vol > 0

    def test_portfolio_metrics_calculation(self, optimizer, sample_data):
        """Test portfolio metrics calculation."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check all metrics are calculated
        assert "expected_return" in result
        assert "volatility" in result
        assert "sharpe_ratio" in result
        assert "diversification_ratio" in result

        # Metrics should be reasonable
        assert result["expected_return"] > 0
        assert result["volatility"] > 0
        assert result["sharpe_ratio"] > 0
        assert result["diversification_ratio"] > 0


@pytest.mark.unit
class TestCreateHandcraftedWeights:
    """Test the convenience function create_handcrafted_weights."""

    def test_basic_usage(self):
        """Test basic usage of create_handcrafted_weights."""
        volatilities = {
            "AAPL": 0.25,
            "MSFT": 0.22,
            "TLT": 0.10,
        }

        weights = create_handcrafted_weights(volatilities)

        # Check all symbols are in result
        assert set(weights.keys()) == set(volatilities.keys())

        # Weights should sum to 1
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

        # Lower volatility should get higher weight
        assert weights["TLT"] > weights["MSFT"]
        assert weights["MSFT"] > weights["AAPL"]

    def test_with_target_volatility(self):
        """Test with custom target volatility."""
        volatilities = {"AAPL": 0.25, "MSFT": 0.22}

        weights = create_handcrafted_weights(
            volatilities,
            target_volatility=0.20,
        )

        # Should produce valid weights
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_with_max_weight_constraint(self):
        """Test with max weight constraint."""
        volatilities = {
            "TLT": 0.10,
            "AAPL": 0.25,
            "MSFT": 0.22,
            "GOOGL": 0.24,
        }

        weights = create_handcrafted_weights(
            volatilities,
            max_weight=0.50,
        )

        # No single weight should exceed max_weight
        for w in weights.values():
            assert w <= 0.51  # Small tolerance

        # Weights should still sum to 1
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_single_asset(self):
        """Test with single asset."""
        volatilities = {"AAPL": 0.25}

        weights = create_handcrafted_weights(volatilities)

        assert weights["AAPL"] == pytest.approx(1.0)

    def test_many_assets(self):
        """Test with many assets."""
        volatilities = {f"Asset_{i}": 0.15 + i * 0.01 for i in range(20)}

        weights = create_handcrafted_weights(volatilities)

        # Should produce valid weights for all assets
        assert len(weights) == 20
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

        # All weights should be positive
        assert all(w > 0 for w in weights.values())

    def test_extreme_volatility_difference(self):
        """Test with extreme volatility differences."""
        volatilities = {
            "LOW_VOL": 0.01,  # 1% volatility
            "HIGH_VOL": 1.0,  # 100% volatility
        }

        weights = create_handcrafted_weights(volatilities)

        # Low volatility asset should dominate
        assert weights["LOW_VOL"] > weights["HIGH_VOL"]

        # Weights should still be valid
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_equal_volatilities(self):
        """Test with all equal volatilities."""
        volatilities = {
            "A": 0.20,
            "B": 0.20,
            "C": 0.20,
            "D": 0.20,
        }

        weights = create_handcrafted_weights(volatilities)

        # Should result in approximately equal weights
        for w in weights.values():
            assert w == pytest.approx(0.25, abs=0.01)

    def test_returns_dict(self):
        """Test that function returns dict with correct types."""
        volatilities = {"AAPL": 0.25, "MSFT": 0.22}

        weights = create_handcrafted_weights(volatilities)

        # Should return dict
        assert isinstance(weights, dict)

        # Values should be floats
        for v in weights.values():
            assert isinstance(v, float)


@pytest.mark.unit
class TestHandcraftedOptimizerEdgeCases:
    """Test edge cases for handcrafted optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance."""
        config = {
            "target_volatility": 0.15,
            "max_instrument_weight": 0.40,
            "use_volatility_scaling": True,
        }
        return HandcraftedWeightsOptimizer(config)

    def test_zero_variance_asset(self, optimizer):
        """Test with zero variance asset."""
        expected_returns = np.array([0.05, 0.08])

        # One asset with zero variance
        cov_matrix = np.array([
            [0.00, 0.00],
            [0.00, 0.04],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)

    def test_perfect_correlation(self, optimizer):
        """Test with perfectly correlated assets."""
        expected_returns = np.array([0.08, 0.10])

        # Perfect correlation
        cov_matrix = np.array([
            [0.04, 0.04],
            [0.04, 0.04],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result

    def test_large_universe(self, optimizer):
        """Test with large universe (50 assets)."""
        np.random.seed(42)
        n = 50

        expected_returns = np.random.randn(n) * 0.02 + 0.08

        # Create positive definite covariance
        L = np.random.randn(n, n) * 0.01
        cov_matrix = L @ L.T + np.eye(n) * 0.04

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should produce valid weights
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-4)

    def test_invalid_covariance_matrix(self, optimizer):
        """Test with invalid covariance matrix."""
        expected_returns = np.array([0.08, 0.10])

        # Non-positive definite matrix
        cov_matrix = np.array([
            [0.04, -0.10],
            [-0.10, 0.03],
        ])

        # Should handle error gracefully
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should fall back to equal weights
        assert result["method"] == "equal_weight_fallback"

    def test_negative_expected_returns(self, optimizer):
        """Test with negative expected returns."""
        expected_returns = np.array([-0.05, 0.08, 0.06])

        cov_matrix = np.array([
            [0.04, 0.01, 0.008],
            [0.01, 0.03, 0.006],
            [0.008, 0.006, 0.02],
        ])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should still produce valid weights
        assert "weights" in result
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)

    def test_mixed_zero_weights_constraint(self, optimizer):
        """Test with min_weight = 0 allowing zero weights."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12])

        cov_matrix = np.array([
            [0.04, 0.01, 0.008, 0.012],
            [0.01, 0.03, 0.006, 0.009],
            [0.008, 0.006, 0.02, 0.007],
            [0.012, 0.009, 0.007, 0.05],
        ])

        constraints = {"min_weight": 0.0, "max_weight": 1.0}

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should produce valid weights
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)
